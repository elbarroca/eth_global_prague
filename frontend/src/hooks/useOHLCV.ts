// src/hooks/useOhlcvData.ts
import { useState, useEffect, useCallback } from 'react';

// Define interfaces based on your MongoDB schema
interface OhlcvCandle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number; // Assuming volume might be present
}

interface OhlcvData {
  _id: string; // Or specific ObjectId type if you use one on frontend
  chain_id: number;
  period_seconds: number;
  base_token_address: string;
  quote_token_address: string;
  timeframe: string;
  base_token_symbol: string;
  chain_name: string;
  last_updated: string; // ISO date string
  ohlcv_candles: OhlcvCandle[];
  quote_token_symbol: string;
}

interface UseOhlcvDataParams {
  chainId: number | null;
  baseTokenAddress: string | null;
  quoteTokenAddress: string | null;
  timeframe: string | null; // e.g., "day", "hour"
  periodSeconds?: number | null; // Optional, if your endpoint can derive it from timeframe
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'; // Your backend URL

export const useOhlcvData = ({
  chainId,
  baseTokenAddress,
  quoteTokenAddress,
  timeframe,
  periodSeconds,
}: UseOhlcvDataParams) => {
  const [data, setData] = useState<OhlcvData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!chainId || !baseTokenAddress || !quoteTokenAddress || !timeframe) {
      setData(null); // Reset data if params are incomplete
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Construct the query parameters
      // Adjust endpoint and params based on your actual backend API
      const queryParams = new URLSearchParams({
        chain_id: String(chainId),
        base_token_address: baseTokenAddress,
        quote_token_address: quoteTokenAddress,
        timeframe: timeframe,
      });
      if (periodSeconds) {
        queryParams.append('period_seconds', String(periodSeconds));
      }

      // Example endpoint: /api/ohlcv?chain_id=...&base_token_address=...
      // You'll need to create this endpoint in your FastAPI backend
      const response = await fetch(`${API_BASE_URL}/api/ohlcv?${queryParams.toString()}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error fetching OHLCV data: ${response.statusText}`);
      }
      const result: OhlcvData = await response.json(); // Assuming backend returns a single matching document
      setData(result);
    } catch (err: any) {
      setError(err.message || 'An unknown error occurred');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [chainId, baseTokenAddress, quoteTokenAddress, timeframe, periodSeconds]);

  useEffect(() => {
    fetchData();
  }, [fetchData]); // Re-fetch when parameters change

  return { data, isLoading, error, refetch: fetchData };
};

// Example Usage in a React Component:
// import { useOhlcvData } from './hooks/useOhlcvData';
//
// const MyChartComponent = () => {
//   const { data, isLoading, error } = useOhlcvData({
//     chainId: 42161,
//     baseTokenAddress: "0x32eb7902d4134bf98a28b963d26de779af92a212",
//     quoteTokenAddress: "0xaf88d065e77c8cc2239327c5edb3a432268e5831",
//     timeframe: "day",
//   });
//
//   if (isLoading) return <p>Loading OHLCV data...</p>;
//   if (error) return <p>Error: {error}</p>;
//   if (!data) return <p>No OHLCV data found.</p>;
//
//   return (
//     <div>
//       <h2>{data.base_token_symbol}/{data.quote_token_symbol} on {data.chain_name}</h2>
//       <p>Last updated: {new Date(data.last_updated).toLocaleString()}</p>
//       {/* Render your chart using data.ohlcv_candles */}
//       <pre>{JSON.stringify(data.ohlcv_candles.slice(0, 5), null, 2)}</pre>
//     </div>
//   );
// };