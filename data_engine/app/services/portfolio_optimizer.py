import pandas_datareader.data as web
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend for server
import matplotlib.pyplot as plt
import io
import base64
import requests
from datetime import datetime, timedelta
from pypfopt import expected_returns, risk_models, black_litterman
from pypfopt.black_litterman import BlackLittermanModel
from pypfopt.efficient_frontier import EfficientFrontier
from pypfopt.discrete_allocation import DiscreteAllocation

def get_market_caps_finnhub(tickers, api_key="d6odtjpr01qnu98hmql0d6odtjpr01qnu98hmqlg"):
    mcaps = {}
    for t in tickers:
        url = f"https://finnhub.io/api/v1/stock/profile2?symbol={t}&token={api_key}"
        try:
            res = requests.get(url).json()
            if "marketCapitalization" in res and res["marketCapitalization"]:
                mcaps[t] = float(res["marketCapitalization"])
            else:
                mcaps[t] = 1e9 # fallback
        except Exception:
            mcaps[t] = 1e9
    return mcaps

def get_stock_data(tickers, years=3):
    """
    Tải Adjusted Close price trong 3 năm gần nhất với tần suất daily.
    Loại bỏ NaN và đồng bộ thời gian giữa các cổ phiếu.
    """
    end_date = datetime.today()
    start_date = end_date - timedelta(days=years * 365)
    # stooq returns MultiIndex with (Attributes, Symbols) for multiple tickers
    # The data is descending so we must sort_index()
    data = web.DataReader(tickers, 'stooq', start=start_date, end=end_date)['Close']
    data = data.sort_index()
    
    # Loại bỏ NaN và đồng bộ thời gian
    data = data.dropna(how='all') # Bỏ ngày không có dữ liệu nào
    data = data.ffill().bfill() # Điền khuyết dữ liệu
    
    # Nếu chỉ có 1 ticker, pandas trả về Series, ta cần chuyển thành DataFrame
    if isinstance(data, pd.Series):
         data = data.to_frame()
         data.columns = tickers
         
    return data

def calculate_returns(prices):
    """
    Tính daily returns bằng pandas
    """
    return prices.pct_change().dropna()

def optimize_portfolio(prices, risk_free_rate=0.02):
    """
    Sử dụng PyPortfolioOpt để tính Expected Returns, Covariance Matrix, 
    và tối ưu danh mục theo max_sharpe().
    """
    # Lấy Market Caps từ Finnhub
    mcaps = get_market_caps_finnhub(prices.columns)
    market_caps = {ticker: mcaps[ticker] for ticker in prices.columns}
    
    # Tính Covariance Matrix
    S = risk_models.CovarianceShrinkage(prices).ledoit_wolf()
    
    # Mô hình Black-Litterman Implied Returns (Cap-Weighted)
    # Giả định Risk Aversion của thị trường delta = 2.5
    delta = 2.5
    pi = black_litterman.market_implied_prior_returns(market_caps, risk_aversion=delta, cov_matrix=S)
    
    # Do không có absolute views, lợi nhuận kỳ vọng chính là market implied returns
    rets = pi
    
    # Efficient Frontier tối ưu hóa theo Sharpe Ratio
    # Tính giới hạn tỷ trọng trên mỗi mã để phân bổ rủi ro thực tế hơn (ví dụ: tối đa 40%)
    # Đảm bảo max_weight * n_assets >= 1.0 để có nghiệm khả thi
    n_assets = len(prices.columns)
    max_weight = max(0.40, 1.0 / n_assets) if n_assets > 0 else 1.0
    
    ef = EfficientFrontier(rets, S, weight_bounds=(0, max_weight))
    weights = ef.max_sharpe(risk_free_rate=risk_free_rate)
    
    # Làm sạch tỷ trọng
    cleaned_weights = ef.clean_weights()
    
    # Tính hiệu suất
    expected_annual_return, annual_volatility, sharpe_ratio = ef.portfolio_performance(risk_free_rate=risk_free_rate)
    
    return cleaned_weights, expected_annual_return, annual_volatility, sharpe_ratio, rets, S, ef

def allocate_shares(cleaned_weights, prices, initial_capital):
    """
    Tính số lượng cổ phiếu cần mua dựa trên số vốn ban đầu và giá hiện tại
    """
    latest_prices = prices.iloc[-1]
    
    # Sử dụng DiscreteAllocation để tính chính xác số lượng cổ phiếu mua được
    da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=initial_capital)
    allocation, leftover = da.lp_portfolio()
    
    return allocation, leftover, latest_prices

def display_results_to_charts(cleaned_weights, daily_returns, mu, S, ef):
    """
    Tạo matplotlib chart và chuyển thành base64:
    - Pie chart phân bổ
    - Tiền phân bổ 
    - Cumulative returns
    """
    charts = {}
    
    # 1. Pie Chart 
    fig, ax = plt.subplots(figsize=(8, 8))
    filtered_weights = {k: v for k, v in cleaned_weights.items() if v > 0.001}
    ax.pie(filtered_weights.values(), labels=filtered_weights.keys(), autopct='%1.1f%%', 
           startangle=90, textprops={'color':"w", 'weight':'bold'})
    ax.set_title("Optimal Portfolio Allocation", color='w', fontsize=16)
    fig.patch.set_facecolor('#0E1525') # Match theme
    ax.set_facecolor('#0E1525')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    charts['pie_chart'] = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    # 2. Cumulative Returns
    portfolio_daily_returns = daily_returns.dot(pd.Series(cleaned_weights))
    cumulative_returns = (1 + portfolio_daily_returns).cumprod()
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(cumulative_returns.index, cumulative_returns.values, color='#22c55e', linewidth=2)
    ax.set_title("Portfolio Cumulative Returns (3 Years)", color='w')
    ax.set_ylabel("Cumulative Return", color='w')
    ax.tick_params(colors='w')
    ax.grid(color='#374151', linestyle='--', linewidth=0.5)
    fig.patch.set_facecolor('#0E1525')
    ax.set_facecolor('#0E1525')
    
    for spine in ax.spines.values():
        spine.set_color('#374151')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    charts['cumulative_returns'] = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return charts

def run_portfolio_optimization(tickers, initial_capital, risk_free_rate=0.02):
    """
    Hàm tổng hợp toàn bộ quy trình
    """
    try:
        # 1. Lấy data
        prices = get_stock_data(tickers, years=3)
        if prices.empty:
            raise ValueError("Không thể tải dữ liệu cho các mã cổ phiếu này.")
            
        daily_returns = calculate_returns(prices)
        
        # 2. Optimize
        cleaned_weights, exp_ret, expected_vol, sharpe, mu, S, ef = optimize_portfolio(prices, risk_free_rate)
        
        # 3. Mua cổ phiếu
        allocation, leftover, latest_prices = allocate_shares(cleaned_weights, prices, initial_capital)
        
        # 4. Vẽ biểu đồ
        charts = display_results_to_charts(cleaned_weights, daily_returns, mu, S, ef)
        
        # Format response
        allocation_details = []
        for ticker, shares in allocation.items():
            price = latest_prices[ticker]
            weight = cleaned_weights[ticker] * 100
            total_value = shares * price
            allocation_details.append({
                "ticker": ticker,
                "shares": shares,
                "current_price": round(price, 2),
                "weight_percent": round(weight, 2),
                "total_value": round(total_value, 2)
            })
            
        return {
            "success": True,
            "performance": {
                "expected_annual_return": round(exp_ret * 100, 2),
                "annual_volatility": round(expected_vol * 100, 2),
                "sharpe_ratio": round(sharpe, 2)
            },
            "allocation": allocation_details,
            "leftover_cash": round(leftover, 2),
            "initial_capital": initial_capital,
            "charts": charts
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }
