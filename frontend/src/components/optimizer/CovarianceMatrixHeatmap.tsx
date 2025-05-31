"use client";

import React from 'react';
import { ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

interface CovarianceMatrixHeatmapProps {
  covarianceMatrix?: { [key: string]: { [key: string]: number } };
  title?: string;
}

const CustomHeatmapCell = (props: any) => {
  const { cx, cy, width, height, fill } = props;
  if (width <= 0 || height <= 0) return null;
  
  // Make squares bigger by expanding them
  const cellSize = Math.min(width, height) * 1.2; // 20% bigger
  const x = cx - cellSize / 2;
  const y = cy - cellSize / 2;
  
  // Use a slightly darker version of the fill for the stroke, or a fixed subtle border
  const strokeColor = "rgba(0, 0, 0, 0.3)"; // Slightly more visible border
  return <rect x={x} y={y} width={cellSize} height={cellSize} fill={fill} stroke={strokeColor} strokeWidth={1} />;
};

const CovarianceMatrixHeatmap: React.FC<CovarianceMatrixHeatmapProps> = ({ covarianceMatrix, title = "Covariance Matrix Heatmap" }) => {
  if (!covarianceMatrix || Object.keys(covarianceMatrix).length === 0) {
    return (
      <Card className="bg-slate-800 border-slate-700 text-gray-300">
        <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
        <CardContent><p className="text-slate-500 italic">Covariance data not available.</p></CardContent>
      </Card>
    );
  }

  const assets = Object.keys(covarianceMatrix);
  
  // First pass: collect all values to determine min/max
  const tempData: { x: string, y: string, value: number, xIndex: number, yIndex: number }[] = [];
  assets.forEach((assetX, i) => {
    assets.forEach((assetY, j) => {
      if (covarianceMatrix[assetX] && typeof covarianceMatrix[assetX][assetY] === 'number') {
        tempData.push({ x: assetX, y: assetY, value: covarianceMatrix[assetX][assetY], xIndex: i, yIndex: j });
      }
    });
  });

  const values = tempData.map(d => d.value);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  
  // Normalize values to 0-1 range for better visualization
  const normalizeValue = (value: number, min: number, max: number) => {
    if (min === max) return 0.5; // Mid-point for single value
    return (value - min) / (max - min);
  };

  // Simple and clear color function: light to dark blue gradient
  const getColor = (normalizedValue: number) => {
    // Clamp normalized value between 0 and 1
    const clamped = Math.max(0, Math.min(1, normalizedValue));
    
    // Simple gradient from very light blue to very dark blue
    // Light blue for low values, dark blue for high values
    const lightness = 90 - (clamped * 70); // 90% to 20% lightness
    const saturation = 40 + (clamped * 50); // 40% to 90% saturation
    
    return `hsl(210, ${saturation}%, ${lightness}%)`;
  };

  // Second pass: create data with normalized values and colors
  const data = tempData.map(item => {
    const normalizedValue = normalizeValue(item.value, minValue, maxValue);
    return {
      ...item,
      normalizedValue,
      displayValue: normalizedValue, // Use normalized value for display
      originalValue: item.value, // Keep original for tooltip
      fill: getColor(normalizedValue)
    };
  });

  const tickFontSize = Math.max(10, Math.min(14, 120 / assets.length));
  const labelHeight = Math.max(80, Math.min(150, tickFontSize * 7));
  const labelWidth = Math.max(80, Math.min(200, tickFontSize * 10));
  const chartHeight = Math.max(500, Math.min(900, assets.length * (tickFontSize + 15) + labelHeight + 60));

  return (
    <Card className="bg-slate-800 border-slate-700 text-gray-300 overflow-hidden">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>
           Asset covariance: Light blue (low/negative) to dark blue (high positive).
        </CardDescription>
      </CardHeader>
      <CardContent style={{ width: '100%', height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 20, bottom: labelHeight, left: labelWidth }}>
            <CartesianGrid fill="rgba(0,0,0,0.0)" stroke="rgba(0,0,0,0.0)"/>
            <XAxis 
              dataKey="xIndex"
              type="number" 
              name="Asset"
              domain={[-0.5, assets.length - 0.5]}
              ticks={assets.map((_, index) => index)}
              tickFormatter={(tickValue) => assets[tickValue]}
              angle={-60}
              textAnchor="end" 
              height={labelHeight - 20} 
              tick={{ fill: '#9CA3AF', fontSize: tickFontSize }} 
              axisLine={{ stroke: '#4B5563' }}
              tickLine={{ stroke: '#4B5563' }}
              interval={0}
            />
            <YAxis 
              dataKey="yIndex"
              type="number" 
              name="Asset" 
              domain={[-0.5, assets.length - 0.5]}
              ticks={assets.map((_, index) => index)}
              tickFormatter={(tickValue) => assets[tickValue]}
              reversed 
              width={labelWidth - 20}
              tick={{ fill: '#9CA3AF', fontSize: tickFontSize }} 
              axisLine={{ stroke: '#4B5563' }}
              tickLine={{ stroke: '#4B5563' }}
              interval={0}
            />
            <Tooltip 
              cursor={false}
              wrapperStyle={{ zIndex: 1000 }}
              contentStyle={{ 
                backgroundColor: 'rgba(17,24,39,0.95)', 
                border: '1px solid #374151', 
                borderRadius: '0.5rem', 
                color: '#D1D5DB',
                padding: '8px 12px',
                fontSize: '12px'
              }}
                             content={({ active, payload }) => {
                 if (active && payload && payload.length > 0) {
                   const data = payload[0].payload;
                   return (
                     <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
                       <div className="font-medium text-white mb-1">
                         {data.x} × {data.y}
                       </div>
                       <div className="text-blue-300">
                         Value: {Number(data.normalizedValue).toFixed(3)}
                       </div>
                     </div>
                   );
                 }
                 return null;
               }}
            />
            <Scatter 
                name="Covariance" 
                data={data} 
                shape={<CustomHeatmapCell />} 
                isAnimationActive={false}
                legendType="none"
            />
          </ScatterChart>
        </ResponsiveContainer>
        <div className="flex justify-center items-center space-x-2 mt-3 mb-3 px-2 text-xs text-slate-400">
            <span>0.000</span>
            <div style={{
                width: '120px', 
                height: '12px', 
                borderRadius: '3px',
                background: `linear-gradient(to right, 
                  ${getColor(0)}, 
                  ${getColor(0.25)}, 
                  ${getColor(0.5)}, 
                  ${getColor(0.75)}, 
                  ${getColor(1)}
                )`
            }}></div>
            <span>1.000</span>
        </div>
      </CardContent>
    </Card>
  );
};

export default CovarianceMatrixHeatmap; 