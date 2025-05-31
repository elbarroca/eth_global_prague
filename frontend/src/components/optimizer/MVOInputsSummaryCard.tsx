"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, HelpCircle } from 'lucide-react';
import { MVOInputsSummary } from '@/types/portfolio-api';
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface MVOInputsSummaryCardProps {
  summary: MVOInputsSummary;
  chainName: string;
}

export const MVOInputsSummaryCard: React.FC<MVOInputsSummaryCardProps> = ({ summary, chainName }) => {
  const topReturns = Object.entries(summary.expected_returns_top_n)
    .sort(([,a],[,b]) => b-a)
    .slice(0, 5); // Display top 5

  return (
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn animation-delay-600">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl font-semibold">
          <FileText className="h-6 w-6 text-yellow-500" />
          MVO Inputs <span className="text-base font-normal text-gray-500">({chainName})</span>
        </CardTitle>
        <CardDescription>Summary of inputs used for the Mean-Variance Optimization model.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 pt-2 text-sm">
        <div className="flex justify-between items-center border-b pb-2">
          <span className="font-medium text-gray-600">Covariance Matrix Shape:</span>
          <span className="text-gray-800 tabular-nums">{summary.covariance_matrix_shape}</span>
        </div>
        <div className="flex justify-between items-center border-b pb-2">
          <span className="font-medium text-gray-600">Valid Symbols for MVO:</span>
          <span className="text-gray-800 tabular-nums">{summary.valid_symbols_count_for_mvo}</span>
        </div>
        
        <div>
          <h4 className="font-semibold text-md mb-2 text-gray-700 flex items-center gap-1.5">
            Top Expected Returns (Annualized)
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                </TooltipTrigger>
                <TooltipContent>
                  <p>Top 5 assets by projected annual returns used in MVO.</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </h4>
          {topReturns.length === 0 ? (
            <p className="text-muted-foreground">No expected returns data to display.</p>
          ) : (
            <ScrollArea className="h-40 rounded-md border p-3 bg-gray-50/50">
              <div className="space-y-1.5">
                {topReturns.map(([asset, returnValue]) => (
                  <div key={asset} className="flex justify-between items-center text-xs p-1.5 rounded hover:bg-gray-100">
                    <span className="font-medium text-gray-700 truncate max-w-[60%]">{asset}</span>
                    <span className="text-green-600 font-semibold tabular-nums">{(returnValue).toFixed(2)}%</span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>

        {/* Placeholder for Covariance Matrix Visualization */}
        <div className="mt-4 pt-4 border-t">
            <h4 className="font-semibold text-md mb-2 text-gray-700">Covariance Matrix (Placeholder)</h4>
            <div className="p-4 h-32 flex items-center justify-center bg-gray-50 rounded-md text-muted-foreground">
                Heatmap or simplified view of the covariance matrix could be here.
            </div>
        </div>
      </CardContent>
    </Card>
  );
}; 