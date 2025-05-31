"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from "@/components/ui/progress";
import { TrendingUp, PieChart as PieChartIcon, TrendingDown } from 'lucide-react';
import { OptimizedPortfolioDetails } from '@/types/portfolio-api';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';

interface OptimizedPortfolioDetailsCardProps {
  details: OptimizedPortfolioDetails;
  chainName: string;
}

// Generate contrasting colors for pie chart segments
const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#00C49F', '#FFBB28', '#FF8042', '#0088FE', '#AF19FF'];

export const OptimizedPortfolioDetailsCard: React.FC<OptimizedPortfolioDetailsCardProps> = ({ details, chainName }) => {
  const sortedWeights = Object.entries(details.weights)
    .sort(([, a], [, b]) => b - a);

  // Dynamic "Others" category for Pie Chart
  const pieChartData = [];
  let otherAssetsWeight = 0;
  const maxPieSlices = 10; // Show top N slices + "Others"
  const otherThreshold = 0.01; // Assets below 1% weight go into "Others"

  sortedWeights.forEach(([name, value], index) => {
    if (index < maxPieSlices -1 && value >= otherThreshold) {
      pieChartData.push({ name, value: parseFloat((value * 100).toFixed(2)) });
    } else {
      otherAssetsWeight += value;
    }
  });

  if (otherAssetsWeight > 0.0001) { // Add others if it has any significant weight
    pieChartData.push({ name: 'Other Assets', value: parseFloat((otherAssetsWeight * 100).toFixed(2)) });
  }

  // Ensure pie chart data is sorted by value for consistent color application if COLORS array is used cyclically
  pieChartData.sort((a, b) => b.value - a.value);

  return (
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn animation-delay-400 bg-slate-800 border-slate-700 text-gray-300">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl font-semibold text-white">
          <PieChartIcon className="h-6 w-6 text-white" />
          Optimized Portfolio <span className="text-base font-normal text-slate-400">({chainName})</span>
        </CardTitle>
        <CardDescription className="text-slate-400">Key metrics and asset allocation of the optimized portfolio.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 pt-2">
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-4 text-sm">
          <MetricItem label="Expected Annual Return" value={`${(details.expected_annual_return).toFixed(2)}%`} icon={<TrendingUp className="text-green-400" />} />
          <MetricItem label="Annual Volatility" value={`${(details.annual_volatility * 100).toFixed(2)}%`} icon={<TrendingUp className="text-orange-400" />} />
          <MetricItem label="Sharpe Ratio" value={`${details.sharpe_ratio.toFixed(2)}`} icon={<TrendingUp className="text-teal-400" />} />
          {details.cvar_95_historical_period !== undefined && (
            <MetricItem label="CVaR (95%)" value={`${(details.cvar_95_historical_period * 100).toFixed(2)}%`} icon={<TrendingUp className="text-red-400" />} />
          )}
          {details.max_drawdown !== undefined && (
            <MetricItem label="Max Drawdown" value={`${(details.max_drawdown * 100).toFixed(2)}%`} icon={<TrendingDown className="text-red-400" />} />
          )}
          {details.sortino_ratio !== undefined && (
            <MetricItem label="Sortino Ratio" value={`${details.sortino_ratio.toFixed(2)}`} icon={<TrendingUp className="text-sky-400" />} />
          )}
          {details.calmar_ratio !== undefined && (
            <MetricItem label="Calmar Ratio" value={`${details.calmar_ratio.toFixed(2)}`} icon={<TrendingUp className="text-purple-400" />} />
          )}
          <MetricItem label="Total Assets Considered" value={`${details.total_assets_considered}`} />
          <MetricItem label="Assets with Allocation" value={`${details.assets_with_allocation}`} />
        </div>
        
        <div className="grid md:grid-cols-2 gap-6 items-start">
          <div>
            <h4 className="font-semibold text-md mb-3 text-slate-200">Top Asset Weights:</h4>
            {Object.entries(details.weights).length === 0 ? (
              <p className="text-slate-500 italic">No asset weights to display.</p>
            ) : (
              <div className="space-y-3 max-h-72 overflow-y-auto pr-2 custom-scrollbar">
                {Object.entries(details.weights).sort(([,a],[,b]) => b-a).map(([asset, weight]) => (
                  <div key={asset} className="text-sm">
                    <div className="flex justify-between mb-1">
                      <span className="font-medium text-slate-200 truncate max-w-[70%]">{asset}</span>
                      <span className="text-white font-semibold">{(weight * 100).toFixed(2)}%</span>
                    </div>
                    <Progress value={weight * 100} className="h-2 bg-slate-700 [&>div]:bg-white" />
                  </div>
                ))}
              </div>
            )}
          </div>
          
          <div className="mt-6 md:mt-0">
            <h4 className="font-semibold text-md mb-3 text-slate-200">Portfolio Allocation Chart:</h4>
            {pieChartData.length > 0 ? (
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieChartData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      outerRadius={100}
                      innerRadius={40}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {pieChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number, name: string) => [`${value.toFixed(2)}%`, name]} contentStyle={{ backgroundColor: 'rgba(30, 41, 59, 0.9)', borderColor: '#475569' }} itemStyle={{ color: '#cbd5e1' }}/>
                    <Legend wrapperStyle={{fontSize: '12px', paddingTop: '10px'}}/>
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="p-4 h-48 flex items-center justify-center bg-slate-700/50 rounded-md text-slate-500 italic">
                No allocation data for chart.
              </div>
            )}
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
    <div className="p-4 bg-slate-700/50 rounded-lg shadow-md">
        <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</span>
            {icon && <span className="h-5 w-5">{icon}</span>}
        </div>
        <p className="text-xl font-semibold text-slate-100 mt-0.5 tabular-nums">{value}</p>
    </div>
) 