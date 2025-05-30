import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Literal, Union, Tuple
from pydantic import BaseModel, Field
# from scipy.stats import norm # Not strictly needed for historical VaR/CVaR as implemented
import logging
import time
from models import Signal, OHLCVDataPoint # Assuming Signal model and OHLCVDataPoint
from arch import arch_model

# Fourier Signal Configuration
class FourierSignalConfig(BaseModel):
    """Configuration for Fourier-based signal generation using statistical arbitrage methodology"""
    price_col_to_use: str = Field(default="close", description="Price column to use for analysis")
    detrend_remove_fraction: float = Field(default=0.05, description="Alpha parameter for Fourier detrending (e.g., 0.05)")
    sma_window: int = Field(default=20, description="SMA window for detrended series local mean")
    
    # Legacy parameters for backward compatibility (not used in stat arb method)
    n_std_dev_bands: float = Field(default=1.5, description="Legacy parameter - not used in stat arb")
    n_components_short: int = Field(default=3, description="Legacy parameter - not used in stat arb") 
    n_components_long: int = Field(default=1, description="Legacy parameter - not used in stat arb")
    rolling_band_window: int = Field(default=30, description="Legacy parameter - not used in stat arb")

SignalAction = Literal["Buy", "Sell", "Hold", "ShortInitiate", "LongInitiate"]

# Helper function to convert numpy types to Python native types for JSON serialization
def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

# --- Helper Functions ---

def calculate_log_returns(series: pd.Series) -> pd.Series:
    """Calculates log returns, handling potential zeros or negative prices if any."""
    assert isinstance(series, pd.Series), "Input 'series' must be a pandas Series."
    series_positive = series[series > 0]
    if series_positive.empty:
        logging.warning("Log returns calculation: No positive prices found in series.")
        return pd.Series(dtype=float)
    if len(series_positive) < 2:
        logging.warning("Log returns calculation: Not enough positive prices (need at least 2) to calculate returns.")
        return pd.Series(dtype=float)
    return np.log(series_positive / series_positive.shift(1))

def calculate_simple_returns(series: pd.Series) -> pd.Series:
    """Calculates simple percentage returns."""
    assert isinstance(series, pd.Series), "Input 'series' must be a pandas Series."
    if len(series) < 2:
        logging.warning("Simple returns calculation: Not enough data (need at least 2) to calculate returns.")
        return pd.Series(dtype=float)
    return series.pct_change()

def calculate_annualized_realized_volatility(
    returns_series: pd.Series,
    window: int = 20,
    trading_periods_per_year: int = 365 # Assuming daily data frequency leading to daily returns
) -> pd.Series:
    """
    Calculates annualized rolling realized volatility from a series of returns.
    `returns_series` should be returns for the period matching the desired output frequency (e.g., daily returns for daily vol).
    """
    assert isinstance(returns_series, pd.Series), "Input 'returns_series' must be a pandas Series."
    assert isinstance(window, int) and window > 0, "Volatility window must be a positive integer."
    assert isinstance(trading_periods_per_year, int) and trading_periods_per_year > 0, "Trading periods per year must be positive."

    if returns_series.dropna().empty or len(returns_series.dropna()) < window:
        logging.debug(f"Not enough data points ({len(returns_series.dropna())}) for rolling volatility with window {window}.")
        # Return a series of NaNs of the same length as input if not enough data for full window calculation
        return pd.Series(np.nan, index=returns_series.index, dtype=float)

    rolling_std_dev = returns_series.rolling(window=window, min_periods=max(1, window // 2)).std() # Ensure some data even if less than window
    annualized_vol = rolling_std_dev * np.sqrt(trading_periods_per_year)
    return annualized_vol


# --- Fourier Analysis Functions ---

def fourier_detrend(
    price_series: pd.Series,
    remove_fraction: float = 0.05
) -> Optional[pd.Series]:
    """
    Detrends a price series using Fourier analysis by removing low-frequency components.
    Implements the methodology from "Spectral Decomposition and Statistical Arbitrage" paper.
    
    Args:
        price_series: Price time series to detrend
        remove_fraction: Alpha parameter - fraction of normalized frequency domain to remove (e.g., 0.05)
    
    Returns:
        Detrended price series or None if failed
    """
    try:
        # Input validation
        if not isinstance(price_series, pd.Series):
            logging.error("Input price_series must be a pandas Series.")
            return None
            
        price_series_cleaned = price_series.dropna()
        if len(price_series_cleaned) < 20:  # Minimum for FFT
            logging.warning(f"Insufficient data points ({len(price_series_cleaned)}) for Fourier detrending. Min 20 required.")
            return None

        # Perform FFT detrending
        data_values = price_series_cleaned.values
        n = len(data_values)
        fft_coeffs = np.fft.fft(data_values)
        frequencies = np.fft.fftfreq(n)

        # Create a copy of coefficients to modify
        fft_coeffs_detrended = fft_coeffs.copy()

        # Remove low-frequency components based on paper's methodology
        # Zero out coefficients where |frequency| < remove_fraction
        fft_coeffs_detrended[np.abs(frequencies) < remove_fraction] = 0

        # Inverse FFT to get detrended signal
        detrended_signal = np.fft.ifft(fft_coeffs_detrended).real
        detrended_series = pd.Series(detrended_signal, index=price_series_cleaned.index, name="DetrendedPrice")

        # Reindex to match original series (fills NaN where original had NaN)
        return detrended_series.reindex(price_series.index)

    except Exception as e:
        logging.error(f"Error during Fourier detrending: {e}")
        return None

def generate_fourier_signals_analysis(
    price_series: pd.Series,
    config: FourierSignalConfig
) -> Optional[Dict[str, Any]]:
    """
    Generate Fourier-based trading signals using statistical arbitrage methodology.
    
    Args:
        price_series: Price time series
        config: Configuration object with signal parameters
    
    Returns:
        Dictionary with Fourier analysis results or None if failed
    """
    try:
        # 1. Fourier Detrending
        detrended_series = fourier_detrend(price_series, remove_fraction=config.detrend_remove_fraction)
        if detrended_series is None or detrended_series.empty or detrended_series.isna().all():
            logging.warning("Could not generate detrended series. No Fourier signals generated.")
            return None

        # 2. Local Mean Estimation (SMA of detrended series)
        detrended_series_cleaned = detrended_series.dropna()
        if len(detrended_series_cleaned) < config.sma_window:
            logging.warning(f"Not enough data ({len(detrended_series_cleaned)}) for SMA window ({config.sma_window}) on detrended series.")
            local_mean_sma = pd.Series(np.nan, index=price_series.index, name="Detrended_SMA")
        else:
            local_mean_sma = detrended_series_cleaned.rolling(
                window=config.sma_window, 
                min_periods=max(1, config.sma_window // 2)
            ).mean()
            local_mean_sma = local_mean_sma.reindex(price_series.index)

        # 3. Volatility Estimation (Global standard deviation of detrended series)
        valid_detrended = detrended_series.dropna()
        if len(valid_detrended) < 2:
            global_std_dev = np.nan
            logging.warning("Not enough valid detrended data points to calculate global standard deviation.")
        else:
            global_std_dev = valid_detrended.std()
            if pd.isna(global_std_dev) or global_std_dev < 1e-8:
                logging.warning(f"Global standard deviation of detrended series is problematic: {global_std_dev}")

        # 4. Adaptive Trading Bands
        if pd.notna(global_std_dev) and global_std_dev > 1e-8:
            upper_band = local_mean_sma + global_std_dev
            lower_band = local_mean_sma - global_std_dev
            
            # 5. Signal Generation Logic
            current_detrended = detrended_series.iloc[-1] if not detrended_series.empty else np.nan
            current_upper = upper_band.iloc[-1] if not upper_band.empty else np.nan
            current_lower = lower_band.iloc[-1] if not lower_band.empty else np.nan
            
            # Previous values for trend detection
            prev_detrended = detrended_series.iloc[-2] if len(detrended_series) > 1 else np.nan
            prev_upper = upper_band.iloc[-2] if len(upper_band) > 1 else np.nan
            prev_lower = lower_band.iloc[-2] if len(lower_band) > 1 else np.nan
            
            # Signal logic: crossing bands
            fourier_signal = "Hold"
            signal_strength = 0.0
            
            if (pd.notna(prev_detrended) and pd.notna(prev_lower) and 
                pd.notna(current_detrended) and pd.notna(current_lower)):
                # Buy signal: crossed above lower band
                if prev_detrended <= prev_lower and current_detrended > current_lower:
                    fourier_signal = "Buy"
                    signal_strength = min(abs(current_detrended - current_lower) / global_std_dev, 1.0)
                    
            if (pd.notna(prev_detrended) and pd.notna(prev_upper) and 
                pd.notna(current_detrended) and pd.notna(current_upper)):
                # Sell signal: crossed below upper band
                if prev_detrended >= prev_upper and current_detrended < current_upper:
                    fourier_signal = "Sell"
                    signal_strength = min(abs(current_detrended - current_upper) / global_std_dev, 1.0)
            
            return {
                "fourier_signal": fourier_signal,
                "signal_strength": signal_strength,
                "detrended_value": current_detrended,
                "upper_band": current_upper,
                "lower_band": current_lower,
                "global_std_dev": global_std_dev,
                "detrended_z_score": (current_detrended - local_mean_sma.iloc[-1]) / global_std_dev if pd.notna(local_mean_sma.iloc[-1]) else np.nan
            }
        else:
            logging.warning("Skipping Fourier signal generation due to invalid global standard deviation.")
            return None
            
    except Exception as e:
        logging.error(f"Error in Fourier signals analysis: {e}")
        return None

# --- GARCH Model Function ---
def fit_garch_and_forecast_volatility(
    returns_series: pd.Series, # Expects daily log returns for daily volatility forecast
    p: int = 1,
    q: int = 1,
    trading_periods_per_year: int = 365 # For annualizing the forecast
) -> Optional[Dict[str, Any]]: # Changed to Any for diverse return dict
    """
    Fits a GARCH(p,q) model and forecasts next-period conditional volatility.
    Returns a dictionary with 'conditional_volatility_forecast_annualized', 'aic', 'bic', 'mu' or None.
    """
    assert isinstance(returns_series, pd.Series), "Input 'returns_series' must be a pandas Series."
    assert isinstance(p, int) and p >= 0, "GARCH order p must be non-negative."
    assert isinstance(q, int) and q >= 0, "GARCH order q must be non-negative."
    assert isinstance(trading_periods_per_year, int) and trading_periods_per_year > 0

    min_data_points = p + q + 20 # Increased minimum for better stability
    if returns_series.dropna().empty or len(returns_series.dropna()) < min_data_points:
        logging.warning(f"Not enough data points ({len(returns_series.dropna())}) for GARCH({p},{q}) model. Required {min_data_points}.")
        return None

    scaled_returns = returns_series.dropna() * 100 # Scale for GARCH fitting
    if scaled_returns.empty:
        logging.warning("Scaled returns are empty after dropna for GARCH.")
        return None

    try:
        am = arch_model(scaled_returns, vol='Garch', p=p, o=0, q=q, dist='Normal', mean='Zero')
        res = am.fit(update_freq=0, disp='off')

        forecast = res.forecast(horizon=1, reindex=False) # reindex=False is often more robust with date indexes
        cond_variance_forecast_scaled = forecast.variance.iloc[0, 0] # Accessing the first (and only) forecast

        if pd.isna(cond_variance_forecast_scaled) or cond_variance_forecast_scaled <= 0: # Variance must be positive
            logging.warning(f"GARCH forecast resulted in NaN or non-positive variance: {cond_variance_forecast_scaled}")
            return None

        cond_volatility_daily = np.sqrt(cond_variance_forecast_scaled) / 100.0
        cond_volatility_annualized = cond_volatility_daily * np.sqrt(trading_periods_per_year)

        return {
            "conditional_volatility_forecast_annualized": cond_volatility_annualized,
            "aic": res.aic,
            "bic": res.bic,
            "mu": res.params['mu'] if 'mu' in res.params else 0.0
        }
    except Exception as e:
        logging.error(f"GARCH({p},{q}) model fitting failed: {e}")
        return None

# --- VaR and CVaR Calculation ---
def calculate_historical_var_cvar(
    returns_series: pd.Series,
    confidence_level: float = 0.95
) -> Optional[Dict[str, float]]:
    """
    Calculates historical Value at Risk (VaR) and Conditional VaR (CVaR / ES).
    `returns_series` should be returns for the period of interest (e.g., daily returns for 1-day VaR).
    Returns VaR and CVaR as positive numbers representing potential loss.
    """
    assert isinstance(returns_series, pd.Series), "Input 'returns_series' must be a pandas Series."
    assert 0 < confidence_level < 1, "Confidence level must be between 0 and 1."

    min_data_points_var = int(1 / (1 - confidence_level)) + 5 # e.g., 25 for 95%
    if returns_series.dropna().empty or len(returns_series.dropna()) < min_data_points_var:
        logging.warning(f"Not enough data points ({len(returns_series.dropna())}) for VaR/CVaR at {confidence_level*100}%. Required ~{min_data_points_var}.")
        return None

    sorted_returns = returns_series.dropna().sort_values()
    var_percentile = (1.0 - confidence_level)
    var_value = sorted_returns.quantile(var_percentile)
    cvar_value = sorted_returns[sorted_returns <= var_value].mean()

    if pd.isna(var_value) or pd.isna(cvar_value):
        logging.warning(f"VaR or CVaR calculation resulted in NaN. Confidence: {confidence_level}")
        return None

    return {
        f"var_{int(confidence_level*100)}": -var_value,
        f"cvar_{int(confidence_level*100)}": -cvar_value
    }

# --- Main Signal Generation Function ---
def generate_quant_advanced_signals(
    asset_symbol: str,
    chain_id: int,
    token_address: Optional[str],
    ohlcv_df: pd.DataFrame,
    current_price: Optional[float] = None,
    trading_periods_per_year: int = 365 # Pass this based on OHLCV data frequency (365 for daily, 365*24 for hourly etc.)
) -> List[Signal]:
    signals: List[Signal] = []
    # Assert preconditions
    assert isinstance(asset_symbol, str) and asset_symbol, "asset_symbol must be a non-empty string."
    assert isinstance(chain_id, int), "chain_id must be an integer."
    assert isinstance(ohlcv_df, pd.DataFrame), "ohlcv_df must be a pandas DataFrame."
    assert 'timestamp' in ohlcv_df.columns and 'close' in ohlcv_df.columns, "ohlcv_df must contain 'timestamp' and 'close' columns."
    assert isinstance(trading_periods_per_year, int) and trading_periods_per_year > 0

    if ohlcv_df.empty or len(ohlcv_df) < 30:
        logging.warning(f"Not enough OHLCV data for Advanced Quant signals on {asset_symbol} (rows: {len(ohlcv_df)}). Required at least 30.")
        return signals

    df = ohlcv_df.copy()
    df.sort_values(by='timestamp', inplace=True)
    # Ensure datetime index for time-series operations and GARCH
    if not isinstance(df.index, pd.DatetimeIndex):
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
        df = df.dropna(subset=['datetime']).set_index('datetime')
        if df.empty:
            logging.error(f"Failed to create valid DatetimeIndex for {asset_symbol}.")
            return signals


    latest_close = df['close'].iloc[-1] if current_price is None else current_price
    if pd.isna(latest_close):
        logging.error(f"Latest close price is NaN for {asset_symbol}. Cannot generate signals.")
        return signals
    latest_timestamp_signal = int(time.time())
    
    # Helper function to create signals with proper type conversion
    def create_signal(signal_type: str, confidence: float, details: Dict[str, Any]) -> Signal:
        return Signal(
            asset_symbol=asset_symbol,
            chain_id=chain_id, 
            token_address=token_address,
            signal_type=signal_type,
            confidence=confidence,
            details=convert_numpy_types(details),
            timestamp=latest_timestamp_signal
        )

    df['log_returns'] = calculate_log_returns(df['close'])
    df['simple_returns'] = calculate_simple_returns(df['close'])
    returns_for_risk_models = df['log_returns'].dropna()

    # --- 1. Enhanced Volatility Analysis & Regime Detection ---
    realized_vol_window = 20
    df['realized_vol_annualized'] = calculate_annualized_realized_volatility(
        df['log_returns'], # Use log returns for vol calculation consistency
        window=realized_vol_window,
        trading_periods_per_year=trading_periods_per_year
    )
    latest_realized_vol_ann = df['realized_vol_annualized'].iloc[-1]

    # Volatility Regime Detection
    if not pd.isna(latest_realized_vol_ann) and len(df['realized_vol_annualized'].dropna()) > realized_vol_window:
        vol_q90 = df['realized_vol_annualized'].quantile(0.90)
        vol_q10 = df['realized_vol_annualized'].quantile(0.10)

        if not pd.isna(vol_q90) and latest_realized_vol_ann > vol_q90:
            signals.append(create_signal(
                "QUANT_VOL_REGIME_HIGH", 0.6,
                {
                    "realized_vol_annualized": latest_realized_vol_ann,
                    "percentile_90th_vol": vol_q90, "price": latest_close}
            ))
        elif not pd.isna(vol_q10) and latest_realized_vol_ann < vol_q10:
            signals.append(create_signal(
                "QUANT_VOL_REGIME_LOW", 0.6,
                {
                    "realized_vol_annualized": latest_realized_vol_ann,
                    "percentile_10th_vol": vol_q10, "price": latest_close}
            ))

    # GARCH Conditional Volatility & Volatility Risk Premium
    garch_results = None
    if len(returns_for_risk_models) >= 30:
        garch_results = fit_garch_and_forecast_volatility(
            returns_for_risk_models, p=1, q=1,
            trading_periods_per_year=trading_periods_per_year
        )
        if garch_results and garch_results.get("conditional_volatility_forecast_annualized") is not None:
            cond_vol_ann = garch_results["conditional_volatility_forecast_annualized"]
            vol_threshold_garch_abs = 0.80 # Example: 80% annualized GARCH vol is high
            if cond_vol_ann > vol_threshold_garch_abs:
                signals.append(create_signal(
                "QUANT_GARCH_HIGH_VOL_FORECAST", 0.7,
                {"forecasted_cond_vol_annualized": cond_vol_ann, "threshold": vol_threshold_garch_abs, "price": latest_close}
            ))

            # Volatility Risk Premium Signal
            if not pd.isna(latest_realized_vol_ann) and latest_realized_vol_ann > 1e-6: # Avoid division by zero or tiny numbers
                vol_premium_ratio = cond_vol_ann / latest_realized_vol_ann
                if vol_premium_ratio > 1.5: # GARCH forecast significantly higher
                     signals.append(create_signal(
                "QUANT_VOL_RISK_PREMIUM_HIGH", 0.65,
                {"garch_vol_ann": cond_vol_ann, "realized_vol_ann": latest_realized_vol_ann, "ratio": vol_premium_ratio, "price": latest_close}
            ))
                elif vol_premium_ratio < 0.67: # GARCH forecast significantly lower (1/1.5)
                     signals.append(Signal(
                        asset_symbol=asset_symbol, chain_id=chain_id, token_address=token_address,
                        signal_type="QUANT_VOL_RISK_PREMIUM_LOW", confidence=0.60, # Market might be complacent
                        details={"garch_vol_ann": cond_vol_ann, "realized_vol_ann": latest_realized_vol_ann, "ratio": vol_premium_ratio, "price": latest_close},
                        timestamp=latest_timestamp_signal))


    # --- 2. VaR/CVaR Risk Signal ---
    returns_for_var_cvar = df['simple_returns'].dropna()
    if len(returns_for_var_cvar) >= 25:
        var_cvar_95 = calculate_historical_var_cvar(returns_for_var_cvar, confidence_level=0.95)
        if var_cvar_95:
            cvar_95_value = var_cvar_95.get("cvar_95")
            cvar_threshold_daily_loss_pct = 0.05 # 5% daily expected shortfall risk
            if cvar_95_value is not None and cvar_95_value > cvar_threshold_daily_loss_pct:
                signals.append(create_signal(
                "QUANT_CVAR95_HIGH_RISK", 0.75,
                {
                        "cvar_95_daily_loss_pct": cvar_95_value * 100,
                        "var_95_daily_loss_pct": var_cvar_95.get("var_95", 0) * 100,
                        "threshold_cvar_pct": cvar_threshold_daily_loss_pct * 100, "price": latest_close}
            ))

    # --- 3. Mean Reversion Potential (Z-Score) ---
    price_sma_window = 20
    if 'close' in df.columns and len(df) >= price_sma_window:
        df_price_sma = df['close'].rolling(window=price_sma_window, min_periods=max(1, price_sma_window//2)).mean()
        df_price_std = df['close'].rolling(window=price_sma_window, min_periods=max(1, price_sma_window//2)).std()
        
        latest_sma = df_price_sma.iloc[-1]
        latest_std = df_price_std.iloc[-1]
        num_std_dev_threshold_mr = 2.0
            
        if not pd.isna(latest_close) and not pd.isna(latest_sma) and not pd.isna(latest_std) and latest_std > 1e-6:
            z_score = (latest_close - latest_sma) / latest_std
            if z_score > num_std_dev_threshold_mr:
                signals.append(create_signal(
                "QUANT_MEANREVERT_OVEREXTENDED_HIGH", 0.6,
                {"price": latest_close, "sma_price": latest_sma, "std_dev_price": latest_std, "z_score": z_score, "threshold_z": num_std_dev_threshold_mr}
            ))
            elif z_score < -num_std_dev_threshold_mr:
                signals.append(create_signal(
                "QUANT_MEANREVERT_OVEREXTENDED_LOW", 0.6,
                {"price": latest_close, "sma_price": latest_sma, "std_dev_price": latest_std, "z_score": z_score, "threshold_z": -num_std_dev_threshold_mr}
            ))

    # --- 4. Momentum Analysis - Advanced ---
    if len(returns_for_risk_models) >= 30:
        # Rolling Sharpe Ratio
        rolling_window = 20
        rolling_returns = returns_for_risk_models.rolling(window=rolling_window)
        rolling_sharpe = rolling_returns.mean() / rolling_returns.std() * np.sqrt(trading_periods_per_year)
        current_sharpe = rolling_sharpe.iloc[-1]
        
        if not pd.isna(current_sharpe):
            # Strong positive momentum
            if current_sharpe > 1.5:
                signals.append(create_signal(
                    "QUANT_MOMENTUM_HIGH_SHARPE", 0.7,
                    {"sharpe_ratio": current_sharpe, "threshold": 1.5, "price": latest_close}
                ))
            # Negative momentum
            elif current_sharpe < -1.0:
                signals.append(create_signal(
                    "QUANT_MOMENTUM_NEGATIVE_SHARPE", 0.7,
                    {"sharpe_ratio": current_sharpe, "threshold": -1.0, "price": latest_close}
                ))
        
        # RSI Divergence Detection
        if len(df) >= 50:
            rsi_window = 14
            price_highs = df['high'].rolling(window=rsi_window).max()
            price_lows = df['low'].rolling(window=rsi_window).min()
            
            # Simple RSI calculation for divergence
            price_change = df['close'].diff()
            gains = price_change.where(price_change > 0, 0)
            losses = -price_change.where(price_change < 0, 0)
            avg_gains = gains.rolling(window=rsi_window).mean()
            avg_losses = losses.rolling(window=rsi_window).mean()
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            # Look for price making new highs while RSI doesn't (bearish divergence)
            recent_price_high = df['high'].iloc[-5:].max()
            recent_rsi_high = rsi.iloc[-5:].max()
            prev_price_high = df['high'].iloc[-20:-5].max()
            prev_rsi_high = rsi.iloc[-20:-5].max()
            
            if (recent_price_high > prev_price_high and 
                recent_rsi_high < prev_rsi_high and 
                not pd.isna(recent_rsi_high) and not pd.isna(prev_rsi_high)):
                signals.append(create_signal(
                    "QUANT_MOMENTUM_BEARISH_DIVERGENCE", 0.65,
                    {"recent_price_high": recent_price_high, "recent_rsi": recent_rsi_high, 
                     "prev_price_high": prev_price_high, "prev_rsi": prev_rsi_high, "price": latest_close}
                ))

    # --- 5. Market Regime Detection ---
    if len(returns_for_risk_models) >= 60:
        # Rolling correlation with market (using returns as proxy)
        rolling_corr_window = 30
        
        # Trend persistence
        price_changes = df['close'].diff()
        trend_direction = (price_changes > 0).astype(int)
        trend_persistence = trend_direction.rolling(window=rolling_corr_window).mean().iloc[-1]
        
        if not pd.isna(trend_persistence):
            # Strong uptrend regime
            if trend_persistence > 0.7:
                signals.append(create_signal(
                    "QUANT_REGIME_STRONG_UPTREND", 0.6,
                    {"trend_persistence": trend_persistence, "threshold": 0.7, "price": latest_close}
                ))
            # Strong downtrend regime
            elif trend_persistence < 0.3:
                signals.append(create_signal(
                    "QUANT_REGIME_STRONG_DOWNTREND", 0.6,
                    {"trend_persistence": trend_persistence, "threshold": 0.3, "price": latest_close}
                ))
        
        # Regime change detection using variance ratio
        short_window = 5
        long_window = 20
        short_var = returns_for_risk_models.rolling(window=short_window).var().iloc[-1]
        long_var = returns_for_risk_models.rolling(window=long_window).var().iloc[-1]
        
        if not pd.isna(short_var) and not pd.isna(long_var) and long_var > 1e-8:
            variance_ratio = short_var / long_var
            # Regime change (high short-term volatility vs long-term)
            if variance_ratio > 3.0:
                signals.append(create_signal(
                    "QUANT_REGIME_CHANGE_DETECTED", 0.65,
                    {"variance_ratio": variance_ratio, "threshold": 3.0, 
                     "short_term_vol": np.sqrt(short_var * trading_periods_per_year), 
                     "long_term_vol": np.sqrt(long_var * trading_periods_per_year), "price": latest_close}
                ))

    # --- 6. Liquidity and Market Microstructure ---
    if 'volume' in df.columns and len(df) >= 30:
        # Volume-Price Trend (VPT) analysis
        price_changes = df['close'].pct_change()
        volume_price_trend = (price_changes * df['volume']).cumsum()
        
        # VPT divergence
        vpt_change = volume_price_trend.iloc[-5:].iloc[-1] - volume_price_trend.iloc[-10:].iloc[0]
        price_change_5d = df['close'].iloc[-1] - df['close'].iloc[-5]
        
        if not pd.isna(vpt_change) and not pd.isna(price_change_5d):
            # Price up but VPT down (bearish divergence)
            if price_change_5d > 0 and vpt_change < 0:
                signals.append(create_signal(
                    "QUANT_LIQUIDITY_BEARISH_VPT_DIVERGENCE", 0.6,
                    {"price_change_5d": price_change_5d, "vpt_change": vpt_change, "price": latest_close}
                ))
            # Price down but VPT up (bullish divergence)
            elif price_change_5d < 0 and vpt_change > 0:
                signals.append(create_signal(
                    "QUANT_LIQUIDITY_BULLISH_VPT_DIVERGENCE", 0.6,
                    {"price_change_5d": price_change_5d, "vpt_change": vpt_change, "price": latest_close}
                ))
        
        # Volume anomaly detection
        volume_sma = df['volume'].rolling(window=20).mean()
        volume_std = df['volume'].rolling(window=20).std()
        latest_volume = df['volume'].iloc[-1]
        
        # Avoid division by zero
        if not pd.isna(volume_sma.iloc[-1]) and not pd.isna(volume_std.iloc[-1]) and volume_std.iloc[-1] > 1e-6:
            volume_zscore = (latest_volume - volume_sma.iloc[-1]) / volume_std.iloc[-1]
            
            if not pd.isna(volume_zscore) and abs(volume_zscore) > 2.5:
                signal_type = "QUANT_LIQUIDITY_VOLUME_SPIKE" if volume_zscore > 0 else "QUANT_LIQUIDITY_VOLUME_DROUGHT"
                signals.append(create_signal(
                    signal_type, 0.55,
                    {"volume_zscore": volume_zscore, "latest_volume": latest_volume, 
                     "avg_volume": volume_sma.iloc[-1], "price": latest_close}
                ))

    # --- 7. Options-like Risk Metrics ---
    if len(returns_for_risk_models) >= 50:
        # Skewness and Kurtosis analysis
        rolling_window = 30
        rolling_skew = returns_for_risk_models.rolling(window=rolling_window).skew()
        rolling_kurt = returns_for_risk_models.rolling(window=rolling_window).kurt()
        
        current_skew = rolling_skew.iloc[-1]
        current_kurt = rolling_kurt.iloc[-1]
        
        if not pd.isna(current_skew):
            # Negative skew (tail risk)
            if current_skew < -1.0:
                signals.append(create_signal(
                    "QUANT_DISTRIBUTION_NEGATIVE_SKEW_RISK", 0.6,
                    {"skewness": current_skew, "threshold": -1.0, "price": latest_close}
                ))
            # High positive skew (potential for large gains)
            elif current_skew > 1.0:
                signals.append(create_signal(
                    "QUANT_DISTRIBUTION_POSITIVE_SKEW_OPPORTUNITY", 0.55,
                    {"skewness": current_skew, "threshold": 1.0, "price": latest_close}
                ))
        
        if not pd.isna(current_kurt):
            # High kurtosis (fat tails - extreme events more likely)
            if current_kurt > 5.0:
                signals.append(create_signal(
                    "QUANT_DISTRIBUTION_HIGH_KURTOSIS_RISK", 0.65,
                    {"kurtosis": current_kurt, "threshold": 5.0, "price": latest_close}
                ))

    # --- 8. Fourier Analysis & Statistical Arbitrage ---
    if len(df) >= 30:  # Minimum data for Fourier analysis
        fourier_config = FourierSignalConfig(
            price_col_to_use="close",
            detrend_remove_fraction=0.05,
            sma_window=20
        )
        
        fourier_results = generate_fourier_signals_analysis(df['close'], fourier_config)
        if fourier_results:
            fourier_signal = fourier_results.get("fourier_signal", "Hold")
            signal_strength = fourier_results.get("signal_strength", 0.0)
            detrended_z_score = fourier_results.get("detrended_z_score", 0.0)
            
            # Generate signals based on Fourier analysis
            if fourier_signal == "Buy" and signal_strength > 0.3:
                confidence = min(0.5 + signal_strength * 0.3, 0.8)  # Scale confidence with signal strength
                signals.append(create_signal(
                    "QUANT_FOURIER_MEAN_REVERSION_BUY", confidence,
                    {
                        "fourier_signal": fourier_signal,
                        "signal_strength": signal_strength,
                        "detrended_z_score": detrended_z_score,
                        "detrended_value": fourier_results.get("detrended_value"),
                        "lower_band": fourier_results.get("lower_band"),
                        "price": latest_close
                    }
                ))
            elif fourier_signal == "Sell" and signal_strength > 0.3:
                confidence = min(0.5 + signal_strength * 0.3, 0.8)
                signals.append(create_signal(
                    "QUANT_FOURIER_MEAN_REVERSION_SELL", confidence,
                    {
                        "fourier_signal": fourier_signal,
                        "signal_strength": signal_strength,
                        "detrended_z_score": detrended_z_score,
                        "detrended_value": fourier_results.get("detrended_value"),
                        "upper_band": fourier_results.get("upper_band"),
                        "price": latest_close
                    }
                ))
            
            # Additional signal for extreme detrended values (statistical arbitrage opportunity)
            if not pd.isna(detrended_z_score):
                if abs(detrended_z_score) > 2.0:  # Extreme deviation from detrended mean
                    signal_type = "QUANT_FOURIER_EXTREME_DEVIATION_HIGH" if detrended_z_score > 0 else "QUANT_FOURIER_EXTREME_DEVIATION_LOW"
                    signals.append(create_signal(
                        signal_type, 0.65,
                        {
                            "detrended_z_score": detrended_z_score,
                            "threshold": 2.0,
                            "detrended_value": fourier_results.get("detrended_value"),
                            "global_std_dev": fourier_results.get("global_std_dev"),
                            "price": latest_close
                        }
                    ))
            
            # Fourier-based volatility regime detection
            global_std_dev = fourier_results.get("global_std_dev", 0.0)
            if not pd.isna(global_std_dev) and global_std_dev > 0:
                # Compare Fourier-derived volatility with realized volatility
                if not pd.isna(latest_realized_vol_ann):
                    # Convert global_std_dev to annualized terms (assuming it's from detrended daily prices)
                    fourier_vol_ann = global_std_dev * np.sqrt(trading_periods_per_year)
                    vol_ratio = fourier_vol_ann / latest_realized_vol_ann if latest_realized_vol_ann > 1e-6 else np.nan
                    
                    if not pd.isna(vol_ratio):
                        if vol_ratio > 1.5:  # Fourier volatility significantly higher
                            signals.append(create_signal(
                                "QUANT_FOURIER_HIGH_STRUCTURAL_VOL", 0.6,
                                {
                                    "fourier_vol_annualized": fourier_vol_ann,
                                    "realized_vol_annualized": latest_realized_vol_ann,
                                    "vol_ratio": vol_ratio,
                                    "threshold": 1.5,
                                    "price": latest_close
                                }
                            ))
                        elif vol_ratio < 0.67:  # Fourier volatility significantly lower
                            signals.append(create_signal(
                                "QUANT_FOURIER_LOW_STRUCTURAL_VOL", 0.55,
                                {
                                    "fourier_vol_annualized": fourier_vol_ann,
                                    "realized_vol_annualized": latest_realized_vol_ann,
                                    "vol_ratio": vol_ratio,
                                    "threshold": 0.67,
                                    "price": latest_close
                                }
                            ))

    logging.info(f"Generated {len(signals)} Advanced Quant signals for {asset_symbol}.")
    return signals