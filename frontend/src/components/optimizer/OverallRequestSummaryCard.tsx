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

  // Filter out summary items that might not be present or are zero/empty to avoid clutter
  const summaryItems = [
    { label: "Chains Requested", value: getChainNames(summary.requested_chain_ids || [], summary.chain_data_gathering_summary || {}), emoji: "🔗" },
    { label: "Timeframe", value: summary.timeframe || 'N/A', emoji: "⏱️" },
    ...('mvo_objective' in summary && summary.mvo_objective ? [{ label: "MVO Objective", value: summary.mvo_objective.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()), emoji: "🎯" }] : []),
    ...('risk_free_rate' in summary && typeof summary.risk_free_rate === 'number' ? [{ label: "Risk-Free Rate", value: `${(summary.risk_free_rate * 100).toFixed(2)}%`, valueClassName: "text-teal-300 font-semibold", emoji: "💰" }] : []),
    ...('max_tokens_per_chain_screening' in summary && summary.max_tokens_per_chain_screening ? [{ label: "Max Tokens Screened/Chain", value: summary.max_tokens_per_chain_screening, emoji: "🔍" }] : []),
    ...('total_unique_assets_after_screening' in summary && summary.total_unique_assets_after_screening ? [{ label: "Total Unique Assets (Post-Screening)", value: summary.total_unique_assets_after_screening, emoji: "✨" }] : []),
    ...('assets_considered_for_global_mvo' in summary && summary.assets_considered_for_global_mvo ? [{ label: "Assets in MVO Calculation", value: summary.assets_considered_for_global_mvo, emoji: "🧮" }] : []),
    ...('assets_in_final_portfolio' in summary && summary.assets_in_final_portfolio ? [{ label: "Assets in Final Portfolio", value: summary.assets_in_final_portfolio, emoji: "✅" }] : []),
    { label: "Total Processing Time", value: `${processingTime}s`, valueClassName: "text-teal-300 font-semibold", emoji: "⏳" },
  ];

  const chainSpecificAssetCounts = Object.entries(summary.chain_data_gathering_summary || {})
    .map(([chainId, chainData]: [string, any]) => ({
      label: `${chainData?.chain_name || `Chain ${chainId}`} Assets Found`, 
      value: chainData?.assets_found || 0,
      emoji: "📦"
    }))
    .filter(item => item.value > 0); // Only show if assets were found

  return (
    <Card className="shadow-2xl transition-all duration-500 ease-out hover:shadow-3xl opacity-0 animate-fadeIn bg-gradient-to-br from-slate-800/95 via-slate-850/95 to-slate-900/95 border border-slate-700/80 text-gray-300 rounded-xl overflow-hidden backdrop-blur-md">
      <CardHeader className="px-7 py-6 border-b border-slate-700/70">
        <CardTitle className="flex items-center gap-3.5 text-xl font-bold text-white tracking-tight">
           <div className={`p-2.5 rounded-lg bg-gradient-to-br ${isSuccessful ? 'from-green-500/20 to-teal-500/20' : 'from-amber-500/20 to-orange-500/20'} backdrop-blur-sm shadow-md`}>
            {isSuccessful ? <CheckCircle className="h-6 w-6 text-green-300" /> : <AlertCircle className="h-6 w-6 text-amber-300" />}
          </div>
          <span>Optimization Request Summary</span>
        </CardTitle>
        <CardDescription className="text-slate-400 text-sm mt-1 ml-[50px]">
          Overview of the parameters and outcome of your portfolio optimization.
        </CardDescription>
      </CardHeader>
      <CardContent className="p-7 space-y-5">
        <div className="grid md:grid-cols-2 gap-x-8 gap-y-3 text-sm">
          {summaryItems.map((item, index) => (
            (item.value !== 'N/A' && item.value !== 0 && item.value !== '' && item.value !== undefined) ? (
              <SummaryItem key={index} label={item.label} value={item.value} valueClassName={item.valueClassName} emoji={item.emoji} />
            ) : null
          ))}
        </div>
        {chainSpecificAssetCounts.length > 0 && (
          <div className="pt-4 border-t border-slate-700/60">
            <h5 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
              <Layers className="h-4 w-4 text-sky-400" />
              Asset Counts by Chain:
            </h5>
            <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-x-8 gap-y-3 text-sm">
              {chainSpecificAssetCounts.map((item, index) => (
                  <SummaryItem key={`chain-${index}`} label={item.label} value={item.value} emoji={item.emoji} />
              ))}
            </div>
          </div>
        )}
         {Object.values(summary.chain_data_gathering_summary || {}).some((chain: any) => chain?.status && !chain?.status.startsWith('success')) && (
          <div className="pt-4 border-t border-slate-700/60">
            <h5 className="text-sm font-semibold text-red-400 mb-2 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              Chain Processing Issues:
            </h5>
            <ul className="list-disc list-inside space-y-1.5 text-xs pl-2">
              {Object.entries(summary.chain_data_gathering_summary || {}).map(([chainId, chainData]: [string, any]) => {
                if (chainData?.status && !chainData.status.startsWith('success')) {
                  return (
                    <li key={`error-${chainId}`} className="text-red-400/90">
                      <span className="font-medium text-slate-300">{chainData.chain_name || `Chain ${chainId}`}:</span> <span className="italic">{chainData.status}</span>
                    </li>
                  );
                }
                return null;
              })}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

interface SummaryItemProps {
  label: string;
  value: string | number;
  valueClassName?: string;
  emoji?: string;
}

const SummaryItem: React.FC<SummaryItemProps> = ({ label, value, valueClassName, emoji }) => (
  <div className="flex justify-between items-center border-b border-slate-700/50 py-3 last:border-b-0 hover:bg-slate-800/30 px-2 -mx-2 rounded-md transition-colors duration-150">
    <span className="flex items-center gap-2 font-medium text-slate-400 text-xs uppercase tracking-wider whitespace-nowrap overflow-hidden text-ellipsis pr-2" title={label}>
      {emoji && <span className="text-base">{emoji}</span>}
      {label}:
    </span>
    <span className={`font-semibold text-sm ${valueClassName || "text-slate-100"}`}>{String(value)}</span>
  </div>
); 