import { ConnectButton } from '@rainbow-me/rainbowkit';
import type { NextPage } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { usePortfolioStore } from '@/stores/portfolio-store';
import { ArrowLeft, Briefcase, Settings, BarChart, Database, Activity } from 'lucide-react';
import { useAccount } from 'wagmi';
import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

import { PortfolioOptimizationForm } from '@/components/optimizer/PortfolioOptimizationForm';
import { OverallRequestSummaryCard } from '@/components/optimizer/OverallRequestSummaryCard';
import { RankedAssetsSummaryCard } from '@/components/optimizer/RankedAssetsSummaryCard';
import { OptimizedPortfolioDetailsCard } from '@/components/optimizer/OptimizedPortfolioDetailsCard';
import { MVOInputsSummaryCard } from '@/components/optimizer/MVOInputsSummaryCard';
import { AssetDeepDiveCard } from '@/components/optimizer/AssetDeepDiveCard';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import {
  PortfolioApiResponse,
  PortfolioFormInputs,
  RankedAssetSummary,
} from '@/types/portfolio-api';

// Define Zod schema for form validation (can be co-located or imported)
const portfolioFormSchema = z.object({
  chains: z.array(z.string()).min(1, "Please select at least one chain."),
  mvoObjective: z.string().min(1, "Please select an MVO objective."),
  timeframe: z.string().min(1, "Please select a timeframe."),
  targetReturn: z.coerce.number().optional(),
  riskFreeRate: z.coerce.number().default(0.02),
});

const Dashboard: NextPage = () => {
  const { isConnected } = useAccount();
  // const { portfolios, activePortfolioId, setActivePortfolio } = usePortfolioStore(); // Commented out as section is removed
  // const activePortfolio = portfolios.find(p => p.id === activePortfolioId); // Commented out

  const [portfolioData, setPortfolioData] = useState<PortfolioApiResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [selectedAssetForDeepDive, setSelectedAssetForDeepDive] = useState<RankedAssetSummary | null>(null);

  const formMethods = useForm<PortfolioFormInputs>({
    resolver: zodResolver(portfolioFormSchema),
    defaultValues: {
      chains: ['1'], // Default to Ethereum for example
      mvoObjective: 'maximize_sharpe',
      timeframe: '1d',
      riskFreeRate: 0.02,
      targetReturn: undefined,
    },
  });

  const onSubmit = async (data: PortfolioFormInputs) => {
    setIsLoading(true);
    setApiError(null);
    setShowResults(false); // Hide previous results before fetching new ones
    // setPortfolioData(null); // Clear old data - optional, if showResults handles visibility
    console.log("Form Data Submitted:", data);

    // Simulate API call
    setTimeout(() => {
      const mockApiResponse: PortfolioApiResponse = {
        results_by_chain: {
          global_cross_chain: {
            chain_id: 0,
            chain_name: "Global Cross-Chain Portfolio",
            status: "success",
            data: {
              ranked_assets_summary: [
                { asset: "TRB-USDC_on_Ethereum", score: 0.77, num_bullish: 5, num_bearish: 3 },
                { asset: "XAUt-USDC_on_Ethereum", score: 0.52, num_bullish: 2, num_bearish: 1 },
                { asset: "MIM-USDC_on_Arbitrum", score: 0.49, num_bullish: 2, num_bearish: 1 },
                { asset: "ELF-USDC_on_Ethereum", score: 0.02, num_bullish: 5, num_bearish: 3 },
                { asset: "stataArbUSDCn-USDC_on_Arbitrum", score: -0.01, num_bullish: 3, num_bearish: 3 },
              ],
              optimized_portfolio_details: {
                weights: { 
                  "MIM-USDC_on_Arbitrum": 0.025670804659467774,
                  "aEthWETH-USDC_on_Ethereum": 0.005775904935772167,
                  "XAI-USDC_on_Ethereum": 0.014411332428068292,
                  "ANIME-USDC_on_Arbitrum": 0.34664275084038354,
                  "WINR-USDC_on_Arbitrum": 0.014145229590328818,
                },
                expected_annual_return: 45.497674,
                annual_volatility: 0.86965,
                sharpe_ratio: 52.294213,
                total_assets_considered: 273,
                assets_with_allocation: 30,
              },
              mvo_inputs_summary: {
                expected_returns_top_n: { 
                  "ANIME-USDC_on_Arbitrum": 112.9492930041536,
                  "GS-USDC_on_Arbitrum": 87.66653399290526,
                  "HOL-USDC_on_Arbitrum": 81.55737783892815, 
                },
                covariance_matrix_shape: "(273, 273)",
                valid_symbols_count_for_mvo: 273,
              },
            },
            error_message: null,
            request_params_for_chain: {
              chain_ids_requested: data.chains.map(id => parseInt(id, 10)),
              timeframe: data.timeframe,
              mvo_objective: data.mvoObjective,
              risk_free_rate: data.riskFreeRate || 0.02,
              annualization_factor_used: 365,
              max_tokens_per_chain_screening: 260,
              target_return: data.targetReturn || null,
            },
          },
        },
        overall_request_summary: {
          requested_chain_ids: data.chains.map(id => parseInt(id, 10)),
          timeframe: data.timeframe,
          max_tokens_per_chain_screening: 260,
          mvo_objective: data.mvoObjective,
          risk_free_rate: data.riskFreeRate || 0.02,
          annualization_factor_used: 365,
          total_unique_assets_after_screening: 274,
          assets_considered_for_global_mvo: 273,
          assets_in_final_portfolio: 30,
          total_processing_time_seconds: 20.59, // Quicker for demo
          chain_data_gathering_summary: {
            "1": { chain_name: "Ethereum", status: "success_data_gathering", error_message: null, assets_found: data.chains.includes('1') ? 181 : 0 },
            "10": { chain_name: "Optimism", status: "success_data_gathering", error_message: null, assets_found: data.chains.includes('10') ? 37 : 0 },
            "42161": { chain_name: "Arbitrum", status: "success_data_gathering", error_message: null, assets_found: data.chains.includes('42161') ? 56 : 0 },
          },
        },
      };
      setPortfolioData(mockApiResponse);
      setIsLoading(false);
      setShowResults(true); // Show results after fetching
      setSelectedAssetForDeepDive(null); // Clear any previous deep dive selection
    }, 1500); // Shorter delay for demo
  };

  const handleAssetSelect = (asset: RankedAssetSummary) => {
    setSelectedAssetForDeepDive(asset);
  };

  const handleCloseDeepDive = () => {
    setSelectedAssetForDeepDive(null);
  };

  const globalPortfolioData = portfolioData?.results_by_chain?.["global_cross_chain"];

  // Add a key to result components to force re-mount and re-animate on new data
  const resultsKey = portfolioData ? JSON.stringify(portfolioData.overall_request_summary.requested_chain_ids) + portfolioData.overall_request_summary.timeframe : 'no_results';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-emerald-900 to-slate-900 text-gray-100">
      <Head>
        <title>DeFi Portfolio Optimizer - AlphaScan</title>
        <meta
          content="Optimize your DeFi portfolio across multiple chains with advanced analytics."
          name="description"
        />
        <link href="/favicon.ico" rel="icon" /> {/* Replace with actual favicon */}
      </Head>

      <nav className="sticky top-0 z-50 px-4 sm:px-6 py-3 border-b border-gray-700 bg-slate-900/80 backdrop-blur-lg">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Link href="/">
              <Button variant="ghost" size="sm" className="hover:bg-slate-700 text-gray-300 hover:text-white">
                <ArrowLeft className="h-4 w-4 mr-1.5" />
                Home
              </Button>
            </Link>
            <div className="text-xl font-bold bg-gradient-to-r from-purple-400 to-violet-300 bg-clip-text text-transparent">
              DeFi Optimizer
            </div>
          </div>
          <ConnectButton />
        </div>
      </nav>

      <main className="px-4 sm:px-6 py-8 sm:py-12">
        <div className="max-w-6xl mx-auto space-y-8">
          
          {!isConnected ? (
            <Card className="text-center py-12 sm:py-20 bg-slate-800/50 border-slate-700 shadow-xl">
                <CardHeader>
                    <Briefcase className="h-16 w-16 mx-auto mb-6 text-purple-400" />
                    <CardTitle className="text-3xl font-bold text-white mb-3">Connect Your Wallet</CardTitle>
                    <CardDescription className="text-lg text-gray-400 mb-6 max-w-md mx-auto">
                        Connect your wallet to unlock advanced portfolio optimization and management features.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <ConnectButton />
                </CardContent>
            </Card>
          ) : (
            <>
              {!showResults && (
                <PortfolioOptimizationForm 
                  onSubmit={onSubmit} 
                  isLoading={isLoading} 
                  formMethods={formMethods} 
                />
              )}

              {isLoading && (
                <Card className="bg-slate-800/50 border-slate-700 shadow-lg">
                  <CardContent className="pt-6 text-center py-10">
                    <div className="flex justify-center items-center mb-4">
                        <svg className="animate-spin h-8 w-8 text-purple-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                    </div>
                    <p className="text-xl font-semibold text-gray-200 animate-pulse">Optimizing Your Portfolio...</p>
                    <p className="text-gray-400">Please wait while we fetch and analyze market data.</p>
                  </CardContent>
                </Card>
              )}
              {apiError && (
                <Card className="border-red-500/50 bg-red-900/30 text-red-200 shadow-lg">
                  <CardHeader>
                    <CardTitle className="text-red-400">Optimization Error</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p>{apiError}</p>
                    <Button variant="outline" onClick={() => setApiError(null)} className="mt-4 border-red-400 text-red-300 hover:bg-red-800">
                        Dismiss
                    </Button>
                  </CardContent>
                </Card>
              )}

              {showResults && portfolioData && (
                <div key={resultsKey} className="space-y-6 mt-8">
                  <Button 
                    onClick={() => {
                      setShowResults(false); 
                      setSelectedAssetForDeepDive(null); // Also clear deep dive selection when going back
                    }}
                    variant="outline" 
                    className="mb-6 bg-slate-700 hover:bg-slate-600 border-slate-600 text-gray-200 hover:text-white">
                    <ArrowLeft className="h-4 w-4 mr-1.5" />
                    Back to Optimizer Form
                  </Button>

                  {selectedAssetForDeepDive && portfolioData ? (
                    <AssetDeepDiveCard 
                      asset={selectedAssetForDeepDive} 
                      requestTimeframe={portfolioData.overall_request_summary.timeframe}
                      onClose={handleCloseDeepDive} 
                    />
                  ) : (
                    globalPortfolioData && (
                      <>
                        <OverallRequestSummaryCard summary={portfolioData.overall_request_summary} />
                        <RankedAssetsSummaryCard 
                          assets={globalPortfolioData.data.ranked_assets_summary} 
                          chainName={globalPortfolioData.chain_name} 
                          onAssetSelect={handleAssetSelect} // Pass the handler
                        />
                        <OptimizedPortfolioDetailsCard details={globalPortfolioData.data.optimized_portfolio_details} chainName={globalPortfolioData.chain_name} />
                        <MVOInputsSummaryCard summary={globalPortfolioData.data.mvo_inputs_summary} chainName={globalPortfolioData.chain_name} />
                      
                        {/* Placeholder for Individual Asset Details - More detailed UI */}
                        <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn animation-delay-800 bg-slate-800 border-slate-700">
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-xl font-semibold text-gray-200">
                              <Database className="h-6 w-6 text-teal-400" />
                              General Information (Placeholder)
                              </CardTitle>
                            <CardDescription className="text-slate-400">Further details or global charts could appear here when no specific asset is selected for deep dive.</CardDescription>
                          </CardHeader>
                          <CardContent className="min-h-[150px] flex items-center justify-center">
                            <p className="text-slate-500 italic">Click an asset in the &apos;Ranked Assets Summary&apos; to see a detailed deep dive.</p>
                          </CardContent>
                        </Card>

                        {/* Placeholder for Benchmark Comparison - More detailed UI */}
                        <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn animation-delay-1000 bg-slate-800 border-slate-700">
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-xl font-semibold text-gray-200">
                              <Activity className="h-6 w-6 text-cyan-400" />
                              Performance vs. Benchmarks (Placeholder)
                              </CardTitle>
                            <CardDescription className="text-slate-400">Track your portfolio&apos;s performance against key market benchmarks (e.g., BTC, ETH).</CardDescription>
                          </CardHeader>
                          <CardContent className="min-h-[150px] flex items-center justify-center">
                            <p className="text-slate-500 italic">Comparative performance charts and detailed metrics will be displayed here.</p>
                          </CardContent>
                        </Card>
                      </>
                    )
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </main>

      <footer className="px-6 py-10 border-t border-gray-700 bg-slate-900/80 mt-12">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-gray-400 text-sm">
            AlphaScan DeFi Portfolio Optimizer | Harnessing data for smarter investments ⛓️
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Dashboard; 