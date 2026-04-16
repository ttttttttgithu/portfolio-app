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

tickers = stocks + crypto + bonds

# -------------------------
# MARKET DATA (FIXED)
# -------------------------

data = {}

with st.spinner("Loading market data..."):
    for t in tickers:
        try:
            df = yf.Ticker(t).history(period="2mo")
            if not df.empty:
                data[t] = df["Close"]
        except:
            pass

if len(data) > 0:

    all_dates = pd.date_range(
        start=min(s.index.min() for s in data.values()),
        end=max(s.index.max() for s in data.values()),
        freq="D"
    )

    aligned = {t: s.reindex(all_dates).ffill() for t, s in data.items()}
    close_prices = pd.DataFrame(aligned)

    latest_prices = close_prices.iloc[-1]
    returns_1d = close_prices.pct_change(1).iloc[-1] * 100
    returns_1w = close_prices.pct_change(7).iloc[-1] * 100
    returns_1m = close_prices.pct_change(30).iloc[-1] * 100

    df = pd.DataFrame({
        "Ticker": close_prices.columns,
        "Price": latest_prices,
        "1D %": returns_1d,
        "1W %": returns_1w,
        "1M %": returns_1m
    }).reset_index(drop=True)

    df["Asset Type"] = df["Ticker"].apply(
        lambda x: "Stock" if x in stocks else ("Crypto" if x in crypto else "Bond")
    )

    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["Price"])

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
# PORTFOLIO CALCULATION
# -------------------------

valid_assets = []

for asset in portfolio:
    t = asset["ticker"]
    d = asset["date"]

    try:
        hist = yf.Ticker(t).history(start=d - pd.Timedelta(days=5),
                                    end=d + pd.Timedelta(days=5))

        if hist.empty:
            continue

        hist["diff"] = (hist.index - d).abs()
        buy_price = hist.loc[hist["diff"].idxmin()]["Close"]

        current = yf.Ticker(t).history(period="1d")

        if current.empty:
            continue

        current_price = current["Close"].iloc[-1]

    except:
        continue

    value = current_price * asset["quantity"]
    cost = buy_price * asset["quantity"]

    asset["value"] = value
    asset["cost"] = cost
    asset["buy_price"] = buy_price
    asset["current_price"] = current_price

    valid_assets.append(asset)

# -------------------------
# RESULTS
# -------------------------

if len(valid_assets) > 0:

    total_value = sum(a["value"] for a in valid_assets)
    total_cost = sum(a["cost"] for a in valid_assets)

    pnl = total_value - total_cost
    pnl_pct = (pnl / total_cost) * 100 if total_cost > 0 else 0

    st.subheader("📊 Portfolio Summary")

    c1, c2, c3 = st.columns(3)
    c1.metric("Value", f"${total_value:,.2f}")
    c2.metric("PnL", f"${pnl:,.2f}")
    c3.metric("PnL %", f"{pnl_pct:.2f}%")

    # PIE
    weights = [a["value"] for a in valid_assets]

    fig, ax = plt.subplots()
    ax.pie(weights, labels=[a["ticker"] for a in valid_assets], autopct="%1.1f%%")
    st.pyplot(fig)

    # -------------------------
    # PERFORMANCE vs SP500
    # -------------------------

    tick_list = [a["ticker"] for a in valid_assets]
    start_date = min(a["date"] for a in valid_assets)

    prices = yf.download(tick_list, start=start_date)["Close"]

    if isinstance(prices, pd.Series):
        prices = prices.to_frame()

    portfolio_value = pd.DataFrame(index=prices.index)

    for a in valid_assets:
        if a["ticker"] in prices.columns:
            portfolio_value[a["ticker"]] = prices[a["ticker"]] * a["quantity"]

    portfolio_value["Total"] = portfolio_value.sum(axis=1)

    sp500 = yf.download("^GSPC", start=start_date)["Close"]

    port_norm = portfolio_value["Total"] / portfolio_value["Total"].iloc[0] * 100
    sp_norm = sp500 / sp500.iloc[0] * 100

    fig2, ax2 = plt.subplots()
    ax2.plot(port_norm, label="Portfolio")
    ax2.plot(sp_norm, label="S&P500")
    ax2.legend()
    st.pyplot(fig2)

else:
    st.warning("Portföy boş veya veri alınamadı")
