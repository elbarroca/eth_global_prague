import requests
import logging
import time
import os
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
ONE_INCH_API_KEY = os.getenv("ONE_INCH_API_KEY", "")
FUSION_PLUS_BASE_URL = "https://api.1inch.dev/fusion-plus"
DEFAULT_SOURCE_APP_NAME = "ETHGlobalPrague"  # Default source app name for your application

logger = logging.getLogger(__name__)

# --- HTTP Session for 1inch Dev Portal & Fusion API ---
SESSION = requests.Session()
if ONE_INCH_API_KEY:
    SESSION.headers.update({"Authorization": f"Bearer {ONE_INCH_API_KEY}"})
else:
    logger.warning("ONE_INCH_API_KEY not found in environment variables. API calls will likely fail.")
SESSION.headers.update({"Accept": "application/json"})
SESSION.headers.update({"Content-Type": "application/json"})

# --- Custom Exception ---
class OneInchAPIError(RuntimeError):
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None, url: Optional[str] = None):
        super().__init__(f"[1inch API] {message}")
        self.status_code = status_code
        self.response_text = response_text
        self.url = url

# --- Helper for Making Requests ---
def _make_one_inch_request(
    method: str,
    endpoint: str,  # e.g., "/v1.0/quote/receive" or "/orders/v1.0/order/ready-to-accept-secret-fills/{orderHash}"
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    service_type: str = None  # Can be "quoter", "orders", or None (default)
) -> Any:
    """
    Make a request to the 1inch Fusion+ API.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path (starting with /)
        params: Query parameters
        json_data: JSON body data
        service_type: Specific service type (quoter, orders, etc.)
    
    Returns:
        JSON response from the API
    """
    # Construct the base URL based on service_type
    if service_type:
        base_url = f"{FUSION_PLUS_BASE_URL}/{service_type}"
    else:
        base_url = FUSION_PLUS_BASE_URL
    
    # If endpoint already includes the service type, use the base URL directly
    if endpoint.startswith("/quoter/") or endpoint.startswith("/orders/"):
        base_url = FUSION_PLUS_BASE_URL
    
    url = f"{base_url}{endpoint}"
    
    try:
        response = SESSION.request(method, url, params=params, json=json_data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - {response.status_code} - {response.text}")
        raise OneInchAPIError(
            f"HTTP error: {response.status_code}",
            status_code=response.status_code,
            response_text=response.text,
            url=url
        ) from http_err
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred: {req_err}")
        raise OneInchAPIError(f"Request failed: {str(req_err)}", url=url) from req_err
    except ValueError as json_err:
        logger.error(f"JSON decoding error: {json_err} - Response text: {response.text}")
        raise OneInchAPIError(f"JSON decoding error: {str(json_err)}", response_text=response.text, url=url) from json_err


# --- Functions related to Fusion+ ---

def get_fusion_plus_quote_backend(
    src_chain_id: int,
    dst_chain_id: int,
    src_token_address: str,
    dst_token_address: str,
    amount_wei: str,
    wallet_address: str,
    enable_estimate: bool = True
) -> Dict[str, Any]:
    """
    Calls the 1inch Fusion+ API to get a cross-chain quote.
    """
    endpoint = "/v1.0/quote/receive"
    payload = {
        "srcChainId": src_chain_id,
        "dstChainId": dst_chain_id,
        "fromTokenAddress": src_token_address,
        "toTokenAddress": dst_token_address,
        "amount": amount_wei,
        "walletAddress": wallet_address,
        "enableEstimate": enable_estimate,
    }
    logger.info(f"Requesting Fusion+ quote with payload: {payload}")
    try:
        quote_response = _make_one_inch_request("POST", endpoint, json_data=payload, service_type="quoter")
        logger.info(f"Received Fusion+ quote: {quote_response}")
        return quote_response
    except OneInchAPIError as e:
        logger.error(f"Error getting Fusion+ quote: {e}")
        raise

def prepare_fusion_plus_order_for_signing_backend(
    quote: Dict[str, Any],
    wallet_address: str,
    receiver_address: Optional[str] = None,
    source_app_name: str = DEFAULT_SOURCE_APP_NAME,
    preset_name: str = "fast",
    custom_preset: Optional[Dict[str, Any]] = None,
    permit: Optional[str] = None,
    deadline_shift_sec: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calls the 1inch Fusion+ API to build the order structure that needs to be signed by the user.
    """
    endpoint = "/v1.0/quote/build"
    
    if not quote.get("quoteId"):
        raise ValueError("quoteId is missing from the quote object.")

    build_payload = {
        "quoteId": quote["quoteId"],
        "walletAddress": wallet_address,
        "receiver": receiver_address if receiver_address else wallet_address,
        "source": source_app_name,
    }

    if custom_preset:
        build_payload["customPreset"] = custom_preset
    
    if permit:
        build_payload["permit"] = permit
    if deadline_shift_sec is not None:
        build_payload["deadlineShift"] = deadline_shift_sec

    logger.info(f"Requesting Fusion+ order build with payload: {build_payload}")
    try:
        built_order_data = _make_one_inch_request("POST", endpoint, json_data=build_payload, service_type="quoter")
        logger.info(f"Received Fusion+ built order data for signing: {built_order_data}")
        return built_order_data
    except OneInchAPIError as e:
        logger.error(f"Error building Fusion+ order for signing: {e}")
        raise


def submit_signed_fusion_plus_order_backend(
    src_chain_id: int,
    signed_order_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Submits a signed Fusion+ order (potentially cross-chain) to the 1inch Relayer.
    """
    endpoint = "/v1.0/submit"
    
    if "chainId" not in signed_order_payload:
        signed_order_payload["chainId"] = src_chain_id
    elif signed_order_payload["chainId"] != src_chain_id:
        logger.warning(f"src_chain_id ({src_chain_id}) differs from chainId in payload ({signed_order_payload['chainId']}). Using payload's.")

    logger.info(f"Submitting signed Fusion+ order with payload: {signed_order_payload}")
    try:
        submission_response = _make_one_inch_request("POST", endpoint, json_data=signed_order_payload)
        logger.info(f"Received Fusion+ order submission response: {submission_response}")
        return submission_response
    except OneInchAPIError as e:
        logger.error(f"Error submitting signed Fusion+ order: {e}")
        raise


# Additional helper for checking order status (useful for cross-chain orders)
def check_order_status(order_hash: str) -> Dict[str, Any]:
    """
    Check the status of an order by its hash.
    """
    endpoint = f"/v1.0/order/ready-to-accept-secret-fills/{order_hash}"
    logger.info(f"Checking status for order: {order_hash}")
    try:
        status_response = _make_one_inch_request("GET", endpoint, service_type="orders")
        logger.info(f"Received order status: {status_response}")
        return status_response
    except OneInchAPIError as e:
        logger.error(f"Error checking order status: {e}")
        raise

