"use client";

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Progress } from "@/components/ui/progress";
import { ArrowRightLeft, ChevronDown, ExternalLink, Wallet } from 'lucide-react';
import { chainOptions, ChainOption } from '@/types/portfolio-api';
import { useAccount, useBalance } from 'wagmi';
import { formatEther } from 'viem';
import { useOrder } from '@/hooks/1inch/useOrder';
import { TOKEN_ADDRESS, SPENDER } from '@/hooks/1inch/useOrder';
import { SupportedChain } from '@1inch/cross-chain-sdk';

interface LiquidatePortfolioButtonProps {
  portfolioWeights: { [key: string]: number };
  selectedChains: string[];
  portfolioTotalValueUSD?: number; // Optional prop for total portfolio value
}

interface BridgeAllocation {
  chainId: string;
  chainName: string;
  chainIcon: string;
  percentage: number;
  estimatedValue: string;
  assets: string[]; // Assets allocated to this chain
}

export const LiquidatePortfolioButton: React.FC<LiquidatePortfolioButtonProps> = ({
  portfolioWeights,
  selectedChains,
  portfolioTotalValueUSD,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLiquidating, setIsLiquidating] = useState(false);
  const [isExecutingTx, setIsExecutingTx] = useState(false);
  const { address, isConnected } = useAccount();
  const { data: balance, isLoading: balanceLoading } = useBalance({
    address: address,
  });
  const { getQuoteAndExecuteOrder, isSDKAvailable } = useOrder();
  
  const [totalPortfolioValue, setTotalPortfolioValue] = useState<number>(0);

  useEffect(() => {
    // Use user's actual WETH balance as portfolio value (in ETH, not USD)
    if (balance && parseFloat(formatEther(balance.value)) > 0) {
      const ethBalance = parseFloat(formatEther(balance.value));
      setTotalPortfolioValue(ethBalance); // Store as ETH amount, not USD
    } else {
      // Fallback to minimal ETH amount if no balance
      setTotalPortfolioValue(0.01); // 0.01 ETH
    }
  }, [balance, portfolioWeights]);

  // Calculate chain allocations based on actual portfolio assets (excluding Base chain from UI)
  const calculateBridgeAllocations = (): BridgeAllocation[] => {
    const chainAllocations: { [chainId: string]: { percentage: number; assets: string[] } } = {};
    const baseChainId = '8453'; // Base chain (source)
    
    // Parse portfolio weights to determine target chain allocations
    Object.entries(portfolioWeights).forEach(([assetTicker, weight]) => {
      // Extract chain information from asset ticker (e.g., "ETH-USDC_on_Ethereum")
      const parts = assetTicker.split('_on_');
      let chainName = parts[1] || 'Unknown';
      
      // Map chain names to chain IDs
      let chainId = '1'; // Default to Ethereum
      if (chainName.toLowerCase().includes('polygon')) chainId = '137';
      else if (chainName.toLowerCase().includes('base')) chainId = '8453';
      else if (chainName.toLowerCase().includes('arbitrum')) chainId = '42161';
      else if (chainName.toLowerCase().includes('optimism')) chainId = '10';
      else if (chainName.toLowerCase().includes('avalanche')) chainId = '43114';
      else if (chainName.toLowerCase().includes('bsc') || chainName.toLowerCase().includes('binance')) chainId = '56';
      else if (chainName.toLowerCase().includes('unichain')) chainId = '130';
      
      // Only include target chains (not Base) in UI, but include all chains from portfolio
      if ((selectedChains.includes(chainId) || Object.keys(portfolioWeights).some(asset => asset.includes(chainName))) && chainId !== baseChainId) {
        if (!chainAllocations[chainId]) {
          chainAllocations[chainId] = { percentage: 0, assets: [] };
        }
        chainAllocations[chainId].percentage += weight * 100;
        chainAllocations[chainId].assets.push(parts[0] || assetTicker);
      }
    });

    // If no target chains found, add selected chains as targets with equal distribution
    if (Object.keys(chainAllocations).length === 0) {
      const targetChains = selectedChains.filter(id => id !== baseChainId);
      if (targetChains.length > 0) {
        const percentagePerChain = 100 / targetChains.length;
        targetChains.forEach(chainId => {
          chainAllocations[chainId] = { 
            percentage: percentagePerChain, 
            assets: ['Portfolio Assets'] 
          };
        });
      }
    }

    // Normalize percentages to ensure they add up to 100%
    const totalPercentage = Object.values(chainAllocations).reduce((sum, data) => sum + data.percentage, 0);
    if (totalPercentage > 0) {
      Object.keys(chainAllocations).forEach(chainId => {
        chainAllocations[chainId].percentage = (chainAllocations[chainId].percentage / totalPercentage) * 100;
      });
    }

    // Convert to BridgeAllocation format
    const allocations: BridgeAllocation[] = Object.entries(chainAllocations).map(([chainId, data]) => {
      const chainOpt = chainOptions.find(opt => opt.id === chainId);
      const ethAmount = (totalPortfolioValue * data.percentage / 100);
      
      return {
        chainId,
        chainName: chainOpt?.name || 'Unknown Chain',
        chainIcon: chainOpt?.icon || '🔗',
        percentage: data.percentage,
        estimatedValue: `${ethAmount.toFixed(4)} ETH`, // Show ETH amount instead of USD
        assets: Array.from(new Set(data.assets)), // Remove duplicates
      };
    });

    // Sort by percentage (highest first)
    return allocations.sort((a, b) => b.percentage - a.percentage);
  };

  const bridgeAllocations = calculateBridgeAllocations();
  
  // Check if portfolio contains WETH or ETH
  const hasWETH = Object.keys(portfolioWeights).some(asset => 
    asset.toLowerCase().includes('weth') || asset.toLowerCase().includes('eth')
  );
  
  // Check if user has meaningful wallet balance
  const hasWalletBalance = balance && parseFloat(formatEther(balance.value)) > 0.001;

  // Cross-chain transaction function using 1inch SDK
  const executeTransaction = async () => {
    if (!address || bridgeAllocations.length < 1) {
      console.error("Missing wallet address or no target chains available");
      return;
    }

    if (!isSDKAvailable) {
      alert('1inch SDK not available. Please check environment configuration.');
      return;
    }

    setIsExecutingTx(true);
    try {
      // Base chain is always the source (where we are)
      const baseChainId = '8453';
      const sourceChainName = 'Base';
      
      // Use the first target chain with highest allocation
      const destChain = bridgeAllocations[0];

      console.log(`🔄 Initiating cross-chain liquidation from ${sourceChainName} to ${destChain.chainName}`);

             // Calculate amount based on actual portfolio allocation (in ETH)
       const ethAmount = parseFloat(destChain.estimatedValue.replace(' ETH', ''));
       const bridgePercentage = Math.min(destChain.percentage, 20); // Max 20% of allocation for safety
       const bridgeAmountETH = (ethAmount * bridgePercentage / 100);
       const amountInWei = (bridgeAmountETH * 1e18).toString(); // Convert ETH to Wei

      // 1inch cross-chain parameters
      const crossChainParams = {
        srcChainId: parseInt(baseChainId) as unknown as SupportedChain, // Base
        dstChainId: parseInt(destChain.chainId) as unknown as SupportedChain, // Target chain
        srcTokenAddress: TOKEN_ADDRESS, // WETH on Base
        dstTokenAddress: TOKEN_ADDRESS, // WETH on target chain
        amount: amountInWei,
        enableEstimate: true,
        walletAddress: address
      };

              console.log("🚀 1inch Cross-chain Parameters:", {
        from: `${sourceChainName} (${baseChainId})`,
        to: `${destChain.chainName} (${destChain.chainId})`,
        amount: `${bridgeAmountETH.toFixed(4)} ETH`,
        amountWei: amountInWei,
        walletAddress: address
      });
      
      // Execute 1inch cross-chain transaction
      const result = await getQuoteAndExecuteOrder(crossChainParams);
      console.log("✅ 1inch Transaction Result:", result);
      
      if (result?.success !== false) {
        alert(`🎉 Cross-chain liquidation initiated successfully!
        
From: ${sourceChainName}
To: ${destChain.chainName}
Amount: ${bridgeAmountETH.toFixed(4)} ETH
        
Transaction will be processed by 1inch Fusion.`);
      } else {
        throw new Error(result?.error || 'Transaction failed');
      }
      
    } catch (error) {
      console.error("❌ Cross-chain transaction error:", error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      alert(`❌ Cross-chain liquidation failed: ${errorMessage}`);
    } finally {
      setIsExecutingTx(false);
    }
  };

  const handleLiquidate = async () => {
    setIsLiquidating(true);
    try {
      console.log('Initiating portfolio liquidation with settings:', {
        bridgeAllocations,
        totalPortfolioValue,
        connectedWallet: address,
      });
      
      await new Promise(resolve => setTimeout(resolve, 2500)); 
      
      alert(`Portfolio Liquidation Process Simulated!\nTotal Amount: ${totalPortfolioValue.toFixed(4)} ETH\n${bridgeAllocations.length} chains targeted for bridging.\n(This is a UI demonstration)`);
      setIsOpen(false);
    } catch (error) {
      console.error('Liquidation simulation failed:', error);
      alert('Liquidation simulation failed. See console for details.');
    } finally {
      setIsLiquidating(false);
    }
  };

  return (
    <div className="mt-8 w-full max-w-2xl mx-auto">
      <Collapsible open={isOpen} onOpenChange={setIsOpen} className="rounded-xl overflow-hidden shadow-xl border border-slate-700/80 bg-gradient-to-br from-slate-800 via-slate-850 to-slate-900">
        <CollapsibleTrigger asChild>
          <Button 
            variant="outline"
            className={`w-full text-white font-semibold text-base py-3.5 px-6 rounded-t-xl ${isOpen ? 'rounded-b-none' : 'rounded-b-xl'} shadow-lg hover:shadow-xl transition-all duration-300 group relative overflow-hidden border-0 bg-gradient-to-r from-red-500 via-pink-500 to-rose-500 hover:from-red-600 hover:via-pink-600 hover:to-rose-600 focus:ring-4 focus:ring-pink-500/50 focus:outline-none`}
          >
            <div className="absolute inset-0 bg-gradient-to-r from-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <span className="relative z-10 flex items-center justify-center gap-2.5">
              <ArrowRightLeft className={`h-5 w-5 transition-transform duration-300 group-hover:scale-110 ${isOpen ? 'rotate-90' : ''}`} />
              <span>Liquidate & Bridge Portfolio</span>
              <ChevronDown className={`h-5 w-5 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
            </span>
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent 
          className="border-t border-slate-700/80 bg-slate-800/70 backdrop-blur-sm"
        >
          <Card className="bg-transparent border-0 shadow-none rounded-none">
            <CardHeader className="pb-4 pt-5 px-6">
              <CardTitle className="text-lg font-semibold text-slate-100 flex items-center gap-2.5">
                <span className="w-2 h-4 bg-pink-500 rounded-sm block"></span>
                Confirm Liquidation & Bridge Plan
              </CardTitle>
              <CardDescription className="text-slate-400 text-sm mt-1 ml-[18px] space-y-3">
                <div>Assets will be liquidated and resulting value bridged based on your portfolio allocation:</div>
                
                {/* Wallet Balance - Only show if user has balance */}
                {isConnected && hasWalletBalance && (
                  <div className="p-2.5 bg-slate-700/60 rounded-md flex items-center gap-2.5 border border-slate-600/70 shadow-sm">
                    <Wallet className="h-4 w-4 text-pink-400 flex-shrink-0" />
                    <div className="text-xs leading-tight">
                      {balanceLoading ? (
                        <span className="text-slate-400 italic">Loading wallet balance...</span>
                      ) : (
                        <>
                          <span className="block text-slate-300">Available WETH: <span className="font-semibold text-pink-300">{parseFloat(formatEther(balance.value)).toFixed(4)} {balance.symbol}</span></span>
                          <span className="block text-slate-300">Portfolio to Liquidate: <span className="font-semibold text-pink-300">{totalPortfolioValue.toFixed(4)} ETH</span></span>
                        </>
                      )}
                    </div>
                  </div>
                )}
                
                {/* WETH Warning */}
                {hasWETH && (
                  <div className="p-2.5 bg-amber-600/20 rounded-md border border-amber-500/50 flex items-start gap-2.5">
                    <span className="text-amber-400 text-sm">⚠️</span>
                    <div className="text-xs text-amber-300 leading-tight">
                      <span className="font-semibold block">WETH/ETH Detected</span>
                      <span className="text-amber-400">Ensure you have enough ETH for gas fees on all target chains before proceeding.</span>
                    </div>
                  </div>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="px-6 pb-6 space-y-5">
              {bridgeAllocations.length === 0 ? (
                <p className="text-slate-500 italic text-center py-6 bg-slate-700/30 rounded-md border border-slate-600/50">
                  No chains selected or no assets to bridge.
                </p>
              ) : (
                <>
                  <div className="space-y-4 max-h-72 overflow-y-auto custom-scrollbar pr-2">
                    {bridgeAllocations.map((allocation) => (
                      <div key={allocation.chainId} className="space-y-3 bg-slate-700/40 p-4 rounded-lg border border-slate-600/60 shadow-sm hover:bg-slate-700/60 transition-colors duration-200">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className="text-2xl opacity-90">{allocation.chainIcon}</span>
                            <div>
                              <span className="font-semibold text-slate-100 block text-sm">{allocation.chainName}</span>
                              <span className="text-xs text-pink-400 font-medium">Amount: {allocation.estimatedValue}</span>
                            </div>
                          </div>
                          <span className="text-pink-300 font-bold text-lg">
                            {allocation.percentage.toFixed(1)}%
                          </span>
                        </div>
                        
                        {/* Assets List */}
                        {allocation.assets.length > 0 && (
                          <div className="mt-2">
                            <div className="text-xs text-slate-400 mb-1.5">Assets to bridge:</div>
                            <div className="flex flex-wrap gap-1.5">
                              {allocation.assets.slice(0, 6).map((asset, idx) => (
                                <span 
                                  key={idx} 
                                  className="text-xs bg-slate-600/60 text-slate-200 px-2 py-1 rounded-md border border-slate-500/50 font-medium"
                                >
                                  {asset}
                                </span>
                              ))}
                              {allocation.assets.length > 6 && (
                                <span className="text-xs text-slate-400 px-2 py-1">
                                  +{allocation.assets.length - 6} more
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                        
                        <Progress 
                          value={allocation.percentage} 
                          className="h-3 bg-slate-600/80 rounded [&>div]:bg-gradient-to-r [&>div]:from-pink-500 [&>div]:to-rose-500 shadow-inner" 
                        />
                      </div>
                    ))}
                  </div>
                  
                  <div className="pt-5 border-t border-slate-700/60">
                    <div className="space-y-2 mb-4 text-sm">
                      <div className="flex items-center justify-between text-slate-300">
                        <span>Total Portfolio Amount:</span>
                        <span className="font-bold text-pink-300 text-base">{totalPortfolioValue.toFixed(4)} ETH</span>
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>Target Chains:</span>
                        <span className="font-medium text-slate-300">{bridgeAllocations.length} chain{bridgeAllocations.length !== 1 ? 's' : ''}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>Source Chain:</span>
                        <span className="font-medium text-slate-300">Base (Current)</span>
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>Total Assets:</span>
                        <span className="font-medium text-slate-300">{Object.keys(portfolioWeights).length} asset{Object.keys(portfolioWeights).length !== 1 ? 's' : ''}</span>
                      </div>
                      {isConnected && address && (
                        <div className="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-slate-700/50">
                          <span>Target Wallet:</span>
                          <span className="font-mono bg-slate-700/50 px-1.5 py-0.5 rounded text-slate-300">{address.slice(0, 6)}...{address.slice(-4)}</span>
                        </div>
                      )}
                       {!isConnected && (
                         <p className="text-xs text-amber-400 text-center py-2 px-3 bg-amber-600/20 rounded-md border border-amber-500/50">Please connect your wallet to proceed with liquidation.</p>
                       )}
                    </div>
                    
                    <div className="space-y-3">
                      <Button 
                        onClick={handleLiquidate}
                        disabled={isLiquidating || !isConnected}
                        className="w-full bg-gradient-to-r from-pink-600 via-rose-600 to-red-600 hover:from-pink-700 hover:via-rose-700 hover:to-red-700 disabled:from-slate-600 disabled:via-slate-600 disabled:to-slate-600 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg transition-all duration-300 transform hover:scale-105 shadow-md hover:shadow-lg focus:ring-4 focus:ring-pink-500/60 focus:outline-none group"
                      >
                        {isLiquidating ? (
                          <>
                            <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Liquidating & Bridging...
                          </>
                        ) : (
                          <>
                            Execute Liquidation & Bridge ({bridgeAllocations.length} target chain{bridgeAllocations.length !== 1 ? 's' : ''})
                            <ExternalLink className="ml-2 h-4 w-4 opacity-80 group-hover:opacity-100 transition-opacity" />
                          </>
                        )}
                      </Button>
                      
                      {bridgeAllocations.length >= 1 && isSDKAvailable && (
                        <Button
                          onClick={executeTransaction}
                          disabled={isExecutingTx || !isConnected}
                          className="w-full bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-600 disabled:from-slate-600 disabled:via-slate-600 disabled:to-slate-600 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg transition-all duration-300 transform hover:scale-105 shadow-md hover:shadow-lg focus:ring-4 focus:ring-emerald-500/60 focus:outline-none group"
                        >
                          {isExecutingTx ? (
                            <>
                              <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Processing 1inch Cross-Chain Liquidation...
                            </>
                          ) : (
                            <>
                              <ArrowRightLeft className="mr-2 h-5 w-5" />
                              Execute 1inch Cross-Chain Liquidation (Base → {bridgeAllocations[0]?.chainName || 'Target'})
                            </>
                          )}
                        </Button>
                      )}
                      
                      {!isSDKAvailable && bridgeAllocations.length >= 1 && (
                        <div className="text-xs text-amber-400 text-center py-2 px-3 bg-amber-600/20 rounded-md border border-amber-500/50">
                          1inch cross-chain liquidation unavailable: SDK not configured
                        </div>
                      )}
                      
                      {bridgeAllocations.length < 1 && (
                        <div className="text-xs text-slate-400 text-center py-2 px-3 bg-slate-700/30 rounded-md border border-slate-600/50">
                          No target chains available for cross-chain liquidation
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
};