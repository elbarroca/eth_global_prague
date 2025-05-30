# app/main.py
from fastapi import FastAPI, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
import logging
import time
import asyncio # New import
from pydantic import BaseModel, Field
from services.mongo_service import (
    connect_to_mongo,
    close_mongo_connection,
    get_ohlcv_from_db,
    store_ohlcv_in_db
)

from models import FusionQuoteRequest, FusionOrderBuildRequest, FusionOrderSubmitRequest
from services import one_inch_data_service # Fixed: changed from one_inch_service to one_inch_data_service
from services import one_inch_fusion_service # Import the fusion service
from configs import * # Changed from relative to absolute import

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
    description="API to fetch popular tokens and their OHLCV data from 1inch, with MongoDB caching.",
    version="0.1.0"
)

# --- NEW: FastAPI Startup and Shutdown Events for MongoDB and HTTP Client ---
@app.on_event("startup")
async def startup_app_clients(): # Renamed and made async
    try:
        await connect_to_mongo() # Await async connection
        logger.info("MongoDB connection established successfully on startup.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB on startup: {e}")
        # Depending on policy, you might want to prevent app startup if DB connection fails
    
    try:
        await one_inch_data_service.get_http_client() # Initialize the shared HTTP client
        logger.info("Global HTTPX client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize global HTTPX client: {e}")


@app.on_event("shutdown")
async def shutdown_app_clients(): # Renamed and made async
    await close_mongo_connection() # Await async close
    logger.info("MongoDB connection closed on shutdown.")
    
    await one_inch_data_service.close_http_client() # Close the shared HTTP client
    logger.info("Global HTTPX client closed.")
# --- END NEW EVENTS ---

# Constants for the screener endpoint
API_CALL_DELAY_SECONDS = 0.75 # Be respectful
SCREENING_TIMEOUT_SECONDS = 60 # 1 minute timeout for entire screening process

@app.get("/screen_tokens/{chain_id}", response_model=List[Dict[str, Any]])
async def screen_tokens_on_chain( # Made async
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
        all_tokens_on_chain = await one_inch_data_service.fetch_1inch_whitelisted_tokens(chain_id_filter=chain_id) # Await async call
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

            cached_ohlcv = await get_ohlcv_from_db( # Await async call
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
                ohlcv_api_response = await one_inch_data_service.get_ohlcv_data( # Await async call
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
                        await store_ohlcv_in_db( # Await async call
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
            
            # Delay before next quote attempt FOR THIS TOKEN (if previous failed and more attempts left)
            # This is already handled by the time.sleep(API_CALL_DELAY_SECONDS) at the start of this inner loop
            # if not ohlcv_fetched_successfully and attempt_idx < len(potential_quotes) - 1:
            #     logger.info(f"Attempt with {quote_name} for {base_token_symbol} failed. Delaying before trying next quote token for this base token.")
            #     time.sleep(API_CALL_DELAY_SECONDS) # This delay might be redundant now
        
        if not ohlcv_fetched_successfully:
             current_result["error"] = last_error_message_for_token 

        screener_results.append(current_result)
        # Delay between processing different BASE TOKENS (regardless of success/failure of previous token)
        # This delay is now managed before each API call attempt within the quote loop
        # time.sleep(API_CALL_DELAY_SECONDS) 
        # However, if all data for a base token came from DB, no API call was made, so no delay.
        # If a base token processing involved any API call, a delay occurred.
        # Consider if a small uniform delay is needed here if all quote attempts for a base token failed before any API call (e.g. all self-pairs)

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

@app.get("/")
async def root():
    return {"message": "Welcome to the 1inch Token Screener API. Use /docs for API documentation."}