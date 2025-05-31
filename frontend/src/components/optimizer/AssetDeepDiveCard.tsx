"use client";

import React, { useEffect, useState, useMemo } from 'react';
import Image from 'next/image';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, X, ArrowLeft } from 'lucide-react';
import { RankedAssetSummary } from '@/types/portfolio-api';
import { Button } from '../ui/button';
import { useAssetData } from '@/hooks/useAssetData';
import { useAssetCoreDetails } from '@/hooks/useAssetCoreDetails';

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
    
    // console.log('Processing OHLCV data for chart:', {
    //   totalCandles: ohlcvCandles.length,
    //   firstCandle: ohlcvCandles[0],
    //   lastCandle: ohlcvCandles[ohlcvCandles.length - 1]
    // });

         const processedData = ohlcvCandles.map((ohlc, index) => {
       // Handle time field
       const timeNum = typeof ohlc.time === 'number' ? ohlc.time : parseInt(String(ohlc.time), 10);
      
      const open = typeof ohlc.open === 'number' ? ohlc.open : parseFloat(String(ohlc.open));
      const high = typeof ohlc.high === 'number' ? ohlc.high : parseFloat(String(ohlc.high));
      const low = typeof ohlc.low === 'number' ? ohlc.low : parseFloat(String(ohlc.low));
      const close = typeof ohlc.close === 'number' ? ohlc.close : parseFloat(String(ohlc.close));
      
      if (isNaN(timeNum) || isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close)) {
        // console.warn('Skipping invalid OHLC data point:', ohlc);
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

    // console.log('Processed chart data:', {
    //   processedCount: processedData.length,
    //   firstProcessed: processedData[0],
    //   lastProcessed: processedData[processedData.length - 1]
    // });

    return processedData;
  }, [ohlcvCandles]);

  const handleRetry = () => {
    if (errorAssetData) refetchAssetData();
    if (errorAssetCoreDetails) refetchAssetCoreDetails();
  };

  // Minimal logging in production
  useEffect(() => {
    if (process.env.NODE_ENV === 'development' && asset) {
      console.log('AssetDeepDiveCard - Dev Log:', {
        asset,
        requestTimeframe,
        ohlcvDataLength: ohlcvData?.ohlcv_candles?.length,
        ohlcvCandlesLength: ohlcvCandles.length,
        ohlcvChartDataLength: ohlcvChartData.length,
        forecastSignalsCount: forecastSignalsArray.length,
        dataSources,
        isLoadingAssetData,
        isLoadingAssetCoreDetails,
        errorAssetData,
        errorAssetCoreDetails,
      });
    }
  }, [asset, requestTimeframe, ohlcvData, ohlcvCandles, forecastSignalsArray, dataSources, ohlcvChartData, isLoadingAssetData, isLoadingAssetCoreDetails, errorAssetData, errorAssetCoreDetails]);


  if (!asset) {
    return null;
  }

  return (
    <Card className="shadow-2xl transition-all duration-500 ease-in-out opacity-0 animate-fadeIn mt-6 bg-gradient-to-br from-slate-800 via-slate-850 to-slate-900 border border-slate-700 text-gray-300 backdrop-blur-lg rounded-xl overflow-hidden">
      <CardHeader className="flex flex-row justify-between items-center pt-5 pb-4 px-6 bg-slate-800/50 border-b border-slate-700">
        <div className="flex-grow">
          <CardTitle className="flex items-center gap-3 text-xl font-bold text-white">
            {isLoadingAssetCoreDetails && <div className="h-7 w-7 rounded-full bg-slate-700 animate-pulse"></div>}
            {!isLoadingAssetCoreDetails && assetCoreDetails?.logo_uri && (
              <Image src={assetCoreDetails.logo_uri} alt={assetCoreDetails.name || baseSymbol} width={28} height={28} className="rounded-full shadow-md border border-slate-600" />
            )}
            <Activity className="h-6 w-6 text-teal-400" />
            <span className="truncate max-w-md">
              Deep Dive: <span className="text-teal-300 font-semibold">
                {(assetCoreDetails?.name && assetCoreDetails.name !== baseSymbol && assetCoreDetails.name.toLowerCase() !== baseSymbol.toLowerCase()) ? assetCoreDetails.name : baseSymbol}
              </span>
              <span className="text-slate-400 font-normal text-sm"> ({baseSymbol}) on {chainNameFromAsset}</span>
            </span>
          </CardTitle>
          <CardDescription className="text-slate-400 text-xs mt-1.5 flex items-center gap-2 flex-wrap">
            <span>Timeframe: <span className='font-medium text-slate-300'>{requestTimeframe}</span></span>
            {assetCoreDetails && <span>Decimals: <span className='font-medium text-slate-300'>{assetCoreDetails.decimals}</span></span>}
            {dataSources.ohlcv && <span className="text-xs bg-slate-700 px-2 py-0.5 rounded-full shadow-sm">OHLCV: {dataSources.ohlcv}</span>}
            {dataSources.forecasts && <span className="text-xs bg-slate-700 px-2 py-0.5 rounded-full shadow-sm">Forecasts: {dataSources.forecasts}</span>}
          </CardDescription>
        </div>
        <div className="flex items-center gap-2 ml-4 flex-shrink-0">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={onClose} 
            className="text-slate-300 hover:text-teal-300 border-slate-600 hover:border-teal-500/70 bg-slate-700/40 hover:bg-slate-700/70 transition-all duration-300 rounded-lg py-2 px-4 group"
            title="Back to Portfolio Results"
          >
            <ArrowLeft className="h-4 w-4 mr-2 text-slate-400 group-hover:text-teal-400 transition-colors" />
            Back to Portfolio
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose} className="text-slate-400 hover:text-slate-100 hover:bg-slate-700/70 rounded-full h-9 w-9">
            <X className="h-5 w-5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-8 p-6">
        {isLoading && (
          <div className="flex flex-col justify-center items-center min-h-[350px] space-y-4 py-10">
            <svg className="animate-spin h-10 w-10 text-teal-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="text-lg text-slate-300 font-medium">Loading asset details...</p>
            <p className="text-sm text-slate-400">Please wait while we fetch the latest data.</p>
          </div>
        )}
        {error && (
          <div className="text-center py-12 bg-red-900/30 border border-red-700 rounded-lg p-8 shadow-lg">
            <p className="font-semibold text-lg text-red-300 mb-3">Error Loading Asset Details</p>
            <p className="text-sm text-red-400 mb-6">{String(error)}</p>
            <Button variant="outline" onClick={handleRetry} className="border-red-500 text-red-300 hover:bg-red-800/60 hover:text-red-200 hover:border-red-400 transition-colors duration-150 px-6 py-2 rounded-md shadow-md">
              Retry Fetching Data
            </Button>
          </div>
        )}
        {!isLoading && !error && (
          <>
            <div className="h-[450px] bg-slate-800/60 p-5 rounded-lg shadow-xl border border-slate-700/80">
              <h4 className="font-semibold text-lg mb-1 text-slate-100">
                Price Performance
              </h4>
              <p className="text-xs text-slate-400 mb-4">
                Showing {ohlcvChartData.length} data points for {baseSymbol}/{quoteSymbol}
              </p>
              {ohlcvChartData.length > 1 ? ( // Require at least 2 points for a line chart
                <div className="h-[350px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart 
                      data={ohlcvChartData} 
                      margin={{ top: 5, right: 20, left: -10, bottom: 5 }} // Adjusted margins
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" strokeOpacity={0.3} />
                      <XAxis 
                        dataKey="index" 
                        stroke="#A0AEC0" 
                        tick={{ fontSize: 11, fill: '#A0AEC0' }}
                        axisLine={{ stroke: '#525f7f' }}
                        tickLine={{ stroke: '#525f7f' }}
                        tickFormatter={(value) => {
                          if (value >= 0 && value < ohlcvChartData.length) {
                            const dataPoint = ohlcvChartData[value];
                            if (dataPoint?.date) {
                              // Show MM-DD, and on first/last tick, show YYYY-MM-DD for clarity
                              if (value === 0 || value === ohlcvChartData.length -1 || value % Math.floor(ohlcvChartData.length / 5) === 0) {
                                return dataPoint.date.slice(5); //MM-DD
                              }
                              return dataPoint.date.slice(5);
                            }
                          }
                          return '';
                        }}
                        interval="preserveStartEnd" // Show first and last tick
                        // Consider adding more ticks if data is dense:
                        // tickCount={Math.min(10, ohlcvChartData.length)} 
                      />
                      <YAxis 
                        stroke="#A0AEC0" 
                        tick={{ fontSize: 11, fill: '#A0AEC0' }} 
                        width={80} // Increased width for better formatting
                        domain={['auto', 'auto']} // Adjusted domain
                        axisLine={{ stroke: '#525f7f' }}
                        tickLine={{ stroke: '#525f7f' }}
                        tickFormatter={(value) => {
                          const num = Number(value);
                          if (isNaN(num)) return "0";
                          if (num === 0) return "0";
                          if (Math.abs(num) < 0.0001) return num.toExponential(2);
                          if (Math.abs(num) < 1) return num.toFixed(5);
                          if (Math.abs(num) < 1000) return num.toFixed(2);
                          return num.toLocaleString(undefined, {maximumFractionDigits: 0});
                        }}
                        allowDataOverflow={true} // Allows better auto domain
                      />
                      <Tooltip
                        contentStyle={{ 
                          backgroundColor: 'rgba(26, 32, 44, 0.9)', // Slightly transparent dark bg
                          border: '1px solid #4A5568',
                          borderRadius: '10px', // More rounded
                          color: '#E2E8F0',
                          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                          padding: '10px 12px'
                        }}
                        itemStyle={{ color: '#E2E8F0' }}
                        labelStyle={{ color: '#cbd5e0', fontWeight: 'bold', marginBottom: '6px' }}
                        labelFormatter={(label) => {
                          const idx = Number(label);
                          if (idx >= 0 && idx < ohlcvChartData.length) {
                            const dataPoint = ohlcvChartData[idx];
                            return dataPoint?.date ? `Date: ${dataPoint.date}` : 'Unknown Date';
                          }
                          return 'Unknown Date';
                        }}
                        formatter={(value, name, props) => {
                          const numValue = Number(value);
                          const { payload } = props;
                          if (isNaN(numValue)) return ['Invalid', name];
                          
                          const formattedValue = numValue < 1 ? `$${numValue.toFixed(6)}` : `$${numValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                          
                          return [
                            <span key={`${name}-${payload?.time || 'price'}`} style={{ color: '#4FD1C5' }}>{formattedValue}</span>,
                            'Close Price'
                          ];
                        }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="close" 
                        stroke="#4FD1C5" // Teal
                        strokeWidth={2.5}
                        dot={false}
                        activeDot={{ r: 6, fill: '#4FD1C5', stroke: '#1A202C', strokeWidth: 2 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : ohlcvCandles.length > 0 ? ( // Simple fallback if Recharts fails or not enough data points
                <div className="h-[350px] flex flex-col items-center justify-center text-center">
                   <p className="text-slate-400 text-md mb-2">Limited Data for Full Chart</p>
                   <p className="text-slate-500 text-sm mb-4">
                     Displaying basic visualization for {ohlcvCandles.length} candle{ohlcvCandles.length === 1 ? '' : 's'}.
                   </p>
                  <div className="w-full max-w-md h-40 relative bg-slate-700/50 rounded p-3 shadow-inner">
                    <div className="h-full flex items-end justify-around gap-1">
                      {ohlcvCandles.slice(-50).map((candle, index) => {
                        const closePrices = ohlcvCandles.slice(-50).map(c => Number(c.close));
                        const maxPrice = Math.max(...closePrices);
                        const minPrice = Math.min(...closePrices);
                        const priceRange = maxPrice - minPrice;
                        const normalizedHeight = priceRange > 0 ? ((Number(candle.close) - minPrice) / priceRange) * 90 : 50; // Use 90% of height
                        
                        return (
                          <div
                            key={index}
                            className="bg-teal-500 rounded-t-sm flex-grow min-w-[3px] transition-all hover:bg-teal-400"
                            style={{ height: `${Math.max(normalizedHeight, 5)}%` }} // Min height 5%
                            title={`${new Date(Number(candle.time) * 1000).toLocaleDateString()} - Close: $${Number(candle.close).toFixed(4)}`}
                          />
                        );
                      })}
                    </div>
                  </div>
                  <div className="w-full max-w-md flex justify-between text-xs text-slate-500 mt-2 px-1">
                      <span>{ohlcvCandles.length > 0 ? new Date(Number(ohlcvCandles[Math.max(0, ohlcvCandles.length - 50)].time) * 1000).toLocaleDateString() : ''}</span>
                      <span>{ohlcvCandles.length > 0 ? new Date(Number(ohlcvCandles[ohlcvCandles.length - 1].time) * 1000).toLocaleDateString() : ''}</span>
                  </div>
                </div>
              ) : (
                <div className="text-center py-16 min-h-[350px] flex flex-col justify-center items-center">
                  <Activity className="h-12 w-12 text-slate-600 mb-4" />
                  <p className="text-slate-400 italic text-lg">No Price Data Available</p>
                  <p className="text-slate-500 text-sm mt-2">
                    Could not fetch or process valid OHLCV data for charting.
                  </p>
                  { (process.env.NODE_ENV === 'development' && ohlcvCandles.length > 0 && ohlcvChartData.length === 0) && (
                    <p className="text-xs text-orange-500 mt-3 bg-orange-900/30 px-3 py-1 rounded-md">
                      Dev Info: {ohlcvCandles.length} raw candles fetched, but {ohlcvChartData.length} processed for chart. Check console for data validation warnings.
                    </p>
                  )}
                   { (process.env.NODE_ENV === 'development' && ohlcvCandles.length > 0) && (
                    <details className="mt-4 text-left w-full max-w-md">
                      <summary className="text-xs text-slate-500 hover:text-slate-300 cursor-pointer transition-colors">Debug: Show first 3 raw candles</summary>
                      <pre className="text-xs text-slate-400 mt-2 bg-slate-900/70 p-3 rounded overflow-auto max-h-40 border border-slate-700">
                        {JSON.stringify(ohlcvCandles.slice(0, 3), null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              )}
            </div>

            <div className="mt-10">
              <h4 className="font-semibold text-lg mb-5 text-slate-100">Active Forecast Signals</h4>
              {forecastSignalsArray.length > 0 ? (
                <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
                  {forecastSignalsArray.map((signal, index) => (
                    <Card key={`${signal.signal_type}-${index}-${signal.forecast_timestamp}`} className="bg-slate-800/70 border border-slate-700/90 text-slate-300 transition-all duration-300 hover:shadow-xl hover:border-slate-600 hover:scale-[1.02] rounded-lg overflow-hidden">
                      <CardHeader className="pb-2.5 pt-4 px-5 bg-slate-700/30 border-b border-slate-700">
                        <CardTitle className="text-base font-semibold text-teal-400 capitalize tracking-wide">{signal.signal_type.replace(/_/g, ' ')}</CardTitle>
                        <CardDescription className="text-xs text-slate-400 pt-1">
                          Forecast: {new Date(signal.forecast_timestamp * 1000).toLocaleDateString()} {new Date(signal.forecast_timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute:'2-digit', hour12: true })}
                          {signal.ohlcv_data_timestamp && <span className="block text-xs opacity-80">Basis: Data from {new Date(signal.ohlcv_data_timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute:'2-digit', hour12: true})}</span>}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="px-5 py-4 text-sm space-y-2">
                        {typeof signal.confidence === 'number' && (
                          <p className="flex justify-between items-center">
                            <span className="text-slate-400">Confidence:</span>
                            <span className={`font-bold text-lg ${signal.confidence > 0.7 ? 'text-green-400' : signal.confidence > 0.4 ? 'text-yellow-400' : 'text-red-400'}`}>
                              {(signal.confidence * 100).toFixed(1)}%
                            </span>
                          </p>
                        )}
                        {signal.details && Object.entries(signal.details).map(([key, value]) => {
                          const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                          let formattedValue;
                          let valueColor = 'text-sky-300';

                          if (typeof value === 'number') {
                            formattedValue = value.toFixed(value % 1 === 0 ? 0 : 4); // No decimals for whole numbers
                            if (key.toLowerCase().includes('price') || key.toLowerCase().includes('value')) {
                                formattedValue = `$${formattedValue}`;
                            }
                            valueColor = 'text-amber-300';
                          } else if (typeof value === 'boolean') {
                            formattedValue = value ? 'Yes' : 'No';
                            valueColor = value ? 'text-green-400' : 'text-red-400';
                          } else {
                            formattedValue = String(value);
                          }
                          
                          return (
                            <p key={key} className="flex justify-between items-center text-xs border-t border-slate-700/50 pt-1.5 first-of-type:border-t-0 first-of-type:pt-0">
                              <span className="text-slate-400 capitalize">{formattedKey}:</span>
                              <span className={`font-medium ${valueColor}`}>{formattedValue}</span>
                            </p>
                          );
                        })}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 bg-slate-800/50 rounded-lg border border-slate-700 shadow-md">
                  <Activity className="h-10 w-10 text-slate-600 mb-3 mx-auto" />
                  <p className="text-slate-400 italic text-md">No Active Forecast Signals</p>
                  <p className="text-slate-500 text-sm mt-1.5">There are currently no forecast signals for this asset and timeframe.</p>
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}; 