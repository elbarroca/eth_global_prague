"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, HelpCircle } from 'lucide-react';
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
}

export const MVOInputsSummaryCard: React.FC<MVOInputsSummaryCardProps> = ({ summary, chainName, covarianceMatrix }) => {
  const topReturns = Object.entries(summary.expected_returns_top_n)
    .sort(([,a],[,b]) => b-a)
    .slice(0, 10); // Display top 10 or fewer based on API response

  return (
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn animation-delay-600 bg-slate-800 border-slate-700 text-gray-300">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl font-semibold text-white">
          <FileText className="h-6 w-6 text-white" />
          MVO Inputs <span className="text-base font-normal text-slate-400">({chainName})</span>
        </CardTitle>
        <CardDescription className="text-slate-400">Summary of inputs used for the Mean-Variance Optimization model.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 pt-2 text-sm">
        <div className="flex justify-between items-center border-b border-slate-600 pb-2">
          <span className="font-medium text-slate-300">Covariance Matrix Shape:</span>
          <span className="text-slate-100 tabular-nums">{summary.covariance_matrix_shape}</span>
        </div>
        <div className="flex justify-between items-center border-b border-slate-600 pb-2">
          <span className="font-medium text-slate-300">Valid Symbols for MVO:</span>
          <span className="text-slate-100 tabular-nums">{summary.valid_symbols_count_for_mvo}</span>
        </div>
        
        <div>
          <h4 className="font-semibold text-md mb-2 text-slate-200 flex items-center gap-1.5">
            Top Expected Returns (Annualized)
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-4 w-4 text-slate-400 cursor-help" />
                </TooltipTrigger>
                <TooltipContent className="bg-slate-700 text-slate-200 border-slate-600">
                  <p>Top 10 assets by projected annual returns used in MVO.</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </h4>
          {topReturns.length === 0 ? (
            <p className="text-slate-500 italic">No expected returns data to display.</p>
          ) : (
            <ScrollArea className="h-40 rounded-md border border-slate-600 p-3 bg-slate-700/30 custom-scrollbar">
              <div className="space-y-1.5">
                {topReturns.map(([asset, returnValue]) => (
                  <div key={asset} className="flex justify-between items-center text-xs p-1.5 rounded hover:bg-slate-600/50">
                    <span className="font-medium text-slate-200 truncate max-w-[60%]">{asset}</span>
                    <span className="text-green-400 font-semibold tabular-nums">{(typeof returnValue === 'number' ? returnValue : 0).toFixed(2)}%</span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-slate-700">
            <h4 className="font-semibold text-md mb-2 text-slate-200">Covariance Matrix (Optimized Assets)</h4>
            {covarianceMatrix && Object.keys(covarianceMatrix).length > 0 ? (
                <CovarianceMatrixHeatmap covarianceMatrix={covarianceMatrix} />
            ) : (
            <div className="p-4 h-32 flex items-center justify-center bg-slate-700/50 rounded-md text-slate-500 italic">
                {summary.valid_symbols_count_for_mvo > 0 ? 
                    (covarianceMatrix ? "Covariance data not available or no assets in matrix." : "Covariance data not provided.") :
                    "No assets were considered for MVO, so no covariance matrix generated."
                }
            </div>
            )}
        </div>
      </CardContent>
    </Card>
  );
}; 