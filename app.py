import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import matplotlib.pyplot as plt

st.title("📊 Portfolio Analyzer (Debug Version)")

# -------------------------
# DATA FETCH (MULTI SOURCE)
# -------------------------
@st.cache_data(ttl=600)
def get_data(ticker):
    log = ""

    # 1️⃣ yfinance
    try:
        df = yf.download(ticker, period="3mo", progress=False)
        if not df.empty and "Close" in df:
            log += "yfinance OK"
            return df[["Close"]], log
        else:
            log += "yfinance EMPTY -> "
    except Exception as e:
        log += f"yfinance ERROR: {e} -> "

    # 2️⃣ stooq fallback (çok sağlamdır)
    try:
        url = f"https://stooq.com/q/d/l/?s={ticker.lower()}&i=d"
        df = pd.read_csv(url)

        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date")
            df.set_index("Date", inplace=True)
            df.rename(columns={"Close": "Close"}, inplace=True)

            log += "stooq OK"
            return df[["Close"]], log
        else:
            log += "stooq EMPTY"
    except Exception as e:
        log += f"stooq ERROR: {e}"

    return pd.DataFrame(), log


# -------------------------
# ASSETS
# -------------------------
tickers = ["AAPL","MSFT","TSLA","NVDA","BTC-USD"]

# -------------------------
# MARKET OVERVIEW
# -------------------------
rows = []
debug_logs = []

for t in tickers:
    df, log = get_data(t)
    debug_logs.append(f"{t} → {log}")

    if df.empty or len(df) < 22:
        continue

    close = df["Close"]

    try:
        price = close.iloc[-1]
        r1d = (close.iloc[-1]/close.iloc[-2]-1)*100
        r1w = (close.iloc[-1]/close.iloc[-6]-1)*100
        r1m = (close.iloc[-1]/close.iloc[-22]-1)*100
    except:
        continue

    rows.append({
        "Ticker": t,
        "Price": price,
        "1D %": r1d,
        "1W %": r1w,
        "1M %": r1m
    })

df = pd.DataFrame(rows)

st.subheader("📈 Market Overview")
st.dataframe(df)

# -------------------------
# DEBUG PANEL
# -------------------------
st.subheader("🛠 Debug Info")
for log in debug_logs:
    st.text(log)

# -------------------------
# PORTFOLIO
# -------------------------
st.subheader("💼 Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

ticker = st.text_input("Ticker").upper()
qty = st.number_input("Quantity", min_value=0.0)

if st.button("Add"):
    if ticker and qty > 0:
        st.session_state.portfolio.append({"ticker": ticker, "qty": qty})

valid = []

for a in st.session_state.portfolio:
    df, _ = get_data(a["ticker"])

    if df.empty:
        continue

    price = df["Close"].iloc[-1]
    value = price * a["qty"]

    a["value"] = value
    valid.append(a)

if valid:
    total = sum(a["value"] for a in valid)

    st.subheader("📊 Total Value")
    st.write(f"${total:,.2f}")

    weights = [a["value"]/total for a in valid]

    fig, ax = plt.subplots()
    ax.pie(weights, labels=[a["ticker"] for a in valid], autopct="%1.1f%%")
    st.pyplot(fig)
else:
    st.warning("Portfolio data yok")
