# test_one_inch_ohlcv_api_with_logging_v2.py

import pytest
import requests
import time
import logging
import os
import sys # Added for path manipulation
from pathlib import Path # Added for path manipulation

# Add the parent directory to the Python path so we can import backend modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# --- Import service functions ---
from backend.services.one_inch_service import (
    get_ohlcv_data, 
    get_cross_prices_data,
    fetch_1inch_whitelisted_tokens,
    OneInchAPIError,
    NATIVE_ASSET_ADDRESS,  # Import NATIVE_ASSET_ADDRESS
    USDC_ADDRESSES,      # Import USDC_ADDRESSES
    USDC_ETHEREUM_ADDRESS, # Keep for direct use if needed, or remove if covered by USDC_ADDRESSES
    USDC_BASE_ADDRESS,     # Keep for direct use if needed, or remove if covered by USDC_ADDRESSES
    USDC_ARBITRUM_CHARTS_API_ADDRESS, # Keep for direct use if needed
    WETH_ETHEREUM_ADDRESS, # Keep for direct use
    ETHEREUM_CHAIN_ID,     # Keep for direct use
    BASE_CHAIN_ID,         # Keep for direct use
    ARBITRUM_CHAIN_ID,     # Keep for direct use
    PERIOD_DAILY_SECONDS,  # Keep for direct use
    GRANULARITY_DAILY,     # Keep for direct use
    GRANULARITY_HOURLY     # Keep for direct use
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
CHARTS_API_BASE_URL = "https://api.1inch.dev/charts/v1.0/chart/aggregated/candle"
PORTFOLIO_API_DOMAIN = "https://api.1inch.dev/portfolio"
CROSS_PRICES_ENDPOINT_PATH = "/integrations/prices/v2/time_range/cross_prices"
PORTFOLIO_CROSS_PRICES_API_URL = f"{PORTFOLIO_API_DOMAIN}{CROSS_PRICES_ENDPOINT_PATH}"

API_KEY = os.getenv("ONE_INCH_API_KEY", "PrA0uavUMpVOig4aopY0MQMqti3gO19d")
if API_KEY == "PrA0uavUMpVOig4aopY0MQMqti3gO19d":
    logger.warning("Using default/example 1inch API Key. Consider setting ONE_INCH_API_KEY environment variable for full access.")

# NATIVE_ETH_ADDRESS is now NATIVE_ASSET_ADDRESS from inch_service
# USDC_ETHEREUM_ADDRESS, USDC_BASE_ADDRESS are available from inch_service via USDC_ADDRESSES or direct import
# USDC_ARBITRUM_CHARTS_API_ADDRESS is available from inch_service via USDC_ADDRESSES or direct import
# WETH_ETHEREUM_ADDRESS is available from inch_service or defined locally if specific
# Chain IDs and periods are available from inch_service or defined locally

# --- Mappings for Portfolio API v2 parameters ---
GRANULARITY_MAP_PORTFOLIO_V2 = {
    "1d": "day",
    "1h": "hour"
}

def _make_1inch_api_request(url: str, params: dict = None, api_description: str = "1inch API"):
    logger.info(f"Attempting to fetch data from {api_description} URL: {url} with params: {params}")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        logger.debug(f"Request URL: {response.url}")
        logger.debug(f"Request headers: {headers}")
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response raw text (first 500 chars): {response.text[:500]}")
        response.raise_for_status()
        json_response = response.json()
        logger.info(f"Successfully fetched data from {api_description} for URL: {url}.")
        return json_response
    except requests.exceptions.Timeout:
        logger.error(f"API request timed out for {api_description} URL: {url}")
        pytest.fail(f"API request timed out for {api_description} URL: {url}")
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error for {api_description}: {http_err} - Status: {response.status_code} - Text: {response.text}")
        pytest.fail(f"HTTP error for {api_description}: {http_err} - Response: {response.text}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"API request failed for {api_description}: {req_err}")
        pytest.fail(f"API request failed for {api_description}: {req_err}")
    except ValueError as json_err:
        response_text_snippet = response.text if 'response' in locals() else 'No response object'
        status_code_snippet = response.status_code if 'response' in locals() else 'N/A'
        logger.error(f"JSON decode error from {api_description}: {json_err}. Status: {status_code_snippet}. Text: {response_text_snippet[:500]}")
        pytest.fail(f"JSON decode error from {api_description}: {json_err}. Text: {response_text_snippet[:500]}")
    return None

def fetch_1inch_ohlcv_data(token0_address: str, token1_address: str, seconds: int, chain_id: int):
    url = f"{CHARTS_API_BASE_URL}/{token0_address}/{token1_address}/{seconds}/{chain_id}"
    return _make_1inch_api_request(url, api_description=f"1inch Charts API (OHLCV {token0_address[:6]}/{token1_address[:6]} on chain {chain_id})")

def validate_ohlcv_response_structure(response_data: dict, pair_description: str):
    logger.info(f"Validating OHLCV response for {pair_description}")
    assert isinstance(response_data, dict), f"Response data not a dict for {pair_description}"
    assert "data" in response_data, f"'data' key missing for {pair_description}"
    candle_list = response_data["data"]
    assert isinstance(candle_list, list), f"'data' not a list for {pair_description}"
    if not candle_list:
        logger.warning(f"Empty candle data list for {pair_description}.")
        return
    for i, candle in enumerate(candle_list):
        assert isinstance(candle, dict), f"Candle #{i} not a dict for {pair_description}"
        expected_keys = {"time", "open", "high", "low", "close"}
        assert expected_keys.issubset(candle.keys()), f"Candle #{i} missing keys for {pair_description}. Expected: {expected_keys}, Got: {list(candle.keys())}"
        for key in expected_keys:
            assert isinstance(candle[key], (int, float, str)), f"Candle #{i}['{key}'] wrong type for {pair_description}"
            try:
                float(candle[key])
            except ValueError:
                pytest.fail(f"Candle #{i}['{key}'] ('{candle[key]}') not convertible to float for {pair_description}.")
        c_high, c_low, c_open, c_close, c_time = map(float, [candle["high"], candle["low"], candle["open"], candle["close"], candle["time"]])
        assert c_high >= c_low, f"Candle #{i} H<L for {pair_description}"
        assert c_high >= c_open, f"Candle #{i} H<O for {pair_description}"
        assert c_high >= c_close, f"Candle #{i} H<C for {pair_description}"
        assert c_low <= c_open, f"Candle #{i} L>O for {pair_description}"
        assert c_low <= c_close, f"Candle #{i} L>C for {pair_description}"
        assert c_time > 1_000_000_000, f"Candle #{i} time too small for {pair_description}"
    logger.info(f"Validated OHLCV structure for {pair_description} ({len(candle_list)} candles).")

def fetch_1inch_cross_prices_data(chain_id: int, token_address: str, vs_token_address: str, time_from: int, time_to: int, granularity: str):
    # Map to new Portfolio API v2 parameter names and granularity values
    params = {
        "chain_id": chain_id, # Was chainId
        "token0_address": token_address, # Was tokenAddress
        "token1_address": vs_token_address, # Was vsTokenAddress
        "from_timestamp": time_from, # Was timeFrom
        "to_timestamp": time_to, # Was timeTo
        "granularity": GRANULARITY_MAP_PORTFOLIO_V2.get(granularity, granularity) # Map to 'day' or 'hour'
    }
    # This URL is now hitting the server but getting 422 due to parameter issues.
    logger.info(f"Attempting to use Portfolio API endpoint {PORTFOLIO_CROSS_PRICES_API_URL} with new v2 params: {params}")
    return _make_1inch_api_request(PORTFOLIO_CROSS_PRICES_API_URL, params=params, api_description=f"1inch Portfolio API (Cross Prices {token_address[:6]}/{vs_token_address[:6]} on chain {chain_id})")

def validate_cross_prices_response_structure(response_data: list, request_description: str):
    """
    Validates the structure of the Cross Prices API (Portfolio v2) response.
    The API v2 returns a list of dictionaries: [{'time': ..., 'open': ..., 'high':..., 'low':..., 'close':..., 'avg':...}, ...]
    """
    logger.info(f"Validating Cross Prices response for {request_description} (new Portfolio v2 structure)")
    
    assert isinstance(response_data, list), f"Expected response data to be a list for {request_description}, got {type(response_data)}"
    logger.debug(f"Response data is a list with {len(response_data)} items for {request_description}.")

    if not response_data:
        logger.warning(f"Received empty price data list for {request_description}. This might be okay for some periods but can be unexpected.")
        return # Allow empty list but log a warning

    for i, price_point_dict in enumerate(response_data):
        logger.debug(f"Validating price point dictionary #{i} for {request_description}")
        assert isinstance(price_point_dict, dict), f"Expected price point #{i} to be a dict for {request_description}, got {type(price_point_dict)}"
        
        # Keys for the Portfolio v2 'prices' endpoint seem to be like OHLCV
        expected_keys = {"timestamp", "open", "high", "low", "close", "avg"}
        assert expected_keys.issubset(price_point_dict.keys()), \
            f"Price point dict #{i} for {request_description} missing one or more keys. Expected subset: {expected_keys}, Got: {list(price_point_dict.keys())}"

        for key in expected_keys:
            assert isinstance(price_point_dict[key], (int, float, str)), \
                f"Price point dict #{i}['{key}'] for {request_description} expected to be int, float, or string, got {type(price_point_dict[key])} with value {price_point_dict[key]}"
            try:
                numeric_value = float(price_point_dict[key])
            except ValueError:
                pytest.fail(f"Price point dict #{i}['{key}'] for {request_description} with value '{price_point_dict[key]}' could not be converted to float.")
            
            if key == "timestamp":
                 assert numeric_value > 1_000_000_000, f"Price point dict #{i} for {request_description}: Timestamp {numeric_value} seems too small."
            elif key in ["open", "high", "low", "close", "avg"]:
                 assert numeric_value >= 0, f"Price point dict #{i}['{key}'] for {request_description} expected to be non-negative, got {numeric_value}"
        
        # Basic sanity checks for OHLC values if present
        c_high = float(price_point_dict["high"])
        c_low = float(price_point_dict["low"])
        c_open = float(price_point_dict["open"])
        c_close = float(price_point_dict["close"])

        assert c_high >= c_low, f"Price point dict #{i} for {request_description}: High ({c_high}) must be >= Low ({c_low})"
        assert c_high >= c_open, f"Price point dict #{i} for {request_description}: High ({c_high}) must be >= Open ({c_open})"
        assert c_high >= c_close, f"Price point dict #{i} for {request_description}: High ({c_high}) must be >= Close ({c_close})"
        assert c_low <= c_open, f"Price point dict #{i} for {request_description}: Low ({c_low}) must be <= Open ({c_open})"
        assert c_low <= c_close, f"Price point dict #{i} for {request_description}: Low ({c_low}) must be <= Close ({c_close})"

    logger.info(f"Successfully validated Cross Prices response structure for {request_description} with {len(response_data)} price points (Portfolio v2 structure).")

@pytest.mark.parametrize("token0, token1, chain_id, network_name", [
    (NATIVE_ASSET_ADDRESS, USDC_ADDRESSES[ETHEREUM_CHAIN_ID], ETHEREUM_CHAIN_ID, "Ethereum (Native/USDC)"),
    (WETH_ETHEREUM_ADDRESS, USDC_ADDRESSES[ETHEREUM_CHAIN_ID], ETHEREUM_CHAIN_ID, "Ethereum (WETH/USDC)"),
    (NATIVE_ASSET_ADDRESS, USDC_ADDRESSES[BASE_CHAIN_ID], BASE_CHAIN_ID, "Base (Native/USDC)"),
    (NATIVE_ASSET_ADDRESS, USDC_ADDRESSES[ARBITRUM_CHAIN_ID], ARBITRUM_CHAIN_ID, "Arbitrum (Native/USDC.e Bridged)"),
])
def test_get_eth_usdc_ohlcv_on_multiple_networks(token0, token1, chain_id, network_name):
    logger.info(f"--- Starting Charts API test for {network_name} (Chain ID: {chain_id}) ---")
    pair_desc = f"{network_name} [{token0[:6]}/{token1[:6]}] OHLCV"
    ohlcv_data = fetch_1inch_ohlcv_data(token0, token1, PERIOD_DAILY_SECONDS, chain_id)
    assert ohlcv_data is not None, f"Fetch failed for {pair_desc}."
    validate_ohlcv_response_structure(ohlcv_data, pair_desc)
    logger.info(f"OHLCV data OK for {pair_desc}. Sample: {ohlcv_data['data'][0] if ohlcv_data.get('data') else 'No data'}")
    logger.info(f"--- Charts API Test for {network_name} PASSED ---")

@pytest.mark.parametrize("token_address, vs_token_address, chain_id, granularity, network_name", [
    (WETH_ETHEREUM_ADDRESS, USDC_ADDRESSES[ETHEREUM_CHAIN_ID], ETHEREUM_CHAIN_ID, GRANULARITY_DAILY, "Ethereum (WETH/USDC Daily) Portfolio"),
    (NATIVE_ASSET_ADDRESS, USDC_ADDRESSES[ETHEREUM_CHAIN_ID], ETHEREUM_CHAIN_ID, GRANULARITY_HOURLY, "Ethereum (Native/USDC Hourly) Portfolio"),
    (NATIVE_ASSET_ADDRESS, USDC_ADDRESSES[ARBITRUM_CHAIN_ID], ARBITRUM_CHAIN_ID, GRANULARITY_DAILY, "Arbitrum (Native/USDC.e Bridged) Portfolio")
])
def test_get_cross_prices_on_multiple_networks(token_address, vs_token_address, chain_id, granularity, network_name):
    logger.info(f"--- Starting Portfolio API test for {network_name} (Gran: {granularity}) ---")
    req_desc = f"{network_name} [{token_address[:6]}/{vs_token_address[:6]}] CrossPrices"
    time_to = int(time.time())
    time_from = time_to - (7*86400 if granularity == GRANULARITY_DAILY else 1*86400)
    cross_prices_data = fetch_1inch_cross_prices_data(chain_id, token_address, vs_token_address, time_from, time_to, granularity)
    assert cross_prices_data is not None, f"Fetch failed for {req_desc}."
    validate_cross_prices_response_structure(cross_prices_data, req_desc)
    logger.info(f"CrossPrices data OK for {req_desc}. Sample: {cross_prices_data[0] if cross_prices_data else 'No data'}")
    logger.info(f"--- Portfolio API Test for {network_name} PASSED (unexpected if xfail) ---")

# --- Token API Helper Functions (adapted from plan) ---
def validate_token_list_structure(token_list: list, chain_id_description: str):
    logger.info(f"Validating token list structure for {chain_id_description}")
    assert isinstance(token_list, list), f"Token list is not a list for {chain_id_description}"
    if not token_list:
        # It's possible a chain might have no whitelisted tokens, or the filter yields none.
        logger.warning(f"Received empty token list for {chain_id_description}. This might be valid.")
        return
    for i, token in enumerate(token_list):
        assert isinstance(token, dict), f"Token #{i} is not a dict for {chain_id_description}"
        # 'logoURI' is optional, 'chainId' is added during processing in the service.
        expected_keys = {'address', 'symbol', 'name', 'decimals', 'chainId', 'logoURI'}
        assert expected_keys.issubset(token.keys()), \
            f"Token #{i} for {chain_id_description} missing keys. Expected subset: {expected_keys}, Got: {list(token.keys())}"
        assert isinstance(token['address'], str) and token['address'].startswith('0x'), f"Token #{i} address invalid: {token['address']}"
        assert isinstance(token['symbol'], str) and len(token['symbol']) > 0, f"Token #{i} symbol invalid: {token['symbol']}"
        assert isinstance(token['name'], str), f"Token #{i} name invalid: {token['name']}"
        assert isinstance(token['decimals'], int), f"Token #{i} decimals invalid: {token['decimals']}"
        # chainId can be N/A if it could not be determined from a flat list without a filter
        assert isinstance(token['chainId'], (int, str)), f"Token #{i} chainId invalid: {token['chainId']}"
        if isinstance(token['chainId'], str):
            assert token['chainId'] == 'N/A', f"Token #{i} chainId string is not 'N/A': {token['chainId']}"
        assert isinstance(token['logoURI'], str), f"Token #{i} logoURI invalid: {token['logoURI']}"
    logger.info(f"Successfully validated token list structure for {chain_id_description} with {len(token_list)} tokens.")

# --- Test Cases for Token API ---
@pytest.mark.parametrize("chain_id, network_name", [
    (ETHEREUM_CHAIN_ID, "Ethereum"),
    (BASE_CHAIN_ID, "Base"),
    (ARBITRUM_CHAIN_ID, "Arbitrum"),
    (137, "Polygon"), # Example of another chain ID that might be in the list
])
def test_get_whitelisted_tokens_for_chain(chain_id, network_name):
    logger.info(f"--- Starting Token API test for {network_name} (Chain ID: {chain_id}) ---")
    try:
        token_list = fetch_1inch_whitelisted_tokens(chain_id_filter=chain_id)
    except OneInchAPIError as e:
        pytest.fail(f"Token API request failed for {network_name}: {e}")
        return

    assert token_list is not None, f"Failed to fetch token list for {network_name}, result is None."
    # We can't assert len(token_list) > 0 because a chain might legitimately have 0 whitelisted tokens or not be in the API response
    if not token_list:
        logger.warning(f"Received an empty token list for {network_name}. This may be expected if the chain has no whitelisted tokens or is not in the provider's list.")
    
    validate_token_list_structure(token_list, network_name)
    
    logger.info(f"Successfully fetched and validated token list for {network_name}. Found {len(token_list)} tokens.")
    if token_list:
        logger.info(f"Sample token for {network_name}: {token_list[0]}")
    logger.info(f"--- Token API Test for {network_name} (Chain ID: {chain_id}) PASSED ---")

# --- Screener Test (Conceptual) ---
@pytest.mark.skip(reason="Conceptual test, involves multiple API calls and may be slow/flaky. Run manually if needed.")
def test_run_screener_example_flow():
    TARGET_CHAIN_ID = ETHEREUM_CHAIN_ID 
    QUOTE_TOKEN_ADDRESS = USDC_ADDRESSES[ETHEREUM_CHAIN_ID]
    # Supported seconds for OHLCV: 300 ,900 ,3600 ,14400 ,86400 ,604800
    SCREENER_PERIODS_SECONDS = [PERIOD_DAILY_SECONDS, 14400] 
    MAX_TOKENS_TO_SCREEN = 2 # Reduced for test brevity

    logger.info(f"--- Starting Screener Example Flow for Chain ID {TARGET_CHAIN_ID} ---")

    # 1. Fetch a list of "popular" tokens (using whitelisted as proxy)
    logger.info(f"Fetching whitelisted tokens for chain {TARGET_CHAIN_ID}...")
    try:
        all_popular_tokens = fetch_1inch_whitelisted_tokens(chain_id_filter=TARGET_CHAIN_ID)
    except OneInchAPIError as e:
        pytest.fail(f"Failed to get popular tokens for screener due to API error: {e}")
        return
        
    assert all_popular_tokens is not None, "Token list fetch returned None."
    if not all_popular_tokens:
        logger.warning(f"No whitelisted tokens found for chain {TARGET_CHAIN_ID}. Screener test cannot proceed fully.")
        # Depending on strictness, you might want to pytest.skip or pass here.
        # For now, let it proceed to see if it handles empty list gracefully.

    tokens_to_screen = all_popular_tokens[:MAX_TOKENS_TO_SCREEN]
    if not tokens_to_screen:
        logger.info("No tokens selected to screen (either MAX_TOKENS_TO_SCREEN is 0 or no tokens were fetched).")
    else:
        logger.info(f"Selected {len(tokens_to_screen)} tokens to screen: {[t['symbol'] for t in tokens_to_screen]}")

    screener_results = {}

    # 2. For each token, get OHLCV data for specified periods
    for token_info in tokens_to_screen:
        token_address = token_info['address']
        token_symbol = token_info['symbol']
        logger.info(f"Processing token: {token_symbol} ({token_address})")
        screener_results[token_symbol] = {'address': token_address, 'name': token_info['name'], 'ohlcv_data': {}}

        for period_seconds in SCREENER_PERIODS_SECONDS:
            period_desc = f"{period_seconds // 3600}h" if period_seconds < PERIOD_DAILY_SECONDS else f"{period_seconds // PERIOD_DAILY_SECONDS}d"
            logger.info(f"  Fetching {period_desc} OHLCV against {QUOTE_TOKEN_ADDRESS[:6]}...")
            
            if token_address.lower() == QUOTE_TOKEN_ADDRESS.lower():
                logger.info(f"  Skipping OHLCV for {token_symbol} vs itself.")
                screener_results[token_symbol]['ohlcv_data'][period_seconds] = "Self-pair"
                continue
            
            ohlcv_data = None
            try:
                ohlcv_data = get_ohlcv_data(token_address, QUOTE_TOKEN_ADDRESS, period_seconds, TARGET_CHAIN_ID)
            except OneInchAPIError as e:
                logger.error(f"  API Error fetching OHLCV for {token_symbol} {period_desc}: {e}")
            except Exception as e:
                 logger.error(f"  Unexpected error fetching OHLCV for {token_symbol} {period_desc}: {e}")

            if ohlcv_data and 'data' in ohlcv_data and ohlcv_data['data']:
                try:
                    validate_ohlcv_response_structure(ohlcv_data, f"{token_symbol} {period_desc}")
                    screener_results[token_symbol]['ohlcv_data'][period_seconds] = ohlcv_data['data']
                    logger.info(f"  Successfully fetched {len(ohlcv_data['data'])} candles for {period_desc}.")
                except AssertionError as e:
                    logger.warning(f"  OHLCV data validation failed for {token_symbol} {period_desc}: {e}")
                    screener_results[token_symbol]['ohlcv_data'][period_seconds] = "Validation failed"
            else:
                logger.warning(f"  No OHLCV data or invalid response for {token_symbol} {period_desc}. Data: {str(ohlcv_data)[:100]}")
                screener_results[token_symbol]['ohlcv_data'][period_seconds] = "No data/Error"
            
            time.sleep(0.75) # API Rate Limiting

    logger.info("--- Screener Example Flow Completed ---")
    logger.info(f"Screener Results (summary):")
    if not screener_results:
        logger.info("No results to display as no tokens were processed.")

    for symbol, data in screener_results.items():
        logger.info(f"Token: {symbol} ({data['name']})")
        if 'ohlcv_data' in data:
            for period, ohlcv_result in data['ohlcv_data'].items():
                status = "Unknown"
                if isinstance(ohlcv_result, list) and ohlcv_result:
                    status = f"Data received ({len(ohlcv_result)} candles)"
                    logger.info(f"    Latest close for period {period}s: {ohlcv_result[-1]['close']}")
                elif isinstance(ohlcv_result, str):
                    status = ohlcv_result # e.g., "Self-pair", "Validation failed", "No data/Error"
                else:
                    status = "No data/Error or unexpected format"
                logger.info(f"  Period {period}s: {status}")
        else:
            logger.info("  No OHLCV data found in results.")

@pytest.fixture(scope="function", autouse=True)
def test_case_delay():
    yield
    logger.debug("Delaying 1s after test case.")
    time.sleep(1.0)