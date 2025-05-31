// src/hooks/useForecastSignals.ts
import { useState, useEffect, useCallback } from 'react';

interface SignalDetails {
  [key: string]: any; // Flexible for different signal types
}

interface ForecastSignal {
  _id: { $oid: string }; // Assuming MongoDB ObjectId structure from your example
  asset_symbol: string;
  chain_id: number;
  base_token_address: string;
  quote_token_address: string;
  base_token_symbol: string;
  quote_token_symbol: string;
  signal_type: string;
  confidence: number;
  details: SignalDetails;
  forecast_timestamp: number;
  ohlcv_data_timestamp: number;
  last_updated: { $date: string }; // Assuming MongoDB Date structure
}

interface UseForecastSignalsParams {
  assetSymbol: string | null; // e.g., "LTO-USDC_on_Ethereum"
  chainId?: number | null; // Optional, if assetSymbol is globally unique
  signalType?: string | null; // Optional, to filter by a specific signal type
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const useForecastSignals = ({
  assetSymbol,
  chainId,
  signalType,
}: UseForecastSignalsParams) => {
  const [signals, setSignals] = useState<ForecastSignal[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!assetSymbol) {
      setSignals([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const queryParams = new URLSearchParams({ asset_symbol: assetSymbol });
      if (chainId) {
        queryParams.append('chain_id', String(chainId));
      }
      if (signalType) {
        queryParams.append('signal_type', signalType);
      }

      // Example endpoint: /api/forecasts/signals?asset_symbol=...
      // You'll need to create this endpoint in your FastAPI backend
      const response = await fetch(`${API_BASE_URL}/api/forecasts/signals?${queryParams.toString()}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error fetching forecast signals: ${response.statusText}`);
      }
      const result: ForecastSignal[] = await response.json();
      setSignals(result);
    } catch (err: any) {
      setError(err.message || 'An unknown error occurred');
      setSignals([]);
    } finally {
      setIsLoading(false);
    }
  }, [assetSymbol, chainId, signalType]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { signals, isLoading, error, refetch: fetchData };
};

// Example Usage:
// import { useForecastSignals } from './hooks/useForecastSignals';
//
// const SignalDisplayComponent = ({ assetSymbol }) => {
//   const { signals, isLoading, error } = useForecastSignals({ assetSymbol });
//
//   if (isLoading) return <p>Loading signals...</p>;
//   if (error) return <p>Error: {error}</p>;
//
//   return (
//     <div>
//       <h3>Signals for {assetSymbol}</h3>
//       {signals.length === 0 ? <p>No signals found.</p> : (
//         <ul>
//           {signals.map(signal => (
//             <li key={signal._id.$oid}>
//               <strong>{signal.signal_type}</strong>: Confidence {signal.confidence.toFixed(2)}
//               (Forecasted: {new Date(signal.forecast_timestamp * 1000).toLocaleDateString()})
//               <pre>{JSON.stringify(signal.details, null, 2)}</pre>
//             </li>
//           ))}
//         </ul>
//       )}
//     </div>
//   );
// };