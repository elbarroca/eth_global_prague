"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from "@/components/ui/progress";
import { ListTree, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { RankedAssetSummary } from '@/types/portfolio-api';

interface RankedAssetsSummaryCardProps {
  assets: RankedAssetSummary[];
  chainName: string;
  onAssetSelect: (asset: RankedAssetSummary) => void;
}

const getScoreColor = (score: number) => {
  if (score > 0.5) return "bg-green-500";
  if (score > 0) return "bg-lime-500";
  if (score === 0) return "bg-yellow-500";
  if (score < -0.5) return "bg-red-500";
  return "bg-orange-500";
};

const getSignalIcon = (score: number) => {
  if (score > 0) return <TrendingUp className="h-4 w-4 text-green-500" />;
  if (score < 0) return <TrendingDown className="h-4 w-4 text-red-500" />;
  return <Minus className="h-4 w-4 text-yellow-500" />;
}

export const RankedAssetsSummaryCard: React.FC<RankedAssetsSummaryCardProps> = ({ assets, chainName, onAssetSelect }) => {
  const topAssets = assets.slice(0, 10); // Display top 10 or fewer

  return (
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn animation-delay-200 bg-slate-800 border-slate-700 text-gray-300">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl font-semibold text-emerald-400">
          <ListTree className="h-6 w-6 text-emerald-500" />
          Ranked Assets Summary <span className="text-base font-normal text-slate-500">({chainName})</span>
        </CardTitle>
        <CardDescription className="text-slate-400">Top assets based on the scoring model. Scores range from -1 (strong bearish) to +1 (strong bullish).</CardDescription>
      </CardHeader>
      <CardContent>
        {topAssets.length === 0 ? (
            <p className="text-slate-500 italic">No ranked assets to display for this selection.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-700">
              <thead className="bg-slate-700/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Asset</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Score / Signal</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Bullish</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Bearish</th>
                </tr>
              </thead>
              <tbody className="bg-slate-800 divide-y divide-slate-700">
                {topAssets.map((asset, index) => (
                  <tr 
                    key={asset.asset} 
                    className={`transition-colors hover:bg-slate-700/60 ${index % 2 === 0 ? 'bg-slate-800' : 'bg-slate-800/70'} cursor-pointer`}
                    onClick={() => onAssetSelect(asset)}
                  >
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-teal-300 hover:text-teal-200 underline decoration-dotted underline-offset-2">{asset.asset}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-300">
                      <div className="flex items-center gap-2">
                        {getSignalIcon(asset.score)}
                        <span className={`font-semibold ${asset.score > 0 ? 'text-green-400' : asset.score < 0 ? 'text-red-400' : 'text-yellow-400'}`}>{asset.score.toFixed(3)}</span>
                        <Progress value={(asset.score + 1) * 50} className={`w-20 h-1.5 bg-slate-600 [&>div]:${getScoreColor(asset.score)}`}/>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-green-400">{asset.num_bullish}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-red-400">{asset.num_bearish}</td>
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