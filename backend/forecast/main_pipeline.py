# backend/forecast/main_pipeline.py
import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
import sys
import os
import asyncio # Added asyncio

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Signal, OHLCVDataPoint
# Import MongoDB service functions
from services.mongo_service import connect_to_mongo, close_mongo_connection, get_ohlcv_from_db
# Import configs for stablecoin filtering
from configs import COMMON_STABLECOIN_SYMBOLS

# Import the forecast functions with correct relative paths
from .quant_forecast import generate_quant_advanced_signals
from .ta_forecast import generate_ta_signals
from .mvo_portfolio import calculate_mvo_inputs, optimize_portfolio_mvo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Stablecoin Filtering Logic ---

def is_stablecoin_pair(asset_symbol: str) -> bool:
    """
    Check if an asset symbol represents a stablecoin vs stablecoin pair.
    Examples: USDC-USDT, EURA-USDC, USDS_2-USDC, USD+-USDC, DOLA-USDC, etc.
    """
    if '-' not in asset_symbol:
        return False
    
    base_symbol, quote_symbol = asset_symbol.split('-', 1)
    
    # Normalize symbols by removing common suffixes and converting to uppercase
    def normalize_symbol(symbol: str) -> str:
        symbol = symbol.upper().strip()
        # Remove common suffixes and prefixes
        for suffix in ['_2', '_E', '.E', '_PLUS', 'PLUS']:
            if symbol.endswith(suffix):
                symbol = symbol[:-len(suffix)]
        # Handle special cases
        if symbol == 'USD+':
            symbol = 'USDPLUS'
        elif symbol == 'MAI':
            symbol = 'MIMATIC'  # MAI is also known as MIMATIC
        return symbol
    
    base_normalized = normalize_symbol(base_symbol)
    quote_normalized = normalize_symbol(quote_symbol)
    
    # Additional pattern matching for USD-like tokens
    def is_usd_like(symbol: str) -> bool:
        symbol = symbol.upper()
        usd_patterns = ['USD', 'USDT', 'USDC', 'DAI', 'DOLA', 'MAI']
        return any(pattern in symbol for pattern in usd_patterns) or symbol.startswith('USD')
    
    # Check if both are stablecoins
    is_base_stable = (base_normalized in COMMON_STABLECOIN_SYMBOLS or 
                     is_usd_like(base_normalized))
    is_quote_stable = (quote_normalized in COMMON_STABLECOIN_SYMBOLS or 
                      is_usd_like(quote_normalized))
    
    result = is_base_stable and is_quote_stable
    
    if result:
        logger.debug(f"Detected stablecoin pair: {asset_symbol} (base: {base_normalized}, quote: {quote_normalized})")
    
    return result

def filter_non_stablecoin_pairs(asset_identifiers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter out stablecoin vs stablecoin pairs from asset identifiers.
    """
    filtered_assets = []
    filtered_out = []
    
    for asset_info in asset_identifiers:
        asset_symbol = asset_info.get("asset_symbol", "")
        
        if is_stablecoin_pair(asset_symbol):
            filtered_out.append(asset_symbol)
            logger.info(f"Filtering out stablecoin pair: {asset_symbol}")
        else:
            filtered_assets.append(asset_info)
    
    if filtered_out:
        logger.info(f"Filtered out {len(filtered_out)} stablecoin pairs: {filtered_out}")
    
    return filtered_assets

# --- Asset Ranking Logic ---

def rank_assets_based_on_signals(
    asset_signals: Dict[str, List[Signal]],
    quant_signal_weights: Optional[Dict[str, float]] = None,
    ta_signal_weights: Optional[Dict[str, float]] = None
) -> pd.DataFrame:
    """
    Ranks assets based on a weighted score of their generated signals.
    """
    if quant_signal_weights is None:
        # Default weights for quant signals (prioritize bullish, high confidence signals)
        quant_signal_weights = {
            "QUANT_FOURIER_MEAN_REVERSION_BUY": 1.5,
            "QUANT_MEANREVERT_OVEREXTENDED_LOW": 1.2,
            "QUANT_MOMENTUM_HIGH_SHARPE": 1.0,
            "QUANT_VOL_REGIME_LOW": 0.8, # Low volatility can be good for some strategies
            "QUANT_DISTRIBUTION_POSITIVE_SKEW_OPPORTUNITY": 0.7,
            "QUANT_LIQUIDITY_BULLISH_VPT_DIVERGENCE": 0.6,
            "QUANT_FOURIER_EXTREME_DEVIATION_LOW": 1.0,
            "QUANT_REGIME_STRONG_UPTREND": 0.9,
            # Penalize bearish/risk signals
            "QUANT_FOURIER_MEAN_REVERSION_SELL": -1.5,
            "QUANT_MEANREVERT_OVEREXTENDED_HIGH": -1.2,
            "QUANT_MOMENTUM_NEGATIVE_SHARPE": -1.0,
            "QUANT_CVAR95_HIGH_RISK": -1.5,
            "QUANT_GARCH_HIGH_VOL_FORECAST": -0.8,
            "QUANT_VOL_REGIME_HIGH": -0.8,
            "QUANT_DISTRIBUTION_NEGATIVE_SKEW_RISK": -1.0,
            "QUANT_LIQUIDITY_BEARISH_VPT_DIVERGENCE": -0.6,
            "QUANT_FOURIER_EXTREME_DEVIATION_HIGH": -1.0,
            "QUANT_REGIME_STRONG_DOWNTREND": -0.9,
        }
    if ta_signal_weights is None:
        # Default weights for TA signals
        ta_signal_weights = {
            "TA_MA_CROSS_BULLISH": 1.0,
            "TA_RSI_OVERSOLD": 0.8,
            "TA_MACD_CROSS_BULLISH": 1.2,
            "TA_MACD_BULLISH_MOMENTUM": 0.9,
            "TA_BB_BREAK_LOWER": 0.7, # Potential reversal
            "TA_STOCH_BULLISH_CROSS": 0.8,
            "TA_VOLUME_BREAKOUT_BULLISH": 0.6,
            "TA_MACD_ZERO_CROSS_BULLISH": 0.7,
            # Penalize bearish TA signals
            "TA_MA_CROSS_BEARISH": -1.0,
            "TA_RSI_OVERBOUGHT": -0.8,
            "TA_MACD_CROSS_BEARISH": -1.2,
            "TA_MACD_BEARISH_MOMENTUM": -0.9,
            "TA_BB_BREAK_UPPER": -0.7, # Potential reversal
            "TA_STOCH_BEARISH_CROSS": -0.8,
            "TA_VOLUME_BREAKOUT_BEARISH": -0.6,
            "TA_MACD_ZERO_CROSS_BEARISH": -0.7,
        }

    asset_scores = []
    for asset_symbol, signals in asset_signals.items():
        total_score = 0
        num_bullish_signals = 0
        num_bearish_signals = 0
        highest_confidence_bullish = 0
        
        for signal in signals:
            weight = 0
            if signal.signal_type.startswith("QUANT_"):
                weight = quant_signal_weights.get(signal.signal_type, 0)
            elif signal.signal_type.startswith("TA_"):
                weight = ta_signal_weights.get(signal.signal_type, 0)
            
            score_contribution = weight * signal.confidence
            total_score += score_contribution

            if weight > 0 : # Bullish signal
                num_bullish_signals +=1
                if signal.confidence > highest_confidence_bullish:
                    highest_confidence_bullish = signal.confidence
            elif weight < 0: # Bearish signal
                num_bearish_signals +=1
        
        asset_scores.append({
            "asset": asset_symbol,
            "score": total_score,
            "num_signals": len(signals),
            "num_bullish": num_bullish_signals,
            "num_bearish": num_bearish_signals,
            "max_bullish_conf": highest_confidence_bullish
        })

    if not asset_scores:
        return pd.DataFrame()

    ranked_df = pd.DataFrame(asset_scores)
    # Prioritize assets with higher scores, more bullish signals, and higher confidence
    ranked_df.sort_values(by=["score", "num_bullish", "max_bullish_conf", "num_bearish"], ascending=[False, False, False, True], inplace=True)
    return ranked_df


# --- Main Orchestration Function ---

async def run_forecast_to_portfolio_pipeline( # Changed to async def
    asset_identifiers: List[Dict[str, Any]], # New parameter: list of dicts with 'base_token_address', 'quote_token_address', 'asset_symbol'
    chain_id: int,
    period_seconds: int,
    timeframe: str, # New parameter: e.g., "daily", "hourly"
    num_top_assets_for_portfolio: int = 10,  # Increased default to 10
    mvo_objective: str = "maximize_sharpe", # or "minimize_volatility"
    risk_free_rate: float = 0.02,
    annualization_factor: int = 252 # Assuming daily data for MVO inputs
) -> Optional[Dict[str, Any]]:
    """
    Runs the full pipeline:
    0. Filters out stablecoin vs stablecoin pairs.
    1. Fetches OHLCV data from MongoDB.
    2. Generates TA and Quant signals for each asset.
    3. Ranks assets based on signals.
    4. Selects top N assets.
    5. Calculates MVO inputs.
    6. Optimizes portfolio.
    """
    # 0. Filter out stablecoin pairs
    logger.info(f"Starting pipeline with {len(asset_identifiers)} assets. Filtering out stablecoin pairs...")
    filtered_asset_identifiers = filter_non_stablecoin_pairs(asset_identifiers)
    
    if not filtered_asset_identifiers:
        logger.error("No assets remaining after filtering out stablecoin pairs.")
        return {"error": "No non-stablecoin assets available for portfolio optimization"}
    
    logger.info(f"After filtering: {len(filtered_asset_identifiers)} assets remaining for analysis")
    
    all_asset_signals: Dict[str, List[Signal]] = {}
    asset_current_prices: Dict[str, float] = {}
    ohlcv_data_dict: Dict[str, pd.DataFrame] = {} # To store fetched and processed data

    # 1. Fetch OHLCV Data and Generate TA and Quant signals
    for asset_info in filtered_asset_identifiers:
        asset_symbol = asset_info["asset_symbol"]
        base_token_address = asset_info["base_token_address"]
        quote_token_address = asset_info["quote_token_address"]

        logger.info(f"Fetching OHLCV data for {asset_symbol} ({base_token_address}/{quote_token_address}) from MongoDB...")
        raw_ohlcv_data = await get_ohlcv_from_db(
            chain_id=chain_id,
            base_token_address=base_token_address,
            quote_token_address=quote_token_address,
            period_seconds=period_seconds,
            timeframe=timeframe
        )

        if not raw_ohlcv_data:
            logger.warning(f"No OHLCV data found or fetched for {asset_symbol}. Using simulated data for testing.")
            # Generate simulated OHLCV data for testing
            simulated_data = generate_simulated_ohlcv_for_asset(asset_symbol, days=200)
            if simulated_data:
                raw_ohlcv_data = simulated_data
            else:
                logger.warning(f"Failed to generate simulated data for {asset_symbol}. Skipping.")
                continue
        
        ohlcv_df = pd.DataFrame(raw_ohlcv_data)
        if ohlcv_df.empty:
            logger.warning(f"OHLCV data for {asset_symbol} is empty after converting to DataFrame. Skipping.")
            continue

        # Rename 'time' to 'timestamp' to match expected column name
        if 'time' in ohlcv_df.columns:
            ohlcv_df.rename(columns={'time': 'timestamp'}, inplace=True)
        else:
            logger.error(f"'time' column missing in fetched OHLCV data for {asset_symbol}. Skipping.")
            continue
            
        # CRITICAL: Add 'volume' column if not present, as per MongoDB schema discussion
        if 'volume' not in ohlcv_df.columns:
            logger.warning(f"'volume' column missing for {asset_symbol}. Initializing with 0.0. Volume-based signals may be affected.")
            ohlcv_df['volume'] = 0.0
        
        ohlcv_data_dict[asset_symbol] = ohlcv_df # Store for MVO input calculation

        if ohlcv_df.empty or len(ohlcv_df) < 30: # Min data for most indicators
            logger.warning(f"Skipping {asset_symbol} due to insufficient OHLCV data ({len(ohlcv_df)} rows after fetch/conversion).")
            continue

        # Ensure 'timestamp' is int (seconds) and other columns are float
        ohlcv_df['timestamp'] = ohlcv_df['timestamp'].astype(int)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in ohlcv_df.columns: # Check if column exists (e.g. volume might have been added)
                 ohlcv_df[col] = ohlcv_df[col].astype(float)
            else:
                logger.error(f"Required column '{col}' missing in OHLCV DataFrame for {asset_symbol} even after processing. Skipping signal generation for this asset.")
                continue # Skip this asset if essential columns are still missing


        current_price = ohlcv_df['close'].iloc[-1]
        asset_current_prices[asset_symbol] = current_price
        # Use the actual base_token_address for the signal's token_address field
        signal_token_address = base_token_address

        logger.info(f"Generating TA signals for {asset_symbol}...")
        ta_signals = generate_ta_signals(
            asset_symbol=asset_symbol,
            chain_id=chain_id,
            token_address=signal_token_address, # Use base_token_address
            ohlcv_df=ohlcv_df.copy(), # Pass a copy
            current_price=current_price
        )
        
        logger.info(f"Generating Quant signals for {asset_symbol}...")
        # For quant signals, determine trading_periods_per_year based on data frequency
        trading_periods_per_year_quant = annualization_factor 
        quant_signals = generate_quant_advanced_signals(
            asset_symbol=asset_symbol,
            chain_id=chain_id,
            token_address=signal_token_address, # Use base_token_address
            ohlcv_df=ohlcv_df.copy(), # Pass a copy
            current_price=current_price,
            trading_periods_per_year=trading_periods_per_year_quant
        )
        
        all_asset_signals[asset_symbol] = ta_signals + quant_signals
        logger.info(f"Generated {len(ta_signals)} TA and {len(quant_signals)} Quant signals for {asset_symbol}.")

    if not all_asset_signals:
        logger.error("No signals generated for any asset. Cannot proceed.")
        return None

    # 2. Rank assets
    logger.info("Ranking assets based on generated signals...")
    ranked_assets_df = rank_assets_based_on_signals(all_asset_signals)
    
    if ranked_assets_df.empty:
        logger.error("Asset ranking resulted in an empty DataFrame. Cannot select assets for portfolio.")
        return None
    
    logger.info("\n--- Asset Ranking ---")
    logger.info(f"\n{ranked_assets_df.to_string()}")

    # 3. Use ALL assets for MVO (let MVO decide optimal allocation)
    all_available_assets = list(ohlcv_data_dict.keys())
    
    if not all_available_assets or len(all_available_assets) < 2:
        logger.error(f"Not enough assets with OHLCV data for MVO (need at least 2, got {len(all_available_assets)}).")
        return {
            "error": f"Not enough assets with OHLCV data for MVO (need at least 2, got {len(all_available_assets)})",
            "ranked_assets": ranked_assets_df.to_dict(orient='records'),
            "available_assets": all_available_assets,
        }
    
    logger.info(f"\nUsing ALL {len(all_available_assets)} assets for MVO optimization: {all_available_assets}")
    
    # Use all available OHLCV data for MVO
    portfolio_ohlcv_data = ohlcv_data_dict


    # 4. Calculate MVO inputs
    logger.info("\nCalculating MVO inputs for selected assets...")
    mvo_inputs = calculate_mvo_inputs(portfolio_ohlcv_data, annualization_factor=annualization_factor)

    if not mvo_inputs["expected_returns"].empty and not mvo_inputs["covariance_matrix"].empty:
        logger.info(f"Expected Returns:\n{mvo_inputs['expected_returns']}")
        logger.info(f"Covariance Matrix:\n{mvo_inputs['covariance_matrix']}")
    else:
        logger.error("Failed to calculate MVO inputs. Expected returns or covariance matrix is empty.")
        return {"error": "MVO input calculation failed", "ranked_assets": ranked_assets_df.to_dict(orient='records')}
        

    # 5. Optimize portfolio
    logger.info(f"\nOptimizing portfolio with objective: {mvo_objective}...")
    optimized_portfolio = optimize_portfolio_mvo(
        expected_returns=mvo_inputs["expected_returns"],
        covariance_matrix=mvo_inputs["covariance_matrix"],
        risk_free_rate=risk_free_rate,
        objective=mvo_objective
    )

    if optimized_portfolio:
        logger.info("\n--- Optimized Portfolio ---")
        logger.info(f"Assets with allocation: {optimized_portfolio['assets_with_allocation']} out of {optimized_portfolio['total_assets_considered']} total")
        logger.info(f"Weights:\n{optimized_portfolio['weights']}")
        logger.info(f"Expected Annual Return: {optimized_portfolio['expected_annual_return']:.4f}")
        logger.info(f"Annual Volatility: {optimized_portfolio['annual_volatility']:.4f}")
        logger.info(f"Sharpe Ratio: {optimized_portfolio['sharpe_ratio']:.4f}")
        
        # Get the assets that received allocation
        selected_assets = optimized_portfolio['weights'].index.tolist()
        
        return {
            "ranked_assets": ranked_assets_df.to_dict(orient='records'),
            "selected_for_portfolio": selected_assets,  # Assets that got non-zero allocation
            "total_assets_considered": optimized_portfolio['total_assets_considered'],
            "mvo_inputs": {
                "expected_returns": mvo_inputs["expected_returns"].to_dict(),
                "covariance_matrix": mvo_inputs["covariance_matrix"].to_dict(),
                "valid_symbols": mvo_inputs["valid_symbols"]
            },
            "optimized_portfolio": {
                "weights": optimized_portfolio['weights'].to_dict(),
                "expected_annual_return": optimized_portfolio['expected_annual_return'],
                "annual_volatility": optimized_portfolio['annual_volatility'],
                "sharpe_ratio": optimized_portfolio['sharpe_ratio'],
                "assets_with_allocation": optimized_portfolio['assets_with_allocation'],
                "total_assets_considered": optimized_portfolio['total_assets_considered']
            }
        }
    else:
        logger.error("Portfolio optimization failed.")
        return {
            "error": "Portfolio optimization failed",
            "ranked_assets": ranked_assets_df.to_dict(orient='records'),
            "available_assets": all_available_assets,
            "total_assets_considered": len(all_available_assets),
             "mvo_inputs": { # Still return MVO inputs if they were calculated
                "expected_returns": mvo_inputs["expected_returns"].to_dict() if not mvo_inputs["expected_returns"].empty else {},
                "covariance_matrix": mvo_inputs["covariance_matrix"].to_dict() if not mvo_inputs["covariance_matrix"].empty else {},
                "valid_symbols": mvo_inputs["valid_symbols"]
            }
        }

# --- Example Usage (Simulated Data) ---
def generate_simulated_ohlcv(days=200, num_assets=10) -> Dict[str, pd.DataFrame]:
    """Generates simulated OHLCV data for multiple assets."""
    all_data = {}
    base_start_price = 100
    for i in range(num_assets):
        asset_symbol = f"ASSET_{chr(65+i)}" # ASSET_A, ASSET_B, ...
        dates = pd.to_datetime([pd.Timestamp.now().normalize() - pd.Timedelta(days=x) for x in range(days)][::-1])
        
        # Simulate price data with some trend and noise
        price_changes = np.random.normal(loc=np.random.uniform(-0.001, 0.002), scale=np.random.uniform(0.01, 0.03), size=days)
        close_prices = base_start_price * (1 + price_changes).cumprod()
        
        # Ensure prices are positive
        close_prices = np.maximum(close_prices, 0.01)

        open_prices = close_prices * (1 + np.random.normal(loc=0, scale=0.005, size=days))
        high_prices = np.maximum(close_prices, open_prices) * (1 + np.random.uniform(0, 0.02, size=days))
        low_prices = np.minimum(close_prices, open_prices) * (1 - np.random.uniform(0, 0.02, size=days))
        volume = np.random.poisson(lam=100000, size=days) * np.random.uniform(0.5, 1.5, size=days)

        # Ensure OHLC consistency
        high_prices = np.maximum.reduce([open_prices, high_prices, low_prices, close_prices])
        low_prices = np.minimum.reduce([open_prices, high_prices, low_prices, close_prices])
        
        df = pd.DataFrame({
            'timestamp': dates.astype(np.int64) // 10**9, # Convert to seconds
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volume
        })
        df.set_index(pd.DatetimeIndex(dates), inplace=True) # Keep DatetimeIndex for potential use elsewhere
        all_data[asset_symbol] = df
    return all_data

def generate_simulated_ohlcv_for_asset(asset_symbol: str, days: int = 200) -> List[Dict[str, Any]]:
    """Generates simulated OHLCV data for a single asset in the format expected by the pipeline."""
    try:
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        base_start_price = 100 if "ETH" in asset_symbol.upper() else 1
        if "ETH" in asset_symbol.upper():
            base_start_price = 2000  # More realistic for ETH
        
        # Create timestamps going backwards from now
        end_date = datetime.now()
        dates = [end_date - timedelta(days=x) for x in range(days)][::-1]
        
        # Simulate price data with some trend and noise
        price_changes = np.random.normal(loc=np.random.uniform(-0.001, 0.002), scale=np.random.uniform(0.015, 0.025), size=days)
        close_prices = base_start_price * (1 + price_changes).cumprod()
        
        # Ensure prices are positive
        close_prices = np.maximum(close_prices, 0.01)

        open_prices = close_prices * (1 + np.random.normal(loc=0, scale=0.005, size=days))
        high_prices = np.maximum(close_prices, open_prices) * (1 + np.random.uniform(0, 0.02, size=days))
        low_prices = np.minimum(close_prices, open_prices) * (1 - np.random.uniform(0, 0.02, size=days))
        volume = np.random.poisson(lam=100000, size=days) * np.random.uniform(0.5, 1.5, size=days)

        # Ensure OHLC consistency
        high_prices = np.maximum.reduce([open_prices, high_prices, low_prices, close_prices])
        low_prices = np.minimum.reduce([open_prices, high_prices, low_prices, close_prices])
        
        # Convert to the format expected by the pipeline (list of dicts with 'time' key)
        ohlcv_data = []
        for i in range(days):
            ohlcv_data.append({
                'time': int(dates[i].timestamp()),
                'open': float(open_prices[i]),
                'high': float(high_prices[i]),
                'low': float(low_prices[i]),
                'close': float(close_prices[i]),
                'volume': float(volume[i])
            })
        
        logger.info(f"Generated {len(ohlcv_data)} simulated OHLCV candles for {asset_symbol}")
        return ohlcv_data
        
    except Exception as e:
        logger.error(f"Error generating simulated OHLCV data for {asset_symbol}: {e}")
        return []

async def main(): # New async main function for example usage
    logger.info("🚀 Starting main forecast to portfolio pipeline with data from MongoDB...")
    
    await connect_to_mongo()

    # Example asset identifiers (replace with actual desired assets)
    # Based on the image:
    # base_token_address: "0xb8c77482e45f1f44de1745f52c74426c631bdd52" (e.g. WETH on some chain)
    # quote_token_address: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48" (e.g. USDC on some chain)
    # period_seconds : 86400 (daily)
    # chain_id : 1
    
    # Import the correct addresses from configs
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from configs import WETH_ETHEREUM_ADDRESS, USDC_ADDRESSES, ETHEREUM_CHAIN_ID
    
    example_assets = [
        {
            "asset_symbol": "WETH-USDC", # User-defined symbol for this pair
            "base_token_address": WETH_ETHEREUM_ADDRESS,
            "quote_token_address": USDC_ADDRESSES[ETHEREUM_CHAIN_ID]
        },
        # Add a few more simulated assets for portfolio testing
        {
            "asset_symbol": "BTC-USDC",
            "base_token_address": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # WBTC
            "quote_token_address": USDC_ADDRESSES[ETHEREUM_CHAIN_ID]
        },
        {
            "asset_symbol": "LINK-USDC",
            "base_token_address": "0x514910771AF9Ca656af840dff83E8264EcF986CA",  # LINK
            "quote_token_address": USDC_ADDRESSES[ETHEREUM_CHAIN_ID]
        },
    ]
    
    chain_id_to_query = 1
    # period_seconds 86400 corresponds to 'daily' timeframe. Adjust if using other periods.
    period_seconds_to_query = 86400 
    timeframe_to_query = "daily" # Ensure this matches what's stored in DB for this period_seconds
                                 # And matches what `store_ohlcv_in_db` uses.
    
    pipeline_result = await run_forecast_to_portfolio_pipeline(
        asset_identifiers=example_assets,
        chain_id=chain_id_to_query,
        period_seconds=period_seconds_to_query,
        timeframe=timeframe_to_query,
        num_top_assets_for_portfolio=min(3, len(example_assets)), # Adjust N based on available assets
        mvo_objective="maximize_sharpe",
        annualization_factor=365 if timeframe_to_query == "daily" else (365 * 24 if timeframe_to_query == "hourly" else 252) # Adjust based on timeframe
    )

    if pipeline_result:
        if "error" in pipeline_result:
            logger.error(f"\nPipeline completed with an error: {pipeline_result['error']}")
            if "ranked_assets" in pipeline_result and isinstance(pipeline_result["ranked_assets"], list) and pipeline_result["ranked_assets"]:
                 logger.info("Asset Ranking was performed:")
                 try:
                     logger.info(pd.DataFrame(pipeline_result["ranked_assets"]).to_string())
                 except Exception as e_df:
                     logger.error(f"Could not print ranked_assets as DataFrame: {e_df}")
                     logger.info(str(pipeline_result["ranked_assets"]))

        else:
            logger.info("\n✅ Pipeline completed successfully!")
            # Detailed output is already logged within the function
            # Example:
            if pipeline_result.get("optimized_portfolio"):
                logger.info("\nFinal Portfolio Weights:")
                for asset, weight in pipeline_result.get("optimized_portfolio", {}).get("weights", {}).items():
                    logger.info(f"  {asset}: {weight:.4f}")
            else:
                logger.info("Portfolio optimization was not reached or did not return weights.")
    else:
        logger.error("\n❌ Pipeline execution failed to produce a result.")

    await close_mongo_connection()
    logger.info("Pipeline finished.")
