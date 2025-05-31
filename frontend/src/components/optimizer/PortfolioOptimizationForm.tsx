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
  formMethods: UseFormReturn<PortfolioFormInputs>; // Allow passing full form methods
}

export const PortfolioOptimizationForm: React.FC<PortfolioOptimizationFormProps> = ({
  onSubmit,
  isLoading,
  formMethods,
}) => {
  const { handleSubmit, control } = formMethods;

  return (
    <Card className="shadow-lg transition-all duration-500 ease-out hover:shadow-xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl font-semibold">
          <Settings className="h-6 w-6 text-blue-600" />
          Portfolio Optimization Parameters
        </CardTitle>
        <CardDescription>
          Configure your preferences to tailor the portfolio optimization.
        </CardDescription>
      </CardHeader>
      <FormProvider {...formMethods}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-6 pt-4">
            <FormField
              control={control}
              name="chains"
              render={() => (
                <FormItem>
                  <div className="mb-3">
                    <FormLabel className="text-md font-medium">Chains</FormLabel>
                    <FormDescription>
                      Select blockchains to include in the optimization.
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
                            className="flex flex-row items-center space-x-2 space-y-0 rounded-md border p-3 hover:bg-accent hover:text-accent-foreground transition-colors"
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
                              />
                            </FormControl>
                            <FormLabel className="font-normal text-sm flex items-center gap-1.5 cursor-pointer">
                              <span className="text-lg">{chain.icon}</span> {chain.name}
                            </FormLabel>
                          </FormItem>
                        )}
                      />
                    ))}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid md:grid-cols-2 gap-6">
              <FormField
                control={control}
                name="mvoObjective"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-md font-medium">MVO Objective</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select MVO objective" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {mvoObjectiveOptions.map(option => (
                          <SelectItem key={option.id} value={option.id}>
                            {option.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Mean-Variance Optimization strategy.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={control}
                name="timeframe"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-md font-medium">Timeframe</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select timeframe" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {timeframeOptions.map(option => (
                          <SelectItem key={option.id} value={option.id}>
                            {option.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Historical data analysis period.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              <FormField
                control={control}
                name="riskFreeRate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-md font-medium">Risk-Free Rate (%)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        placeholder="e.g., 2 for 2%"
                        value={field.value !== undefined ? field.value * 100 : ''}
                        onChange={e => {
                            const val = parseFloat(e.target.value);
                            field.onChange(isNaN(val) ? undefined : val / 100);
                        }}
                        step="0.01"
                      />
                    </FormControl>
                    <FormDescription>
                      Annual rate for calculations (e.g., Sharpe Ratio). Default: 2%.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={control}
                name="targetReturn"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-md font-medium">Target Return (Optional, %)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        placeholder="e.g., 10 for 10%"
                        value={field.value !== undefined ? field.value * 100 : ''}
                        onChange={e => {
                            const val = parseFloat(e.target.value);
                            field.onChange(isNaN(val) ? undefined : val / 100);
                        }}
                        step="0.1"
                      />
                    </FormControl>
                    <FormDescription>
                      Desired annual return for specific MVO objectives.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          </CardContent>
          <CardFooter className="pt-2">
            <Button type="submit" disabled={isLoading} className="w-full sm:w-auto text-base py-3 px-6 group">
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Optimizing...
                </>
              ) : (
                <>
                  Optimize Portfolio
                  <BarChart className="ml-2 h-5 w-5 transition-transform duration-300 group-hover:translate-x-1" />
                </>
              )}
            </Button>
          </CardFooter>
        </form>
      </FormProvider>
    </Card>
  );
}; 