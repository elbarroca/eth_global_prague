"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form" // Assuming you have a Form component like in shadcn examples
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { usePortfolioStore, type ApiCallParams } from "@/stores/portfolio-store"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { SlidersHorizontal, Info } from 'lucide-react'
import { Switch } from "@radix-ui/react-switch"

// Zod schema for form validation based on ApiCallParams
const formSchema = z.object({
  chain_ids: z.string().min(1, "At least one chain ID is required"),
  timeframe: z.enum(['day', 'week', 'month', 'quarter', 'year']),
  max_tokens_per_chain: z.coerce.number().min(2).max(500),
  mvo_objective: z.enum(['maximize_sharpe', 'minimize_volatility', 'target_return']),
  risk_free_rate: z.coerce.number().min(0).max(1),
  annualization_factor_override: z.coerce.number().min(1).optional().nullable(),
  target_return_input: z.coerce.number().min(0).max(5).optional().nullable(), // e.g. 0.8 for 80%
  use_ranking_for_expected_returns: z.boolean(),
  score_to_return_scale: z.coerce.number().min(0),
  ohlcv_history_points_for_cov: z.coerce.number().min(20).max(500),
});

export function ApiParametersForm() {
  const {
    apiParameters,
    setApiParameters,
    fetchAndSetPortfolioApiData,
    getActivePortfolio,
    isLoadingApiData,
  } = usePortfolioStore();
  
  const activePortfolio = getActivePortfolio();

  const form = useForm<ApiCallParams>({
    resolver: zodResolver(formSchema),
    defaultValues: apiParameters,
  });

  const onSubmit = (values: ApiCallParams) => {
    setApiParameters(values);
    if (activePortfolio) {
      fetchAndSetPortfolioApiData(activePortfolio.id, values);
    }
    console.log("Form submitted with values:", values);
  };
  
  // Watch mvo_objective to conditionally show target_return_input
  const mvoObjective = form.watch("mvo_objective");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <SlidersHorizontal className="h-5 w-5" />
          Optimization Parameters
        </CardTitle>
        <CardDescription>
          Configure the parameters for portfolio optimization and data fetching.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              <FormField
                control={form.control}
                name="chain_ids"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Chain IDs</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., 1,42161,10" {...field} />
                    </FormControl>
                    <FormDescription>
                      Comma-separated string of chain IDs.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="timeframe"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Timeframe</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select timeframe" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="day">Day</SelectItem>
                        <SelectItem value="week">Week</SelectItem>
                        <SelectItem value="month">Month</SelectItem>
                        <SelectItem value="quarter">Quarter</SelectItem>
                        <SelectItem value="year">Year</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>Timeframe for OHLCV data.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              <FormField
                control={form.control}
                name="max_tokens_per_chain"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Max Tokens per Chain</FormLabel>
                    <FormControl>
                      <Input type="number" placeholder="260" {...field} onChange={event => field.onChange(+event.target.value)} />
                    </FormControl>
                    <FormDescription>Max tokens to screen (2-500).</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="mvo_objective"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>MVO Objective</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select MVO objective" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="maximize_sharpe">Maximize Sharpe Ratio</SelectItem>
                        <SelectItem value="minimize_volatility">Minimize Volatility</SelectItem>
                        <SelectItem value="target_return">Target Return</SelectItem>
                      </SelectContent>
                    </Select>
                     <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            
            {mvoObjective === 'target_return' && (
              <FormField
                control={form.control}
                name="target_return_input"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Target Annualized Return</FormLabel>
                    <FormControl>
                      <Input type="number" placeholder="e.g., 0.8 for 80%" {...field} onChange={event => field.onChange(event.target.value === '' ? null : +event.target.value)} value={field.value ?? ''}/>
                    </FormControl>
                    <FormDescription>Required if MVO Objective is Target Return.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <div className="grid md:grid-cols-2 gap-6">
              <FormField
                control={form.control}
                name="risk_free_rate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Risk-Free Rate</FormLabel>
                    <FormControl>
                      <Input type="number" placeholder="0.02" {...field} onChange={event => field.onChange(+event.target.value)} />
                    </FormControl>
                    <FormDescription>Annual risk-free rate (e.g., 0.02 for 2%).</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="score_to_return_scale"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Score to Return Scale</FormLabel>
                    <FormControl>
                      <Input type="number" placeholder="0.2" {...field} onChange={event => field.onChange(+event.target.value)} />
                    </FormControl>
                    <FormDescription>Factor to convert ranking score to annual return.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            
            <div className="grid md:grid-cols-2 gap-6">
                <FormField
                  control={form.control}
                  name="ohlcv_history_points_for_cov"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>OHLCV History Points</FormLabel>
                      <FormControl>
                        <Input type="number" placeholder="100" {...field} onChange={event => field.onChange(+event.target.value)} />
                      </FormControl>
                      <FormDescription>Data points for covariance (20-500).</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                    control={form.control}
                    name="annualization_factor_override"
                    render={({ field }) => (
                    <FormItem>
                        <FormLabel>Annualization Factor Override</FormLabel>
                        <FormControl>
                        <Input type="number" placeholder="e.g., 365" {...field} onChange={event => field.onChange(event.target.value === '' ? null : +event.target.value)} value={field.value ?? ''}/>
                        </FormControl>
                        <FormDescription>Optional. E.g., 365 for daily data.</FormDescription>
                        <FormMessage />
                    </FormItem>
                    )}
                />
            </div>

            <FormField
              control={form.control}
              name="use_ranking_for_expected_returns"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">Use Ranking for Expected Returns</FormLabel>
                    <FormDescription>
                      Utilize ranking scores as expected returns instead of fetching from signals.
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                </FormItem>
              )}
            />

            <div className="flex justify-end pt-4">
              <Button type="submit" disabled={isLoadingApiData || !activePortfolio}>
                {isLoadingApiData ? "Optimizing..." : "Run Optimization"}
              </Button>
            </div>
            {!activePortfolio && <p className="text-sm text-destructive text-right">No active portfolio selected. Create or select one first.</p>}
          </form>
        </Form>
      </CardContent>
    </Card>
  )
} 