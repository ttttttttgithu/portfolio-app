import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Portfolio Analyzer", layout="wide")
st.title("📊 Portfolio Analyzer")

# -------------------------
# MARKET DATA
# -------------------------
stocks = ["AAPL", "MSFT"]
crypto = ["BTC-USD", "ETH-USD"]
bonds = ["TLT", "IEF"]

tickers = stocks + crypto + bonds

data = yf.download(tickers, start="2020-01-01", progress=False)

if "Close" not in data:
    st.error("Market data alınamadı")
    st.stop()

close_prices = data["Close"]

latest_prices = close_prices.iloc[-1]
returns_1d = close_prices.pct_change(1).iloc[-1] * 100
returns_1w = close_prices.pct_change(5).iloc[-1] * 100
returns_1m = close_prices.pct_change(21).iloc[-1] * 100

df = pd.DataFrame({
    "Price": latest_prices,
    "1D %": returns_1d,
    "1W %": returns_1w,
    "1M %": returns_1m,
})

df["Asset Type"] = df.index.map(
    lambda x: "Stock" if x in stocks else ("Crypto" if x in crypto else "Bond")
)

df = df.reset_index().rename(columns={"index": "Ticker"})

st.subheader("📈 Market Overview")
st.dataframe(df, use_container_width=True)

# -------------------------
# PORTFOLIO INPUT
# -------------------------
st.subheader("💼 Add Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

col1, col2, col3 = st.columns(3)

with col1:
    ticker = st.text_input("Ticker")

with col2:
    date = st.date_input("Buy Date")

with col3:
    quantity = st.number_input("Quantity", min_value=0.0)

if st.button("Add Asset"):
    if ticker != "" and quantity > 0:
        st.session_state.portfolio.append({
            "ticker": ticker.upper(),
            "date": str(date),
            "quantity": quantity
        })
        st.success("✅ Asset eklendi!")
    else:
        st.warning("Ticker boş olamaz ve quantity > 0 olmalı")

portfolio = st.session_state.portfolio

# -------------------------
# SHOW PORTFOLIO
# -------------------------
st.subheader("📋 Current Portfolio")

if len(portfolio) > 0:
    st.dataframe(pd.DataFrame(portfolio), use_container_width=True)
else:
    st.info("Henüz asset eklenmedi.")

# -------------------------
# CALCULATIONS
# -------------------------
valid_assets = []

for asset in portfolio:
    ticker = asset["ticker"]
    date = asset["date"]

    try:
        data = yf.download(
            ticker,
            start=date,
            end=pd.to_datetime(date) + pd.Timedelta(days=5),
            progress=False
        )
    except:
        data = pd.DataFrame()

    if data.empty or "Close" not in data:
        continue

    try:
        buy_price = float(data["Close"].iloc[0])
    except:
        continue

    current_data = yf.download(ticker, period="1d", progress=False)

    if current_data.empty or "Close" not in current_data:
        continue

    current_price = float(current_data["Close"].iloc[-1])

    current_value = current_price * asset["quantity"]
    cost = buy_price * asset["quantity"]

    asset["buy_price"] = buy_price
    asset["current_price"] = current_price
    asset["value"] = current_value
    asset["cost"] = cost

    valid_assets.append(asset)

# -------------------------
# PORTFOLIO METRICS
# -------------------------
if len(valid_assets) > 0:

    total_value = float(sum(a["value"] for a in valid_assets))
    total_cost = float(sum(a["cost"] for a in valid_assets))

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0

    st.subheader("📊 Portfolio Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Value", f"${total_value:,.2f}")
    col2.metric("PnL ($)", f"${total_pnl:,.2f}")
    col3.metric("PnL (%)", f"{total_pnl_pct:.2f}%")

    # -------------------------
    # WEIGHTS
    # -------------------------
    for a in valid_assets:
        a["weight"] = a["value"] / total_value

    # -------------------------
    # PIE CHART
    # -------------------------
    labels = [a["ticker"] for a in valid_assets]
    sizes = [a["weight"] for a in valid_assets]

    fig1, ax1 = plt.subplots()
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%')
    ax1.set_title("Portfolio Distribution")
    st.pyplot(fig1)

    # -------------------------
    # PRICE DATA
    # -------------------------
    tickers = [a["ticker"] for a in valid_assets]
    start_date = min(a["date"] for a in valid_assets)

    price_data = yf.download(tickers, start=start_date, progress=False)["Close"]

    if isinstance(price_data, pd.Series):
        price_data = price_data.to_frame()

    portfolio_value = pd.DataFrame(index=price_data.index)

    for a in valid_assets:
        if a["ticker"] in price_data.columns:
            portfolio_value[a["ticker"]] = price_data[a["ticker"]] * a["quantity"]

    portfolio_value["Total"] = portfolio_value.sum(axis=1)

    # -------------------------
    # S&P500
    # -------------------------
    sp500 = yf.download("^GSPC", start=start_date, progress=False)["Close"]

    portfolio_norm = portfolio_value["Total"] / portfolio_value["Total"].iloc[0] * 100
    sp500_norm = sp500 / sp500.iloc[0] * 100

    fig2, ax2 = plt.subplots()
    ax2.plot(portfolio_norm, label="Portfolio")
    ax2.plot(sp500_norm, label="S&P 500")
    ax2.legend()
    ax2.set_title("Portfolio vs S&P 500")
    st.pyplot(fig2)

    # -------------------------
    # RETURNS
    # -------------------------
    returns = price_data.pct_change().dropna()

    weights = np.array([a["weight"] for a in valid_assets])
    returns = returns[[a["ticker"] for a in valid_assets]]

    mean_returns = returns.mean()
    expected_return = np.dot(weights, mean_returns) * 252

    cov_matrix = returns.cov()
    variance = np.dot(weights, np.dot(cov_matrix, weights)) * 252
    std_dev = np.sqrt(variance)

    st.subheader("📉 Risk Metrics")
    st.write(f"Expected Return: {expected_return:.2%}")
    st.write(f"Volatility: {std_dev:.2%}")

    # -------------------------
    # ALPHA BETA CAPM
    # -------------------------
    sp500_returns = sp500.pct_change().dropna()
    portfolio_returns = portfolio_value["Total"].pct_change().dropna()

    portfolio_returns, sp500_returns = portfolio_returns.align(sp500_returns, join='inner')

    if len(portfolio_returns) > 0:
        cov_matrix = np.cov(portfolio_returns, sp500_returns)

        beta = cov_matrix[0][1] / cov_matrix[1][1]

        risk_free_rate = 0.02
        market_return = sp500_returns.mean() * 252

        alpha = expected_return - (risk_free_rate + beta * (market_return - risk_free_rate))
        capm_return = risk_free_rate + beta * (market_return - risk_free_rate)

        st.subheader("📊 Advanced Metrics")

        col1, col2, col3 = st.columns(3)
        col1.metric("Beta", f"{beta:.2f}")
        col2.metric("Alpha", f"{alpha:.2%}")
        col3.metric("CAPM Return", f"{capm_return:.2%}")

    # -------------------------
    # CUMULATIVE RETURNS
    # -------------------------
    returns_pct = portfolio_value["Total"].pct_change().fillna(0)
    cumulative_returns = (1 + returns_pct).cumprod() * 100

    fig3, ax3 = plt.subplots()
    ax3.plot(cumulative_returns, label="Portfolio (%)")
    ax3.set_title("Cumulative Return")
    ax3.legend()
    st.pyplot(fig3)

    # -------------------------
    # INFLATION ADJUSTED
    # -------------------------
    inflation_rate = 0.03
    daily_inflation = (1 + inflation_rate) ** (1/252) - 1

    inflation_series = (1 + daily_inflation) ** np.arange(len(cumulative_returns))
    real_returns = cumulative_returns / inflation_series

    fig4, ax4 = plt.subplots()
    ax4.plot(real_returns, label="Real Return")
    ax4.legend()
    ax4.set_title("Inflation Adjusted Return")
    st.pyplot(fig4)

    # -------------------------
    # COMBINED
    # -------------------------
    fig5, ax5 = plt.subplots()
    ax5.plot(cumulative_returns, label="Portfolio (Nominal)")
    ax5.plot(real_returns, label="Portfolio (Real)")
    ax5.plot(sp500_norm, label="S&P 500")
    ax5.legend()
    ax5.set_title("Portfolio vs Market vs Inflation")
    st.pyplot(fig5)

else:
    st.warning("Geçerli veri yok veya henüz hesaplanamadı.")
