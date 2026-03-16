'use client';
import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries } from 'lightweight-charts';
import axios from 'axios';
import useWebSocket from 'react-use-websocket';

interface StockChartProps {
    symbol: string;
    timeframe: string;
}

export default function StockChart({ symbol, timeframe }: StockChartProps) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const [loading, setLoading] = useState(true);
    const [livePrice, setLivePrice] = useState<number | null>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const lastCandleRef = useRef<any>(null); // To store the latest candle for real-time updates

    // Finnhub WebSocket connection
    const FINNHUB_TOKEN = 'd6odtjpr01qnu98hmql0d6odtjpr01qnu98hmqlg';
    const socketUrl = `wss://ws.finnhub.io?token=${FINNHUB_TOKEN}`;
    const { sendMessage, lastMessage } = useWebSocket(socketUrl, {
        shouldReconnect: () => true,
    });

    // Handle WebSocket Subscriptions
    useEffect(() => {
        // Subscribe to current symbol
        sendMessage(JSON.stringify({ type: 'subscribe', symbol: symbol }));
        return () => {
             // Unsubscribe when component unmounts or symbol changes
             sendMessage(JSON.stringify({ type: 'unsubscribe', symbol: symbol }));
        };
    }, [symbol, sendMessage]);

    // Handle incoming Finnhub WebSocket messages
    useEffect(() => {
        if (lastMessage !== null) {
            try {
                const message = JSON.parse(lastMessage.data);
                if (message.type === 'trade' && message.data && message.data.length > 0) {
                    // Finnhub can send multiple trades in a batch; get the latest one
                    const latestTrade = message.data[message.data.length - 1];
                    const tradePrice = latestTrade.p;
                    
                    if (latestTrade.s === symbol) {
                        setLivePrice(tradePrice);
                        
                        // Update the last candle on the chart using the live trade price
                        if (lastCandleRef.current && seriesRef.current) {
                            lastCandleRef.current.close = tradePrice;
                            lastCandleRef.current.high = Math.max(lastCandleRef.current.high, tradePrice);
                            lastCandleRef.current.low = Math.min(lastCandleRef.current.low, tradePrice);
                            
                            seriesRef.current.update(lastCandleRef.current);
                        }
                    }
                }
            } catch (err) {
                console.error("Error parsing websocket message:", err);
            }
        }
    }, [lastMessage, symbol]);

    // Initialize Chart and Load Historical Data
    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#d1d5db', // gray-300
            },
            grid: {
                vertLines: { color: '#374151' }, // gray-700
                horzLines: { color: '#374151' },
            },
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
            },
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight,
        });

        // Initialize empty series
        const newSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#22c55e', // green-500
            downColor: '#ef4444', // red-500
            borderVisible: false,
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
        });

        chartRef.current = chart;
        seriesRef.current = newSeries;

        // Auto-resize listener
        const handleResize = () => {
            if (chartContainerRef.current && chartRef.current) {
                chartRef.current.applyOptions({
                    width: chartContainerRef.current.clientWidth,
                    height: chartContainerRef.current.clientHeight,
                });
            }
        };
        window.addEventListener('resize', handleResize);

        // Fetch Data
        setLoading(true);
        setLivePrice(null); // Reset live price until socket gives data
        axios.get(`http://localhost:5001/api/stocks/${symbol}/chart?range=${timeframe}`)
            .then(res => {
                const data = res.data.data; // { time, open, high, low, close }
                if (data && data.length > 0 && seriesRef.current) {
                    seriesRef.current.setData(data);
                    chartRef.current?.timeScale().fitContent();
                    
                    // Save the last candle so WebSocket can update it
                    lastCandleRef.current = { ...data[data.length - 1] };
                }
            })
            .catch(err => console.error("Error fetching chart data:", err))
            .finally(() => setLoading(false));

        return () => {
             window.removeEventListener('resize', handleResize);
             chart.remove();
        };
    }, [symbol, timeframe]);

    return (
        <div className="w-full h-full relative">
            {/* Display Real-time live price indicator overlaid on chart */}
            <div className="absolute top-4 left-4 z-10">
                {livePrice !== null ? (
                    <div className="flex items-center gap-2 bg-gray-900/80 backdrop-blur-md px-3 py-1.5 rounded-full border border-gray-700 shadow-lg">
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                        </span>
                        <span className="text-white font-bold tracking-wider">${livePrice.toFixed(2)}</span>
                    </div>
                ) : (
                    <div className="px-3 py-1.5 rounded-full bg-gray-900/50 backdrop-blur-md border border-gray-800 text-gray-500 text-sm font-semibold">
                        Waiting for live data...
                    </div>
                )}
            </div>
            
            {loading && (
                 <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50 z-20 backdrop-blur-sm">
                    <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-green-500 border-b-2 border-blue-500"></div>
                 </div>
            )}
            <div ref={chartContainerRef} className="w-full h-full" />
        </div>
    );
}
