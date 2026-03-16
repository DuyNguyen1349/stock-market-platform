import React, { useState } from 'react';
import axios from 'axios';
import { Bot, TrendingUp, TrendingDown, Minus, X } from 'lucide-react';

export default function Screener() {
    const [loadingTicker, setLoadingTicker] = useState<string | null>(null);
    const [prediction, setPrediction] = useState<any | null>(null);

    const handlePredict = async (ticker: string) => {
        setLoadingTicker(ticker);
        try {
            const res = await axios.post('http://127.0.0.1:5000/api/predict', { ticker });
            if (res.data.success) {
                setPrediction(res.data);
            } else {
                alert('Prediction failed: ' + res.data.error);
            }
        } catch (err: any) {
            alert('Error: ' + err.message);
        } finally {
            setLoadingTicker(null);
        }
    };

    return (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 h-full flex flex-col relative">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
               <Bot className="text-blue-400" /> AI Market Screener & Predictor
            </h2>
            <div className="overflow-x-auto flex-1">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="text-gray-400 border-b border-gray-800">
                            <th className="pb-3 px-4 font-semibold">Symbol</th>
                            <th className="pb-3 px-4 font-semibold">Company</th>
                            <th className="pb-3 px-4 font-semibold text-right">Price</th>
                            <th className="pb-3 px-4 font-semibold text-right">Change</th>
                            <th className="pb-3 px-4 font-semibold text-right">Volume</th>
                            <th className="pb-3 px-4 font-semibold text-right">Market Cap</th>
                            <th className="pb-3 px-4 font-semibold text-center">AI Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META'].map((t, i) => {
                            const change = (Math.random() * 6) - 2;
                            const isPos = change > 0;
                            const isPredicting = loadingTicker === t;
                            return (
                                <tr key={t} className="border-b border-gray-800/50 hover:bg-gray-800/50 transition">
                                    <td className="py-4 px-4 font-bold">{t}</td>
                                    <td className="py-4 px-4 text-gray-300">Company {t}</td>
                                    <td suppressHydrationWarning className="py-4 px-4 text-right">${(150 + Math.random() * 300).toFixed(2)}</td>
                                    <td suppressHydrationWarning className={`py-4 px-4 text-right font-semibold ${isPos ? 'text-green-500' : 'text-red-500'}`}>
                                        {isPos ? '+' : ''}{change.toFixed(2)}%
                                    </td>
                                    <td suppressHydrationWarning className="py-4 px-4 text-right">{(Math.random() * 50 + 10).toFixed(1)}M</td>
                                    <td suppressHydrationWarning className="py-4 px-4 text-right">${(Math.random() * 2 + 1).toFixed(2)}T</td>
                                    <td className="py-4 px-4 text-center">
                                        <button 
                                            onClick={() => handlePredict(t)}
                                            disabled={loadingTicker !== null}
                                            className="bg-blue-600/20 border border-blue-500 hover:bg-blue-600 text-blue-400 hover:text-white px-4 py-1.5 rounded-lg text-sm font-bold transition disabled:opacity-50 flex items-center gap-2 mx-auto">
                                            {isPredicting ? <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full block"></span> : 'Predict'}
                                        </button>
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>

            {/* Prediction Modal */}
            {prediction && (
                <div className="absolute inset-0 bg-gray-900/95 backdrop-blur-sm z-50 rounded-xl flex items-center justify-center p-6 border border-gray-800 animate-fade-in shadow-2xl">
                    <div className="w-full max-w-4xl bg-gray-950 border border-gray-800 rounded-2xl shadow-2xl overflow-hidden relative">
                         <button onClick={() => setPrediction(null)} className="absolute top-4 right-4 text-gray-400 hover:text-white bg-gray-800 p-1.5 rounded-full"><X size={20} /></button>
                         <div className="p-6 border-b border-gray-800 flex items-center justify-between bg-gradient-to-r from-gray-900 to-gray-950">
                             <div>
                                 <h3 className="text-3xl font-black text-white">{prediction.ticker} <span className="text-xl font-medium text-gray-400">90-Day AI Forecast</span></h3>
                             </div>
                             <div className={`px-4 py-2 rounded-xl border flex items-center gap-2 font-black text-xl uppercase tracking-wider
                                  ${prediction.recommendation.includes('BUY') ? 'bg-green-500/10 text-green-400 border-green-500/30' : 
                                    prediction.recommendation.includes('SELL') ? 'bg-red-500/10 text-red-400 border-red-500/30' : 
                                    'bg-gray-500/10 text-gray-400 border-gray-500/30'}`}>
                                  {prediction.recommendation.includes('BUY') ? <TrendingUp size={24} /> : 
                                   prediction.recommendation.includes('SELL') ? <TrendingDown size={24} /> : <Minus size={24} />}
                                  {prediction.recommendation}
                             </div>
                         </div>
                         <div className="p-6 flex flex-col gap-6">
                             <div className="grid grid-cols-3 gap-4">
                                 <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center shadow-inner">
                                     <span className="text-gray-400 text-sm font-bold uppercase block mb-1">Current</span>
                                     <span className="text-2xl font-mono block text-white">${prediction.current_price}</span>
                                 </div>
                                 <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center shadow-inner">
                                     <span className="text-gray-400 text-sm font-bold uppercase block mb-1">Predicted (90D)</span>
                                     <span className="text-2xl font-mono block text-white">${prediction.predicted_price_90d}</span>
                                 </div>
                                 <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center shadow-inner">
                                     <span className="text-gray-400 text-sm font-bold uppercase block mb-1">Expected Change</span>
                                     <span className={`text-2xl font-mono block font-black ${prediction.change_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                         {prediction.change_pct > 0 ? '+' : ''}{prediction.change_pct}%
                                     </span>
                                 </div>
                             </div>
                             <div className="rounded-xl overflow-hidden border border-gray-800 w-full aspect-[2/1] bg-gray-900 relative">
                                  <img 
                                      src={`data:image/png;base64,${prediction.chart}`} 
                                      alt={`${prediction.ticker} Forecast`} 
                                      className="w-full h-full object-contain absolute inset-0" 
                                  />
                             </div>
                             <p className="text-center text-sm font-medium text-gray-500">
                                 Powered by Meta Prophet Time-Series Analytics
                             </p>
                         </div>
                    </div>
                </div>
            )}
        </div>
    );
}
