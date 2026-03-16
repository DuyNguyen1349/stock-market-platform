import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MessageSquareText } from 'lucide-react';

export default function MarketSentiment({ symbol }: { symbol: string }) {
    const [analysis, setAnalysis] = useState<string>('Analyzing market sentiment...');
    const [nlpMetrics, setNlpMetrics] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        // This makes a call to the local backend (Port 5001) which proxies to Python and Gemini
        axios.get(`http://localhost:5001/api/ai/sentiment/${symbol}`)
            .then(res => {
                setAnalysis(res.data.analysis);
                setNlpMetrics(res.data.metrics);
            })
            .catch(() => setAnalysis('Failed to fetch AI sentiment. Please try again later.'))
            .finally(() => setLoading(false));
    }, [symbol]);

    return (
        <div className="bg-gray-800/60 border border-indigo-500/30 rounded-xl p-4 mt-4 shadow-lg backdrop-blur-sm">
            <h4 className="font-bold text-lg mb-3 flex items-center gap-2 text-indigo-400">
                <MessageSquareText size={20} /> AI Market Sentiment: {symbol}
            </h4>
            <div className={`text-gray-300 text-sm leading-relaxed ${loading ? 'animate-pulse' : ''} bg-gray-900/50 p-4 rounded-lg border border-gray-700/50 min-h-[100px] mb-4`}>
                {analysis}
            </div>

            {nlpMetrics && !loading && (
                <div className="grid grid-cols-2 gap-3 mb-2">
                    <div className="bg-gray-800 p-3 rounded border border-gray-700">
                        <span className="block text-xs text-gray-400 capitalize">NLP Compound Index</span>
                        <span className={`block font-bold mt-1 ${nlpMetrics.avg_compound > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {nlpMetrics.avg_compound > 0 ? '+' : ''}{nlpMetrics.avg_compound.toFixed(2)}
                        </span>
                    </div>
                    <div className="bg-gray-800 p-3 rounded border border-gray-700">
                        <span className="block text-xs text-gray-400 capitalize">Analyzed Headlines</span>
                        <span className="block font-bold mt-1 text-blue-400">{nlpMetrics.headline_count} Arts.</span>
                    </div>
                </div>
            )}

            {/* Visual Bar */}
            <div className="mt-2 flex gap-1 h-2 rounded-full overflow-hidden opacity-80">
                 <div className="bg-red-500 transition-all duration-500" style={{ width: nlpMetrics ? `${50 - Math.min(50, (nlpMetrics.avg_compound * 100))}%` : '25%' }}></div>
                 <div className="bg-gray-500 w-1/4"></div>
                 <div className="bg-green-500 transition-all duration-500" style={{ width: nlpMetrics ? `${50 + Math.max(-50, (nlpMetrics.avg_compound * 100))}%` : '50%' }}></div>
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1 font-semibold">
                <span>Bearish</span>
                <span>Bullish</span>
            </div>
        </div>
    );
}
