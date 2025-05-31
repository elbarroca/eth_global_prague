import type { NextPage } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowRight, Wallet, Shield, Zap } from 'lucide-react';
import { InteractiveStarryBackground } from '@/components/ui/interactive-starry-background';
import { AnimatedFeatureIcon } from '@/components/ui/animated-feature-icon';

const Home: NextPage = () => {
  return (
    <div className="min-h-screen text-gray-100 relative">
      <InteractiveStarryBackground />
      <div style={{ position: 'relative', zIndex: 1 }}>
        <Head>
          <title>Web3 App - Connect Your Future</title>
          <meta
            content="The next generation Web3 application powered by RainbowKit and wagmi"
            name="description"
          />
          <link href="/favicon.ico" rel="icon" />
        </Head>

        {/* Navigation */}
        <nav className="px-6 sm:px-8 py-6 sticky top-0 z-50 bg-black/70 backdrop-blur-md shadow-lg border-b border-green-700/50">
          <div className="max-w-7xl mx-auto flex justify-between items-center">
            <div className="text-3xl font-bold bg-gradient-to-r from-green-400 to-emerald-600 bg-clip-text text-transparent px-4 py-2 border border-green-600/70 rounded-lg shadow-md">
              Web3App
            </div>
            <Link href="/dashboard">
              <Button 
                variant="outline" 
                className="border-green-500 text-green-400 hover:bg-green-500 hover:text-black transition-colors duration-300"
              >
                Go to Dashboard
              </Button>
            </Link>
          </div>
        </nav>

        {/* Hero Section */}
        <main className="px-6 sm:px-8 py-24 md:py-32">
          <div className="max-w-7xl mx-auto grid md:grid-cols-5 gap-16 items-center">
            {/* Text Content Area - Spanning 3 columns */}
            <div className="md:col-span-3 text-left">
              <h1 className="text-6xl sm:text-7xl md:text-8xl font-bold mb-10 leading-tight text-center">
                <span className="text-gray-50">Connect Your</span>
                <span className="block text-center bg-gradient-to-r from-green-400 via-emerald-500 to-teal-500 bg-clip-text text-transparent leading-normal sm:leading-tight relative py-2">
                  Web3 Future
                  <span className="absolute bottom-0 left-1/2 transform -translate-x-1/2 h-1 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full opacity-75 w-3/4"></span>
                </span>
              </h1>
              <div className="px-4 py-6 md:px-6 md:py-8 border border-green-600/70 rounded-lg shadow-md bg-black/40 backdrop-blur-sm">
                <p className="text-xl sm:text-2xl text-gray-300 leading-relaxed max-w-2xl">
                  Experience the next generation of decentralized applications with seamless 
                  wallet integration, secure transactions, and intuitive user experience.
                </p>
              </div>
            </div>

            {/* CTA Buttons Area - Spanning 2 columns, aligned to the right or stacked on mobile */}
            <div className="md:col-span-2 flex flex-col gap-6 items-start md:items-start">
              <Link href="/dashboard" className="w-full md:w-auto">
                <Button variant="outline" size="lg" className="w-full text-xl px-12 py-7 h-auto shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-300 border-green-600 text-green-400 hover:bg-green-600 hover:text-white hover:border-green-700">
                  Get Started
                  <ArrowRight className="ml-3 h-6 w-6" />
                </Button>
              </Link>
              <Link href="/dashboard" className="w-full md:w-auto">
                <Button variant="outline" size="lg" className="w-full text-xl px-12 py-7 h-auto border-green-600 text-green-400 hover:bg-green-600 hover:text-white hover:border-green-700 transform hover:scale-105 transition-all duration-300">
                  Learn More
                </Button>
              </Link>
            </div>
          </div>

          {/* Features Grid - Placed after the new hero layout */}
          <div className="max-w-7xl mx-auto">
            <div className="flex flex-wrap justify-center items-start gap-10 lg:gap-12 mt-32 md:mt-48">
              {/* Feature Card 1 - Slightly offset and different hover effect */}
              <div className="w-full md:w-1/3 lg:w-1/4 transform hover:-translate-y-2 hover:rotate-[-2deg] transition-all duration-300">
                <div className="px-4 py-6 md:px-6 md:py-8 border border-green-600/70 rounded-lg shadow-md bg-black/40 backdrop-blur-sm group flex flex-col items-center h-full hover:border-green-500">
                  <AnimatedFeatureIcon IconComponent={Wallet} />
                  <h3 className="text-2xl font-semibold mb-4 bg-gradient-to-r from-green-400 to-emerald-600 bg-clip-text text-transparent">Easy Wallet Connection</h3>
                  <p className="text-gray-400 leading-relaxed mb-6 text-center">
                    Connect your favorite wallet with just one click. Support for MetaMask, 
                    WalletConnect, and more.
                  </p>
                  <Link href="/dashboard" className="mt-auto">
                    <Button variant="ghost" className="mt-4 text-green-400 hover:bg-green-700/20 hover:text-green-300 transition-colors duration-300">
                      Try Now <ArrowRight className="ml-2 h-5 w-5" />
                    </Button>
                  </Link>
                </div>
              </div>

              {/* Feature Card 2 - Center, slightly larger on hover */}
              <div className="w-full md:w-1/3 lg:w-1/4 transform hover:scale-105 transition-all duration-300 z-10">
                <div className="px-4 py-6 md:px-6 md:py-8 border border-green-600/70 rounded-lg shadow-md bg-black/40 backdrop-blur-sm group flex flex-col items-center h-full hover:border-green-400">
                  <AnimatedFeatureIcon IconComponent={Shield} containerSizeClassName='w-20 h-20' iconSizeClassName='h-10 w-10' />
                  <h3 className="text-3xl font-semibold mb-5 bg-gradient-to-r from-green-400 to-emerald-600 bg-clip-text text-transparent">Secure Transactions</h3>
                  <p className="text-gray-300 leading-relaxed mb-7 text-center">
                    Built with security in mind. Your transactions are protected by 
                    industry-leading encryption and smart contracts.
                  </p>
                  <Link href="/dashboard" className="mt-auto">
                    <Button variant="ghost" className="mt-4 text-green-300 hover:bg-green-600/30 hover:text-green-200 transition-colors duration-300 text-lg">
                      Learn More <ArrowRight className="ml-2 h-5 w-5" />
                    </Button>
                  </Link>
                </div>
              </div>

              {/* Feature Card 3 - Slightly offset and different hover effect */}
              <div className="w-full md:w-1/3 lg:w-1/4 transform hover:-translate-y-2 hover:rotate-[2deg] transition-all duration-300">
                <div className="px-4 py-6 md:px-6 md:py-8 border border-green-600/70 rounded-lg shadow-md bg-black/40 backdrop-blur-sm group flex flex-col items-center h-full hover:border-green-500">
                  <AnimatedFeatureIcon IconComponent={Zap} />
                  <h3 className="text-2xl font-semibold mb-4 bg-gradient-to-r from-green-400 to-emerald-600 bg-clip-text text-transparent">Lightning Fast</h3>
                  <p className="text-gray-400 leading-relaxed mb-6 text-center">
                    Optimized for speed and performance. Experience instant transactions 
                    and real-time updates.
                  </p>
                  <Link href="/dashboard" className="mt-auto">
                    <Button variant="ghost" className="mt-4 text-green-400 hover:bg-green-700/20 hover:text-green-300 transition-colors duration-300">
                      Experience <ArrowRight className="ml-2 h-5 w-5" />
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </div>
          
          {/* Final CTA - Making it wider and more distinct */}
          <div className="max-w-7xl mx-auto mt-32 md:mt-48">
            <div className="px-4 py-10 sm:px-8 sm:py-14 md:px-10 md:py-20 border border-green-600/70 rounded-lg shadow-md bg-black/40 backdrop-blur-sm text-white text-center transform hover:scale-[1.03] transition-transform duration-300 hover:border-green-500/90">
              <h2 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-8 bg-gradient-to-r from-green-400 to-emerald-600 bg-clip-text text-transparent">
                Ready to dive into Web3?
              </h2>
              <p className="text-xl sm:text-2xl mb-12 opacity-95 max-w-3xl mx-auto text-gray-100">
                Join thousands of users already exploring the decentralized future. 
                Your journey starts now!
              </p>
              <Link href="/dashboard">
                <Button size="lg" variant="secondary" className="text-xl px-12 py-7 h-auto shadow-lg hover:shadow-xl transform hover:scale-110 transition-all duration-300 bg-gray-50 text-green-700 hover:bg-green-600 hover:text-white focus:ring-4 focus:ring-gray-200">
                  Launch Dashboard
                  <ArrowRight className="ml-3 h-7 w-7" />
                </Button>
              </Link>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="px-6 sm:px-8 py-16 border-t border-green-700/30 bg-black/60 backdrop-blur-sm mt-24 md:mt-32">
          <div className="max-w-7xl mx-auto text-center">
            <p className="text-gray-400 text-lg">
              Made with ❤️ for the Web3 community
            </p>
          </div>
        </footer>

      </div>
    </div>
  );
};

export default Home;
