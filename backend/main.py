# app/main.py
from fastapi import FastAPI, HTTPException, Query, Body
from typing import List, Optional, Dict, Any, Tuple
import logging
import time
import asyncio
from datetime import datetime, timedelta, timezone
import pandas as pd
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from services.mongo_service import (
    connect_to_mongo,
    close_mongo_connection,
    get_ohlcv_from_db,
    store_ohlcv_in_db,
    get_portfolio_from_cache,
    store_portfolio_in_cache,
    store_forecast_signals,
    get_recent_forecast_signals,
    get_cross_chain_portfolio_from_cache,
    store_cross_chain_portfolio_in_cache
)
from models import FusionQuoteRequest, FusionOrderBuildRequest, FusionOrderSubmitRequest, SingleChainPortfolioOptimizationResult, CrossChainPortfolioResponse, Signal, ForecastSignalRecord
from services import one_inch_data_service , one_inch_fusion_service
from configs import *
from forecast.main_pipeline import run_forecast_to_portfolio_pipeline, filter_non_stablecoin_pairs, rank_assets_based_on_signals
from forecast.quant_forecast import generate_quant_advanced_signals
from forecast.ta_forecast import generate_ta_signals
from forecast.mvo_portfolio import calculate_mvo_inputs, optimize_portfolio_mvo

# Configure logging for the main application
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

app = FastAPI(
    title="1inch Token Screener API",
    description="API for DeFI Asset Management, Token Screening, and Portfolio Optimization",
    version="0.1.0"
)

# CORS configuration
origins = [
    "http://localhost", # Your frontend origin if it's just localhost without port
    "http://localhost:3000",  # Assuming your Next.js frontend runs on port 3000
    # Add any other origins you need to allow (e.g., your deployed frontend URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.on_event("startup")
async def startup_app_clients():
 
    await connect_to_mongo()
    logger.info("MongoDB connection established successfully on startup.")
    await one_inch_data_service.get_http_client()
    logger.info("Global HTTPX client initialized.")

@app.on_event("shutdown")
async def shutdown_app_clients():
    await close_mongo_connection()
    logger.info("MongoDB connection closed on shutdown.")
    
    await one_inch_data_service.close_http_client()
    logger.info("Global HTTPX client closed.")

# Constants for the screener endpoint
API_CALL_DELAY_SECONDS = 0.2 # Delay between 1inch API calls to avoid rate limiting
SCREENING_TIMEOUT_SECONDS = 180 # Increased timeout for screening + OHLCV fetching

@app.get("/screen_tokens/{chain_id}", response_model=List[Dict[str, Any]])
async def screen_tokens_on_chain(
    chain_id: int,
    timeframe: str = Query("day", enum=["month", "week", "day", "hour4", "hour", "min15", "min5"], description="Timeframe for OHLCV data.")
):
    """
    Screens tokens on a given chain:
    1. Fetches a list of whitelisted (popular) tokens.
    2. For each token, attempts to fetch OHLCV data against USDC (fallback USDT):
       - Checks MongoDB for fresh data first.
       - If not found or stale, fetches from 1inch API and stores/updates in MongoDB.
    
    The process is limited to a configurable number of tokens and has a timeout for efficiency.
    """
    # Reduced to 50 tokens for faster processing (was 30)
    default_max_tokens_for_screening_endpoint = 50
    return await asyncio.wait_for(
        _perform_token_screening(chain_id, timeframe, default_max_tokens_for_screening_endpoint),
        timeout=SCREENING_TIMEOUT_SECONDS
    )

async def _perform_token_screening(chain_id: int, timeframe: str, max_tokens_to_screen: int) -> List[Dict[str, Any]]:
    start_time = time.time()
    chain_name = CHAIN_ID_TO_NAME.get(chain_id, "Unknown Chain")
    
    # Determine period_seconds from timeframe and map to 1inch API format
    timeframe_mapping = {
        "min5": ("5min", 300),
        "min15": ("15min", 900), 
        "hour": ("hour", 3600),
        "hour4": ("4hour", 14400),
        "day": ("day", 86400),
        "week": ("week", 604800),
        "month": ("month", 2592000)  # Approx 30 days
    }
    
    timeframe_lower = timeframe.lower()
    if timeframe_lower in timeframe_mapping:
        api_timeframe, period_seconds = timeframe_mapping[timeframe_lower]
        # Update timeframe to match 1inch API format for downstream usage
        timeframe = api_timeframe
    else:
        logger.warning(f"Invalid timeframe '{timeframe}' received. Defaulting to day (86400s).")
        period_seconds = 86400
        timeframe = "day" # Ensure timeframe string is also defaulted for consistency
        
    logger.info(f"Starting token screening for chain: {chain_name} (ID: {chain_id}) with timeframe='{timeframe}' (period: {period_seconds}s) - Timeout: {SCREENING_TIMEOUT_SECONDS}s")

    if not one_inch_data_service.API_KEY or one_inch_data_service.API_KEY == "PrA0uavUMpVOig4aopY0MQMqti3gO19d":
         logger.warning("API Key is not properly set or is using the default placeholder. Results may be limited or fail.")

    # Step 1: Fetch whitelisted tokens
    try:
        all_tokens_on_chain = await one_inch_data_service.fetch_1inch_whitelisted_tokens(chain_id_filter=chain_id)
    except one_inch_data_service.OneInchAPIError as e:
        logger.error(f"API Error fetching token list for {chain_name}: {e}")
        raise HTTPException(status_code=e.status_code or 503, detail=f"Failed to fetch token list from 1inch: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching token list for {chain_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching the token list.")

    if not all_tokens_on_chain:
        logger.warning(f"No whitelisted tokens found for {chain_name}.")
        return []

    # Limit to maximum tokens for performance
    tokens_to_screen_count = min(len(all_tokens_on_chain), max_tokens_to_screen)
    tokens_to_screen = all_tokens_on_chain[:tokens_to_screen_count]
    
    if len(all_tokens_on_chain) > tokens_to_screen_count:
        logger.info(f"Limited token screening to {tokens_to_screen_count} tokens out of {len(all_tokens_on_chain)} available tokens for {chain_name}")
    
    logger.info(f"Attempting to screen {len(tokens_to_screen)} tokens for {chain_name}: {[t['symbol'] for t in tokens_to_screen[:10]]}...") # Log first 10

    # Step 2: Define quote token strategy (USDC -> USDT)
    potential_quotes = []
    
    # Add USDC if available on this chain
    usdc_address_on_chain = USDC_ADDRESSES.get(chain_id)
    if usdc_address_on_chain:
        potential_quotes.append({
            "address": usdc_address_on_chain,
            "symbol_template": f"USDC_on_{chain_name}", 
            "name": "USDC"
        })
    
    # Add USDT if available on this chain
    usdt_address_on_chain = USDT_ADDRESSES.get(chain_id) 
    if usdt_address_on_chain:
        potential_quotes.append({
            "address": usdt_address_on_chain,
            "symbol_template": f"USDT_on_{chain_name}", 
            "name": "USDT"
        })

    # Build comprehensive list of all known stablecoin addresses on this chain (for quote tokens)
    # This specific list `known_stablecoin_addresses_on_chain` is less critical now for the base token,
    # as we'll use the symbol list. But it's still useful for quickly identifying if a quote token address is a stable.
    known_quote_stablecoin_addresses = []
    if usdc_address_on_chain:
        known_quote_stablecoin_addresses.append(usdc_address_on_chain.lower())
    if usdt_address_on_chain:
        known_quote_stablecoin_addresses.append(usdt_address_on_chain.lower())

    # Step 3: Fetch OHLCV for each selected token using the defined quote strategy
    screener_results = []
    for token_info in tokens_to_screen:
        base_token_address = token_info['address']
        base_token_symbol = token_info['symbol']
        
        current_result = {
            "chain_id": chain_id,
            "chain_name": chain_name,
            "base_token_address": base_token_address,
            "base_token_symbol": base_token_symbol,
            "base_token_name": token_info.get('name', 'N/A'),
            "quote_token_address": None,
            "quote_token_symbol": None,
            "short_quote_token_symbol": None,
            "period_seconds": period_seconds,
            "ohlcv_data": None,
            "data_source": "api", # Will be updated if from DB
            "error": "No suitable quote token (USDC/USDT) configured or all attempts failed."
        }

        if not potential_quotes:
            logger.warning(f"No USDC or USDT addresses configured for chain {chain_name}. Cannot fetch OHLCV for {base_token_symbol}.")
            current_result["error"] = f"No USDC or USDT addresses configured for chain {chain_name}."
            screener_results.append(current_result)
            # No API call here, so no explicit delay needed beyond the main loop's delay
            continue

        ohlcv_fetched_successfully = False
        last_error_message_for_token = current_result["error"]

        for attempt_idx, quote_candidate in enumerate(potential_quotes):
            quote_address = quote_candidate["address"]
            long_quote_symbol = f"{quote_candidate['name']}_on_{chain_name}"
            short_quote_symbol = quote_candidate["name"]

            current_result["quote_token_address"] = quote_address # Tentatively set
            current_result["quote_token_symbol"] = long_quote_symbol  # Tentatively set
            current_result["short_quote_token_symbol"] = short_quote_symbol # Tentatively set

            base_addr_lower = base_token_address.lower()
            quote_addr_lower = quote_address.lower()

            if base_addr_lower == quote_addr_lower:
                logger.info(f"Skipping OHLCV for {base_token_symbol} against itself ({short_quote_symbol} on {chain_name}).")
                last_error_message_for_token = f"Self-pair with {short_quote_symbol}, OHLCV not applicable."
                current_result["error"] = last_error_message_for_token
                continue

            # --- NEW: Skip stablecoin vs stablecoin pairs ---
            # Check if base token is a known stablecoin by its symbol
            is_base_stable_by_symbol = token_info.get('symbol', '').upper() in COMMON_STABLECOIN_SYMBOLS
            
            # Quote candidates are USDC/USDT, which are stable.
            # We can also check the quote_address directly if we had a broader list of quote stables.
            is_quote_stable_by_address = quote_addr_lower in known_quote_stablecoin_addresses

            if is_base_stable_by_symbol and is_quote_stable_by_address:
                logger.info(f"Skipping OHLCV for stablecoin base ({base_token_symbol}) vs stablecoin quote ({short_quote_symbol}) on {chain_name}.")
                last_error_message_for_token = f"Stablecoin vs stablecoin pair ({base_token_symbol}/{short_quote_symbol}), OHLCV not fetched."
                current_result["error"] = last_error_message_for_token
                continue # Try next quote candidate

            pair_desc = f"{base_token_symbol}/{long_quote_symbol} on {chain_name}"
            logger.info(f"Processing OHLCV for {pair_desc} (using {short_quote_symbol}, attempt {attempt_idx + 1}/{len(potential_quotes)})...")

            db_check_result = await get_ohlcv_from_db(
                chain_id, base_token_address, quote_address, period_seconds, timeframe
            )
            
            latest_known_timestamp_from_db: Optional[int] = None
            if db_check_result and db_check_result.get("latest_candle_timestamp_in_db") is not None:
                latest_known_timestamp_from_db = db_check_result["latest_candle_timestamp_in_db"]
                logger.info(f"Latest known candle timestamp from DB for {pair_desc} is {latest_known_timestamp_from_db}")

            # Define the 24-hour threshold for API refresh - Extended to 7 days for faster processing
            long_term_refresh_threshold = timedelta(hours=168)  # 7 days (was 23 hours)

            if db_check_result:
                db_candles = db_check_result["data"]
                db_last_updated = db_check_result["last_updated"]
                
                # Check if data is recent enough (less than 24 hours old) to avoid API call
                if datetime.now(timezone.utc) - db_last_updated < long_term_refresh_threshold:
                    current_result["ohlcv_data"] = db_candles
                    current_result["error"] = None
                    current_result["data_source"] = "database_recent"
                    current_result["quote_token_address"] = quote_address 
                    current_result["quote_token_symbol"] = long_quote_symbol
                    current_result["short_quote_token_symbol"] = short_quote_symbol
                    logger.info(f"Using RECENT ({db_last_updated.isoformat()}) OHLCV data from DB for {pair_desc} ({len(db_candles)} candles). No API call needed.")
                    ohlcv_fetched_successfully = True
                    break # Successfully got recent data from DB for this quote pair

                # If data is older than 24 hours, or was marked stale_short_term and we want to refresh
                logger.info(f"Data for {pair_desc} found in DB but is older than {long_term_refresh_threshold} (last updated: {db_last_updated.isoformat()}). Will attempt API fetch.")
                # We will proceed to API fetch below, but we have db_candles if API fails
            else: # No data in DB at all
                logger.info(f"Data for {pair_desc} not in DB. Fetching from API (attempt {attempt_idx + 1}/{len(potential_quotes)})...")

            # --- API Fetching (only if needed) ---
            await asyncio.sleep(API_CALL_DELAY_SECONDS) 

            try:
                # This is where you would implement logic to fetch only NEWER candles if db_check_result had data
                # For now, it fetches the full range as before.
                # from_timestamp_for_api = db_check_result["raw_document"]["ohlcv_candles"][-1]["time"] + 1 if db_check_result and db_candles else None 
                # This 'limit' is for the number of candles, not a time range.
                # The get_ohlcv_data calculates from/to timestamps based on limit.
                
                logger.info(f"Fetching from 1inch API for {pair_desc}...")
                ohlcv_api_response = await one_inch_data_service.get_ohlcv_data(
                    base_token_address=base_token_address, 
                    quote_token_address=quote_address, 
                    timeframe_granularity=timeframe, # This is like "day", "hour"
                    chain_id=chain_id,
                    limit=1000 # Max candles
                )

                if ohlcv_api_response and isinstance(ohlcv_api_response, list):
                    api_candles = ohlcv_api_response
                    current_result["ohlcv_data"] = api_candles
                    current_result["error"] = None
                    current_result["data_source"] = "api"
                    current_result["quote_token_address"] = quote_address 
                    current_result["quote_token_symbol"] = long_quote_symbol
                    current_result["short_quote_token_symbol"] = short_quote_symbol


                    logger.info(f"Successfully fetched {len(api_candles)} candles for {pair_desc} from API.")
                    ohlcv_fetched_successfully = True
                    
                    if api_candles: 
                        await store_ohlcv_in_db(
                            chain_id, base_token_address, quote_address, 
                            period_seconds, timeframe, api_candles,
                            base_token_symbol=base_token_symbol,
                            quote_token_symbol=short_quote_symbol,
                            chain_name=chain_name,
                            latest_known_timestamp_in_db=latest_known_timestamp_from_db
                        )
                    else: 
                        logger.warning(f"API returned success but data array is empty for {pair_desc}. Not storing in DB.")
                    break # Successfully fetched from API
                elif ohlcv_api_response and isinstance(ohlcv_api_response, dict) and "data" in ohlcv_api_response:
                    # Fallback: some APIs might still use nested "data" structure
                    api_candles = ohlcv_api_response["data"]
                    current_result["ohlcv_data"] = api_candles
                    current_result["error"] = None
                    current_result["data_source"] = "api"
                    current_result["quote_token_address"] = quote_address
                    current_result["quote_token_symbol"] = long_quote_symbol
                    current_result["short_quote_token_symbol"] = short_quote_symbol


                    logger.info(f"Successfully fetched {len(api_candles)} candles for {pair_desc} from API (nested data).")
                    ohlcv_fetched_successfully = True
                    
                    if api_candles:
                        await store_ohlcv_in_db(
                            chain_id, base_token_address, quote_address, 
                            period_seconds, timeframe, api_candles,
                            base_token_symbol=base_token_symbol,
                            quote_token_symbol=short_quote_symbol,
                            chain_name=chain_name,
                            latest_known_timestamp_in_db=latest_known_timestamp_from_db
                        )
                    break
                else: # API response was not as expected (e.g. empty dict, non-list)
                    logger.warning(f"OHLCV data for {pair_desc} (with {short_quote_symbol}) was fetched but data is empty, not a list, or in unexpected format. Response type: {type(ohlcv_api_response)}")
                    last_error_message_for_token = f"OHLCV data missing/empty from API (with {short_quote_symbol})."
                    # If API fails but we had stale DB data, use that as a fallback
                    if db_check_result and db_check_result.get("data"):
                        logger.warning(f"API fetch for {pair_desc} failed or returned empty. Using STALE data from DB as fallback (last updated: {db_check_result['last_updated']}).")
                        current_result["ohlcv_data"] = db_check_result["data"]
                        current_result["error"] = None # Clearing error as we have fallback data
                        current_result["data_source"] = "database_stale_fallback"
                        current_result["quote_token_address"] = quote_address
                        current_result["quote_token_symbol"] = long_quote_symbol
                        current_result["short_quote_token_symbol"] = short_quote_symbol
                        ohlcv_fetched_successfully = True # Considered successful as we have data
                        break # Stop trying other quote tokens if we have a fallback
                    else:
                         current_result["error"] = last_error_message_for_token

            except one_inch_data_service.OneInchAPIError as e:
                logger.error(f"API Error fetching OHLCV for {pair_desc} (with {short_quote_symbol}): {e}")
                last_error_message_for_token = f"1inch API Error (with {short_quote_symbol}): {str(e)}"
                if db_check_result and db_check_result.get("data"): # Fallback to stale data on API error
                    logger.warning(f"API error for {pair_desc}. Using STALE data from DB as fallback (last updated: {db_check_result['last_updated']}).")
                    current_result["ohlcv_data"] = db_check_result["data"]
                    current_result["error"] = None
                    current_result["data_source"] = "database_stale_fallback_on_api_error"
                    current_result["quote_token_address"] = quote_address
                    current_result["quote_token_symbol"] = long_quote_symbol
                    current_result["short_quote_token_symbol"] = short_quote_symbol
                    ohlcv_fetched_successfully = True
                    break
                else:
                    current_result["error"] = last_error_message_for_token
                if e.response_text and "charts not supported for chosen tokens" in e.response_text:
                    logger.warning(f"'Charts not supported' error for {pair_desc} with {short_quote_symbol}. Fallback (if any) will proceed.")
            except Exception as e:
                logger.error(f"Unexpected error fetching OHLCV for {pair_desc} (with {short_quote_symbol}): {e}", exc_info=True)
                last_error_message_for_token = f"Unexpected error (with {short_quote_symbol}): {str(e)}"
                if db_check_result and db_check_result.get("data"): # Fallback to stale data on general error
                    logger.warning(f"Unexpected error for {pair_desc}. Using STALE data from DB as fallback (last updated: {db_check_result['last_updated']}).")
                    current_result["ohlcv_data"] = db_check_result["data"]
                    current_result["error"] = None
                    current_result["data_source"] = "database_stale_fallback_on_exception"
                    current_result["quote_token_address"] = quote_address
                    current_result["quote_token_symbol"] = long_quote_symbol
                    current_result["short_quote_token_symbol"] = short_quote_symbol
                    ohlcv_fetched_successfully = True
                    break
                else:
                    current_result["error"] = last_error_message_for_token
            
        if not ohlcv_fetched_successfully:
             current_result["error"] = last_error_message_for_token 

        screener_results.append(current_result)

    logger.info(f"Screening completed for chain: {chain_name}. Returning {len(screener_results)} results.")
    
    end_time = time.time()
    total_time = end_time - start_time
    logger.info(f"Token screening completed in {total_time:.2f} seconds (limit: {SCREENING_TIMEOUT_SECONDS}s)")
    
    return screener_results

# Fusion+ API endpoints
@app.post("/fusion/quote", response_model=Dict[str, Any])
async def get_fusion_quote(request: FusionQuoteRequest):
    """
    Get a cross-chain swap quote using 1inch Fusion+
    """
    logger.info(f"Getting Fusion+ quote for {request.src_token_address} on chain {request.src_chain_id} to {request.dst_token_address} on chain {request.dst_chain_id}")
    
    try:
        quote = one_inch_fusion_service.get_fusion_plus_quote_backend(
            src_chain_id=request.src_chain_id,
            dst_chain_id=request.dst_chain_id,
            src_token_address=request.src_token_address,
            dst_token_address=request.dst_token_address,
            amount_wei=request.amount_wei,
            wallet_address=request.wallet_address,
            enable_estimate=request.enable_estimate
        )
        return quote
    except one_inch_fusion_service.OneInchAPIError as e:
        logger.error(f"API Error getting Fusion+ quote: {e}")
        raise HTTPException(status_code=e.status_code or 503, detail=f"Failed to get Fusion+ quote: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error getting Fusion+ quote: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.post("/fusion/build_order", response_model=Dict[str, Any])
async def build_fusion_order(request: FusionOrderBuildRequest):
    """
    Build a Fusion+ order structure for signing
    """
    logger.info(f"Building Fusion+ order for wallet {request.wallet_address}")
    
    try:
        order_data = one_inch_fusion_service.prepare_fusion_plus_order_for_signing_backend(
            quote=request.quote,
            wallet_address=request.wallet_address,
            receiver_address=request.receiver_address,
            source_app_name=request.source_app_name,
            preset_name=request.preset_name,
            custom_preset=request.custom_preset,
            permit=request.permit,
            deadline_shift_sec=request.deadline_shift_sec
        )
        return order_data
    except one_inch_fusion_service.OneInchAPIError as e:
        logger.error(f"API Error building Fusion+ order: {e}")
        raise HTTPException(status_code=e.status_code or 503, detail=f"Failed to build Fusion+ order: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error building Fusion+ order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.post("/fusion/submit_order", response_model=Dict[str, Any])
async def submit_fusion_order(request: FusionOrderSubmitRequest):
    """
    Submit a signed Fusion+ order to the 1inch relayer
    """
    logger.info(f"Submitting signed Fusion+ order on chain {request.src_chain_id}")
    
    try:
        submission_result = one_inch_fusion_service.submit_signed_fusion_plus_order_backend(
            src_chain_id=request.src_chain_id,
            signed_order_payload=request.signed_order_payload
        )
        return submission_result
    except one_inch_fusion_service.OneInchAPIError as e:
        logger.error(f"API Error submitting Fusion+ order: {e}")
        raise HTTPException(status_code=e.status_code or 503, detail=f"Failed to submit Fusion+ order: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error submitting Fusion+ order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/fusion/order_status/{order_hash}", response_model=Dict[str, Any])
async def get_order_status(order_hash: str):
    """
    Check the status of a Fusion+ order
    """
    logger.info(f"Checking status for order: {order_hash}")
    
    try:
        status = one_inch_fusion_service.check_order_status(order_hash)
        return status
    except one_inch_fusion_service.OneInchAPIError as e:
        logger.error(f"API Error checking order status: {e}")
        raise HTTPException(status_code=e.status_code or 503, detail=f"Failed to check order status: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error checking order status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Welcome to the 1inch API. Use /docs for API documentation."}

async def process_single_chain_data_gathering(
    chain_id_to_process: int,
    timeframe_to_use: str,
    max_tokens_to_screen_for_chain: int,
    chain_name_map: Dict[int, str] # Pass CHAIN_ID_TO_NAME for consistent naming
) -> Tuple[int, str, List[Dict[str, Any]], Optional[str]]: # chain_id, chain_name, list_of_asset_data, error_message
    """
    Fetches screener results (including OHLCV data as DataFrames) for a single chain.
    """
    chain_start_time = time.time()
    # Use the passed chain_name_map for consistency
    chain_name = chain_name_map.get(chain_id_to_process, f"Unknown Chain ({chain_id_to_process})")
    logger.info(f"Data gathering: Starting for chain: {chain_name} (ID: {chain_id_to_process})")

    asset_data_for_chain: List[Dict[str, Any]] = []
    error_message_for_this_chain: Optional[str] = None

    try:
        screener_results = await asyncio.wait_for(
            _perform_token_screening(chain_id_to_process, timeframe_to_use, max_tokens_to_screen_for_chain),
            timeout=SCREENING_TIMEOUT_SECONDS
        )

        if not screener_results:
            logger.warning(f"Data gathering: No assets found or screened for chain {chain_id_to_process} ({chain_name}).")
            error_message_for_this_chain = "No assets found or screened for this chain via _perform_token_screening."
        else:
            logger.info(f"Data gathering: Received {len(screener_results)} items from _perform_token_screening for chain {chain_name}.")
            for item_idx, item in enumerate(screener_results):
                base_symbol = item.get("base_token_symbol")
                if not (item.get("ohlcv_data") and not item.get("error") and item.get("base_token_address") and item.get("quote_token_address") and base_symbol):
                    logger.warning(f"Data gathering: Skipping item {item_idx} for chain {chain_name} due to missing critical data or error: {item.get('error', 'N/A') if item.get('error') else 'Missing data fields'}")
                    continue

                quote_symbol_short = item.get("quote_token_symbol", "QUOTE").split('_')[0]
                asset_symbol_global = f"{base_symbol}-{quote_symbol_short}_on_{chain_name}"

                try:
                    df = pd.DataFrame(item["ohlcv_data"])
                    if df.empty:
                        logger.warning(f"Data gathering: OHLCV DataFrame initially empty for {asset_symbol_global}. Skipping.")
                        continue
                    
                    if 'time' in df.columns and 'timestamp' not in df.columns:
                        df.rename(columns={'time': 'timestamp'}, inplace=True)
                    if 'timestamp' not in df.columns:
                        logger.warning(f"Data gathering: 'timestamp' column missing for {asset_symbol_global} after potential rename. Skipping.")
                        continue

                    df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce').astype('Int64') # Allow NaNs before dropping
                    df.dropna(subset=['timestamp'], inplace=True) # Drop rows where timestamp couldn't be converted
                    if df.empty:
                        logger.warning(f"Data gathering: DataFrame empty for {asset_symbol_global} after timestamp conversion/dropna. Skipping.")
                        continue
                    
                    required_ohlc_cols = ['open', 'high', 'low', 'close']
                    missing_cols = [col for col in required_ohlc_cols if col not in df.columns]
                    if missing_cols:
                        logger.warning(f"Data gathering: Missing OHLC columns {missing_cols} for {asset_symbol_global}. Skipping.")
                        continue
                        
                    for col in required_ohlc_cols:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    df.dropna(subset=required_ohlc_cols, inplace=True) # Drop rows if OHLC couldn't be numeric
                    if df.empty:
                        logger.warning(f"Data gathering: DataFrame empty for {asset_symbol_global} after OHLC conversion/dropna. Skipping.")
                        continue

                    if 'volume' not in df.columns:
                        logger.debug(f"Data gathering: 'volume' column missing for {asset_symbol_global}. Initializing with 0.0.")
                        df['volume'] = 0.0
                    else:
                        df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0.0)
                    
                    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()


                    asset_data_for_chain.append({
                        "asset_symbol_global": asset_symbol_global,
                        "ohlcv_df": df,
                        "base_token_address": item["base_token_address"],
                        "quote_token_address": item["quote_token_address"],
                        "chain_id": chain_id_to_process,
                        "chain_name": chain_name
                    })
                except Exception as e_df:
                    logger.error(f"Data gathering: Error processing DataFrame for {asset_symbol_global} on chain {chain_name}: {e_df}", exc_info=True)
                    # error_message_for_this_chain might accumulate last error, or just log per-asset
            
            if not asset_data_for_chain and not error_message_for_this_chain: # If all assets from screener failed conversion
                 error_message_for_this_chain = "No valid OHLCV data could be processed for any screened assets on this chain."
                 logger.warning(error_message_for_this_chain)

    except asyncio.TimeoutError:
        logger.error(f"Data gathering: Token screening timed out for chain {chain_id_to_process} ({chain_name}).")
        error_message_for_this_chain = "Token screening phase timed out for this chain."
    except HTTPException as e_http:
        logger.error(f"Data gathering: HTTP error for chain {chain_id_to_process} ({chain_name}): {e_http.detail}")
        error_message_for_this_chain = f"HTTP error during token screening: {e_http.detail}"
    except Exception as e_main:
        logger.error(f"Data gathering: Unexpected error for chain {chain_id_to_process} ({chain_name}): {str(e_main)}", exc_info=True)
        error_message_for_this_chain = f"An unexpected error occurred: {str(e_main)}"
    
    chain_end_time = time.time()
    logger.info(f"Data gathering: Finished for chain {chain_id_to_process} ({chain_name}). Took {chain_end_time - chain_start_time:.2f}s. Found {len(asset_data_for_chain)} valid assets.")
    return chain_id_to_process, chain_name, asset_data_for_chain, error_message_for_this_chain

@app.post("/portfolio/optimize_cross_chain/",
            summary="Screen, Forecast, and Optimize a Single Portfolio Across Multiple Chains",
            response_model=CrossChainPortfolioResponse)
async def get_optimized_portfolios_for_chains(
    chain_ids_str: str = Query(..., alias="chain_ids", description="Comma-separated string of chain IDs. E.g., 1,42161,10"),
    timeframe: str = Query("day", enum=["month", "week", "day", "hour4", "hour", "min15", "min5"], description="Timeframe for OHLCV data."),
    max_tokens_per_chain: int = Query(50, ge=2, le=500, description="Max number of tokens to screen per chain (default 50, range 2-500)."),
    mvo_objective: str = Query("maximize_sharpe", enum=["maximize_sharpe", "minimize_volatility", "maximize_return"]),
    risk_free_rate: float = Query(0.02, description="Risk-free rate."),
    annualization_factor_override: Optional[int] = Query(None, ge=1),
    target_return: Optional[float] = Query(None, description="Target annualized return (e.g., 0.8 for 80%) for 'minimize_volatility'.")
):
    main_request_start_time = time.time()
    try:
        chain_ids_input_list = [int(c.strip()) for c in chain_ids_str.split(',') if c.strip()]
        if not chain_ids_input_list: raise ValueError("No chain IDs provided.")
        # Sort and join to ensure consistent cache key for chain_ids_str
        # This is important if the user enters "1,10" vs "10,1"
        chain_ids_input_list.sort()
        consistent_chain_ids_str = ",".join(map(str, chain_ids_input_list))

    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid chain_ids: {e}")

    logger.info(f"Cross-Chain Global MVO Request: chain_ids_str='{consistent_chain_ids_str}', timeframe={timeframe}, max_tokens_per_chain={max_tokens_per_chain}, objective={mvo_objective}")

    # Attempt to retrieve from cache first
    try:
        cached_result = await get_cross_chain_portfolio_from_cache(
            chain_ids_str=consistent_chain_ids_str,
            timeframe=timeframe,
            max_tokens_per_chain=max_tokens_per_chain,
            mvo_objective=mvo_objective,
            risk_free_rate=risk_free_rate,
            annualization_factor_override=annualization_factor_override,
            target_return=target_return
        )
        if cached_result:
            logger.info(f"✅ Returning CACHED cross-chain portfolio response for request: {consistent_chain_ids_str}, {timeframe}")
            # The cached_result should already be a dict representation of CrossChainPortfolioResponse
            return cached_result # FastAPI will serialize this dict to JSON
    except Exception as e_cache_get:
        logger.warning(f"Error retrieving from cross-chain portfolio cache (request: {consistent_chain_ids_str}, {timeframe}): {e_cache_get}. Proceeding with full calculation.")


    # Map timeframe to 1inch API format and determine period_seconds/annualization
    timeframe_config = {
        "min5": ("5min", 300, 365 * 24 * 12),
        "min15": ("15min", 900, 365 * 24 * 4),
        "hour": ("hour", 3600, 365 * 24),
        "hour4": ("4hour", 14400, 365 * 6),
        "day": ("day", 86400, 365),
        "week": ("week", 604800, 52),
        "month": ("month", 2592000, 12)
    }
    
    timeframe_lower = timeframe.lower()
    if timeframe_lower in timeframe_config:
        api_timeframe, period_seconds, default_annual_factor = timeframe_config[timeframe_lower]
        # Update timeframe to match 1inch API format for downstream usage
        timeframe = api_timeframe
    else: 
        period_seconds, default_annual_factor = 86400, 365 # Default to day
        timeframe = "day"

    annualization_factor = annualization_factor_override if annualization_factor_override is not None else default_annual_factor

    # --- Step 1: Concurrently gather screened asset data from all chains ---
    logger.info("Starting concurrent data gathering for all specified chains...")
    data_gathering_tasks = [
        process_single_chain_data_gathering(cid, timeframe, max_tokens_per_chain, CHAIN_ID_TO_NAME) for cid in chain_ids_input_list # Use the list here
    ]
    gathered_chain_data_results = await asyncio.gather(*data_gathering_tasks, return_exceptions=True)

    # --- Step 2: Aggregate OHLCV data and create unique global asset list ---
    all_asset_identifiers_global: List[Dict[str, Any]] = []
    ohlcv_data_global: Dict[str, pd.DataFrame] = {}
    chain_processing_statuses: Dict[str, Dict[str, Any]] = {}

    for i, result_or_exc in enumerate(gathered_chain_data_results):
        original_chain_id = chain_ids_input_list[i] # Use the list here
        processed_chain_name = CHAIN_ID_TO_NAME.get(original_chain_id, f"Unknown Chain ({original_chain_id})")

        # Explicitly check for CancelledError first
        if isinstance(result_or_exc, asyncio.CancelledError):
            logger.warning(f"Data gathering task for chain {original_chain_id} ({processed_chain_name}) was cancelled.")
            chain_processing_statuses[str(original_chain_id)] = {
                "chain_name": processed_chain_name,
                "status": "error_task_cancelled",
                "error_message": "Task was cancelled.",
                "assets_found": 0
            }
            continue
        # Then check for other exceptions
        elif isinstance(result_or_exc, Exception):
            logger.error(f"Data gathering task for chain {original_chain_id} ({processed_chain_name}) failed with exception: {type(result_or_exc).__name__} - {str(result_or_exc)}", exc_info=result_or_exc)
            chain_processing_statuses[str(original_chain_id)] = {
                "chain_name": processed_chain_name,
                "status": "error_task_exception",
                "error_message": f"{type(result_or_exc).__name__}: {str(result_or_exc)}",
                "assets_found": 0
            }
            continue

        # If we reach here, result_or_exc should be a valid tuple
        try:
            _chain_id, _chain_name, asset_data_list, error_msg_chain = result_or_exc
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to unpack result for chain {original_chain_id} ({processed_chain_name}). Result was: {result_or_exc}. Error: {e}", exc_info=True)
            chain_processing_statuses[str(original_chain_id)] = {
                "chain_name": processed_chain_name,
                "status": "error_unpacking_result",
                "error_message": f"Failed to unpack result: {str(e)}",
                "assets_found": 0
            }
            continue
        
        chain_processing_statuses[str(_chain_id)] = {
            "chain_name": _chain_name, "status": "success_data_gathering" if not error_msg_chain else "partial_data_gathering",
            "error_message": error_msg_chain, "assets_found": len(asset_data_list)
        }
        if error_msg_chain and not asset_data_list: continue

        for asset_data in asset_data_list:
            asset_symbol_g = asset_data["asset_symbol_global"]
            if asset_symbol_g not in ohlcv_data_global:
                ohlcv_data_global[asset_symbol_g] = asset_data["ohlcv_df"]
                all_asset_identifiers_global.append({
                    "asset_symbol": asset_symbol_g, "base_token_address": asset_data["base_token_address"],
                    "quote_token_address": asset_data["quote_token_address"], "chain_id": asset_data["chain_id"],
                    "chain_name": asset_data["chain_name"]
                })
            else: logger.warning(f"Duplicate asset symbol during global aggregation: {asset_symbol_g}. Keeping first.")

    if not all_asset_identifiers_global:
        # Check if any chain had a hard failure vs. just no assets
        hard_failures = sum(1 for stat in chain_processing_statuses.values() if "error" in stat["status"])
        if hard_failures == len(chain_ids_input_list): # Use the list here
             raise HTTPException(status_code=503, detail="Data gathering failed for all requested chains.")
        else:
             raise HTTPException(status_code=404, detail="No valid asset data gathered from any chain after screening. Some chains might have had partial success or no assets.")

    logger.info(f"Global data aggregation complete. Total unique assets for forecasting: {len(all_asset_identifiers_global)}")

    # --- Step 3: Global Forecasting ---
    logger.info("Starting global forecasting for all aggregated assets...")
    global_all_signals: Dict[str, List[Signal]] = {}
    
    valid_identifiers_for_forecast = [
        ident for ident in all_asset_identifiers_global if ident["asset_symbol"] in ohlcv_data_global and not ohlcv_data_global[ident["asset_symbol"]].empty
    ]

    # Define how old a forecast can be to be considered fresh (e.g., 4 hours)
    MAX_FORECAST_AGE_HOURS = 4

    for asset_info_global in valid_identifiers_for_forecast:
        asset_symbol_g = asset_info_global["asset_symbol"]
        original_chain_id_for_signal = asset_info_global["chain_id"]
        base_token_addr_for_signal = asset_info_global["base_token_address"]
        ohlcv_df_g = ohlcv_data_global[asset_symbol_g]
        
        min_data_points = 50
        if len(ohlcv_df_g) < min_data_points:
            logger.warning(f"Global forecast: Insufficient OHLCV for {asset_symbol_g} ({len(ohlcv_df_g)} rows). Need {min_data_points}. Skipping signal generation/retrieval.")
            continue

        # Attempt to retrieve recent forecast signals from DB
        retrieved_db_signals: Optional[List[ForecastSignalRecord]] = await get_recent_forecast_signals(
            asset_symbol_global=asset_symbol_g, 
            chain_id=original_chain_id_for_signal,
            max_forecast_age_hours=MAX_FORECAST_AGE_HOURS
        )

        if retrieved_db_signals:
            logger.info(f"Using {len(retrieved_db_signals)} cached forecast signals for {asset_symbol_g}.")
            current_signals_for_asset = []
            for rec in retrieved_db_signals:
                current_signals_for_asset.append(Signal(
                    asset_symbol=rec.asset_symbol,
                    signal_type=rec.signal_type,
                    confidence=rec.confidence,
                    details=rec.details,
                    timestamp=rec.forecast_timestamp,
                    chain_id=rec.chain_id,
                    base_token_address=rec.base_token_address
                ))
            global_all_signals[asset_symbol_g] = current_signals_for_asset
        else:
            logger.info(f"No recent cached signals for {asset_symbol_g}. Generating new signals...")
            current_price_g = ohlcv_df_g['close'].iloc[-1]
            ta_signals_g = generate_ta_signals(asset_symbol_g, original_chain_id_for_signal, base_token_addr_for_signal, ohlcv_df_g.copy(), current_price_g)
            quant_signals_g = generate_quant_advanced_signals(asset_symbol_g, original_chain_id_for_signal, base_token_addr_for_signal, ohlcv_df_g.copy(), current_price_g, annualization_factor)
            generated_signals_list = ta_signals_g + quant_signals_g
            global_all_signals[asset_symbol_g] = generated_signals_list
            
    if not global_all_signals:
        # Before raising, check if it was due to all assets failing the min_data_points check
        if not valid_identifiers_for_forecast or all(len(ohlcv_data_global[ident["asset_symbol"]]) < 50 for ident in valid_identifiers_for_forecast if ident["asset_symbol"] in ohlcv_data_global):
            raise HTTPException(status_code=404, detail="Global forecasting: No assets had sufficient data (min 50 points) for signal generation.")
        else:
            raise HTTPException(status_code=500, detail="Global forecasting generated no signals for assets that had sufficient data.")

    signals_to_save_globally: List[ForecastSignalRecord] = []
    current_forecast_time_global = int(pd.Timestamp.now(tz='utc').timestamp())
    for asset_sym_g, sig_list_g in global_all_signals.items():
        asset_info_orig = next((aig for aig in all_asset_identifiers_global if aig["asset_symbol"] == asset_sym_g), None)
        if not asset_info_orig: continue

        last_ohlcv_ts_g = int(ohlcv_df_g['timestamp'].iloc[-1]) if asset_sym_g in ohlcv_data_global and not ohlcv_data_global[asset_sym_g].empty else 0
        
        # Parse base and quote symbols from asset_sym_g (e.g., "WBTC-USDC_on_Arbitrum")
        base_s = None
        quote_s = None
        try:
            pair_part = asset_sym_g.split('_on_')[0]
            parts = pair_part.split('-')
            if len(parts) >= 1:
                base_s = parts[0]
            if len(parts) >= 2:
                quote_s = parts[1]
        except Exception:
            logger.warning(f"Could not parse base/quote symbols from asset_symbol: {asset_sym_g}")

        for sig_g in sig_list_g: # sig_list_g is List[Signal]
            signals_to_save_globally.append(ForecastSignalRecord(
                asset_symbol=sig_g.asset_symbol, 
                chain_id=asset_info_orig["chain_id"],
                base_token_address=asset_info_orig["base_token_address"],
                quote_token_address=asset_info_orig.get("quote_token_address"),
                base_token_symbol=base_s,
                quote_token_symbol=quote_s,
                signal_type=sig_g.signal_type, 
                confidence=sig_g.confidence, 
                details=sig_g.details,
                forecast_timestamp=current_forecast_time_global, 
                ohlcv_data_timestamp=last_ohlcv_ts_g,
            ))
            
    if signals_to_save_globally:
        logger.info(f"Attempting to store {len(signals_to_save_globally)} globally generated forecast signals...")
        try: await store_forecast_signals(signals_to_save_globally)
        except Exception as e_store_sig: logger.error(f"Error storing global forecast signals: {e_store_sig}", exc_info=True)

    # --- Step 4: Global Ranking ---
    logger.info("Performing global asset ranking...")
    global_ranked_assets_df = rank_assets_based_on_signals(global_all_signals)
    if global_ranked_assets_df.empty: 
        # Check if global_all_signals was empty due to prior filtering
        if not global_all_signals: 
            raise HTTPException(status_code=404, detail="Global asset ranking failed because no signals were generated or available for ranking.")
        else:
            raise HTTPException(status_code=500, detail="Global asset ranking produced an empty result from non-empty signals.")
    logger.info(f"Global Asset Ranking (Top 5):\n{global_ranked_assets_df.head().to_string()}")

    # --- Step 5: Select Assets for Global MVO ---
    assets_for_global_mvo_input = [
        asset_sym for asset_sym in global_ranked_assets_df['asset'].tolist()
        if asset_sym in ohlcv_data_global and not ohlcv_data_global[asset_sym].empty and len(ohlcv_data_global[asset_sym]) >= 2 
    ]
    if len(assets_for_global_mvo_input) < 2:
        raise HTTPException(status_code=400, detail=f"Not enough assets ({len(assets_for_global_mvo_input)}) for Global MVO after ranking (min 2 with sufficient data for covariance).")

    ohlcv_for_global_mvo_input = {sym: ohlcv_data_global[sym] for sym in assets_for_global_mvo_input}
    
    # --- Step 6: Calculate Global MVO Inputs ---
    logger.info(f"Calculating MVO inputs for {len(assets_for_global_mvo_input)} global assets...")
    mvo_inputs_global = calculate_mvo_inputs(
        ohlcv_data=ohlcv_for_global_mvo_input,
        ranked_assets_df=global_ranked_assets_df[global_ranked_assets_df['asset'].isin(assets_for_global_mvo_input)].copy(), # Pass filtered df
        annualization_factor=annualization_factor
    )
    if mvo_inputs_global["expected_returns"].empty or mvo_inputs_global["covariance_matrix"].empty:
        raise HTTPException(status_code=500, detail="Global MVO input calculation failed (empty returns/covariance).")

    # --- Step 7: Perform Global MVO ---
    logger.info(f"Optimizing global portfolio with objective: {mvo_objective}...")
    optimized_global_portfolio_raw = optimize_portfolio_mvo(
        expected_returns=mvo_inputs_global["expected_returns"],
        covariance_matrix=mvo_inputs_global["covariance_matrix"],
        historical_period_returns_df=mvo_inputs_global.get("historical_period_returns_df"), # Pass historical returns for CVaR
        risk_free_rate=risk_free_rate,
        annualization_factor=annualization_factor,
        objective=mvo_objective, 
        target_return=target_return
    )
    if not optimized_global_portfolio_raw: raise HTTPException(status_code=500, detail="Global portfolio optimization failed.")

    # Ensure weights are converted to dict for Pydantic serialization
    optimized_global_portfolio_serializable = optimized_global_portfolio_raw.copy()
    if "weights" in optimized_global_portfolio_serializable and isinstance(optimized_global_portfolio_serializable["weights"], pd.Series):
        optimized_global_portfolio_serializable["weights"] = optimized_global_portfolio_serializable["weights"].to_dict()

    # --- Calculate alternative MVO portfolios ---
    alternative_optimized_portfolios = {}
    mvo_options_for_alternatives = ["maximize_sharpe", "minimize_volatility", "maximize_return"]

    for alt_obj_name in mvo_options_for_alternatives:
        # For these alternatives, target_return is always None (absolute min_vol for "minimize_volatility")
        alt_calc_target_return = None
        
        is_primary_equivalent = (
            alt_obj_name == mvo_objective and \
            alt_calc_target_return == target_return # target_return is the user's original input
        )

        if not is_primary_equivalent:
            logger.info(f"Calculating alternative global portfolio for objective: {alt_obj_name}")
            try:
                alt_portfolio_raw = optimize_portfolio_mvo(
                    expected_returns=mvo_inputs_global["expected_returns"],
                    covariance_matrix=mvo_inputs_global["covariance_matrix"],
                    historical_period_returns_df=mvo_inputs_global.get("historical_period_returns_df"),
                    risk_free_rate=risk_free_rate,
                    annualization_factor=annualization_factor,
                    objective=alt_obj_name,
                    target_return=alt_calc_target_return 
                )

                if alt_portfolio_raw:
                    alt_portfolio_serializable = alt_portfolio_raw.copy()
                    if "weights" in alt_portfolio_serializable and isinstance(alt_portfolio_serializable["weights"], pd.Series):
                        alt_portfolio_serializable["weights"] = alt_portfolio_serializable["weights"].to_dict()
                    alternative_optimized_portfolios[alt_obj_name] = alt_portfolio_serializable
                else:
                    logger.warning(f"Failed to calculate alternative global portfolio for {alt_obj_name}.")
                    alternative_optimized_portfolios[alt_obj_name] = {"error": f"Optimization failed for {alt_obj_name}"}
            except Exception as e_alt_mvo:
                logger.error(f"Error calculating alternative MVO for {alt_obj_name}: {e_alt_mvo}", exc_info=True)
                alternative_optimized_portfolios[alt_obj_name] = {"error": f"Exception during {alt_obj_name} optimization: {str(e_alt_mvo)}"}

    # --- Step 8: Format and Return Final Response ---
    total_duration = time.time() - main_request_start_time
    global_portfolio_data_payload = {
        "ranked_assets_summary": global_ranked_assets_df[['asset', 'score', 'num_bullish', 'num_bearish']].head(20).to_dict(orient='records'),
        "optimized_portfolio_details": optimized_global_portfolio_serializable,
        "alternative_optimized_portfolios": alternative_optimized_portfolios,
        "mvo_inputs_summary": {
            "expected_returns_top_n": mvo_inputs_global["expected_returns"].nlargest(min(5, len(mvo_inputs_global["expected_returns"]))).to_dict(),
            "covariance_matrix_shape": str(mvo_inputs_global["covariance_matrix"].shape),
            "valid_symbols_count_for_mvo": len(mvo_inputs_global["valid_symbols"])
        },
    }

    final_response_object = CrossChainPortfolioResponse(
        results_by_chain={ # This structure is kept for consistency, but now holds one global result
            "global_cross_chain": SingleChainPortfolioOptimizationResult(
                chain_id=0, # Representing a global/aggregated scope
                chain_name="Global Cross-Chain Portfolio", 
                status="success", 
                data=global_portfolio_data_payload,
                request_params_for_chain={
                    "chain_ids_requested": chain_ids_input_list, "timeframe": timeframe, "mvo_objective": mvo_objective,
                    "risk_free_rate": risk_free_rate, "annualization_factor_used": annualization_factor,
                    "max_tokens_per_chain_screening": max_tokens_per_chain, "target_return": target_return
                })
        },
        overall_request_summary={
            "requested_chain_ids": chain_ids_input_list,
            "timeframe": timeframe, 
            "max_tokens_per_chain_screening": max_tokens_per_chain,
            "mvo_objective": mvo_objective, 
            "risk_free_rate": risk_free_rate, 
            "annualization_factor_used": annualization_factor,
            "total_unique_assets_after_screening": len(all_asset_identifiers_global),
            "assets_considered_for_global_mvo": len(assets_for_global_mvo_input),
            "assets_in_final_portfolio": optimized_global_portfolio_serializable.get("assets_with_allocation", 0),
            "total_processing_time_seconds": round(total_duration, 2),
            "chain_data_gathering_summary": chain_processing_statuses
        }
    )

    # Store the successful result in cache
    try:
        await store_cross_chain_portfolio_in_cache(
            chain_ids_str=consistent_chain_ids_str, # Use the consistent string for cache key
            timeframe=timeframe,
            max_tokens_per_chain=max_tokens_per_chain,
            mvo_objective=mvo_objective,
            risk_free_rate=risk_free_rate,
            annualization_factor_override=annualization_factor_override,
            target_return=target_return,
            portfolio_response_data=final_response_object.model_dump() # Pass the dict form of the response
        )
        logger.info(f"Successfully cached cross-chain portfolio response for request: {consistent_chain_ids_str}, {timeframe}")
    except Exception as e_cache_store:
        logger.warning(f"Failed to store cross-chain portfolio response in cache (request: {consistent_chain_ids_str}, {timeframe}): {e_cache_store}. Proceeding without caching this result.")

    return final_response_object

@app.post("/portfolio/optimize/{chain_id}", summary="Screen, Forecast, and Optimize Portfolio", response_model=Dict[str, Any])
async def get_optimized_portfolio_for_chain(
    chain_id: int,
    timeframe: str = Query("day", enum=["month", "week", "day", "hour4", "hour", "min15", "min5"], description="Timeframe for OHLCV data."),
    num_top_assets: int = Query(10, ge=2, le=20, description="Number of top assets for MVO (2-20). Min 2 for MVO."),
    mvo_objective: str = Query("maximize_sharpe", enum=["maximize_sharpe", "minimize_volatility", "maximize_return"], description="MVO objective function."),
    risk_free_rate: float = Query(0.02, description="Risk-free rate for Sharpe ratio calculation."),
    annualization_factor_override: Optional[int] = Query(None, ge=1, description="Optional: Override annualization factor for MVO (e.g., 365 for daily, 252 for trading days). Default is dynamic based on timeframe."),
    target_return: Optional[float] = Query(None, description="Target annualized return (e.g., 0.8 for 80%). Used if objective is 'minimize_volatility'.")
):
    """
    Full pipeline:
    0. Check portfolio cache for existing results.
    1. Screens tokens on the specified chain to get OHLCV data (fetches from 1inch & stores in DB if needed).
    2. Runs forecasting models (TA & Quant) on the screened assets.
    3. Ranks assets based on forecast signals.
    4. Selects the top N assets.
    5. Performs Mean-Variance Optimization (MVO) to determine optimal portfolio weights.
    6. Caches the results for future requests.
    """
    logger.info(f"Received request for portfolio optimization: chain_id={chain_id}, timeframe={timeframe}, top_n={num_top_assets}, objective={mvo_objective}")

    # 0. Check portfolio cache first
    try:
        cached_portfolio = await get_portfolio_from_cache(
            chain_id=chain_id,
            timeframe=timeframe,
            mvo_objective=mvo_objective,
            risk_free_rate=risk_free_rate,
            annualization_factor=annualization_factor if annualization_factor_override is not None else (365 if timeframe.lower() == "daily" else 365 * 24)
        )
        
        if cached_portfolio:
            logger.info(f"✅ Returning cached portfolio results for chain {chain_id} ({timeframe}, {mvo_objective})")
            return cached_portfolio
        else:
            logger.info(f"No fresh cached portfolio found. Proceeding with full pipeline...")
    except Exception as e:
        logger.warning(f"Error checking portfolio cache: {e}. Proceeding with full pipeline...")

    # 1. Perform token screening (fetches and stores OHLCV)
    try:
        screener_results = await asyncio.wait_for(
            _perform_token_screening(chain_id, timeframe, num_top_assets), # Pass num_top_assets as max_tokens_to_screen
            timeout=SCREENING_TIMEOUT_SECONDS 
        )
    except asyncio.TimeoutError:
        logger.error(f"Portfolio optimization pipeline: Token screening part timed out for chain {chain_id}.")
        raise HTTPException(
            status_code=408,
            detail=f"Token screening phase timed out after {SCREENING_TIMEOUT_SECONDS} seconds. The chain might be too busy or have too many tokens."
        )
    except HTTPException as e: # Propagate HTTP exceptions from screening
        logger.error(f"Portfolio optimization pipeline: HTTP error during token screening: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Portfolio optimization pipeline: Unexpected error during token screening: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during token screening: {str(e)}")


    if not screener_results:
        logger.warning(f"Portfolio optimization pipeline: No assets found or screened for chain {chain_id} and timeframe {timeframe}.")
        raise HTTPException(status_code=404, detail="No assets found or screened for the given chain and timeframe.")

    # 2. Prepare asset_identifiers for the forecasting pipeline
    asset_identifiers: List[Dict[str, Any]] = []
    valid_screened_assets_count = 0
    for item in screener_results:
        if item.get("ohlcv_data") and not item.get("error") and item.get("base_token_address") and item.get("quote_token_address") and item.get("base_token_symbol"):
            # Construct a user-friendly asset symbol, e.g., "WETH-USDC"
            quote_symbol_short = item.get("quote_token_symbol", "QUOTE").split('_')[0]
            asset_symbol = f"{item['base_token_symbol']}-{quote_symbol_short}"
            
            asset_identifiers.append({
                "asset_symbol": asset_symbol,
                "base_token_address": item["base_token_address"],
                "quote_token_address": item["quote_token_address"],
                # The pipeline will use these to fetch the OHLCV data itself
            })
            valid_screened_assets_count += 1
        else:
            logger.debug(f"Skipping asset {item.get('base_token_symbol', 'N/A')} due to missing data or error: {item.get('error', 'N/A')}")
            
    if not asset_identifiers:
        logger.error(f"Portfolio optimization pipeline: No valid assets with OHLCV data after screening for chain {chain_id}.")
        raise HTTPException(status_code=404, detail="No assets with valid OHLCV data found after screening. Cannot proceed with forecasting.")
    
    logger.info(f"Portfolio optimization pipeline: Prepared {len(asset_identifiers)} valid assets for forecasting from {valid_screened_assets_count} screened results.")

    # 3. Determine period_seconds and annualization_factor, map to 1inch API format
    timeframe_config = {
        "min5": ("5min", 300, 365 * 24 * 12),
        "min15": ("15min", 900, 365 * 24 * 4),
        "hour": ("hour", 3600, 365 * 24),
        "hour4": ("4hour", 14400, 365 * 6),
        "day": ("day", 86400, 365),
        "week": ("week", 604800, 52),
        "month": ("month", 2592000, 12)  # Approx 30 days
    }
    
    timeframe_lower = timeframe.lower()
    if timeframe_lower in timeframe_config:
        api_timeframe, period_seconds, default_annual_factor = timeframe_config[timeframe_lower]
        # Update timeframe to match 1inch API format for downstream usage
        timeframe = api_timeframe
    else: 
        logger.warning(f"Invalid timeframe '{timeframe}' in optimize endpoint. Defaulting to daily period and annualization.")
        period_seconds = 86400
        default_annual_factor = 365
        timeframe = "day" # Ensure timeframe string is also defaulted

    annualization_factor = annualization_factor_override if annualization_factor_override is not None else default_annual_factor
    
    logger.info(f"Portfolio optimization pipeline: Using period_seconds={period_seconds}, timeframe_api_string='{timeframe_lower}', annualization_factor={annualization_factor}.")

    # 4. Run the forecast-to-portfolio pipeline
    try:
        # Ensure num_top_assets is not greater than the number of available valid assets
        actual_num_top_assets = min(num_top_assets, len(asset_identifiers))
        if actual_num_top_assets < 2 and len(asset_identifiers) >=2: # If user requested <2 but we have enough, use 2
             actual_num_top_assets = 2
        elif len(asset_identifiers) < 2: # Not enough assets for MVO at all
            logger.error(f"Portfolio optimization pipeline: Not enough valid assets ({len(asset_identifiers)}) for MVO (min 2 required).")
            raise HTTPException(status_code=400, detail=f"Not enough valid assets ({len(asset_identifiers)}) to perform MVO. Minimum 2 assets are required after screening.")

        logger.info(f"Calling forecast pipeline with {len(asset_identifiers)} assets, requesting top {actual_num_top_assets} for MVO.")
        
        pipeline_result = await run_forecast_to_portfolio_pipeline(
            asset_identifiers=asset_identifiers,
            chain_id=chain_id,
            period_seconds=period_seconds,
            timeframe=timeframe,
            num_top_assets_for_portfolio=actual_num_top_assets,
            mvo_objective=mvo_objective,
            risk_free_rate=risk_free_rate,
            annualization_factor=annualization_factor,
            target_return_param=target_return # Pass target_return here
        )
    except Exception as e:
        logger.error(f"Portfolio optimization pipeline: Error during forecast/MVO execution: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred during the forecasting or portfolio optimization process: {str(e)}")

    if not pipeline_result:
        logger.error("Portfolio optimization pipeline: Forecasting pipeline returned no result.")
        raise HTTPException(status_code=500, detail="Forecasting and MVO pipeline did not return a result.")

    if "error" in pipeline_result:
        logger.error(f"Portfolio optimization pipeline: Pipeline completed with an error: {pipeline_result['error']}")
        # Provide more context if available
        detail_message = f"Pipeline error: {pipeline_result['error']}"
        if "ranked_assets" in pipeline_result and pipeline_result["ranked_assets"]:
             detail_message += " Asset ranking was performed. Check logs for details."
        elif "selected_for_portfolio" in pipeline_result and pipeline_result["selected_for_portfolio"]:
             detail_message += f" Assets selected: {pipeline_result['selected_for_portfolio']} but optimization may have failed."

        raise HTTPException(status_code=422, detail=detail_message) # 422 for unprocessable entity due to data issues

    logger.info("Portfolio optimization pipeline: Successfully completed.")
    
    # 6. Cache the successful results
    if pipeline_result and "optimized_portfolio" in pipeline_result and not pipeline_result.get("error"):
        try:
            # Add total_assets_screened to the result for caching
            pipeline_result["total_assets_screened"] = len(screener_results)
            
            await store_portfolio_in_cache(
                chain_id=chain_id,
                timeframe=timeframe,
                mvo_objective=mvo_objective,
                risk_free_rate=risk_free_rate,
                annualization_factor=annualization_factor,
                portfolio_result=pipeline_result
            )
            logger.info(f"✅ Portfolio results cached successfully for chain {chain_id}")
        except Exception as e:
            logger.warning(f"Failed to cache portfolio results: {e}. Returning results anyway.")
    
    return pipeline_result