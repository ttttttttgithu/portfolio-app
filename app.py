import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("📊 Portfolio Analyzer")

# -------------------------
# MARKET OVERVIEW
# -------------------------
stocks = ["AAPL", "MSFT"]
crypto = ["BTC-USD", "ETH-USD"]
bonds = ["TLT", "IEF"]

tickers = stocks + crypto + bonds

data = yf.download(tickers, period="1mo", progress=False)

if not data.empty:
    close_prices = data["Close"]

    latest_prices = close_prices.iloc[-1]
    returns_1d = close_prices.pct_change(1).iloc[-1] * 100
    returns_1w = close_prices.pct_change(5).iloc[-1] * 100
    returns_1m = close_prices.pct_change(21).iloc[-1] * 100

    df = pd.DataFrame({
        "Ticker": latest_prices.index,
        "Price": latest_prices.values,
        "1D %": returns_1d.values,
        "1W %": returns_1w.values,
        "1M %": returns_1m.values
    })

    df["Asset Type"] = df["Ticker"].apply(
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

col1, col2, col3 = st.columns(3)

with col1:
    ticker = st.text_input("Ticker (örn: AAPL)")
    ticker = ticker.replace('"', '').replace("'", "").strip().upper()

with col2:
    date = st.date_input("Buy Date")

    # Gelecek tarih fix
    if date > pd.Timestamp.today().date():
        st.warning("Gelecek tarih girdin → bugüne çekildi")
        date = pd.Timestamp.today().date()

with col3:
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
    t = asset["ticker"]
    d = asset["date"]

    try:
        hist = yf.download(
            t,
            start=d - pd.Timedelta(days=10),
            end=d + pd.Timedelta(days=10),
            progress=False
        )

        if hist.empty:
            continue

        hist = hist.reset_index()

        # en yakın işlem günü bul
        hist["diff"] = (hist["Date"] - d).abs()
        row = hist.loc[hist["diff"].idxmin()]

        buy_price = row["Close"]

        # 🔥 SERIES FIX
        if isinstance(buy_price, pd.Series):
            buy_price = buy_price.iloc[0]

        if pd.isna(buy_price):
            continue

        buy_price = float(buy_price)

        # current price
        current_data = yf.download(t, period="1d", progress=False)

        if current_data.empty:
            continue

        cp = current_data["Close"].dropna()

        if cp.empty:
            continue

        current_price = cp.iloc[-1]

        # 🔥 SERIES FIX
        if isinstance(current_price, pd.Series):
            current_price = current_price.iloc[0]

        current_price = float(current_price)

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

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0

    st.subheader("📊 Portfolio Summary")
    c1, c2, c3 = st.columns(3)

    c1.metric("Total Value", f"${total_value:,.2f}")
    c2.metric("PnL ($)", f"${total_pnl:,.2f}")
    c3.metric("PnL (%)", f"{total_pnl_pct:.2f}%")

    # -------------------------
    # PIE CHART
    # -------------------------
    for a in valid_assets:
        a["weight"] = a["value"] / total_value

    fig1, ax1 = plt.subplots(figsize=(4,4))
    ax1.pie(
        [a["weight"] for a in valid_assets],
        labels=[a["ticker"] for a in valid_assets],
        autopct='%1.1f%%'
    )
    ax1.set_title("Portfolio Distribution")
    st.pyplot(fig1)

    # -------------------------
    # PERFORMANCE VS S&P500
    # -------------------------
    tickers = [a["ticker"] for a in valid_assets]
    start_date = min(a["date"] for a in valid_assets)

    price_data = yf.download(tickers, start=start_date, progress=False)["Close"]

    if isinstance(price_data, pd.Series):
        price_data = price_data.to_frame()

    portfolio_value = pd.DataFrame(index=price_data.index)

    for a in valid_assets:
        if a["ticker"] in price_data.columns:
            portfolio_value[a["ticker"]] = price_data[a["ticker"]] * a["quantity"]

    portfolio_value["Total"] = portfolio_value.sum(axis=1)

    sp500 = yf.download("^GSPC", start=start_date, progress=False)["Close"]

    portfolio_norm = portfolio_value["Total"] / portfolio_value["Total"].iloc[0] * 100
    sp500_norm = sp500 / sp500.iloc[0] * 100

    fig2, ax2 = plt.subplots(figsize=(6,3))
    ax2.plot(portfolio_norm, label="Portfolio")
    ax2.plot(sp500_norm, label="S&P 500")
    ax2.legend()
    ax2.set_title("Portfolio vs S&P 500")
    st.pyplot(fig2)

    # -------------------------
    # RISK METRICS
    # -------------------------
    returns = price_data.pct_change().dropna()

    weights = np.array([a["weight"] for a in valid_assets])
    returns = returns[[a["ticker"] for a in valid_assets]]

    expected_return = np.dot(weights, returns.mean()) * 252
    volatility = np.sqrt(np.dot(weights, np.dot(returns.cov()*252, weights)))

    sp500_returns = sp500.pct_change().dropna()
    portfolio_returns = portfolio_value["Total"].pct_change().dropna()

    portfolio_returns, sp500_returns = portfolio_returns.align(sp500_returns, join='inner')

    if len(portfolio_returns) > 1:
        beta = np.cov(portfolio_returns, sp500_returns)[0][1] / np.var(sp500_returns)
    else:
        beta = 0

    risk_free_rate = 0.02
    market_return = sp500_returns.mean() * 252

    capm = risk_free_rate + beta * (market_return - risk_free_rate)
    alpha = expected_return - capm

    st.subheader("📉 Risk Metrics")
    st.write(f"Expected Return: {expected_return:.2%}")
    st.write(f"Volatility: {volatility:.2%}")
    st.write(f"Beta: {beta:.2f}")
    st.write(f"Alpha: {alpha:.2%}")
    st.write(f"CAPM: {capm:.2%}")

else:
    st.warning("Geçerli veri yok. Ticker doğru mu kontrol et (örn: AAPL, BTC-USD)")
