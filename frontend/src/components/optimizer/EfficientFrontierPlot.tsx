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
      volatility: primaryPortfolio.annual_volatility * 100,
      return: primaryPortfolio.expected_annual_return * 100,
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
            name: displayName,
            volatility: portfolio.annual_volatility * 100,
            return: portfolio.expected_annual_return * 100,
            sharpe: portfolio.sharpe_ratio || 0,
            isPrimary: false,
          });
        }
      }
    });
  }

  if (points.length === 0) {
    return (
      <Card className="bg-slate-800 border-slate-700 text-gray-300">
        <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
        <CardContent><p className="text-slate-500 italic">Not enough data for Efficient Frontier plot.</p></CardContent>
      </Card>
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

  const zRange = minSharpe === maxSharpe ? [200, 200] : [100, 800];

  const primaryColor = "#10B981";
  const alternativeColor = "#3B82F6";

  return (
    <Card className="bg-slate-800 border-slate-700 text-gray-300">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>Portfolio risk (Volatility %) vs. Expected Return (%). Bubble size indicates Sharpe Ratio.</CardDescription>
      </CardHeader>
      <CardContent style={{ width: '100%', height: 450 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 20, right: 40, bottom: 50, left: 30 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              type="number" 
              dataKey="volatility" 
              name="Volatility"
              unit="%"
              domain={xDomain}
              tickFormatter={(tick) => `${tick.toFixed(1)}%`}
              tick={{ fill: '#9CA3AF', fontSize: 11 }}
              axisLine={{ stroke: '#4B5563' }}
              tickLine={{ stroke: '#4B5563' }}
            >
              <Label value="Annualized Volatility (%)" offset={-35} position="insideBottom" fill="#9CA3AF" fontSize={12}/>
            </XAxis>
            <YAxis 
              type="number" 
              dataKey="return" 
              name="Return" 
              unit="%"
              domain={yDomain}
              tickFormatter={(tick) => `${tick.toFixed(1)}%`}
              tick={{ fill: '#9CA3AF', fontSize: 11 }}
              axisLine={{ stroke: '#4B5563' }}
              tickLine={{ stroke: '#4B5563' }}
            >
              <Label value="Expected Annual Return (%)" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} fill="#9CA3AF" fontSize={12} offset={-15}/>
            </YAxis>
            <ZAxis type="number" dataKey="sharpe" range={zRange} name="Sharpe Ratio" />
            <Tooltip 
              cursor={{ strokeDasharray: '3 3', fill: 'rgba(200,200,200,0.05)' }} 
              wrapperStyle={{ zIndex: 1000 }}
              contentStyle={{ backgroundColor: 'rgba(17,24,39,0.9)', border: '1px solid #374151', borderRadius: '0.5rem', color: '#D1D5DB' }}
              itemStyle={{ color: '#E5E7EB' }}
              formatter={(value: any, name: string, entry: any) => {
                const payload = entry.payload as PlotPoint;
                if (name === "Volatility" || name === "Return") {
                  return [`${Number(value).toFixed(2)}%`, payload.name];
                }
                if (name === "Sharpe Ratio") {
                  return [Number(value).toFixed(3), payload.name];
                }
                return [value, payload.name];
              }}
              labelFormatter={(label) => `Portfolio: ${points[label as any]?.name || ''}`}
            />
            <Legend wrapperStyle={{ paddingTop: '20px', color: '#9CA3AF' }} />
            <Scatter name="Portfolios" data={points} >
                {points.map((point, index) => (
                    <Cell key={`cell-${index}`} fill={point.isPrimary ? primaryColor : alternativeColor} />
                ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

export default EfficientFrontierPlot; 