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
}

interface BridgeAllocation {
  chainId: string;
  chainName: string;
  chainIcon: string;
  percentage: number;
  estimatedValue: string;
}

export const LiquidatePortfolioButton: React.FC<LiquidatePortfolioButtonProps> = ({
  portfolioWeights,
  selectedChains,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLiquidating, setIsLiquidating] = useState(false);
  const { address, isConnected } = useAccount();
  const { data: balance, isLoading: balanceLoading } = useBalance({
    address: address,
  });
  
  // Mock portfolio value - in real implementation, this would come from actual portfolio data
  const [totalPortfolioValue, setTotalPortfolioValue] = useState<number>(0);

  useEffect(() => {
    // Calculate total portfolio value based on weights and mock values
    // In real implementation, this would fetch actual token balances and prices
    const mockValue = balance ? parseFloat(formatEther(balance.value)) * 10 : 1000; // Mock multiplier
    setTotalPortfolioValue(mockValue);
  }, [balance]);

  // Calculate bridge allocations based on portfolio weights and selected chains
  const calculateBridgeAllocations = (): BridgeAllocation[] => {
    const totalAssets = Object.keys(portfolioWeights).length;
    const chainsWithAssets = selectedChains.filter(chainId => 
      chainOptions.find(chain => chain.id === chainId)
    );

    if (chainsWithAssets.length === 0) return [];

    // Distribute assets evenly across selected chains for simplification
    // In a real implementation, this would be based on actual asset distribution
    const basePercentage = 100 / chainsWithAssets.length;
    
    return chainsWithAssets.map((chainId, index) => {
      const chainOption = chainOptions.find(chain => chain.id === chainId);
      if (!chainOption) return null;

      // Add some variation to make it more realistic
      const variation = (Math.random() - 0.5) * 20; // ±10% variation
      let percentage = basePercentage + variation;
      
      // Ensure percentages are positive and sum to 100%
      if (index === chainsWithAssets.length - 1) {
        // Last chain gets the remainder to ensure total is 100%
        const usedPercentage = chainsWithAssets.slice(0, -1).reduce((sum, _, i) => {
          const prevVariation = (Math.random() - 0.5) * 20;
          return sum + Math.max(5, basePercentage + prevVariation);
        }, 0);
        percentage = Math.max(5, 100 - usedPercentage);
      } else {
        percentage = Math.max(5, percentage);
      }

      const estimatedValue = (totalPortfolioValue * percentage / 100).toFixed(2);
      
      return {
        chainId,
        chainName: chainOption.name,
        chainIcon: chainOption.icon,
        percentage: Math.round(percentage * 100) / 100,
        estimatedValue: `$${estimatedValue}`,
      };
    }).filter(Boolean) as BridgeAllocation[];
  };

  const bridgeAllocations = calculateBridgeAllocations();
  const totalValue = Object.values(portfolioWeights).reduce((sum, weight) => sum + weight, 0);

  const handleLiquidate = async () => {
    setIsLiquidating(true);
    
    try {
      // Simulate liquidation process
      console.log('Liquidating portfolio with bridge allocations:', bridgeAllocations);
      console.log('Total portfolio value:', totalPortfolioValue);
      console.log('Connected wallet:', address);
      
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      alert(`Portfolio liquidation initiated! 
      Total Value: $${totalPortfolioValue.toFixed(2)}
      Bridge Allocations: ${bridgeAllocations.length} chains
      (This is a demo)`);
      
      setIsOpen(false); // Close the collapsible after successful liquidation
    } catch (error) {
      console.error('Liquidation failed:', error);
      alert('Liquidation failed. Please try again.');
    } finally {
      setIsLiquidating(false);
    }
  };

  return (
    <div className="mt-6">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <Button 
            className="w-full bg-gradient-to-r from-emerald-600 to-emerald-700 hover:from-emerald-700 hover:to-emerald-800 text-white font-bold text-lg py-4 px-8 rounded-xl shadow-lg hover:shadow-xl transition-all duration-500 transform hover:scale-105 group relative overflow-hidden animate-pulse hover:animate-none"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-400/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
            <span className="relative z-10 flex items-center justify-center gap-3">
              <ArrowRightLeft className={`h-6 w-6 transition-transform duration-300 ${isOpen ? 'rotate-12' : ''}`} />
              <span className="transition-all duration-300">Liquidate Portfolio</span>
              <ChevronDown className={`h-5 w-5 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
            </span>
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent 
          className="mt-4"
        >
          <Card className="bg-slate-800/95 border-slate-600/50 backdrop-blur-sm shadow-lg">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
                <ArrowRightLeft className="h-5 w-5 text-emerald-400" />
                Bridge Asset Distribution
              </CardTitle>
              <CardDescription className="text-slate-300 text-sm">
                Assets will be bridged to the following chains based on optimal distribution:
                {isConnected && (
                  <div className="mt-2 p-2 bg-slate-700/50 rounded-md flex items-center gap-2">
                    <Wallet className="h-4 w-4 text-emerald-400" />
                    <span className="text-xs">
                      {balanceLoading ? (
                        "Loading wallet balance..."
                      ) : balance ? (
                        `Wallet Balance: ${parseFloat(formatEther(balance.value)).toFixed(4)} ${balance.symbol} | Portfolio Value: $${totalPortfolioValue.toFixed(2)}`
                      ) : (
                        `Portfolio Value: $${totalPortfolioValue.toFixed(2)}`
                      )}
                    </span>
                  </div>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {bridgeAllocations.length === 0 ? (
                <p className="text-slate-500 italic text-center py-4">
                  No chains selected for bridging
                </p>
              ) : (
                <>
                  {bridgeAllocations.map((allocation) => (
                    <div key={allocation.chainId} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-xl">{allocation.chainIcon}</span>
                          <div className="flex flex-col">
                            <span className="font-medium text-slate-200">{allocation.chainName}</span>
                            <span className="text-xs text-emerald-400 font-medium">{allocation.estimatedValue}</span>
                          </div>
                        </div>
                        <span className="text-white font-semibold">
                          {allocation.percentage.toFixed(1)}%
                        </span>
                      </div>
                      <Progress 
                        value={allocation.percentage} 
                        className="h-2 bg-slate-700 [&>div]:bg-gradient-to-r [&>div]:from-emerald-500 [&>div]:to-emerald-600" 
                      />
                    </div>
                  ))}
                  
                  <div className="pt-4 border-t border-slate-600/50">
                    <div className="space-y-2 mb-3">
                      <div className="flex items-center justify-between text-sm text-slate-400">
                        <span>Total Portfolio Value:</span>
                        <span className="font-medium text-emerald-400">${totalPortfolioValue.toFixed(2)}</span>
                      </div>
                      {isConnected && address && (
                        <div className="flex items-center justify-between text-xs text-slate-500">
                          <span>Connected Wallet:</span>
                          <span className="font-mono">{address.slice(0, 6)}...{address.slice(-4)}</span>
                        </div>
                      )}
                    </div>
                    
                    <Button 
                      onClick={handleLiquidate}
                      disabled={isLiquidating || !isConnected}
                      className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-semibold py-2 rounded-lg transition-all duration-300 transform hover:scale-105 shadow-md hover:shadow-lg disabled:transform-none disabled:shadow-none"
                    >
                      {isLiquidating ? (
                        <>
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Processing...
                        </>
                      ) : (
                        <>
                          Confirm Liquidation
                          <ExternalLink className="ml-2 h-4 w-4" />
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