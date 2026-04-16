import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("📊 Portfolio Analyzer (Offline Test)")

# -------------------------
# FAKE DATA (GARANTİLİ)
# -------------------------
np.random.seed(42)

dates = pd.date_range(end=pd.Timestamp.today(), periods=60)

data = {
    "AAPL": 150 + np.cumsum(np.random.randn(60)),
    "MSFT": 300 + np.cumsum(np.random.randn(60)),
    "TSLA": 200 + np.cumsum(np.random.randn(60)),
}

df = pd.DataFrame(data, index=dates)

# -------------------------
# MARKET OVERVIEW
# -------------------------
rows = []

for col in df.columns:
    close = df[col]

    price = close.iloc[-1]
    r1d = (close.iloc[-1]/close.iloc[-2]-1)*100
    r1w = (close.iloc[-1]/close.iloc[-6]-1)*100
    r1m = (close.iloc[-1]/close.iloc[-22]-1)*100

    rows.append({
        "Ticker": col,
        "Price": price,
        "1D %": r1d,
        "1W %": r1w,
        "1M %": r1m
    })

overview = pd.DataFrame(rows)

st.subheader("📈 Market Overview")
st.dataframe(overview)

# -------------------------
# PORTFOLIO
# -------------------------
st.subheader("💼 Portfolio")

portfolio = {
    "AAPL": 10,
    "MSFT": 5,
    "TSLA": 2
}

values = []

for t, qty in portfolio.items():
    price = df[t].iloc[-1]
    values.append(price * qty)

total = sum(values)

st.write(f"Total Value: ${total:,.2f}")

# PIE
fig, ax = plt.subplots()
ax.pie(values, labels=portfolio.keys(), autopct="%1.1f%%")
st.pyplot(fig)

# PERFORMANCE
norm = df / df.iloc[0] * 100

fig2, ax2 = plt.subplots()
ax2.plot(norm)
ax2.legend(df.columns)
st.pyplot(fig2)
