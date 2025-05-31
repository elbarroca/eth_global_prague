"use client";

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, ComposedChart } from 'recharts';
import { TrendingUp, Activity, HelpCircle, Eye } from 'lucide-react';
import { OverallRequestSummary, RankedAssetSummary } from '@/types/portfolio-api'; // Assuming types might be useful
import { Button } from '../ui/button';

interface OHLCVDataPoint {
  time: number; // timestamp
  open: number;
  high: number;
  low: number;
  close: number;
}

interface ForecastSignal {
  signal_type: string;
  confidence?: number;
  price?: number;
  upper_band?: number;
  middle_band?: number;
  lower_band?: number;
  bb_position?: number;
  forecast_timestamp: number; // From when the forecast was made
  ohlcv_data_timestamp?: number; // Timestamp of the OHLCV data point this forecast might relate to
}

interface AssetDeepDiveCardProps {
  asset: RankedAssetSummary | null; // The selected asset from the ranked list
  requestTimeframe: string; // Added to know the context of the initial request
  onClose: () => void; // Function to close/hide this card
}

export const AssetDeepDiveCard: React.FC<AssetDeepDiveCardProps> = ({ asset, requestTimeframe, onClose }) => {
  const [ohlcvData, setOhlcvData] = useState<OHLCVDataPoint[]>([]);
  const [forecasts, setForecasts] = useState<ForecastSignal[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!asset || !requestTimeframe) {
      setOhlcvData([]);
      setForecasts([]);
      setError(null);
      return;
    }

    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // Parse asset string: e.g., "TRB-USDC_on_Ethereum"
        const parts = asset.asset.split("_on_");
        const assetSymbol = parts[0]; // e.g., "TRB-USDC"
        const chainName = parts.length > 1 ? parts[1] : "Unknown"; // e.g., "Ethereum"

        console.log(`Fetching data for: ${assetSymbol} on ${chainName}, timeframe: ${requestTimeframe}`);

        const response = await fetch(`/api/asset-details?assetSymbol=${encodeURIComponent(assetSymbol)}&chainName=${encodeURIComponent(chainName)}&timeframe=${encodeURIComponent(requestTimeframe)}`);
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ message: response.statusText }));
          throw new Error(errorData.message || `Failed to fetch asset details: ${response.statusText}`);
        }
        
        const data = await response.json();
        setOhlcvData(data.ohlcv || []);
        setForecasts(data.forecasts || []);

      } catch (err) {
        setError(err instanceof Error ? err.message : "An unknown error occurred");
        setOhlcvData([]);
        setForecasts([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [asset, requestTimeframe]);

  if (!asset) {
    return null; // Don't render if no asset is selected
  }

  // Helper to format timestamp for charts
  const formatXAxis = (tickItem: number) => {
    return new Date(tickItem * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  
  // Combine OHLCV data with forecast for plotting signals (example for price target)
  const combinedChartData = ohlcvData.map(ohlc => {
    const relevantForecast = forecasts.find(f => f.ohlcv_data_timestamp === ohlc.time && f.price);
    return {
      ...ohlc,
      forecastPrice: relevantForecast?.price,
      // Add other forecast indicators if needed (e.g., bb_upper, bb_lower)
      bb_upper: forecasts.find(f => f.ohlcv_data_timestamp === ohlc.time && f.upper_band)?.upper_band,
      bb_lower: forecasts.find(f => f.ohlcv_data_timestamp === ohlc.time && f.lower_band)?.lower_band,
    };
  });


  return (
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl opacity-0 animate-fadeIn mt-6 bg-slate-800 border-slate-700 text-gray-300">
      <CardHeader className="flex flex-row justify-between items-center">
        <div>
          <CardTitle className="flex items-center gap-2 text-xl font-semibold text-teal-400">
            <Eye className="h-6 w-6 text-teal-500" />
            Asset Deep Dive: <span className="text-teal-300">{asset.asset}</span>
          </CardTitle>
          <CardDescription className="text-slate-400">
            Detailed OHLCV chart and forecast signals for the selected asset.
          </CardDescription>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose} className="text-slate-400 hover:text-slate-200 hover:bg-slate-700">
          Close
        </Button>
      </CardHeader>
      <CardContent className="space-y-6 pt-2">
        {isLoading && (
          <div className="flex justify-center items-center min-h-[300px]">
            <svg className="animate-spin h-8 w-8 text-teal-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="ml-3 text-slate-300">Loading asset details...</p>
          </div>
        )}
        {error && (
          <div className="text-center py-10 text-red-400">
            <p>Error loading asset details: {error}</p>
            <Button variant="outline" onClick={() => { /* TODO: Implement retry logic */ }} className="mt-4 border-red-400 text-red-300 hover:bg-red-800/50">
              Retry
            </Button>
          </div>
        )}
        {!isLoading && !error && (
          <>
            {/* OHLCV Chart with Forecasts */}
            <div className="h-[400px] bg-slate-700/30 p-4 rounded-md">
              <h4 className="font-semibold text-md mb-3 text-slate-200">OHLCV Chart & Bollinger Bands (Example)</h4>
              {ohlcvData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={combinedChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                    <XAxis dataKey="time" tickFormatter={formatXAxis} stroke="#94a3b8" dy={10} />
                    <YAxis yAxisId="left" stroke="#94a3b8" domain={['auto', 'auto']} allowDataOverflow={true}/>
                    <Tooltip
                        contentStyle={{ backgroundColor: 'rgba(30, 41, 59, 0.9)', borderColor: '#475569', color: '#e2e8f0' }}
                        itemStyle={{ color: '#cbd5e1' }}
                        cursor={{ fill: 'rgba(71, 85, 105, 0.3)' }}
                    />
                    <Legend wrapperStyle={{ color: '#e2e8f0' }} />
                    {/* Candlestick would be ideal here, but recharts doesn't have a native one.
                        Using Line for Close price, and Area for High-Low range as a simplified representation.
                        Or focus on a line chart for 'close' and add Bollinger Bands.
                    */}
                    <Line yAxisId="left" type="monotone" dataKey="close" stroke="#2dd4bf" name="Close Price" dot={false} strokeWidth={2} />
                    {/* Example Bollinger Bands from forecast data */}
                    {forecasts.some(f => f.upper_band && f.lower_band) && (
                        <>
                            <Line yAxisId="left" type="monotone" dataKey="bb_upper" stroke="#f472b6" name="Upper Band" dot={false} strokeWidth={1} strokeDasharray="5 5" />
                            <Line yAxisId="left" type="monotone" dataKey="bb_lower" stroke="#f472b6" name="Lower Band" dot={false} strokeWidth={1} strokeDasharray="5 5" />
                            {/* <Line yAxisId="left" type="monotone" dataKey="bb_middle" stroke="#a78bfa" name="Middle Band" dot={false} strokeWidth={1} strokeDasharray="3 3" /> */}
                        </>
                    )}
                     {forecasts.some(f => f.price) && (
                         <Line yAxisId="left" type="monotone" dataKey="forecastPrice" name="Forecast Price" stroke="#fbbf24" strokeWidth={2} dot={{ r: 4 }} strokeDasharray="8 4" />
                     )}
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-slate-500 italic text-center py-10">No OHLCV data available for this asset.</p>
              )}
            </div>

            {/* Forecast Signals Summary */}
            <div className="mt-6">
              <h4 className="font-semibold text-md mb-3 text-slate-200">Active Forecast Signals</h4>
              {forecasts.length > 0 ? (
                <div className="grid md:grid-cols-2 gap-4">
                  {forecasts.map((signal, index) => (
                    <Card key={index} className="bg-slate-700/50 border-slate-600 text-slate-300">
                      <CardHeader className="pb-3 pt-4 px-4">
                        <CardTitle className="text-base font-semibold text-teal-400">{signal.signal_type.replace(/_/g, ' ')}</CardTitle>
                        <CardDescription className="text-xs text-slate-400">
                          Forecasted: {new Date(signal.forecast_timestamp * 1000).toLocaleString()}
                          {signal.ohlcv_data_timestamp && ` (Data @ ${new Date(signal.ohlcv_data_timestamp * 1000).toLocaleTimeString()})`}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="px-4 pb-4 text-sm space-y-1">
                        {signal.confidence && <p>Confidence: <span className="font-semibold text-teal-300">{(signal.confidence * 100).toFixed(1)}%</span></p>}
                        {signal.price && <p>Target Price: <span className="font-semibold text-amber-400">${signal.price.toFixed(4)}</span></p>}
                        {signal.upper_band && <p>BB Upper: <span className="font-semibold text-pink-400">${signal.upper_band.toFixed(4)}</span></p>}
                        {signal.middle_band && <p>BB Middle: <span className="font-semibold text-purple-400">${signal.middle_band.toFixed(4)}</span></p>}
                        {signal.lower_band && <p>BB Lower: <span className="font-semibold text-pink-400">${signal.lower_band.toFixed(4)}</span></p>}
                        {signal.bb_position !== undefined && <p>BB Position: <span className="font-semibold text-sky-400">{signal.bb_position.toFixed(3)}</span></p>}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 italic">No active forecast signals for this asset.</p>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}; 