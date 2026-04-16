import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Portfolio Analyzer", layout="wide")

st.title("📊 Portfolio Analyzer (Offline Working Version)")

# -------------------------
# FAKE MARKET DATA
# -------------------------
np.random.seed(42)

dates = pd.date_range(end=pd.Timestamp.today(), periods=120)

def generate_price(start):
    return start + np.cumsum(np.random.normal(0, 1, len(dates)))

prices = pd.DataFrame({
    "AAPL": generate_price(150),
    "MSFT": generate_price(300),
    "TSLA": generate_price(200),
    "NVDA": generate_price(400),
    "BTC": generate_price(30000),
}, index=dates)

# -------------------------
# MARKET OVERVIEW
# -------------------------
st.subheader("📈 Market Overview")

rows = []

for col in prices.columns:
    close = prices[col]

    price = close.iloc[-1]
    r1d = (close.iloc[-1] / close.iloc[-2] - 1) * 100
    r1w = (close.iloc[-1] / close.iloc[-6] - 1) * 100
    r1m = (close.iloc[-1] / close.iloc[-22] - 1) * 100

    rows.append({
        "Ticker": col,
        "Price": round(price, 2),
        "1D %": round(r1d, 2),
        "1W %": round(r1w, 2),
        "1M %": round(r1m, 2)
    })

overview = pd.DataFrame(rows)
st.dataframe(overview, use_container_width=True)

# -------------------------
# PORTFOLIO INPUT
# -------------------------
st.subheader("💼 Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}

col1, col2 = st.columns(2)

with col1:
    ticker = st.selectbox("Select Asset", prices.columns)

with col2:
    quantity = st.number_input("Quantity", min_value=0.0, step=1.0)

if st.button("Add / Update Asset"):
    if quantity > 0:
        st.session_state.portfolio[ticker] = quantity
    elif ticker in st.session_state.portfolio:
        del st.session_state.portfolio[ticker]

portfolio = st.session_state.portfolio

# -------------------------
# PORTFOLIO CALC
# -------------------------
if portfolio:

    values = {}
    for t, qty in portfolio.items():
        price = prices[t].iloc[-1]
        values[t] = price * qty

    total_value = sum(values.values())

    st.subheader("📊 Portfolio Summary")
    c1, c2 = st.columns(2)

    c1.metric("Total Value", f"${total_value:,.2f}")
    c2.metric("Number of Assets", len(portfolio))

    # -------------------------
    # PIE CHART
    # -------------------------
    fig1, ax1 = plt.subplots()
    ax1.pie(values.values(), labels=values.keys(), autopct="%1.1f%%")
    ax1.set_title("Portfolio Allocation")
    st.pyplot(fig1)

    # -------------------------
    # PERFORMANCE
    # -------------------------
    st.subheader("📈 Portfolio Performance")

    portfolio_series = pd.Series(0, index=prices.index)

    for t, qty in portfolio.items():
        portfolio_series += prices[t] * qty

    normalized = portfolio_series / portfolio_series.iloc[0] * 100

    fig2, ax2 = plt.subplots()
    ax2.plot(normalized, label="Portfolio")
    ax2.set_title("Normalized Performance")
    ax2.legend()
    st.pyplot(fig2)

else:
    st.info("Portföye asset ekle")

# -------------------------
# DEBUG INFO
# -------------------------
st.subheader("🛠 Debug Info")
st.write("Bu versiyon internet kullanmaz → çalışıyorsa sistemin OK")
