# backend/app/services/blockscout_service.py
import requests
import logging
from typing import List, Dict, Any, Optional, Union

from configs import *

logger = logging.getLogger(__name__)

# Use a session for connection pooling and consistent headers. [1, 2, 4, 12]
session = requests.Session()
session.headers.update({"Accept": "application/json"})

DEFAULT_TIMEOUT = 10  # seconds

def _get_blockscout_base_url(chain_name: str) -> str:
    """Helper to get the correct Blockscout API base URL based on chain_name."""
    if chain_name.lower() == "sepolia":
        return BLOCKSCOUT_SEPOLIA_API_BASE_URL
    elif chain_name.lower() == "rootstock_testnet" and BLOCKSCOUT_ROOTSTOCK_TESTNET_API_BASE_URL:
        return BLOCKSCOUT_ROOTSTOCK_TESTNET_API_BASE_URL
    # Add more chains here as needed
    else:
        raise ValueError(f"Unsupported chain_name or Blockscout URL not configured: {chain_name}")

def _query_blockscout_v2(
    blockscout_api_base_url: str,
    api_v2_path_segment: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """
    Core helper function to query Blockscout API V2 endpoints.
    """
    assert blockscout_api_base_url.endswith("/api"), \
        f"Blockscout API base URL must end with /api. Received: {blockscout_api_base_url}"
    assert api_v2_path_segment.startswith("/v2/"), \
        f"Blockscout API V2 path segment must start with /v2/. Received: {api_v2_path_segment}"

    full_url = f"{blockscout_api_base_url.rstrip('/')}{api_v2_path_segment}"
    logger.debug(f"Querying Blockscout V2 URL: {full_url} with params: {params}")


    response = session.get(full_url, params=params, timeout=timeout)

    if response.status_code == 404:
        logger.warning(f"Blockscout API returned 404 Not Found for {full_url}. Params: {params}")
        return None if not api_v2_path_segment.endswith(("/token-balances", "/transactions")) else []


    response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses

    return response.json()

def fetch_native_balance_blockscout(target_address: str, chain_name: str) -> Optional[int]:
    """
    Fetches the native coin balance for a given address.
    Returns balance in wei as an int, or None if not found or error.
    Doc: e.g., https://eth-sepolia.blockscout.com/api-docs (find /api/v2/addresses/{address_hash})
    """
    if not target_address or not isinstance(target_address, str) or not target_address.startswith("0x"):
        raise ValueError("target_address must be a valid 0x-prefixed Ethereum address string.")
    if not chain_name or not isinstance(chain_name, str):
        raise ValueError("chain_name must be a non-empty string.")

    api_base_url = _get_blockscout_base_url(chain_name)
    api_v2_path_segment = f"/v2/addresses/{target_address}"


    data = _query_blockscout_v2(api_base_url, api_v2_path_segment)
    if data and isinstance(data, dict) and "coin_balance" in data:
        balance_wei_str = data.get("coin_balance")
        if balance_wei_str is not None:
            return int(balance_wei_str) # Balance is usually a string representing wei
    return None


def fetch_erc20_balances_blockscout(target_address: str, chain_name: str) -> List[Dict[str, Any]]:
    """
    Fetches ERC20 token balances for a given address.
    Doc: e.g., https://eth-sepolia.blockscout.com/api-docs (find /api/v2/addresses/{address_hash}/token-balances)
    """
    if not target_address or not isinstance(target_address, str) or not target_address.startswith("0x"):
        raise ValueError("target_address must be a valid 0x-prefixed Ethereum address string.")
    if not chain_name or not isinstance(chain_name, str):
        raise ValueError("chain_name must be a non-empty string.")

    api_base_url = _get_blockscout_base_url(chain_name)
    api_v2_path_segment = f"/v2/addresses/{target_address}/token-balances"
    transformed_balances: List[Dict[str, Any]] = []


    raw_balances = _query_blockscout_v2(api_base_url, api_v2_path_segment)

    if raw_balances is None: # Can happen with 404 for an address with no token balances
        return []
    if not isinstance(raw_balances, list):
        logger.error(f"Expected list of token balances, got {type(raw_balances)} for {target_address} on {chain_name}")
        return []

    for item in raw_balances:
        if not isinstance(item, dict) or "token" not in item or not isinstance(item["token"], dict):
            logger.warning(f"Skipping malformed token balance item: {item}")
            continue
        token_data = item["token"]
        balance_entry = {
            "contract_address": token_data.get("address"),
            "symbol": token_data.get("symbol"),
            "name": token_data.get("name"),
            "decimals": str(token_data.get("decimals")),
            "balance_wei": str(item.get("value")),      
            "token_type": token_data.get("type"),
            "icon_url": token_data.get("icon_url")
        }
        
        if not balance_entry["contract_address"] or balance_entry["balance_wei"] is None:
            logger.warning(f"Skipping token balance item with missing address or value: {balance_entry}")
            continue
        transformed_balances.append(balance_entry)
    return transformed_balances



def fetch_address_transactions_blockscout(
    target_address: str,
    chain_name: str,
    limit: int = 10,
    page_token: Optional[str] = None # For pagination if API supports it directly
) -> Dict[str, Any]: # Returns a dict with 'items' and 'next_page_params'
    """
    Fetches transactions for a given address.
    Doc: e.g., https://eth-sepolia.blockscout.com/api-docs (find /api/v2/addresses/{address_hash}/transactions)
    Note: Blockscout V2 pagination uses `next_page_params` which is a complex object.
           For simplicity, this example may not fully implement iterative pagination.
           The 'filter' param might be relevant e.g. 'erc_20' or 'coin' (native)
    """
    if not target_address or not isinstance(target_address, str) or not target_address.startswith("0x"):
        raise ValueError("target_address must be a valid 0x-prefixed Ethereum address string.")
    if not chain_name or not isinstance(chain_name, str):
        raise ValueError("chain_name must be a non-empty string.")
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer.")


    api_base_url = _get_blockscout_base_url(chain_name)
    api_v2_path_segment = f"/v2/addresses/{target_address}/transactions"
    query_params: Dict[str, Any] = {} # Add page_token or other pagination params if structure is known

    data = _query_blockscout_v2(api_base_url, api_v2_path_segment, params=query_params)

    if data and isinstance(data, dict) and "items" in data and "next_page_params" in data:
        # Ensure items is a list
        if not isinstance(data["items"], list):
            logger.error(f"Expected 'items' to be a list, got {type(data['items'])}")
            return {"items": [], "next_page_params": None}
        # You might want to simplify transaction items here
        # For now, returning the structure as is.
        return {
            "items": data["items"][:limit], # Manually limit if more items returned than requested
            "next_page_params": data["next_page_params"]
        }
    elif data is None and api_v2_path_segment.endswith("/transactions"): # Handle 404 case for this endpoint
        return {"items": [], "next_page_params": None}

    logger.warning(f"Unexpected transaction data structure for {target_address} on {chain_name}: {str(data)[:200]}")
    return {"items": [], "next_page_params": None} # Default empty response
