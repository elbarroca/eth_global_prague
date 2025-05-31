"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Info, Layers, TrendingUp, CheckCircle, AlertCircle } from 'lucide-react';
import { OverallRequestSummary as ApiOverallRequestSummary } from '@/types/portfolio-api';
import { OverallRequestSummary as StoreOverallRequestSummary } from '@/stores/portfolio-store';

// Create a union type that can handle both API and Store versions
type OverallRequestSummary = ApiOverallRequestSummary | StoreOverallRequestSummary;

interface OverallRequestSummaryCardProps {
  summary: OverallRequestSummary;
}

const getChainNames = (chainIds: number[], chainDataSummary: OverallRequestSummary['chain_data_gathering_summary']) => {
  return chainIds.map(id => chainDataSummary[String(id)]?.chain_name || `Chain ${id}`).join(', ');
};

export const OverallRequestSummaryCard: React.FC<OverallRequestSummaryCardProps> = ({ summary }) => {
  const processingTime = summary.total_processing_time_seconds?.toFixed(2) || 'N/A';
  const isSuccessful = Object.values(summary.chain_data_gathering_summary || {}).every((chain: any) => chain?.status?.startsWith('success'));

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
        <SummaryItem label="Chains Requested" value={getChainNames(summary.requested_chain_ids || [], summary.chain_data_gathering_summary || {})} />
        <SummaryItem label="Timeframe" value={summary.timeframe || 'N/A'} />
        {'mvo_objective' in summary && summary.mvo_objective && <SummaryItem label="MVO Objective" value={summary.mvo_objective.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())} />}
        {'risk_free_rate' in summary && summary.risk_free_rate && <SummaryItem label="Risk-Free Rate" value={`${(summary.risk_free_rate * 100).toFixed(2)}%`} valueClassName="text-teal-400 font-semibold" />}
        
        {'max_tokens_per_chain_screening' in summary && summary.max_tokens_per_chain_screening && <SummaryItem label="Max Tokens Screened" value={summary.max_tokens_per_chain_screening} />}
        {'total_unique_assets_after_screening' in summary && summary.total_unique_assets_after_screening && <SummaryItem label="Total Unique Assets" value={summary.total_unique_assets_after_screening} />}
        {'assets_considered_for_global_mvo' in summary && summary.assets_considered_for_global_mvo && <SummaryItem label="Assets in MVO" value={summary.assets_considered_for_global_mvo} />}
        {'assets_in_final_portfolio' in summary && summary.assets_in_final_portfolio && <SummaryItem label="Assets in Final Portfolio" value={summary.assets_in_final_portfolio} />}
        
        <SummaryItem label="Processing Time" value={`${processingTime}s`} valueClassName="text-teal-400 font-semibold" />
        {Object.entries(summary.chain_data_gathering_summary || {}).map(([chainId, chainData]: [string, any]) => (
             <SummaryItem 
                key={chainId} 
                label={`${chainData?.chain_name || `Chain ${chainId}`} Assets Found`} 
                value={chainData?.assets_found || 0} 
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