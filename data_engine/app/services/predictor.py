import pandas_datareader.data as web
import pandas as pd
from datetime import datetime, timedelta
import io
import base64
from prophet import Prophet
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def generate_forecast_chart(df, forecast, ticker):
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Plot historical data
    ax.plot(df['ds'], df['y'], label='Historical Price', color='#3b82f6', linewidth=2)
    
    # Plot forecast trend
    ax.plot(forecast['ds'], forecast['yhat'], label='Forecast Trend', color='#22c55e', linestyle='--', linewidth=2)
    
    # Plot confidence interval
    ax.fill_between(forecast['ds'], forecast['yhat_lower'], forecast['yhat_upper'], color='#22c55e', alpha=0.2, label='Confidence Interval')
    
    ax.set_title(f"{ticker} AI Price Forecast (Prophet Model)", color='w', fontsize=14)
    ax.set_ylabel("Price (USD)", color='w')
    ax.tick_params(colors='w')
    ax.grid(color='#374151', linestyle='--', linewidth=0.5)
    
    # Styling to match the theme
    fig.patch.set_facecolor('#0E1525')
    ax.set_facecolor('#0E1525')
    for spine in ax.spines.values():
        spine.set_color('#374151')
        
    ax.legend(facecolor='#1f2937', edgecolor='#374151', labelcolor='w')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def predict_stock_price(ticker, days=90):
    try:
        # 1. Fetch historical data (last 2 years is usually good for Prophet)
        end_date = datetime.today()
        start_date = end_date - timedelta(days=2 * 365)
        
        data = web.DataReader(ticker, 'stooq', start=start_date, end=end_date)
        if data.empty:
            raise ValueError(f"Could not load data for {ticker}")
            
        data = data.sort_index()
        
        # 2. Prepare data for Prophet
        # Prophet requires columns 'ds' (datestamp) and 'y' (numeric value)
        df_prophet = data[['Close']].reset_index()
        df_prophet.rename(columns={'Date': 'ds', 'Close': 'y'}, inplace=True)
        # remove timezone if any
        df_prophet['ds'] = df_prophet['ds'].dt.tz_localize(None)

        # 3. Train Prophet Model
        m = Prophet(daily_seasonality=False, yearly_seasonality=True, weekly_seasonality=True, changepoint_prior_scale=0.05)
        m.fit(df_prophet)
        
        # 4. Make Future Predictions
        future = m.make_future_dataframe(periods=days)
        # Tidy up future dataframe to skip weekends (stock market closed)
        future = future[future['ds'].dt.dayofweek < 5]
        forecast = m.predict(future)
        
        # Extract the prediction part only
        last_hist_date = df_prophet['ds'].max()
        future_forecast = forecast[forecast['ds'] > last_hist_date]
        
        if future_forecast.empty:
             raise ValueError("Failed to generate future dates")
             
        # Calculate expected change
        current_price = df_prophet.iloc[-1]['y']
        predicted_price = future_forecast.iloc[-1]['yhat']
        change_pct = ((predicted_price - current_price) / current_price) * 100
        
        # Determine logical Recommendation
        recommendation = "HOLD"
        confidence = "Neutral"
        
        if change_pct > 5:
            recommendation = "BUY"
            confidence = "Bullish Outlook"
            if change_pct > 15:
                recommendation = "STRONG BUY"
                
        elif change_pct < -5:
            recommendation = "SELL"
            confidence = "Bearish Outlook"
            if change_pct < -15:
                recommendation = "STRONG SELL"
                
        # 5. Generate Chart
        chart_base64 = generate_forecast_chart(df_prophet, forecast, ticker)
        
        return {
            "success": True,
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "predicted_price_90d": round(predicted_price, 2),
            "change_pct": round(change_pct, 2),
            "recommendation": recommendation,
            "confidence": confidence,
            "chart": chart_base64
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }
