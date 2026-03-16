import express, { Request, Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { GoogleGenerativeAI } from '@google/generative-ai';
import axios from 'axios';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5001;

app.use(cors());
app.use(express.json());

// Health Check
app.get('/api/health', (req: Request, res: Response) => {
    res.json({ status: 'OK', message: 'Stock Market Platform API is running' });
});

app.get('/api/stocks', (req: Request, res: Response) => {
    res.json({
        data: [
            { symbol: 'AAPL', name: 'Apple Inc.', price: 175.50, change: 1.2, changePercent: 0.68 },
            { symbol: 'MSFT', name: 'Microsoft', price: 330.25, change: -0.5, changePercent: -0.15 },
            { symbol: 'NVDA', name: 'Nvidia', price: 450.80, change: 2.1, changePercent: 0.46 },
            { symbol: 'TSLA', name: 'Tesla Inc.', price: 215.30, change: 5.4, changePercent: 2.57 },
        ]
    });
});

// Real-time AI Sentiment Analysis via Gemini API + Python NLP Backend
app.get('/api/ai/sentiment/:symbol', async (req: Request, res: Response) => {
    const symbol = (req.params.symbol as string).toUpperCase();
    try {
        let pythonData = null;
        try {
            // Fetch real NLP data from our Python Flask Data Pipeline (port 5000)
            const pyRes = await axios.get(`http://127.0.0.1:5000/api/sentiment?ticker=${symbol}`, { timeout: 10000 });
            pythonData = pyRes.data;
        } catch(e) {
            console.error("Warning: Python backend unreachable. Using generic logic.", e);
        }

        const apiKey = process.env.GEMINI_API_KEY || "DUMMY_KEY";
        
        let sentimentText = "";
        
        if (apiKey !== "DUMMY_KEY") {
            const genAI = new GoogleGenerativeAI(apiKey);
            const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

            let prompt = `You are a top-tier financial analyst. Write a highly analytical, 3 sentence real-time sentiment analysis for ${symbol} stock based on general market knowledge. Keep it professional, objective, and dense with financial terminology. DO NOT mention you are AI.`;
            
            if (pythonData && pythonData.avg_compound !== undefined) {
                 prompt = `You are a top-tier financial analyst. We have just scraped recent news for ${symbol}. The NLP VADER sentiment metrics are: Average Compound Score: ${pythonData.avg_compound} (where >0 is positive), Total Recent Articles: ${pythonData.headline_count}, Sentiment Breadth: ${pythonData.breadth}%. Base your highly analytical, 3 sentence real-time sentiment analysis specifically on these data points and general market knowledge. Keep it professional, objective, and dense with financial terminology. DO NOT mention you are AI. Also mention the news impact based on these metrics.`;
            }

            const result = await model.generateContent(prompt);
            sentimentText = result.response.text();
        } else {
            // Fallback
             if (pythonData && pythonData.avg_compound !== undefined) {
                 const isPos = pythonData.avg_compound > 0;
                 sentimentText = `Analysis of ${pythonData.headline_count} recent news articles for ${symbol} reveals a ${isPos ? 'bullish' : 'bearish'} posture with a compound score of ${pythonData.avg_compound}. The sentiment breadth sits at ${pythonData.breadth}%, signaling ${isPos ? 'strong accumulation and positive news flow' : 'distribution and negative headwinds'} in the near term. Algorithmic news interpretation suggests standard standard deviation volatility.`;
             } else {
                 sentimentText = `${symbol} is exhibiting robust relative strength amidst a broader macroeconomic rotation. Institutional accumulation remains evident, as technical indicators suggest a solid support base forming above key moving averages. Volatility expectations are muted, indicating sustained bullish momentum in the near term.`;
             }
        }

        res.json({ 
            analysis: sentimentText,
            metrics: pythonData // Pass raw metrics to frontend 
        });
    } catch (error) {
        console.error("AI Error:", error);
        res.status(500).json({ analysis: "System is experiencing high volume. AI analysis temporarily unavailable.", metrics: null });
    }
});

// Mock OHLC for TradingView chart integration
app.get('/api/stocks/:symbol/chart', (req: Request, res: Response) => {
    const symbol = req.params.symbol as string;
    const range = req.query.range as string || '1M';
    const data = [];
    let currentPrice = 150 + Math.random() * 50;
    
    // Determine how many data points based on timeframe
    let daysToGenerate = 30; // 1M default
    if(range === '1D') daysToGenerate = 1; // normally intraday, but we'll mock 1 candle for now to avoid breaking interval logic easily
    if(range === '1W') daysToGenerate = 7;
    if(range === '3M') daysToGenerate = 90;
    if(range === '1Y') daysToGenerate = 365;
    if(range === '5Y') daysToGenerate = 1825;

    // Generate days of mock data
    const now = new Date();
    // Start X days ago
    let current = new Date(now.getTime() - daysToGenerate * 24 * 60 * 60 * 1000);
    
    for (let i = 0; i < daysToGenerate; i++) {
        const volatility = currentPrice * 0.02; 
        const open = currentPrice;
        const close = open + (Math.random() * volatility - volatility / 2);
        const high = Math.max(open, close) + Math.random() * (volatility / 2);
        const low = Math.min(open, close) - Math.random() * (volatility / 2);
        
        data.push({
            time: current.toISOString().split('T')[0], // YYYY-MM-DD
            open: parseFloat(open.toFixed(2)),
            high: parseFloat(high.toFixed(2)),
            low: parseFloat(low.toFixed(2)),
            close: parseFloat(close.toFixed(2)),
            value: parseFloat(close.toFixed(2)) // for line charts
        });
        
        currentPrice = close;
        current.setDate(current.getDate() + 1);
    }

    res.json({ symbol: symbol.toUpperCase(), data });
});

app.listen(PORT, () => {
    console.log(`[Backend API] Server is running on http://localhost:${PORT}`);
});
