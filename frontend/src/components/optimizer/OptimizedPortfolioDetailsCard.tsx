"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from "@/components/ui/progress";
import { 
  TrendingUp, 
  PieChart as PieChartIcon, 
  TrendingDown, 
  Layers, 
  Target,
  Shield,
  BarChart3,
  Zap,
  Award,
  Activity
} from 'lucide-react';
import { OptimizedPortfolioDetails, RankedAssetSummary } from '@/types/portfolio-api';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';
import { LiquidatePortfolioButton } from './LiquidatePorfolioButton';

interface OptimizedPortfolioDetailsCardProps {
  details: OptimizedPortfolioDetails & { asset_details_map?: { [asset_ticker: string]: RankedAssetSummary } }; // Use RankedAssetSummary
  chainName: string;
  onAssetSelect?: (asset: RankedAssetSummary) => void; // Make optional with default handler
  // Props for LiquidatePortfolioButton
  selectedBridgeChains?: string[]; // Array of chain IDs to bridge to
  portfolioTotalValueUSD?: number;  // Total USD value of the portfolio being displayed
}

// Generate contrasting colors for pie chart segments
const COLORS = ['#10B981', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#F97316', '#84CC16', '#D946EF', '#22D3EE'];

export const OptimizedPortfolioDetailsCard: React.FC<OptimizedPortfolioDetailsCardProps> = ({ 
  details, 
  chainName, 
  onAssetSelect,
  selectedBridgeChains,
  portfolioTotalValueUSD 
}) => {
  const sortedWeights = Object.entries(details.weights)
    .sort(([, a], [, b]) => b - a);

  // Dynamic "Others" category for Pie Chart
  const pieChartData = [];
  let otherAssetsWeight = 0;
  const maxPieSlices = 7; // Show top N-1 slices + "Others"
  const otherThreshold = 0.015; // Assets below 1.5% weight go into "Others"

  sortedWeights.forEach(([name, value], index) => {
    if (pieChartData.length < maxPieSlices && value >= otherThreshold) {
      pieChartData.push({ name, value: parseFloat((value * 100).toFixed(2)) });
    } else {
      otherAssetsWeight += value;
    }
  });

  if (otherAssetsWeight > 0.0001 && pieChartData.length <= maxPieSlices) {
    pieChartData.push({ name: 'Others', value: parseFloat((otherAssetsWeight * 100).toFixed(2)) });
  }

  pieChartData.sort((a, b) => b.value - a.value);

  const totalAssetsInvolved = sortedWeights.length;

  return (
    <Card className="shadow-2xl transition-all duration-500 ease-out hover:shadow-3xl opacity-0 animate-fadeIn animation-delay-400 bg-gradient-to-br from-slate-800/95 via-slate-850/95 to-slate-900/95 border border-slate-700/80 text-gray-300 rounded-xl overflow-hidden backdrop-blur-md">
      <CardHeader className="px-7 py-6 border-b border-slate-700/70">
        <CardTitle className="flex items-center gap-3.5 text-xl font-bold text-white tracking-tight">
          <div className="p-2.5 rounded-lg bg-gradient-to-br from-emerald-500/20 to-green-500/20 backdrop-blur-sm shadow-md">
            <Target className="h-6 w-6 text-emerald-300" />
          </div>
          <span>Optimized Portfolio Insights</span> 
          <span className="text-base font-normal text-slate-400 ml-1">({chainName})</span>
        </CardTitle>
        <CardDescription className="text-slate-400 text-sm mt-1 ml-[50px]">Key performance metrics and asset allocation for your strategy.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-8 p-7">
        {/* Key Performance Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
          <MetricCard 
            label="Expected Annual Return" 
            value={`${details.expected_annual_return.toFixed(2)}%`} 
            icon={<TrendingUp className="h-5 w-5" />} // Color set in MetricCard
            positive={details.expected_annual_return > 0}
            dataCy="annual-return"
          />
          <MetricCard 
            label="Annual Volatility" 
            value={`${(details.annual_volatility * 100).toFixed(2)}%`} 
            icon={<Activity className="h-5 w-5" />}
            dataCy="annual-volatility"
          />
          <MetricCard 
            label="Sharpe Ratio" 
            value={details.sharpe_ratio.toFixed(3)} 
            icon={<Award className="h-5 w-5" />}
            positive={details.sharpe_ratio > 1} // Example: Sharpe > 1 is good
            dataCy="sharpe-ratio"
          />
          <MetricCard 
            label="Portfolio Assets" 
            value={`${details.assets_with_allocation} / ${totalAssetsInvolved}`} 
            icon={<Layers className="h-5 w-5" />}
            dataCy="portfolio-assets"
          />
        </div>

        {/* Additional Metrics (if available) */}
        {(details.max_drawdown !== undefined || details.sortino_ratio !== undefined || details.calmar_ratio !== undefined || details.cvar_95_historical_period !== undefined) && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-5 pt-5 border-t border-slate-700/60">
            {details.max_drawdown !== undefined && (
              <MetricCard 
                label="Max Drawdown" 
                value={`${(details.max_drawdown * 100).toFixed(2)}%`} 
                icon={<TrendingDown className="h-5 w-5" />}
                negative // Max drawdown is inherently negative/loss
                dataCy="max-drawdown"
              />
            )}
            {details.sortino_ratio !== undefined && (
              <MetricCard 
                label="Sortino Ratio" 
                value={details.sortino_ratio.toFixed(3)} 
                icon={<Shield className="h-5 w-5" />}
                positive={details.sortino_ratio > 1} // Example: Sortino > 1 is good
                dataCy="sortino-ratio"
              />
            )}
            {details.calmar_ratio !== undefined && (
              <MetricCard 
                label="Calmar Ratio" 
                value={details.calmar_ratio.toFixed(3)} 
                icon={<Zap className="h-5 w-5" />}
                positive={details.calmar_ratio > 0.5} // Example: Calmar > 0.5 is good
                dataCy="calmar-ratio"
              />
            )}
            {details.cvar_95_historical_period !== undefined && (
              <MetricCard 
                label="CVaR (95%)" 
                value={`${(details.cvar_95_historical_period * 100).toFixed(2)}%`} 
                icon={<BarChart3 className="h-5 w-5" />}
                negative // CVaR is a risk measure, lower is better
                dataCy="cvar"
              />
            )}
          </div>
        )}
        
        <div className="grid lg:grid-cols-5 gap-x-8 gap-y-10 pt-6 border-t border-slate-700/60">
          {/* Asset Weights - taking more width */}
          <div className="lg:col-span-3">
            <h4 className="font-semibold text-lg mb-5 text-slate-100 flex items-center gap-2.5">
              <span className="w-2 h-4 bg-emerald-400 rounded-sm block"></span>
              Asset Allocation Breakdown
            </h4>
            {Object.entries(details.weights).length === 0 ? (
              <div className="p-6 h-48 flex items-center justify-center bg-slate-800/40 rounded-lg text-slate-500 italic border border-slate-700">
                No asset weights to display for this portfolio.
              </div>
            ) : (
              <div className="space-y-3.5 max-h-[360px] overflow-y-auto pr-3 custom-scrollbar">
                {sortedWeights.map(([assetTicker, weight]) => {
                  const assetDetail = details.asset_details_map?.[assetTicker];
                  const canBeClicked = !!assetDetail && !!onAssetSelect;

                  return (
                    <div 
                      key={assetTicker} 
                      className={`bg-slate-700/40 rounded-lg p-3.5 transition-all duration-200 border border-slate-700/60 shadow-sm ${
                        canBeClicked 
                          ? 'hover:bg-slate-700/70 hover:shadow-md cursor-pointer hover:border-teal-500/50 hover:scale-[1.02] group' 
                          : 'hover:bg-slate-700/60'
                      }`}
                      onClick={() => {
                        if (canBeClicked && assetDetail && onAssetSelect) {
                          console.log('Asset clicked:', assetTicker, assetDetail);
                          onAssetSelect(assetDetail);
                        }
                      }}
                      title={canBeClicked ? `Click to deep dive into ${assetTicker}` : assetTicker}
                    >
                      <div className="flex justify-between items-center mb-1.5">
                        <span className={`font-medium text-sm truncate max-w-[70%] transition-colors duration-200 ${
                          canBeClicked ? 'text-teal-300 group-hover:text-teal-200' : 'text-slate-200'
                        }`}>
                          {assetTicker}
                          {canBeClicked && (
                            <span className="ml-2 text-xs opacity-60 group-hover:opacity-100 transition-opacity">
                              📊 Click to analyze
                            </span>
                          )}
                        </span>
                        <span className="text-emerald-300 font-semibold text-sm tabular-nums">{(weight * 100).toFixed(2)}%</span>
                      </div>
                      <Progress value={weight * 100} className="h-2.5 bg-slate-600/70 rounded [&>div]:bg-gradient-to-r [&>div]:from-emerald-500 [&>div]:to-teal-400 shadow-inner" />
                    </div>
                  );
                })}
                 {sortedWeights.length === 0 && (
                  <p className="text-slate-500 italic text-center py-4">No assets have allocations.</p>
                )}
              </div>
            )}
          </div>
          
          {/* Pie Chart - taking less width */}
          <div className="lg:col-span-2">
            <h4 className="font-semibold text-lg mb-5 text-slate-100 flex items-center gap-2.5">
              <span className="w-2 h-4 bg-blue-400 rounded-sm block"></span>
              Visual Distribution
            </h4>
            {pieChartData.length > 0 ? (
              <div className="h-[320px] w-full bg-slate-800/40 p-4 rounded-lg border border-slate-700/60 shadow-inner">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                    <Pie
                      data={pieChartData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent, value }) => percent > 0.03 ? `${name} ${value.toFixed(0)}%` : ''} // Show label if > 3%
                      outerRadius={100} // Slightly smaller for better fit with legend
                      innerRadius={45} // Donut hole
                      fill="#8884d8"
                      dataKey="value"
                      stroke="#1e293b" // Background color for separation
                      strokeWidth={2}
                      paddingAngle={1}
                    >
                      {pieChartData.map((entry, index) => {
                        const assetDetail = details.asset_details_map?.[entry.name];
                        const canBeClicked = !!assetDetail && entry.name !== 'Others' && !!onAssetSelect;
                        
                        return (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={COLORS[index % COLORS.length]} 
                            className={`focus:outline-none transition-opacity ${
                              canBeClicked ? 'hover:opacity-80 cursor-pointer' : 'hover:opacity-90'
                            }`}
                            onClick={() => {
                              if (canBeClicked && assetDetail && onAssetSelect) {
                                console.log('Pie chart segment clicked:', entry.name, assetDetail);
                                onAssetSelect(assetDetail);
                              }
                            }}
                          />
                        );
                      })}
                    </Pie>
                    <Tooltip 
                      formatter={(value: number, name: string) => {
                        const assetDetail = details.asset_details_map?.[name];
                        const canBeClicked = !!assetDetail && name !== 'Others' && !!onAssetSelect;
                        return [
                          `${value.toFixed(2)}%${canBeClicked ? ' (Click to analyze)' : ''}`, 
                          name
                        ];
                      }} 
                      contentStyle={{ 
                        backgroundColor: 'rgba(26, 32, 44, 0.95)', // Darker, more opaque
                        borderColor: '#4A5568', // Tailwind slate-600
                        borderRadius: '10px',
                        borderWidth: '1.5px',
                        boxShadow: '0 8px 20px rgba(0,0,0,0.4)',
                        padding: '10px 14px'
                      }} 
                      itemStyle={{ color: '#e2e8f0' }} // Tailwind slate-200
                      labelStyle={{ color: '#cbd5e1', fontWeight: 'bold', marginBottom: '6px' }} // Tailwind slate-300
                    />
                    <Legend 
                      layout="horizontal" 
                      verticalAlign="bottom" 
                      align="center"
                      wrapperStyle={{fontSize: '11px', paddingTop: '20px', lineHeight: '1.5'}}
                      iconType="circle"
                      iconSize={8}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="p-6 h-[320px] flex items-center justify-center bg-slate-800/40 rounded-lg text-slate-500 italic border border-slate-700">
                No allocation data large enough for chart.
              </div>
            )}
          </div>
        </div>

        {/* Liquidation Button Section */}
        <div className="mt-8 pt-6 border-t border-slate-700/70">
          <div className="mb-4">
            <h4 className="font-semibold text-lg mb-2 text-slate-100 flex items-center gap-2.5">
              <span className="w-2 h-4 bg-red-400 rounded-sm block"></span>
              Portfolio Management
            </h4>
            <p className="text-slate-400 text-sm">
              Liquidate your current portfolio and bridge assets across multiple chains for optimal distribution.
            </p>
          </div>
          <LiquidatePortfolioButton
            portfolioWeights={details.weights}
            selectedChains={selectedBridgeChains || ['1', '137']} // Default to Ethereum and Polygon for testing
            portfolioTotalValueUSD={portfolioTotalValueUSD || 10000} // Default value for testing
          />
        </div>
      </CardContent>
    </Card>
  );
};

interface MetricCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  positive?: boolean;
  negative?: boolean;
  dataCy?: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, icon, positive, negative, dataCy }) => {
  const getColors = () => {
    if (positive) return { bg: "bg-emerald-700/20", text: "text-emerald-300", border: "border-emerald-600/50", iconText: "text-emerald-400" };
    if (negative) return { bg: "bg-red-700/20", text: "text-red-300", border: "border-red-600/50", iconText: "text-red-400" };
    return { bg: "bg-sky-700/20", text: "text-sky-300", border: "border-sky-600/50", iconText: "text-sky-400" }; // Default to a neutral blueish color
  };

  const colors = getColors();

  return (
    <div 
      className={`rounded-lg p-4 transition-all duration-200 border shadow-sm hover:shadow-lg ${colors.bg} ${colors.border} hover:border-opacity-80`}
      data-cy={dataCy}
    >
      <div className={`flex items-center justify-between mb-1.5 ${colors.iconText}`}>
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider whitespace-nowrap overflow-hidden text-ellipsis" title={label}>{label}</span>
        {icon}
      </div>
      <p className={`text-xl font-bold ${colors.text} tabular-nums`}>{value}</p>
    </div>
  );
}; 