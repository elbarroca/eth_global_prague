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
    _, p_volatility = _calculate_portfolio_performance(weights, expected_returns, cov_matrix)
    return p_volatility

def _portfolio_return(weights: np.ndarray, expected_returns: pd.Series, cov_matrix: pd.DataFrame, risk_free_rate: float = None) -> float:
    """Calculates negative portfolio return (to be minimized for maximize_return objective)."""
    # cov_matrix and risk_free_rate are not used here but kept for consistent signature
    p_return, _ = _calculate_portfolio_performance(weights, expected_returns, cov_matrix)
    return -p_return # We minimize the negative return

def _calculate_max_drawdown(portfolio_period_returns: pd.Series) -> float:
    """
    Calculates the maximum drawdown from a series of portfolio period returns.
    Returns drawdown as a positive value (e.g., 0.2 for 20% drawdown).
    """
    if portfolio_period_returns.empty:
        return 0.0
    cumulative_returns = (1 + portfolio_period_returns).cumprod()
    peak = cumulative_returns.expanding(min_periods=1).max()
    drawdown = (cumulative_returns - peak) / peak
    max_drawdown = abs(drawdown.min()) # Max drawdown is the minimum (most negative) value in the drawdown series
    return float(max_drawdown) if pd.notna(max_drawdown) else 0.0

def _calculate_sortino_ratio(portfolio_period_returns: pd.Series, annualized_risk_free_rate: float, annualization_factor: int) -> float:
    """
    Calculates the Sortino ratio.
    """
    if portfolio_period_returns.empty or annualization_factor == 0:
        return 0.0

    # Annualized portfolio return
    annualized_portfolio_return = (portfolio_period_returns.mean() * annualization_factor)

    # Per-period risk-free rate
    period_risk_free_rate = annualized_risk_free_rate / annualization_factor
    
    # Target downside returns
    target_downside_returns = portfolio_period_returns[portfolio_period_returns < period_risk_free_rate]
    
    if target_downside_returns.empty: # No returns below the target
        # If mean return > RFR, Sortino is effectively infinite (or very large positive).
        # If mean return <= RFR, Sortino is negative or zero.
        # For simplicity, return a large number if returns are good, or 0 if not.
        return 100.0 if annualized_portfolio_return > annualized_risk_free_rate else 0.0


    # Annualized downside deviation
    downside_deviation = np.std(target_downside_returns) * np.sqrt(annualization_factor)
    
    if downside_deviation == 0:
         # If no downside deviation and return > RFR, Sortino is effectively infinite.
        return 100.0 if annualized_portfolio_return > annualized_risk_free_rate else 0.0

    sortino_ratio = (annualized_portfolio_return - annualized_risk_free_rate) / downside_deviation
    return float(sortino_ratio) if pd.notna(sortino_ratio) else 0.0


def calculate_mvo_inputs(
    ohlcv_data: Dict[str, pd.DataFrame], # Assuming this was the original first arg
    ranked_assets_df: Optional[pd.DataFrame] = None, # Add this new argument
    annualization_factor: int = 365 # Trading days in a year
) -> Dict[str, Any]:
    """
    Calculates expected returns (annualized) and covariance matrix (annualized)
    from historical OHLCV data.
    """
    returns_dict = {}
    valid_symbols_for_mvo = []

    for symbol, df in ohlcv_data.items():
        if 'close' in df.columns and not df['close'].empty:
            # Use log returns for calculations, can also use simple returns
            log_returns = np.log(df['close'] / df['close'].shift(1)).dropna()
            if not log_returns.empty:
                returns_dict[symbol] = log_returns
                valid_symbols_for_mvo.append(symbol)
            else:
                logger.warning(f"No log returns could be calculated for {symbol}, skipping for MVO inputs.")
        else:
            logger.warning(f"Close price data missing or empty for {symbol}, skipping for MVO inputs.")
            
    if not returns_dict or len(returns_dict) < 2: # Need at least two assets for covariance
        logger.error("Not enough valid assets with returns data to calculate MVO inputs.")
        return {"expected_returns": pd.Series(dtype=float), "covariance_matrix": pd.DataFrame(), "valid_symbols": [], "historical_period_returns_df": pd.DataFrame()}

    # Use pd.concat instead of iteratively assigning columns to avoid fragmentation
    all_returns_df = pd.concat(returns_dict, axis=1)
    all_returns_df = all_returns_df.ffill().bfill().fillna(0)
    
    expected_returns = all_returns_df.mean() * annualization_factor
    covariance_matrix = all_returns_df.cov() * annualization_factor
    
    return {
        "expected_returns": expected_returns, # pd.Series
        "covariance_matrix": covariance_matrix, # pd.DataFrame
        "valid_symbols": valid_symbols_for_mvo, # List of symbols used
        "historical_period_returns_df": all_returns_df # Added for CVaR calculation
    }

def optimize_portfolio_mvo(
    expected_returns: pd.Series,
    covariance_matrix: pd.DataFrame,
    historical_period_returns_df: Optional[pd.DataFrame] = None, # Added for CVaR
    risk_free_rate: float = 0.02,
    annualization_factor: int = 365, # Added for Sortino Ratio
    target_return: Optional[float] = None, # For efficient frontier point
    objective: str = "maximize_sharpe" # or "minimize_volatility" or "maximize_return"
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
            logger.info(f"Applying target return constraint for minimize_volatility: {target_return}")
            constraints = (
                constraints, # Keep sum of weights = 1
                {'type': 'eq', 'fun': lambda weights: _calculate_portfolio_performance(weights, expected_returns, covariance_matrix)[0] - target_return}
            )
        else:
            logger.info("No target return specified for minimize_volatility. Minimizing global volatility.")
    elif objective == "maximize_return":
        # For maximizing return with long-only, sum-to-one weights, it's putting 100% on the highest expected return asset.
        # However, to fit into the optimizer framework or allow for diversification if other constraints were present,
        # we can use the optimizer. Or, more simply, just pick the best one.
        # Using optimizer for consistency and if other constraints might be added later.
        opt_func = _portfolio_return
        # If a target_return is specified with maximize_return, it could imply a floor,
        # but standard MVO maximize_return doesn't typically use it this way.
        # For now, we'll ignore target_return for maximize_return as it aims for the highest possible.
    else:
        logger.error(f"Unsupported MVO objective: {objective}")
        return None

    try:
        # Special handling for maximize_return to simplify and guarantee 100% on highest return asset
        # if no other complex constraints are in play.
        if objective == "maximize_return" and not (isinstance(constraints, tuple) and len(constraints) > 1): # only basic sum-to-1 constraint
            best_asset_idx = np.argmax(expected_returns.values)
            optimal_weights = np.zeros(num_assets)
            optimal_weights[best_asset_idx] = 1.0
            result_success = True
            result_message = "Directly assigned 100% to highest expected return asset."
            logger.info(result_message)
        else:
            optimization_result = minimize(opt_func, initial_weights, args=args, method='SLSQP',
                                bounds=bounds, constraints=constraints, options=optimizer_options)
            result_success = optimization_result.success
            optimal_weights = optimization_result.x if result_success else initial_weights
            result_message = optimization_result.message if not result_success else "Optimization successful."

    except Exception as e:
        logger.error(f"MVO optimization failed: {e}")
        return None

    if not result_success:
        logger.warning(f"MVO optimization did not succeed: {result_message}")
        # Fallback for maximize_return if optimizer fails for some reason
        if objective == "maximize_return":
            logger.warning("Optimizer failed for 'maximize_return', falling back to assigning 100% to highest expected return asset.")
            best_asset_idx = np.argmax(expected_returns.values)
            optimal_weights = np.zeros(num_assets)
            optimal_weights[best_asset_idx] = 1.0
        else: # For other objectives, if optimizer fails, returning None or initial_weights might be options
             return None

    # Normalize weights to ensure they sum to exactly 1.0 and handle precision issues
    if np.sum(optimal_weights) > 1e-6 : # Avoid division by zero if all weights are zero
        optimal_weights = optimal_weights / np.sum(optimal_weights)
    else: # If all weights are somehow zero (e.g. optimizer failure and bad initial guess)
        logger.warning("All optimal weights are zero or near zero. Optimizer likely failed to find a solution. Returning None.")
        return None # Or handle by assigning equal weights, or 100% to highest return asset as a last resort.
                    # For now, returning None to indicate failure more clearly.

    # Create weights series
    weights_series = pd.Series(optimal_weights, index=assets)
    
    # Filter out assets with zero or near-zero weights (less than 0.1%)
    min_weight_threshold = 0.001  # 0.1%
    non_zero_weights = weights_series[weights_series >= min_weight_threshold]
    
    if non_zero_weights.empty and not weights_series.empty: # If all are < threshold but not all zero initially
        logger.warning(f"All optimized weights are below threshold {min_weight_threshold}. Assigning 100% to asset with highest ER if objective is not minimize_volatility, or highest weight from optimizer otherwise.")
        if objective != "minimize_volatility" and not expected_returns.empty:
             best_asset = expected_returns.idxmax()
             non_zero_weights = pd.Series([1.0], index=[best_asset])
        elif not weights_series.empty: # Fallback to the one with the largest weight from optimizer
            best_asset_from_opt = weights_series.idxmax()
            non_zero_weights = pd.Series([1.0], index=[best_asset_from_opt])
        else: # Should not happen if initial check passed
            logger.error("Cannot determine fallback asset as input series are empty.")
            return None
            
    elif non_zero_weights.empty and weights_series.empty: # Should be caught earlier
        logger.error("Optimizer returned empty weights series and initial weights were also empty.")
        return None

    # Renormalize the non-zero weights to sum to 1.0
    if not non_zero_weights.empty:
        non_zero_weights = non_zero_weights / non_zero_weights.sum()
    else: # Should ideally not happen if fallback logic above is robust
        logger.warning("Non_zero_weights became empty even after fallback, this indicates an issue.")
        # As a last resort, if expected_returns is not empty, pick the best one.
        if not expected_returns.empty:
            best_asset = expected_returns.idxmax()
            non_zero_weights = pd.Series([1.0], index=[best_asset])
        else: # Cannot proceed
            return None

    logger.info(f"Portfolio optimization result: {len(non_zero_weights)} assets with non-zero weights (filtered from {len(assets)} total assets)")
    logger.info(f"Non-zero weights sum: {non_zero_weights.sum():.6f}")

    # Calculate performance using the filtered weights
    # Create a full weights array for performance calculation
    full_weights = pd.Series(0.0, index=assets) # Use original 'assets' index for full dimensionality
    full_weights.loc[non_zero_weights.index] = non_zero_weights # Populate with optimized, filtered, renormalized weights
    
    opt_return, opt_volatility = _calculate_portfolio_performance(full_weights.values, expected_returns, covariance_matrix)
    sharpe_ratio = (opt_return - risk_free_rate) / opt_volatility if opt_volatility > 1e-9 else 0

    # Initialize additional metrics
    max_drawdown_val = 0.0
    sortino_ratio_val = 0.0
    calmar_ratio_val = 0.0
    portfolio_historical_returns = pd.Series(dtype=float)

    if historical_period_returns_df is not None and not historical_period_returns_df.empty:
        # Ensure historical returns columns match the assets in full_weights
        # Align historical_period_returns_df columns with 'assets' (index of expected_returns and columns of cov_matrix)
        aligned_returns_df = historical_period_returns_df.reindex(columns=assets).fillna(0.0)
        
        if not aligned_returns_df.empty and not aligned_returns_df.isnull().all().all():
            portfolio_historical_returns = aligned_returns_df.dot(full_weights) # Calculate portfolio historical returns
            
            if not portfolio_historical_returns.empty and not portfolio_historical_returns.isnull().all():
                max_drawdown_val = _calculate_max_drawdown(portfolio_historical_returns)
                sortino_ratio_val = _calculate_sortino_ratio(portfolio_historical_returns, risk_free_rate, annualization_factor)
                
                if max_drawdown_val > 1e-9: # Avoid division by zero for Calmar
                    calmar_ratio_val = opt_return / max_drawdown_val
                else: # If max drawdown is zero (e.g. all positive returns), Calmar can be very high or undefined
                    calmar_ratio_val = 100.0 if opt_return > 0 else 0.0

    # Calculate CVaR (e.g., 95% Historical CVaR)
    cvar_95 = None
    if not portfolio_historical_returns.empty and not portfolio_historical_returns.isnull().all():
        confidence_level = 0.95
        var_95 = portfolio_historical_returns.quantile(1 - confidence_level)
        cvar_95_val = portfolio_historical_returns[portfolio_historical_returns <= var_95].mean()
        if pd.notna(cvar_95_val):
            cvar_95 = round(cvar_95_val, 6)
            logger.info(f"Calculated CVaR (95%): {cvar_95}")
        else:
            logger.warning("CVaR calculation resulted in NaN, possibly due to insufficient data points beyond VaR.")
    else:
        logger.warning("Portfolio historical returns are empty or all NaN, cannot calculate CVaR.")

    # Filtered covariance matrix for assets in the portfolio
    optimized_covariance_matrix = pd.DataFrame()
    if not non_zero_weights.empty:
        optimized_covariance_matrix = covariance_matrix.loc[non_zero_weights.index, non_zero_weights.index]


    return {
        "weights": non_zero_weights.to_dict(),  # Return non-zero weights as dict
        "expected_annual_return": round(opt_return, 6),
        "annual_volatility": round(opt_volatility, 6),
        "sharpe_ratio": round(sharpe_ratio, 6),
        "cvar_95_historical_period": cvar_95,
        "max_drawdown": round(max_drawdown_val, 6),
        "sortino_ratio": round(sortino_ratio_val, 6),
        "calmar_ratio": round(calmar_ratio_val, 6),
        "covariance_matrix_optimized": optimized_covariance_matrix.to_dict(orient='index'), # Cov matrix for optimized portfolio
        "total_assets_considered": len(assets),
        "assets_with_allocation": len(non_zero_weights)
    }
