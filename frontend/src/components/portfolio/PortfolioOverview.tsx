"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { usePortfolioStore } from '@/stores/portfolio-store'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { TrendingUp, TrendingDown, DollarSign, Coins } from 'lucide-react'
import React from 'react'
import EthereumIcon from '@/components/icons/EthereumIcon'
import { LiquidatePortfolioButton } from '../optimizer/LiquidatePortfolioButton'

// Mock data for charts
const performanceData = [
  { date: 'Jan', value: 4000 },
  { date: 'Feb', value: 4500 },
  { date: 'Mar', value: 4200 },
  { date: 'Apr', value: 5100 },
  { date: 'May', value: 5800 },
  { date: 'Jun', value: 6200 },
]

const assetDistributionData = [
  { name: 'ETH', value: 45, color: '#627EEA' },
  { name: 'BTC', value: 30, color: '#F7931A' },
  { name: 'USDC', value: 15, color: '#2775CA' },
  { name: 'Others', value: 10, color: '#9CA3AF' },
]

// Define a mapping for chain logos
const chainLogos: { [key: string]: React.ReactNode } = {
  '1': <EthereumIcon />,
  '137': '🟣',
  '42161': '🔵',
  '10': '🔴',
  '43114': '🔺',
  '56': '🟡',
  // Add other chain IDs from backend/configs.py with their logos/emojis
}

const chainNames: { [key: string]: string } = {
    '1': "Ethereum",
    '137': "Polygon",
    '42161': "Arbitrum",
    '10': "Optimism",
    '43114': "Avalanche",
    '56': "BSC",
    // From backend/configs.py
    '324': "zkSync Era",
    '250': "Fantom",
    '100': "Gnosis",
    '8453': "Base",
    '59144': "Linea",
    '146': "Sonic",
    '130': "Unichain",
}

export function PortfolioOverview() {
  const { getActivePortfolio } = usePortfolioStore()
  const portfolio = getActivePortfolio()

  if (!portfolio) {
    return (
      <Card className="w-full bg-slate-800 border-slate-700 text-gray-300">
        <CardContent className="flex flex-col items-center justify-center h-64">
          <p className="text-slate-500">No active portfolio selected. Please create or select one.</p>
        </CardContent>
      </Card>
    )
  }

  // Prepare data for Chain Distribution Chart based on portfolio
  const portfolioChainDistribution = portfolio.chains.map(chainId => ({
    name: chainNames[chainId] || `Chain ${chainId}`,
    value: portfolio.assets.filter(asset => asset.chain === chainId).length,
    logo: chainLogos[chainId] || '❓'
  })).filter(c => c.value > 0)

  // Example: Augmenting stats with more dynamic data if available
  const totalValue = portfolio.totalValue
  const numberOfAssets = portfolio.assets.length
  const numberOfChains = new Set(portfolio.assets.map(a => a.chain)).size

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Total Value</CardTitle>
            <DollarSign className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-400">${totalValue.toLocaleString()}</div>
            <p className="text-xs text-slate-500">
              {/* Placeholder for dynamic change */}
              <span className="text-green-500 flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                +0.00% from last month
              </span>
            </p>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Assets</CardTitle>
            <Coins className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-sky-400">{numberOfAssets}</div>
            <p className="text-xs text-slate-500">Across {numberOfChains} chain(s)</p>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">24h Change</CardTitle>
            <TrendingUp className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            {/* Placeholder for dynamic change */}
            <div className="text-2xl font-bold text-green-500">+$0.00</div>
            <p className="text-xs text-slate-500">+0.00%</p>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Best Performer (24h)</CardTitle>
            <TrendingUp className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
             {/* Placeholder */}
            <div className="text-2xl font-bold text-yellow-400">N/A</div>
            <p className="text-xs text-slate-500">N/A</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList className="bg-slate-700 text-slate-300">
          <TabsTrigger value="performance" className="data-[state=active]:bg-slate-600 data-[state=active]:text-white">Performance</TabsTrigger>
          <TabsTrigger value="allocation" className="data-[state=active]:bg-slate-600 data-[state=active]:text-white">Allocation</TabsTrigger>
          <TabsTrigger value="chains" className="data-[state=active]:bg-slate-600 data-[state=active]:text-white">Chains</TabsTrigger>
        </TabsList>

        <TabsContent value="performance" className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-200">Portfolio Performance</CardTitle>
              <CardDescription className="text-slate-400">Your portfolio value over time (mock data)</CardDescription>
            </CardHeader>
            <CardContent className="pt-2">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                  <XAxis dataKey="date" stroke="#94a3b8" className="text-xs" />
                  <YAxis stroke="#94a3b8" className="text-xs" />
                  <Tooltip contentStyle={{ backgroundColor: 'rgba(30, 41, 59, 0.9)', borderColor: '#475569', color: '#e2e8f0' }} />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#8b5cf6" // purple-500
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="allocation" className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-200">Asset Allocation</CardTitle>
              <CardDescription className="text-slate-400">Distribution of your assets (mock data)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={assetDistributionData} // Use the renamed mock data
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry) => `${entry.name} ${entry.value}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {assetDistributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: 'rgba(30, 41, 59, 0.9)', borderColor: '#475569', color: '#e2e8f0' }} />
                  <Legend wrapperStyle={{ color: '#e2e8f0' }} />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="chains" className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-200">Chain Distribution</CardTitle>
              <CardDescription className="text-slate-400">Asset count across different blockchains</CardDescription>
            </CardHeader>
            <CardContent>
            {portfolioChainDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={portfolioChainDistribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                  <XAxis dataKey="name" stroke="#94a3b8" className="text-xs" />
                  <YAxis stroke="#94a3b8" className="text-xs" allowDecimals={false} />
                  <Tooltip contentStyle={{ backgroundColor: 'rgba(30, 41, 59, 0.9)', borderColor: '#475569', color: '#e2e8f0' }} />
                  <Legend wrapperStyle={{ color: '#e2e8f0' }} />
                  <Bar dataKey="value" name="Assets on Chain" fill="#2dd4bf" /> {/* teal-400 for bars */}
                </BarChart>
              </ResponsiveContainer>
              ) : (
                <p className="text-slate-500 italic text-center py-10">No assets in the portfolio to display chain distribution.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Liquidate Portfolio Button - Added Section */}
      <div className="mt-8 pt-6 border-t border-slate-700/60">
        <LiquidatePortfolioButton 
          portfolioWeights={Object.fromEntries(
            portfolio.assets.map(asset => [asset.id, 1 / portfolio.assets.length]) // Mock percentage
          )} 
          selectedChains={Array.from(new Set(portfolio.assets.map(asset => asset.chain)))}
        />
      </div>

    </div>
  )
} 