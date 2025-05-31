import type { NextPage } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowRight, Brain, Database, GitFork, Zap, Shield, Globe, Clock, Network, Sparkles, TrendingUp, Target } from 'lucide-react';
import { cn } from 'lib/utils';

// Enhanced chain logos with better styling using proper Tailwind
const ChainLogo = ({ name, symbol }: { name: string; symbol: string }) => (
  <div className="flex flex-col items-center group cursor-pointer">
    <div className={cn(
      "w-16 h-16 rounded-full flex items-center justify-center text-lg font-bold",
      "bg-gradient-to-br from-emerald-800 to-emerald-900 text-emerald-100",
      "border border-emerald-700/50 shadow-lg",
      "transition-all duration-500 transform",
      "group-hover:from-emerald-400 group-hover:to-emerald-500 group-hover:text-slate-900",
      "group-hover:scale-110 group-hover:rotate-12 group-hover:shadow-emerald-400/50",
      "group-hover:border-emerald-300"
    )}>
      {symbol}
    </div>
    <p className={cn(
      "mt-3 font-medium text-slate-400 transition-colors duration-300",
      "group-hover:text-emerald-400"
    )}>
      {name}
    </p>
  </div>
);

const Home: NextPage = () => {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans relative overflow-hidden antialiased">
      {/* Animated background elements */}
      <div className="fixed inset-0 z-0">
        <div className="absolute top-20 left-10 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-emerald-400/5 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-emerald-600/5 rounded-full blur-3xl animate-pulse delay-500"></div>
      </div>

      <Head>
        <title>QuantumLeap - Unlock Cross-Chain Alpha. Intelligently.</title>
        <meta
          content="QuantumLeap leverages real-time multi-chain data, advanced forecasting, and Modern Portfolio Theory to identify and suggest high-potential DeFi portfolios across 8 EVM chains."
          name="description"
        />
        <link href="/favicon.ico" rel="icon" />
      </Head>

      {/* Navigation */}
      <nav className={cn(
        "px-6 py-4 sticky top-0 z-50 backdrop-blur-lg bg-slate-800/90",
        "border-b border-slate-700/50 shadow-lg"
      )}>
        <div className="max-w-7xl mx-auto flex justify-between items-center relative z-10">
          <div className="text-3xl font-bold text-emerald-400 flex items-center gap-2">
            <Network className="w-8 h-8 animate-pulse" />
            QuantumLeap
          </div>
          <Link href="/dashboard">
            <Button 
              variant="outline" 
              className={cn(
                "border-emerald-400/50 text-slate-100 bg-transparent",
                "hover:bg-emerald-500 hover:text-slate-900 hover:border-emerald-400",
                "transition-all duration-300 hover:scale-105",
                "hover:shadow-lg hover:shadow-emerald-400/25"
              )}
            >
              Launch Dashboard
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="px-6 relative z-10">
        <section className="py-20 md:py-32 bg-slate-800/30 relative">
          <div className="max-w-6xl mx-auto text-center">
            <div className="mb-8 flex justify-center">
              <div className={cn(
                "inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium",
                "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400",
                "animate-pulse backdrop-blur-sm"
              )}>
                <Sparkles className="w-4 h-4" />
                Built in 36 hours for ETHGlobal Prague
                <Sparkles className="w-4 h-4" />
              </div>
            </div>
            
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-slate-100 mb-8 leading-tight">
              Unlock <span className="text-emerald-400 animate-pulse">Cross-Chain</span> Alpha.{' '}
              <span className="bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
                Intelligently.
              </span>
            </h1>
            
            <p className="text-xl md:text-2xl text-slate-300 mb-12 leading-relaxed max-w-4xl mx-auto">
              QuantumLeap leverages <span className="text-emerald-400 font-semibold">real-time multi-chain data</span>, 
              <span className="text-emerald-400 font-semibold"> advanced AI forecasting</span>, and 
              <span className="text-emerald-400 font-semibold"> Modern Portfolio Theory</span> to identify and suggest 
              high-potential DeFi portfolios across <span className="text-emerald-400 font-bold">8 EVM chains</span>.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
              <Link href="/dashboard">
                <Button 
                  size="lg" 
                  className={cn(
                    "text-lg px-10 py-6 h-auto font-bold",
                    "bg-emerald-500 hover:bg-emerald-400 text-slate-900",
                    "shadow-xl hover:shadow-2xl hover:shadow-emerald-400/25",
                    "transition-all duration-300 hover:scale-105 transform",
                    "border border-emerald-400/50"
                  )}
                >
                  <TrendingUp className="mr-2 h-5 w-5" />
                  Discover Alpha Portfolios
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
            </div>
            
            <div className="flex justify-center items-center gap-x-4 flex-wrap">
              <span className="text-slate-400 text-sm mr-2 mb-2 sm:mb-0 font-medium">Powered by 8 EVM Chains:</span>
              {['ETH', 'BNB', 'ARB', 'POLY', 'OPT', 'AVAX', 'FTM', 'BASE'].map((chain, index) => (
                <div 
                  key={chain} 
                  className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center text-xs m-1 cursor-pointer",
                    "bg-gradient-to-br from-emerald-700 to-emerald-800 text-emerald-100",
                    "border border-emerald-600/50 shadow-md",
                    "hover:from-emerald-400 hover:to-emerald-500 hover:text-slate-900",
                    "hover:border-emerald-300 hover:shadow-emerald-400/50",
                    "transition-all duration-300 hover:scale-110"
                  )}
                  title={chain}
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  {chain.substring(0,3)}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section className="py-16 md:py-24 bg-slate-900">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-3xl md:text-4xl font-bold text-center mb-4 text-slate-100">
              From Raw Data to <span className="text-emerald-400">Actionable Alpha</span>
            </h2>
            <p className="text-center text-slate-400 mb-16 text-lg max-w-2xl mx-auto">
              Our intelligent pipeline transforms multi-chain chaos into profitable opportunities
            </p>
            
            <div className="grid md:grid-cols-4 gap-8">
              {[
                { 
                  icon: <Database className="w-12 h-12 text-emerald-400 mb-4 mx-auto" />, 
                  title: 'Multi-Chain Data Ingestion', 
                  description: 'Real-time aggregation from 8 leading EVM ecosystems with sub-second latency.',
                  step: '01'
                },
                { 
                  icon: <Brain className="w-12 h-12 text-emerald-400 mb-4 mx-auto" />, 
                  title: 'AI-Powered Forecasting', 
                  description: 'Advanced ML models predict asset performance using quantitative & technical analysis.',
                  step: '02'
                },
                { 
                  icon: <Target className="w-12 h-12 text-emerald-400 mb-4 mx-auto" />, 
                  title: 'Portfolio Optimization', 
                  description: 'Nobel Prize-winning MVO algorithms construct risk-adjusted portfolios for maximum alpha.',
                  step: '03'
                },
                { 
                  icon: <Zap className="w-12 h-12 text-emerald-400 mb-4 mx-auto" />, 
                  title: 'Instant Execution', 
                  description: 'Get actionable portfolio suggestions with future 1inch Fusion+ integration.',
                  step: '04'
                }
              ].map((step, index) => (
                <Card 
                  key={index} 
                  className={cn(
                    "p-6 text-center group relative",
                    "bg-gradient-to-br from-slate-800 to-slate-900",
                    "border border-emerald-500/20 hover:border-emerald-400/50",
                    "shadow-lg hover:shadow-xl hover:shadow-emerald-400/20",
                    "transition-all duration-300 hover:scale-105 transform",
                    "backdrop-blur-sm"
                  )}
                  style={{ animationDelay: `${index * 150}ms` }}
                >
                  <div className="relative">
                    <div className={cn(
                      "absolute -top-3 -right-3 w-8 h-8 rounded-full",
                      "bg-emerald-500 border border-emerald-400",
                      "flex items-center justify-center text-xs font-bold text-slate-900"
                    )}>
                      {step.step}
                    </div>
                    <div className="group-hover:animate-bounce">
                      {step.icon}
                    </div>
                  </div>
                  <CardHeader className="pb-2">
                    <CardTitle className={cn(
                      "text-xl font-semibold text-slate-100",
                      "group-hover:text-emerald-400 transition-colors"
                    )}>
                      {step.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-slate-400 text-sm leading-relaxed">
                      {step.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Key Features Section */}
        <section className="py-16 md:py-24 bg-slate-800/30">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-3xl md:text-4xl font-bold text-center mb-4 text-slate-100">
              Why Choose <span className="text-emerald-400">QuantumLeap</span>?
            </h2>
            <p className="text-center text-slate-400 mb-16 text-lg max-w-2xl mx-auto">
              The most advanced cross-chain portfolio optimization platform in DeFi
            </p>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
              {[
                { 
                  icon: <Globe className="w-10 h-10 text-emerald-400 mb-4" />, 
                  title: 'True Cross-Chain Intelligence', 
                  description: 'Go beyond single-chain silos. Our platform processes data from 8 EVM networks to uncover diversified opportunities and mitigate chain-specific risks.',
                  highlight: '8 Chains'
                },
                { 
                  icon: <Brain className="w-10 h-10 text-emerald-400 mb-4" />, 
                  title: 'Advanced AI Forecasting', 
                  description: 'Proprietary ML models combine quantitative analysis, technical indicators, and market sentiment for superior alpha generation.',
                  highlight: 'AI-Powered'
                },
                { 
                  icon: <Shield className="w-10 h-10 text-emerald-400 mb-4" />, 
                  title: 'Nobel Prize-Winning MVO', 
                  description: 'Leverage Modern Portfolio Theory to build scientifically optimized portfolios that maximize returns while minimizing risk.',
                  highlight: 'Risk-Optimized'
                },
                { 
                  icon: <Clock className="w-10 h-10 text-emerald-400 mb-4" />, 
                  title: 'Lightning-Fast Discovery', 
                  description: 'Built for speed at ETHGlobal Prague. Identify market opportunities in real-time with sub-second data processing.',
                  highlight: 'Real-Time'
                }
              ].map((feature, index) => (
                <Card 
                  key={feature.title} 
                  className={cn(
                    "p-6 flex flex-col items-start group relative overflow-hidden",
                    "bg-gradient-to-br from-slate-800 to-slate-900",
                    "border border-emerald-500/20 hover:border-emerald-400/50",
                    "shadow-lg hover:shadow-xl hover:shadow-emerald-400/20",
                    "transition-all duration-300 hover:scale-105 transform",
                    "backdrop-blur-sm"
                  )}
                >
                  <div className={cn(
                    "absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-medium",
                    "bg-emerald-500/20 border border-emerald-500/30 text-emerald-400"
                  )}>
                    {feature.highlight}
                  </div>
                  <div className="group-hover:animate-pulse">
                    {feature.icon}
                  </div>
                  <CardHeader className="p-0 pb-2">
                    <CardTitle className={cn(
                      "text-xl font-semibold text-slate-100",
                      "group-hover:text-emerald-400 transition-colors"
                    )}>
                      {feature.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <CardDescription className="text-slate-400 text-sm leading-relaxed">
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Supported Chains Section */}
        <section className="py-16 md:py-24 bg-slate-900">
          <div className="max-w-6xl mx-auto text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-4 text-slate-100">
              Comprehensive <span className="text-emerald-400">EVM Ecosystem</span> Coverage
            </h2>
            <p className="text-slate-400 mb-12 text-lg max-w-2xl mx-auto">
              Access the deepest liquidity and broadest opportunities across major blockchain networks
            </p>
            
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-6 md:gap-8">
              {[
                { name: 'Ethereum', symbol: 'ETH' },
                { name: 'BNB Chain', symbol: 'BNB' },
                { name: 'Arbitrum', symbol: 'ARB' },
                { name: 'Polygon', symbol: 'POLY' },
                { name: 'Optimism', symbol: 'OP' },
                { name: 'Avalanche', symbol: 'AVAX' },
                { name: 'Fantom', symbol: 'FTM' },
                { name: 'Base', symbol: 'BASE' },
              ].map((chain, index) => (
                <div key={chain.name} style={{ animationDelay: `${index * 100}ms` }}>
                  <ChainLogo name={chain.name} symbol={chain.symbol} />
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Call to Action Section */}
        <section className="py-20 md:py-32 bg-slate-800/30 relative">
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 to-teal-500/5"></div>
          <div className="max-w-4xl mx-auto text-center relative z-10">
            <Card className={cn(
              "p-10 md:p-16",
              "bg-gradient-to-br from-slate-800 to-slate-900",
              "border border-emerald-500/30 hover:border-emerald-400/60",
              "shadow-2xl hover:shadow-emerald-400/25",
              "transition-all duration-300 backdrop-blur-sm"
            )}>
              <CardHeader>
                <CardTitle className="text-3xl md:text-4xl font-bold mb-6 text-slate-100">
                  Ready to Dominate <span className="text-emerald-400">Cross-Chain DeFi</span>?
                </CardTitle>
                <CardDescription className="text-lg text-slate-300 mb-10 max-w-2xl mx-auto leading-relaxed">
                  Join the alpha hunters using QuantumLeap to discover high-performing portfolios across 8 EVM chains. 
                  Your next 10x opportunity is waiting.
                </CardDescription>
              </CardHeader>
              
              <CardContent>
                <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                  <Link href="/dashboard">
                    <Button 
                      size="lg" 
                      className={cn(
                        "text-lg px-12 py-6 h-auto font-bold",
                        "bg-emerald-500 hover:bg-emerald-400 text-slate-900",
                        "shadow-xl hover:shadow-2xl hover:shadow-emerald-400/25",
                        "transition-all duration-300 hover:scale-105 transform",
                        "border border-emerald-400/50"
                      )}
                    >
                      <TrendingUp className="mr-2 h-5 w-5" />
                      Launch QuantumLeap
                      <ArrowRight className="ml-2 h-5 w-5" />
                    </Button>
                  </Link>
                  <Link href="https://github.com/elbarroca/eth_global_prague" target="_blank" rel="noopener noreferrer">
                    <Button 
                      variant="outline" 
                      size="lg" 
                      className={cn(
                        "text-lg px-12 py-6 h-auto",
                        "border-emerald-400/50 text-slate-100 bg-transparent",
                        "hover:bg-emerald-500 hover:text-slate-900 hover:border-emerald-400",
                        "transition-all duration-300 hover:scale-105",
                        "hover:shadow-lg hover:shadow-emerald-400/25"
                      )}
                    >
                      <GitFork className="mr-2 h-5 w-5" />
                      View Repository
                    </Button>
                  </Link>
                </div>
                
                <div className="flex justify-center items-center gap-4 text-sm text-slate-400">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
                    <span>Live Data</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse delay-300"></div>
                    <span>AI-Powered</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse delay-700"></div>
                    <span>Risk-Optimized</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className={cn(
        "px-6 py-12 relative z-10",
        "border-t border-slate-700/50 bg-slate-900"
      )}>
        <div className="max-w-7xl mx-auto">
          <div className="text-center">
            <div className="text-2xl font-bold text-emerald-400 mb-4 flex items-center justify-center gap-2">
              <Network className="w-6 h-6" />
              QuantumLeap
            </div>
            <p className="text-slate-400 text-sm mb-4">
              © {new Date().getFullYear()} QuantumLeap. Built with ❤️ at ETHGlobal Prague.
            </p>
            <Link 
              href="https://github.com/elbarroca/eth_global_prague" 
              target="_blank" 
              rel="noopener noreferrer" 
              className={cn(
                "inline-flex items-center gap-2 text-slate-400 text-sm font-medium",
                "hover:text-emerald-400 transition-colors duration-300"
              )}
            >
              <GitFork className="w-4 h-4" />
              Open Source on GitHub
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Home;
