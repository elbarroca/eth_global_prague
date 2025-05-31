"use client";

import React, { useState } from 'react';
import { useFormContext, Controller, FormProvider, UseFormReturn } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Settings, Terminal, Eye, EyeOff } from 'lucide-react';
import { PortfolioFormInputs, mvoObjectiveOptions, timeframeOptions, chainOptions } from '@/types/portfolio-api';
import { LogStreamViewer } from './LogStreamViewer';

interface PortfolioOptimizationFormProps {
  onSubmit: (data: PortfolioFormInputs) => void;
  isLoading: boolean;
  formMethods: UseFormReturn<PortfolioFormInputs, any, PortfolioFormInputs>;
}

export const PortfolioOptimizationForm: React.FC<PortfolioOptimizationFormProps> = ({
  onSubmit,
  isLoading,
  formMethods,
}) => {
  const { handleSubmit, control, watch } = formMethods;
  const mvoObjective = watch("mvoObjective");
  
  // State for log viewer
  const [showLogs, setShowLogs] = useState(false);
  const [logsActive, setLogsActive] = useState(false);

  // Enhanced submit handler to activate logs
  const handleFormSubmit = (data: PortfolioFormInputs) => {
    setLogsActive(true);
    setShowLogs(true);
    onSubmit(data);
  };

  // Toggle log viewer visibility
  const toggleLogViewer = () => {
    setShowLogs(!showLogs);
    if (!showLogs) {
      setLogsActive(true); // Ensure logs are active if viewer is opened manually
    }
  };

  return (
    <div className="space-y-8"> {/* Increased spacing */}
      <Card className="shadow-2xl transition-all duration-700 ease-out hover:shadow-3xl bg-gradient-to-br from-slate-800/95 via-slate-850/95 to-slate-900/95 border border-slate-700/80 backdrop-blur-md text-gray-200 overflow-hidden rounded-xl">
        <div className="absolute inset-0 bg-gradient-to-tr from-teal-500/5 via-transparent to-transparent pointer-events-none opacity-50" />
        <CardHeader className="relative border-b border-slate-700/70 px-7 py-6">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-3.5 text-2xl font-bold text-white tracking-tight">
                <div className="p-2.5 rounded-lg bg-gradient-to-br from-teal-500/20 to-blue-500/20 backdrop-blur-sm shadow-md">
                  <Settings className="h-6 w-6 text-teal-300" />
                </div>
                <span>Portfolio Optimization Setup</span>
              </CardTitle>
              <CardDescription className="text-slate-400 text-sm mt-2.5 ml-12">
                Fine-tune your parameters to discover the optimal asset allocation.
              </CardDescription>
            </div>
            <Button
              type="button"
              variant="outline" // Changed variant for better contrast
              size="sm"
              onClick={toggleLogViewer}
              className="text-slate-300 hover:text-teal-300 border-slate-600 hover:border-teal-500/70 bg-slate-700/40 hover:bg-slate-700/70 transition-all duration-300 rounded-lg py-2 px-4 group"
              title={showLogs ? "Hide Real-time Logs" : "Show Real-time Logs"}
            >
              {showLogs ? (
                <>
                  <EyeOff className="h-5 w-5 mr-2 text-slate-400 group-hover:text-teal-400 transition-colors" />
                  Hide Logs
                </>
              ) : (
                <>
                  <Terminal className="h-5 w-5 mr-2 text-slate-400 group-hover:text-teal-400 transition-colors" />
                  Show Logs
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <FormProvider {...formMethods}>
          <form onSubmit={handleSubmit(handleFormSubmit)}>
            <CardContent className="space-y-12 p-7 relative"> {/* Increased padding and spacing */}
              
              <FormField
                control={control}
                name="chains"
                render={() => (
                  <FormItem className="space-y-4">
                    <div className="mb-1">
                      <FormLabel className="text-base font-semibold text-slate-100 flex items-center gap-2.5">
                        <span className="w-2 h-4 bg-teal-400 rounded-sm block"></span>
                        Blockchain Networks
                      </FormLabel>
                      <FormDescription className="text-slate-400 text-sm mt-1 ml-[18px]">
                        Select networks to include in your portfolio analysis.
                      </FormDescription>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4"> {/* Responsive columns */}
                      {chainOptions.map((chain) => (
                        <FormField
                          key={chain.id}
                          control={control}
                          name="chains"
                          render={({ field }) => (
                            <FormItem
                              className="flex flex-row items-center space-x-3.5 space-y-0 rounded-lg border border-slate-700/70 p-4 hover:bg-slate-700/50 hover:border-slate-600 transition-all duration-200 bg-slate-700/30 backdrop-blur-sm group cursor-pointer shadow-sm hover:shadow-md"
                            >
                              <FormControl>
                                <Checkbox
                                  checked={field.value?.includes(chain.id)}
                                  onCheckedChange={(checked) => {
                                    const newValue = field.value ? [...field.value] : [];
                                    if (checked) {
                                      newValue.push(chain.id);
                                    } else {
                                      const index = newValue.indexOf(chain.id);
                                      if (index > -1) {
                                        newValue.splice(index, 1);
                                      }
                                    }
                                    field.onChange(newValue);
                                  }}
                                  className="border-slate-500 data-[state=checked]:bg-teal-500 data-[state=checked]:border-teal-400 data-[state=checked]:text-white focus-visible:ring-teal-500/80 transition-all duration-200 w-5 h-5 rounded"
                                />
                              </FormControl>
                              <FormLabel className="font-medium text-sm flex items-center gap-2.5 cursor-pointer text-slate-200 group-hover:text-white transition-colors">
                                <span className="text-2xl opacity-90 group-hover:opacity-100">{chain.icon}</span> 
                                <span className="pt-0.5">{chain.name}</span>
                              </FormLabel>
                            </FormItem>
                          )}
                        />
                      ))}
                    </div>
                    <FormMessage className="text-red-400 pt-1" />
                  </FormItem>
                )}  
              />

              <div className="grid md:grid-cols-3 gap-x-8 gap-y-10"> {/* Consistent gap */}
                <FormField
                  control={control}
                  name="mvoObjective"
                  render={({ field }) => (
                    <FormItem className="space-y-3">
                      <FormLabel className="text-base font-semibold text-slate-100 flex items-center gap-2.5">
                        <span className="w-2 h-4 bg-teal-400 rounded-sm block"></span>
                        Optimization Strategy
                      </FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger className="bg-slate-700/50 border-slate-600/70 hover:border-slate-500 focus:ring-teal-500/80 text-slate-100 h-12 rounded-lg backdrop-blur-sm transition-all duration-200 text-sm px-4">
                            <SelectValue placeholder="Choose optimization strategy" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent className="bg-slate-800/95 border-slate-700 text-slate-100 backdrop-blur-md shadow-2xl rounded-lg">
                          {mvoObjectiveOptions.map(option => (
                            <SelectItem key={option.id} value={option.id} className="focus:bg-teal-500/20 text-slate-100 hover:bg-slate-700/50 transition-colors py-2.5 px-3 text-sm">
                              {option.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormDescription className="text-slate-400 text-xs pt-1 ml-1">
                        Select your preferred method for portfolio construction.
                      </FormDescription>
                      <FormMessage className="text-red-400 text-xs" />
                    </FormItem>
                  )}
                />
                <FormField
                  control={control}
                  name="timeframe"
                  render={({ field }) => (
                    <FormItem className="space-y-3">
                      <FormLabel className="text-base font-semibold text-slate-100 flex items-center gap-2.5">
                         <span className="w-2 h-4 bg-teal-400 rounded-sm block"></span>
                        Analysis Period
                      </FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger className="bg-slate-700/50 border-slate-600/70 hover:border-slate-500 focus:ring-teal-500/80 text-slate-100 h-12 rounded-lg backdrop-blur-sm transition-all duration-200 text-sm px-4">
                            <SelectValue placeholder="Select analysis timeframe" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent className="bg-slate-800/95 border-slate-700 text-slate-100 backdrop-blur-md shadow-2xl rounded-lg">
                          {timeframeOptions.map(option => (
                            <SelectItem key={option.id} value={option.id} className="focus:bg-teal-500/20 text-slate-100 hover:bg-slate-700/50 transition-colors py-2.5 px-3 text-sm">
                              {option.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormDescription className="text-slate-400 text-xs pt-1 ml-1">
                        Set historical data range (5 min to 1 month).
                      </FormDescription>
                      <FormMessage className="text-red-400 text-xs" />
                    </FormItem>
                  )}
                />
                <FormField
                  control={control}
                  name="maxTokensPerChain"
                  render={({ field }) => (
                    <FormItem className="space-y-3">
                      <FormLabel className="text-base font-semibold text-slate-100 flex items-center gap-2.5">
                        <span className="w-2 h-4 bg-teal-400 rounded-sm block"></span>
                        Max Assets Per Chain
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="Default: 50"
                          {...field}
                          onChange={e => {
                              const val = parseInt(e.target.value, 10);
                              field.onChange(isNaN(val) ? undefined : Math.max(10, Math.min(val, 500))); // Enforce range
                          }}
                          className="bg-slate-700/50 border-slate-600/70 placeholder:text-slate-500 focus:border-teal-500/80 focus:ring-teal-500/80 text-slate-100 h-12 rounded-lg backdrop-blur-sm transition-all duration-200 text-sm px-4"
                        />
                      </FormControl>
                      <FormDescription className="text-slate-400 text-xs pt-1 ml-1">
                        Range: 10-500.
                        <br />
                        <span className="text-xs text-amber-400/90 font-medium">⚡ Higher values significantly increase processing time.</span>
                      </FormDescription>
                      <FormMessage className="text-red-400 text-xs" />
                    </FormItem>
                  )}
                />
              </div>
            </CardContent>
            <CardFooter className="px-7 py-8 relative border-t border-slate-700/70">
              <div className="w-full flex justify-center">
                <Button 
                  type="submit" 
                  disabled={isLoading} 
                  className="bg-gradient-to-r from-teal-500 via-cyan-500 to-sky-500 hover:from-teal-400 hover:via-cyan-400 hover:to-sky-400 text-white font-semibold text-base py-3.5 px-10 rounded-lg shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none group relative overflow-hidden focus:ring-4 focus:ring-teal-500/50 focus:outline-none"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  {isLoading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2.5 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span className="relative z-10">Optimizing Portfolio...</span>
                    </>
                  ) : (
                    <>
                      <span className="relative z-10 flex items-center">
                        Optimize My Portfolio
                        <BarChart className="ml-2.5 h-5 w-5 transition-transform duration-300 group-hover:translate-x-0.5" />
                      </span>
                    </>
                  )}
                </Button>
              </div>
            </CardFooter>
          </form>
        </FormProvider>
      </Card>

      {/* Real-time Log Stream Viewer */}
      {showLogs && (
        <div className="transition-all duration-500 ease-out opacity-100 transform translate-y-0">
          <LogStreamViewer 
            isActive={logsActive}
            onClose={() => {
              setShowLogs(false);
              // Optionally deactivate logs if viewer is explicitly closed and form is not submitting
              // if (!isLoading) setLogsActive(false); 
            }}
          />
        </div>
      )}
    </div>
  );
}; 