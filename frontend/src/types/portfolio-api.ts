
export interface RankedAssetSummary {
  asset: string;
  score: number;
  num_bullish: number;
  num_bearish: number;
  chain_id?: number;
  base_token_address?: string;
  quote_token_address?: string;
}

export interface OptimizedPortfolioDetails {
  weights: { [key: string]: number };
  expected_annual_return: number;
  annual_volatility: number;
  sharpe_ratio: number;
  total_assets_considered: number;
  assets_with_allocation: number;
  cvar_95_historical_period?: number;
  max_drawdown?: number;
  sortino_ratio?: number;
  calmar_ratio?: number;
  covariance_matrix_optimized?: { [key: string]: { [key: string]: number } };
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
    alternative_optimized_portfolios?: {
      [objective: string]: OptimizedPortfolioDetails | { error: string; details?: string };
    };
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
  total_processing_time_seconds: number;
  chain_data_gathering_summary: any;
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
  maxTokensPerChain?: number;
  riskFreeRate?: number;
}

// Define a type for individual chain options
export interface ChainOption {
  id: string;
  name: string;
  icon: string; // Reverted to string for now
}

// Chain options for the form
// Using string IDs as they are often easier to handle in forms and match common API practices.
// Make sure these IDs correspond to what your backend expects.
export const chainOptions: ChainOption[] = [
  { id: '1', name: 'Ethereum', icon: '🔷' },
  { id: '137', name: 'Polygon', icon: '🟣' },
  { id: '324', name: 'zkSync Era', icon: '⚡' },
  { id: '42161', name: 'Arbitrum', icon: '🔵' },
  { id: '43114', name: 'Avalanche', icon: '🔺' },
  { id: '10', name: 'Optimism', icon: '🔴' },
  { id: '8453', name: 'Base', icon: '🧱' },
  { id: '59144', name: 'Linea', icon: '〰️' },
  { id: '146', name: 'Sonic', icon: '🎵' },
  { id: '130', name: 'Unichain', icon: '🦄' },
];

export const mvoObjectiveOptions = [
  { id: 'maximize_sharpe', name: 'Maximize Sharpe Ratio' },
  { id: 'minimize_volatility', name: 'Minimize Volatility' },
  { id: 'maximize_return', name: 'Maximize ROI' },
  // Add other objectives if available, e.g., target_return, target_volatility
];

export const timeframeOptions = [
  { id: 'min5', name: '5 Minutes' },
  { id: 'min15', name: '15 Minutes' },
  { id: 'hour1', name: '1 Hour' },
  { id: 'hour4', name: '4 Hours' },
  { id: 'day', name: '1 Day' },
  { id: 'week', name: '1 Week' },
  { id: 'month', name: '1 Month' },

];

// New types for the combined asset data endpoint
export interface AssetOhlcvData {
  ohlcv_candles: Array<{
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume?: number;
  }>;
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

export interface AssetForecastSignal {
  signal_type: string;
  confidence: number;
  details: { [key: string]: any };
  forecast_timestamp: number;
  ohlcv_data_timestamp: number;
  asset_symbol: string;
  chain_id: number;
  base_token_address: string;
}

export interface AssetDataApiResponse {
  ohlcv_data: AssetOhlcvData | null;
  forecast_signals: AssetForecastSignal[];
  error: string | null;
  data_sources: { [key: string]: string };
} 