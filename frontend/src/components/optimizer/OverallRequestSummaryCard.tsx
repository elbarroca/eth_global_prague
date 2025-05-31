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
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn bg-slate-800 border-slate-700 text-gray-300">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl font-semibold text-emerald-400">
          <Info className="h-6 w-6 text-emerald-500" />
          Optimization Summary
        </CardTitle>
        <CardDescription className="text-slate-400">Overview of the optimization request and results.</CardDescription>
      </CardHeader>
      <CardContent className="grid md:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-4 text-sm pt-2">
        <div className="flex justify-between border-b border-slate-600 pb-2">
          <span className="font-medium text-slate-300">Requested Chains:</span>
          <span className="text-slate-100">{summary.requested_chain_ids.join(', ')}</span>
        </div>
        <div className="flex justify-between border-b border-slate-600 pb-2">
          <span className="font-medium text-slate-300">Timeframe:</span>
          <span className="text-slate-100">{summary.timeframe}</span>
        </div>
        <div className="flex justify-between border-b border-slate-600 pb-2">
          <span className="font-medium text-slate-300">MVO Objective:</span>
          <span className="text-slate-100">{summary.mvo_objective.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
        </div>
        <div className="flex justify-between border-b border-slate-600 pb-2">
          <span className="font-medium text-slate-300">Risk-Free Rate:</span>
          <span className="text-teal-400 font-semibold">{(summary.risk_free_rate * 100).toFixed(2)}%</span>
        </div>
        <div className="flex justify-between border-b border-slate-600 pb-2">
          <span className="font-medium text-slate-300">Max Tokens Screened:</span>
          <span className="text-slate-100">{summary.max_tokens_per_chain_screening}</span>
        </div>
        <div className="flex justify-between border-b border-slate-600 pb-2">
          <span className="font-medium text-slate-300">Total Unique Assets:</span>
          <span className="text-slate-100">{summary.total_unique_assets_after_screening}</span>
        </div>
        <div className="flex justify-between border-b border-slate-600 pb-2">
          <span className="font-medium text-slate-300">Assets in MVO:</span>
          <span className="text-slate-100">{summary.assets_considered_for_global_mvo}</span>
        </div>
        <div className="flex justify-between border-b border-slate-600 pb-2">
          <span className="font-medium text-slate-300">Assets in Final Portfolio:</span>
          <span className="text-slate-100">{summary.assets_in_final_portfolio}</span>
        </div>
        <div className="flex justify-between border-b border-slate-600 pb-2">
          <span className="font-medium text-slate-300">Processing Time:</span>
          <span className="text-teal-400 font-semibold">{summary.total_processing_time_seconds.toFixed(2)}s</span>
        </div>
        {Object.entries(summary.chain_data_gathering_summary).map(([chainId, chainData]) => (
            <div className="flex justify-between border-b border-slate-600 pb-2" key={chainId}>
                <span className="font-medium text-slate-300">{chainData.chain_name} Assets:</span>
                <span className="text-slate-100">{chainData.assets_found}</span>
            </div>
        ))}
      </CardContent>
    </Card>
  );
}; 