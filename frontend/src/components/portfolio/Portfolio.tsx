import React, { useState } from 'react';
import { PieChart, List, TrendingUp, Settings2, BarChart3, AlertCircle } from 'lucide-react';
import axios from 'axios';

interface AllocationDetail {
    ticker: string;
    shares: number;
    current_price: number;
    weight_percent: number;
    total_value: number;
}

interface PortfolioResult {
    success: boolean;
    performance: {
        expected_annual_return: number;
        annual_volatility: number;
        sharpe_ratio: number;
    };
    allocation: AllocationDetail[];
    leftover_cash: number;
    initial_capital: number;
    charts: {
        pie_chart: string;
        cumulative_returns: string;
    };
    error?: string;
}

export default function Portfolio() {
  const [tickers, setTickers] = useState<string>("AAPL, MSFT, TSLA, NVDA");
  const [capital, setCapital] = useState<number>(100000);
  const [riskFree, setRiskFree] = useState<number>(0.02);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PortfolioResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleOptimize = async () => {
      setLoading(true);
      setErrorMsg(null);
      setResult(null);
      
      try {
          // Parse tickers from string
          const tickerList = tickers.split(',').map(t => t.trim().toUpperCase()).filter(t => t);
          
          if (tickerList.length === 0) {
              throw new Error("Please enter at least one ticker.");
          }
          if (capital < 100) {
              throw new Error("Initial capital must be at least $100");
          }

          const response = await axios.post('http://127.0.0.1:5000/api/portfolio/optimize', {
              tickers: tickerList,
              initial_capital: capital,
              risk_free_rate: riskFree
          });

          if (response.data.success) {
              setResult(response.data);
          } else {
              setErrorMsg(response.data.error || "Optimization failed.");
          }
      } catch (error: any) {
          console.error(error);
          setErrorMsg(error.response?.data?.error || error.message || "An unexpected error occurred.");
      } finally {
          setLoading(false);
      }
  };

  return (
    <div className="bg-[#0E1525] border border-gray-800 rounded-xl p-6 h-full flex flex-col gap-6 overflow-y-auto w-full relative">
        <h2 className="text-2xl font-black bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent flex items-center gap-2">
            AI Portfolio Optimizer <span className="text-sm font-semibold text-gray-400 block pt-1 bg-none text-white">(Mean-Variance Optimization)</span>
        </h2>
        
        {/* Controls Panel */}
        <div className="flex flex-col xl:flex-row gap-6 items-start bg-gray-900/60 p-6 rounded-xl border border-gray-800 shadow-inner">
            <div className="flex-1 w-full space-y-4">
                 <div>
                     <label className="text-sm font-bold text-gray-400 mb-2 block flex items-center gap-2">
                         <List size={16} /> Asset Tickers (Comma separated)
                     </label>
                     <input 
                         type="text" 
                         value={tickers}
                         onChange={(e) => setTickers(e.target.value)}
                         className="w-full bg-gray-950 border border-gray-800 text-white rounded-lg px-4 py-2.5 focus:outline-none focus:border-blue-500 transition shadow-inner"
                         placeholder="e.g. AAPL, MSFT, GOOGL"
                     />
                 </div>
                 <div className="flex gap-4">
                     <div className="flex-1">
                         <label className="text-sm font-bold text-gray-400 mb-2 block flex items-center gap-2">
                             <BarChart3 size={16} /> Initial Capital ($)
                         </label>
                         <input 
                             type="number" 
                             value={capital}
                             onChange={(e) => setCapital(Number(e.target.value))}
                             className="w-full bg-gray-950 border border-gray-800 text-white rounded-lg px-4 py-2.5 focus:outline-none focus:border-blue-500 transition shadow-inner font-mono"
                             min="100"
                         />
                     </div>
                     <div className="flex-1">
                         <label className="text-sm font-bold text-gray-400 mb-2 block flex items-center gap-2">
                             <Settings2 size={16} /> Risk-Free Rate
                         </label>
                         <input 
                             type="number" 
                             step="0.01"
                             value={riskFree}
                             onChange={(e) => setRiskFree(Number(e.target.value))}
                             className="w-full bg-gray-950 border border-gray-800 text-white rounded-lg px-4 py-2.5 focus:outline-none focus:border-blue-500 transition shadow-inner font-mono"
                         />
                     </div>
                 </div>
            </div>
            
            <div className="xl:h-full flex flex-col justify-end xl:pb-1 mt-auto">
                 <button 
                    onClick={handleOptimize}
                    disabled={loading}
                    className="w-full xl:w-48 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white font-black py-4 px-6 rounded-xl transition shadow-[0_0_20px_rgba(16,185,129,0.3)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
                     {loading ? (
                         <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white"></div>
                     ) : (
                         <>
                            <TrendingUp size={20} /> Optimize
                         </>
                     )}
                 </button>
            </div>
        </div>

        {errorMsg && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-4 rounded-lg flex items-center gap-3 font-semibold">
                <AlertCircle size={20} /> {errorMsg}
            </div>
        )}
        
        {/* Results Panel */}
        {result && (
        <div className="animate-fade-in flex flex-col xl:flex-row gap-8 mt-4">
             {/* Left Column: Stats & Allocation */}
             <div className="flex-1 flex flex-col gap-6">
                 {/* Performance Stats */}
                 <div className="grid grid-cols-3 gap-4">
                     <div className="bg-gray-800/40 p-4 rounded-xl border border-gray-800 text-center">
                         <p className="text-gray-400 font-bold mb-1 text-sm uppercase tracking-wider">Exp Return</p>
                         <h3 className="text-2xl font-black text-emerald-400">{result.performance.expected_annual_return}%</h3>
                     </div>
                     <div className="bg-gray-800/40 p-4 rounded-xl border border-gray-800 text-center">
                         <p className="text-gray-400 font-bold mb-1 text-sm uppercase tracking-wider">Volatility</p>
                         <h3 className="text-2xl font-black text-orange-400">{result.performance.annual_volatility}%</h3>
                     </div>
                     <div className="bg-gray-800/40 p-4 rounded-xl border border-gray-800 text-center">
                         <p className="text-gray-400 font-bold mb-1 text-sm uppercase tracking-wider">Sharpe</p>
                         <h3 className="text-2xl font-black text-blue-400">{result.performance.sharpe_ratio}</h3>
                     </div>
                 </div>

                 {/* Holding Details */}
                 <div className="flex-1 bg-gray-800/20 rounded-xl p-5 border border-gray-800/50 h-full">
                     <h4 className="font-bold flex items-center justify-between text-gray-300 mb-4 pb-4 border-b border-gray-800">
                         <span className="flex items-center gap-2"><PieChart size={18} /> Asset Holding Guide</span>
                         <span className="text-sm font-medium text-gray-400">Total: ${result.initial_capital.toLocaleString()}</span>
                     </h4>
                     
                     <div className="flex flex-col gap-3">
                         {result.allocation.map(holding => (
                             <div key={holding.ticker} className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-3 bg-gray-900/80 rounded-lg border border-gray-700/50">
                                 <div className="flex items-center gap-3">
                                     <div className="w-10 h-10 rounded-full bg-gray-800 flex items-center justify-center font-black text-xs text-blue-400 border border-gray-700">
                                         {holding.ticker}
                                     </div>
                                     <div>
                                         <span className="font-bold block text-white">{holding.weight_percent}%</span>
                                         <span className="text-xs font-semibold text-gray-400">{holding.shares} shares @ ${holding.current_price}</span>
                                     </div>
                                 </div>
                                 <div className="text-right mt-2 sm:mt-0">
                                     <span className="font-mono font-bold text-emerald-400 block">${holding.total_value.toLocaleString()}</span>
                                 </div>
                             </div>
                         ))}
                     </div>
                     
                     <div className="mt-4 p-3 bg-orange-500/10 border border-orange-500/20 rounded-lg text-orange-400/80 text-sm font-semibold flex justify-between">
                         <span>Leftover Cash:</span>
                         <span className="font-mono">${result.leftover_cash.toLocaleString()}</span>
                     </div>
                 </div>
             </div>

             {/* Right Column: Matplotlib Charts */}
             <div className="flex-1 flex flex-col gap-6">
                 {result.charts.cumulative_returns && (
                     <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 shadow-xl overflow-hidden aspect-video relative group">
                        <img 
                            src={`data:image/png;base64,${result.charts.cumulative_returns}`} 
                            alt="Cumulative Returns" 
                            className="w-full h-full object-contain mix-blend-screen opacity-90 transition-opacity group-hover:opacity-100" 
                        />
                     </div>
                 )}
                 {result.charts.pie_chart && (
                     <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 shadow-xl overflow-hidden aspect-square max-h-[400px] relative mx-auto xl:mx-0 w-full flex justify-center group">
                        <img 
                            src={`data:image/png;base64,${result.charts.pie_chart}`} 
                            alt="Allocation Pie Chart" 
                            className="w-full h-full object-contain mix-blend-screen opacity-90 transition-opacity group-hover:opacity-100" 
                        />
                     </div>
                 )}
             </div>
        </div>
        )}
    </div>
  );
}
