import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("📊 Portfolio Analyzer")

# -------------------------
# MARKET OVERVIEW (ESKİ HAL)
# -------------------------
stocks = ["AAPL", "MSFT"]
crypto = ["BTC-USD", "ETH-USD"]
bonds = ["TLT", "IEF"]

tickers = stocks + crypto + bonds

data = yf.download(tickers, period="1mo", progress=False)["Close"]

latest_prices = data.iloc[-1]

returns_1d = data.pct_change(1).iloc[-1] * 100
returns_1w = data.pct_change(5).iloc[-1] * 100
returns_1m = data.pct_change(21).iloc[-1] * 100

df = pd.DataFrame({
    "Price": latest_prices,
    "1D %": returns_1d,
    "1W %": returns_1w,
    "1M %": returns_1m,
})

df["Asset Type"] = df.index.map(
    lambda x: "Stock" if x in stocks else ("Crypto" if x in crypto else "Bond")
)

df = df.reset_index().rename(columns={"index": "Ticker"})

st.subheader("📈 Market Overview")
st.dataframe(df, use_container_width=True)

# -------------------------
# PORTFOLIO INPUT
# -------------------------
st.subheader("💼 Add Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

col1, col2, col3 = st.columns(3)

with col1:
    ticker = st.text_input("Ticker (örn: AAPL)")

with col2:
    date = st.date_input("Buy Date")

with col3:
    quantity = st.number_input("Quantity", min_value=0.0)

if st.button("Add Asset"):
    st.session_state.portfolio.append({
        "ticker": ticker.upper(),
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
        hist = yf.download(ticker, start=date - pd.Timedelta(days=5),
                           end=date + pd.Timedelta(days=5),
                           progress=False)

        if hist.empty:
            continue

        hist = hist.reset_index()

        # En yakın tarih
        hist["diff"] = abs(hist["Date"] - date)
        row = hist.sort_values("diff").iloc[0]

        buy_price = float(row["Close"])

        current_data = yf.download(ticker, period="1d", progress=False)

        if current_data.empty:
            continue

        current_price = float(current_data["Close"].iloc[-1])

        value = current_price * asset["quantity"]
        cost = buy_price * asset["quantity"]

        asset.update({
            "buy_price": buy_price,
            "current_price": current_price,
            "value": value,
            "cost": cost
        })

        valid_assets.append(asset)

    except:
        continue

# -------------------------
# PORTFOLIO SUMMARY
# -------------------------
if len(valid_assets) > 0:

    total_value = sum(a["value"] for a in valid_assets)
    total_cost = sum(a["cost"] for a in valid_assets)

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0

    # Enflasyon (varsayım %3)
    inflation_rate = 0.03
    real_return = total_pnl_pct - (inflation_rate * 100)

    st.subheader("📊 Portfolio Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Value", f"${total_value:,.2f}")
    col2.metric("PnL ($)", f"${total_pnl:,.2f}")
    col3.metric("PnL (%)", f"{total_pnl_pct:.2f}%")
    col4.metric("Real Return (Inflation Adj.)", f"{real_return:.2f}%")

    # -------------------------
    # PIE CHART
    # -------------------------
    for a in valid_assets:
        a["weight"] = a["value"] / total_value

    fig1, ax1 = plt.subplots(figsize=(5, 5))
    ax1.pie(
        [a["weight"] for a in valid_assets],
        labels=[a["ticker"] for a in valid_assets],
        autopct="%1.1f%%"
    )
    ax1.set_title("Portfolio Distribution")
    st.pyplot(fig1)

    # -------------------------
    # PERFORMANCE vs S&P500
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

    fig2, ax2 = plt.subplots(figsize=(8, 4))
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

    mean_returns = returns.mean()
    expected_return = np.dot(weights, mean_returns) * 252

    cov_matrix = returns.cov()
    variance = np.dot(weights, np.dot(cov_matrix, weights)) * 252
    std_dev = np.sqrt(variance)

    # -------------------------
    # BETA / ALPHA / CAPM
    # -------------------------
    portfolio_returns = portfolio_value["Total"].pct_change().dropna()
    sp500_returns = sp500.pct_change().dropna()

    portfolio_returns, sp500_returns = portfolio_returns.align(sp500_returns, join="inner")

    if len(portfolio_returns) > 1:
        cov = np.cov(portfolio_returns, sp500_returns)

        beta = cov[0][1] / cov[1][1]

        risk_free_rate = 0.02
        market_return = sp500_returns.mean() * 252

        capm = risk_free_rate + beta * (market_return - risk_free_rate)
        alpha = expected_return - capm
    else:
        beta, alpha, capm = 0, 0, 0

    st.subheader("📉 Risk Metrics")

    st.write(f"Expected Return: {expected_return:.2%}")
    st.write(f"Volatility: {std_dev:.2%}")
    st.write(f"Beta: {beta:.2f}")
    st.write(f"Alpha: {alpha:.2%}")
    st.write(f"CAPM Expected Return: {capm:.2%}")

else:
    st.warning("Geçerli veri yok. Ticker ve tarihi kontrol et (örn: AAPL, BTC-USD).")
