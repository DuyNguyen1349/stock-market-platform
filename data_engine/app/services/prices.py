# app/services/prices.py
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf

def _one_price_df(ticker: str, days=30) -> pd.DataFrame:
    end = datetime.now()
    start = end - timedelta(days=days)
    df = yf.download(ticker, start=start.date(), end=end.date(), progress=False, threads=False)
    if df.empty:
        print(f"[WARN] No price data for {ticker}")
        return pd.DataFrame()
    df = df.rename_axis("date").reset_index()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["Return"] = df["Close"].pct_change()
    return df[["date","Close","Return"]]

def get_prices(tickers: list[str], days=30) -> dict[str, pd.DataFrame]:
    return {t:_one_price_df(t, days=days) for t in tickers}
