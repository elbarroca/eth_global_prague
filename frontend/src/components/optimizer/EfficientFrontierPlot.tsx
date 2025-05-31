"use client";

import React from 'react';
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Label,
  Cell
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { OptimizedPortfolioDetails } from '@/types/portfolio-api';
import { TrendingUp, Target } from 'lucide-react';

interface EfficientFrontierPlotProps {
  primaryPortfolio?: OptimizedPortfolioDetails;
  alternativePortfolios?: { [key: string]: OptimizedPortfolioDetails | { error: string } };
  primaryPortfolioName?: string;
  title?: string;
}

interface PlotPoint {
  name: string;
  volatility: number;
  return: number;
  sharpe: number;
  isPrimary: boolean;
  displayName: string;
}

const EfficientFrontierPlot: React.FC<EfficientFrontierPlotProps> = ({ 
  primaryPortfolio, 
  alternativePortfolios, 
  primaryPortfolioName = "Primary Portfolio",
  title = "Efficient Frontier"
}) => {
  const points: PlotPoint[] = [];

  if (primaryPortfolio && typeof primaryPortfolio.annual_volatility === 'number' && typeof primaryPortfolio.expected_annual_return === 'number') {
    points.push({
      name: primaryPortfolioName,
      displayName: "Primary Strategy",
      volatility: primaryPortfolio.annual_volatility * 100,
      return: primaryPortfolio.expected_annual_return,
      sharpe: primaryPortfolio.sharpe_ratio || 0,
      isPrimary: true,
    });
  }

  if (alternativePortfolios) {
    Object.entries(alternativePortfolios).forEach(([key, portfolio]) => {
      if (portfolio && 'annual_volatility' in portfolio && typeof portfolio.annual_volatility === 'number' && typeof portfolio.expected_annual_return === 'number') {
        const displayName = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        if (displayName.toLowerCase() !== primaryPortfolioName.toLowerCase()) {
          points.push({
            name: key,
            displayName: displayName,
            volatility: portfolio.annual_volatility * 100,
            return: portfolio.expected_annual_return,
            sharpe: portfolio.sharpe_ratio || 0,
            isPrimary: false,
          });
        }
      }
    });
  }

  if (points.length === 0) {
    return (
      <div className="bg-slate-800/40 rounded-lg border border-slate-700/60 p-8 shadow-inner">
        <div className="flex flex-col items-center justify-center h-40 space-y-3">
          <TrendingUp className="h-8 w-8 text-slate-600" />
          <p className="text-slate-500 italic text-center">
            Insufficient data points to generate Efficient Frontier visualization.
          </p>
        </div>
      </div>
    );
  }

  const volatilities = points.map(p => p.volatility);
  const returns = points.map(p => p.return);
  const sharpes = points.map(p => p.sharpe);

  const minVol = Math.min(...volatilities);
  const maxVol = Math.max(...volatilities);
  const minRet = Math.min(...returns);
  const maxRet = Math.max(...returns);
  const minSharpe = Math.min(...sharpes);
  const maxSharpe = Math.max(...sharpes);

  const xDomain: [number, number] = [Math.max(0, minVol - (maxVol - minVol) * 0.1), maxVol + (maxVol - minVol) * 0.1];
  const yDomain: [number, number] = [minRet - Math.abs(maxRet - minRet) * 0.1, maxRet + Math.abs(maxRet - minRet) * 0.1];
  
  if (points.length === 1) {
    xDomain[0] = Math.max(0, points[0].volatility * 0.8);
    xDomain[1] = points[0].volatility * 1.2;
    yDomain[0] = points[0].return * (points[0].return >= 0 ? 0.8 : 1.2);
    yDomain[1] = points[0].return * (points[0].return >= 0 ? 1.2 : 0.8);
  }
  if (xDomain[0] === xDomain[1]) xDomain[1] += 1;
  if (yDomain[0] === yDomain[1]) yDomain[1] += 1;

  const zRange = minSharpe === maxSharpe ? [300, 300] : [200, 600];

  const primaryColor = "#10B981"; // Emerald
  const alternativeColor = "#3B82F6"; // Blue

  return (
    <div className="bg-slate-800/40 rounded-lg border border-slate-700/60 shadow-inner">
      <div className="p-4 border-b border-slate-700/50">
        <div className="flex items-center gap-3 mb-2">
          <Target className="h-5 w-5 text-purple-400" />
          <h5 className="font-semibold text-slate-100 text-base">{title}</h5>
        </div>
        <p className="text-slate-400 text-sm">
          Risk vs. Return analysis across portfolio strategies. Bubble size represents Sharpe Ratio performance.
        </p>
        
        {/* Portfolio Legend */}
        <div className="flex flex-wrap gap-4 mt-3 pt-3 border-t border-slate-700/50">
          {points.map((point, index) => (
            <div key={index} className="flex items-center gap-2">
              <div 
                className="w-3 h-3 rounded-full border border-slate-600"
                style={{ backgroundColor: point.isPrimary ? primaryColor : alternativeColor }}
              />
              <span className="text-xs text-slate-300 font-medium">
                {point.displayName}
              </span>
              <span className="text-xs text-slate-500">
                (Sharpe: {point.sharpe.toFixed(2)})
              </span>
            </div>
          ))}
        </div>
      </div>
      
      <div className="p-4" style={{ height: 450 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 20, right: 40, bottom: 60, left: 60 }}>
            <CartesianGrid strokeDasharray="2 2" stroke="#475569" strokeOpacity={0.3} />
            <XAxis 
              type="number" 
              dataKey="volatility" 
              name="Volatility"
              unit="%"
              domain={xDomain}
              tickFormatter={(tick) => `${tick.toFixed(1)}%`}
              tick={{ fill: '#94A3B8', fontSize: 11 }}
              axisLine={{ stroke: '#64748B' }}
              tickLine={{ stroke: '#64748B' }}
            >
              <Label 
                value="Portfolio Volatility (%)" 
                offset={-40} 
                position="insideBottom" 
                fill="#94A3B8" 
                fontSize={12}
                fontWeight="500"
              />
            </XAxis>
            <YAxis 
              type="number" 
              dataKey="return" 
              name="Return" 
              unit="%"
              domain={yDomain}
              tickFormatter={(tick) => `${(tick * 100).toFixed(1)}%`}
              tick={{ fill: '#94A3B8', fontSize: 11 }}
              axisLine={{ stroke: '#64748B' }}
              tickLine={{ stroke: '#64748B' }}
            >
              <Label 
                value="Expected Annual Return (%)" 
                angle={-90} 
                position="insideLeft" 
                style={{ textAnchor: 'middle' }} 
                fill="#94A3B8" 
                fontSize={12} 
                fontWeight="500"
                offset={-40}
              />
            </YAxis>
            <ZAxis type="number" dataKey="sharpe" range={zRange} name="Sharpe Ratio" />
            <Tooltip 
              cursor={{ strokeDasharray: '2 2', fill: 'rgba(59, 130, 246, 0.1)', stroke: '#3B82F6' }} 
              wrapperStyle={{ zIndex: 1000 }}
              contentStyle={{ 
                backgroundColor: 'rgba(15, 23, 42, 0.95)', 
                border: '1px solid #475569', 
                borderRadius: '8px', 
                color: '#E2E8F0',
                boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
                backdropFilter: 'blur(8px)'
              }}
              itemStyle={{ color: '#F1F5F9', fontSize: '12px' }}
              labelStyle={{ color: '#CBD5E1', fontWeight: 'bold', marginBottom: '4px' }}
              formatter={(value: any, name: string, entry: any) => {
                const payload = entry.payload as PlotPoint;
                if (name === "Volatility") {
                  return [`${Number(value).toFixed(2)}%`, "Volatility"];
                }
                if (name === "Return") {
                  return [`${(Number(value) * 100).toFixed(2)}%`, "Expected Return"];
                }
                if (name === "Sharpe Ratio") {
                  return [Number(value).toFixed(3), "Sharpe Ratio"];
                }
                return [value, name];
              }}
              labelFormatter={(label, payload) => {
                if (payload && payload.length > 0) {
                  const point = payload[0].payload as PlotPoint;
                  return `${point.displayName}`;
                }
                return '';
              }}
            />
            <Scatter name="Portfolio Strategies" data={points}>
              {points.map((point, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={point.isPrimary ? primaryColor : alternativeColor}
                  stroke={point.isPrimary ? "#059669" : "#2563EB"}
                  strokeWidth={2}
                  fillOpacity={0.8}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default EfficientFrontierPlot; 