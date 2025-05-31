# app/main.py
from fastapi import FastAPI, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
import logging
import time
import json
import asyncio
import uvicorn
from pydantic import BaseModel, Field
from services.mongo_service import (
    connect_to_mongo,
    close_mongo_connection,
    get_ohlcv_from_db,
    store_ohlcv_in_db,
    get_portfolio_from_cache,
    store_portfolio_in_cache
)

from models import FusionQuoteRequest, FusionOrderBuildRequest, FusionOrderSubmitRequest
from services import one_inch_data_service
from services import one_inch_fusion_service
from configs import *
from forecast.main_pipeline import run_forecast_to_portfolio_pipeline

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

# --- NEW: FastAPI Startup and Shutdown Events for MongoDB and HTTP Client ---
@app.on_event("startup")
async def startup_app_clients():
    try:
        await connect_to_mongo()
        logger.info("MongoDB connection established successfully on startup.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB on startup: {e}")
    
    try:
        await one_inch_data_service.get_http_client()
        logger.info("Global HTTPX client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize global HTTPX client: {e}")

@app.on_event("shutdown")
async def shutdown_app_clients():
    await close_mongo_connection()
    logger.info("MongoDB connection closed on shutdown.")
    
    await one_inch_data_service.close_http_client()
    logger.info("Global HTTPX client closed.")
# --- END NEW EVENTS ---

# Constants for the screener endpoint
API_CALL_DELAY_SECONDS = 0.2 # Delay between 1inch API calls to avoid rate limiting
SCREENING_TIMEOUT_SECONDS = 180 # Increased timeout for screening + OHLCV fetching

@app.get("/screen_tokens/{chain_id}", response_model=List[Dict[str, Any]])
async def screen_tokens_on_chain(
    chain_id: int,
    timeframe: str = Query("daily", enum=["hourly", "daily"], description="Timeframe for OHLCV data ('daily', 'hourly').")
):
    """
    Screens tokens on a given chain:
    1. Fetches a list of whitelisted (popular) tokens.
    2. For each token, attempts to fetch OHLCV data against USDC (fallback USDT):
       - Checks MongoDB for fresh data first.
       - If not found or stale, fetches from 1inch API and stores/updates in MongoDB.
    
    The process is limited to 30 tokens and has a 1-minute timeout for efficiency.
    """
    try:
        # Wrap the entire screening process with a timeout
        return await asyncio.wait_for(
            _perform_token_screening(chain_id, timeframe),
            timeout=SCREENING_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        logger.warning(f"Token screening for chain {chain_id} timed out after {SCREENING_TIMEOUT_SECONDS} seconds")
        raise HTTPException(
            status_code=408, 
            detail=f"Token screening timed out after {SCREENING_TIMEOUT_SECONDS} seconds. Try again or use a smaller token set."
        )

async def _perform_token_screening(chain_id: int, timeframe: str) -> List[Dict[str, Any]]:
    start_time = time.time()
    chain_name = CHAIN_ID_TO_NAME.get(chain_id, "Unknown Chain")
    
    # Determine period_seconds from timeframe
    if timeframe.lower() == "hourly":
        period_seconds = PERIOD_HOURLY_SECONDS
    elif timeframe.lower() == "daily":
        period_seconds = PERIOD_DAILY_SECONDS
    else:
        logger.warning(f"Invalid timeframe '{timeframe}' received. Defaulting to daily (86400s).")
        period_seconds = PERIOD_DAILY_SECONDS 
        
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

    # Limit to maximum 30 tokens for performance
    MAX_TOKENS_TO_SCREEN = 30
    tokens_to_screen = all_tokens_on_chain[:MAX_TOKENS_TO_SCREEN]
    
    if len(all_tokens_on_chain) > MAX_TOKENS_TO_SCREEN:
        logger.info(f"Limited token screening to {MAX_TOKENS_TO_SCREEN} tokens out of {len(all_tokens_on_chain)} available tokens for {chain_name}")
    
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
            quote_symbol = f"{quote_candidate['name']}_on_{chain_name}"
            quote_name = quote_candidate["name"]

            current_result["quote_token_address"] = quote_address # Tentatively set
            current_result["quote_token_symbol"] = quote_symbol  # Tentatively set

            base_addr_lower = base_token_address.lower()
            quote_addr_lower = quote_address.lower()

            if base_addr_lower == quote_addr_lower:
                logger.info(f"Skipping OHLCV for {base_token_symbol} against itself ({quote_name} on {chain_name}).")
                last_error_message_for_token = f"Self-pair with {quote_name}, OHLCV not applicable."
                current_result["error"] = last_error_message_for_token
                continue

            # --- NEW: Skip stablecoin vs stablecoin pairs ---
            # Check if base token is a known stablecoin by its symbol
            is_base_stable_by_symbol = token_info.get('symbol', '').upper() in COMMON_STABLECOIN_SYMBOLS
            
            # Quote candidates are USDC/USDT, which are stable.
            # We can also check the quote_address directly if we had a broader list of quote stables.
            is_quote_stable_by_address = quote_addr_lower in known_quote_stablecoin_addresses

            if is_base_stable_by_symbol and is_quote_stable_by_address:
                logger.info(f"Skipping OHLCV for stablecoin base ({base_token_symbol}) vs stablecoin quote ({quote_name}) on {chain_name}.")
                last_error_message_for_token = f"Stablecoin vs stablecoin pair ({base_token_symbol}/{quote_name}), OHLCV not fetched."
                current_result["error"] = last_error_message_for_token
                # If this error is set, and it's the last quote candidate, it will persist.
                continue # Try next quote candidate
            # --- END NEW ---

            pair_desc = f"{base_token_symbol}/{quote_symbol} on {chain_name}"
            logger.info(f"Processing OHLCV for {pair_desc} (using {quote_name}, attempt {attempt_idx + 1}/{len(potential_quotes)})...")

            cached_ohlcv = await get_ohlcv_from_db(
                chain_id, base_token_address, quote_address, period_seconds, timeframe
            )
            if cached_ohlcv is not None: # Not None means fresh data found (empty list is valid cached data)
                current_result["ohlcv_data"] = cached_ohlcv
                current_result["error"] = None
                current_result["data_source"] = "database"
                current_result["quote_token_address"] = quote_address # Confirm from DB query
                current_result["quote_token_symbol"] = quote_symbol
                logger.info(f"Successfully fetched {len(cached_ohlcv)} candles for {pair_desc} from database.")
                ohlcv_fetched_successfully = True
                break # Successfully got data from DB

            logger.info(f"Data for {pair_desc} not in DB or stale. Fetching from API (attempt {attempt_idx + 1}/{len(potential_quotes)})...")
            await asyncio.sleep(API_CALL_DELAY_SECONDS) # Use asyncio.sleep

            try:
                ohlcv_api_response = await one_inch_data_service.get_ohlcv_data(
                    base_token_address, quote_address, period_seconds, chain_id
                )
                if ohlcv_api_response and "data" in ohlcv_api_response:
                    api_candles = ohlcv_api_response["data"]
                    current_result["ohlcv_data"] = api_candles
                    current_result["error"] = None
                    current_result["data_source"] = "api"
                    current_result["quote_token_address"] = quote_address # Confirm from successful API call
                    current_result["quote_token_symbol"] = quote_symbol

                    logger.info(f"Successfully fetched {len(api_candles)} candles for {pair_desc} from API.")
                    ohlcv_fetched_successfully = True
                    
                    # --- NEW: Store in MongoDB ---
                    if api_candles: # Only store if data is not empty
                        await store_ohlcv_in_db(
                            chain_id, base_token_address, quote_address, 
                            period_seconds, timeframe, api_candles
                        )
                    else: # API returned success but empty data array
                        logger.warning(f"API returned success but 'data' array is empty for {pair_desc}. Not storing in DB.")
                    break 
                else:
                    logger.warning(f"OHLCV data for {pair_desc} (with {quote_name}) was fetched but 'data' array is empty or missing in API response.")
                    last_error_message_for_token = f"OHLCV data missing/empty from API (with {quote_name})."
                    current_result["error"] = last_error_message_for_token
            
            except one_inch_data_service.OneInchAPIError as e:
                logger.error(f"API Error fetching OHLCV for {pair_desc} (with {quote_name}): {e}")
                last_error_message_for_token = f"1inch API Error (with {quote_name}): {str(e)}"
                current_result["error"] = last_error_message_for_token
                if e.response_text and "charts not supported for chosen tokens" in e.response_text:
                    logger.warning(f"'Charts not supported' error for {pair_desc} with {quote_name}. Fallback (if any) will proceed.")

            except Exception as e:
                logger.error(f"Unexpected error fetching OHLCV for {pair_desc} (with {quote_name}): {e}", exc_info=True)
                last_error_message_for_token = f"Unexpected error (with {quote_name}): {str(e)}"
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

@app.post("/portfolio/optimize/{chain_id}", summary="Screen, Forecast, and Optimize Portfolio", response_model=Dict[str, Any])
async def get_optimized_portfolio_for_chain(
    chain_id: int,
    timeframe: str = Query("daily", enum=["hourly", "daily"], description="Timeframe for OHLCV data ('daily', 'hourly')."),
    num_top_assets: int = Query(10, ge=2, le=20, description="Number of top assets for MVO (2-20). Min 2 for MVO."),
    mvo_objective: str = Query("maximize_sharpe", enum=["maximize_sharpe", "minimize_volatility"], description="MVO objective function."),
    risk_free_rate: float = Query(0.02, description="Risk-free rate for Sharpe ratio calculation."),
    annualization_factor_override: Optional[int] = Query(None, ge=1, description="Optional: Override annualization factor for MVO (e.g., 365 for daily, 252 for trading days). Default is dynamic based on timeframe.")
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
        # Use the same timeout mechanism as the /screen_tokens endpoint
        screener_results = await asyncio.wait_for(
            _perform_token_screening(chain_id, timeframe),
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
            # Quote symbol from screener might be "USDC_on_Ethereum", so take the part before "_"
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


    # 3. Determine period_seconds and annualization_factor
    if timeframe.lower() == "hourly":
        period_seconds = PERIOD_HOURLY_SECONDS
        default_annual_factor = 365 * 24 
    elif timeframe.lower() == "daily":
        period_seconds = PERIOD_DAILY_SECONDS
        default_annual_factor = 365 
    else: # Should not happen due to Query enum, but as a fallback
        logger.warning(f"Invalid timeframe '{timeframe}' in optimize endpoint. Defaulting to daily period and annualization.")
        period_seconds = PERIOD_DAILY_SECONDS
        default_annual_factor = 252 # Common trading days
        
    annualization_factor = annualization_factor_override if annualization_factor_override is not None else default_annual_factor
    
    logger.info(f"Portfolio optimization pipeline: Using period_seconds={period_seconds}, annualization_factor={annualization_factor}.")

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
            annualization_factor=annualization_factor
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