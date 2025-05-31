import pandas as pd
import numpy as np
from scipy.optimize import minimize
import logging
from typing import Dict, Any, Optional, Tuple
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def _portfolio_volatility(weights: np.ndarray, expected_returns: pd.Series, cov_matrix: pd.DataFrame, risk_free_rate: float = None) -> float:
    """Calculates portfolio volatility (to be minimized for min_volatility objective)."""
    # expected_returns and risk_free_rate are not used here but kept for consistent signature with _neg_sharpe_ratio
    return _calculate_portfolio_performance(weights, expected_returns, cov_matrix)[1]

def calculate_mvo_inputs(
    ohlcv_data: Dict[str, pd.DataFrame], # Assuming this was the original first arg
    ranked_assets_df: Optional[pd.DataFrame] = None, # Add this new argument
    annualization_factor: int = 252 # Trading days in a year
) -> Dict[str, Any]:
    """
    Calculates expected returns (annualized) and covariance matrix (annualized)
    from historical OHLCV data.
    """
    all_returns_df = pd.DataFrame()
    valid_symbols_for_mvo = []

    for symbol, df in ohlcv_data.items():
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

    all_returns_df = all_returns_df.ffill().bfill().fillna(0)
    
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
        return None

    optimal_weights = result.x
    # Normalize weights to ensure they sum to exactly 1.0
    optimal_weights /= np.sum(optimal_weights)
    
    # Create weights series
    weights_series = pd.Series(optimal_weights, index=assets)
    
    # Filter out assets with zero or near-zero weights (less than 0.1%)
    min_weight_threshold = 0.001  # 0.1%
    non_zero_weights = weights_series[weights_series >= min_weight_threshold]
    
    if non_zero_weights.empty:
        logger.warning("All optimized weights are below threshold. Returning top asset with 100% weight.")
        # Fallback: give 100% to the asset with highest expected return
        best_asset = expected_returns.idxmax()
        non_zero_weights = pd.Series([1.0], index=[best_asset])
    else:
        # Renormalize the non-zero weights to sum to 1.0
        non_zero_weights = non_zero_weights / non_zero_weights.sum()
    
    logger.info(f"Portfolio optimization result: {len(non_zero_weights)} assets with non-zero weights (filtered from {len(assets)} total assets)")
    logger.info(f"Non-zero weights sum: {non_zero_weights.sum():.6f}")

    # Calculate performance using the filtered weights
    # Create a full weights array for performance calculation
    full_weights = pd.Series(0.0, index=assets)
    full_weights.loc[non_zero_weights.index] = non_zero_weights
    
    opt_return, opt_volatility = _calculate_portfolio_performance(full_weights.values, expected_returns, covariance_matrix)
    sharpe_ratio = (opt_return - risk_free_rate) / opt_volatility if opt_volatility > 1e-9 else 0

    return {
        "weights": non_zero_weights,  # Only return non-zero weights
        "expected_annual_return": round(opt_return, 6),
        "annual_volatility": round(opt_volatility, 6),
        "sharpe_ratio": round(sharpe_ratio, 6),
        "total_assets_considered": len(assets),
        "assets_with_allocation": len(non_zero_weights)
    }
