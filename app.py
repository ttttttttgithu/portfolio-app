import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("📊 Portfolio Analyzer")

# -------------------------
# MARKET DATA
# -------------------------
stocks = ["AAPL", "MSFT"]
crypto = ["BTC-USD", "ETH-USD"]
bonds = ["TLT", "IEF"]

tickers = stocks + crypto + bonds

data = yf.download(tickers, start="2020-01-01", progress=False)

if not data.empty:
    close_prices = data["Close"]

    df = pd.DataFrame({
        "Price": close_prices.iloc[-1],
        "1D %": close_prices.pct_change(1).iloc[-1] * 100,
        "1W %": close_prices.pct_change(5).iloc[-1] * 100,
        "1M %": close_prices.pct_change(21).iloc[-1] * 100,
    })

    df["Asset Type"] = df.index.map(
        lambda x: "Stock" if x in stocks else ("Crypto" if x in crypto else "Bond")
    )

    st.subheader("📈 Market Overview")
    st.dataframe(df)

# -------------------------
# PORTFOLIO INPUT
# -------------------------
st.subheader("💼 Add Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

ticker = st.text_input("Ticker (örn: AAPL, BTC-USD)").upper()
date = st.date_input("Buy Date")
quantity = st.number_input("Quantity", min_value=0.0)

if st.button("Add Asset"):
    if ticker != "" and quantity > 0:
        st.session_state.portfolio.append({
            "ticker": ticker,
            "date": pd.to_datetime(date),
            "quantity": quantity
        })
        st.success("Asset eklendi!")

portfolio = st.session_state.portfolio

# -------------------------
# CALCULATIONS
# -------------------------
valid_assets = []

for asset in portfolio:
    ticker = asset["ticker"]
    date = asset["date"]

    try:
        # 🔥 BUY PRICE (fallback sistem)
        data = yf.download(
            ticker,
            start=date,
            end=date + pd.Timedelta(days=10),
            progress=False
        )

        if data.empty:
            # fallback → son 1 aydan ilk price al
            data = yf.download(ticker, period="1mo", progress=False)

        if data.empty:
            continue

        buy_price = float(data["Close"].dropna().iloc[0])

        # 🔥 CURRENT PRICE
        current_data = yf.download(ticker, period="1d", progress=False)

        if current_data.empty:
            current_data = yf.download(ticker, period="5d", progress=False)

        if current_data.empty:
            continue

        current_price = float(current_data["Close"].dropna().iloc[-1])

        value = current_price * asset["quantity"]
        cost = buy_price * asset["quantity"]

        valid_assets.append({
            "ticker": ticker,
            "buy_price": buy_price,
            "current_price": current_price,
            "value": value,
            "cost": cost
        })

    except Exception as e:
        st.write(f"Hata ({ticker}):", e)
        continue

# -------------------------
# RESULTS
# -------------------------
if len(valid_assets) > 0:

    total_value = float(sum(a["value"] for a in valid_assets))
    total_cost = float(sum(a["cost"] for a in valid_assets))

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    st.subheader("📊 Portfolio Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Value", f"${total_value:,.2f}")
    col2.metric("PnL ($)", f"${total_pnl:,.2f}")
    col3.metric("PnL (%)", f"{total_pnl_pct:.2f}%")

    # -------------------------
    # PIE CHART
    # -------------------------
    for a in valid_assets:
        a["weight"] = a["value"] / total_value

    labels = [a["ticker"] for a in valid_assets]
    sizes = [a["weight"] for a in valid_assets]

    fig1, ax1 = plt.subplots(figsize=(4,4))
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%')
    ax1.set_title("Portfolio Distribution")
    st.pyplot(fig1)

    # -------------------------
    # PERFORMANCE
    # -------------------------
    tickers = [a["ticker"] for a in valid_assets]

    price_data = yf.download(tickers, period="1y", progress=False)["Close"]

    if isinstance(price_data, pd.Series):
        price_data = price_data.to_frame()

    portfolio_value = price_data.copy()

    for a in valid_assets:
        if a["ticker"] in portfolio_value.columns:
            qty = a["value"] / a["current_price"]
            portfolio_value[a["ticker"]] *= qty

    portfolio_value["Total"] = portfolio_value.sum(axis=1)

    portfolio_norm = portfolio_value["Total"] / portfolio_value["Total"].iloc[0] * 100

    fig2, ax2 = plt.subplots(figsize=(6,3))
    ax2.plot(portfolio_norm, label="Portfolio")
    ax2.legend()
    ax2.set_title("Portfolio Performance")
    st.pyplot(fig2)

    # -------------------------
    # RISK
    # -------------------------
    returns = price_data.pct_change().dropna()

    returns = returns[[a["ticker"] for a in valid_assets]]

    weights = np.array([a["weight"] for a in valid_assets])

    mean_returns = returns.mean()
    expected_return = float(np.dot(weights, mean_returns) * 252)

    cov_matrix = returns.cov()
    variance = float(np.dot(weights, np.dot(cov_matrix, weights)) * 252)
    std_dev = np.sqrt(variance)

    st.subheader("📉 Risk Metrics")
    st.write(f"Expected Return: {expected_return:.2%}")
    st.write(f"Volatility: {std_dev:.2%}")

else:
    st.warning("Geçerli veri yok. Ticker doğru mu kontrol et (örn: AAPL, BTC-USD)")
