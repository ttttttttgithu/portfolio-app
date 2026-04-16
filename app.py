import streamlit as st
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt

st.title("📊 Portfolio Analyzer (Stable Version)")

API_KEY = "BURAYA_API_KEYİNİ_YAZ"

# -------------------------
# DATA FETCH (ALPHA VANTAGE)
# -------------------------
@st.cache_data(ttl=600)
def get_stock_data(symbol):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol}&outputsize=compact&apikey={API_KEY}"
    
    try:
        r = requests.get(url).json()
        data = r.get("Time Series (Daily)", {})
        
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data).T
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        df["Close"] = df["4. close"].astype(float)

        return df[["Close"]]
    except:
        return pd.DataFrame()

# -------------------------
# ASSETS
# -------------------------
stocks = ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","META"]
tickers = stocks

# -------------------------
# MARKET OVERVIEW
# -------------------------
rows = []

for t in tickers:
    df = get_stock_data(t)

    if df.empty or len(df) < 22:
        continue

    close = df["Close"]

    price = close.iloc[-1]
    r1d = (close.iloc[-1]/close.iloc[-2]-1)*100
    r1w = (close.iloc[-1]/close.iloc[-6]-1)*100
    r1m = (close.iloc[-1]/close.iloc[-22]-1)*100

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
# PORTFOLIO INPUT
# -------------------------
st.subheader("💼 Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

ticker = st.text_input("Ticker").upper()
quantity = st.number_input("Quantity", min_value=0.0)

if st.button("Add"):
    if ticker and quantity > 0:
        st.session_state.portfolio.append({
            "ticker": ticker,
            "quantity": quantity
        })

# -------------------------
# CALCULATE
# -------------------------
valid = []

for asset in st.session_state.portfolio:
    df = get_stock_data(asset["ticker"])

    if df.empty:
        continue

    price = df["Close"].iloc[-1]
    value = price * asset["quantity"]

    asset["value"] = value
    valid.append(asset)

# -------------------------
# RESULTS
# -------------------------
if valid:

    total = sum(a["value"] for a in valid)

    st.subheader("📊 Portfolio Value")
    st.write(f"${total:,.2f}")

    weights = [a["value"]/total for a in valid]

    fig, ax = plt.subplots()
    ax.pie(weights, labels=[a["ticker"] for a in valid], autopct="%1.1f%%")
    st.pyplot(fig)

else:
    st.warning("Veri yok veya API çalışmıyor")
