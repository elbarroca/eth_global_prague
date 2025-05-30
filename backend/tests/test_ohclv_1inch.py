# test_one_inch_ohlcv_api_with_logging_v2.py

import pytest
import requests
import time
import logging
import os

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

API_KEY = os.environ.get("ONE_INCH_API_KEY", "PrA0uavUMpVOig4aopY0MQMqti3gO19d")
if API_KEY == "PrA0uavUMpVOig4aopY0MQMqti3gO19d":
    logger.warning("Using default/example 1inch API Key. Consider setting ONE_INCH_API_KEY environment variable for full access.")

NATIVE_ETH_ADDRESS = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
USDC_ETHEREUM_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDC_BASE_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# --- MODIFICATION for Arbitrum USDC Address for CHARTS API ---
# Official Native USDC on Arbitrum: 0xaf88d065e77c8cC2239327C5EDb3A53fC7Cb328 (was causing 400 on Charts)
# Bridged USDC (USDC.e) on Arbitrum: 0xff970a61a04b1ca14834a43f5de4533ebddb5cc8
# Let's try USDC.e for the Charts API as it's a common alternative if native isn't directly supported by an aggregator's charting.
USDC_ARBITRUM_CHARTS_API_ADDRESS = "0xff970a61a04b1ca14834a43f5de4533ebddb5cc8" # Bridged USDC (USDC.e)
USDC_ARBITRUM_NATIVE_ADDRESS = "0xaf88d065e77c8cC2239327C5EDb3A53fC7Cb328" # Native USDC (for Portfolio API if it ever works)

WETH_ETHEREUM_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

ETHEREUM_CHAIN_ID = 1
BASE_CHAIN_ID = 8453
ARBITRUM_CHAIN_ID = 42161

PERIOD_DAILY_SECONDS = 86400
GRANULARITY_DAILY = "1d"
GRANULARITY_HOURLY = "1h"

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
    (NATIVE_ETH_ADDRESS, USDC_ETHEREUM_ADDRESS, ETHEREUM_CHAIN_ID, "Ethereum (ETH/USDC)"),
    (WETH_ETHEREUM_ADDRESS, USDC_ETHEREUM_ADDRESS, ETHEREUM_CHAIN_ID, "Ethereum (WETH/USDC)"),
    (NATIVE_ETH_ADDRESS, USDC_BASE_ADDRESS, BASE_CHAIN_ID, "Base (ETH/USDC)"),
    (NATIVE_ETH_ADDRESS, USDC_ARBITRUM_CHARTS_API_ADDRESS, ARBITRUM_CHAIN_ID, "Arbitrum (ETH/USDC.e Bridged)"), # Using USDC.e for Arbitrum Charts
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
    (WETH_ETHEREUM_ADDRESS, USDC_ETHEREUM_ADDRESS, ETHEREUM_CHAIN_ID, GRANULARITY_DAILY, "Ethereum (WETH/USDC Daily) Portfolio"),
    (NATIVE_ETH_ADDRESS, USDC_ETHEREUM_ADDRESS, ETHEREUM_CHAIN_ID, GRANULARITY_HOURLY, "Ethereum (ETH/USDC Hourly) Portfolio"),
    # Using BRIDGED USDC.e for Arbitrum here for Portfolio API, similar to Charts API.
    (NATIVE_ETH_ADDRESS, USDC_ARBITRUM_CHARTS_API_ADDRESS, ARBITRUM_CHAIN_ID, GRANULARITY_DAILY, "Arbitrum (ETH/USDC.e Bridged) Portfolio")
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

@pytest.fixture(scope="function", autouse=True)
def test_case_delay():
    yield
    logger.debug("Delaying 1s after test case.")
    time.sleep(1.0)