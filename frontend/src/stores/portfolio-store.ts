import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// API Response Structures (based on user provided example)
export interface RankedAssetSummary {
  asset: string;
  score: number;
  num_bullish: number;
  num_bearish: number;
}

export interface OptimizedPortfolioDetails {
  weights: Record<string, number>;
  expected_annual_return: number;
  annual_volatility: number;
  sharpe_ratio: number;
  total_assets_considered: number;
  assets_with_allocation: number;
}

export interface MvoInputsSummary {
  expected_returns_top_n: Record<string, number>;
  covariance_matrix_shape: string; // e.g., "(273, 273)"
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

export interface GlobalCrossChainData {
  chain_id: number;
  chain_name: string;
  status: string;
  data: {
    ranked_assets_summary: RankedAssetSummary[];
    optimized_portfolio_details: OptimizedPortfolioDetails;
    mvo_inputs_summary: MvoInputsSummary;
  };
  error_message: string | null;
  request_params_for_chain: RequestParamsForChain;
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
  chain_data_gathering_summary: Record<string, { // chain_id as key
    chain_name: string;
    status: string;
    error_message: string | null;
    assets_found: number;
  }>;
}

export interface ApiResponseData {
  results_by_chain: {
    global_cross_chain: GlobalCrossChainData;
    // Potentially other chain-specific results if the API supports it
  };
  overall_request_summary: OverallRequestSummary;
}
// End of API Response Structures

export interface Portfolio {
  id: string
  name: string
  description?: string
  assets: Asset[] // This might represent manually added assets or a simplified list
  totalValue: number // This might be a manually entered value or derived
  chains: string[] // User selected chains for this portfolio config
  createdAt: Date
  updatedAt: Date
  apiData?: ApiResponseData | null; // To store the fetched API data
  lastApiUpdate?: Date | null;
}

export interface Asset { // Simple asset structure, details might come from API/MongoDB
  id: string
  symbol: string
  name: string
  balance: number
  value: number
  chain: string
  price: number
  change24h: number
}

// For API Parameter Form
export interface ApiCallParams {
  chain_ids: string; // Comma-separated string of chain IDs
  timeframe: 'day' | 'week' | 'month' | 'quarter' | 'year';
  max_tokens_per_chain: number;
  mvo_objective: 'maximize_sharpe' | 'minimize_volatility' | 'target_return';
  risk_free_rate: number;
  annualization_factor_override?: number | null;
  target_return_input?: number | null; // For 'target_return' objective
  use_ranking_for_expected_returns: boolean;
  score_to_return_scale: number;
  ohlcv_history_points_for_cov: number;
}

interface PortfolioState {
  portfolios: Portfolio[]
  activePortfolioId: string | null
  apiParameters: ApiCallParams;
  isLoadingApiData: boolean;
  selectedChain: string | null;

  createPortfolio: (portfolio: Omit<Portfolio, 'id' | 'createdAt' | 'updatedAt' | 'apiData' | 'lastApiUpdate'>) => void
  updatePortfolio: (id: string, updates: Partial<Omit<Portfolio, 'apiData' | 'lastApiUpdate'>>) => void
  deletePortfolio: (id: string) => void
  setActivePortfolio: (id: string) => void
  setSelectedChain: (chain: string) => void;
  
  setApiParameters: (params: Partial<ApiCallParams>) => void;
  fetchAndSetPortfolioApiData: (portfolioId: string, params: ApiCallParams) => Promise<void>; // Placeholder for actual API call logic
  clearPortfolioApiData: (portfolioId: string) => void;

  addAsset: (portfolioId: string, asset: Asset) => void // Kept for potential manual asset management
  removeAsset: (portfolioId: string, assetId: string) => void // Kept for potential manual asset management
  getActivePortfolio: () => Portfolio | null
}

const defaultApiParams: ApiCallParams = {
  chain_ids: '1,42161,10', // Defaulting to Ethereum, Arbitrum, Optimism as per example
  timeframe: 'day',
  max_tokens_per_chain: 260,
  mvo_objective: 'maximize_sharpe',
  risk_free_rate: 0.02,
  annualization_factor_override: null,
  target_return_input: null,
  use_ranking_for_expected_returns: true,
  score_to_return_scale: 0.2,
  ohlcv_history_points_for_cov: 100,
};

export const usePortfolioStore = create<PortfolioState>()(
  persist(
    (set, get) => ({
      portfolios: [],
      activePortfolioId: null,
      apiParameters: defaultApiParams,
      isLoadingApiData: false,
      selectedChain: null,

      createPortfolio: (portfolio) => {
        const newPortfolio: Portfolio = {
          ...portfolio,
          id: Date.now().toString(),
          createdAt: new Date(),
          updatedAt: new Date(),
          apiData: null,
          lastApiUpdate: null,
        }
        set((state) => ({
          portfolios: [...state.portfolios, newPortfolio],
          activePortfolioId: newPortfolio.id, // Optionally set new portfolio as active
        }))
      },

      updatePortfolio: (id, updates) => {
        set((state) => ({
          portfolios: state.portfolios.map((p) =>
            p.id === id ? { ...p, ...updates, updatedAt: new Date() } : p
          ),
        }))
      },

      deletePortfolio: (id) => {
        set((state) => ({
          portfolios: state.portfolios.filter((p) => p.id !== id),
          activePortfolioId: state.activePortfolioId === id ? (state.portfolios.length > 1 ? state.portfolios.filter(p => p.id !== id)[0].id : null) : state.activePortfolioId,
        }))
      },

      setActivePortfolio: (id) => {
        set({ activePortfolioId: id })
      },

      setSelectedChain: (chain) => {
        set({ selectedChain: chain })
      },
      
      setApiParameters: (params) => {
        set((state) => ({ apiParameters: { ...state.apiParameters, ...params }}));
      },

      // This is a placeholder. Actual API call would happen here.
      fetchAndSetPortfolioApiData: async (portfolioId, params) => {
        set({ isLoadingApiData: true });
        console.log('Fetching API data for portfolio:', portfolioId, 'with params:', params);
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 2000)); 

        // -----
        // In a real app, you would make the actual API call here using params
        // const response = await fetch('/your-api-endpoint', { method: 'POST', body: JSON.stringify(params) });
        // const apiData: ApiResponseData = await response.json();
        // For now, using a mock structure based on the user's example for demonstration
        const mockApiData: ApiResponseData = {
          results_by_chain: {
            global_cross_chain: {
              chain_id: 0,
              chain_name: "Global Cross-Chain Portfolio",
              status: "success",
              data: {
                ranked_assets_summary: [
                  { asset: "TRB-USDC_on_Ethereum", score: 0.77, num_bullish: 5, num_bearish: 3 },
                  { asset: "XAUt-USDC_on_Ethereum", score: 0.525, num_bullish: 2, num_bearish: 1 },
                  // ... more ranked assets
                ],
                optimized_portfolio_details: {
                  weights: { "MIM-USDC_on_Arbitrum": 0.0256, "ANIME-USDC_on_Arbitrum": 0.3466 /* ... more weights */ },
                  expected_annual_return: 45.497,
                  annual_volatility: 0.869,
                  sharpe_ratio: 52.294,
                  total_assets_considered: 273,
                  assets_with_allocation: 30
                },
                mvo_inputs_summary: {
                  expected_returns_top_n: { "ANIME-USDC_on_Arbitrum": 112.94, /* ... more */ },
                  covariance_matrix_shape: "(273, 273)",
                  valid_symbols_count_for_mvo: 273
                }
              },
              error_message: null,
              request_params_for_chain: {
                chain_ids_requested: params.chain_ids.split(',').map(Number),
                timeframe: params.timeframe,
                mvo_objective: params.mvo_objective,
                risk_free_rate: params.risk_free_rate,
                annualization_factor_used: params.annualization_factor_override || 365, 
                max_tokens_per_chain_screening: params.max_tokens_per_chain,
                target_return: params.target_return_input || null
              }
            }
          },
          overall_request_summary: {
            requested_chain_ids: params.chain_ids.split(',').map(Number),
            timeframe: params.timeframe,
            max_tokens_per_chain_screening: params.max_tokens_per_chain,
            mvo_objective: params.mvo_objective,
            risk_free_rate: params.risk_free_rate,
            annualization_factor_used: params.annualization_factor_override || 365,
            total_unique_assets_after_screening: 274,
            assets_considered_for_global_mvo: 273,
            assets_in_final_portfolio: 30,
            total_processing_time_seconds: 207.59,
            chain_data_gathering_summary: {
              "1": { chain_name: "Ethereum", status: "success_data_gathering", error_message: null, assets_found: 181 },
              "10": { chain_name: "Optimism", status: "success_data_gathering", error_message: null, assets_found: 37 },
              "42161": { chain_name: "Arbitrum", status: "success_data_gathering", error_message: null, assets_found: 56 }
            }
          }
        };
        // -----

        set((state) => ({
          portfolios: state.portfolios.map((p) =>
            p.id === portfolioId ? { ...p, apiData: mockApiData, lastApiUpdate: new Date() } : p
          ),
          isLoadingApiData: false,
        }));
      },

      clearPortfolioApiData: (portfolioId) => {
        set((state) => ({
          portfolios: state.portfolios.map((p) => 
            p.id === portfolioId ? { ...p, apiData: null, lastApiUpdate: null } : p
          ),
        }));
      },

      // Manual asset management (can be expanded or integrated with API flow later)
      addAsset: (portfolioId, asset) => {
        set((state) => ({
          portfolios: state.portfolios.map((p) =>
            p.id === portfolioId
              ? {
                  ...p,
                  assets: [...p.assets, asset],
                  totalValue: p.totalValue + asset.value, // Simple sum, API data would be more accurate
                  updatedAt: new Date(),
                }
              : p
          ),
        }))
      },

      removeAsset: (portfolioId, assetId) => {
        set((state) => ({
          portfolios: state.portfolios.map((p) => {
            if (p.id !== portfolioId) return p
            const assetToRemove = p.assets.find((a) => a.id === assetId)
            return {
              ...p,
              assets: p.assets.filter((a) => a.id !== assetId),
              totalValue: p.totalValue - (assetToRemove?.value || 0), // Simple subtraction
              updatedAt: new Date(),
            }
          }),
        }))
      },

      getActivePortfolio: () => {
        const state = get()
        return state.portfolios.find((p) => p.id === state.activePortfolioId) || null
      },
    }),
    {
      name: 'portfolio-storage',
      // partialize: (state) => ({ portfolios: state.portfolios, activePortfolioId: state.activePortfolioId, apiParameters: state.apiParameters }), // Choose what to persist
    }
  )
) 