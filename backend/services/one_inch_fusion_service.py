import requests
import logging
import time # For potential delays or timeouts
from typing import Optional, List, Dict, Any, Union # Added Union

# Import settings/configs
try:
    from ..configs import *
except ImportError:
    # Fallback for absolute import
    from configs import *

# Configuration constants (these should be defined in configs.py or environment)
FUSION_PLUS_API_BASE_URL = "https://api.1inch.dev/fusion-plus"  # As per cross-chain-sdk
DEFAULT_SOURCE_APP_NAME = "AOSE_DApp"

logger = logging.getLogger(__name__)

# --- HTTP Session for 1inch Dev Portal & Fusion API ---
SESSION = requests.Session()
if ONE_INCH_API_KEY:
    SESSION.headers.update({"Authorization": f"Bearer {ONE_INCH_API_KEY}"})
SESSION.headers.update({"Accept": "application/json"})
SESSION.headers.update({"Content-Type": "application/json"}) # Good practice for POST

# --- Custom Exception ---
class OneInchAPIError(RuntimeError):
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None, url: Optional[str] = None):
        super().__init__(f"[1inch API] {message}")
        self.status_code = status_code
        self.response_text = response_text
        self.url = url

# --- Helper for Making Requests (Assuming you have this defined elsewhere) ---
def _make_one_inch_request(
    method: str,
    endpoint: str, # e.g., "/v1.0/quote/receive"
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    base_url: str = FUSION_PLUS_API_BASE_URL # Default to Fusion+
) -> Any:
    url = f"{base_url}{endpoint}"
    try:
        response = SESSION.request(method, url, params=params, json=json_data, timeout=30) # Added timeout
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
    except ValueError as json_err: # Catch JSON decoding errors
        logger.error(f"JSON decoding error: {json_err} - Response text: {response.text}")
        raise OneInchAPIError(f"JSON decoding error: {str(json_err)}", response_text=response.text, url=url) from json_err


# --- NEW: Functions related to Fusion+ ---

def get_fusion_plus_quote_backend(
    src_chain_id: int,
    dst_chain_id: int,
    src_token_address: str,
    dst_token_address: str,
    amount_wei: str,
    wallet_address: str, # Required by the cross-chain SDK's getQuote
    enable_estimate: bool = True # As seen in cross-chain SDK
    # permit_data: Optional[str] = None # Permit is usually part of order creation if needed
) -> Dict[str, Any]:
    """
    Calls the 1inch Fusion+ API to get a cross-chain quote.
    Corresponds to `POST /v1.0/quoter/{srcChainId}/quote/receive` (based on typical 1inch API structure,
    but cross-chain SDK uses a unified endpoint, so we'll use that for direct call).
    The cross-chain SDK example points to a general quote endpoint for fusion-plus.
    The swagger for /v1.0/quote/receive seems more generic. Let's assume a POST to a path that includes chain info or is handled by the body.
    The cross-chain SDK example uses: `sdk.getQuote({ amount, srcChainId, dstChainId, srcTokenAddress, dstTokenAddress, walletAddress, enableEstimate })`
    The API endpoint for this is likely `POST /v1.0/quote/receive` on the `fusion-plus` base URL.
    """
    # The `POST /v1.0/quote/receive` endpoint in the Swagger link you provided seems to be for this.
    # It expects a body.
    endpoint = "/v1.0/quote/receive" # From your provided Swagger link
    payload = {
        "srcChainId": src_chain_id,
        "dstChainId": dst_chain_id,
        "fromTokenAddress": src_token_address, # API uses fromTokenAddress/toTokenAddress
        "toTokenAddress": dst_token_address,
        "amount": amount_wei,
        "walletAddress": wallet_address,
        "enableEstimate": enable_estimate,
        # "permit": permit_data, # Permit is usually for the order itself, not the quote.
        # "takingFeeBps": 0 # Optional: if you have specific fee requirements
    }
    logger.info(f"Requesting Fusion+ quote with payload: {payload}")
    try:
        quote_response = _make_one_inch_request("POST", endpoint, json_data=payload, base_url=FUSION_PLUS_API_BASE_URL)
        logger.info(f"Received Fusion+ quote: {quote_response}")
        return quote_response # This will be the full quote object from the API
    except OneInchAPIError as e:
        logger.error(f"Error getting Fusion+ quote: {e}")
        raise # Re-raise the error for the caller to handle

def prepare_fusion_plus_order_for_signing_backend(
    quote: Dict[str, Any], # The full quote object from get_fusion_plus_quote_backend
    wallet_address: str, # User's EVM wallet address (maker) on source chain
    receiver_address: Optional[str] = None, # User's destination address (e.g., Solana if different, or EVM on dest chain)
    # Preset and secrets are crucial for Fusion+ and come from the quote or are generated.
    # The cross-chain SDK example: sdk.createOrder(quote, { walletAddress, hashLock, preset, source, secretHashes })
    # `hashLock` and `secretHashes` are derived from `secrets`.
    # The backend *could* generate secrets if it's also going to manage their submission later,
    # but this is complex. Typically, the frontend SDK might handle secret generation.
    # For this function, we assume the necessary parts of the quote (like presets) guide this.
    # The `POST /v1.0/order/build` endpoint is likely what the SDK calls.
    source_app_name: str = DEFAULT_SOURCE_APP_NAME,
    # We need to choose a preset from the quote.
    # And then potentially prepare for secrets if the backend is involved in that part.
    # For now, this function will focus on parameters for the equivalent of `sdk.createOrder`
    # which means we might be calling the `/order/build` endpoint.
    preset_name: str = "fast", # User should select or default to a preset from the quote
    # If secrets are managed by frontend, it will handle hashLock and secretHashes.
    # If backend were to prepare for `build` API call, it might need these.
    # For now, let's assume this function prepares params for frontend SDK's createOrder,
    # or if calling /order/build, it would need more inputs like generated secrets/hashlock.
    # Let's align with the `/v1.0/order/build` swagger.
    # This endpoint helps construct the order data that needs to be signed.
    custom_preset: Optional[Dict[str, Any]] = None, # If not using a named preset from quote
    permit: Optional[str] = None, # EIP-2612 permit for fromToken
    deadline_shift_sec: Optional[int] = None # If you want to adjust auction deadline

) -> Dict[str, Any]:
    """
    Calls the 1inch Fusion+ API to build the order structure that needs to be signed by the user.
    Corresponds to `POST /v1.0/quoter/{srcChainId}/order/build` (adjusting for actual Fusion+ structure).
    The swagger link provided is `POST /v1.0/quote/build` - this seems to be the one.
    """
    endpoint = "/v1.0/quote/build" # From your provided Swagger link for "build"
    
    # Extract necessary info from the quote for the build payload
    # The build payload requires `quoteId` and parameters to customize the order.
    if not quote.get("quoteId"):
        raise ValueError("quoteId is missing from the quote object.")

    build_payload = {
        "quoteId": quote["quoteId"],
        "walletAddress": wallet_address,
        "receiver": receiver_address if receiver_address else wallet_address,
        "source": source_app_name,
        # Preset handling: The API might expect either a preset name (if it can resolve it from quoteId)
        # or the actual preset values. The cross-chain SDK uses a preset from the quote.
        # `quote.presets[chosen_preset_name]` would contain `auctionDuration`, `initialRate`, etc.
        # The /v1.0/quote/build swagger shows it takes `customPreset` or relies on quote's default.
    }

    if custom_preset: # If providing a full custom preset structure
        build_payload["customPreset"] = custom_preset
    elif preset_name and quote.get("presets") and quote["presets"].get(preset_name):
        # If using a named preset from the quote, the API might infer it from quoteId,
        # or you might need to pass specific fields. The /quote/build swagger implies
        # it might take `auctionDuration`, `minReceiveAmount`, etc. directly if not using `customPreset`.
        # For simplicity, let's assume if not custom_preset, the API uses the quote's default or recommended.
        # The SDK's `createOrder` takes the *chosen preset object* from the quote.
        # The API might be similar or just needs the name/quoteId.
        # The swagger for /quote/build doesn't explicitly list preset name as a top-level field,
        # suggesting it either uses the quote's default or requires `customPreset`.
        # For cross-chain, `hashLock` and `secretHashes` are also vital.
        # The `/v1.0/quote/build` swagger *does not* show hashLock or secretHashes.
        # This implies that `/v1.0/quote/build` might be for simpler Fusion orders, OR
        # that these are added *after* this build step by the SDK before signing, OR
        # there's a different build endpoint for cross-chain that includes these.

        # Given the cross-chain SDK `createOrder(quote, { walletAddress, hashLock, preset, source, secretHashes })`
        # It's likely the `order` object returned by `/v1.0/quote/build` is then augmented with hashLock/secretHashes
        # by the SDK before constructing the EIP-712 typed data for signing.

        # For now, this function will just call `/v1.0/quote/build`.
        # The frontend SDK would then take this response, add hashLock/secretHashes (generated on frontend),
        # and then prepare for EIP-712 signing.
        pass # API will use default from quote or one specified if API allows name

    if permit:
        build_payload["permit"] = permit
    if deadline_shift_sec is not None: # API uses `deadlineShift`
        build_payload["deadlineShift"] = deadline_shift_sec


    logger.info(f"Requesting Fusion+ order build with payload: {build_payload}")
    try:
        # The build endpoint is under /quoter/{chainId}/order/build in some contexts.
        # However, your swagger link is /v1.0/quote/build. Let's use that.
        # Chain context for build might be implicit from quoteId.
        built_order_data = _make_one_inch_request("POST", endpoint, json_data=build_payload, base_url=FUSION_PLUS_API_BASE_URL)
        logger.info(f"Received Fusion+ built order data for signing: {built_order_data}")
        # This response should contain the `order` structure (EIP-712 domain, types, message)
        # and potentially other details needed for signing.
        # For cross-chain, the SDK would then add `hashLock` and `secretHashes` to the order message.
        return built_order_data
    except OneInchAPIError as e:
        logger.error(f"Error building Fusion+ order for signing: {e}")
        raise


def submit_signed_fusion_plus_order_backend(
    src_chain_id: int, # Source chain ID, needed for the API path
    signed_order_payload: Dict[str, Any], # This is the payload for POST /v1.0/submit
                                          # which includes `order` (the signed EIP-712 order object),
                                          # `quoteId`, and `secretHashes` for cross-chain.
) -> Dict[str, Any]:
    """
    Submits a signed Fusion+ order (potentially cross-chain) to the 1inch Relayer.
    Corresponds to `POST /v1.0/relayer/{srcChainId}/order/submit` or the SDK's `sdk.submitOrder()`.
    The swagger link provided is `POST /v1.0/submit`. This endpoint is chain-agnostic in path,
    implying chainId might be part of the payload or inferred.
    However, the cross-chain SDK's `submitOrder(quote.srcChainId, order, quoteId, secretHashes)`
    suggests `srcChainId` is key. The general `/v1.0/submit` swagger takes `chainId` in the body.
    """
    endpoint = "/v1.0/submit" # From your provided Swagger link
    
    # The payload for `/v1.0/submit` according to its swagger:
    # { chainId: number, order: FusionOrder, quoteId: string, secretHashes?: string[] }
    # `signed_order_payload` should already be structured like this by the caller.
    # Ensure chainId is present.
    if "chainId" not in signed_order_payload:
        signed_order_payload["chainId"] = src_chain_id
    elif signed_order_payload["chainId"] != src_chain_id:
        # Or handle as an error, depending on desired strictness
        logger.warning(f"src_chain_id ({src_chain_id}) differs from chainId in payload ({signed_order_payload['chainId']}). Using payload's.")


    logger.info(f"Submitting signed Fusion+ order with payload: {signed_order_payload}")
    try:
        submission_response = _make_one_inch_request("POST", endpoint, json_data=signed_order_payload, base_url=FUSION_PLUS_API_BASE_URL)
        logger.info(f"Received Fusion+ order submission response: {submission_response}")
        # Expected response: { orderHash: string, txHash?: string (if executed immediately), status: string }
        return submission_response
    except OneInchAPIError as e:
        logger.error(f"Error submitting signed Fusion+ order: {e}")
        raise
