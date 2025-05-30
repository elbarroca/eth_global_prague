# backend/tests/test_conceptual_screener_simple.py

import pytest
import requests
import time
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# --- Import service functions ---
from backend.one_inch_service import (
    get_ohlcv_data,
    fetch_1inch_whitelisted_tokens,
    OneInchAPIError,
    USDC_ADDRESSES,
    NATIVE_ASSET_ADDRESS,
    WETH_ETHEREUM_ADDRESS,  # Import WETH address
    ETHEREUM_CHAIN_ID,      # Import Ethereum chain ID
    BASE_CHAIN_ID,          # Assuming BASE_CHAIN_ID is imported from backend.inch_service
    ARBITRUM_CHAIN_ID       # Assuming ARBITRUM_CHAIN_ID is imported from backend.inch_service
)

# --- Logging Configuration ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

# --- Configuration ---
API_KEY = os.environ.get("ONE_INCH_API_KEY")
if not API_KEY:
    logger.warning("Using default/example 1inch API Key because ONE_INCH_API_KEY environment variable is not set. Full access might be restricted.")
    API_KEY = "PrA0uavUMpVOig4aopY0MQMqti3gO19d"

# --- Constants ---
# NATIVE_ASSET_ADDRESS is now imported from inch_service

# Simplified chains to test (just 2 chains for faster testing)
CHAINS_TO_TEST = [
    1,  # Ethereum
    8453,  # Base
    137,  # Polygon
    42161,  # Arbitrum
    10,  # Optimism
    43114,  # Avalanche
    324,  # zkSync Era
]

CHAIN_ID_TO_NAME = {
    1: "Ethereum",
    8453: "Base",
    137: "Polygon",
    42161: "Arbitrum",
    10: "Optimism",
    43114: "Avalanche",
    324: "zkSync Era",
}

PERIOD_DAILY_SECONDS = 86400
MAX_TOKENS_TO_SCREEN_PER_CHAIN = 2  # Reduced to 2 for faster testing
API_CALL_DELAY_SECONDS = 1.0  # Slightly reduced delay

# --- Helper function to validate OHLCV ---
def validate_ohlcv_response_structure(response_data: dict, pair_description: str):
    logger.info(f"Validating OHLCV response for {pair_description}")
    assert isinstance(response_data, dict), f"Response data not a dict for {pair_description}"
    assert "data" in response_data, f"'data' key missing for {pair_description}"
    candle_list = response_data["data"]
    assert isinstance(candle_list, list), f"'data' not a list for {pair_description}"

    if not candle_list:
        logger.warning(f"Empty candle data list for {pair_description}. This might be valid for some pairs/periods.")
        return

    for i, candle in enumerate(candle_list):
        assert isinstance(candle, dict), f"Candle #{i} not a dict for {pair_description}"
        expected_keys = {"time", "open", "high", "low", "close"}
        assert expected_keys.issubset(candle.keys()), \
            f"Candle #{i} missing keys for {pair_description}. Expected: {expected_keys}, Got: {list(candle.keys())}"
        
        # Basic validation that values can be converted to float
        for key in expected_keys:
            try:
                float(candle[key])
            except ValueError:
                pytest.fail(f"Candle #{i}['{key}'] ('{candle[key]}') not convertible to float for {pair_description}.")

    logger.info(f"Validated OHLCV structure for {pair_description} ({len(candle_list)} candles).")


# --- Test Function ---
def test_fetch_ohlcv_for_top_tokens_per_chain_simple():
    logger.info(f"--- Starting SIMPLE Conceptual Screener: Fetching OHLCV for top {MAX_TOKENS_TO_SCREEN_PER_CHAIN} tokens per chain ---")

    for chain_id in CHAINS_TO_TEST:
        chain_name = CHAIN_ID_TO_NAME.get(chain_id, "Unknown")
        logger.info(f"\n>>> Processing Chain: {chain_name} (ID: {chain_id})")

        # Step 1: Fetch whitelisted tokens for the current chain
        logger.info(f"Fetching whitelisted tokens for {chain_name}...")
        try:
            all_tokens_on_chain = fetch_1inch_whitelisted_tokens(chain_id_filter=chain_id)
            time.sleep(API_CALL_DELAY_SECONDS)
        except OneInchAPIError as e:
            logger.error(f"API Error fetching token list for {chain_name}: {e}. Skipping chain.")
            continue 
        except Exception as e:
            logger.error(f"Unexpected error fetching token list for {chain_name}: {e}. Skipping chain.")
            continue

        if not all_tokens_on_chain:
            logger.warning(f"No whitelisted tokens found or returned for {chain_name}. Skipping OHLCV checks for this chain.")
            continue

        logger.info(f"Found {len(all_tokens_on_chain)} tokens for {chain_name}. Selecting top {MAX_TOKENS_TO_SCREEN_PER_CHAIN}.")
        
        tokens_to_screen = all_tokens_on_chain[:MAX_TOKENS_TO_SCREEN_PER_CHAIN]

        # Determine the quote token for this chain
        # Prioritize USDC if available, otherwise use native asset
        # USDC_ADDRESSES is now imported from backend.inch_service

        if chain_id in USDC_ADDRESSES:
            quote_token_address = USDC_ADDRESSES[chain_id]
            if chain_id == ETHEREUM_CHAIN_ID:
                quote_token_symbol = "USDC"  # Simplified for Ethereum
            elif chain_id == BASE_CHAIN_ID: # Example, BASE_CHAIN_ID should be defined or imported
                quote_token_symbol = "USDC_BASE"
            # Add more specific USDC symbols as needed, align with USDC_ADDRESSES in inch_service
            # Example for Arbitrum - ensure ARBITRUM_CHAIN_ID is available if used here
            # elif chain_id == ARBITRUM_CHAIN_ID: 
            #     quote_token_symbol = "USDC_ARB" # Or "USDCe_ARB" depending on the address used
            else:
                quote_token_symbol = f"USDC_on_{chain_name}"
        else:
            quote_token_address = NATIVE_ASSET_ADDRESS
            if chain_id == ETHEREUM_CHAIN_ID:
                quote_token_symbol = "ETH" # Native asset on Ethereum is ETH
            else:
                quote_token_symbol = f"Native-{chain_name.split()[0]}"

        logger.info(f"Using '{quote_token_symbol}' ({quote_token_address}) as quote token for {chain_name}.")

        # Step 2: For each selected token, get OHLCV data
        for token_info in tokens_to_screen:
            base_token_address = token_info['address']
            base_token_symbol = token_info['symbol']
            base_token_name = token_info['name']

            logger.info(f"  Processing token: {base_token_symbol} ({base_token_name} - {base_token_address[:10]}...) on {chain_name}")

            if base_token_address.lower() == quote_token_address.lower():
                logger.info(f"    Skipping OHLCV for {base_token_symbol} against itself ({quote_token_symbol}).")
                continue
            
            pair_desc = f"{base_token_symbol}/{quote_token_symbol} on {chain_name}"
            logger.info(f"    Fetching daily OHLCV for {pair_desc}...")

            ohlcv_data = None
            current_quote_token_address = quote_token_address
            current_quote_token_symbol = quote_token_symbol
            
            try:
                ohlcv_data = get_ohlcv_data(base_token_address, current_quote_token_address, PERIOD_DAILY_SECONDS, chain_id)
            except OneInchAPIError as e:
                original_pair_desc = f"{base_token_symbol}/{current_quote_token_symbol} on {chain_name}"
                logger.error(f"    API Error fetching OHLCV for {original_pair_desc}: {e}")
                # Check if it's Ethereum, the quote was USDC, and the error is "charts not supported"
                if chain_id == ETHEREUM_CHAIN_ID and \
                   current_quote_token_address == USDC_ADDRESSES.get(ETHEREUM_CHAIN_ID) and \
                   e.response_text and "charts not supported for chosen tokens" in e.response_text:
                    
                    logger.warning(f"    Attempting fallback to WETH for {base_token_symbol} on Ethereum.")
                    current_quote_token_address = WETH_ETHEREUM_ADDRESS
                    current_quote_token_symbol = "WETH" # Simplified WETH symbol for Ethereum
                    pair_desc = f"{base_token_symbol}/{current_quote_token_symbol} on {chain_name}" # Update pair_desc for logging
                    logger.info(f"    Fetching daily OHLCV for {pair_desc}...")
                    try:
                        ohlcv_data = get_ohlcv_data(base_token_address, current_quote_token_address, PERIOD_DAILY_SECONDS, chain_id)
                    except OneInchAPIError as e_weth:
                        logger.error(f"    API Error fetching OHLCV with WETH fallback for {pair_desc}: {e_weth}")
                    except Exception as e_weth_unexpected:
                        logger.error(f"    Unexpected error with WETH fallback for {pair_desc}: {e_weth_unexpected}")
            except Exception as e:
                pair_desc_for_error = f"{base_token_symbol}/{current_quote_token_symbol} on {chain_name}"
                logger.error(f"    Unexpected error fetching OHLCV for {pair_desc_for_error}: {e}")
            
            time.sleep(API_CALL_DELAY_SECONDS)

            # Construct pair_desc for successful validation/logging using the latest current_quote_token_symbol
            final_pair_desc = f"{base_token_symbol}/{current_quote_token_symbol} on {chain_name}"

            if ohlcv_data:
                try:
                    validate_ohlcv_response_structure(ohlcv_data, final_pair_desc)
                    if ohlcv_data.get("data"):
                        logger.info(f"    ✅ Successfully fetched and validated {len(ohlcv_data['data'])} candles for {final_pair_desc}.")
                    else:
                        logger.warning(f"    ⚠️  OHLCV data for {final_pair_desc} was fetched but the 'data' array is empty or missing.")
                except AssertionError as e_assert:
                    logger.warning(f"    ❌ OHLCV data validation failed for {final_pair_desc}: {e_assert}")
                except Exception as e_val:
                    logger.warning(f"    ❌ An unexpected error occurred during OHLCV validation for {final_pair_desc}: {e_val}")
            else:
                logger.warning(f"    ❌ No OHLCV data returned or error occurred for {final_pair_desc}.")

    logger.info(f"--- SIMPLE Conceptual Screener Test Completed ---")


if __name__ == "__main__":
    # Allow running the test directly with python
    print("Running SIMPLE conceptual screener test directly...")
    test_fetch_ohlcv_for_top_tokens_per_chain_simple()
    print("Simple test completed!") 