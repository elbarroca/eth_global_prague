"use client";

import React from 'react';
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
import { BarChart, Settings } from 'lucide-react';
import { PortfolioFormInputs, mvoObjectiveOptions, timeframeOptions, chainOptions } from '@/types/portfolio-api';

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

  return (
    <Card className="shadow-2xl transition-all duration-700 ease-out hover:shadow-3xl bg-gradient-to-br from-slate-800/90 via-slate-800/95 to-slate-900/90 border border-slate-600/50 backdrop-blur-sm text-gray-200 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] via-transparent to-transparent pointer-events-none" />
      <CardHeader className="relative">
        <CardTitle className="flex items-center gap-3 text-2xl font-bold text-white tracking-tight">
          <div className="p-2 rounded-xl bg-white/10 backdrop-blur-sm">
            <Settings className="h-6 w-6 text-white" />
          </div>
          Portfolio Optimization
        </CardTitle>
        <CardDescription className="text-slate-300 text-base mt-2">
          Configure your preferences to create the perfect portfolio strategy.
        </CardDescription>
      </CardHeader>
      <FormProvider {...formMethods}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-10 pt-6 relative">
            <FormField
              control={control}
              name="chains"
              render={() => (
                <FormItem className="space-y-4">
                  <div className="space-y-2">
                    <FormLabel className="text-lg font-semibold text-white flex items-center gap-2">
                      <span className="w-2 h-2 bg-white rounded-full"></span>
                      Blockchain Networks
                    </FormLabel>
                    <FormDescription className="text-slate-300 text-sm">
                      Select the blockchain networks to include in your portfolio optimization.
                    </FormDescription>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {chainOptions.map((chain) => (
                      <FormField
                        key={chain.id}
                        control={control}
                        name="chains"
                        render={({ field }) => (
                          <FormItem
                            className="flex flex-row items-center space-x-3 space-y-0 rounded-xl border border-slate-600/50 p-4 hover:bg-white/5 hover:border-white/20 transition-all duration-300 bg-slate-700/20 backdrop-blur-sm group cursor-pointer"
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
                                className="border-slate-400 data-[state=checked]:bg-white data-[state=checked]:border-white data-[state=checked]:text-slate-900 focus-visible:ring-white/50 transition-all duration-200"
                              />
                            </FormControl>
                            <FormLabel className="font-medium text-sm flex items-center gap-3 cursor-pointer text-white group-hover:text-white/90 transition-colors">
                              <span className="text-xl">{chain.icon}</span> 
                              <span>{chain.name}</span>
                            </FormLabel>
                          </FormItem>
                        )}
                      />
                    ))}
                  </div>
                  <FormMessage className="text-red-400" />
                </FormItem>
              )}
            />

            <div className="grid md:grid-cols-3 gap-8">
              <FormField
                control={control}
                name="mvoObjective"
                render={({ field }) => (
                  <FormItem className="space-y-3">
                    <FormLabel className="text-lg font-semibold text-white flex items-center gap-2">
                      <span className="w-2 h-2 bg-white rounded-full"></span>
                      Optimization Strategy
                    </FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger className="bg-slate-700/30 border-slate-600/50 hover:border-white/30 focus:ring-white/50 text-white h-12 rounded-xl backdrop-blur-sm transition-all duration-300">
                          <SelectValue placeholder="Choose your optimization strategy" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent className="bg-slate-800/95 border-slate-600/50 text-white backdrop-blur-sm">
                        {mvoObjectiveOptions.map(option => (
                          <SelectItem key={option.id} value={option.id} className="focus:bg-white/10 text-white hover:bg-white/5 transition-colors">
                            {option.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription className="text-slate-300 text-sm">
                      Choose your preferred optimization approach for maximum returns.
                    </FormDescription>
                    <FormMessage className="text-red-400" />
                  </FormItem>
                )}
              />
              <FormField
                control={control}
                name="timeframe"
                render={({ field }) => (
                  <FormItem className="space-y-3">
                    <FormLabel className="text-lg font-semibold text-white flex items-center gap-2">
                      <span className="w-2 h-2 bg-white rounded-full"></span>
                      Analysis Period
                    </FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger className="bg-slate-700/30 border-slate-600/50 hover:border-white/30 focus:ring-white/50 text-white h-12 rounded-xl backdrop-blur-sm transition-all duration-300">
                          <SelectValue placeholder="Select analysis timeframe" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent className="bg-slate-800/95 border-slate-600/50 text-white backdrop-blur-sm">
                        {timeframeOptions.map(option => (
                          <SelectItem key={option.id} value={option.id} className="focus:bg-white/10 text-white hover:bg-white/5 transition-colors">
                            {option.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription className="text-slate-300 text-sm">
                      Historical data period for analysis (5 minutes to 1 month).
                    </FormDescription>
                    <FormMessage className="text-red-400" />
                  </FormItem>
                )}
              />
              <FormField
                control={control}
                name="maxTokensPerChain"
                render={({ field }) => (
                  <FormItem className="space-y-3">
                    <FormLabel className="text-lg font-semibold text-white flex items-center gap-2">
                      <span className="w-2 h-2 bg-white rounded-full"></span>
                      Assets Per Chain
                    </FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        placeholder="50"
                        {...field}
                        onChange={e => {
                            const val = parseInt(e.target.value, 10);
                            field.onChange(isNaN(val) ? undefined : val);
                        }}
                        className="bg-slate-700/30 border-slate-600/50 placeholder:text-slate-400 focus:border-white/50 focus:ring-white/50 text-white h-12 rounded-xl backdrop-blur-sm transition-all duration-300"
                      />
                    </FormControl>
                    <FormDescription className="text-slate-300 text-sm">
                      Maximum assets to analyze per blockchain (10-500).
                      <br />
                      <span className="text-xs text-amber-400/80 font-medium">⚡ Higher values increase processing time</span>
                    </FormDescription>
                    <FormMessage className="text-red-400" />
                  </FormItem>
                )}
              />
            </div>
          </CardContent>
          <CardFooter className="pt-8 pb-8 relative">
            <div className="w-full flex justify-center">
              <Button 
                type="submit" 
                disabled={isLoading} 
                className="bg-gradient-to-r from-white to-gray-100 hover:from-gray-100 hover:to-white text-slate-900 font-bold text-lg py-4 px-12 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-500 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none group relative overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                {isLoading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-6 w-6 text-slate-900" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span className="relative z-10">Optimizing Portfolio...</span>
                  </>
                ) : (
                  <>
                    <span className="relative z-10 flex items-center">
                      Optimize Portfolio
                      <BarChart className="ml-3 h-6 w-6 transition-transform duration-300 group-hover:translate-x-1 group-hover:scale-110" />
                    </span>
                  </>
                )}
              </Button>
            </div>
          </CardFooter>
        </form>
      </FormProvider>
    </Card>
  );
}; 