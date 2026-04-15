import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("📊 Portfolio Analyzer")

# -------------------------
# MARKET DATA (ilk kısım - SENİN çalışan kısım)
# -------------------------
stocks = ["AAPL", "MSFT"]
crypto = ["BTC-USD", "ETH-USD"]
bonds = ["TLT", "IEF"]

tickers = stocks + crypto + bonds

data = yf.download(tickers, start="2020-01-01", progress=False)
close_prices = data["Close"]

latest_prices = close_prices.iloc[-1]

returns_1d = close_prices.pct_change(1).iloc[-1] * 100
returns_1w = close_prices.pct_change(5).iloc[-1] * 100
returns_1m = close_prices.pct_change(21).iloc[-1] * 100

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
st.dataframe(df)

# -------------------------
# PORTFOLIO INPUT
# -------------------------
st.subheader("💼 Add Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

col1, col2, col3 = st.columns(3)

with col1:
    ticker = st.text_input("Ticker (örn: AAPL, BTC-USD)")

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
# CALCULATIONS (DÜZELTİLMİŞ)
# -------------------------
valid_assets = []

for asset in portfolio:
    try:
        hist = yf.download(asset["ticker"], period="5y", progress=False)

        if hist.empty:
            continue

        hist = hist.reset_index()

        # en yakın tarih
        hist["diff"] = abs(hist["Date"] - asset["date"])
        row = hist.loc[hist["diff"].idxmin()]

        buy_price = float(row["Close"])

        current_data = yf.download(asset["ticker"], period="1d", progress=False)
        current_price = float(current_data["Close"].iloc[-1])

        value = current_price * asset["quantity"]
        cost = buy_price * asset["quantity"]

        valid_assets.append({
            "ticker": asset["ticker"],
            "buy_price": buy_price,
            "current_price": current_price,
            "value": value,
            "cost": cost
        })

    except:
        continue

# -------------------------
# SONUÇLAR
# -------------------------
if len(valid_assets) == 0:
    st.warning("Geçerli veri yok. Ticker doğru mu kontrol et.")
    st.stop()

# toplamlar
total_value = sum(a["value"] for a in valid_assets)
total_cost = sum(a["cost"] for a in valid_assets)

total_pnl = total_value - total_cost
total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0

st.subheader("📊 Portfolio Summary")

col1, col2, col3 = st.columns(3)
col1.metric("Total Value", f"${total_value:,.2f}")
col2.metric("PnL ($)", f"${total_pnl:,.2f}")
col3.metric("PnL (%)", f"{total_pnl_pct:.2f}%")

# -------------------------
# PIE CHART (küçük)
# -------------------------
labels = [a["ticker"] for a in valid_assets]
sizes = [a["value"] for a in valid_assets]

fig1, ax1 = plt.subplots(figsize=(4,4))
ax1.pie(sizes, labels=labels, autopct='%1.1f%%')
ax1.set_title("Portfolio Distribution")
st.pyplot(fig1)

# -------------------------
# PERFORMANCE GRAPH
# -------------------------
tickers = [a["ticker"] for a in valid_assets]

price_data = yf.download(tickers, period="1y", progress=False)["Close"]

if isinstance(price_data, pd.Series):
    price_data = price_data.to_frame()

portfolio_series = price_data.copy()

for a in valid_assets:
    if a["ticker"] in portfolio_series.columns:
        portfolio_series[a["ticker"]] *= a["value"] / price_data[a["ticker"]].iloc[-1]

portfolio_series["Total"] = portfolio_series.sum(axis=1)

sp500 = yf.download("^GSPC", period="1y", progress=False)["Close"]

# normalize
portfolio_norm = portfolio_series["Total"] / portfolio_series["Total"].iloc[0] * 100
sp500_norm = sp500 / sp500.iloc[0] * 100

fig2, ax2 = plt.subplots(figsize=(6,3))
ax2.plot(portfolio_norm, label="Portfolio")
ax2.plot(sp500_norm, label="S&P 500")
ax2.legend()
ax2.set_title("Performance")
st.pyplot(fig2)

# -------------------------
# RISK METRICS (FIXED)
# -------------------------
returns = price_data.pct_change().dropna()

weights = np.array([a["value"] for a in valid_assets])
weights = weights / weights.sum()

returns = returns[[a["ticker"] for a in valid_assets]]

mean_returns = returns.mean()
expected_return = np.dot(weights, mean_returns) * 252

cov_matrix = returns.cov()
variance = np.dot(weights, np.dot(cov_matrix, weights)) * 252
std_dev = np.sqrt(variance)

# beta FIX
portfolio_returns = portfolio_series["Total"].pct_change().dropna()
sp500_returns = sp500.pct_change().dropna()

portfolio_returns, sp500_returns = portfolio_returns.align(sp500_returns, join='inner')

beta = np.cov(portfolio_returns, sp500_returns)[0][1] / np.var(sp500_returns)

risk_free = 0.02
market_return = sp500_returns.mean() * 252

alpha = expected_return - (risk_free + beta * (market_return - risk_free))

# -------------------------
# METRICS OUTPUT
# -------------------------
st.subheader("📉 Risk Metrics")

st.write(f"Expected Return: {expected_return:.2%}")
st.write(f"Volatility: {std_dev:.2%}")
st.write(f"Beta: {beta:.2f}")
st.write(f"Alpha: {alpha:.2%}")
