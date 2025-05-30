# app/main.py
from fastapi import FastAPI, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
import logging
import time
from pydantic import BaseModel, Field

from models import FusionQuoteRequest, FusionOrderBuildRequest, FusionOrderSubmitRequest
from services import one_inch_service # Changed from relative to absolute import
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
DEFAULT_MAX_TOKENS_TO_SCREEN = 5
DEFAULT_PERIOD_SECONDS = PERIOD_DAILY_SECONDS # Daily
API_CALL_DELAY_SECONDS = 0.75 # Be respectful

@app.get("/screen_tokens/{chain_id}", response_model=List[Dict[str, Any]])
async def screen_tokens_on_chain(
    chain_id: int,
    max_tokens: int = Query(DEFAULT_MAX_TOKENS_TO_SCREEN, ge=1, le=20, description="Maximum number of popular tokens to screen."),
    period_seconds: int = Query(DEFAULT_PERIOD_SECONDS, description="OHLCV period in seconds (e.g., 86400 for daily, 3600 for hourly)."),
    quote_token_type: str = Query("usdc", enum=["usdc", "native", "weth_on_eth"], description="Type of quote token to use (usdc, native, or weth_on_eth for Ethereum).")
):
    """
    Screens tokens on a given chain:
    1. Fetches a list of whitelisted (popular) tokens.
    2. For the top `max_tokens`, fetches their OHLCV data against a specified quote token.
    """
    chain_name = CHAIN_ID_TO_NAME.get(chain_id, "Unknown Chain")
    logger.info(f"Starting token screening for chain: {chain_name} (ID: {chain_id}) with max_tokens={max_tokens}, period={period_seconds}s, quote_type='{quote_token_type}'")

    if not one_inch_service.API_KEY or one_inch_service.API_KEY == "PrA0uavUMpVOig4aopY0MQMqti3gO19d":
         logger.warning("API Key is not properly set or is using the default placeholder. Results may be limited or fail.")
         # Depending on policy, you might want to raise an HTTPException here if API key is mandatory

    # Step 1: Fetch whitelisted tokens
    try:
        all_tokens_on_chain = one_inch_service.fetch_1inch_whitelisted_tokens(chain_id_filter=chain_id)
        time.sleep(API_CALL_DELAY_SECONDS) # Delay after fetching token list
    except one_inch_service.OneInchAPIError as e:
        logger.error(f"API Error fetching token list for {chain_name}: {e}")
        raise HTTPException(status_code=e.status_code or 503, detail=f"Failed to fetch token list from 1inch: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching token list for {chain_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching the token list.")

    if not all_tokens_on_chain:
        logger.warning(f"No whitelisted tokens found for {chain_name}.")
        return []

    tokens_to_screen = all_tokens_on_chain[:max_tokens]
    logger.info(f"Selected {len(tokens_to_screen)} tokens for {chain_name}: {[t['symbol'] for t in tokens_to_screen]}")

    # Step 2: Determine the quote token
    quote_token_address = None
    quote_token_symbol = ""

    if quote_token_type == "usdc":
        quote_token_address = USDC_ADDRESSES.get(chain_id)
        if quote_token_address:
            quote_token_symbol = f"USDC_on_{chain_name}"
        else:
            logger.warning(f"USDC address not configured for chain {chain_name}. Falling back to native asset.")
            quote_token_type = "native" # Fallback
    
    if quote_token_type == "native":
        quote_token_address = NATIVE_ASSET_ADDRESS
        quote_token_symbol = f"Native_{chain_name.split()[0]}"

    elif quote_token_type == "weth_on_eth" and chain_id == ETHEREUM_CHAIN_ID:
        quote_token_address = WETH_ETHEREUM_ADDRESS
        quote_token_symbol = "WETH_on_Ethereum"
    
    if not quote_token_address: # If still no quote token (e.g. weth_on_eth on non-ETH chain)
        logger.error(f"Could not determine a valid quote token for type '{quote_token_type}' on chain {chain_name}. Defaulting to native.")
        quote_token_address = NATIVE_ASSET_ADDRESS
        quote_token_symbol = f"Native_{chain_name.split()[0]}"


    logger.info(f"Using '{quote_token_symbol}' ({quote_token_address}) as quote token for {chain_name}.")

    # Step 3: Fetch OHLCV for each selected token
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
            "quote_token_address": quote_token_address,
            "quote_token_symbol": quote_token_symbol,
            "period_seconds": period_seconds,
            "ohlcv_data": None,
            "error": None
        }

        if base_token_address.lower() == quote_token_address.lower():
            logger.info(f"Skipping OHLCV for {base_token_symbol} against itself.")
            current_result["error"] = "Self-pair, OHLCV not applicable."
            screener_results.append(current_result)
            continue

        pair_desc = f"{base_token_symbol}/{quote_token_symbol} on {chain_name}"
        logger.info(f"Fetching OHLCV for {pair_desc}...")

        try:
            ohlcv_api_response = one_inch_service.get_ohlcv_data(
                base_token_address, quote_token_address, period_seconds, chain_id
            )
            if ohlcv_api_response and "data" in ohlcv_api_response:
                current_result["ohlcv_data"] = ohlcv_api_response["data"]
                logger.info(f"Successfully fetched {len(ohlcv_api_response['data'])} candles for {pair_desc}.")
            else:
                logger.warning(f"OHLCV data for {pair_desc} was fetched but 'data' array is empty or missing.")
                current_result["error"] = "OHLCV data missing or empty in API response."
        
        except one_inch_service.OneInchAPIError as e:
            logger.error(f"API Error fetching OHLCV for {pair_desc}: {e}")
            current_result["error"] = f"1inch API Error: {str(e)}"
            # Specific fallback for "charts not supported" on Ethereum when quote is USDC
            if chain_id == ETHEREUM_CHAIN_ID and \
               quote_token_address == USDC_ADDRESSES.get(ETHEREUM_CHAIN_ID) and \
               e.response_text and "charts not supported for chosen tokens" in e.response_text:
                
                logger.warning(f"Attempting fallback to WETH for {base_token_symbol} on Ethereum.")
                fallback_quote_address = WETH_ETHEREUM_ADDRESS
                fallback_quote_symbol = "WETH_on_Ethereum"
                current_result["quote_token_address"] = fallback_quote_address # Update result to show actual quote used
                current_result["quote_token_symbol"] = fallback_quote_symbol

                pair_desc_fallback = f"{base_token_symbol}/{fallback_quote_symbol} on {chain_name}"
                logger.info(f"Fetching OHLCV for {pair_desc_fallback} (fallback)...")
                try:
                    time.sleep(API_CALL_DELAY_SECONDS) # Delay before fallback
                    ohlcv_fallback_response = one_inch_service.get_ohlcv_data(
                        base_token_address, fallback_quote_address, period_seconds, chain_id
                    )
                    if ohlcv_fallback_response and "data" in ohlcv_fallback_response:
                        current_result["ohlcv_data"] = ohlcv_fallback_response["data"]
                        current_result["error"] = None # Clear previous error
                        logger.info(f"Successfully fetched {len(ohlcv_fallback_response['data'])} candles for {pair_desc_fallback} (fallback).")
                    else:
                        current_result["error"] = f"Fallback to {fallback_quote_symbol} failed or returned empty data."
                except one_inch_service.OneInchAPIError as e_fallback:
                    logger.error(f"API Error on WETH fallback for {pair_desc_fallback}: {e_fallback}")
                    current_result["error"] = f"1inch API Error on WETH fallback: {str(e_fallback)}"

        except Exception as e:
            logger.error(f"Unexpected error fetching OHLCV for {pair_desc}: {e}", exc_info=True)
            current_result["error"] = f"Unexpected error: {str(e)}"
        
        screener_results.append(current_result)
        time.sleep(API_CALL_DELAY_SECONDS) # Delay between OHLCV calls for different tokens

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