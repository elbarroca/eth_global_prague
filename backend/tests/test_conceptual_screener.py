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
from backend.services.one_inch_service import (
    get_ohlcv_data,
    fetch_1inch_whitelisted_tokens,
    OneInchAPIError,
    USDC_ADDRESSES,
    NATIVE_ASSET_ADDRESS,
    WETH_ETHEREUM_ADDRESS,  # Import WETH address
    USDT_ADDRESSES, # Import USDT addresses
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
API_KEY = os.getenv("ONE_INCH_API_KEY")
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

        # Determine the quote token for this chain: try USDC, then USDT, then Native, with specific WETH fallback on ETH
        
        quote_token_address = None
        quote_token_symbol = ""
        quote_token_type = "" # To track what we are using: "USDC", "USDT", "NATIVE", "WETH"

        # Attempt 1: USDC
        if chain_id in USDC_ADDRESSES:
            quote_token_address = USDC_ADDRESSES[chain_id]
            quote_token_symbol = f"USDC_on_{chain_name}"
            quote_token_type = "USDC"
            logger.info(f"Attempting primary quote: {quote_token_symbol} ({quote_token_address}) for {chain_name}")
        else:
            logger.info(f"USDC address not available for {chain_name}. Will try USDT or Native.")


        # Step 2: For each selected token, get OHLCV data
        for token_info in tokens_to_screen:
            base_token_address = token_info['address']
            base_token_symbol = token_info['symbol']
            base_token_name = token_info['name']

            logger.info(f"  Processing token: {base_token_symbol} ({base_token_name} - {base_token_address[:10]}...) on {chain_name}")

            # Initialize effective quote details for this token, might change with fallbacks
            effective_quote_address = quote_token_address
            effective_quote_symbol = quote_token_symbol
            effective_quote_type = quote_token_type
            
            # Fallback to Native if no USDC was initially set (e.g. USDC not configured for chain)
            if not effective_quote_address:
                logger.info(f"    No initial USDC quote for {chain_name}. Attempting USDT or Native for {base_token_symbol}.")
                # Try USDT first if not USDC
                if chain_id in USDT_ADDRESSES:
                    effective_quote_address = USDT_ADDRESSES[chain_id]
                    effective_quote_symbol = f"USDT_on_{chain_name}"
                    effective_quote_type = "USDT"
                    logger.info(f"    Using USDT as quote: {effective_quote_symbol} ({effective_quote_address}) for {base_token_symbol} on {chain_name}")
                else: # Fallback to Native if no USDT
                    effective_quote_address = NATIVE_ASSET_ADDRESS
                    effective_quote_symbol = f"Native_{chain_name.split()[0]}"
                    effective_quote_type = "NATIVE"
                    logger.info(f"    USDT not available. Using Native asset as quote: {effective_quote_symbol} ({effective_quote_address}) for {base_token_symbol} on {chain_name}")
            
            if not effective_quote_address: # Should not happen if native is always a fallback
                logger.error(f"    CRITICAL: Could not determine any quote token for {base_token_symbol} on {chain_name}. Skipping.")
                continue

            if base_token_address.lower() == effective_quote_address.lower():
                logger.info(f"    Skipping OHLCV for {base_token_symbol} against itself ({effective_quote_symbol}).")
                continue
            
            pair_desc = f"{base_token_symbol}/{effective_quote_symbol} on {chain_name}"
            logger.info(f"    Fetching daily OHLCV for {pair_desc}...")

            ohlcv_data = None
            
            try:
                # Initial attempt with the determined quote (USDC or Native or initial USDT)
                ohlcv_data = get_ohlcv_data(base_token_address, effective_quote_address, PERIOD_DAILY_SECONDS, chain_id)
            
            except OneInchAPIError as e:
                logger.error(f"    API Error fetching OHLCV for {pair_desc}: {e}")
                
                # Fallback logic:
                # If the first attempt was USDC and it failed with "charts not supported":
                if effective_quote_type == "USDC" and e.response_text and "charts not supported for chosen tokens" in e.response_text:
                    logger.warning(f"    USDC quote for {pair_desc} not supported. Attempting fallback to USDT.")
                    if chain_id in USDT_ADDRESSES:
                        effective_quote_address = USDT_ADDRESSES[chain_id]
                        effective_quote_symbol = f"USDT_on_{chain_name}"
                        effective_quote_type = "USDT"
                        pair_desc = f"{base_token_symbol}/{effective_quote_symbol} on {chain_name}" # Update pair_desc
                        logger.info(f"    Fetching daily OHLCV for {pair_desc} (USDT fallback)...")
                        try:
                            ohlcv_data = get_ohlcv_data(base_token_address, effective_quote_address, PERIOD_DAILY_SECONDS, chain_id)
                        except OneInchAPIError as e_usdt:
                            logger.error(f"    API Error on USDT fallback for {pair_desc}: {e_usdt}")
                            # If USDT also fails with "charts not supported" on Ethereum, try WETH
                            if chain_id == ETHEREUM_CHAIN_ID and e_usdt.response_text and "charts not supported for chosen tokens" in e_usdt.response_text:
                                logger.warning(f"    USDT quote also not supported for {pair_desc} on Ethereum. Attempting WETH fallback.")
                                effective_quote_address = WETH_ETHEREUM_ADDRESS
                                effective_quote_symbol = "WETH_on_Ethereum"
                                effective_quote_type = "WETH"
                                pair_desc = f"{base_token_symbol}/{effective_quote_symbol} on {chain_name}"
                                logger.info(f"    Fetching daily OHLCV for {pair_desc} (WETH fallback)...")
                                try:
                                    ohlcv_data = get_ohlcv_data(base_token_address, effective_quote_address, PERIOD_DAILY_SECONDS, chain_id)
                                except OneInchAPIError as e_weth:
                                    logger.error(f"    API Error on WETH fallback for {pair_desc}: {e_weth}")
                                except Exception as e_weth_unexpected:
                                    logger.error(f"    Unexpected error on WETH fallback for {pair_desc}: {e_weth_unexpected}")
                        except Exception as e_usdt_unexpected:
                             logger.error(f"    Unexpected error on USDT fallback for {pair_desc}: {e_usdt_unexpected}")
                    else:
                        logger.warning(f"    USDT not configured for {chain_name}. Cannot fallback from USDC to USDT.")
                        # If on Ethereum and original USDC failed, and no USDT, directly try WETH
                        if chain_id == ETHEREUM_CHAIN_ID: # No USDT, try WETH on ETH
                            logger.warning(f"    Attempting WETH fallback directly for {base_token_symbol} on Ethereum as USDC failed and USDT not available.")
                            effective_quote_address = WETH_ETHEREUM_ADDRESS
                            effective_quote_symbol = "WETH_on_Ethereum"
                            effective_quote_type = "WETH"
                            pair_desc = f"{base_token_symbol}/{effective_quote_symbol} on {chain_name}"
                            logger.info(f"    Fetching daily OHLCV for {pair_desc} (WETH fallback)...")
                            try:
                                ohlcv_data = get_ohlcv_data(base_token_address, effective_quote_address, PERIOD_DAILY_SECONDS, chain_id)
                            except OneInchAPIError as e_weth:
                                logger.error(f"    API Error on WETH fallback for {pair_desc}: {e_weth}")
                            except Exception as e_weth_unexpected:
                                logger.error(f"    Unexpected error on WETH fallback for {pair_desc}: {e_weth_unexpected}")
                
                # If the first attempt was NOT USDC, or the error was different, or not on ETH for WETH fallback:
                # No further automatic fallbacks in this branch beyond initial Native if USDC/USDT addresses weren't present.
                # The ohlcv_data will remain None or hold the error from the primary attempt.

            except Exception as e_unexpected:
                logger.error(f"    Unexpected error fetching OHLCV for {pair_desc}: {e_unexpected}")
            
            time.sleep(API_CALL_DELAY_SECONDS)

            # Construct pair_desc for successful validation/logging using the latest effective_quote_symbol
            final_pair_desc = f"{base_token_symbol}/{effective_quote_symbol} on {chain_name}"

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