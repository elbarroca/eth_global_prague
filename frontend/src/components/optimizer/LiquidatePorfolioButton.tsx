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
  const { address, isConnected } = useAccount();
  const { data: balance, isLoading: balanceLoading } = useBalance({
    address: address,
  });
  
  const [totalPortfolioValue, setTotalPortfolioValue] = useState<number>(0);

  useEffect(() => {
    // Use provided portfolioTotalValueUSD if available, otherwise calculate from wallet balance
    if (portfolioTotalValueUSD !== undefined) {
      setTotalPortfolioValue(portfolioTotalValueUSD);
    } else {
      const mockValue = balance ? parseFloat(formatEther(balance.value)) * 10 : 1000; 
      setTotalPortfolioValue(mockValue);
    }
  }, [balance, portfolioTotalValueUSD]);

  // Calculate chain allocations based on actual portfolio assets
  const calculateBridgeAllocations = (): BridgeAllocation[] => {
    const chainAllocations: { [chainId: string]: { percentage: number; assets: string[] } } = {};
    
    // Parse portfolio weights to determine chain allocations
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
      
      // Only include if chain is in selectedChains
      if (selectedChains.includes(chainId)) {
        if (!chainAllocations[chainId]) {
          chainAllocations[chainId] = { percentage: 0, assets: [] };
        }
        chainAllocations[chainId].percentage += weight * 100;
        chainAllocations[chainId].assets.push(parts[0] || assetTicker);
      }
    });

    // Convert to BridgeAllocation format
    const allocations: BridgeAllocation[] = Object.entries(chainAllocations).map(([chainId, data]) => {
      const chainOpt = chainOptions.find(opt => opt.id === chainId);
      const estimatedValue = (totalPortfolioValue * data.percentage / 100).toFixed(2);
      
      return {
        chainId,
        chainName: chainOpt?.name || 'Unknown Chain',
        chainIcon: chainOpt?.icon || '🔗',
        percentage: data.percentage,
        estimatedValue: `$${estimatedValue}`,
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

  const handleLiquidate = async () => {
    setIsLiquidating(true);
    try {
      console.log('Initiating portfolio liquidation with settings:', {
        bridgeAllocations,
        totalPortfolioValue,
        connectedWallet: address,
      });
      
      await new Promise(resolve => setTimeout(resolve, 2500)); 
      
      alert(`Portfolio Liquidation Process Simulated!\nTotal Value: $${totalPortfolioValue.toFixed(2)}\n${bridgeAllocations.length} chains targeted for bridging.\n(This is a UI demonstration)`);
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
                          <span className="block text-slate-300">Wallet Balance: <span className="font-semibold text-pink-300">{parseFloat(formatEther(balance.value)).toFixed(4)} {balance.symbol}</span></span>
                          <span className="block text-slate-300">Portfolio Value: <span className="font-semibold text-pink-300">${totalPortfolioValue.toFixed(2)}</span></span>
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
                              <span className="text-xs text-pink-400 font-medium">Value: {allocation.estimatedValue}</span>
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
                        <span>Total Portfolio Value:</span>
                        <span className="font-bold text-pink-300 text-base">${totalPortfolioValue.toFixed(2)}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>Chains to Bridge:</span>
                        <span className="font-medium text-slate-300">{bridgeAllocations.length} chain{bridgeAllocations.length !== 1 ? 's' : ''}</span>
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
                          Execute Liquidation & Bridge ({bridgeAllocations.length} chain{bridgeAllocations.length !== 1 ? 's' : ''})
                          <ExternalLink className="ml-2 h-4 w-4 opacity-80 group-hover:opacity-100 transition-opacity" />
                        </>
                      )}
                    </Button>
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