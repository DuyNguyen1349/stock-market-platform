'use client';
import React, { useState } from 'react';
import { LineChart, Search, Bell, PieChart, TrendingUp, BarChart2 } from 'lucide-react';
import dynamic from 'next/dynamic';

// Next.js dynamic import because lightweight-charts relies on window/document objects which are undefined during SSR
const StockChart = dynamic(() => import('@/components/StockChart'), { ssr: false });
import Screener from '@/components/screener/Screener';
import Portfolio from '@/components/portfolio/Portfolio';
import MarketSentiment from '@/components/sentiment/MarketSentiment';
import SentimentDashboard from '@/components/sentiment/SentimentDashboard';

export default function Home() {
  const [activeSymbol, setActiveSymbol] = useState('AAPL');
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [timeframe, setTimeframe] = useState('1M');

  return (
    <div className="flex h-screen bg-[#0E1525] text-white font-sans">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 flex flex-col pt-6 px-4 shrink-0">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-green-400 to-blue-500 bg-clip-text text-transparent mb-12 uppercase tracking-widest pl-2">
          FinSpace
        </h1>
        <nav className="flex flex-col gap-2">
          <button 
             onClick={() => setCurrentTab('dashboard')}
             className={`rounded-lg p-3 flex items-center gap-3 font-semibold transition ${currentTab === 'dashboard' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'}`}>
            <PieChart size={20} />
            Dashboard
          </button>
          <button 
             onClick={() => setCurrentTab('screener')}
             className={`rounded-lg p-3 flex items-center gap-3 font-medium transition ${currentTab === 'screener' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'}`}>
            <TrendingUp size={20} />
            Screener
          </button>
          <button 
             onClick={() => setCurrentTab('portfolio')}
             className={`rounded-lg p-3 flex items-center gap-3 font-medium transition ${currentTab === 'portfolio' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'}`}>
            <LineChart size={20} />
            Portfolio
          </button>
          <button 
             onClick={() => setCurrentTab('sentiment')}
             className={`rounded-lg p-3 flex items-center gap-3 font-medium transition ${currentTab === 'sentiment' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'}`}>
            <BarChart2 size={20} />
            Sentiment
          </button>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative overflow-y-auto">
        {/* Header */}
        <header className="h-20 border-b border-gray-800 flex items-center justify-between px-8 bg-[#0E1525] sticky top-0 z-10 shrink-0">
          <div className="relative w-96">
            <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
            <input 
              className="w-full bg-gray-900 border border-gray-800 text-white rounded-full pl-10 pr-4 py-2 focus:outline-none focus:border-blue-500 transition shadow-inner"
              placeholder="Search stocks (e.g., TSLA, NVDA)..."
              onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                      const val = (e.target as HTMLInputElement).value.toUpperCase();
                      if (val) setActiveSymbol(val);
                      (e.target as HTMLInputElement).value = '';
                  }
              }}
            />
          </div>
          <div className="flex items-center gap-6">
            <button className="text-gray-400 hover:text-white transition"><Bell size={22} /></button>
            <div className="w-9 h-9 bg-blue-600 rounded-full cursor-pointer flex items-center justify-center font-bold text-sm">
              AD
            </div>
          </div>
        </header>

        {/* Dashboard Cards */}
        <div className="p-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {['NASDAQ', 'S&P 500', 'DOW JONES', 'RUSSELL'].map((idx, i) => (
              <div key={idx} className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-lg">
                <p className="text-gray-400 font-medium text-sm mb-1">{idx}</p>
                <h3 className="text-2xl font-bold mb-2">{(12050 + i * 50).toLocaleString()}</h3>
                <span suppressHydrationWarning className="text-green-500 text-sm font-semibold block bg-green-500/10 w-fit px-2 py-0.5 rounded-md">
                  +1.{(Math.random() * 5).toFixed(2)}%
                </span>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 min-h-[600px]">
            {/* Main Area based on Tab */}
            <div className={`relative flex flex-col ${currentTab === 'sentiment' ? 'lg:col-span-3' : 'lg:col-span-2'}`}>
              {currentTab === 'screener' && <Screener />}
              {currentTab === 'portfolio' && <Portfolio />}
              {currentTab === 'sentiment' && <SentimentDashboard symbol={activeSymbol} />}
              
              {currentTab === 'dashboard' && (
                  <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 relative flex flex-col h-full border-b-[4px] border-blue-500/20 shadow-[0_4px_30px_rgb(0,0,0,0.5)]">
                      <div className="flex justify-between items-center mb-4">
                          <div>
                              <h2 className="text-2xl font-black bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent drop-shadow-sm">{activeSymbol}</h2>
                              <span className="text-sm font-semibold tracking-wide text-gray-500 block uppercase pt-0.5">Real-time Advanced Chart</span>
                          </div>
                          <div className="flex bg-gray-950 p-1.5 rounded-lg border border-gray-800 shadow-inner">
                              {['1D', '1W', '1M', '3M', '1Y', '5Y'].map(tf => (
                                  <button 
                                     key={tf} 
                                     onClick={() => setTimeframe(tf)}
                                     className={`px-3 py-1.5 text-xs tracking-wider uppercase font-black rounded-md transition duration-200 ${tf === timeframe ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-md' : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}>
                                      {tf}
                                  </button>
                              ))}
                          </div>
                      </div>
                      <div className="flex-1 w-full relative min-h-[400px]">
                         <StockChart symbol={activeSymbol} timeframe={timeframe} />
                      </div>
                  </div>
              )}
            </div>

            {/* Right Side Panel */}
            {currentTab !== 'sentiment' && (
            <div className="flex flex-col gap-6">
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex flex-col gap-4 max-h-[400px] overflow-y-auto">
                  <h4 className="font-bold text-lg mb-2">Trending Stocks</h4>
                  {['TSLA', 'NVDA', 'AAPL', 'AMD', 'META', 'AMZN'].map((t) => {
                    const isPos = Math.random() > 0.3;
                    return (
                      <div key={t} 
                           onClick={() => setActiveSymbol(t)}
                           className={`flex justify-between items-center bg-gray-800/40 hover:bg-gray-700 cursor-pointer p-3 rounded-lg border transition ${activeSymbol === t ? 'border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.2)]' : 'border-gray-800/80'}`}
                      >
                        <div>
                          <span className="block font-bold mb-0.5 text-[15px]">{t}</span>
                          <span className="text-xs text-gray-400">Equity</span>
                        </div>
                        <div className="text-right">
                          <span suppressHydrationWarning className="block font-bold">${(Math.random() * 300 + 50).toFixed(2)}</span>
                          <span suppressHydrationWarning className={`text-sm font-semibold ${isPos ? 'text-green-400' : 'text-red-400'}`}>
                            {isPos ? '+' : '-'}{((Math.random() * 5)).toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <MarketSentiment symbol={activeSymbol} />
            </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
