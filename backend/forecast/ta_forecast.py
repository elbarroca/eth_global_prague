import logging
import pandas as pd
import numpy as np
import talib # Import TA-Lib
from typing import List, Dict, Any, Optional
from models import Signal, OHLCVDataPoint # Assuming Signal model and OHLCVDataPoint are defined
import time

# Helper function to convert numpy types to Python native types for JSON serialization with validation
def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization with validation."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        # Check for invalid float values
        if np.isnan(obj) or np.isinf(obj):
            logging.warning(f"Converting invalid float value {obj} to None")
            return None
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (int, float)) and not np.isfinite(obj):
        logging.warning(f"Converting invalid numeric value {obj} to None")
        return None
    return obj

# --- Signal Generation Functions ---
def generate_ta_signals(
    asset_symbol: str,
    chain_id: int,
    base_token_address: Optional[str],
    ohlcv_df: pd.DataFrame,
    current_price: Optional[float] = None
) -> List[Signal]:
    """
    Generates essential TA-based signals from OHLCV data using TA-Lib.
    Focuses on the most reliable and actionable signals.
    Requires minimum 50 data points for robust signal generation.
    """
    signals: List[Signal] = []
    min_data_points = 50  # Increased from 30 to 50 for better reliability

    # Enhanced validation
    if ohlcv_df.empty or len(ohlcv_df) < min_data_points:
        logging.warning(f"Not enough OHLCV data for TA signals on {asset_symbol} (rows: {len(ohlcv_df)}). Required at least {min_data_points}.")
        return signals

    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in ohlcv_df.columns:
            logging.error(f"'{col}' column missing in OHLCV data for {asset_symbol}.")
            return signals
        
        # Enhanced numeric validation
        if col != 'timestamp':
            if not pd.api.types.is_numeric_dtype(ohlcv_df[col]):
                logging.error(f"'{col}' column is not numeric in OHLCV data for {asset_symbol}.")
                return signals
            
            # Check for infinite values
            if np.isinf(ohlcv_df[col]).any():
                logging.error(f"'{col}' column contains infinite values for {asset_symbol}.")
                return signals
            
            # Check for negative prices (except volume which can be 0)
            if col != 'volume' and (ohlcv_df[col] <= 0).any():
                logging.error(f"'{col}' column contains non-positive values for {asset_symbol}.")
                return signals
        
        # Handle volume NaNs
        if col == 'volume' and ohlcv_df[col].isnull().any():
            logging.warning(f"Volume data for {asset_symbol} contains NaNs. Filling with 0 for TA-Lib compatibility.")
            ohlcv_df[col] = ohlcv_df[col].fillna(0)

    # Use a copy to avoid SettingWithCopyWarning and prepare data for TA-Lib
    df = ohlcv_df.copy()
    df.sort_values(by='timestamp', inplace=True)

    # Additional validation for sufficient data after sorting
    if len(df) < min_data_points:
        logging.warning(f"Insufficient data after sorting for {asset_symbol}: {len(df)} < {min_data_points}")
        return signals

    # Validate OHLC relationships
    invalid_ohlc = (
        (df['high'] < df['low']) | 
        (df['high'] < df['open']) | 
        (df['high'] < df['close']) |
        (df['low'] > df['open']) | 
        (df['low'] > df['close'])
    )
    
    if invalid_ohlc.any():
        logging.warning(f"Invalid OHLC relationships detected for {asset_symbol}. Fixing {invalid_ohlc.sum()} rows.")
        # Fix invalid OHLC relationships
        df.loc[invalid_ohlc, 'high'] = df.loc[invalid_ohlc, ['open', 'close']].max(axis=1)
        df.loc[invalid_ohlc, 'low'] = df.loc[invalid_ohlc, ['open', 'close']].min(axis=1)

    # Prepare numpy arrays for TA-Lib with enhanced validation
    try:
        open_prices = np.ascontiguousarray(df['open'].values, dtype=np.float64)
        high_prices = np.ascontiguousarray(df['high'].values, dtype=np.float64)
        low_prices = np.ascontiguousarray(df['low'].values, dtype=np.float64)
        close_prices = np.ascontiguousarray(df['close'].values, dtype=np.float64)
        volume = np.ascontiguousarray(df['volume'].values, dtype=np.float64)
        
        # Validate array lengths are consistent and sufficient
        array_lengths = [len(arr) for arr in [open_prices, high_prices, low_prices, close_prices, volume]]
        if not all(length == array_lengths[0] for length in array_lengths):
            logging.error(f"Inconsistent array lengths for {asset_symbol}: {array_lengths}")
            return signals
        
        if array_lengths[0] < min_data_points:
            logging.error(f"Array length {array_lengths[0]} insufficient for {asset_symbol}, need {min_data_points}")
            return signals
        
        # Final validation of numpy arrays - handle NaN values more gracefully
        arrays_info = [('open', open_prices), ('high', high_prices), 
                      ('low', low_prices), ('close', close_prices), ('volume', volume)]
        
        for arr_name, arr in arrays_info:
            if np.isnan(arr).any():
                nan_count = np.isnan(arr).sum()
                total_count = len(arr)
                nan_percentage = nan_count / total_count
                
                # If less than 10% NaN, try to interpolate (more strict than before)
                if nan_percentage < 0.1:
                    logging.warning(f"{arr_name} array contains {nan_count} NaN values for {asset_symbol}. Attempting interpolation.")
                    # Simple forward fill and backward fill
                    arr_series = pd.Series(arr)
                    arr_series = arr_series.ffill().bfill()
                    
                    # Update the array
                    if arr_name == 'open':
                        open_prices = arr_series.values
                    elif arr_name == 'high':
                        high_prices = arr_series.values
                    elif arr_name == 'low':
                        low_prices = arr_series.values
                    elif arr_name == 'close':
                        close_prices = arr_series.values
                    elif arr_name == 'volume':
                        volume = arr_series.values
                else:
                    logging.error(f"{arr_name} array contains too many NaN values ({nan_percentage:.1%}) for {asset_symbol}")
                    return signals
                    
            if np.isinf(arr).any():
                logging.error(f"{arr_name} array contains infinite values for {asset_symbol}")
                return signals
                
    except (ValueError, TypeError) as e:
        logging.error(f"Error converting OHLCV data to numpy arrays for {asset_symbol}: {e}")
        return signals

    # Validate current price
    if current_price is not None:
        if not np.isfinite(current_price) or current_price <= 0:
            logging.warning(f"Invalid current_price {current_price} for {asset_symbol}. Using latest close.")
            current_price = None
    
    latest_close_price = float(close_prices[-1]) if current_price is None else float(current_price)
    
    # Final validation of latest price
    if not np.isfinite(latest_close_price) or latest_close_price <= 0:
        logging.error(f"Invalid latest close price {latest_close_price} for {asset_symbol}")
        return signals
        
    latest_timestamp_signal = int(time.time())
    
    # Helper function to create signals with enhanced validation
    def create_signal(signal_type: str, confidence: float, details: Dict[str, Any]) -> Signal:
        # Validate confidence
        if not (0 <= confidence <= 1):
            logging.warning(f"Invalid confidence {confidence} for signal {signal_type}. Clamping to [0,1].")
            confidence = max(0, min(1, confidence))
        
        # Validate details values
        validated_details = {}
        for key, value in details.items():
            if isinstance(value, (int, float)) and not np.isfinite(value):
                logging.warning(f"Invalid value {value} for detail {key} in signal {signal_type}")
                continue # Skip invalid detail
            validated_details[key] = value
            
        return Signal(
            asset_symbol=asset_symbol,
            chain_id=chain_id, 
            base_token_address=base_token_address,
            signal_type=signal_type,
            confidence=confidence,
            details=convert_numpy_types(validated_details),
            timestamp=latest_timestamp_signal
        )

    # --- 1. Moving Average (MA) Crossover - Most Reliable Trend Signal ---
    try:
        sma_10 = talib.SMA(close_prices, timeperiod=10)
        sma_20 = talib.SMA(close_prices, timeperiod=20)

        if not (np.isnan(sma_10[-1]) or np.isnan(sma_20[-1]) or np.isnan(sma_10[-2]) or np.isnan(sma_20[-2])):
            # Bullish Crossover: SMA_10 crosses above SMA_20
            sma_10_val = float(round(sma_10[-1], 6))
            sma_20_val = float(round(sma_20[-1], 6))
            if sma_10[-1] > sma_20[-1] and sma_10[-2] <= sma_20[-2]:
                signals.append(create_signal(
                    "TA_MA_CROSS_BULLISH", 0.75,
                    {"sma_10": sma_10_val, "sma_20": sma_20_val, "price": latest_close_price}
                ))
            # Bearish Crossover: SMA_10 crosses below SMA_20
            elif sma_10[-1] < sma_20[-1] and sma_10[-2] >= sma_20[-2]:
                signals.append(create_signal(
                    "TA_MA_CROSS_BEARISH", 0.75,
                    {"sma_10": sma_10_val, "sma_20": sma_20_val, "price": latest_close_price}
                ))
    except Exception as e:
        logging.error(f"Error calculating MA Crossover for {asset_symbol}: {e}")

    # --- 2. RSI (Relative Strength Index) - Most Reliable Momentum Oscillator ---
    rsi_period = 14
    try:
        rsi = talib.RSI(close_prices, timeperiod=rsi_period)
        if not np.isnan(rsi[-1]):
            latest_rsi_val = float(round(rsi[-1], 2))
            # Overbought Signal (RSI > 70) - made slightly less restrictive
            if latest_rsi_val > 65:  # Changed from 70 to 65
                confidence = 0.7 if latest_rsi_val > 70 else 0.6
                signals.append(create_signal(
                    "TA_RSI_OVERBOUGHT", confidence,
                    {"rsi": latest_rsi_val, "threshold": 65, "price": latest_close_price}
                ))
            # Oversold Signal (RSI < 30) - made slightly less restrictive
            elif latest_rsi_val < 35:  # Changed from 30 to 35
                confidence = 0.7 if latest_rsi_val < 30 else 0.6
                signals.append(create_signal(
                    "TA_RSI_OVERSOLD", confidence,
                    {"rsi": latest_rsi_val, "threshold": 35, "price": latest_close_price}
                ))
            # Add neutral zone signals for additional insights
            elif 45 <= latest_rsi_val <= 55:
                signals.append(create_signal(
                    "TA_RSI_NEUTRAL", 0.5,
                    {"rsi": latest_rsi_val, "price": latest_close_price}
                ))
    except Exception as e:
        logging.error(f"Error calculating RSI for {asset_symbol}: {e}")

    # --- 3. MACD (Moving Average Convergence Divergence) - Best Trend Momentum Combo ---
    try:
        macd_line, signal_line, histogram = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)
        
        # Check if we have enough valid data points
        if (len(macd_line) >= 2 and len(signal_line) >= 2 and len(histogram) >= 2):
            # Find the last valid (non-NaN) values
            last_valid_idx = -1
            prev_valid_idx = -2
            
            # Look for the most recent valid values
            for i in range(len(macd_line) - 1, -1, -1):
                if not np.isnan(macd_line[i]) and not np.isnan(signal_line[i]) and not np.isnan(histogram[i]):
                    if last_valid_idx == -1:
                        last_valid_idx = i
                    elif prev_valid_idx == -2:
                        prev_valid_idx = i
                        break
            
            if last_valid_idx != -1 and prev_valid_idx != -2:
                # Get current and previous values
                macd_current = macd_line[last_valid_idx]
                signal_current = signal_line[last_valid_idx]
                histogram_current = histogram[last_valid_idx]
                
                macd_prev = macd_line[prev_valid_idx]
                signal_prev = signal_line[prev_valid_idx]
                
                # Validate all values are finite
                if all(np.isfinite([macd_current, signal_current, histogram_current, macd_prev, signal_prev])):
                    macd_val = float(round(macd_current, 6))
                    signal_val = float(round(signal_current, 6))
                    histogram_val = float(round(histogram_current, 6))
                    
                    logging.debug(f"MACD Debug for {asset_symbol}: macd={macd_val}, signal={signal_val}, histogram={histogram_val}")
                    
                    # Relaxed MACD crossover conditions (remove histogram requirement for basic signals)
                    
                    # Bullish crossover: MACD crosses above Signal Line
                    if macd_current > signal_current and macd_prev <= signal_prev:
                        signals.append(create_signal(
                            "TA_MACD_CROSS_BULLISH", 0.8,
                            {
                                "macd": macd_val, 
                                "signal_line": signal_val, 
                                "histogram": histogram_val, 
                                "price": latest_close_price,
                                "crossover_strength": abs(macd_val - signal_val)
                            }
                        ))
                        logging.info(f"Generated MACD Bullish crossover for {asset_symbol}")
                        
                    # Bearish crossover: MACD crosses below Signal Line
                    elif macd_current < signal_current and macd_prev >= signal_prev:
                        signals.append(create_signal(
                            "TA_MACD_CROSS_BEARISH", 0.8,
                            {
                                "macd": macd_val, 
                                "signal_line": signal_val, 
                                "histogram": histogram_val, 
                                "price": latest_close_price,
                                "crossover_strength": abs(macd_val - signal_val)
                            }
                        ))
                        logging.info(f"Generated MACD Bearish crossover for {asset_symbol}")
                    
                    # MACD Zero Line Cross signals
                    if len(macd_line) >= 3:
                        # Find another previous valid value for zero line cross detection
                        zero_prev_idx = prev_valid_idx - 1
                        while zero_prev_idx >= 0 and np.isnan(macd_line[zero_prev_idx]):
                            zero_prev_idx -= 1
                            
                        if zero_prev_idx >= 0:
                            macd_zero_prev = macd_line[zero_prev_idx]
                            
                            # Bullish: MACD crosses above zero line
                            if macd_current > 0 and macd_zero_prev <= 0:
                                signals.append(create_signal(
                                    "TA_MACD_ZERO_CROSS_BULLISH", 0.7,
                                    {
                                        "macd": macd_val,
                                        "signal_line": signal_val,
                                        "histogram": histogram_val,
                                        "price": latest_close_price
                                    }
                                ))
                                
                            # Bearish: MACD crosses below zero line
                            elif macd_current < 0 and macd_zero_prev >= 0:
                                signals.append(create_signal(
                                    "TA_MACD_ZERO_CROSS_BEARISH", 0.7,
                                    {
                                        "macd": macd_val,
                                        "signal_line": signal_val,
                                        "histogram": histogram_val,
                                        "price": latest_close_price
                                    }
                                ))
                    
                    # MACD Divergence signals (additional strong signals)
                    if histogram_val > 0 and macd_val > signal_val:
                        # Strong bullish momentum
                        if abs(histogram_val) > abs(macd_val) * 0.1:  # Histogram is significant
                            signals.append(create_signal(
                                "TA_MACD_BULLISH_MOMENTUM", 0.75,
                                {
                                    "macd": macd_val,
                                    "signal_line": signal_val,
                                    "histogram": histogram_val,
                                    "momentum_strength": abs(histogram_val),
                                    "price": latest_close_price
                                }
                            ))
                    elif histogram_val < 0 and macd_val < signal_val:
                        # Strong bearish momentum
                        if abs(histogram_val) > abs(macd_val) * 0.1:  # Histogram is significant
                            signals.append(create_signal(
                                "TA_MACD_BEARISH_MOMENTUM", 0.75,
                                {
                                    "macd": macd_val,
                                    "signal_line": signal_val,
                                    "histogram": histogram_val,
                                    "momentum_strength": abs(histogram_val),
                                    "price": latest_close_price
                                }
                            ))
                else:
                    logging.warning(f"MACD values contain infinite/invalid numbers for {asset_symbol}")
            else:
                logging.debug(f"Insufficient valid MACD data for {asset_symbol}")
        else:
            logging.debug(f"MACD arrays too short for {asset_symbol}: macd={len(macd_line)}, signal={len(signal_line)}")
                
    except Exception as e:
        logging.error(f"Error calculating MACD for {asset_symbol}: {e}")
        if hasattr(e, '__class__'):
            logging.error(f"MACD Error type: {e.__class__.__name__}")

    # --- 4. Bollinger Bands (BB) - Volatility and Mean Reversion ---
    bb_window = 20
    try:
        upper_band, middle_band, lower_band = talib.BBANDS(close_prices, timeperiod=bb_window, nbdevup=2, nbdevdn=2, matype=talib.MA_Type.SMA)
        if not (np.isnan(upper_band[-1]) or np.isnan(lower_band[-1]) or np.isnan(middle_band[-1])):
            upper_b_val = float(round(upper_band[-1], 6))
            middle_b_val = float(round(middle_band[-1], 6))
            lower_b_val = float(round(lower_band[-1], 6))
            
            # Calculate Bollinger Band position
            bb_position = (latest_close_price - lower_band[-1]) / (upper_band[-1] - lower_band[-1])
            
            # Price breaks above Upper Band (potential overbought)
            if latest_close_price > upper_band[-1]:
                signals.append(create_signal(
                    "TA_BB_BREAK_UPPER", 0.65,
                    {"price": latest_close_price, "upper_band": upper_b_val, "middle_band": middle_b_val, "bb_position": round(bb_position, 3)}
                ))
            # Price breaks below Lower Band (potential oversold)
            elif latest_close_price < lower_band[-1]:
                signals.append(create_signal(
                    "TA_BB_BREAK_LOWER", 0.65,
                    {"price": latest_close_price, "lower_band": lower_b_val, "middle_band": middle_b_val, "bb_position": round(bb_position, 3)}
                ))
    except Exception as e:
        logging.error(f"Error calculating Bollinger Bands for {asset_symbol}: {e}")

    # --- 5. Stochastic Oscillator - Momentum for Entry/Exit Timing ---
    try:
        slowk, slowd = talib.STOCH(high_prices, low_prices, close_prices, 
                                   fastk_period=14, slowk_period=3, slowk_matype=0, 
                                   slowd_period=3, slowd_matype=0)
        if not (np.isnan(slowk[-1]) or np.isnan(slowd[-1]) or np.isnan(slowk[-2]) or np.isnan(slowd[-2])):
            k_val = float(round(slowk[-1], 2))
            d_val = float(round(slowd[-1], 2))
            
            # Bullish: %K crosses above %D in oversold territory
            if slowk[-1] > slowd[-1] and slowk[-2] <= slowd[-2] and slowk[-1] < 20:
                signals.append(create_signal(
                    "TA_STOCH_BULLISH_CROSS", 0.7,
                    {"stoch_k": k_val, "stoch_d": d_val, "price": latest_close_price}
                ))
            # Bearish: %K crosses below %D in overbought territory  
            elif slowk[-1] < slowd[-1] and slowk[-2] >= slowd[-2] and slowk[-1] > 80:
                signals.append(create_signal(
                    "TA_STOCH_BEARISH_CROSS", 0.7,
                    {"stoch_k": k_val, "stoch_d": d_val, "price": latest_close_price}
                ))
    except Exception as e:
        logging.error(f"Error calculating Stochastic for {asset_symbol}: {e}")

    # --- 6. Volume Analysis - Confirm Price Movements ---
    try:
        if len(volume) >= 20:
            volume_sma = talib.SMA(volume, timeperiod=20)
            if not np.isnan(volume_sma[-1]) and volume_sma[-1] > 0:
                volume_ratio = volume[-1] / volume_sma[-1]
                
                # High volume with price movement - made less restrictive
                price_change_pct = (close_prices[-1] - close_prices[-2]) / close_prices[-2] * 100
                
                # Lower thresholds for more signals
                if volume_ratio > 1.5 and abs(price_change_pct) > 1.0:  # Reduced from 2.0 to 1.5 and 2.0 to 1.0
                    signal_type = "TA_VOLUME_BREAKOUT_BULLISH" if price_change_pct > 0 else "TA_VOLUME_BREAKOUT_BEARISH"
                    confidence = 0.7 if volume_ratio > 2.0 and abs(price_change_pct) > 2.0 else 0.6
                    signals.append(create_signal(
                        signal_type, confidence,
                        {"volume_ratio": round(volume_ratio, 2), "price_change_pct": round(price_change_pct, 2), "price": latest_close_price}
                    ))
                
                # Add volume anomaly signals
                if volume_ratio > 3.0:  # Very high volume
                    signals.append(create_signal(
                        "TA_VOLUME_SPIKE", 0.6,
                        {"volume_ratio": round(volume_ratio, 2), "price": latest_close_price}
                    ))
                elif volume_ratio < 0.3:  # Very low volume
                    signals.append(create_signal(
                        "TA_VOLUME_DROUGHT", 0.5,
                        {"volume_ratio": round(volume_ratio, 2), "price": latest_close_price}
                    ))
                
                # Add volume trend signals
                if len(volume) >= 40:
                    volume_sma_short = talib.SMA(volume, timeperiod=10)
                    if not np.isnan(volume_sma_short[-1]) and volume_sma_short[-1] > 0:
                        volume_trend_ratio = volume_sma_short[-1] / volume_sma[-1]
                        if volume_trend_ratio > 1.2:  # Increasing volume trend
                            signals.append(create_signal(
                                "TA_VOLUME_TREND_INCREASING", 0.5,
                                {"volume_trend_ratio": round(volume_trend_ratio, 2), "price": latest_close_price}
                            ))
                        elif volume_trend_ratio < 0.8:  # Decreasing volume trend
                            signals.append(create_signal(
                                "TA_VOLUME_TREND_DECREASING", 0.5,
                                {"volume_trend_ratio": round(volume_trend_ratio, 2), "price": latest_close_price}
                            ))
    except Exception as e:
        logging.error(f"Error calculating Volume analysis for {asset_symbol}: {e}")

    logging.info(f"Generated {len(signals)} essential TA signals for {asset_symbol}.")
    
    # --- 7. Additional Price Action Signals (if we have few signals so far) ---
    if len(signals) < 3:  # Add more signals if we don't have many
        try:
            # Price momentum signals
            if len(close_prices) >= 5:
                price_change_1d = (close_prices[-1] - close_prices[-2]) / close_prices[-2] * 100
                price_change_3d = (close_prices[-1] - close_prices[-4]) / close_prices[-4] * 100 if len(close_prices) >= 4 else 0
                
                # Strong price movements
                if abs(price_change_1d) > 3.0:
                    signal_type = "TA_PRICE_STRONG_MOVE_UP" if price_change_1d > 0 else "TA_PRICE_STRONG_MOVE_DOWN"
                    signals.append(create_signal(
                        signal_type, 0.6,
                        {"price_change_1d_pct": round(price_change_1d, 2), "price": latest_close_price}
                    ))
                
                # Momentum consistency
                if abs(price_change_3d) > 5.0 and np.sign(price_change_1d) == np.sign(price_change_3d):
                    signal_type = "TA_PRICE_MOMENTUM_CONSISTENT_UP" if price_change_3d > 0 else "TA_PRICE_MOMENTUM_CONSISTENT_DOWN"
                    signals.append(create_signal(
                        signal_type, 0.55,
                        {"price_change_3d_pct": round(price_change_3d, 2), "price": latest_close_price}
                    ))
            
            # Simple trend signals based on recent highs/lows
            if len(close_prices) >= 10:
                recent_high = np.max(close_prices[-10:])
                recent_low = np.min(close_prices[-10:])
                current_position = (latest_close_price - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5
                
                if current_position > 0.8:  # Near recent high
                    signals.append(create_signal(
                        "TA_PRICE_NEAR_RECENT_HIGH", 0.5,
                        {"position_in_range": round(current_position, 2), "recent_high": recent_high, "price": latest_close_price}
                    ))
                elif current_position < 0.2:  # Near recent low
                    signals.append(create_signal(
                        "TA_PRICE_NEAR_RECENT_LOW", 0.5,
                        {"position_in_range": round(current_position, 2), "recent_low": recent_low, "price": latest_close_price}
                    ))
                    
        except Exception as e:
            logging.error(f"Error calculating additional price action signals for {asset_symbol}: {e}")
    
    return signals