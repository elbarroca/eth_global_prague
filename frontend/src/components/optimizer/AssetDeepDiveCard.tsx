"use client";

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, ComposedChart } from 'recharts';
import { TrendingUp, Activity, HelpCircle, Eye, X } from 'lucide-react';
import { OverallRequestSummary, RankedAssetSummary } from '@/types/portfolio-api'; // Assuming types might be useful
import { Button } from '../ui/button';
import { useOhlcvData } from '@/hooks/mongo/useOHLCV'; // Corrected import path
import { useForecastSignals } from '@/hooks/mongo/useForecast'; // Corrected import path
import { useAssetCoreDetails, AssetCoreDetails } from '@/hooks/mongo/useAssetCoreDetails'; // Adjust path if needed

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
  // Parse asset identifiers from the asset prop
  const assetIdentifier = asset?.asset || ""; // e.g. "ETH-USDC_on_Ethereum"
  const [tokenPair, chainNameFromAsset] = assetIdentifier.split("_on_"); // ["ETH-USDC", "Ethereum"]
  const [baseSymbol, quoteSymbol] = tokenPair.split("-"); // ["ETH", "USDC"]

  // Prepare params for hooks
  // IMPORTANT: RankedAssetSummary needs to provide chain_id, base_token_address, quote_token_address
  // If they are not directly available, this part will need adjustment or a lookup mechanism.
  const ohlcvParams = {
    chainId: asset?.chain_id || null,
    baseTokenAddress: asset?.base_token_address || null,
    quoteTokenAddress: asset?.quote_token_address || null,
    timeframe: requestTimeframe, // This will be a query param for the new endpoint
  };

  const forecastParams = {
    assetSymbol: assetIdentifier, // Pass the full "TOKEN-QUOTE_on_Chain" string
    chainId: asset?.chain_id, // Pass the chain_id from the asset
    // signalType: null, // Optionally, to filter by a specific signal type
  };

  const {
    data: ohlcvDataFull,
    isLoading: isLoadingOhlcv,
    error: errorOhlcv,
    refetch: refetchOhlcv
  } = useOhlcvData(ohlcvParams);

  const {
    signals: forecastSignalsData,
    isLoading: isLoadingForecasts,
    error: errorForecasts,
    refetch: refetchForecasts
  } = useForecastSignals(forecastParams);

  const {
    data: assetCoreDetails,
    isLoading: isLoadingAssetCoreDetails,
    error: errorAssetCoreDetails,
    refetch: refetchAssetCoreDetails
  } = useAssetCoreDetails({
    chainId: asset?.chain_id,
    tokenAddress: asset?.base_token_address // Fetching details for the base token
  });

  // Derived state for easier use in the component
  const ohlcvCandles = ohlcvDataFull?.ohlcv_candles || [];

  // Combined loading and error states
  const isLoading = isLoadingOhlcv || isLoadingForecasts || isLoadingAssetCoreDetails;
  const error = errorOhlcv || errorForecasts || errorAssetCoreDetails;

  useEffect(() => {
    // Optional: if you want to trigger a refetch if asset or timeframe changes
    // and the hooks don't automatically handle it through their own dependency arrays.
    // This might be redundant if the hooks are set up correctly.
    // refetchOhlcv();
    // refetchForecasts();
  }, [asset, requestTimeframe]); // Dependencies that might trigger re-fetch

  if (!asset) {
    return null;
  }

  const formatXAxis = (tickItem: number) => {
    return new Date(tickItem * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const combinedChartData = ohlcvCandles.map(ohlc => {
    // Find relevant forecast. Forecasts are an array, might have multiple signals for a given timestamp.
    // This logic might need to be more sophisticated based on how you want to display multiple forecasts.
    const relevantForecastsForTimestamp = forecastSignalsData.filter(f => f.ohlcv_data_timestamp === ohlc.time);
    
    let forecastPrice, bb_upper, bb_lower, bb_middle;
    // Example: pick the first available forecast of a certain type
    const priceForecast = relevantForecastsForTimestamp.find(f => f.details?.price !== undefined);
    if (priceForecast) forecastPrice = priceForecast.details.price;

    const bbForecast = relevantForecastsForTimestamp.find(f => f.details?.upper_band !== undefined && f.details?.lower_band !== undefined);
    if (bbForecast) {
      bb_upper = bbForecast.details.upper_band;
      bb_lower = bbForecast.details.lower_band;
      bb_middle = bbForecast.details.middle_band; // Assuming middle_band is also in details
    }

    return {
      time: ohlc.time,
      open: ohlc.open,
      high: ohlc.high,
      low: ohlc.low,
      close: ohlc.close,
      forecastPrice,
      bb_upper,
      bb_lower,
      bb_middle,
    };
  });

  const handleRetry = () => {
    if (errorOhlcv) refetchOhlcv();
    if (errorForecasts) refetchForecasts();
    if (errorAssetCoreDetails) refetchAssetCoreDetails();
  };

  return (
    <Card className="shadow-xl transition-all duration-300 ease-out opacity-0 animate-fadeIn mt-6 bg-slate-800/80 border-slate-700 text-gray-300 backdrop-blur-md">
      <CardHeader className="flex flex-row justify-between items-start pt-4 pb-3 px-5 bg-slate-700/30 rounded-t-lg">
        <div>
          <CardTitle className="flex items-center gap-2.5 text-lg font-semibold text-white">
            {isLoadingAssetCoreDetails && <div className="h-6 w-6 rounded-full bg-slate-600 animate-pulse"></div>}
            {!isLoadingAssetCoreDetails && assetCoreDetails?.logo_uri && (
              <img src={assetCoreDetails.logo_uri} alt={assetCoreDetails.name} className="h-6 w-6 rounded-full" />
            )}
            <Activity className="h-5 w-5 text-teal-400" />
            Asset Deep Dive: <span className="text-teal-300">{assetCoreDetails?.name || baseSymbol} ({assetCoreDetails?.symbol || asset.asset})</span>
          </CardTitle>
          <CardDescription className="text-slate-400 text-xs mt-1">
            OHLCV chart and forecast signals for timeframe: {requestTimeframe}. 
            {assetCoreDetails && ` Decimals: ${assetCoreDetails.decimals}`}
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
            {/* Display specific errors */}
            {errorOhlcv && <p className="text-sm">OHLCV: {String(errorOhlcv)}</p>}
            {errorForecasts && <p className="text-sm">Forecasts: {String(errorForecasts)}</p>}
            {errorAssetCoreDetails && <p className="text-sm">Core Details: {String(errorAssetCoreDetails)}</p>}
            <Button variant="outline" onClick={handleRetry} className="mt-4 border-red-400 text-red-300 hover:bg-red-800/50 hover:text-red-200">
              Retry All
            </Button>
          </div>
        )}
        {!isLoading && !error && (
          <>
            <div className="h-[400px] bg-slate-700/40 p-4 rounded-lg shadow-inner">
              <h4 className="font-semibold text-md mb-4 text-slate-100">Price Chart & Key Forecasts</h4>
              {combinedChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="calc(100% - 30px)">
                  <ComposedChart data={combinedChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
                    <XAxis dataKey="time" tickFormatter={formatXAxis} stroke="#A0AEC0" dy={10} tick={{ fontSize: 12 }} />
                    <YAxis yAxisId="left" stroke="#A0AEC0" domain={['auto', 'auto']} allowDataOverflow={true} tick={{ fontSize: 12 }} width={70} />
                    <Tooltip
                        contentStyle={{ backgroundColor: 'rgba(26, 32, 44, 0.95)', borderColor: '#4A5568', color: '#E2E8F0', borderRadius: '0.5rem' }}
                        itemStyle={{ color: '#CBD5E0' }}
                        cursor={{ fill: 'rgba(74, 85, 104, 0.3)' }}
                        labelFormatter={(label) => new Date(label * 1000).toLocaleString()}
                    />
                    <Legend wrapperStyle={{ color: '#E2E8F0', paddingTop: '10px' }} />
                    <Line yAxisId="left" type="monotone" dataKey="close" stroke="#4FD1C5" name="Close Price" dot={false} strokeWidth={2} />
                    {combinedChartData.some(d => d.bb_upper && d.bb_lower) && (
                        <>
                            <Line yAxisId="left" type="monotone" dataKey="bb_upper" stroke="#ED64A6" name="Upper Band" dot={false} strokeWidth={1.5} strokeDasharray="4 4" />
                            <Line yAxisId="left" type="monotone" dataKey="bb_lower" stroke="#ED64A6" name="Lower Band" dot={false} strokeWidth={1.5} strokeDasharray="4 4" />
                            {combinedChartData.some(d => d.bb_middle) && (
                               <Line yAxisId="left" type="monotone" dataKey="bb_middle" stroke="#A78BFA" name="Middle Band" dot={false} strokeWidth={1} strokeDasharray="3 3" />
                            )}
                        </>
                    )}
                     {combinedChartData.some(d => d.forecastPrice) && (
                         <Line yAxisId="left" type="monotone" dataKey="forecastPrice" name="Forecast Price" stroke="#F6E05E" strokeWidth={2} dot={{ r: 4, fill: '#F6E05E' }} strokeDasharray="8 4" />
                     )}
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-slate-500 italic text-center py-10">No OHLCV data available to display chart.</p>
              )}
            </div>

            <div className="mt-8">
              <h4 className="font-semibold text-md mb-4 text-slate-100">Active Forecast Signals Summary</h4>
              {forecastSignalsData.length > 0 ? (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {forecastSignalsData.map((signal, index) => (
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
                        {/* Render details based on common patterns, assuming details is an object */}
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