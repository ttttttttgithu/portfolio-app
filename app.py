import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time

st.title("📊 Portfolio Analyzer")

# -------------------------
# INPUT
# -------------------------
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

ticker = st.text_input("Ticker (örn: AAPL, MSFT, BTC-USD)")
date = st.date_input("Buy Date")
quantity = st.number_input("Quantity", min_value=0.0)

if st.button("Add Asset"):
    if ticker and quantity > 0:
        st.session_state.portfolio.append({
            "ticker": ticker.upper(),
            "date": pd.to_datetime(date),
            "quantity": float(quantity)
        })
        st.success("Asset eklendi!")

portfolio = st.session_state.portfolio

# -------------------------
# SAFE DOWNLOAD FUNCTION
# -------------------------
def safe_download(ticker, start=None, end=None, period=None):
    for _ in range(3):
        try:
            data = yf.download(
                ticker,
                start=start,
                end=end,
                period=period,
                interval="1d",
                auto_adjust=True,
                threads=False,
                progress=False
            )
            if not data.empty:
                return data
        except:
            time.sleep(1)
    return pd.DataFrame()

# -------------------------
# CALCULATIONS
# -------------------------
valid_assets = []

for asset in portfolio:
    ticker = asset["ticker"]
    date = asset["date"]
    quantity = asset["quantity"]

    hist = safe_download(
        ticker,
        start=date - pd.Timedelta(days=10),
        end=date + pd.Timedelta(days=10)
    )

    if hist.empty:
        st.warning(f"{ticker} veri çekilemedi ❌")
        continue

    hist = hist.reset_index()

    # en yakın gün
    hist["diff"] = (hist["Date"] - date).abs()
    closest_row = hist.loc[hist["diff"].idxmin()]

    buy_price = float(closest_row["Close"])

    current_data = safe_download(ticker, period="5d")

    if current_data.empty:
        st.warning(f"{ticker} güncel veri yok ❌")
        continue

    current_price = float(current_data["Close"].dropna().iloc[-1])

    value = current_price * quantity
    cost = buy_price * quantity

    valid_assets.append({
        "ticker": ticker,
        "value": float(value),
        "cost": float(cost),
        "quantity": quantity
    })

# -------------------------
# RESULTS
# -------------------------
if len(valid_assets) == 0:
    st.error("Hiç veri çekilemedi. Büyük ihtimalle ticker hatalı veya API sorunu var.")
else:

    total_value = float(sum(a["value"] for a in valid_assets))
    total_cost = float(sum(a["cost"] for a in valid_assets))

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost != 0 else 0

    st.subheader("📊 Portfolio Summary")
    st.metric("Total Value", f"${total_value:,.2f}")
    st.metric("PnL ($)", f"${total_pnl:,.2f}")
    st.metric("PnL (%)", f"{total_pnl_pct:.2f}%")

    # -------------------------
    # PIE CHART
    # -------------------------
    for a in valid_assets:
        a["weight"] = a["value"] / total_value

    fig, ax = plt.subplots()
    ax.pie(
        [a["weight"] for a in valid_assets],
        labels=[a["ticker"] for a in valid_assets],
        autopct="%1.1f%%"
    )
    ax.set_title("Portfolio Distribution")

    st.pyplot(fig)
