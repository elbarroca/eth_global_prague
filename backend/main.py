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
# Fix import error by importing directly from service files
from services.one_inch_fusion_service import get_fusion_plus_quote_backend, prepare_fusion_plus_order_for_signing_backend, submit_signed_fusion_plus_order_backend, check_order_status, OneInchAPIError
# If you have a one_inch_service.py file, import directly from it too
# from services.one_inch_service import fetch_1inch_whitelisted_tokens, get_ohlcv_data
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
    # Note: This endpoint may need to be updated if you don't have one_inch_service
    # For now keeping it as a placeholder
    return []

# Fusion+ API endpoints
@app.post("/fusion/quote", response_model=Dict[str, Any])
async def get_fusion_quote(request: FusionQuoteRequest):
    """
    Get a cross-chain swap quote using 1inch Fusion+
    """
    logger.info(f"Getting Fusion+ quote for {request.src_token_address} on chain {request.src_chain_id} to {request.dst_token_address} on chain {request.dst_chain_id}")
    
    try:
        quote = get_fusion_plus_quote_backend(
            src_chain_id=request.src_chain_id,
            dst_chain_id=request.dst_chain_id,
            src_token_address=request.src_token_address,
            dst_token_address=request.dst_token_address,
            amount_wei=request.amount_wei,
            wallet_address=request.wallet_address,
            enable_estimate=request.enable_estimate
        )
        return quote
    except OneInchAPIError as e:
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
        order_data = prepare_fusion_plus_order_for_signing_backend(
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
    except OneInchAPIError as e:
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
        submission_result = submit_signed_fusion_plus_order_backend(
            src_chain_id=request.src_chain_id,
            signed_order_payload=request.signed_order_payload
        )
        return submission_result
    except OneInchAPIError as e:
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
        status = check_order_status(order_hash)
        return status
    except OneInchAPIError as e:
        logger.error(f"API Error checking order status: {e}")
        raise HTTPException(status_code=e.status_code or 503, detail=f"Failed to check order status: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error checking order status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Welcome to the 1inch Fusion+ API. Use /docs for API documentation."}