# backend/forecast/main_pipeline.py
import pandas as pd
import logging
from typing import List, Dict, Any, Optional, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Signal, ForecastSignalRecord
from services.mongo_service import get_ohlcv_from_db, store_forecast_signals
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
    all_available_assets: Optional[List[str]] = None,  # NEW: List of all assets to ensure comprehensive scoring
    quant_signal_weights: Optional[Dict[str, float]] = None,
    ta_signal_weights: Optional[Dict[str, float]] = None
) -> pd.DataFrame:
    """
    Ranks assets based on a weighted score of their generated signals.
    Now ensures ALL assets get scored, even if they have no signals.
    """
    if quant_signal_weights is None:
        # Enhanced weights for quant signals with more granular scoring
        quant_signal_weights = {
            # Strong bullish signals
            "QUANT_FOURIER_MEAN_REVERSION_BUY": 2.0,
            "QUANT_MEANREVERT_OVEREXTENDED_LOW": 1.8,
            "QUANT_MOMENTUM_HIGH_SHARPE": 1.5,
            "QUANT_FOURIER_EXTREME_DEVIATION_LOW": 1.4,
            "QUANT_REGIME_STRONG_UPTREND": 1.3,
            "QUANT_DISTRIBUTION_POSITIVE_SKEW_OPPORTUNITY": 1.0,
            
            # Moderate bullish signals
            "QUANT_VOL_REGIME_LOW": 0.8,
            "QUANT_LIQUIDITY_BULLISH_VPT_DIVERGENCE": 0.7,
            "QUANT_VOL_RISK_PREMIUM_LOW": 0.6,
            "QUANT_LIQUIDITY_VOLUME_SPIKE": 0.5,
            
            # Strong bearish/risk signals
            "QUANT_FOURIER_MEAN_REVERSION_SELL": -2.0,
            "QUANT_MEANREVERT_OVEREXTENDED_HIGH": -1.8,
            "QUANT_CVAR95_HIGH_RISK": -1.7,
            "QUANT_MOMENTUM_NEGATIVE_SHARPE": -1.5,
            "QUANT_FOURIER_EXTREME_DEVIATION_HIGH": -1.4,
            "QUANT_REGIME_STRONG_DOWNTREND": -1.3,
            "QUANT_DISTRIBUTION_NEGATIVE_SKEW_RISK": -1.2,
            "QUANT_DISTRIBUTION_HIGH_KURTOSIS_RISK": -1.1,
            
            # Moderate bearish signals
            "QUANT_GARCH_HIGH_VOL_FORECAST": -1.0,
            "QUANT_VOL_REGIME_HIGH": -0.9,
            "QUANT_LIQUIDITY_BEARISH_VPT_DIVERGENCE": -0.8,
            "QUANT_VOL_RISK_PREMIUM_HIGH": -0.7,
            "QUANT_MOMENTUM_BEARISH_DIVERGENCE": -0.6,
            "QUANT_LIQUIDITY_VOLUME_DROUGHT": -0.5,
        }
        
    if ta_signal_weights is None:
        # Enhanced weights for TA signals
        ta_signal_weights = {
            # Strong bullish TA signals
            "TA_MACD_CROSS_BULLISH": 1.5,
            "TA_MA_CROSS_BULLISH": 1.3,
            "TA_STOCH_BULLISH_CROSS": 1.0,
            "TA_RSI_OVERSOLD": 0.9,
            "TA_MACD_BULLISH_MOMENTUM": 0.8,
            "TA_MACD_ZERO_CROSS_BULLISH": 0.8,
            "TA_BB_BREAK_LOWER": 0.7,  # Potential reversal
            "TA_VOLUME_BREAKOUT_BULLISH": 0.6,
            "TA_PRICE_NEAR_RECENT_LOW": 0.5,  # Potential bounce
            
            # Strong bearish TA signals
            "TA_MACD_CROSS_BEARISH": -1.5,
            "TA_MA_CROSS_BEARISH": -1.3,
            "TA_STOCH_BEARISH_CROSS": -1.0,
            "TA_RSI_OVERBOUGHT": -0.9,
            "TA_MACD_BEARISH_MOMENTUM": -0.8,
            "TA_MACD_ZERO_CROSS_BEARISH": -0.8,
            "TA_BB_BREAK_UPPER": -0.7,  # Potential reversal
            "TA_VOLUME_BREAKOUT_BEARISH": -0.6,
            "TA_PRICE_NEAR_RECENT_HIGH": -0.5,  # Potential pullback
        }

    # Ensure we score ALL assets, not just those with signals
    assets_to_score = set()
    if all_available_assets:
        assets_to_score.update(all_available_assets)
    assets_to_score.update(asset_signals.keys())
    
    asset_scores = []
    for asset_symbol in assets_to_score:
        signals = asset_signals.get(asset_symbol, [])  # Empty list if no signals
        
        total_score = 0
        weighted_confidence_sum = 0
        total_weight_abs = 0
        num_bullish_signals = 0
        num_bearish_signals = 0
        highest_confidence_bullish = 0
        highest_confidence_bearish = 0
        signal_diversity_score = 0
        
        # Track signal types for diversity scoring
        quant_signal_types = set()
        ta_signal_types = set()
        
        for signal in signals:
            weight = 0
            if signal.signal_type.startswith("QUANT_"):
                weight = quant_signal_weights.get(signal.signal_type, 0)
                quant_signal_types.add(signal.signal_type)
            elif signal.signal_type.startswith("TA_"):
                weight = ta_signal_weights.get(signal.signal_type, 0)
                ta_signal_types.add(signal.signal_type)
            
            # Calculate score contribution with confidence weighting
            confidence = signal.confidence if signal.confidence is not None else 0.5
            score_contribution = weight * confidence
            total_score += score_contribution
            
            # Track weighted confidence and total weights for normalization
            weighted_confidence_sum += abs(weight) * confidence
            total_weight_abs += abs(weight)

            if weight > 0:  # Bullish signal
                num_bullish_signals += 1
                if confidence > highest_confidence_bullish:
                    highest_confidence_bullish = confidence
            elif weight < 0:  # Bearish signal
                num_bearish_signals += 1
                if confidence > highest_confidence_bearish:
                    highest_confidence_bearish = confidence
        
        # Calculate signal diversity bonus (having both quant and TA signals is good)
        signal_diversity_score = len(quant_signal_types) * 0.1 + len(ta_signal_types) * 0.1
        if len(quant_signal_types) > 0 and len(ta_signal_types) > 0:
            signal_diversity_score += 0.2  # Bonus for having both types
        
        # Normalize score by total absolute weight to prevent bias toward assets with more signals
        normalized_score = total_score
        if total_weight_abs > 0:
            # Add a small diversity bonus to the normalized score
            normalized_score = total_score + signal_diversity_score
        
        # Calculate average confidence across all signals
        avg_confidence = weighted_confidence_sum / total_weight_abs if total_weight_abs > 0 else 0
        
        # Calculate signal quality score (balance of bullish vs bearish)
        signal_balance = num_bullish_signals - num_bearish_signals
        signal_quality = (highest_confidence_bullish - highest_confidence_bearish) * 0.5
        
        asset_scores.append({
            "asset": asset_symbol,
            "score": round(normalized_score, 6),
            "num_signals": len(signals),
            "num_bullish": num_bullish_signals,
            "num_bearish": num_bearish_signals,
            "max_bullish_conf": round(highest_confidence_bullish, 4),
            "max_bearish_conf": round(highest_confidence_bearish, 4),
            "avg_confidence": round(avg_confidence, 4),
            "signal_balance": signal_balance,
            "signal_quality": round(signal_quality, 4),
            "signal_diversity": round(signal_diversity_score, 4),
            "quant_signals": len(quant_signal_types),
            "ta_signals": len(ta_signal_types)
        })

    if not asset_scores:
        return pd.DataFrame()

    ranked_df = pd.DataFrame(asset_scores)
    
    # Enhanced sorting: prioritize score, then signal quality, then diversity
    ranked_df.sort_values(
        by=["score", "signal_quality", "signal_diversity", "avg_confidence", "num_bullish", "max_bullish_conf"], 
        ascending=[False, False, False, False, False, False], 
        inplace=True
    )
    
    # Reset index after sorting
    ranked_df.reset_index(drop=True, inplace=True)
    
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
    annualization_factor: int = 252, # Assuming daily data for MVO inputs
    target_return_param: Optional[float] = None # Added this parameter
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
        
        ohlcv_candles_list = []
        if raw_ohlcv_data and "data" in raw_ohlcv_data:
            ohlcv_candles_list = raw_ohlcv_data["data"]
            if not ohlcv_candles_list: # Check if the list of candles is empty
                logger.warning(f"OHLCV candle list for {asset_symbol} from DB is empty. Skipping.")
                continue
        else:
            logger.warning(f"No OHLCV data or 'data' field not found in DB response for {asset_symbol}. Skipping.")
            continue
        
        ohlcv_df = pd.DataFrame(ohlcv_candles_list)
        if ohlcv_df.empty: # Should be redundant now if ohlcv_candles_list was not empty, but good as a safeguard
            logger.warning(f"DataFrame for {asset_symbol} is empty even after fetching candle list. Skipping.")
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

        min_data_points = 50  # Updated to match forecast modules requirement
        if ohlcv_df.empty or len(ohlcv_df) < min_data_points:
            logger.warning(f"Skipping {asset_symbol} due to insufficient OHLCV data ({len(ohlcv_df)} rows after fetch/conversion). Required at least {min_data_points}.")
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
            base_token_address=signal_token_address, # Use base_token_address
            ohlcv_df=ohlcv_df.copy(), # Pass a copy
            current_price=current_price
        )
        
        logger.info(f"Generating Quant signals for {asset_symbol}...")
        # For quant signals, determine trading_periods_per_year based on data frequency
        trading_periods_per_year_quant = annualization_factor 
        quant_signals = generate_quant_advanced_signals(
            asset_symbol=asset_symbol,
            chain_id=chain_id,
            base_token_address=signal_token_address, # Use base_token_address
            ohlcv_df=ohlcv_df.copy(), # Pass a copy
            current_price=current_price,
            trading_periods_per_year=trading_periods_per_year_quant
        )
        
        all_asset_signals[asset_symbol] = ta_signals + quant_signals
        logger.info(f"Generated {len(ta_signals)} TA and {len(quant_signals)} Quant signals for {asset_symbol}.")

    if not all_asset_signals:
        logger.error("No signals generated for any asset. Cannot proceed.")
        return None

    # Store generated signals
    signals_to_save_to_db: List[ForecastSignalRecord] = []
    current_forecast_time = int(pd.Timestamp.now(tz='utc').timestamp())
    for asset_symbol, signals_list in all_asset_signals.items():
        last_ohlcv_timestamp = 0
        if asset_symbol in ohlcv_data_dict and not ohlcv_data_dict[asset_symbol].empty:
            last_ohlcv_timestamp = int(ohlcv_data_dict[asset_symbol]['timestamp'].iloc[-1])
            
        for sig in signals_list:
            signals_to_save_to_db.append(
                ForecastSignalRecord(
                    asset_symbol=sig.asset_symbol,
                    chain_id=sig.chain_id if sig.chain_id is not None else chain_id, # Ensure chain_id is present
                    base_token_address=sig.base_token_address if sig.base_token_address is not None else "N/A", # Ensure base_token_address
                    signal_type=sig.signal_type,
                    timeframe=timeframe, # Added timeframe
                    confidence=sig.confidence,
                    details=sig.details,
                    forecast_timestamp=current_forecast_time, # Timestamp of when this forecast batch was run
                    ohlcv_data_timestamp=last_ohlcv_timestamp, # Timestamp of the data used
                )
            )
    
    if signals_to_save_to_db:
        logger.info(f"Attempting to store {len(signals_to_save_to_db)} generated forecast signals to DB...")
        try:
            await store_forecast_signals(signals_to_save_to_db)
            logger.info("Successfully stored forecast signals.")
        except Exception as e:
            logger.error(f"Error storing forecast signals: {e}", exc_info=True)
            # Continue pipeline even if signal storage fails for now

    # 2. Rank assets - now includes ALL assets, even those without signals
    logger.info("Ranking assets based on generated signals...")
    all_available_asset_symbols = list(ohlcv_data_dict.keys())  # All assets with OHLCV data
    ranked_assets_df = rank_assets_based_on_signals(
        all_asset_signals, 
        all_available_assets=all_available_asset_symbols
    )
    
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
    mvo_inputs = calculate_mvo_inputs(
        portfolio_ohlcv_data, # Pass portfolio_ohlcv_data positionally
        ranked_assets_df=ranked_assets_df,
        annualization_factor=annualization_factor
    )

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
        historical_period_returns_df=mvo_inputs.get("historical_period_returns_df"),
        risk_free_rate=risk_free_rate,
        annualization_factor=annualization_factor,
        objective=mvo_objective,
        target_return=target_return_param
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
                "expected_returns": mvo_inputs["expected_returns"].to_dict() if not bool(mvo_inputs["expected_returns"].empty) else {},
                "covariance_matrix": mvo_inputs["covariance_matrix"].to_dict() if not bool(mvo_inputs["covariance_matrix"].empty) else {},
                "valid_symbols": mvo_inputs["valid_symbols"]
            }
        }

