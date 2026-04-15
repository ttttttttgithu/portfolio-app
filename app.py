import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📊 Portfolio Analyzer")

# -------------------------
# MARKET DATA
# -------------------------
tickers = ["AAPL", "MSFT", "BTC-USD", "ETH-USD"]

data = yf.download(tickers, start="2020-01-01", progress=False)

if not data.empty:
    close_prices = data["Close"]

    st.subheader("📈 Market Overview")
    st.dataframe(close_prices.tail())

# -------------------------
# PORTFOLIO INPUT
# -------------------------
st.subheader("💼 Add Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

ticker = st.text_input("Ticker (örn: AAPL)").upper()
date = st.date_input("Buy Date")
quantity = st.number_input("Quantity", min_value=0.0)

if st.button("Add Asset"):
    if ticker != "" and quantity > 0:
        st.session_state.portfolio.append({
            "ticker": ticker,
            "date": pd.to_datetime(date),
            "quantity": quantity
        })
        st.success("Asset eklendi!")

portfolio = st.session_state.portfolio

# -------------------------
# SAFE PRICE FUNCTION 🔥
# -------------------------
def get_price(df):
    try:
        close = df["Close"]

        # Eğer DataFrame gelirse (multi index)
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        close = close.dropna()

        if len(close) == 0:
            return None

        return float(close.iloc[0])

    except:
        return None

# -------------------------
# CALCULATIONS
# -------------------------
valid_assets = []

for asset in portfolio:
    ticker = asset["ticker"]
    date = asset["date"]

    try:
        # BUY PRICE
        data = yf.download(
            ticker,
            start=date,
            end=date + pd.Timedelta(days=10),
            progress=False
        )

        if data.empty:
            data = yf.download(ticker, period="1mo", progress=False)

        buy_price = get_price(data)

        # CURRENT PRICE
        current_data = yf.download(ticker, period="1d", progress=False)

        if current_data.empty:
            current_data = yf.download(ticker, period="5d", progress=False)

        current_price = get_price(current_data)

        if buy_price is None or current_price is None:
            continue

        value = current_price * asset["quantity"]
        cost = buy_price * asset["quantity"]

        valid_assets.append({
            "ticker": ticker,
            "buy_price": buy_price,
            "current_price": current_price,
            "value": value,
            "cost": cost
        })

    except Exception as e:
        st.write(f"Hata ({ticker}):", e)
        continue

# -------------------------
# RESULTS
# -------------------------
if len(valid_assets) > 0:

    total_value = sum(a["value"] for a in valid_assets)
    total_cost = sum(a["cost"] for a in valid_assets)

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    st.subheader("📊 Portfolio Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Value", f"${total_value:,.2f}")
    col2.metric("PnL ($)", f"${total_pnl:,.2f}")
    col3.metric("PnL (%)", f"{total_pnl_pct:.2f}%")

    # PIE
    for a in valid_assets:
        a["weight"] = a["value"] / total_value

    labels = [a["ticker"] for a in valid_assets]
    sizes = [a["weight"] for a in valid_assets]

    fig1, ax1 = plt.subplots(figsize=(4,4))
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%')
    st.pyplot(fig1)

    # PERFORMANCE
    tickers = [a["ticker"] for a in valid_assets]

    price_data = yf.download(tickers, period="1y", progress=False)["Close"]

    if isinstance(price_data, pd.Series):
        price_data = price_data.to_frame()

    portfolio_value = price_data.copy()

    for a in valid_assets:
        if a["ticker"] in portfolio_value.columns:
            qty = a["value"] / a["current_price"]
            portfolio_value[a["ticker"]] *= qty

    portfolio_value["Total"] = portfolio_value.sum(axis=1)

    norm = portfolio_value["Total"] / portfolio_value["Total"].iloc[0] * 100

    fig2, ax2 = plt.subplots(figsize=(6,3))
    ax2.plot(norm)
    ax2.set_title("Portfolio Performance")
    st.pyplot(fig2)

    # RISK
    returns = price_data.pct_change().dropna()

    returns = returns[[a["ticker"] for a in valid_assets]]
    weights = np.array([a["weight"] for a in valid_assets])

    expected_return = float(np.dot(weights, returns.mean()) * 252)
    variance = float(np.dot(weights, np.dot(returns.cov(), weights)) * 252)
    std_dev = np.sqrt(variance)

    st.subheader("📉 Risk Metrics")
    st.write(f"Expected Return: {expected_return:.2%}")
    st.write(f"Volatility: {std_dev:.2%}")

else:
    st.warning("Geçerli veri yok. Ticker doğru mu kontrol et.")
