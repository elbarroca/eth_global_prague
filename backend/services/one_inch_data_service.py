import requests
import logging
import os
import time
import httpx
import asyncio
from typing import Optional

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

API_KEY = os.getenv("ONE_INCH_API_KEY")
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
USDC_ZKSYNC_ADDRESS = "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4"
USDC_ARBITRUM_NATIVE_ADDRESS = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"

# --- USDT Addresses (Canonical or widely recognized) ---
USDT_ETHEREUM_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
USDT_ARBITRUM_ADDRESS = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"
USDT_POLYGON_ADDRESS = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
USDT_OPTIMISM_ADDRESS = "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58"
USDT_AVALANCHE_ADDRESS = "0xc7198437980c041c805A1EDcbA50c1Ce5db95118" # Native USDT
USDT_ZKSYNC_ERA_ADDRESS = "0x493257fA496cb83AF5EAbA3805EC149AE805B09d"
# USDT_BASE_ADDRESS = "..." # Base does not have a widely adopted canonical USDT yet

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

# Addresses for USDT on different chains
USDT_ADDRESSES = {
    ETHEREUM_CHAIN_ID: USDT_ETHEREUM_ADDRESS,
    # BASE_CHAIN_ID: USDT_BASE_ADDRESS, # Commented out as no clear canonical USDT on Base
    ARBITRUM_CHAIN_ID: USDT_ARBITRUM_ADDRESS,
    POLYGON_CHAIN_ID: USDT_POLYGON_ADDRESS,
    OPTIMISM_CHAIN_ID: USDT_OPTIMISM_ADDRESS,
    AVALANCHE_CHAIN_ID: USDT_AVALANCHE_ADDRESS,
    ZKSYNC_ERA_CHAIN_ID: USDT_ZKSYNC_ERA_ADDRESS,
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
    def __init__(self, message, status_code=None, response_text=None, url_requested=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        self.url_requested = url_requested

    def __str__(self):
        return f"{super().__str__()} (Status: {self.status_code}, URL: {self.url_requested}, Response: {self.response_text[:500] if self.response_text else 'N/A'})"

# --- Global httpx.AsyncClient instance for connection pooling ---
# It's better to manage the client's lifecycle, e.g., at application startup/shutdown,
# but for this service module, we can define it here.
# Consider passing a client instance if this service is instantiated.
_async_http_client: Optional[httpx.AsyncClient] = None

async def get_http_client() -> httpx.AsyncClient:
    """Provides a global httpx.AsyncClient instance, creating it if necessary."""
    global _async_http_client
    if _async_http_client is None or _async_http_client.is_closed:
        _async_http_client = httpx.AsyncClient(timeout=30) # Default timeout
    return _async_http_client

async def close_http_client():
    """Closes the global httpx.AsyncClient."""
    global _async_http_client
    if _async_http_client and not _async_http_client.is_closed:
        await _async_http_client.aclose()
        _async_http_client = None
        logger.info("Global httpx.AsyncClient closed.")

async def _make_1inch_api_request(url: str, params: dict = None, api_description: str = "1inch API"):
    logger.info(f"Attempting to fetch data async from {api_description} URL: {url} with params: {params}")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json"
    }
    
    client = await get_http_client()

    try:
        response = await client.get(url, headers=headers, params=params)
        logger.debug(f"Request URL: {response.url}")
        logger.debug(f"Request headers: {headers}")
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response raw text (first 500 chars): {response.text[:500]}")
        
        response.raise_for_status()
        
        json_response = response.json()
        logger.info(f"Successfully fetched data async from {api_description} for URL: {url}.")
        return json_response
        
    except httpx.TimeoutException as e:
        logger.error(f"API request timed out for {api_description} URL: {e.request.url}")
        raise OneInchAPIError(
            f"API request timed out for {api_description}", 
            response_text=str(e),
            url_requested=str(e.request.url)
        ) from e
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error for {api_description}: {e} - Status: {e.response.status_code} - URL: {e.request.url} - Text: {e.response.text}")
        raise OneInchAPIError(
            f"HTTP error for {api_description}",
            status_code=e.response.status_code,
            response_text=e.response.text,
            url_requested=str(e.request.url)
        ) from e
    except httpx.RequestError as e:
        logger.error(f"API request failed for {api_description} URL: {e.request.url}: {e}")
        raise OneInchAPIError(
            f"API request failed for {api_description}", 
            response_text=str(e),
            url_requested=str(e.request.url)
        ) from e
    except ValueError as e:
        response_text_snippet = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available'
        status_code_snippet = response.status_code if 'response' in locals() and hasattr(response, 'status_code') else 'N/A'
        url_snippet = str(response.url) if 'response' in locals() and hasattr(response, 'url') else url
        logger.error(f"JSON decode error from {api_description}: {e}. Status: {status_code_snippet}. URL: {url_snippet}. Text: {response_text_snippet[:500]}")
        raise OneInchAPIError(
            f"JSON decode error from {api_description}",
            status_code=status_code_snippet,
            response_text=response_text_snippet,
            url_requested=url_snippet
        ) from e

async def get_ohlcv_data(token0_address: str, token1_address: str, interval_seconds: int, chain_id: int):
    """
    Fetches OHLCV (candlestick) data from the 1inch Charts API asynchronously.

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
    return await _make_1inch_api_request(url, api_description=f"1inch Charts API (OHLCV {token0_address[:6]}/{token1_address[:6]} on chain {chain_id})")

async def get_cross_prices_data(chain_id: int, token0_address: str, token1_address: str, from_timestamp: int, to_timestamp: int, granularity_key: str):
    """
    Fetches historical cross-price data from the 1inch Portfolio API v2 asynchronously.

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
    logger.info(f"Requesting Portfolio API v2 async with params: {params}")
    return await _make_1inch_api_request(PORTFOLIO_CROSS_PRICES_API_URL, params=params, api_description=f"1inch Portfolio API v2 (Cross Prices {token0_address[:6]}/{token1_address[:6]} on chain {chain_id})")

async def fetch_1inch_whitelisted_tokens(chain_id_filter: int = None) -> list[dict]:
    """
    Fetches 1inch whitelisted multi-chain tokens asynchronously, optionally filtering by a specific chainId.
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
    params = {"provider": "1inch"}

    logger.info(f"Fetching 1inch whitelisted multi-chain tokens async. Filter for chain ID: {chain_id_filter if chain_id_filter else 'None'}")

    try:
        all_chains_tokens_data = await _make_1inch_api_request(
            url,
            params=params,
            api_description="1inch Token API (Multi-chain Whitelist v1.3)"
        )
    except OneInchAPIError as e:
        logger.error(f"Failed to fetch whitelisted tokens async: {e}")
        raise

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
