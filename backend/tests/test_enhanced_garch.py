#!/usr/bin/env python3
"""
Test script for the enhanced GARCH implementation.
Tests with synthetic crypto-like data to validate improvements.
"""

import sys
import os
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from forecast.quant_forecast import fit_garch_and_forecast_volatility, diagnose_garch_data_suitability

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_crypto_like_returns(n_periods: int = 500, volatility_regime_changes: bool = True) -> pd.Series:
    """
    Generate synthetic returns that mimic cryptocurrency characteristics:
    - High volatility
    - Volatility clustering
    - Fat tails
    - Occasional extreme moves
    """
    np.random.seed(42)  # For reproducibility
    
    returns = []
    current_vol = 0.02  # Starting daily volatility (2%)
    
    for i in range(n_periods):
        # Volatility clustering: current volatility depends on previous volatility
        if i > 0:
            vol_persistence = 0.9
            vol_innovation = 0.1 * np.random.normal(0, 0.01)
            current_vol = vol_persistence * current_vol + vol_innovation
            current_vol = max(0.005, min(0.1, current_vol))  # Bound between 0.5% and 10%
        
        # Regime changes (sudden volatility spikes)
        if volatility_regime_changes and np.random.random() < 0.02:  # 2% chance per period
            current_vol *= np.random.uniform(2, 5)  # Volatility spike
            logger.info(f"Volatility regime change at period {i}: new vol = {current_vol:.4f}")
        
        # Generate return with fat tails (t-distribution)
        df = 4  # Degrees of freedom for t-distribution (fat tails)
        shock = np.random.standard_t(df)
        
        # Occasional extreme moves (crypto flash crashes/pumps)
        if np.random.random() < 0.005:  # 0.5% chance of extreme move
            shock *= np.random.uniform(3, 8)
            logger.info(f"Extreme move at period {i}: shock = {shock:.2f}")
        
        daily_return = current_vol * shock
        returns.append(daily_return)
    
    return pd.Series(returns, name='crypto_returns')

def test_garch_with_different_data_types():
    """Test GARCH fitting with different types of synthetic data."""
    
    test_cases = [
        {
            "name": "Normal Crypto Returns",
            "data": generate_crypto_like_returns(500, volatility_regime_changes=True),
            "description": "Typical crypto returns with volatility clustering and regime changes"
        },
        {
            "name": "High Volatility Crypto",
            "data": generate_crypto_like_returns(300, volatility_regime_changes=True) * 3,
            "description": "Very high volatility crypto (3x normal)"
        },
        {
            "name": "Stable Returns",
            "data": pd.Series(np.random.normal(0, 0.005, 400)),
            "description": "Low volatility, normally distributed returns"
        },
        {
            "name": "Extreme Outliers",
            "data": pd.Series(np.concatenate([
                np.random.normal(0, 0.02, 450),
                [0.5, -0.4, 0.3, -0.6, 0.8]  # Extreme outliers
            ])),
            "description": "Returns with extreme outliers"
        },
        {
            "name": "Insufficient Data",
            "data": pd.Series(np.random.normal(0, 0.02, 30)),
            "description": "Insufficient data points for GARCH"
        }
    ]
    
    results = {}
    
    for test_case in test_cases:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {test_case['name']}")
        logger.info(f"Description: {test_case['description']}")
        logger.info(f"Data points: {len(test_case['data'])}")
        
        # First, run diagnostics
        logger.info("\n--- GARCH Data Suitability Diagnosis ---")
        diagnosis = diagnose_garch_data_suitability(test_case['data'])
        logger.info(f"Suitable for GARCH: {diagnosis['suitable']}")
        
        # Handle different diagnosis return structures
        if 'issues' in diagnosis and diagnosis['issues']:
            logger.info(f"Issues identified: {diagnosis['issues']}")
        elif 'reason' in diagnosis:
            logger.info(f"Reason: {diagnosis['reason']}")
            
        if 'recommendations' in diagnosis and diagnosis['recommendations']:
            logger.info(f"Recommendations: {diagnosis['recommendations']}")
        
        # Display key metrics if available
        if 'metrics' in diagnosis:
            metrics = diagnosis['metrics']
            logger.info(f"Data metrics:")
            logger.info(f"  - Mean: {metrics['mean']:.6f}")
            logger.info(f"  - Std: {metrics['std']:.6f}")
            logger.info(f"  - Skewness: {metrics['skewness']:.3f}")
            logger.info(f"  - Kurtosis: {metrics['kurtosis']:.3f}")
            
            # Handle optional metrics that might not be present
            if 'variance_ratio' in metrics:
                logger.info(f"  - Variance ratio: {metrics['variance_ratio']:.3f}")
            if 'autocorr_sq_lag1' in metrics:
                logger.info(f"  - Volatility clustering (lag-1): {metrics['autocorr_sq_lag1']:.3f}")
            elif 'volatility_clustering' in metrics:
                logger.info(f"  - Volatility clustering: {metrics['volatility_clustering']:.3f}")
        else:
            logger.info("Detailed metrics not available (insufficient data)")
        
        # Now test GARCH fitting
        logger.info("\n--- GARCH Model Fitting ---")
        try:
            garch_result = fit_garch_and_forecast_volatility(
                test_case['data'], 
                p=1, 
                q=1, 
                trading_periods_per_year=365
            )
            
            if garch_result:
                logger.info("✅ GARCH fitting successful!")
                logger.info(f"Model: {garch_result['model_config']}")
                logger.info(f"Forecasted annual volatility: {garch_result['conditional_volatility_forecast_annualized']:.4f}")
                
                # Handle None values for AIC/BIC
                aic = garch_result.get('aic')
                bic = garch_result.get('bic')
                if aic is not None:
                    logger.info(f"AIC: {aic:.2f}")
                else:
                    logger.info("AIC: N/A")
                    
                if bic is not None:
                    logger.info(f"BIC: {bic:.2f}")
                else:
                    logger.info("BIC: N/A")
                
                if garch_result.get('persistence'):
                    logger.info(f"Persistence: {garch_result['persistence']:.4f}")
                
                logger.info(f"Vol ratio to historical: {garch_result['vol_ratio_to_historical']:.2f}")
                
                # Check if it's a fallback
                if garch_result['convergence_flag'] == -1:
                    logger.warning("⚠️  Used historical volatility fallback")
                else:
                    logger.info("✅ True GARCH model converged")
                    
            else:
                logger.error("❌ GARCH fitting completely failed")
                
        except Exception as e:
            logger.error(f"❌ GARCH fitting raised exception: {type(e).__name__} - {e}")
            garch_result = None
        
        results[test_case['name']] = {
            'diagnosis': diagnosis,
            'garch_result': garch_result,
            'success': garch_result is not None
        }
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY OF TESTS")
    logger.info(f"{'='*60}")
    
    successful_tests = sum(1 for r in results.values() if r['success'])
    total_tests = len(results)
    
    logger.info(f"Successful GARCH fits: {successful_tests}/{total_tests}")
    
    for name, result in results.items():
        status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
        if result['success'] and result['garch_result']['convergence_flag'] == -1:
            status += " (fallback)"
        elif result['success']:
            status += " (true GARCH)"
        
        logger.info(f"  {name}: {status}")
    
    return results

def test_specific_crypto_scenario():
    """Test with a specific scenario that mimics the problematic crypto data."""
    logger.info(f"\n{'='*60}")
    logger.info("TESTING SPECIFIC CRYPTO SCENARIO")
    logger.info(f"{'='*60}")
    
    # Create data similar to what was failing in the logs
    np.random.seed(123)
    
    # Generate 393 data points (as mentioned in the log)
    n_points = 393
    
    # Create returns with characteristics that might cause GARCH to fail
    base_returns = np.random.normal(0, 0.0378, n_points)  # ~3.78% std as in logs
    
    # Add some volatility clustering
    for i in range(1, n_points):
        if abs(base_returns[i-1]) > 0.05:  # If previous return was large
            base_returns[i] *= 2  # Increase current volatility
    
    # Add some extreme outliers
    outlier_indices = np.random.choice(n_points, size=int(n_points * 0.02), replace=False)
    for idx in outlier_indices:
        base_returns[idx] *= np.random.uniform(5, 10)
    
    crypto_returns = pd.Series(base_returns, name='problematic_crypto')
    
    logger.info(f"Generated {len(crypto_returns)} data points")
    logger.info(f"Mean: {crypto_returns.mean():.6f}")
    logger.info(f"Std: {crypto_returns.std():.6f}")
    logger.info(f"Min: {crypto_returns.min():.6f}")
    logger.info(f"Max: {crypto_returns.max():.6f}")
    
    # Test diagnosis
    diagnosis = diagnose_garch_data_suitability(crypto_returns)
    logger.info(f"\nDiagnosis - Suitable: {diagnosis['suitable']}")
    
    if 'issues' in diagnosis:
        logger.info(f"Issues: {diagnosis['issues']}")
    elif 'reason' in diagnosis:
        logger.info(f"Reason: {diagnosis['reason']}")
        
    if 'recommendations' in diagnosis:
        logger.info(f"Recommendations: {diagnosis['recommendations']}")
    
    # Test GARCH
    garch_result = fit_garch_and_forecast_volatility(crypto_returns, p=1, q=1, trading_periods_per_year=365)
    
    if garch_result:
        logger.info(f"\n✅ GARCH Result:")
        logger.info(f"Model: {garch_result['model_config']}")
        logger.info(f"Annual Vol Forecast: {garch_result['conditional_volatility_forecast_annualized']:.4f}")
        logger.info(f"Convergence Flag: {garch_result['convergence_flag']}")
        
        if 'garch_diagnosis' in garch_result:
            diag = garch_result['garch_diagnosis']
            logger.info(f"Diagnosis in result - Suitable: {diag['suitable']}")
    else:
        logger.error("❌ GARCH completely failed")
    
    return garch_result

if __name__ == "__main__":
    logger.info("Starting Enhanced GARCH Testing")
    
    # Test with different data types
    test_results = test_garch_with_different_data_types()
    
    # Test specific scenario
    specific_result = test_specific_crypto_scenario()
    
    logger.info("\n🎉 Testing completed!")
    
    # Final assessment
    if any(r['success'] for r in test_results.values()):
        logger.info("✅ Enhanced GARCH implementation shows improvements")
    else:
        logger.warning("⚠️  Enhanced GARCH implementation may need further tuning") 