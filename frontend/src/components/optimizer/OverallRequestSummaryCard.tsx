"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Info } from 'lucide-react';
import { OverallRequestSummary } from '@/types/portfolio-api';

interface OverallRequestSummaryCardProps {
  summary: OverallRequestSummary;
}

export const OverallRequestSummaryCard: React.FC<OverallRequestSummaryCardProps> = ({ summary }) => {
  return (
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl font-semibold">
          <Info className="h-6 w-6 text-blue-500" />
          Optimization Summary
        </CardTitle>
        <CardDescription>Overview of the optimization request and results.</CardDescription>
      </CardHeader>
      <CardContent className="grid md:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-3 text-sm pt-2">
        <div className="flex justify-between border-b pb-1">
          <span className="font-medium text-gray-600">Requested Chains:</span>
          <span className="text-gray-800">{summary.requested_chain_ids.join(', ')}</span>
        </div>
        <div className="flex justify-between border-b pb-1">
          <span className="font-medium text-gray-600">Timeframe:</span>
          <span className="text-gray-800">{summary.timeframe}</span>
        </div>
        <div className="flex justify-between border-b pb-1">
          <span className="font-medium text-gray-600">MVO Objective:</span>
          <span className="text-gray-800">{summary.mvo_objective.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
        </div>
        <div className="flex justify-between border-b pb-1">
          <span className="font-medium text-gray-600">Risk-Free Rate:</span>
          <span className="text-gray-800">{(summary.risk_free_rate * 100).toFixed(2)}%</span>
        </div>
        <div className="flex justify-between border-b pb-1">
          <span className="font-medium text-gray-600">Max Tokens Screened:</span>
          <span className="text-gray-800">{summary.max_tokens_per_chain_screening}</span>
        </div>
        <div className="flex justify-between border-b pb-1">
          <span className="font-medium text-gray-600">Total Unique Assets:</span>
          <span className="text-gray-800">{summary.total_unique_assets_after_screening}</span>
        </div>
        <div className="flex justify-between border-b pb-1">
          <span className="font-medium text-gray-600">Assets in MVO:</span>
          <span className="text-gray-800">{summary.assets_considered_for_global_mvo}</span>
        </div>
        <div className="flex justify-between border-b pb-1">
          <span className="font-medium text-gray-600">Assets in Final Portfolio:</span>
          <span className="text-gray-800">{summary.assets_in_final_portfolio}</span>
        </div>
        <div className="flex justify-between border-b pb-1">
          <span className="font-medium text-gray-600">Processing Time:</span>
          <span className="text-gray-800">{summary.total_processing_time_seconds.toFixed(2)}s</span>
        </div>
        {Object.entries(summary.chain_data_gathering_summary).map(([chainId, chainData]) => (
            <div className="flex justify-between border-b pb-1" key={chainId}>
                <span className="font-medium text-gray-600">{chainData.chain_name} Assets:</span>
                <span className="text-gray-800">{chainData.assets_found}</span>
            </div>
        ))}
      </CardContent>
    </Card>
  );
}; 