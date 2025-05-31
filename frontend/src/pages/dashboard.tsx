import { ConnectButton } from '@rainbow-me/rainbowkit';
import type { NextPage } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Wallet, Activity, TrendingUp, Shield, Zap, ExternalLink } from 'lucide-react';

const Dashboard: NextPage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <Head>
        <title>Dashboard - Web3 App</title>
        <meta
          content="Dashboard for your Web3 application"
          name="description"
        />
        <link href="/favicon.ico" rel="icon" />
      </Head>

      {/* Navigation */}
      <nav className="sticky top-0 z-50 px-6 py-4 border-b border-white/20 bg-white/70 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="sm" className="hover:bg-white/50">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Home
              </Button>
            </Link>
            <div className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Web3App Dashboard
            </div>
          </div>
          <div className="flex items-center">
            <ConnectButton />
          </div>
        </div>
      </nav>

      {/* Main Dashboard */}
      <main className="px-6 py-12">
        <div className="max-w-7xl mx-auto">
          
          {/* Welcome Section */}
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4 leading-tight">
              Welcome to Your 
              <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent block sm:inline">
                {' '}Web3 Dashboard
              </span>
            </h1>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed">
              Connect your wallet and explore the next generation of decentralized applications
            </p>
          </div>

          {/* Stats Cards */}
          <div className="grid md:grid-cols-3 gap-6 mb-12">
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/30 hover:shadow-xl transition-all duration-300">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Wallet className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600 font-medium">Wallet Status</p>
                  <p className="text-2xl font-bold text-gray-900">Connected</p>
                </div>
              </div>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/30 hover:shadow-xl transition-all duration-300">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <TrendingUp className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600 font-medium">Portfolio Value</p>
                  <p className="text-2xl font-bold text-gray-900">$0.00</p>
                </div>
              </div>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/30 hover:shadow-xl transition-all duration-300">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Activity className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600 font-medium">Transactions</p>
                  <p className="text-2xl font-bold text-gray-900">0</p>
                </div>
              </div>
            </div>
          </div>

          {/* Resources Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-8 shadow-lg border border-white/30 hover:shadow-xl transition-all duration-300 group">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Shield className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="text-xl font-semibold mb-4 text-gray-900">RainbowKit Documentation</h3>
              <p className="text-gray-600 mb-6 leading-relaxed">
                Learn how to customize your wallet connection flow and integrate with different wallets.
              </p>
              <Button variant="outline" asChild className="w-full sm:w-auto">
                <a href="https://rainbowkit.com" target="_blank" rel="noopener noreferrer">
                  View Docs <ExternalLink className="ml-2 h-4 w-4" />
                </a>
              </Button>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-8 shadow-lg border border-white/30 hover:shadow-xl transition-all duration-300 group">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Zap className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="text-xl font-semibold mb-4 text-gray-900">wagmi Documentation</h3>
              <p className="text-gray-600 mb-6 leading-relaxed">
                Discover powerful React hooks for Ethereum that make interacting with the blockchain simple.
              </p>
              <Button variant="outline" asChild className="w-full sm:w-auto">
                <a href="https://wagmi.sh" target="_blank" rel="noopener noreferrer">
                  Explore wagmi <ExternalLink className="ml-2 h-4 w-4" />
                </a>
              </Button>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-8 shadow-lg border border-white/30 hover:shadow-xl transition-all duration-300 group">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Activity className="h-6 w-6 text-purple-600" />
              </div>
              <h3 className="text-xl font-semibold mb-4 text-gray-900">RainbowKit Examples</h3>
              <p className="text-gray-600 mb-6 leading-relaxed">
                Discover boilerplate example RainbowKit projects to accelerate your development.
              </p>
              <Button variant="outline" asChild className="w-full sm:w-auto">
                <a href="https://github.com/rainbow-me/rainbowkit/tree/main/examples" target="_blank" rel="noopener noreferrer">
                  View Examples <ExternalLink className="ml-2 h-4 w-4" />
                </a>
              </Button>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-8 shadow-lg border border-white/30 hover:shadow-xl transition-all duration-300 group">
              <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Shield className="h-6 w-6 text-yellow-600" />
              </div>
              <h3 className="text-xl font-semibold mb-4 text-gray-900">Next.js Documentation</h3>
              <p className="text-gray-600 mb-6 leading-relaxed">
                Find in-depth information about Next.js features and API for building modern web apps.
              </p>
              <Button variant="outline" asChild className="w-full sm:w-auto">
                <a href="https://nextjs.org/docs" target="_blank" rel="noopener noreferrer">
                  Learn Next.js <ExternalLink className="ml-2 h-4 w-4" />
                </a>
              </Button>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-8 shadow-lg border border-white/30 hover:shadow-xl transition-all duration-300 group">
              <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <TrendingUp className="h-6 w-6 text-red-600" />
              </div>
              <h3 className="text-xl font-semibold mb-4 text-gray-900">Next.js Examples</h3>
              <p className="text-gray-600 mb-6 leading-relaxed">
                Discover and deploy boilerplate example Next.js projects for various use cases.
              </p>
              <Button variant="outline" asChild className="w-full sm:w-auto">
                <a href="https://github.com/vercel/next.js/tree/canary/examples" target="_blank" rel="noopener noreferrer">
                  Browse Examples <ExternalLink className="ml-2 h-4 w-4" />
                </a>
              </Button>
            </div>

            <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-8 text-white">
              <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center mb-6 hover:scale-110 transition-transform">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-4">Deploy Your App</h3>
              <p className="text-white/90 mb-6 leading-relaxed">
                Instantly deploy your Next.js site to a public URL with Vercel for seamless hosting.
              </p>
              <Button variant="secondary" asChild className="w-full sm:w-auto">
                <a href="https://vercel.com/new?utm_source=create-next-app&utm_medium=default-template&utm_campaign=create-next-app" target="_blank" rel="noopener noreferrer">
                  Deploy Now <ExternalLink className="ml-2 h-4 w-4" />
                </a>
              </Button>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-6 py-12 border-t border-gray-200 bg-white/50 backdrop-blur-sm mt-12">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-gray-600">
            Made with ❤️ by your frens at 🌈
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Dashboard; 