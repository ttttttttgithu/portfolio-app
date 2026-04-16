import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📊 Portfolio Analyzer")

# =====================================================
# 🟢 1. MANUAL PORTFOLIO (STABLE)
# =====================================================
st.subheader("🛠️ Manual Portfolio Builder")

if "manual_assets" not in st.session_state:
    st.session_state.manual_assets = []

with st.form("manual_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)

    name = col1.text_input("Asset Name")
    price = col2.number_input("Buy Price", min_value=0.0)
    qty = col3.number_input("Quantity", min_value=0.0)

    add = st.form_submit_button("Add Asset")

    if add:
        if name and price > 0 and qty > 0:
            st.session_state.manual_assets.append({
                "Asset": name.upper(),
                "Price": price,
                "Quantity": qty
            })

# DISPLAY MANUAL
if len(st.session_state.manual_assets) > 0:
    df_manual = pd.DataFrame(st.session_state.manual_assets)
    df_manual["Value"] = df_manual["Price"] * df_manual["Quantity"]

    st.markdown("### 📋 Manual Portfolio")
    st.dataframe(df_manual, use_container_width=True)

    total_val = df_manual["Value"].sum()
    st.metric("Total Value", f"${total_val:,.2f}")

    fig, ax = plt.subplots()
    ax.pie(df_manual["Value"], labels=df_manual["Asset"], autopct="%1.1f%%")
    ax.set_title("Allocation")
    st.pyplot(fig)

# =====================================================
# 🟢 2. MARKET OVERVIEW (FAST & STABLE)
# =====================================================
st.subheader("📈 Market Overview")

tickers = ["AAPL","MSFT","GOOGL","AMZN","TSLA","BTC-USD","ETH-USD","TLT","GLD"]

data = {}

for t in tickers:
    try:
        df = yf.download(t, period="1mo", progress=False)["Close"]
        if not df.empty:
            data[t] = df
    except:
        pass

if data:
    prices = pd.DataFrame(data)
    latest = prices.iloc[-1]
    change = prices.pct_change().iloc[-1] * 100

    overview = pd.DataFrame({
        "Price": latest,
        "1D %": change
    })

    st.dataframe(overview, use_container_width=True)

# =====================================================
# 🟢 3. REAL PORTFOLIO (ORIGINAL LOGIC SIMPLIFIED)
# =====================================================
st.subheader("💼 Portfolio (Live Data)")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

with st.form("portfolio_form", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)

    ticker = c1.text_input("Ticker").upper()
    date = c2.date_input("Buy Date")
    qty = c3.number_input("Quantity", min_value=0.0)

    add = st.form_submit_button("Add")

    if add:
        if ticker and qty > 0:
            st.session_state.portfolio.append({
                "ticker": ticker,
                "date": pd.to_datetime(date),
                "qty": qty
            })

# CALCULATE
results = []

for a in st.session_state.portfolio:
    try:
        hist = yf.download(a["ticker"], period="1y", progress=False)["Close"]

        if hist.empty:
            continue

        buy_price = hist.loc[hist.index >= a["date"]].iloc[0]
        current_price = hist.iloc[-1]

        value = current_price * a["qty"]
        cost = buy_price * a["qty"]

        results.append({
            "Ticker": a["ticker"],
            "Value": value,
            "Cost": cost
        })

    except:
        continue

# DISPLAY
if results:
    df = pd.DataFrame(results)

    total_value = df["Value"].sum()
    total_cost = df["Cost"].sum()

    pnl = total_value - total_cost

    st.metric("Total Value", f"${total_value:,.2f}")
    st.metric("PnL", f"${pnl:,.2f}")

    weights = df["Value"] / total_value

    fig, ax = plt.subplots()
    ax.pie(weights, labels=df["Ticker"], autopct="%1.1f%%")
    st.pyplot(fig)

else:
    st.info("Henüz portfolio eklenmedi.")
