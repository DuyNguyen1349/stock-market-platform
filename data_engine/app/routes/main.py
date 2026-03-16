from flask import Blueprint, request, render_template, current_app, jsonify
from datetime import datetime, date
import hashlib

from app.services.snapshot import load_snapshot, save_snapshot
from app.services.news import fetch_news_multi
from app.services.sentiment import score_sentiment
from app.charts import (
    chart_line_per_headline,
    chart_source_weighted_bar,
    chart_distribution_hist,
    chart_pie_composition,
    chart_sentiment_breadth,
    chart_wordcloud,
    chart_wordcount,
    chart_daily_stacked
)
from app import cache

bp = Blueprint('main', __name__)

# Cache generating function based on key
def generate_cache_key():
    ticker = request.form.get("ticker", "AAPL").strip().upper() if request.method == "POST" else "AAPL"
    start = request.form.get("start", (date.today().replace(day=1)).isoformat()) if request.method == "POST" else (date.today().replace(day=1)).isoformat()
    end = request.form.get("end", date.today().isoformat()) if request.method == "POST" else date.today().isoformat()
    key = f"{ticker}_{start}_{end}"
    return hashlib.md5(key.encode('utf-8')).hexdigest()

@bp.route("/", methods=["GET", "POST"])
def home():
    # --------- defaults ----------
    ticker = request.args.get("ticker", "AAPL").strip().upper()
    iframe_mode = request.args.get("iframe", "0") == "1"
    theme = request.args.get("theme", "dark")
    
    today = date.today()
    start = (today.replace(day=1)).isoformat()
    end = today.isoformat()

    # --------- xử lý form ----------
    if request.method == "POST":
        ticker = request.form.get("ticker", "AAPL").strip().upper()
        start = request.form.get("start", start)
        end = request.form.get("end", end)

    # --------- parse sang date ----------
    try:
        s_date = datetime.fromisoformat(start).date()
    except Exception:
        s_date = None
    try:
        e_date = datetime.fromisoformat(end).date()
    except Exception:
        e_date = None

    # --------- Caching Data ---------
    cache_key = f"sentiment_data_{ticker}_{start}_{end}"
    data_cache = cache.get(cache_key)

    if data_cache:
        df = data_cache['df']
        rows = data_cache['rows']
    else:
        # Load snapshot logic
        snap = load_snapshot(ticker, start, end)
        if snap is None:
            rows = fetch_news_multi(
                [ticker],
                start_date=s_date,
                end_date=e_date,
                limit=365,
                use_finviz=False     
            )

            # Deduplication
            seen = set()
            dedup_rows = []
            for r in rows:
                key = (r.get("ticker", "").upper(), (r.get("title", "")).casefold())
                if key in seen: continue
                seen.add(key)
                dedup_rows.append(r)
            rows = dedup_rows
            
            # Save local json backup if necessary
            snap = save_snapshot(ticker, start, end, rows)
        else:
            rows = snap["rows"]

        # chấm điểm sentiment - Heavy operation
        df = score_sentiment(rows)
        # Store df and rows to cache for 1 hour
        cache.set(cache_key, {'df': df, 'rows': rows}, timeout=3600)

    # Filter dataframe
    if not df.empty:
        df = df[
            (df["date"] >= datetime.fromisoformat(start).date()) &
            (df["date"] <= datetime.fromisoformat(end).date())
        ]

    # ===== KPI HEADER =====
    avg_compound = None
    breadth = None
    headline_count = 0
    top_source = "-"
    headlines = []

    if not df.empty:
        sub = df[df["ticker"] == ticker].sort_values("ts", ascending=False).copy()
        headlines = [
            {
                "date": str(r["date"]),
                "time": r["time"],
                "title": r["title"],
                "url": r["url"],
                "compound": float(r["compound"]),
            }
            for _, r in sub.iterrows()
        ]
        if not sub.empty:
            avg_compound = round(float(sub["compound"].mean()), 2)
            pos = (sub["compound"] > 0.05).sum()
            neg = (sub["compound"] < -0.05).sum()
            n   = len(sub)
            breadth = round((pos - neg) / max(1, n) * 100, 1)
            headline_count = n

            src_col = "publisher" if "publisher" in sub.columns else ("source" if "source" in sub.columns else None)
            if src_col is not None and not sub[src_col].dropna().empty:
                top_source = (
                    sub[src_col]
                    .astype(str).str.strip().str.lower()
                    .replace({"yahoo":"yahoo finance","wsj":"wall street journal"})
                    .value_counts()
                    .idxmax()
                ).title()

    # --------- Build Charts ----------
    widgets = {"intraday": None}
    if not df.empty:
        widgets["line_headline"] = chart_line_per_headline(df, ticker)
        widgets["dist_hist"]    = chart_distribution_hist(df, ticker)
        widgets["pie_sent"]     = chart_pie_composition(df, ticker)
        widgets["sent_breadth"] = chart_sentiment_breadth(df, ticker)
        widgets["source_avg"] = chart_source_weighted_bar(df, ticker)
        widgets["daily_stacked"] = chart_daily_stacked(df, ticker)
        widgets["wordcloud"] = chart_wordcloud(df, ticker)
        widgets["wordcount"] = chart_wordcount(df, ticker)

    return render_template(
        "dashboard.html",
        ticker=ticker,
        start=start,
        end=end,
        COLOR_SCHEME=current_app.config['COLOR_SCHEME'],
        avg_compound=avg_compound,
        breadth=breadth,
        headline_count=headline_count,
        top_source=top_source,
        headlines=headlines,
        iframe_mode=iframe_mode,
        theme=theme,
        **widgets
    )

@bp.route("/api/sentiment", methods=["GET"])
def api_sentiment():
    ticker = request.args.get("ticker", "AAPL").strip().upper()
    try:
        from app.services.snapshot import load_snapshot, save_snapshot
        from app.services.news import fetch_news_multi
        from app.services.sentiment import score_sentiment
        from app import cache
        from datetime import datetime, date, timedelta

        end = date.today().isoformat()
        start = (date.today() - timedelta(days=30)).isoformat() # 30 days default
        s_date = datetime.fromisoformat(start).date()
        e_date = datetime.fromisoformat(end).date()

        cache_key = f"api_sentiment_{ticker}_{start}_{end}"
        data_cache = cache.get(cache_key)

        if data_cache:
            df = data_cache['df']
        else:
            snap = load_snapshot(ticker, start, end)
            if snap is None:
                rows = fetch_news_multi([ticker], start_date=s_date, end_date=e_date, limit=100, use_finviz=False)
                seen = set()
                dedup_rows = []
                for r in rows:
                    key = (r.get("ticker", "").upper(), (r.get("title", "")).casefold())
                    if key in seen: continue
                    seen.add(key)
                    dedup_rows.append(r)
                rows = dedup_rows
            else:
                rows = snap["rows"]

            df = score_sentiment(rows)
            cache.set(cache_key, {'df': df}, timeout=3600)

        avg_compound = 0
        breadth = 0
        headline_count = 0
        headlines = []

        if not df.empty:
            sub = df[df["ticker"] == ticker].sort_values("ts", ascending=False).copy()
            if not sub.empty:
                avg_compound = round(float(sub["compound"].mean()), 2)
                pos = (sub["compound"] > 0.05).sum()
                neg = (sub["compound"] < -0.05).sum()
                n = len(sub)
                breadth = round((float(pos) - float(neg)) / max(1, n) * 100, 1)
                headline_count = n
                
                # Get latest 5 headlines
                for _, r in sub.head(5).iterrows():
                    headlines.append({
                        "date": str(r["date"]),
                        "title": r["title"],
                        "compound": float(r["compound"])
                    })

        # Calculate a text logic for Gemini wrapper
        sentiment_label = "Neutral"
        if avg_compound > 0.1: sentiment_label = "Bullish"
        if avg_compound < -0.1: sentiment_label = "Bearish"

        return jsonify({
            "ticker": ticker,
            "avg_compound": avg_compound,
            "breadth": breadth,
            "headline_count": headline_count,
            "sentiment_label": sentiment_label,
            "recent_news": headlines
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/api/portfolio/optimize", methods=["POST", "OPTIONS"])
def api_portfolio_optimize():
    if request.method == "OPTIONS":
        return jsonify({}), 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        tickers = data.get("tickers", [])
        initial_capital = data.get("initial_capital", 10000)
        risk_free_rate = data.get("risk_free_rate", 0.02)
        
        if not tickers:
            return jsonify({"error": "List of tickers is required"}), 400
            
        from app.services.portfolio_optimizer import run_portfolio_optimization
        
        result = run_portfolio_optimization(tickers, initial_capital, risk_free_rate)
        
        if not result.get("success"):
            return jsonify(result), 500
            
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error in portfolio optimization: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
@bp.route("/api/predict", methods=["POST", "OPTIONS"])
def api_predict_stock():
    if request.method == "OPTIONS":
        return jsonify({}), 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        ticker = data.get("ticker", "").strip().upper()
        if not ticker:
            return jsonify({"error": "Ticker is required"}), 400
            
        from app.services.predictor import predict_stock_price
        
        result = predict_stock_price(ticker, days=90)
        
        if not result.get("success"):
            return jsonify(result), 500
            
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error in predicting stock: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors
    if isinstance(e, getattr(current_app, 'HTTPException', type(None))):
        return e
    # Non-HTTP errors map to 500
    current_app.logger.error(f"Error handling request: {e}", exc_info=True)
    return render_template("error.html", error_message=str(e)), 500
