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

# --- Token API Configuration (New) ---
TOKEN_API_DOMAIN = "https://api.1inch.dev/token"
MULTI_CHAIN_TOKENS_ENDPOINT_V1_3 = "/v1.3/multi-chain"

API_KEY = os.environ.get("ONE_INCH_API_KEY")
if not API_KEY:
    logger.error("ONE_INCH_API_KEY environment variable is not set. Please set it in your environment.")

# --- Constants (can be expanded or moved to a config file/class) ---
NATIVE_ASSET_ADDRESS = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
USDC_ETHEREUM_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDC_BASE_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_ARBITRUM_CHARTS_API_ADDRESS = "0xff970a61a04b1ca14834a43f5de4533ebddb5cc8" # Bridged USDC (USDC.e)
USDC_POLYGON_ADDRESS = "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359"
USDC_OPTIMISM_ADDRESS = "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85"
USDC_AVALANCHE_ADDRESS = "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
USDC_ZKSYNC_ADDRESS = "0x1d17CBcF0D6D143135aE902365D2E5e2A16538D4"
USDC_ARBITRUM_NATIVE_ADDRESS = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"

WETH_ETHEREUM_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

ETHEREUM_CHAIN_ID = 1
BASE_CHAIN_ID = 8453
ARBITRUM_CHAIN_ID = 42161
POLYGON_CHAIN_ID = 137
OPTIMISM_CHAIN_ID = 10
AVALANCHE_CHAIN_ID = 43114
ZKSYNC_ERA_CHAIN_ID = 324

# Addresses for USDC on different chains, useful for quote tokens
USDC_ADDRESSES = {
    ETHEREUM_CHAIN_ID: USDC_ETHEREUM_ADDRESS,
    BASE_CHAIN_ID: USDC_BASE_ADDRESS,
    ARBITRUM_CHAIN_ID: USDC_ARBITRUM_NATIVE_ADDRESS, # Using Native USDC for Arbitrum
    POLYGON_CHAIN_ID: USDC_POLYGON_ADDRESS,
    OPTIMISM_CHAIN_ID: USDC_OPTIMISM_ADDRESS,
    AVALANCHE_CHAIN_ID: USDC_AVALANCHE_ADDRESS,
    ZKSYNC_ERA_CHAIN_ID: USDC_ZKSYNC_ADDRESS,
}

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

def fetch_1inch_whitelisted_tokens(chain_id_filter: int = None) -> list[dict]:
    """
    Fetches 1inch whitelisted multi-chain tokens, optionally filtering by a specific chainId.
    The endpoint returns data for all chains it supports; filtering is done client-side.

    Args:
        chain_id_filter: Optional chain ID to filter the results for.

    Returns:
        A list of token dictionaries, each containing address, symbol, name, decimals, and chainId.
        Returns an empty list if the API call fails or no tokens match the filter.

    Raises:
        OneInchAPIError: If the API request fails.
    """
    url = f"{TOKEN_API_DOMAIN}{MULTI_CHAIN_TOKENS_ENDPOINT_V1_3}"
    params = {"provider": "1inch"}  # As suggested by 1inch documentation

    logger.info(f"Fetching 1inch whitelisted multi-chain tokens. Filter for chain ID: {chain_id_filter if chain_id_filter else 'None'}")

    try:
        all_chains_tokens_data = _make_1inch_api_request(
            url,
            params=params,
            api_description="1inch Token API (Multi-chain Whitelist v1.3)"
        )
    except OneInchAPIError as e:
        logger.error(f"Failed to fetch whitelisted tokens: {e}")
        raise # Re-raise the error to be handled by the caller

    if not all_chains_tokens_data:
        logger.warning("Received no data from multi-chain token endpoint.")
        return []

    processed_tokens = []

    # Scenario 1: Response is a dictionary keyed by chain ID (string)
    if isinstance(all_chains_tokens_data, dict):
        logger.info(f"Fetched multi-chain token data as dict. Available chain IDs: {list(all_chains_tokens_data.keys())}")
        if chain_id_filter:
            chain_id_str = str(chain_id_filter)
            if chain_id_str in all_chains_tokens_data:
                tokens_for_chain = all_chains_tokens_data[chain_id_str]
                if isinstance(tokens_for_chain, list):
                    for token_data in tokens_for_chain:
                        if isinstance(token_data, dict) and all(k in token_data for k in ['address', 'symbol', 'name', 'decimals']):
                            processed_tokens.append({
                                'address': token_data['address'],
                                'symbol': token_data['symbol'],
                                'name': token_data['name'],
                                'decimals': token_data['decimals'],
                                'logoURI': token_data.get('logoURI') or '',  # Handle None values
                                'chainId': chain_id_filter
                            })
                        else:
                            logger.warning(f"Skipping malformed token data for chain {chain_id_str}: {str(token_data)[:100]}")
                else:
                    logger.warning(f"Token data for chain {chain_id_str} is not a list: {type(tokens_for_chain)}")
            else:
                logger.warning(f"Chain ID {chain_id_filter} not found in multi-chain token response dictionary.")
        else: # No filter, process all tokens from all chains in the dictionary
            logger.info("Processing all tokens from multi-chain dictionary (no chain_id_filter).")
            for chain_id_key, tokens_for_chain in all_chains_tokens_data.items():
                try:
                    current_chain_id = int(chain_id_key)
                except ValueError:
                    logger.warning(f"Could not parse chain ID key '{chain_id_key}' to int. Skipping.")
                    continue
                if isinstance(tokens_for_chain, list):
                    for token_data in tokens_for_chain:
                        if isinstance(token_data, dict) and all(k in token_data for k in ['address', 'symbol', 'name', 'decimals']):
                            processed_tokens.append({
                                'address': token_data['address'],
                                'symbol': token_data['symbol'],
                                'name': token_data['name'],
                                'decimals': token_data['decimals'],
                                'logoURI': token_data.get('logoURI') or '',  # Handle None values
                                'chainId': current_chain_id
                            })
                        else:
                            logger.warning(f"Skipping malformed token data for chain {chain_id_key}: {str(token_data)[:100]}")
    # Scenario 2: Response is a flat list of tokens
    elif isinstance(all_chains_tokens_data, list):
        logger.info("Fetched multi-chain token data as a flat list.")
        for token_data in all_chains_tokens_data:
            if not (isinstance(token_data, dict) and all(k in token_data for k in ['address', 'symbol', 'name', 'decimals'])):
                logger.warning(f"Skipping malformed token data in flat list: {str(token_data)[:100]}")
                continue

            # Check for chainId or chainIds field for filtering
            token_chain_id = token_data.get('chainId')
            token_chain_ids = token_data.get('chainIds') # Some APIs use a list of chain IDs

            matches_filter = False
            if chain_id_filter is None: # No filter, include the token
                matches_filter = True
            elif token_chain_id is not None and token_chain_id == chain_id_filter:
                matches_filter = True
            elif isinstance(token_chain_ids, list) and chain_id_filter in token_chain_ids:
                matches_filter = True
            
            if matches_filter:
                processed_tokens.append({
                    'address': token_data['address'],
                    'symbol': token_data['symbol'],
                    'name': token_data['name'],
                    'decimals': token_data['decimals'],
                    'logoURI': token_data.get('logoURI') or '',  # Handle None values
                    'chainId': chain_id_filter if chain_id_filter is not None else token_chain_id if token_chain_id is not None else 'N/A' # Best effort for chainId
                })
    else:
        logger.error(f"Unexpected data structure for multi-chain tokens: {type(all_chains_tokens_data)}. Response: {str(all_chains_tokens_data)[:200]}")
        return []

    logger.info(f"Processed {len(processed_tokens)} tokens for chain ID filter: {chain_id_filter if chain_id_filter else 'ALL'}.")
    return processed_tokens
