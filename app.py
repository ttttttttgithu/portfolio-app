import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("📊 Portfolio Analyzer")

# -------------------------
# CACHE
# -------------------------
@st.cache_data(ttl=600)
def get_data(ticker, period="3mo"):
    try:
        df = yf.download(ticker, period=period, progress=False)
        return df
    except:
        return pd.DataFrame()

# -------------------------
# ASSETS
# -------------------------
stocks = [
"AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","BRK-B","JPM","JNJ",
"V","PG","UNH","HD","MA","DIS","ADBE","NFLX","KO","PEP",
"XOM","CVX","ABBV","MRK","PFE"
]

crypto = [
"BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD","ADA-USD","DOGE-USD",
"MATIC-USD","LTC-USD","TRX-USD","AVAX-USD","SHIB-USD","LINK-USD",
"ATOM-USD","XLM-USD","ETC-USD","FIL-USD","HBAR-USD","EGLD-USD",
"XTZ-USD","THETA-USD","AAVE-USD","EOS-USD","NEO-USD","KSM-USD"
]

bonds = [
"TLT","IEF","SHY","BND","AGG","LQD","HYG","TIP","MUB","VGIT",
"VCIT","VCSH","BLV","BSV","SCHZ","SPTL","SPSB","IGSB","FLOT",
"USIG","TFLO","VTIP","BIV","TLH","EDV"
]

tickers = stocks + crypto + bonds

# -------------------------
# MARKET OVERVIEW (ROBUST)
# -------------------------

rows = []

for t in tickers:
    df_t = get_data(t)

    if df_t.empty or "Close" not in df_t:
        continue

    close = df_t["Close"].dropna()

    if len(close) < 22:
        continue

    try:
        price = float(close.iloc[-1])
        r1d = (close.iloc[-1] / close.iloc[-2] - 1) * 100
        r1w = (close.iloc[-1] / close.iloc[-6] - 1) * 100
        r1m = (close.iloc[-1] / close.iloc[-22] - 1) * 100
    except:
        continue

    asset_type = "Stock" if t in stocks else ("Crypto" if t in crypto else "Bond")

    rows.append({
        "Ticker": t,
        "Price": price,
        "1D %": r1d,
        "1W %": r1w,
        "1M %": r1m,
        "Asset Type": asset_type
    })

df = pd.DataFrame(rows)

st.subheader("📈 Market Overview")
st.dataframe(df)

# -------------------------
# PORTFOLIO INPUT
# -------------------------

st.subheader("💼 Add Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

col1, col2, col3 = st.columns(3)

with col1:
    ticker = st.text_input("Ticker").strip().upper()

with col2:
    date = st.date_input("Buy Date")

with col3:
    quantity = st.number_input("Quantity", min_value=0.0)

if st.button("Add Asset"):
    if ticker and quantity > 0:
        st.session_state.portfolio.append({
            "ticker": ticker,
            "date": pd.to_datetime(date),
            "quantity": quantity
        })

portfolio = st.session_state.portfolio

# -------------------------
# PORTFOLIO CALC
# -------------------------

valid_assets = []

for asset in portfolio:
    t = asset["ticker"]
    d = asset["date"]

    df_t = get_data(t, period="1y")

    if df_t.empty:
        continue

    df_t = df_t.reset_index()
    df_t["diff"] = (df_t["Date"] - d).abs()

    try:
        buy_price = float(df_t.loc[df_t["diff"].idxmin()]["Close"])
        current_price = float(df_t["Close"].dropna().iloc[-1])
    except:
        continue

    value = current_price * asset["quantity"]
    cost = buy_price * asset["quantity"]

    asset["value"] = value
    asset["cost"] = cost

    valid_assets.append(asset)

# -------------------------
# RESULTS
# -------------------------

if valid_assets:

    total_value = sum(a["value"] for a in valid_assets)
    total_cost = sum(a["cost"] for a in valid_assets)

    pnl = total_value - total_cost
    pnl_pct = (pnl / total_cost) * 100 if total_cost else 0

    st.subheader("📊 Portfolio Summary")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Value", f"${total_value:,.2f}")
    c2.metric("PnL", f"${pnl:,.2f}")
    c3.metric("PnL %", f"{pnl_pct:.2f}%")

    # PIE
    weights = [a["value"]/total_value for a in valid_assets]

    fig, ax = plt.subplots()
    ax.pie(weights, labels=[a["ticker"] for a in valid_assets], autopct='%1.1f%%')
    st.pyplot(fig)

else:
    st.warning("Portfolio boş veya veri yok")
