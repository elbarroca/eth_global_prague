"use client";

import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { ListTree, TrendingUp, TrendingDown, Minus, ExternalLink, Filter } from 'lucide-react';
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

type FilterType = 'all' | 'most_bullish' | 'most_bearish';

export const RankedAssetsSummaryCard: React.FC<RankedAssetsSummaryCardProps> = ({ assets, chainName, onAssetSelect }) => {
  const [filter, setFilter] = useState<FilterType>('all');

  const filteredAndSortedAssets = useMemo(() => {
    let filtered = [...assets];
    
    switch (filter) {
      case 'most_bullish':
        // Sort by highest number of bullish signals, then by score
        filtered.sort((a, b) => {
          if (b.num_bullish !== a.num_bullish) {
            return b.num_bullish - a.num_bullish;
          }
          return b.score - a.score;
        });
        break;
      case 'most_bearish':
        // Sort by highest number of bearish signals, then by lowest score
        filtered.sort((a, b) => {
          if (b.num_bearish !== a.num_bearish) {
            return b.num_bearish - a.num_bearish;
          }
          return a.score - b.score;
        });
        break;
      case 'all':
      default:
        // Keep original order (presumably sorted by score already)
        break;
    }
    
    return filtered.slice(0, 10); // Display top 10 or fewer
  }, [assets, filter]);

  return (
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn animation-delay-200 bg-slate-800/70 border-slate-700 text-gray-300 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl font-semibold text-white">
          <ListTree className="h-6 w-6 text-emerald-400" />
          Ranked Assets Summary <span className="text-base font-normal text-slate-400">({chainName})</span>
        </CardTitle>
        <CardDescription className="text-slate-400">
          Top assets based on the scoring model. Scores range from -1 (strong bearish) to +1 (strong bullish).
        </CardDescription>
        
        {/* Filter Buttons */}
        <div className="flex gap-2 mt-4">
          <Button
            variant={filter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('all')}
            className="text-xs"
          >
            <Filter className="h-3 w-3 mr-1" />
            All Assets
          </Button>
          <Button
            variant={filter === 'most_bullish' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('most_bullish')}
            className="text-xs"
          >
            <TrendingUp className="h-3 w-3 mr-1" />
            Most Bullish
          </Button>
          <Button
            variant={filter === 'most_bearish' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('most_bearish')}
            className="text-xs"
          >
            <TrendingDown className="h-3 w-3 mr-1" />
            Most Bearish
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {filteredAndSortedAssets.length === 0 ? (
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
                {filteredAndSortedAssets.map((asset: RankedAssetSummary) => (
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