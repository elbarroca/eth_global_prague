from dataclasses import dataclass
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# Define Pydantic models for Fusion+ API requests
class FusionQuoteRequest(BaseModel):
    src_chain_id: int = Field(..., description="Source chain ID")
    dst_chain_id: int = Field(..., description="Destination chain ID")
    src_token_address: str = Field(..., description="Source token address")
    dst_token_address: str = Field(..., description="Destination token address")
    amount_wei: str = Field(..., description="Amount in wei")
    wallet_address: str = Field(..., description="User's wallet address")
    enable_estimate: bool = Field(True, description="Enable estimation")

class FusionOrderBuildRequest(BaseModel):
    quote: Dict[str, Any] = Field(..., description="Quote object from get_fusion_plus_quote")
    wallet_address: str = Field(..., description="User's wallet address")
    receiver_address: Optional[str] = Field(None, description="Receiver address (if different from wallet)")
    source_app_name: Optional[str] = Field(None, description="Source app name")
    preset_name: str = Field("fast", description="Preset name (fast, normal, etc.)")
    custom_preset: Optional[Dict[str, Any]] = Field(None, description="Custom preset configuration")
    permit: Optional[str] = Field(None, description="EIP-2612 permit")
    deadline_shift_sec: Optional[int] = Field(None, description="Deadline shift in seconds")

class FusionOrderSubmitRequest(BaseModel):
    src_chain_id: int = Field(..., description="Source chain ID")
    signed_order_payload: Dict[str, Any] = Field(..., description="Signed order payload")


@dataclass
class Signal:
    asset_symbol: str
    signal_type: str
    confidence: float
    details: Dict[str, Any]
    timestamp: int
    chain_id: Optional[int] = None
    token_address: Optional[str] = None

@dataclass
class OHLCVDataPoint:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float 




# --- Pydantic Models for MongoDB Data ---
class OHLVCRecord(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float

class StoredOHLCVData(BaseModel):
    chain_id: int
    base_token_address: str
    quote_token_address: str
    period_seconds: int
    timeframe: str # "hourly" or "daily"
    ohlcv_candles: List[OHLVCRecord]
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PortfolioWeights(BaseModel):
    asset_symbol: str
    weight: float

class StoredPortfolioData(BaseModel):
    chain_id: int
    timeframe: str
    num_top_assets: int
    mvo_objective: str
    risk_free_rate: float
    annualization_factor: int
    portfolio_weights: List[PortfolioWeights]
    expected_annual_return: float
    annual_volatility: float
    sharpe_ratio: float
    selected_assets: List[str]  # List of asset symbols used
    total_assets_screened: int
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SingleChainPortfolioOptimizationResult(BaseModel):
    chain_id: int
    chain_name: str
    status: str # e.g., "success", "error", "no_assets_found"
    data: Optional[Dict[str, Any]] = None # Contains the successful pipeline result
    error_message: Optional[str] = None
    request_params_for_chain: Dict[str, Any]

class CrossChainPortfolioResponse(BaseModel):
    results_by_chain: Dict[str, SingleChainPortfolioOptimizationResult] # Chain ID as string key
    overall_request_summary: Dict[str, Any]
