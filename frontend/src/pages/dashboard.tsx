import { ConnectButton } from '@rainbow-me/rainbowkit';
import type { NextPage } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Briefcase, Settings, BarChart, Database, Activity, ArrowRightLeft } from 'lucide-react';
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
import EfficientFrontierPlot from '@/components/optimizer/EfficientFrontierPlot';

import {
  PortfolioApiResponse,
  PortfolioFormInputs,
  RankedAssetSummary,
  OptimizedPortfolioDetails,
  ChainOption,
  chainOptions,
} from '@/types/portfolio-api';

import { useOrder } from '@/hooks/1inch/useOrder';
import { TOKEN_ADDRESS, SPENDER } from '@/hooks/1inch/useOrder';
import { SupportedChain } from '@1inch/cross-chain-sdk';

const { getQuoteAndExecuteOrder } = useOrder();

// Define Zod schema for form validation (can be co-located or imported)
const portfolioFormSchema = z.object({
  chains: z.array(z.string()).min(1, "Please select at least one chain."),
  mvoObjective: z.string().min(1, "Please select an MVO objective."),
  timeframe: z.string().min(1, "Please select a timeframe."),
  targetReturn: z.coerce.number().optional(),
  maxTokensPerChain: z.coerce.number().min(10).max(100).optional(),
  riskFreeRate: z.coerce.number().min(0).max(1).optional(),
});

// Define a type for storing selected chain details
interface SelectedChainDetails {
  id: string;
  chainId: number;
  name: string;
}

const Dashboard: NextPage = () => {
  const { address: accountAddress, isConnected } = useAccount();
  
  const [portfolioData, setPortfolioData] = useState<PortfolioApiResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [selectedAssetForDeepDive, setSelectedAssetForDeepDive] = useState<RankedAssetSummary | null>(null);
  const [displayedMVOObjective, setDisplayedMVOObjective] = useState<string>("primary");
  
  // New state for tracking selected chains with full details
  const [selectedChains, setSelectedChains] = useState<SelectedChainDetails[]>([]);
  const [isExecutingTx, setIsExecutingTx] = useState(false);

  const formMethods = useForm<PortfolioFormInputs, any, PortfolioFormInputs>({
    resolver: zodResolver(portfolioFormSchema),
    defaultValues: {
      chains: ['1'], // Default to Ethereum for example
      mvoObjective: 'maximize_sharpe',
      timeframe: 'day',
      targetReturn: undefined,
      maxTokensPerChain: 50,
      riskFreeRate: 0.02,
    },
  });

  // Function to map chain IDs to full chain details
  const mapChainsToDetails = (chainIds: string[]): SelectedChainDetails[] => {
    return chainIds.map(id => {
      const chainOption = chainOptions.find(option => option.id === id);
      return {
        id,
        chainId: parseInt(id),
        name: chainOption?.name || `Chain ${id}`
      };
    });
  };

  const onSubmit = async (data: PortfolioFormInputs) => {
    setIsLoading(true);
    setApiError(null);
    setShowResults(false);
    setSelectedAssetForDeepDive(null);
    
    // Store selected chains with their details
    setSelectedChains(mapChainsToDetails(data.chains));
    
    console.log("Form Data Submitted for API call:", data);

    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    const queryParams = new URLSearchParams({
      chain_ids: data.chains.join(','),
      timeframe: data.timeframe,
      mvo_objective: data.mvoObjective,
    });

    if (data.maxTokensPerChain !== undefined) {
      queryParams.append('max_tokens_per_chain', String(data.maxTokensPerChain));
    }
    if (data.riskFreeRate !== undefined) {
      queryParams.append('risk_free_rate', String(data.riskFreeRate));
    }
    if (data.targetReturn !== undefined) {
      queryParams.append('target_return', String(data.targetReturn));
    }

    console.log("Making API call with params:", queryParams.toString());

    try {
      const response = await fetch(`${API_BASE_URL}/portfolio/optimize_cross_chain/?${queryParams.toString()}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch (e) {
          const textError = await response.text();
          throw new Error(textError || `API Error: ${response.status} ${response.statusText}`);
        }
        throw new Error(errorData.detail || `API Error: ${response.status} ${response.statusText}`);
      }

      const result: PortfolioApiResponse = await response.json();
      setPortfolioData(result);
      setShowResults(true);
    } catch (error: any) {
      console.error("API Error:", error);
      setApiError(error.message || "An unexpected error occurred while fetching portfolio data.");
      setPortfolioData(null);
    } finally {
      setIsLoading(false);
    }
  };

  // New function to execute cross-chain transaction
  const executeTransaction = async () => {
    if (!accountAddress || selectedChains.length < 2) {
      console.error("Missing wallet address or need at least 2 chains for cross-chain transaction");
      return;
    }

    setIsExecutingTx(true);
    try {
      // Example transaction - in real implementation you'd need to decide which chains to use
      // Here we're just using the first two selected chains
      const sourceChain = selectedChains[0];
      const destChain = selectedChains[1];

      console.log(`Preparing transaction from ${sourceChain.name} to ${destChain.name}`);

      const params = {
        srcChainId: sourceChain.chainId as unknown as SupportedChain,
        dstChainId: destChain.chainId as unknown as SupportedChain,
        srcTokenAddress: TOKEN_ADDRESS,
        dstTokenAddress: TOKEN_ADDRESS,
        amount: "10000000000000000", // 0.01 ETH in wei
        enableEstimate: true,
        walletAddress: accountAddress
      };

      console.log("Transaction params:", params);
      
      // This would trigger the actual transaction
      const result = await getQuoteAndExecuteOrder(params);
      console.log("Transaction result:", result);
      
    } catch (error) {
      console.error("Transaction error:", error);
    } finally {
      setIsExecutingTx(false);
    }
  };

  const handleAssetSelect = (asset: RankedAssetSummary) => {
    setSelectedAssetForDeepDive(asset);
  };

  const handleCloseDeepDive = () => {
    setSelectedAssetForDeepDive(null);
  };

  const globalPortfolioData = portfolioData?.results_by_chain?.["global_cross_chain"];
  
  // Determine which portfolio details to display based on selection
  let portfolioDetailsToDisplay: OptimizedPortfolioDetails | null | undefined = globalPortfolioData?.data.optimized_portfolio_details;
  const alternativePortfolios = globalPortfolioData?.data.alternative_optimized_portfolios;

  if (displayedMVOObjective !== "primary" && alternativePortfolios && alternativePortfolios[displayedMVOObjective]) {
    const altPortfolio = alternativePortfolios[displayedMVOObjective];
    // Check if it's a valid portfolio detail and not an error object
    if (altPortfolio && typeof altPortfolio === 'object' && 'weights' in altPortfolio) {
         portfolioDetailsToDisplay = altPortfolio as OptimizedPortfolioDetails;
    }
  }

  const mvoDisplayOptions = [ {id: "primary", name: `Primary: ${globalPortfolioData?.request_params_for_chain.mvo_objective.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Objective'}`} ];
  if (alternativePortfolios) {
    Object.keys(alternativePortfolios).forEach(key => {
      // Only add if it's a valid portfolio and not an error placeholder
      const altPortfolio = alternativePortfolios[key];
      if (altPortfolio && typeof altPortfolio === 'object' && 'weights' in altPortfolio) {
        mvoDisplayOptions.push({ id: key, name: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) });
      }
    });
  }

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
        <link href="/favicon.ico" rel="icon" />
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
            <div className="text-xl font-bold text-white">
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
                    <Briefcase className="h-16 w-16 mx-auto mb-6 text-white" />
                    <CardTitle className="text-3xl font-bold text-white mb-3">Connect Your Wallet</CardTitle>
                    <CardDescription className="text-lg text-gray-300 mb-6 max-w-md mx-auto">
                        Connect your wallet to unlock advanced portfolio optimization and management features.
                    </CardDescription>
                </CardHeader>
                <CardContent>
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
                        <svg className="animate-spin h-8 w-8 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
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
                  <div className="flex justify-between items-center">
                    <Button 
                      onClick={() => {
                        setShowResults(false); 
                        setSelectedAssetForDeepDive(null);
                      }}
                      variant="outline" 
                      className="mb-6 bg-slate-700 hover:bg-slate-600 border-slate-600 text-gray-200 hover:text-white">
                      <ArrowLeft className="h-4 w-4 mr-1.5" />
                      Back to Optimizer Form
                    </Button>
                    
                    {selectedChains.length >= 2 && (
                      <Button
                        onClick={executeTransaction}
                        disabled={isExecutingTx}
                        className="mb-6 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-600 text-white font-semibold rounded-xl px-6 py-3 shadow-lg hover:shadow-xl transition-all duration-300"
                      >
                        {isExecutingTx ? (
                          <>
                            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Processing...
                          </>
                        ) : (
                          <>
                            <ArrowRightLeft className="h-5 w-5 mr-2" />
                            Execute Cross-Chain Transaction
                          </>
                        )}
                      </Button>
                    )}
                  </div>

                  {/* Debugging - Show Selected Chains (can be removed in production) */}
                  {selectedChains.length > 0 && (
                    <Card className="bg-slate-800/50 border-slate-700 shadow-lg mb-6">
                      <CardHeader>
                        <CardTitle className="text-white text-lg">Selected Chains</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2">
                          {selectedChains.map((chain) => (
                            <div key={chain.id} className="px-3 py-1 bg-slate-700 rounded-md text-white">
                              {chain.name} (ID: {chain.id})
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {selectedAssetForDeepDive && portfolioData ? (
                    <AssetDeepDiveCard 
                      asset={selectedAssetForDeepDive} 
                      requestTimeframe={portfolioData.overall_request_summary.timeframe}
                      onClose={handleCloseDeepDive} 
                    />
                  ) : (
                    globalPortfolioData && portfolioDetailsToDisplay && (
                      <>
                        <OverallRequestSummaryCard summary={portfolioData.overall_request_summary} />
                        
                        <RankedAssetsSummaryCard 
                          assets={globalPortfolioData.data.ranked_assets_summary} 
                          chainName={globalPortfolioData.chain_name} 
                          onAssetSelect={handleAssetSelect} // Pass the handler
                        />
                        
                        {/* Dropdown to select MVO objective for display - moved below ranked assets */}
                        {mvoDisplayOptions.length > 1 && (
                            <Card className="bg-gradient-to-r from-slate-800 to-slate-700 border-slate-600 text-gray-300 shadow-lg">
                                <CardHeader className="pb-3 pt-5 px-6">
                                    <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
                                        <BarChart className="h-5 w-5 text-emerald-400" />
                                        View Portfolio Results For:
                                    </CardTitle>
                                    <CardDescription className="text-slate-300">
                                        Switch between different optimization strategies to compare results.
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="pb-5 px-6">
                                    <div className="flex flex-wrap gap-3">
                                        {mvoDisplayOptions.map(option => (
                                            <Button
                                                key={option.id}
                                                variant={displayedMVOObjective === option.id ? "default" : "outline"}
                                                onClick={() => setDisplayedMVOObjective(option.id)}
                                                className={
                                                    displayedMVOObjective === option.id 
                                                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white border-emerald-600 shadow-md transform hover:scale-105 transition-all duration-200' 
                                                    : 'bg-slate-700/50 hover:bg-slate-600 border-slate-500 text-gray-200 hover:text-white hover:border-slate-400 transition-all duration-200'
                                                }
                                            >
                                                {option.name}
                                            </Button>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                        
                        <OptimizedPortfolioDetailsCard 
                          details={{
                            ...portfolioDetailsToDisplay,
                            asset_details_map: globalPortfolioData.data.ranked_assets_summary.reduce((acc, asset) => {
                              acc[asset.asset] = asset;
                              return acc;
                            }, {} as { [key: string]: RankedAssetSummary })
                          }} 
                          chainName={globalPortfolioData.chain_name} 
                          onAssetSelect={handleAssetSelect}
                        />
                        <MVOInputsSummaryCard 
                          summary={globalPortfolioData.data.mvo_inputs_summary} 
                          chainName={globalPortfolioData.chain_name} 
                          covarianceMatrix={portfolioDetailsToDisplay.covariance_matrix_optimized} // Use displayed portfolio's covariance
                          efficientFrontierPlot={ // Pass the plot as a prop
                            <EfficientFrontierPlot 
                              primaryPortfolio={globalPortfolioData.data.optimized_portfolio_details}
                              alternativePortfolios={globalPortfolioData.data.alternative_optimized_portfolios}
                            />
                          }
                        />
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

