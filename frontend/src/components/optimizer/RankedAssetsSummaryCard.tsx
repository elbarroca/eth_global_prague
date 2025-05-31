"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from "@/components/ui/progress";
import { ListTree, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { RankedAssetSummary } from '@/types/portfolio-api';

interface RankedAssetsSummaryCardProps {
  assets: RankedAssetSummary[];
  chainName: string;
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

export const RankedAssetsSummaryCard: React.FC<RankedAssetsSummaryCardProps> = ({ assets, chainName }) => {
  const topAssets = assets.slice(0, 10); // Display top 10 or fewer

  return (
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn animation-delay-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl font-semibold">
          <ListTree className="h-6 w-6 text-green-500" />
          Ranked Assets Summary <span className="text-base font-normal text-gray-500">({chainName})</span>
        </CardTitle>
        <CardDescription>Top assets based on the scoring model. Scores range from -1 (strong bearish) to +1 (strong bullish).</CardDescription>
      </CardHeader>
      <CardContent>
        {topAssets.length === 0 ? (
            <p className="text-muted-foreground">No ranked assets to display for this selection.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Asset</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score / Signal</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Bullish</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Bearish</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {topAssets.map((asset, index) => (
                  <tr key={asset.asset} className={`transition-colors hover:bg-gray-50 ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}`}>
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-800">{asset.asset}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      <div className="flex items-center gap-2">
                        {getSignalIcon(asset.score)}
                        <span className={`font-semibold ${asset.score > 0 ? 'text-green-600' : asset.score < 0 ? 'text-red-600' : 'text-yellow-600'}`}>{asset.score.toFixed(3)}</span>
                        <Progress value={(asset.score + 1) * 50} className={`w-20 h-1.5 ${getScoreColor(asset.score)}`}/>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-green-600">{asset.num_bullish}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-red-600">{asset.num_bearish}</td>
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