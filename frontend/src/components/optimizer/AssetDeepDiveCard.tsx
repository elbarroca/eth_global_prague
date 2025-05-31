"use client";

import React, { useEffect, useState, useMemo } from 'react';
import Image from 'next/image';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, X } from 'lucide-react';
import { RankedAssetSummary } from '@/types/portfolio-api';
import { Button } from '../ui/button';
<<<<<<< HEAD
import { useAssetData } from '@/hooks/useAssetData';
import { useAssetCoreDetails } from '@/hooks/useAssetCoreDetails';
=======
import { useOhlcvData } from '@/hooks/mongo/useOHLCV'; // Corrected import path
import { useForecastSignals } from '@/hooks/mongo/useForecast'; // Corrected import path
// import { useAssetCoreDetails, AssetCoreDetails } from '@/hooks/mongo/useAssetCoreDetails'; // Adjust path if needed
>>>>>>> c12bea4bc7c5ae306b86dae483d12381f417d034

interface OHLCVDataPoint {
  time?: number; // timestamp
  timestamp?: number; // alternative timestamp field
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface ForecastSignal {
  signal_type: string;
  confidence?: number;
  details: { [key: string]: any };
  forecast_timestamp: number; // From when the forecast was made
  ohlcv_data_timestamp?: number; // Timestamp of the OHLCV data point this forecast might relate to
}

interface AssetDeepDiveCardProps {
  asset: RankedAssetSummary | null; // The selected asset from the ranked list
  requestTimeframe: string; // Added to know the context of the initial request
  onClose: () => void; // Function to close/hide this card
}

export const AssetDeepDiveCard: React.FC<AssetDeepDiveCardProps> = ({ asset, requestTimeframe, onClose }) => {
  // Parse asset identifiers from the asset prop
  const assetIdentifier = asset?.asset || ""; // e.g. "ETH-USDC_on_Ethereum"
  
  const identifierParts = assetIdentifier.split("_on_");
  const tokenPairString = identifierParts[0] || "";
  const chainNameFromAsset = identifierParts[1] || "Unknown Chain";

  const symbolParts = tokenPairString.split("-");
  const baseSymbol = symbolParts[0] || "N/A";
  const quoteSymbol = symbolParts[1] || "N/A"; // Parse quote symbol

  // Use the new combined hook
  const {
    data: assetData,
    isLoading: isLoadingAssetData,
    error: errorAssetData,
    refetch: refetchAssetData,
    ohlcvData,
    forecastSignals,
    dataSources
  } = useAssetData({
    chainId: asset?.chain_id || null,
    baseTokenAddress: asset?.base_token_address || null,
    quoteTokenAddress: asset?.quote_token_address || null,
    timeframe: requestTimeframe,
    maxForecastAgeHours: 4,
    baseSymbolHint: baseSymbol !== "N/A" ? baseSymbol : null, // Pass hints
    quoteSymbolHint: quoteSymbol !== "N/A" ? quoteSymbol : null,
  });

  const {
    data: assetCoreDetails,
    isLoading: isLoadingAssetCoreDetails,
    error: errorAssetCoreDetails,
    refetch: refetchAssetCoreDetails
  } = useAssetCoreDetails({
    chainId: asset?.chain_id ?? null,
    tokenAddress: asset?.base_token_address ?? null // Fetching details for the base token
  });

  // Derived state for easier use in the component - memoized to prevent re-renders
  const ohlcvCandles = useMemo(() => ohlcvData?.ohlcv_candles || [], [ohlcvData]);
  const forecastSignalsArray = useMemo(() => forecastSignals || [], [forecastSignals]);

  // Combined loading and error states
  const isLoading = isLoadingAssetData || isLoadingAssetCoreDetails;
  const error = errorAssetData || errorAssetCoreDetails;

  // Memoized chart data processing
  const ohlcvChartData = useMemo(() => {
    if (!ohlcvCandles.length) return [];
    
    console.log('Processing OHLCV data for chart:', {
      totalCandles: ohlcvCandles.length,
      firstCandle: ohlcvCandles[0],
      lastCandle: ohlcvCandles[ohlcvCandles.length - 1]
    });

         const processedData = ohlcvCandles.map((ohlc, index) => {
       // Handle time field
       const timeNum = typeof ohlc.time === 'number' ? ohlc.time : parseInt(String(ohlc.time), 10);
      
      const open = typeof ohlc.open === 'number' ? ohlc.open : parseFloat(String(ohlc.open));
      const high = typeof ohlc.high === 'number' ? ohlc.high : parseFloat(String(ohlc.high));
      const low = typeof ohlc.low === 'number' ? ohlc.low : parseFloat(String(ohlc.low));
      const close = typeof ohlc.close === 'number' ? ohlc.close : parseFloat(String(ohlc.close));
      
      if (isNaN(timeNum) || isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close)) {
        console.warn('Skipping invalid OHLC data point:', ohlc);
        return null;
      }
      
      return {
        index,
        time: timeNum,
        open,
        high,
        low,
        close,
        // Add formatted date for easier debugging
        date: new Date(timeNum * 1000).toISOString().split('T')[0]
      };
    }).filter(Boolean);

    console.log('Processed chart data:', {
      processedCount: processedData.length,
      firstProcessed: processedData[0],
      lastProcessed: processedData[processedData.length - 1]
    });

    return processedData;
  }, [ohlcvCandles]);

  const handleRetry = () => {
    if (errorAssetData) refetchAssetData();
    if (errorAssetCoreDetails) refetchAssetCoreDetails();
  };

  useEffect(() => {
    if (asset) {
      console.log('AssetDeepDiveCard - Asset:', asset);
      console.log('AssetDeepDiveCard - Timeframe:', requestTimeframe);
      console.log('AssetDeepDiveCard - Raw OHLCV Data from hook (ohlcvData):', ohlcvData);
      console.log('AssetDeepDiveCard - Raw OHLCV Candles from hook (ohlcvCandles):', ohlcvCandles.slice(0,5));
      console.log('AssetDeepDiveCard - Mapped OHLCV Chart Data (ohlcvChartData):', ohlcvChartData.slice(0,5));
      console.log('AssetDeepDiveCard - OHLCV Candles Length:', ohlcvCandles.length);
      console.log('AssetDeepDiveCard - OHLCV Chart Data Length:', ohlcvChartData.length);
      console.log('AssetDeepDiveCard - Forecast Signals:', forecastSignalsArray.slice(0,5));
      console.log('AssetDeepDiveCard - Data Sources:', dataSources);
      console.log('AssetDeepDiveCard - Loading states:', { isLoadingAssetData, isLoadingAssetCoreDetails });
      console.log('AssetDeepDiveCard - Errors:', { errorAssetData, errorAssetCoreDetails });
    }
  }, [asset, requestTimeframe, ohlcvData, ohlcvCandles, forecastSignalsArray, dataSources, ohlcvChartData, isLoadingAssetData, isLoadingAssetCoreDetails, errorAssetData, errorAssetCoreDetails]);

  if (!asset) {
    return null;
  }

  return (
    <Card className="shadow-xl transition-all duration-300 ease-out opacity-0 animate-fadeIn mt-6 bg-slate-800/80 border-slate-700 text-gray-300 backdrop-blur-md">
      <CardHeader className="flex flex-row justify-between items-start pt-4 pb-3 px-5 bg-slate-700/30 rounded-t-lg">
        <div>
          <CardTitle className="flex items-center gap-2.5 text-lg font-semibold text-white">
            {isLoadingAssetCoreDetails && <div className="h-6 w-6 rounded-full bg-slate-600 animate-pulse"></div>}
            {!isLoadingAssetCoreDetails && assetCoreDetails?.logo_uri && (
              <Image src={assetCoreDetails.logo_uri} alt={assetCoreDetails.name || baseSymbol} width={24} height={24} className="rounded-full" />
            )}
            <Activity className="h-5 w-5 text-teal-400" />
            Asset Deep Dive: <span className="text-teal-300">
              {(assetCoreDetails?.name && assetCoreDetails.name !== baseSymbol && assetCoreDetails.name.toLowerCase() !== baseSymbol.toLowerCase()) ? assetCoreDetails.name : baseSymbol} ({baseSymbol}) on {chainNameFromAsset}
            </span>
          </CardTitle>
          <CardDescription className="text-slate-400 text-xs mt-1">
            OHLCV chart and forecast signals for timeframe: {requestTimeframe}. 
            {assetCoreDetails && ` Decimals: ${assetCoreDetails.decimals}`}
            {dataSources.ohlcv && <span className="ml-2 text-xs bg-slate-600 px-2 py-1 rounded">OHLCV: {dataSources.ohlcv}</span>}
            {dataSources.forecasts && <span className="ml-2 text-xs bg-slate-600 px-2 py-1 rounded">Forecasts: {dataSources.forecasts}</span>}
          </CardDescription>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="text-slate-400 hover:text-slate-100 hover:bg-slate-700 h-8 w-8">
          <X className="h-5 w-5" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-6 p-5">
        {isLoading && (
          <div className="flex flex-col justify-center items-center min-h-[300px] space-y-3">
            <svg className="animate-spin h-8 w-8 text-teal-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="ml-3 text-slate-300">Loading asset details...</p>
          </div>
        )}
        {error && (
          <div className="text-center py-10 text-red-400 bg-red-900/20 rounded-md p-6">
            <p className="font-semibold mb-2">Error loading asset details:</p>
            <p className="text-sm">{String(error)}</p>
            <Button variant="outline" onClick={handleRetry} className="mt-4 border-red-400 text-red-300 hover:bg-red-800/50 hover:text-red-200">
              Retry
            </Button>
          </div>
        )}
        {!isLoading && !error && (
          <>
            <div className="h-[400px] bg-slate-700/40 p-4 rounded-lg shadow-inner">
              <h4 className="font-semibold text-md mb-4 text-slate-100">
                Price Chart 
                <span className="text-xs text-slate-400 ml-2">
                  ({ohlcvChartData.length} data points)
                </span>
              </h4>
              {ohlcvChartData.length > 0 ? (
                <div className="h-full">
                  <ResponsiveContainer width="100%" height={350}>
                    <LineChart 
                      data={ohlcvChartData} 
                      margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
                      <XAxis 
                        dataKey="index" 
                        stroke="#A0AEC0" 
                        tick={{ fontSize: 10 }}
                        tickFormatter={(value) => {
                          if (value >= 0 && value < ohlcvChartData.length) {
                            const dataPoint = ohlcvChartData[value];
                            if (dataPoint?.date) {
                              return dataPoint.date.slice(5); // MM-DD format
                            }
                          }
                          return '';
                        }}
                      />
                      <YAxis 
                        stroke="#A0AEC0" 
                        tick={{ fontSize: 10 }} 
                        width={70}
                        domain={['dataMin', 'dataMax']}
                        tickFormatter={(value) => {
                          const num = Number(value);
                          if (isNaN(num)) return "0";
                          if (num < 1) return num.toFixed(4);
                          if (num < 1000) return num.toFixed(2);
                          return num.toFixed(0);
                        }}
                      />
                      <Tooltip
                        contentStyle={{ 
                          backgroundColor: '#1a202c', 
                          border: '1px solid #4A5568',
                          borderRadius: '8px',
                          color: '#E2E8F0'
                        }}
                        labelFormatter={(label) => {
                          const idx = Number(label);
                          if (idx >= 0 && idx < ohlcvChartData.length) {
                            const dataPoint = ohlcvChartData[idx];
                            return dataPoint?.date || 'Unknown Date';
                          }
                          return 'Unknown Date';
                        }}
                        formatter={(value, name) => {
                          const numValue = Number(value);
                          if (isNaN(numValue)) return ['Invalid', name];
                          return [`$${numValue.toFixed(4)}`, 'Price']; 
                        }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="close" 
                        stroke="#4FD1C5" 
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 3, fill: '#4FD1C5' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : ohlcvCandles.length > 0 ? (
                // Fallback simple chart if Recharts fails but we have data
                <div className="h-full flex flex-col">
                  <div className="text-center text-slate-400 text-sm mb-4">
                    Simple Price Visualization ({ohlcvCandles.length} candles)
                  </div>
                  <div className="flex-1 relative bg-slate-800/50 rounded p-2">
                    <div className="h-full flex items-end justify-between gap-1">
                      {ohlcvCandles.slice(-50).map((candle, index) => {
                        const maxPrice = Math.max(...ohlcvCandles.slice(-50).map(c => Number(c.close)));
                        const minPrice = Math.min(...ohlcvCandles.slice(-50).map(c => Number(c.close)));
                        const priceRange = maxPrice - minPrice;
                        const normalizedHeight = priceRange > 0 ? ((Number(candle.close) - minPrice) / priceRange) * 100 : 50;
                        
                        return (
                          <div
                            key={index}
                            className="bg-teal-400 rounded-sm min-w-[2px] transition-all hover:bg-teal-300"
                            style={{ height: `${Math.max(normalizedHeight, 2)}%` }}
                            title={`${new Date(Number(candle.time) * 1000).toLocaleDateString()}: $${Number(candle.close).toFixed(4)}`}
                          />
                        );
                      })}
                    </div>
                    <div className="absolute bottom-0 left-0 right-0 flex justify-between text-xs text-slate-500 mt-1">
                      <span>{ohlcvCandles.length > 0 ? new Date(Number(ohlcvCandles[Math.max(0, ohlcvCandles.length - 50)].time) * 1000).toLocaleDateString() : ''}</span>
                      <span>{ohlcvCandles.length > 0 ? new Date(Number(ohlcvCandles[ohlcvCandles.length - 1].time) * 1000).toLocaleDateString() : ''}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-10">
                  <p className="text-slate-500 italic">No valid price data available to chart after processing.</p>
                  <p className="text-slate-400 text-sm mt-2">
                    Raw OHLCV Candles fetched: {ohlcvCandles.length} | 
                    Processed chart data points: {ohlcvChartData.length}
                  </p>
                  {ohlcvCandles.length > 0 && ohlcvChartData.length === 0 && (
                    <p className="text-xs text-orange-400 mt-1">All fetched candles might have been invalid for charting. Check console warnings.</p>
                  )}
                  {ohlcvCandles.length > 0 && (
                    <details className="mt-4 text-left">
                      <summary className="text-xs text-slate-400 cursor-pointer">Debug: Show first few raw candles</summary>
                      <pre className="text-xs text-slate-300 mt-2 bg-slate-900/50 p-2 rounded overflow-auto max-h-32">
                        {JSON.stringify(ohlcvCandles.slice(0, 3), null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              )}
            </div>

            <div className="mt-8">
              <h4 className="font-semibold text-md mb-4 text-slate-100">Active Forecast Signals Summary</h4>
              {forecastSignalsArray.length > 0 ? (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {forecastSignalsArray.map((signal, index) => (
                    <Card key={`${signal.signal_type}-${index}`} className="bg-slate-700/60 border-slate-600/70 text-slate-300 transition-all hover:shadow-lg hover:border-slate-500">
                      <CardHeader className="pb-2 pt-3 px-4">
                        <CardTitle className="text-sm font-semibold text-teal-400 capitalize">{signal.signal_type.replace(/_/g, ' ')}</CardTitle>
                        <CardDescription className="text-xs text-slate-400 pt-0.5">
                          Forecasted: {new Date(signal.forecast_timestamp * 1000).toLocaleDateString()} {new Date(signal.forecast_timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute:'2-digit'})}
                          {signal.ohlcv_data_timestamp && <span className="block text-xs">Based on data from: {new Date(signal.ohlcv_data_timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute:'2-digit'})}</span>}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="px-4 pb-3 text-xs space-y-1.5">
                        {typeof signal.confidence === 'number' && <p>Confidence: <span className="font-semibold text-teal-300">{(signal.confidence * 100).toFixed(1)}%</span></p>}
                        {signal.details && Object.entries(signal.details).map(([key, value]) => {
                          if (typeof value === 'number') {
                            return <p key={key} className="capitalize">{key.replace(/_/g, ' ')}: <span className="font-semibold text-amber-400">{value.toFixed(4)}</span></p>;
                          } else if (typeof value === 'string' || typeof value === 'boolean') {
                            return <p key={key} className="capitalize">{key.replace(/_/g, ' ')}: <span className="font-semibold text-sky-400">{String(value)}</span></p>;
                          }
                          return null;
                        })}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 italic text-center py-6">No active forecast signals found for this asset and timeframe.</p>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}; 