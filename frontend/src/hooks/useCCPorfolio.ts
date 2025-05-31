// src/hooks/useCrossChainPortfolio.ts
import { useState, useEffect, useCallback } from 'react';

// Define interfaces based on your portfolio cache schema
interface RankedAssetSummary {
  asset: string;
  score: number;
  num_bullish: number;
  num_bearish: number;
}

interface PortfolioWeights {
  [assetSymbol: string]: number;
}

interface OptimizedPortfolioDetails {
  weights: PortfolioWeights;
  expected_annual_return: number;
  annual_volatility: number;
  sharpe_ratio: number;
  cvar_95_historical_period?: number;
  max_drawdown?: number;
  sortino_ratio?: number;
  calmar_ratio?: number;
  covariance_matrix_optimized?: any; // Can be complex, define further if needed
  total_assets_considered: number;
  assets_with_allocation: number;
}

interface AlternativePortfolios {
    [objective: string]: OptimizedPortfolioDetails; // e.g., "maximize_sharpe", "minimize_volatility"
}

interface GlobalPortfolioData {
  ranked_assets_summary: RankedAssetSummary[];
  optimized_portfolio_details: OptimizedPortfolioDetails;
  alternative_optimized_portfolios?: AlternativePortfolios; // From your example data
  mvo_inputs_summary: {
    expected_returns_top_n: { [assetSymbol: string]: number };
    covariance_matrix_shape: string;
    valid_symbols_count_for_mvo: number;
  };
}

interface SingleChainResult {
  chain_id: number;
  chain_name: string;
  status: string;
  data: GlobalPortfolioData; // Assuming the global portfolio structure
  error_message: string | null;
  request_params_for_chain: any; // Define further if needed
}

interface OverallRequestSummary {
    // Define based on your schema
    requested_chain_ids: number[];
    timeframe: string;
    // ... other fields
    total_processing_time_seconds: number;
    chain_data_gathering_summary: any;
}

interface CrossChainPortfolioResponseData {
  results_by_chain: {
    global_cross_chain: SingleChainResult;
  };
  overall_request_summary: OverallRequestSummary;
}


interface CachedCrossChainPortfolio {
  _id: { $oid: string };
  request_timeframe: string;
  request_mvo_objective: string;
  // ... other request parameters you use for querying
  last_updated: { $date: string };
  response_data: CrossChainPortfolioResponseData;
}

interface UseCrossChainPortfolioParams {
  // Parameters to identify which cached portfolio to fetch, e.g.:
  timeframe?: string;
  mvoObjective?: string;
  // Add other relevant query params your backend endpoint expects
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const useCrossChainPortfolio = (params?: UseCrossChainPortfolioParams) => {
  const [portfolio, setPortfolio] = useState<CachedCrossChainPortfolio | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const queryParams = new URLSearchParams();
      if (params?.timeframe) queryParams.append('timeframe', params.timeframe);
      if (params?.mvoObjective) queryParams.append('mvo_objective', params.mvoObjective);
      // Add other params to queryParams

      // Example endpoint: /api/portfolio/cross-chain/cached
      // Or if you fetch by specific ID or latest: /api/portfolio/cross-chain/latest
      // You'll need to create this endpoint in your FastAPI backend
      const response = await fetch(`${API_BASE_URL}/api/portfolio/cross-chain/latest?${queryParams.toString()}`);


      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error fetching cross-chain portfolio: ${response.statusText}`);
      }
      const result: CachedCrossChainPortfolio = await response.json();
      setPortfolio(result);
    } catch (err: any) {
      setError(err.message || 'An unknown error occurred');
      setPortfolio(null);
    } finally {
      setIsLoading(false);
    }
  }, [params]); // Re-fetch if params object reference changes

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { portfolio, isLoading, error, refetch: fetchData };
};

// Example Usage:
// import { useCrossChainPortfolio } from './hooks/useCrossChainPortfolio';
//
// const PortfolioDashboard = () => {
//   const { portfolio, isLoading, error } = useCrossChainPortfolio({
//     timeframe: "day",
//     mvoObjective: "maximize_return" // Example params
//   });
//
//   if (isLoading) return <p>Loading portfolio...</p>;
//   if (error) return <p>Error: {error}</p>;
//   if (!portfolio) return <p>No portfolio data found.</p>;
//
//   const globalPortfolioData = portfolio.response_data.results_by_chain.global_cross_chain.data;
//
//   return (
//     <div>
//       <h2>Global Cross-Chain Portfolio ({portfolio.request_mvo_objective} - {portfolio.request_timeframe})</h2>
//       <p>Last Updated: {new Date(portfolio.last_updated.$date).toLocaleString()}</p>
//       <h3>Optimized Weights:</h3>
//       <pre>{JSON.stringify(globalPortfolioData.optimized_portfolio_details.weights, null, 2)}</pre>
//       <h3>Ranked Assets Summary (Top 5):</h3>
//       <pre>{JSON.stringify(globalPortfolioData.ranked_assets_summary.slice(0,5), null, 2)}</pre>
//       {/* Display other relevant data */}
//     </div>
//   );
// };