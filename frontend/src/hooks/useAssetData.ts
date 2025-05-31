import { useState, useEffect, useCallback } from 'react';

// Define interfaces for the combined response
interface OhlcvCandle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface OhlcvData {
  ohlcv_candles: OhlcvCandle[];
  last_updated: string | null;
  chain_id: number;
  base_token_address: string;
  quote_token_address: string;
  timeframe: string;
  period_seconds: number;
  base_token_symbol: string;
  quote_token_symbol: string;
  chain_name: string;
}

interface ForecastSignal {
  signal_type: string;
  confidence: number;
  details: { [key: string]: any };
  forecast_timestamp: number;
  ohlcv_data_timestamp: number;
  asset_symbol: string;
  chain_id: number;
  base_token_address: string;
}

interface AssetDataResponse {
  ohlcv_data: OhlcvData | null;
  forecast_signals: ForecastSignal[];
  error: string | null;
  data_sources: { [key: string]: string };
}

interface UseAssetDataParams {
  chainId: number | null;
  baseTokenAddress: string | null;
  quoteTokenAddress: string | null;
  timeframe: string | null;
  periodSeconds?: number | null;
  maxForecastAgeHours?: number;
  baseSymbolHint?: string | null;
  quoteSymbolHint?: string | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const useAssetData = ({
  chainId,
  baseTokenAddress,
  quoteTokenAddress,
  timeframe,
  periodSeconds,
  maxForecastAgeHours = 4,
  baseSymbolHint,
  quoteSymbolHint,
}: UseAssetDataParams) => {
  const [data, setData] = useState<AssetDataResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!chainId || !baseTokenAddress || !quoteTokenAddress || !timeframe) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const queryParams = new URLSearchParams({
        chain_id: String(chainId),
        base_token_address: baseTokenAddress,
        quote_token_address: quoteTokenAddress,
        timeframe: timeframe,
        max_forecast_age_hours: String(maxForecastAgeHours),
      });

      if (periodSeconds) {
        queryParams.append('period_seconds', String(periodSeconds));
      }
      if (baseSymbolHint) {
        queryParams.append('base_symbol_hint', baseSymbolHint);
      }
      if (quoteSymbolHint) {
        queryParams.append('quote_symbol_hint', quoteSymbolHint);
      }

      const response = await fetch(`${API_BASE_URL}/api/asset_data?${queryParams.toString()}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error fetching asset data: ${response.statusText}`);
      }

      const result: AssetDataResponse = await response.json();
      setData(result);

      // Set error if the response contains an error but still return the data
      if (result.error) {
        setError(result.error);
      }
    } catch (err: any) {
      setError(err.message || 'An unknown error occurred');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [chainId, baseTokenAddress, quoteTokenAddress, timeframe, periodSeconds, maxForecastAgeHours, baseSymbolHint, quoteSymbolHint]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { 
    data, 
    isLoading, 
    error, 
    refetch: fetchData,
    // Convenience accessors
    ohlcvData: data?.ohlcv_data || null,
    forecastSignals: data?.forecast_signals || [],
    dataSources: data?.data_sources || {},
  };
};

// Example Usage:
// import { useAssetData } from './hooks/useAssetData';
//
// const AssetAnalysisComponent = () => {
//   const { data, isLoading, error, ohlcvData, forecastSignals } = useAssetData({
//     chainId: 42161,
//     baseTokenAddress: "0x32eb7902d4134bf98a28b963d26de779af92a212",
//     quoteTokenAddress: "0xaf88d065e77c8cc2239327c5edb3a432268e5831",
//     timeframe: "day",
//   });
//
//   if (isLoading) return <p>Loading asset data...</p>;
//   if (error) return <p>Error: {error}</p>;
//   if (!data) return <p>No asset data found.</p>;
//
//   return (
//     <div>
//       {ohlcvData && (
//         <div>
//           <h3>OHLCV Data</h3>
//           <p>{ohlcvData.base_token_symbol}/{ohlcvData.quote_token_symbol} on {ohlcvData.chain_name}</p>
//           <p>Candles: {ohlcvData.ohlcv_candles.length}</p>
//         </div>
//       )}
//       {forecastSignals.length > 0 && (
//         <div>
//           <h3>Forecast Signals</h3>
//           <p>Found {forecastSignals.length} signals</p>
//         </div>
//       )}
//     </div>
//   );
// }; 