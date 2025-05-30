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
