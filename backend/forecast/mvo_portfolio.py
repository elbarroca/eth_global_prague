import pandas as pd
import numpy as np
from scipy.optimize import minimize
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# Placeholder functions for cache management (since they don't exist in mongo_service.py)
def clear_expired_cache() -> Dict[str, int]:
    """Placeholder function for cache clearing."""
    logger.warning("Cache clearing not implemented - using placeholder function")
    return {}

def get_cache_stats() -> Dict[str, Any]:
    """Placeholder function for cache stats."""
    logger.warning("Cache stats not implemented - using placeholder function")
    return {}

def get_db():
    """Placeholder function for database connection."""
    logger.warning("Database connection not implemented - using placeholder function")
    return None

# Define ScreeningTag enum locally to avoid circular imports
class ScreeningTag(str, Enum):
    LOW_RISK = "LOW_RISK"
    MID_RISK = "MID_RISK"
    HIGH_RISK = "HIGH_RISK"
    SOLANA_ECOSYSTEM = "SOLANA_ECOSYSTEM"
    DEFI = "DEFI"
    GAMING = "GAMING"

# --- Configuration for Screening ---
# Map ScreeningTag enums to string values for the screening function
SCREENING_TAG_MAP = {
    ScreeningTag.LOW_RISK: "LOW_RISK",
    ScreeningTag.MID_RISK: "MID_RISK", 
    ScreeningTag.HIGH_RISK: "HIGH_RISK",
    ScreeningTag.SOLANA_ECOSYSTEM: "SOLANA_ECOSYSTEM",
    ScreeningTag.DEFI: "DEFI",
    ScreeningTag.GAMING: "GAMING",
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Helper Functions for MVO ---

def _calculate_portfolio_performance(weights: np.ndarray, expected_returns: pd.Series, cov_matrix: pd.DataFrame) -> Tuple[float, float]:
    """Calculates annualized portfolio return and volatility."""
    portfolio_return = np.sum(expected_returns * weights)
    portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    return portfolio_return, portfolio_volatility

def _neg_sharpe_ratio(weights: np.ndarray, expected_returns: pd.Series, cov_matrix: pd.DataFrame, risk_free_rate: float) -> float:
    """Calculates the negative Sharpe ratio (to be minimized)."""
    p_return, p_volatility = _calculate_portfolio_performance(weights, expected_returns, cov_matrix)
    if p_volatility == 0: # Avoid division by zero
        return -np.inf if (p_return - risk_free_rate) > 0 else np.inf
    return -(p_return - risk_free_rate) / p_volatility

def _portfolio_volatility(weights: np.ndarray, expected_returns: pd.Series, cov_matrix: pd.DataFrame) -> float:
    """Calculates portfolio volatility (to be minimized for min_volatility objective)."""
    # expected_returns is not used here but kept for consistent signature with _neg_sharpe_ratio if optimizer swaps objectives
    return _calculate_portfolio_performance(weights, expected_returns, cov_matrix)[1]


# --- Core Service Functions ---

def fetch_and_screen_tokens_by_tags(
    tags: List[ScreeningTag],
    max_assets_to_fetch_initially: int = 250, # How many to get from /coins/markets
    vs_currency: str = "usd",
    use_cache: bool = True,
    force_refresh: bool = False
) -> List[Dict[str, Any]]:
    """
    Fetches token data from CoinGecko and screens them based on provided tags.
    Uses MongoDB caching to reduce API calls and improve performance.
    
    Args:
        tags: List of ScreeningTag enums for filtering
        max_assets_to_fetch_initially: Maximum assets to fetch initially
        vs_currency: Target currency for market data
        use_cache: Whether to use MongoDB caching (default: True)
        force_refresh: Force refresh cache and fetch fresh data (default: False)
    
    Returns:
        List of asset details (symbol, coingecko_id, name, etc.)
    """
    # If force_refresh is True, disable cache for this call
    effective_use_cache = use_cache and not force_refresh
    
    if force_refresh:
        logger.info("🔄 Force refresh requested - bypassing cache for fresh data")
    
    try:
        # Convert ScreeningTag enums to string values for the screening function
        tag_strings = [SCREENING_TAG_MAP.get(tag, str(tag)) for tag in tags]
        
        # Use the enhanced screening function from coingecko.py with caching
        screened_coins = fetch_and_screen_tokens_by_tags(
            tags=tag_strings,
            vs_currency=vs_currency,
            max_assets_to_fetch=max_assets_to_fetch_initially,
            use_cache=effective_use_cache
        )
        
        cache_status = "cached" if effective_use_cache and not force_refresh else "fresh API"
        logger.info(f"Enhanced screening completed with {len(screened_coins)} assets ({cache_status} data).")
        
    except Exception as e:
        logger.error(f"Unexpected error during screening: {e}")
        return []

    if not screened_coins:
        logger.warning("No coins found after screening")
        return []
    
    # Convert to the expected format
    screened_assets = []
    for coin in screened_coins:
        asset_data = {
            "coingecko_id": coin.get("id"),
            "symbol": coin.get("symbol", "").upper(),
            "name": coin.get("name"),
            "current_price": coin.get("current_price"),
            "market_cap": coin.get("market_cap"),
            "volatility_7d_percentage": coin.get("price_change_percentage_7d_in_currency"),
            "categories": coin.get("categories", []),
            "matched_categories": coin.get("matched_categories", []),
            "matched_tags": coin.get("matched_tags", []),
            "data_source": "cached" if effective_use_cache and not force_refresh else "api"
        }
        
        # Only include if we have essential data
        if asset_data["coingecko_id"] and asset_data["symbol"] and asset_data["name"]:
            screened_assets.append(asset_data)
    
    logger.info(f"Screened down to {len(screened_assets)} assets based on tags: {tags}")
    return screened_assets


def calculate_mvo_inputs(
    ohlcv_data_dict: Dict[str, pd.DataFrame], # Dict of {symbol: ohlcv_df}
    annualization_factor: int = 252 # Trading days in a year
) -> Dict[str, Any]:
    """
    Calculates expected returns (annualized) and covariance matrix (annualized)
    from historical OHLCV data.
    """
    all_returns_df = pd.DataFrame()
    valid_symbols_for_mvo = []

    for symbol, df in ohlcv_data_dict.items():
        if 'close' in df.columns and not df['close'].empty:
            # Use log returns for calculations, can also use simple returns
            log_returns = np.log(df['close'] / df['close'].shift(1)).dropna()
            if not log_returns.empty:
                all_returns_df[symbol] = log_returns
                valid_symbols_for_mvo.append(symbol)
            else:
                logger.warning(f"No log returns could be calculated for {symbol}, skipping for MVO inputs.")
        else:
            logger.warning(f"Close price data missing or empty for {symbol}, skipping for MVO inputs.")
            
    if all_returns_df.empty or all_returns_df.shape[1] < 2: # Need at least two assets for covariance
        logger.error("Not enough valid assets with returns data to calculate MVO inputs.")
        return {"expected_returns": pd.Series(dtype=float), "covariance_matrix": pd.DataFrame(), "valid_symbols": []}

    # Handle potential NaNs if assets have different start dates in their history
    # Fill NaNs by propagating last valid observation forward, then back, then 0 if still NaN
    all_returns_df = all_returns_df.fillna(method='ffill').fillna(method='bfill').fillna(0)
    
    expected_returns = all_returns_df.mean() * annualization_factor
    covariance_matrix = all_returns_df.cov() * annualization_factor
    
    return {
        "expected_returns": expected_returns, # pd.Series
        "covariance_matrix": covariance_matrix, # pd.DataFrame
        "valid_symbols": valid_symbols_for_mvo # List of symbols used
    }


def optimize_portfolio_mvo(
    expected_returns: pd.Series,
    covariance_matrix: pd.DataFrame,
    risk_free_rate: float = 0.02,
    target_return: Optional[float] = None, # For efficient frontier point
    objective: str = "maximize_sharpe" # or "minimize_volatility"
) -> Optional[Dict[str, Any]]:
    """
    Performs Mean-Variance Optimization.
    Returns a dictionary with optimal weights, expected return, volatility, and Sharpe ratio.
    """
    num_assets = len(expected_returns)
    if num_assets == 0 or covariance_matrix.empty:
        logger.error("Cannot optimize: No assets or empty covariance matrix.")
        return None
    
    # Ensure consistent indexing
    assets = expected_returns.index
    covariance_matrix = covariance_matrix.loc[assets, assets]

    args = (expected_returns, covariance_matrix, risk_free_rate)
    
    # Constraints: sum of weights is 1
    constraints = ({'type': 'eq', 'fun': lambda weights: np.sum(weights) - 1})
    
    # Bounds: weights between 0 and 1 (no short selling)
    bounds = tuple((0, 1) for _ in range(num_assets))
    
    # Initial guess: equal weights
    initial_weights = np.array(num_assets * [1. / num_assets])

    optimizer_options = {'ftol': 1e-9, 'disp': False}

    if objective == "maximize_sharpe":
        opt_func = _neg_sharpe_ratio
    elif objective == "minimize_volatility":
        opt_func = _portfolio_volatility
        if target_return is not None: # Constraint for specific return if minimizing volatility
            constraints = (
                constraints, # Keep sum of weights = 1
                {'type': 'eq', 'fun': lambda weights: _calculate_portfolio_performance(weights, expected_returns, covariance_matrix)[0] - target_return}
            )
    else:
        logger.error(f"Unsupported MVO objective: {objective}")
        return None

    try:
        result = minimize(opt_func, initial_weights, args=args, method='SLSQP',
                          bounds=bounds, constraints=constraints, options=optimizer_options)
    except Exception as e:
        logger.error(f"MVO optimization failed: {e}")
        return None

    if not result.success:
        logger.warning(f"MVO optimization did not succeed: {result.message}")
        # Could attempt with different initial weights or return failure
        # For now, if it fails, we return None or could return equal weight as fallback
        return None

    optimal_weights = result.x
    # Normalize weights slightly if they are very close to sum 1 due to precision
    optimal_weights /= np.sum(optimal_weights)

    # Calculate performance of the optimized portfolio
    opt_return, opt_volatility = _calculate_portfolio_performance(optimal_weights, expected_returns, covariance_matrix)
    sharpe_ratio = (opt_return - risk_free_rate) / opt_volatility if opt_volatility > 1e-9 else 0

    return {
        "weights": pd.Series(optimal_weights, index=assets),
        "expected_annual_return": opt_return,
        "annual_volatility": opt_volatility,
        "sharpe_ratio": sharpe_ratio
    }

def generate_liquidation_suggestion(optimized_portfolio_details: Optional[Dict[str, Any]]) -> str:
    """
    Generates a simple textual suggestion for portfolio liquidation.
    """
    if not optimized_portfolio_details or not optimized_portfolio_details.get("assets"):
        return "No portfolio was constructed, so no specific liquidation strategy can be suggested at this time. Consider market conditions if you hold any assets."

    # Example:
    num_assets = len(optimized_portfolio_details["assets"])
    suggestion = f"For the {num_assets}-asset portfolio: "
    suggestion += "Consider a gradual liquidation strategy. Monitor individual asset performance against their expected contribution. "
    suggestion += "Set clear take-profit and stop-loss levels for each position. "
    suggestion += "Rebalance if asset weights deviate significantly from the optimal allocation due to price changes, or liquidate based on your overall investment horizon and market outlook. "
    
    if optimized_portfolio_details.get("sharpe_ratio", 0) < 0.5 and optimized_portfolio_details.get("sharpe_ratio") is not None:
        suggestion += "Given the portfolio's Sharpe ratio, be cautious and monitor closely for underperformance. "
    
    return suggestion

# --- Cache Management Functions ---

def get_portfolio_cache_status() -> Dict[str, Any]:
    """
    Gets comprehensive cache status for portfolio construction services.
    
    Returns:
        Dictionary with cache statistics and health information
    """
    try:
        cache_stats = get_cache_stats()
        
        # Calculate total cache health
        total_entries = sum(stats.get("total_entries", 0) for stats in cache_stats.values() if isinstance(stats, dict))
        total_valid = sum(stats.get("valid_entries", 0) for stats in cache_stats.values() if isinstance(stats, dict))
        total_expired = sum(stats.get("expired_entries", 0) for stats in cache_stats.values() if isinstance(stats, dict))
        
        cache_health = {
            "overall_health": "healthy" if total_expired < total_entries * 0.3 else "needs_cleanup",
            "total_cache_entries": total_entries,
            "valid_entries": total_valid,
            "expired_entries": total_expired,
            "cache_hit_potential": f"{(total_valid / total_entries * 100):.1f}%" if total_entries > 0 else "0%",
            "collections": cache_stats
        }
        
        logger.info(f"📊 Cache status: {total_valid}/{total_entries} valid entries ({cache_health['cache_hit_potential']} hit potential)")
        return cache_health
        
    except Exception as e:
        logger.error(f"❌ Failed to get cache status: {e}")
        return {"error": str(e), "overall_health": "unknown"}

def cleanup_portfolio_cache(force_cleanup: bool = False) -> Dict[str, Any]:
    """
    Cleans up expired cache entries for portfolio construction services.
    
    Args:
        force_cleanup: If True, clears all cache regardless of expiration
    
    Returns:
        Dictionary with cleanup results
    """
    try:
        if force_cleanup:
            logger.info("🧹 Force cleanup requested - clearing all cache entries")
            # For force cleanup, we'd need to implement a function to clear all cache
            # For now, just clear expired
            cleared_counts = clear_expired_cache()
            cleanup_type = "force_cleanup_expired_only"
        else:
            cleared_counts = clear_expired_cache()
            cleanup_type = "expired_only"
        
        total_cleared = sum(cleared_counts.values())
        
        cleanup_result = {
            "cleanup_type": cleanup_type,
            "total_entries_cleared": total_cleared,
            "collections_cleared": cleared_counts,
            "status": "success" if total_cleared >= 0 else "failed"
        }
        
        if total_cleared > 0:
            logger.info(f"🧹 Cache cleanup completed: {total_cleared} entries cleared")
        else:
            logger.info("✨ Cache is clean - no expired entries found")
        
        return cleanup_result
        
    except Exception as e:
        logger.error(f"❌ Cache cleanup failed: {e}")
        return {"error": str(e), "status": "failed"}

def refresh_screening_cache_for_tags(
    tags: List[ScreeningTag],
    vs_currency: str = "usd",
    max_assets: int = 250
) -> Dict[str, Any]:
    """
    Forces a refresh of cached screening data for specific tags.
    
    Args:
        tags: List of screening tags to refresh
        vs_currency: Target currency
        max_assets: Maximum assets to fetch
    
    Returns:
        Dictionary with refresh results
    """
    try:
        logger.info(f"🔄 Refreshing cache for tags: {tags}")
        
        # Force refresh by calling with force_refresh=True
        refreshed_assets = fetch_and_screen_tokens_by_tags(
            tags=tags,
            max_assets_to_fetch_initially=max_assets,
            vs_currency=vs_currency,
            use_cache=True,
            force_refresh=True
        )
        
        refresh_result = {
            "tags_refreshed": [str(tag) for tag in tags],
            "assets_found": len(refreshed_assets),
            "vs_currency": vs_currency,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Cache refresh completed: {len(refreshed_assets)} assets for tags {tags}")
        return refresh_result
        
    except Exception as e:
        logger.error(f"❌ Cache refresh failed for tags {tags}: {e}")
        return {
            "tags_refreshed": [str(tag) for tag in tags],
            "error": str(e),
            "status": "failed",
            "timestamp": datetime.now().isoformat()
        }

def get_cache_recommendations() -> List[str]:
    """
    Provides recommendations for cache management based on current cache state.
    
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    try:
        cache_status = get_portfolio_cache_status()
        
        if cache_status.get("overall_health") == "needs_cleanup":
            recommendations.append("🧹 Consider running cache cleanup - high number of expired entries detected")
        
        total_entries = cache_status.get("total_cache_entries", 0)
        if total_entries == 0:
            recommendations.append("📦 Cache is empty - first API calls will populate cache for better performance")
        elif total_entries > 1000:
            recommendations.append("📊 Large cache detected - consider periodic cleanup to maintain performance")
        
        valid_entries = cache_status.get("valid_entries", 0)
        if valid_entries < total_entries * 0.5 and total_entries > 0:
            recommendations.append("⏰ Many cache entries are expired - cleanup recommended")
        
        if not recommendations:
            recommendations.append("✅ Cache is in good health - no immediate action needed")
        
    except Exception as e:
        recommendations.append(f"❌ Unable to analyze cache health: {str(e)}")
    
    return recommendations 