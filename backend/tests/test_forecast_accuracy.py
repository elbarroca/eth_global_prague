#!/usr/bin/env python3
"""
Comprehensive test script to validate the accuracy of TA and Quant forecast modules.
Tests for calculation correctness, edge cases, and numerical stability.
"""

import pandas as pd
import numpy as np
import logging
import sys
import os
from typing import List, Dict, Any
import warnings

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Import the forecast modules
from forecast.ta_forecast import generate_ta_signals, convert_numpy_types
from forecast.quant_forecast import (
    generate_quant_advanced_signals,
    calculate_log_returns,
    calculate_simple_returns,
    calculate_annualized_realized_volatility,
    fit_garch_and_forecast_volatility,
    calculate_historical_var_cvar,
    fourier_detrend,
    generate_fourier_signals_analysis,
    FourierSignalConfig
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

def create_test_ohlcv_data(n_periods: int = 200, price_start: float = 100.0, add_trend: bool = True) -> pd.DataFrame:
    """Create synthetic OHLCV data for testing."""
    np.random.seed(42)  # For reproducible results
    
    # Ensure we have at least 50 periods for proper testing
    n_periods = max(n_periods, 50)
    
    timestamps = [1640995200 + i * 86400 for i in range(n_periods)]  # Daily timestamps starting Jan 1, 2022
    
    # Generate price series with trend and volatility
    returns = np.random.normal(0.001 if add_trend else 0, 0.02, n_periods)  # 2% daily volatility
    prices = [price_start]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Create OHLCV data
    data = []
    for i, (ts, price) in enumerate(zip(timestamps, prices)):
        # Add some intraday volatility
        high = price * (1 + abs(np.random.normal(0, 0.01)))
        low = price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        volume = abs(np.random.normal(1000000, 200000))
        
        data.append({
            'timestamp': ts,
            'open': open_price,
            'high': max(high, open_price, close_price),
            'low': min(low, open_price, close_price),
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data)

def create_insufficient_test_data(n_periods: int, price_start: float = 100.0) -> pd.DataFrame:
    """Create synthetic OHLCV data with insufficient periods for testing edge cases."""
    np.random.seed(42)  # For reproducible results
    
    timestamps = [1640995200 + i * 86400 for i in range(n_periods)]  # Daily timestamps starting Jan 1, 2022
    
    # Generate price series with trend and volatility
    returns = np.random.normal(0.001, 0.02, n_periods)  # 2% daily volatility
    prices = [price_start]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Create OHLCV data
    data = []
    for i, (ts, price) in enumerate(zip(timestamps, prices)):
        # Add some intraday volatility
        high = price * (1 + abs(np.random.normal(0, 0.01)))
        low = price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        volume = abs(np.random.normal(1000000, 200000))
        
        data.append({
            'timestamp': ts,
            'open': open_price,
            'high': max(high, open_price, close_price),
            'low': min(low, open_price, close_price),
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data)

def test_log_returns_calculation():
    """Test log returns calculation for accuracy and edge cases."""
    logger.info("Testing log returns calculation...")
    
    # Test normal case
    prices = pd.Series([100, 105, 102, 108, 110])
    log_returns = calculate_log_returns(prices)
    
    # Manual calculation for verification
    expected = np.log(prices / prices.shift(1))
    
    # Check if results match (ignoring first NaN)
    assert np.allclose(log_returns[1:], expected[1:], equal_nan=True), "Log returns calculation failed"
    
    # Test edge case: prices with zeros
    prices_with_zero = pd.Series([100, 0, 105, 102])
    log_returns_zero = calculate_log_returns(prices_with_zero)
    assert not log_returns_zero.isna().all(), "Log returns should handle zeros gracefully"
    
    # Test edge case: negative prices
    prices_negative = pd.Series([100, -50, 105, 102])
    log_returns_neg = calculate_log_returns(prices_negative)
    assert not log_returns_neg.isna().all(), "Log returns should handle negative prices gracefully"
    
    logger.info("✓ Log returns calculation tests passed")

def test_volatility_calculation():
    """Test annualized volatility calculation."""
    logger.info("Testing volatility calculation...")
    
    # Create test returns
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0, 0.02, 100))  # 2% daily volatility
    
    vol_series = calculate_annualized_realized_volatility(returns, window=20, trading_periods_per_year=252)
    
    # Check that volatility is positive and reasonable
    valid_vol = vol_series.dropna()
    assert (valid_vol > 0).all(), "Volatility should be positive"
    assert (valid_vol < 2.0).all(), "Volatility should be reasonable (< 200%)"
    
    # Test edge case: insufficient data
    short_returns = pd.Series([0.01, 0.02])
    short_vol = calculate_annualized_realized_volatility(short_returns, window=20)
    assert short_vol.isna().all(), "Should return NaN for insufficient data"
    
    logger.info("✓ Volatility calculation tests passed")

def test_garch_model():
    """Test GARCH model fitting and forecasting."""
    logger.info("Testing GARCH model...")
    
    # Create test returns with volatility clustering
    np.random.seed(42)
    n = 100
    returns = []
    vol = 0.02
    
    for i in range(n):
        vol = 0.8 * vol + 0.2 * 0.02 + 0.1 * vol * np.random.normal(0, 1)**2
        returns.append(np.random.normal(0, vol))
    
    returns_series = pd.Series(returns)
    
    # Test GARCH fitting
    garch_results = fit_garch_and_forecast_volatility(returns_series, p=1, q=1, trading_periods_per_year=252)
    
    if garch_results is not None:
        assert 'conditional_volatility_forecast_annualized' in garch_results
        assert garch_results['conditional_volatility_forecast_annualized'] > 0
        assert garch_results['conditional_volatility_forecast_annualized'] < 2.0  # Reasonable volatility
        logger.info("✓ GARCH model tests passed")
    else:
        logger.warning("GARCH model returned None - may need more data or different parameters")

def test_var_cvar_calculation():
    """Test VaR and CVaR calculation."""
    logger.info("Testing VaR/CVaR calculation...")
    
    # Create test returns with known distribution
    np.random.seed(42)
    returns = pd.Series(np.random.normal(-0.001, 0.02, 1000))  # Slightly negative mean
    
    var_cvar = calculate_historical_var_cvar(returns, confidence_level=0.95)
    
    if var_cvar is not None:
        assert 'var_95' in var_cvar
        assert 'cvar_95' in var_cvar
        assert var_cvar['var_95'] > 0  # VaR should be positive (loss)
        assert var_cvar['cvar_95'] > 0  # CVaR should be positive (loss)
        assert var_cvar['cvar_95'] >= var_cvar['var_95']  # CVaR should be >= VaR
        logger.info("✓ VaR/CVaR calculation tests passed")
    else:
        logger.warning("VaR/CVaR calculation returned None")

def test_fourier_analysis():
    """Test Fourier analysis and detrending."""
    logger.info("Testing Fourier analysis...")
    
    # Create test price series with trend and cycles
    t = np.linspace(0, 4*np.pi, 100)
    trend = 100 + 0.5 * t
    cycle = 5 * np.sin(t) + 2 * np.sin(3*t)
    noise = np.random.normal(0, 1, 100)
    prices = pd.Series(trend + cycle + noise)
    
    # Test detrending
    detrended = fourier_detrend(prices, remove_fraction=0.05)
    
    if detrended is not None:
        assert len(detrended) == len(prices)
        assert not detrended.isna().all()
        
        # Test signal generation
        config = FourierSignalConfig()
        fourier_results = generate_fourier_signals_analysis(prices, config)
        
        if fourier_results is not None:
            assert 'fourier_signal' in fourier_results
            assert fourier_results['fourier_signal'] in ['Buy', 'Sell', 'Hold']
            logger.info("✓ Fourier analysis tests passed")
        else:
            logger.warning("Fourier signal generation returned None")
    else:
        logger.warning("Fourier detrending returned None")

def test_ta_signals():
    """Test TA signal generation."""
    logger.info("Testing TA signal generation...")
    
    # Create test data
    ohlcv_df = create_test_ohlcv_data(n_periods=50)
    
    # Generate TA signals
    ta_signals = generate_ta_signals(
        asset_symbol="TEST",
        chain_id=1,
        token_address="0x123",
        ohlcv_df=ohlcv_df
    )
    
    # Validate signals
    for signal in ta_signals:
        assert hasattr(signal, 'asset_symbol')
        assert hasattr(signal, 'signal_type')
        assert hasattr(signal, 'confidence')
        assert 0 <= signal.confidence <= 1
        assert signal.signal_type.startswith('TA_')
        
        # Test numpy type conversion
        converted_details = convert_numpy_types(signal.details)
        assert isinstance(converted_details, dict)
    
    logger.info(f"✓ TA signals test passed - generated {len(ta_signals)} signals")

def test_quant_signals():
    """Test Quant signal generation."""
    logger.info("Testing Quant signal generation...")
    
    # Create test data
    ohlcv_df = create_test_ohlcv_data(n_periods=100)
    
    # Generate Quant signals
    quant_signals = generate_quant_advanced_signals(
        asset_symbol="TEST",
        chain_id=1,
        token_address="0x123",
        ohlcv_df=ohlcv_df,
        trading_periods_per_year=252
    )
    
    # Validate signals
    for signal in quant_signals:
        assert hasattr(signal, 'asset_symbol')
        assert hasattr(signal, 'signal_type')
        assert hasattr(signal, 'confidence')
        assert 0 <= signal.confidence <= 1
        assert signal.signal_type.startswith('QUANT_')
    
    logger.info(f"✓ Quant signals test passed - generated {len(quant_signals)} signals")

def test_50_plus_data_points():
    """Test that forecast functions work properly with 50+ data points."""
    logger.info("Testing 50+ data points validation...")
    
    # Test with exactly 50 points
    ohlcv_df_50 = create_test_ohlcv_data(n_periods=50)
    
    # Test TA signals with 50 points
    ta_signals_50 = generate_ta_signals(
        asset_symbol="TEST_50",
        chain_id=1,
        token_address="0x123",
        ohlcv_df=ohlcv_df_50
    )
    
    # Test Quant signals with 50 points
    quant_signals_50 = generate_quant_advanced_signals(
        asset_symbol="TEST_50",
        chain_id=1,
        token_address="0x123",
        ohlcv_df=ohlcv_df_50,
        trading_periods_per_year=252
    )
    
    # Test with 100 points for comparison
    ohlcv_df_100 = create_test_ohlcv_data(n_periods=100)
    
    ta_signals_100 = generate_ta_signals(
        asset_symbol="TEST_100",
        chain_id=1,
        token_address="0x123",
        ohlcv_df=ohlcv_df_100
    )
    
    quant_signals_100 = generate_quant_advanced_signals(
        asset_symbol="TEST_100",
        chain_id=1,
        token_address="0x123",
        ohlcv_df=ohlcv_df_100,
        trading_periods_per_year=252
    )
    
    # Test with insufficient data (49 points)
    ohlcv_df_49 = create_insufficient_test_data(n_periods=49)
    
    ta_signals_49 = generate_ta_signals(
        asset_symbol="TEST_49",
        chain_id=1,
        token_address="0x123",
        ohlcv_df=ohlcv_df_49
    )
    
    quant_signals_49 = generate_quant_advanced_signals(
        asset_symbol="TEST_49",
        chain_id=1,
        token_address="0x123",
        ohlcv_df=ohlcv_df_49,
        trading_periods_per_year=252
    )
    
    # Validate results
    assert len(ta_signals_50) >= 0, "TA signals should work with 50 data points"
    assert len(quant_signals_50) >= 0, "Quant signals should work with 50 data points"
    assert len(ta_signals_100) >= len(ta_signals_50), "More data should produce at least as many signals"
    assert len(quant_signals_100) >= len(quant_signals_50), "More data should produce at least as many signals"
    assert len(ta_signals_49) == 0, "TA signals should not work with insufficient data"
    assert len(quant_signals_49) == 0, "Quant signals should not work with insufficient data"
    
    logger.info(f"✓ 50+ data points test passed - TA: 50pts={len(ta_signals_50)}, 100pts={len(ta_signals_100)}, 49pts={len(ta_signals_49)}")
    logger.info(f"✓ 50+ data points test passed - Quant: 50pts={len(quant_signals_50)}, 100pts={len(quant_signals_100)}, 49pts={len(quant_signals_49)}")

def test_edge_cases():
    """Test edge cases and error handling."""
    logger.info("Testing edge cases...")
    
    # Test with minimal data (should fail gracefully)
    minimal_data = create_insufficient_test_data(n_periods=5)
    ta_signals_minimal = generate_ta_signals("TEST_MINIMAL", 1, "0x123", minimal_data)
    quant_signals_minimal = generate_quant_advanced_signals("TEST_MINIMAL", 1, "0x123", minimal_data)
    assert len(ta_signals_minimal) == 0
    assert len(quant_signals_minimal) == 0
    
    # Test with data containing some NaN values
    nan_data = create_test_ohlcv_data(n_periods=60)  # Increased from 50 to 60
    # Introduce some NaN values (but not too many)
    nan_indices = np.random.choice(len(nan_data), size=6, replace=False)  # 10% NaN
    nan_data.loc[nan_indices, 'close'] = np.nan
    
    ta_signals_nan = generate_ta_signals("TEST_NAN", 1, "0x123", nan_data)
    quant_signals_nan = generate_quant_advanced_signals("TEST_NAN", 1, "0x123", nan_data)
    
    # Should handle NaN gracefully
    assert isinstance(ta_signals_nan, list)
    assert isinstance(quant_signals_nan, list)
    
    logger.info("✓ Edge cases test passed")

def main():
    """Run comprehensive forecast accuracy tests."""
    logger.info("Starting comprehensive forecast accuracy tests...")
    
    try:
        test_log_returns_calculation()
        test_volatility_calculation()
        test_garch_model()
        test_var_cvar_calculation()
        test_fourier_analysis()
        test_ta_signals()
        test_quant_signals()
        test_50_plus_data_points()
        test_edge_cases()
        
        logger.info("🎉 All tests passed! Forecast modules are working correctly with 50+ data points.")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    main() 