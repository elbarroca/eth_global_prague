export interface RankedAssetSummary {
  asset: string;
  score: number;
  num_bullish: number;
  num_bearish: number;
}

export interface OptimizedPortfolioDetails {
  weights: { [key: string]: number };
  expected_annual_return: number;
  annual_volatility: number;
  sharpe_ratio: number;
  total_assets_considered: number;
  assets_with_allocation: number;
}

export interface MVOInputsSummary {
  expected_returns_top_n: { [key: string]: number };
  covariance_matrix_shape: string;
  valid_symbols_count_for_mvo: number;
}

export interface RequestParamsForChain {
  chain_ids_requested: number[];
  timeframe: string;
  mvo_objective: string;
  risk_free_rate: number;
  annualization_factor_used: number;
  max_tokens_per_chain_screening: number;
  target_return: number | null;
}

export interface ChainData {
  chain_id: number;
  chain_name: string;
  status: string;
  data: {
    ranked_assets_summary: RankedAssetSummary[];
    optimized_portfolio_details: OptimizedPortfolioDetails;
    mvo_inputs_summary: MVOInputsSummary;
  };
  error_message: string | null;
  request_params_for_chain: RequestParamsForChain;
}

export interface ChainDataGatheringSummaryDetail {
  chain_name: string;
  status: string;
  error_message: string | null;
  assets_found: number;
}

export interface OverallRequestSummary {
  requested_chain_ids: number[];
  timeframe: string;
  max_tokens_per_chain_screening: number;
  mvo_objective: string;
  risk_free_rate: number;
  annualization_factor_used: number;
  total_unique_assets_after_screening: number;
  assets_considered_for_global_mvo: number;
  assets_in_final_portfolio: number;
  total_processing_time_seconds: number;
  chain_data_gathering_summary: {
    [key: string]: ChainDataGatheringSummaryDetail;
  };
}

export interface PortfolioApiResponse {
  results_by_chain: {
    [key: string]: ChainData; // e.g., "global_cross_chain"
  };
  overall_request_summary: OverallRequestSummary;
}

// Form types
export interface PortfolioFormInputs {
  chains: string[]; // array of chain IDs
  mvoObjective: string;
  timeframe: string;
  targetReturn?: number;
  riskFreeRate?: number; // Added based on API response
}

// Chain options for the form
// Using string IDs as they are often easier to handle in forms and match common API practices.
// Make sure these IDs correspond to what your backend expects.
export const chainOptions = [
  { id: '1', name: 'Ethereum', icon: '🔷' },
  { id: '137', name: 'Polygon', icon: '🟣' },
  { id: '42161', name: 'Arbitrum', icon: '🔵' },
  { id: '10', name: 'Optimism', icon: '🔴' },
  { id: '43114', name: 'Avalanche', icon: '🔺' },
  { id: '56', name: 'BSC', icon: '🟡' },
];

export const mvoObjectiveOptions = [
  { id: 'maximize_sharpe', name: 'Maximize Sharpe Ratio' },
  { id: 'minimize_volatility', name: 'Minimize Volatility' },
  // Add other objectives if available, e.g., maximize_return, target_return, target_volatility
];

export const timeframeOptions = [
  { id: '1h', name: '1 Hour' },
  { id: '1d', name: '1 Day' },
  { id: '7d', name: '7 Days' },
  { id: '30d', name: '30 Days' },
  // Based on typical API usage, "day" from your example might be "1d"
  // Adjust these values (id and name) based on what your API endpoint for timeframe expects.
]; 