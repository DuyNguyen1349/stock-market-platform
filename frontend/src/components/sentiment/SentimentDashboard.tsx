import React, { useRef, useEffect, useState } from 'react';

export default function SentimentDashboard({ symbol }: { symbol: string }) {
    const iframeRef = useRef<HTMLIFrameElement>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        if (iframeRef.current) {
            // Passing iframe=1 hides the Python specific header and margin
            // Passing theme=dark forces the dark mode CSS to render immediately
            iframeRef.current.src = `http://localhost:5000/?ticker=${symbol}&iframe=1&theme=dark`;
        }
    }, [symbol]);

    return (
        <div className="w-full h-full min-h-[1400px] bg-[#0f172a] rounded-xl overflow-hidden shadow-lg border border-gray-800 relative">
            {loading && (
                <div className="absolute inset-0 flex items-center justify-center bg-[#0B0E14] z-10">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                </div>
            )}
            <iframe 
                ref={iframeRef}
                onLoad={() => setLoading(false)}
                className="w-full h-full absolute inset-0 border-none"
                title={`Sentiment Analysis Dashboard for ${symbol}`}
            />
        </div>
    );
}
