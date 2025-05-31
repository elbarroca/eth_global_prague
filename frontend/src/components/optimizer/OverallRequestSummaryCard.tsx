"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Info, Layers, TrendingUp, CheckCircle, AlertCircle } from 'lucide-react';
import { OverallRequestSummary } from '@/types/portfolio-api';

interface OverallRequestSummaryCardProps {
  summary: OverallRequestSummary;
}

const getChainNames = (chainIds: number[], chainDataSummary: OverallRequestSummary['chain_data_gathering_summary']) => {
  return chainIds.map(id => chainDataSummary[String(id)]?.chain_name || `Chain ${id}`).join(', ');
};

export const OverallRequestSummaryCard: React.FC<OverallRequestSummaryCardProps> = ({ summary }) => {
  const processingTime = summary.total_processing_time_seconds?.toFixed(2) || 'N/A';
  const isSuccessful = Object.values(summary.chain_data_gathering_summary).every(chain => chain.status.startsWith('success'));

  return (
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn bg-slate-800 border-slate-700 text-gray-300">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-xl font-semibold text-white">
          {isSuccessful ? <CheckCircle className="h-6 w-6 text-green-400" /> : <AlertCircle className="h-6 w-6 text-amber-400" />}
          Optimization Summary
        </CardTitle>
        <CardDescription className="text-slate-400">
          Key parameters and outcome of your portfolio optimization request.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid md:grid-cols-2 gap-x-6 gap-y-3 text-sm pt-2">
        <SummaryItem label="Chains Requested" value={getChainNames(summary.requested_chain_ids, summary.chain_data_gathering_summary)} />
        <SummaryItem label="Timeframe" value={summary.timeframe} />
        <SummaryItem label="MVO Objective" value={summary.mvo_objective.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} />
        <SummaryItem label="Risk-Free Rate" value={`${(summary.risk_free_rate * 100).toFixed(2)}%`} valueClassName="text-teal-400 font-semibold" />
        
        <SummaryItem label="Max Tokens Screened" value={summary.max_tokens_per_chain_screening} />
        <SummaryItem label="Total Unique Assets" value={summary.total_unique_assets_after_screening} />
        <SummaryItem label="Assets in MVO" value={summary.assets_considered_for_global_mvo} />
        <SummaryItem label="Assets in Final Portfolio" value={summary.assets_in_final_portfolio} />
        
        <SummaryItem label="Processing Time" value={`${processingTime}s`} valueClassName="text-teal-400 font-semibold" />
        {Object.entries(summary.chain_data_gathering_summary).map(([chainId, chainData]) => (
             <SummaryItem 
                key={chainId} 
                label={`${chainData.chain_name} Assets Found`} 
                value={chainData.assets_found} 
             />
        ))}
      </CardContent>
    </Card>
  );
};

interface SummaryItemProps {
  label: string;
  value: string | number;
  valueClassName?: string;
}

const SummaryItem: React.FC<SummaryItemProps> = ({ label, value, valueClassName }) => (
  <div className="flex justify-between items-center border-b border-slate-700 py-2">
    <span className="font-medium text-slate-300">{label}:</span>
    <span className={valueClassName || "text-slate-100"}>{value}</span>
  </div>
); 