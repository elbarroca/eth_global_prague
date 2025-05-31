import type { NextPage } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowRight, Wallet, Shield, Zap } from 'lucide-react';

const Home: NextPage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <Head>
        <title>Web3 App - Connect Your Future</title>
        <meta
          content="The next generation Web3 application powered by RainbowKit and wagmi"
          name="description"
        />
        <link href="/favicon.ico" rel="icon" />
      </Head>

      {/* Navigation */}
      <nav className="px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Web3App
          </div>
          <Link href="/dashboard">
            <Button variant="outline" className="hover:bg-white/50">Go to Dashboard</Button>
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="px-6 py-20">
        <div className="max-w-7xl mx-auto text-center">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-gray-900 mb-8 leading-tight">
              Connect Your
              <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent block sm:inline">
                {' '}Web3 Future
              </span>
            </h1>
            
            <p className="text-xl md:text-2xl text-gray-600 mb-12 leading-relaxed max-w-3xl mx-auto">
              Experience the next generation of decentralized applications with seamless 
              wallet integration, secure transactions, and intuitive user experience.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-20">
              <Link href="/dashboard">
                <Button size="lg" className="text-lg px-8 py-6 h-auto shadow-lg hover:shadow-xl transition-all">
                  Get Started
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="/dashboard">
                <Button variant="outline" size="lg" className="text-lg px-8 py-6 h-auto hover:bg-white/50">
                  Learn More
                </Button>
              </Link>
            </div>

            {/* Features Grid */}
            <div className="grid md:grid-cols-3 gap-8 mt-20">
              <div className="bg-white/80 backdrop-blur-sm rounded-xl p-8 shadow-lg border border-white/30 hover:shadow-xl transition-all duration-300 group">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-6 mx-auto group-hover:scale-110 transition-transform">
                  <Wallet className="h-6 w-6 text-blue-600" />
                </div>
                <h3 className="text-xl font-semibold mb-4 text-gray-900">Easy Wallet Connection</h3>
                <p className="text-gray-600 leading-relaxed mb-4">
                  Connect your favorite wallet with just one click. Support for MetaMask, 
                  WalletConnect, and more.
                </p>
                <Link href="/dashboard">
                  <Button variant="ghost" className="mt-4 hover:bg-blue-50">
                    Try Now <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>

              <div className="bg-white/80 backdrop-blur-sm rounded-xl p-8 shadow-lg border border-white/30 hover:shadow-xl transition-all duration-300 group">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-6 mx-auto group-hover:scale-110 transition-transform">
                  <Shield className="h-6 w-6 text-purple-600" />
                </div>
                <h3 className="text-xl font-semibold mb-4 text-gray-900">Secure Transactions</h3>
                <p className="text-gray-600 leading-relaxed mb-4">
                  Built with security in mind. Your transactions are protected by 
                  industry-leading encryption and smart contracts.
                </p>
                <Link href="/dashboard">
                  <Button variant="ghost" className="mt-4 hover:bg-purple-50">
                    Learn More <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>

              <div className="bg-white/80 backdrop-blur-sm rounded-xl p-8 shadow-lg border border-white/30 hover:shadow-xl transition-all duration-300 group">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-6 mx-auto group-hover:scale-110 transition-transform">
                  <Zap className="h-6 w-6 text-green-600" />
                </div>
                <h3 className="text-xl font-semibold mb-4 text-gray-900">Lightning Fast</h3>
                <p className="text-gray-600 leading-relaxed mb-4">
                  Optimized for speed and performance. Experience instant transactions 
                  and real-time updates.
                </p>
                <Link href="/dashboard">
                  <Button variant="ghost" className="mt-4 hover:bg-green-50">
                    Experience <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </div>

            {/* Final CTA */}
            <div className="mt-20 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-12 text-white shadow-2xl">
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Ready to dive into Web3?
              </h2>
              <p className="text-xl mb-8 opacity-90 max-w-2xl mx-auto">
                Join thousands of users already exploring the decentralized future.
              </p>
              <Link href="/dashboard">
                <Button size="lg" variant="secondary" className="text-lg px-8 py-6 h-auto shadow-lg hover:shadow-xl transition-all">
                  Launch Dashboard
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-6 py-12 border-t border-gray-200 bg-white/50 backdrop-blur-sm mt-12">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-gray-600">
            Made with ❤️ for the Web3 community
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Home;
