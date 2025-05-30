import requests
import logging
import os
import time

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

API_KEY = os.environ.get("ONE_INCH_API_KEY")
if not API_KEY:
    logger.error("ONE_INCH_API_KEY environment variable is not set. Please set it in your environment.")
    exit(1)

# --- Constants (can be expanded or moved to a config file/class) ---
NATIVE_ETH_ADDRESS = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
USDC_ETHEREUM_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDC_BASE_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_ARBITRUM_CHARTS_API_ADDRESS = "0xff970a61a04b1ca14834a43f5de4533ebddb5cc8" # Bridged USDC (USDC.e)
WETH_ETHEREUM_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

ETHEREUM_CHAIN_ID = 1
BASE_CHAIN_ID = 8453
ARBITRUM_CHAIN_ID = 42161

PERIOD_DAILY_SECONDS = 86400
GRANULARITY_DAILY = "1d"
GRANULARITY_HOURLY = "1h"

# Mapping for Portfolio API v2 granularity parameter
GRANULARITY_MAP_PORTFOLIO_V2 = {
    "1d": "day",
    "1h": "hour"
}

class OneInchAPIError(Exception):
    """Custom exception for 1inch API errors."""
    def __init__(self, message, status_code=None, response_text=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text

    def __str__(self):
        return f"{super().__str__()} (Status: {self.status_code}, Response: {self.response_text[:500] if self.response_text else 'N/A'})"


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
        
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        
        json_response = response.json()
        logger.info(f"Successfully fetched data from {api_description} for URL: {url}.")
        return json_response
        
    except requests.exceptions.Timeout as e:
        logger.error(f"API request timed out for {api_description} URL: {url}")
        raise OneInchAPIError(f"API request timed out for {api_description} URL: {url}", response_text=str(e)) from e
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error for {api_description}: {e} - Status: {e.response.status_code} - Text: {e.response.text}")
        raise OneInchAPIError(
            f"HTTP error for {api_description}",
            status_code=e.response.status_code,
            response_text=e.response.text
        ) from e
    except requests.exceptions.RequestException as e: # Catch other request-related errors (e.g., connection error)
        logger.error(f"API request failed for {api_description}: {e}")
        raise OneInchAPIError(f"API request failed for {api_description}", response_text=str(e)) from e
    except ValueError as e: # JSONDecodeError inherits from ValueError
        response_text_snippet = response.text if 'response' in locals() else 'No response object available'
        status_code_snippet = response.status_code if 'response' in locals() else 'N/A'
        logger.error(f"JSON decode error from {api_description}: {e}. Status: {status_code_snippet}. Text: {response_text_snippet[:500]}")
        raise OneInchAPIError(
            f"JSON decode error from {api_description}",
            status_code=status_code_snippet,
            response_text=response_text_snippet
        ) from e

def get_ohlcv_data(token0_address: str, token1_address: str, interval_seconds: int, chain_id: int):
    """
    Fetches OHLCV (candlestick) data from the 1inch Charts API.

    Args:
        token0_address: The address of the first token in the pair.
        token1_address: The address of the second token in the pair.
        interval_seconds: The time interval for candles in seconds (e.g., 86400 for daily).
        chain_id: The chain ID (e.g., 1 for Ethereum).

    Returns:
        A dictionary containing the OHLCV data.
        Example: {'data': [{'time': ..., 'open': ..., 'high': ..., 'low': ..., 'close': ...}, ...]}

    Raises:
        OneInchAPIError: If the API request fails or returns an error.
    """
    url = f"{CHARTS_API_BASE_URL}/{token0_address}/{token1_address}/{interval_seconds}/{chain_id}"
    return _make_1inch_api_request(url, api_description=f"1inch Charts API (OHLCV {token0_address[:6]}/{token1_address[:6]} on chain {chain_id})")

def get_cross_prices_data(chain_id: int, token0_address: str, token1_address: str, from_timestamp: int, to_timestamp: int, granularity_key: str):
    """
    Fetches historical cross-price data from the 1inch Portfolio API v2.

    Args:
        chain_id: The chain ID.
        token0_address: The address of the base token.
        token1_address: The address of the quote token.
        from_timestamp: The start of the time range (Unix timestamp).
        to_timestamp: The end of the time range (Unix timestamp).
        granularity_key: The granularity of the data ('1d' for daily, '1h' for hourly). 
                         Will be mapped to 'day' or 'hour' for the API.

    Returns:
        A list of dictionaries, where each dictionary represents a price point.
        Example: [{'timestamp': ..., 'open': ..., 'high': ..., 'low': ..., 'close': ..., 'avg': ...}, ...]

    Raises:
        OneInchAPIError: If the API request fails or returns an error.
    """
    granularity_api_value = GRANULARITY_MAP_PORTFOLIO_V2.get(granularity_key)
    if not granularity_api_value:
        logger.error(f"Invalid granularity_key: '{granularity_key}'. Supported keys: {list(GRANULARITY_MAP_PORTFOLIO_V2.keys())}")
        raise ValueError(f"Invalid granularity_key: '{granularity_key}'. Supported keys: {list(GRANULARITY_MAP_PORTFOLIO_V2.keys())}")

    params = {
        "chain_id": chain_id,
        "token0_address": token0_address,
        "token1_address": token1_address,
        "from_timestamp": from_timestamp,
        "to_timestamp": to_timestamp,
        "granularity": granularity_api_value
    }
    logger.info(f"Requesting Portfolio API v2 with params: {params}")
    return _make_1inch_api_request(PORTFOLIO_CROSS_PRICES_API_URL, params=params, api_description=f"1inch Portfolio API v2 (Cross Prices {token0_address[:6]}/{token1_address[:6]} on chain {chain_id})")
