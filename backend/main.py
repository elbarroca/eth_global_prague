# app/main.py
from fastapi import FastAPI, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
import logging
import time
from pydantic import BaseModel, Field

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
    description="API to fetch popular tokens and their OHLCV data from 1inch.",
    version="0.1.0"
)

# Constants for the screener endpoint
API_CALL_DELAY_SECONDS = 0.75 # Be respectful

@app.get("/screen_tokens/{chain_id}", response_model=List[Dict[str, Any]])
async def screen_tokens_on_chain(
    chain_id: int,
    timeframe: str = Query("daily", enum=["hourly", "daily"], description="Timeframe for OHLCV data ('daily', 'hourly').")
):
    """
    Screens tokens on a given chain:
    1. Fetches a list of whitelisted (popular) tokens.
    2. For all fetched tokens, attempts to fetch their OHLCV data against USDC, with a fallback to USDT.
    """
    chain_name = CHAIN_ID_TO_NAME.get(chain_id, "Unknown Chain")
    
    # Determine period_seconds from timeframe
    if timeframe.lower() == "hourly":
        period_seconds = PERIOD_HOURLY_SECONDS
    elif timeframe.lower() == "daily":
        period_seconds = PERIOD_DAILY_SECONDS
    else:
        # This case should ideally not be reached due to the enum in Query
        logger.warning(f"Invalid timeframe '{timeframe}' received. Defaulting to daily (86400s).")
        period_seconds = PERIOD_DAILY_SECONDS 
        
    logger.info(f"Starting token screening for chain: {chain_name} (ID: {chain_id}) with timeframe='{timeframe}' (period: {period_seconds}s)")

    if not one_inch_data_service.API_KEY or one_inch_data_service.API_KEY == "PrA0uavUMpVOig4aopY0MQMqti3gO19d":
         logger.warning("API Key is not properly set or is using the default placeholder. Results may be limited or fail.")
         # Depending on policy, you might want to raise an HTTPException here if API key is mandatory

    # Step 1: Fetch whitelisted tokens
    try:
        all_tokens_on_chain = one_inch_data_service.fetch_1inch_whitelisted_tokens(chain_id_filter=chain_id)
        time.sleep(API_CALL_DELAY_SECONDS) # Delay after fetching token list
    except one_inch_data_service.OneInchAPIError as e:
        logger.error(f"API Error fetching token list for {chain_name}: {e}")
        raise HTTPException(status_code=e.status_code or 503, detail=f"Failed to fetch token list from 1inch: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching token list for {chain_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching the token list.")

    if not all_tokens_on_chain:
        logger.warning(f"No whitelisted tokens found for {chain_name}.")
        return []

    tokens_to_screen = all_tokens_on_chain # Process all tokens
    logger.info(f"Attempting to screen {len(tokens_to_screen)} tokens for {chain_name}: {[t['symbol'] for t in tokens_to_screen]}")

    # Step 2: Define quote token strategy (USDC -> USDT)
    # These are potential quote tokens to try in order.
    # Assumes USDC_ADDRESSES and USDT_ADDRESSES are in configs.py
    potential_quotes = []
    usdc_address_on_chain = USDC_ADDRESSES.get(chain_id)
    if usdc_address_on_chain:
        potential_quotes.append({
            "address": usdc_address_on_chain,
            "symbol_template": f"USDC_on_{chain_name}", # Symbol will be confirmed if used
            "name": "USDC"
        })
    
    usdt_address_on_chain = USDT_ADDRESSES.get(chain_id) # Assumes USDT_ADDRESSES is in configs.py
    if usdt_address_on_chain:
        potential_quotes.append({
            "address": usdt_address_on_chain,
            "symbol_template": f"USDT_on_{chain_name}", # Symbol will be confirmed if used
            "name": "USDT"
        })

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
            "quote_token_address": None, # Will be set upon successful fetch
            "quote_token_symbol": None,  # Will be set upon successful fetch
            "period_seconds": period_seconds,
            "ohlcv_data": None,
            "error": "No suitable quote token (USDC/USDT) configured or all attempts failed." # Default error
        }

        if not potential_quotes:
            logger.warning(f"No USDC or USDT addresses configured for chain {chain_name}. Cannot fetch OHLCV for {base_token_symbol}.")
            current_result["error"] = f"No USDC or USDT addresses configured for chain {chain_name}."
            screener_results.append(current_result)
            time.sleep(API_CALL_DELAY_SECONDS) # Still delay before next token, though this one failed early
            continue

        ohlcv_fetched_successfully = False
        last_error_message_for_token = current_result["error"]

        for attempt_idx, quote_candidate in enumerate(potential_quotes):
            quote_address = quote_candidate["address"]
            # Construct a symbol like "USDC_on_Ethereum" or "USDT_on_Polygon"
            quote_symbol = f"{quote_candidate['name']}_on_{chain_name}" 
            quote_name = quote_candidate["name"]

            # Tentatively set quote info in result, might be overwritten by next attempt or confirmed on success
            current_result["quote_token_address"] = quote_address
            current_result["quote_token_symbol"] = quote_symbol

            if base_token_address.lower() == quote_address.lower():
                logger.info(f"Skipping OHLCV for {base_token_symbol} against itself ({quote_name} on {chain_name}).")
                last_error_message_for_token = f"Self-pair with {quote_name}, OHLCV not applicable."
                current_result["error"] = last_error_message_for_token
                # If this isn't the last quote option, the loop will try the next one.
                # If it IS the last, this error will persist for this token.
                continue # Try next quote token if available

            pair_desc = f"{base_token_symbol}/{quote_symbol} on {chain_name}"
            logger.info(f"Attempting OHLCV for {pair_desc} (using {quote_name}, attempt {attempt_idx + 1}/{len(potential_quotes)})...")

            try:
                ohlcv_api_response = one_inch_data_service.get_ohlcv_data(
                    base_token_address, quote_address, period_seconds, chain_id
                )
                if ohlcv_api_response and "data" in ohlcv_api_response:
                    current_result["ohlcv_data"] = ohlcv_api_response["data"]
                    current_result["error"] = None # Clear previous error
                    # Confirm the quote token that succeeded
                    current_result["quote_token_address"] = quote_address 
                    current_result["quote_token_symbol"] = quote_symbol
                    logger.info(f"Successfully fetched {len(ohlcv_api_response['data'])} candles for {pair_desc}.")
                    ohlcv_fetched_successfully = True
                    break # Successfully fetched OHLCV, no need to try other quote tokens for this base_token
                else:
                    logger.warning(f"OHLCV data for {pair_desc} (with {quote_name}) was fetched but 'data' array is empty or missing.")
                    last_error_message_for_token = f"OHLCV data missing/empty from API (with {quote_name})."
                    current_result["error"] = last_error_message_for_token
            
            except one_inch_data_service.OneInchAPIError as e:
                logger.error(f"API Error fetching OHLCV for {pair_desc} (with {quote_name}): {e}")
                last_error_message_for_token = f"1inch API Error (with {quote_name}): {str(e)}"
                current_result["error"] = last_error_message_for_token
                # Specific handling for "charts not supported" can be logged but general fallback handles it
                if e.response_text and "charts not supported for chosen tokens" in e.response_text:
                    logger.warning(f"'Charts not supported' error for {pair_desc} with {quote_name}. Fallback (if any) will proceed.")

            except Exception as e:
                logger.error(f"Unexpected error fetching OHLCV for {pair_desc} (with {quote_name}): {e}", exc_info=True)
                last_error_message_for_token = f"Unexpected error (with {quote_name}): {str(e)}"
                current_result["error"] = last_error_message_for_token
            
            if ohlcv_fetched_successfully: # Should be redundant because of break above
                break 
            
            # If an attempt failed and it's not the last potential quote, delay before next attempt for THIS token
            if not ohlcv_fetched_successfully and attempt_idx < len(potential_quotes) - 1:
                logger.info(f"Attempt with {quote_name} for {base_token_symbol} failed. Delaying before trying next quote token.")
                time.sleep(API_CALL_DELAY_SECONDS)
        
        # current_result["error"] will hold the error from the last failed attempt for this token,
        # or None if an attempt was successful.
        if not ohlcv_fetched_successfully:
             current_result["error"] = last_error_message_for_token # Ensure the most relevant error is set

        screener_results.append(current_result)
        # Delay between processing different base tokens (regardless of success/failure of previous token)
        time.sleep(API_CALL_DELAY_SECONDS) 

    logger.info(f"Screening completed for chain: {chain_name}. Returning {len(screener_results)} results.")
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