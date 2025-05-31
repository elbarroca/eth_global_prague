"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from "@/components/ui/progress";
import { ListTree, TrendingUp, TrendingDown, Minus, ExternalLink } from 'lucide-react';
import { RankedAssetSummary } from '@/types/portfolio-api';

interface RankedAssetsSummaryCardProps {
  assets: RankedAssetSummary[];
  chainName: string;
  onAssetSelect: (asset: RankedAssetSummary) => void;
}

const getScoreColorClass = (score: number) => {
  if (score > 0.7) return "bg-emerald-500";
  if (score > 0.3) return "bg-green-500";
  if (score > 0) return "bg-lime-500";
  if (score === 0) return "bg-yellow-500";
  if (score < -0.7) return "bg-red-600";
  if (score < -0.3) return "bg-red-500";
  return "bg-orange-500";
};

const getSignalIcon = (score: number) => {
  if (score > 0) return <TrendingUp className="h-5 w-5 text-emerald-400" />;
  if (score < 0) return <TrendingDown className="h-5 w-5 text-red-400" />;
  return <Minus className="h-5 w-5 text-yellow-400" />;
}

export const RankedAssetsSummaryCard: React.FC<RankedAssetsSummaryCardProps> = ({ assets, chainName, onAssetSelect }) => {
  const topAssets = assets.slice(0, 10); // Display top 10 or fewer

  return (
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn animation-delay-200 bg-slate-800/70 border-slate-700 text-gray-300 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl font-semibold text-white">
          <ListTree className="h-6 w-6 text-emerald-400" />
          Ranked Assets Summary <span className="text-base font-normal text-slate-400">({chainName})</span>
        </CardTitle>
        <CardDescription className="text-slate-400">Top assets based on the scoring model. Scores range from -1 (strong bearish) to +1 (strong bullish).</CardDescription>
      </CardHeader>
      <CardContent>
        {topAssets.length === 0 ? (
            <p className="text-slate-500 italic py-4">No ranked assets to display for this selection.</p>
        ) : (
          <div className="overflow-x-auto -mx-2">
            <table className="min-w-full">
              <thead className="bg-slate-700/60">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider rounded-tl-md">Asset</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Score / Signal</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider">Bullish Signals</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider rounded-tr-md">Bearish Signals</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {topAssets.map((asset) => (
                  <tr 
                    key={asset.asset} 
                    className="transition-all duration-150 ease-in-out hover:bg-slate-700/70 cursor-pointer group"
                    onClick={() => onAssetSelect(asset)}
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center">
                        <span className="text-sm font-medium text-teal-400 group-hover:text-teal-300 transition-colors">{asset.asset}</span>
                        <ExternalLink className="ml-1.5 h-3.5 w-3.5 text-slate-500 group-hover:text-teal-400 transition-colors" />
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-300">
                      <div className="flex items-center gap-2">
                        {getSignalIcon(asset.score)}
                        <span className={`font-semibold text-base w-14 text-right ${asset.score > 0 ? 'text-emerald-400' : asset.score < 0 ? 'text-red-400' : 'text-yellow-400'}`}>
                          {asset.score.toFixed(3)}
                        </span>
                        <Progress value={(asset.score + 1) * 50} className={`w-24 h-2 bg-slate-600/70 rounded-full [&>div]:${getScoreColorClass(asset.score)} transition-all`}/>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-emerald-400 text-center font-medium">{asset.num_bullish}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-red-400 text-center font-medium">{asset.num_bearish}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}; 