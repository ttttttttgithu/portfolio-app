import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("📊 Portfolio Analyzer")

# -------------------------
# TICKERS
# -------------------------

stocks = ["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","BRK-B","JPM","JNJ"]
crypto = ["BTC-USD","ETH-USD","SOL-USD"]
bonds = ["TLT","IEF","BND"]

ALL_TICKERS = list(set(stocks + crypto + bonds))

# -------------------------
# SINGLE DATA PIPELINE (MAIN FIX)
# -------------------------

@st.cache_data
def load_data():
    data = yf.download(ALL_TICKERS, period="3mo", group_by="ticker", auto_adjust=True)

    price_dict = {}

    for t in ALL_TICKERS:
        try:
            if t in data:
                df = data[t]["Close"].dropna()
                if not df.empty:
                    price_dict[t] = df
        except:
            continue

    prices = pd.DataFrame(price_dict)

    # 🔥 CRITICAL FIX
    prices = prices.ffill().bfill()

    return prices

prices = load_data()

# -------------------------
# MARKET OVERVIEW
# -------------------------

if not prices.empty:

    latest = prices.iloc[-1]

    returns_1d = prices.pct_change(1).iloc[-1] * 100
    returns_1w = prices.pct_change(5).iloc[-1] * 100
    returns_1m = prices.pct_change(21).iloc[-1] * 100

    market_df = pd.DataFrame({
        "Ticker": prices.columns,
        "Price": latest,
        "1D %": returns_1d,
        "1W %": returns_1w,
        "1M %": returns_1m
    }).reset_index(drop=True)

    market_df["Asset Type"] = market_df["Ticker"].apply(
        lambda x: "Stock" if x in stocks else ("Crypto" if x in crypto else "Bond")
    )

    st.subheader("📈 Market Overview")
    st.dataframe(market_df)

# -------------------------
# PORTFOLIO INPUT
# -------------------------

st.subheader("💼 Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

col1, col2, col3 = st.columns(3)

with col1:
    ticker = st.text_input("Ticker").upper().strip()

with col2:
    date = st.date_input("Buy Date")
    if date > pd.Timestamp.today().date():
        date = pd.Timestamp.today().date()

with col3:
    quantity = st.number_input("Quantity", min_value=0.0)

if st.button("Add Asset"):
    if ticker and quantity > 0:
        st.session_state.portfolio.append({
            "ticker": ticker,
            "date": pd.to_datetime(date),
            "quantity": quantity
        })
        st.success("Added!")

portfolio = st.session_state.portfolio

# -------------------------
# PORTFOLIO CALCULATION (USING SAME DATA)
# -------------------------

valid_assets = []

for asset in portfolio:
    t = asset["ticker"]
    d = asset["date"]

    if t not in prices.columns:
        continue

    series = prices[t].dropna()

    if series.empty:
        continue

    # 🔥 nearest buy date
    nearest_date = series.index.get_indexer([d], method="nearest")[0]
    buy_price = series.iloc[nearest_date]

    current_price = series.iloc[-1]

    value = current_price * asset["quantity"]
    cost = buy_price * asset["quantity"]

    asset["value"] = value
    asset["cost"] = cost

    valid_assets.append(asset)

# -------------------------
# RESULTS
# -------------------------

if len(valid_assets) > 0:

    total_value = sum(a["value"] for a in valid_assets)
    total_cost = sum(a["cost"] for a in valid_assets)

    pnl = total_value - total_cost
    pnl_pct = (pnl / total_cost) * 100 if total_cost > 0 else 0

    st.subheader("📊 Summary")

    c1, c2, c3 = st.columns(3)
    c1.metric("Value", f"${total_value:,.2f}")
    c2.metric("PnL", f"${pnl:,.2f}")
    c3.metric("PnL %", f"{pnl_pct:.2f}%")

    # PIE
    fig, ax = plt.subplots()
    ax.pie(
        [a["value"] for a in valid_assets],
        labels=[a["ticker"] for a in valid_assets],
        autopct="%1.1f%%"
    )
    st.pyplot(fig)

    # PERFORMANCE
    tick_list = [a["ticker"] for a in valid_assets]
    port_prices = prices[tick_list]

    portfolio_series = (port_prices * [a["quantity"] for a in valid_assets]).sum(axis=1)

    sp500 = yf.download("^GSPC", period="3mo")["Close"]

    portfolio_norm = portfolio_series / portfolio_series.iloc[0] * 100
    sp500_norm = sp500 / sp500.iloc[0] * 100

    fig2, ax2 = plt.subplots()
    ax2.plot(portfolio_norm, label="Portfolio")
    ax2.plot(sp500_norm, label="S&P500")
    ax2.legend()
    st.pyplot(fig2)

else:
    st.info("Portföy boş")
