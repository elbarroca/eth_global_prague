"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, HelpCircle, TrendingUp, BarChart3 } from 'lucide-react';
import { MVOInputsSummary, OptimizedPortfolioDetails } from '@/types/portfolio-api';
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import CovarianceMatrixHeatmap from './CovarianceMatrixHeatmap';

interface MVOInputsSummaryCardProps {
  summary: MVOInputsSummary;
  chainName: string;
  covarianceMatrix?: OptimizedPortfolioDetails['covariance_matrix_optimized'];
  efficientFrontierPlot?: React.ReactNode;
}

export const MVOInputsSummaryCard: React.FC<MVOInputsSummaryCardProps> = ({ summary, chainName, covarianceMatrix, efficientFrontierPlot }) => {
  const topReturns = Object.entries(summary.expected_returns_top_n)
    .sort(([,a],[,b]) => b-a)
    .slice(0, 10); // Display top 10 or fewer based on API response

  return (
    <Card className="shadow-2xl transition-all duration-500 ease-out hover:shadow-3xl opacity-0 animate-fadeIn animation-delay-600 bg-gradient-to-br from-slate-800/95 via-slate-850/95 to-slate-900/95 border border-slate-700/80 text-gray-300 rounded-xl overflow-hidden backdrop-blur-md">
      <div className="absolute inset-0 bg-gradient-to-tr from-blue-500/5 via-transparent to-transparent pointer-events-none opacity-50" />
      <CardHeader className="relative border-b border-slate-700/70 px-7 py-6">
        <CardTitle className="flex items-center gap-3.5 text-xl font-bold text-white tracking-tight">
          <div className="p-2.5 rounded-lg bg-gradient-to-br from-blue-500/20 to-indigo-500/20 backdrop-blur-sm shadow-md">
            <FileText className="h-6 w-6 text-blue-300" />
          </div>
          <span>MVO Analysis Inputs</span>
          <span className="text-base font-normal text-slate-400 ml-1">({chainName})</span>
        </CardTitle>
        <CardDescription className="text-slate-400 text-sm mt-2.5 ml-[50px]">
          Mathematical foundation and data inputs used for Mean-Variance Optimization.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-8 p-7 relative">
        
        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-slate-700/40 rounded-lg p-4 border border-slate-700/60 shadow-sm hover:bg-slate-700/60 transition-all duration-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-blue-400" />
                Matrix Dimensions
              </span>
            </div>
            <p className="text-2xl font-bold text-blue-300 tabular-nums">{summary.covariance_matrix_shape}</p>
            <p className="text-xs text-slate-400 mt-1">Asset correlation matrix size</p>
          </div>
          
          <div className="bg-slate-700/40 rounded-lg p-4 border border-slate-700/60 shadow-sm hover:bg-slate-700/60 transition-all duration-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-emerald-400" />
                Valid Assets
              </span>
            </div>
            <p className="text-2xl font-bold text-emerald-300 tabular-nums">{summary.valid_symbols_count_for_mvo}</p>
            <p className="text-xs text-slate-400 mt-1">Assets included in optimization</p>
          </div>
        </div>
        
        {/* Top Expected Returns */}
        <div>
          <h4 className="font-semibold text-lg mb-4 text-slate-100 flex items-center gap-2.5">
            <span className="w-2 h-4 bg-emerald-400 rounded-sm block"></span>
            Top Expected Returns (Annualized)
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-5 w-5 text-slate-400 cursor-help hover:text-slate-300 transition-colors" />
                </TooltipTrigger>
                <TooltipContent className="bg-slate-800/95 text-slate-200 border-slate-600 backdrop-blur-md shadow-xl rounded-lg">
                  <p className="text-sm">Top 10 assets by projected annual returns used in MVO calculation.</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </h4>
          {topReturns.length === 0 ? (
            <div className="p-6 h-48 flex items-center justify-center bg-slate-800/40 rounded-lg text-slate-500 italic border border-slate-700">
              No expected returns data available for display.
            </div>
          ) : (
            <div className="bg-slate-800/40 rounded-lg border border-slate-700/60 shadow-inner">
              <ScrollArea className="h-64 p-4">
                <div className="space-y-2.5">
                  {topReturns.map(([asset, returnValue], index) => (
                    <div 
                      key={asset} 
                      className="flex justify-between items-center p-3 rounded-lg bg-slate-700/40 border border-slate-600/50 hover:bg-slate-700/70 hover:border-slate-600 transition-all duration-200 group"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-emerald-500/20 to-green-500/20 flex items-center justify-center text-xs font-bold text-emerald-300 border border-emerald-500/30">
                          {index + 1}
                        </div>
                        <span className="font-medium text-slate-200 truncate max-w-[200px] group-hover:text-white transition-colors" title={asset}>
                          {asset}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-emerald-400 font-bold text-base tabular-nums">
                          {(typeof returnValue === 'number' ? returnValue : 0).toFixed(2)}%
                        </span>
                        <TrendingUp className="h-4 w-4 text-emerald-400 opacity-60 group-hover:opacity-100 transition-opacity" />
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}
        </div>

        {/* Covariance Matrix Section */}
        <div className="pt-6 border-t border-slate-700/60">
          <h4 className="font-semibold text-lg mb-4 text-slate-100 flex items-center gap-2.5">
            <span className="w-2 h-4 bg-blue-400 rounded-sm block"></span>
            Asset Correlation Matrix
          </h4>
          {covarianceMatrix && Object.keys(covarianceMatrix).length > 0 ? (
            <div className="bg-slate-800/40 rounded-lg border border-slate-700/60 p-4 shadow-inner">
              <CovarianceMatrixHeatmap covarianceMatrix={covarianceMatrix} />
            </div>
          ) : (
            <div className="p-8 h-40 flex flex-col items-center justify-center bg-slate-800/40 rounded-lg text-slate-500 italic border border-slate-700 space-y-2">
              <BarChart3 className="h-8 w-8 text-slate-600" />
              <p className="text-center text-sm">
                {summary.valid_symbols_count_for_mvo > 0 ? 
                  (covarianceMatrix ? "Covariance data not available or no assets in matrix." : "Covariance data not provided.") :
                  "No assets were considered for MVO, so no covariance matrix generated."
                }
              </p>
            </div>
          )}
        </div>

        {/* Efficient Frontier Plot */}
        {efficientFrontierPlot && (
          <div className="pt-6 border-t border-slate-700/60">
            <h4 className="font-semibold text-lg mb-4 text-slate-100 flex items-center gap-2.5">
              <span className="w-2 h-4 bg-purple-400 rounded-sm block"></span>
              Efficient Frontier Analysis
            </h4>
            <div className="bg-slate-800/40 rounded-lg border border-slate-700/60 p-4 shadow-inner">
              {efficientFrontierPlot}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}; 