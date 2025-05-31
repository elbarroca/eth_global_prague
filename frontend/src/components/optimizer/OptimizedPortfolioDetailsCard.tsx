"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from "@/components/ui/progress";
import { TrendingUp, PieChart } from 'lucide-react';
import { OptimizedPortfolioDetails } from '@/types/portfolio-api';

interface OptimizedPortfolioDetailsCardProps {
  details: OptimizedPortfolioDetails;
  chainName: string;
}

export const OptimizedPortfolioDetailsCard: React.FC<OptimizedPortfolioDetailsCardProps> = ({ details, chainName }) => {
  const sortedWeights = Object.entries(details.weights)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 15); // Display top 15 or fewer asset weights

  return (
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn animation-delay-400">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl font-semibold">
          <PieChart className="h-6 w-6 text-purple-500" />
          Optimized Portfolio <span className="text-base font-normal text-gray-500">({chainName})</span>
        </CardTitle>
        <CardDescription>Key metrics and asset allocation of the optimized portfolio.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 pt-2">
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-3 text-sm">
          <MetricItem label="Expected Annual Return" value={`${(details.expected_annual_return).toFixed(2)}%`} icon={<TrendingUp className="text-green-500" />} />
          <MetricItem label="Annual Volatility" value={`${(details.annual_volatility * 100).toFixed(2)}%`} />
          <MetricItem label="Sharpe Ratio" value={`${details.sharpe_ratio.toFixed(2)}`} />
          <MetricItem label="Total Assets Considered" value={`${details.total_assets_considered}`} />
          <MetricItem label="Assets with Allocation" value={`${details.assets_with_allocation}`} />
        </div>
        
        <div>
          <h4 className="font-semibold text-md mb-2 text-gray-700">Top Asset Weights:</h4>
          {sortedWeights.length === 0 ? (
            <p className="text-muted-foreground">No asset weights to display.</p>
          ) : (
            <div className="space-y-2.5 max-h-72 overflow-y-auto pr-2">
              {sortedWeights.map(([asset, weight]) => (
                <div key={asset} className="text-sm">
                  <div className="flex justify-between mb-0.5">
                    <span className="font-medium text-gray-700 truncate max-w-[70%]">{asset}</span>
                    <span className="text-gray-600">{(weight * 100).toFixed(2)}%</span>
                  </div>
                  <Progress value={weight * 100} className="h-1.5 bg-purple-100 [&>div]:bg-purple-500" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Placeholder for Charts */}
        <div className="mt-4 pt-4 border-t">
            <h4 className="font-semibold text-md mb-2 text-gray-700">Portfolio Allocation Chart (Placeholder)</h4>
            <div className="p-4 h-48 flex items-center justify-center bg-gray-50 rounded-md text-muted-foreground">
                Pie chart visualizing asset weights will be here. (e.g., using Recharts)
            </div>
        </div>
      </CardContent>
    </Card>
  );
};

interface MetricItemProps {
    label: string;
    value: string | number;
    icon?: React.ReactNode;
}
const MetricItem: React.FC<MetricItemProps> = ({label, value, icon}) => (
    <div className="p-3 bg-gray-50/80 rounded-md shadow-sm">
        <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">{label}</span>
            {icon && <span className="h-4 w-4">{icon}</span>}
        </div>
        <p className="text-lg font-semibold text-gray-800 mt-0.5">{value}</p>
    </div>
) 