# app/core/config.py
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv() # Load variables from .env file

ONE_INCH_API_KEY = os.getenv("ONE_INCH_API_KEY")

NATIVE_ASSET_ADDRESS = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

COMMON_STABLECOIN_SYMBOLS = {
    "USDT", "USDC", "USDS", "USDE", "DAI", "SUSD", "USD1", "FDUSD", "PYUSD", "USDX",
    "BUSD", "TUSD", "USDP", "GUSD", "FRAX", "LUSD", "PAX", "EURA", "EURS", "USDC.E",
    "USDT.E", "USDS_2", "USDC_2", "USDT_2", "USDC.E", "USDT.E", "USDC_E", "USDT_E", "ALUSD",
    "DOLA", "USD+", "USDPLUS", "USD_PLUS", "MIMATIC", "MAI", "AGEUR", "JEUR", "CEUR",
    "USDD", "USTC", "USDH", "USDN", "USDK", "USDJ", "USDR", "USDS", "USDT", "USDC"
}
# Chain IDs (can be expanded)
ETHEREUM_CHAIN_ID = 1
BASE_CHAIN_ID = 8453
ARBITRUM_CHAIN_ID = 42161
POLYGON_CHAIN_ID = 137
OPTIMISM_CHAIN_ID = 10
AVALANCHE_CHAIN_ID = 43114
ZKSYNC_ERA_CHAIN_ID = 324
LINEA_CHAIN_ID = 59144 # Added Linea

CHAIN_ID_TO_NAME = {
    ETHEREUM_CHAIN_ID: "Ethereum",
    BASE_CHAIN_ID: "Base",
    ARBITRUM_CHAIN_ID: "Arbitrum",
    POLYGON_CHAIN_ID: "Polygon",
    OPTIMISM_CHAIN_ID: "Optimism",
    AVALANCHE_CHAIN_ID: "Avalanche",
    ZKSYNC_ERA_CHAIN_ID: "zkSync Era",
    LINEA_CHAIN_ID: "Linea",
}

# USDC Addresses (ensure these are the ones preferred by the Charts API for each chain)
USDC_ADDRESSES = {
    ETHEREUM_CHAIN_ID: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    BASE_CHAIN_ID: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    ARBITRUM_CHAIN_ID: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", # Native USDC on Arbitrum
    POLYGON_CHAIN_ID: "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359",  # Polygon PoS USDC
    OPTIMISM_CHAIN_ID: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", # Native USDC on Optimism
    AVALANCHE_CHAIN_ID: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",# Avalanche USDC.e (Bridged) or Native if preferred
    ZKSYNC_ERA_CHAIN_ID: "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4", # Native USDC on zkSync Era
    LINEA_CHAIN_ID: "0x176211869cA2b568f2A7D4EE941E073a821EE1ff", # Linea USDC (Bridged from Ethereum)
}

# USDT Addresses - Placeholder, please verify and complete
USDT_ADDRESSES = {
    ETHEREUM_CHAIN_ID: "0xdac17f958d2ee523a2206206994597c13d831ec7",
    ARBITRUM_CHAIN_ID: "0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9", 
    POLYGON_CHAIN_ID: "0xc2132d05d31c914a87c6611c10748aeb04b58e8f",
    BASE_CHAIN_ID: "0x4000ae0277180000",
}

WETH_ETHEREUM_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

PERIOD_HOURLY_SECONDS = 3600
PERIOD_4HOURLY_SECONDS = 14400
PERIOD_DAILY_SECONDS = 86400

BLOCKSCOUT_SEPOLIA_API_BASE_URL: str = "https://eth-sepolia.blockscout.com/api"
BLOCKSCOUT_ROOTSTOCK_TESTNET_API_BASE_URL: Optional[str] = None # Example