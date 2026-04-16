import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📊 Portfolio Analyzer")

stocks = ["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","BRK-B","JPM","JNJ"]
crypto = ["BTC-USD","ETH-USD","SOL-USD"]
bonds = ["TLT","IEF","BND"]

ALL_TICKERS = stocks + crypto + bonds

@st.cache_data
def load_prices(tickers):
    raw = yf.download(
        tickers,
        period="3mo",
        interval="1d",
        auto_adjust=True,
        group_by="ticker",
        progress=False,
        threads=True
    )

    frames = []

    if isinstance(raw.columns, pd.MultiIndex):
        for t in tickers:
            if (t, "Close") in raw.columns:
                s = raw[(t, "Close")].rename(t)
                frames.append(s)
    else:
        s = raw["Close"]
        s.name = tickers[0]
        frames.append(s)

    df = pd.concat(frames, axis=1)

    full_index = pd.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(full_index).ffill().bfill()

    return df

prices = load_prices(ALL_TICKERS)

if not prices.empty:

    latest = prices.iloc[-1]

    def ret(p):
        return prices.pct_change(p).iloc[-1] * 100

    market_df = pd.DataFrame({
        "Ticker": prices.columns,
        "Price": latest,
        "1D %": ret(1),
        "1W %": ret(7),
        "1M %": ret(30)
    }).reset_index(drop=True)

    market_df["Asset Type"] = market_df["Ticker"].apply(
        lambda x: "Stock" if x in stocks else ("Crypto" if x in crypto else "Bond")
    )

    market_df = market_df.replace([np.inf, -np.inf], np.nan).dropna(subset=["Price"])

    st.subheader("📈 Market Overview")
    st.dataframe(market_df, use_container_width=True)

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
        st.success("Added")

portfolio = st.session_state.portfolio

valid_assets = []

for asset in portfolio:
    t = asset["ticker"]
    d = asset["date"]

    if t not in prices.columns:
        continue

    series = prices[t]

    if series.isna().all():
        continue

    idx = series.index.get_indexer([d], method="nearest")[0]

    buy_price = float(series.iloc[idx])
    current_price = float(series.iloc[-1])

    value = current_price * asset["quantity"]
    cost = buy_price * asset["quantity"]

    asset["value"] = value
    asset["cost"] = cost

    valid_assets.append(asset)

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

    fig, ax = plt.subplots()
    ax.pie(
        [a["value"] for a in valid_assets],
        labels=[a["ticker"] for a in valid_assets],
        autopct="%1.1f%%"
    )
    st.pyplot(fig)

    tick_list = [a["ticker"] for a in valid_assets]
    port_df = prices[tick_list]

    weights = np.array([a["quantity"] for a in valid_assets])
    portfolio_series = (port_df * weights).sum(axis=1)

    sp500 = yf.download("^GSPC", period="3mo", progress=False)["Close"]
    sp500 = sp500.reindex(portfolio_series.index).ffill().bfill()

    portfolio_norm = portfolio_series / portfolio_series.iloc[0] * 100
    sp_norm = sp500 / sp500.iloc[0] * 100

    fig2, ax2 = plt.subplots()
    ax2.plot(portfolio_norm, label="Portfolio")
    ax2.plot(sp_norm, label="S&P500")
    ax2.legend()
    st.pyplot(fig2)

else:
    st.info("Portföy boş")
