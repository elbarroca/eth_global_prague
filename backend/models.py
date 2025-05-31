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
    asset_symbol: str # Global symbol e.g. "ETH-USDC_on_Optimism"
    signal_type: str
    confidence: float
    details: Dict[str, Any]
    timestamp: int # Forecast timestamp
    chain_id: Optional[int] = None
    base_token_address: Optional[str] = None # Renamed from token_address
    # Optional: add quote_token_address, base_token_symbol, quote_token_symbol if needed by signal generation/ranking logic itself

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
    # _id: ObjectIdField  -> implied by MongoDB
    chain_id: int
    base_token_address: str
    quote_token_address: str
    period_seconds: int
    timeframe: str # e.g. "day", "hour", "min15"
    
    # New fields:
    base_token_symbol: str 
    quote_token_symbol: str # e.g., "USDC", "USDT"
    chain_name: str 

    ohlcv_candles: List[OHLVCRecord] = Field(default_factory=list)
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

class ForecastSignalRecord(BaseModel):
    asset_symbol: str                 # e.g., "ETH-USDC_on_Optimism" - Global identifier
    chain_id: int
    base_token_address: Optional[str] = None
    quote_token_address: Optional[str] = None 
    base_token_symbol: Optional[str] = None   
    quote_token_symbol: Optional[str] = None  
    signal_type: str 
    timeframe: str # Added timeframe field
    confidence: float
    details: Dict[str, Any] 
    forecast_timestamp: int 
    ohlcv_data_timestamp: int 
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

class StoredCrossChainPortfolioData(BaseModel):
    request_chain_ids_str: str
    request_timeframe: str
    request_max_tokens_per_chain: int
    request_mvo_objective: str
    request_risk_free_rate: float
    request_annualization_factor_override: Optional[int] = None
    request_target_return: Optional[float] = None
    
    # The actual response data to cache
    response_data: CrossChainPortfolioResponse
    
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
