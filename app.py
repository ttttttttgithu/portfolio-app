import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📊 Portfolio Analyzer")

# -------------------------
# MARKET OVERVIEW
# -------------------------
st.subheader("📈 Market Overview")

stocks = ["AAPL", "MSFT"]
crypto = ["BTC-USD", "ETH-USD"]
bonds = ["TLT", "IEF"]

tickers_all = stocks + crypto + bonds

data = yf.download(tickers_all, start="2020-01-01", progress=False)

if not data.empty:
    close_prices = data["Close"]

    latest_prices = close_prices.iloc[-1]

    returns_1d = close_prices.pct_change(1).iloc[-1] * 100
    returns_1w = close_prices.pct_change(5).iloc[-1] * 100
    returns_1m = close_prices.pct_change(21).iloc[-1] * 100

    df_market = pd.DataFrame({
        "Price": latest_prices,
        "1D %": returns_1d,
        "1W %": returns_1w,
        "1M %": returns_1m,
    })

    df_market["Asset Type"] = df_market.index.map(
        lambda x: "Stock" if x in stocks else ("Crypto" if x in crypto else "Bond")
    )

    df_market = df_market.reset_index().rename(columns={"index": "Ticker"})
    st.dataframe(df_market)
else:
    st.warning("Market data alınamadı")

# -------------------------
# SESSION STATE
# -------------------------
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# -------------------------
# INPUT
# -------------------------
st.subheader("💼 Add Asset")

col1, col2, col3 = st.columns(3)

with col1:
    ticker = st.text_input("Ticker").upper()

with col2:
    date = st.date_input("Buy Date")

with col3:
    quantity = st.number_input("Quantity", min_value=0.0)

if st.button("Add Asset"):
    if ticker != "" and quantity > 0:
        st.session_state.portfolio.append({
            "ticker": ticker,
            "date": pd.to_datetime(date),
            "quantity": float(quantity)
        })
        st.success("Asset eklendi!")

portfolio = st.session_state.portfolio

# -------------------------
# HELPER (CRITICAL FIX)
# -------------------------
def safe_float(x):
    return float(np.array(x).flatten()[0])

# -------------------------
# CALCULATIONS
# -------------------------
valid_assets = []

for asset in portfolio:
    ticker = asset["ticker"]
    buy_date = asset["date"]

    try:
        hist = yf.download(
            ticker,
            start=buy_date - pd.Timedelta(days=10),
            end=buy_date + pd.Timedelta(days=10),
            progress=False
        )

        if hist.empty:
            continue

        hist = hist.reset_index()

        hist["diff"] = (hist["Date"] - buy_date).abs()
        row = hist.sort_values("diff").iloc[0]

        buy_price = safe_float(row["Close"])

        current = yf.download(ticker, period="5d", progress=False)

        if current.empty:
            continue

        current_price = safe_float(current["Close"].dropna().iloc[-1])

        quantity = asset["quantity"]

        value = current_price * quantity
        cost = buy_price * quantity

        valid_assets.append({
            "ticker": ticker,
            "quantity": quantity,
            "buy_price": buy_price,
            "current_price": current_price,
            "value": value,
            "cost": cost
        })

    except:
        continue

# -------------------------
# OUTPUT
# -------------------------
if len(valid_assets) == 0:
    st.warning("Geçerli veri yok. Ticker doğru mu? (örn: AAPL, BTC-USD)")
    st.stop()

df = pd.DataFrame(valid_assets)

total_value = float(df["value"].sum())
total_cost = float(df["cost"].sum())

total_pnl = total_value - total_cost
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

st.subheader("📊 Portfolio Summary")

col1, col2, col3 = st.columns(3)

col1.metric("Total Value", f"${total_value:,.2f}")
col2.metric("PnL ($)", f"${total_pnl:,.2f}")
col3.metric("PnL (%)", f"{total_pnl_pct:.2f}%")

# TABLE
df["PnL"] = df["value"] - df["cost"]
df["PnL %"] = (df["PnL"] / df["cost"]) * 100

st.dataframe(df)

# PIE
df["weight"] = df["value"] / total_value

fig1, ax1 = plt.subplots()
ax1.pie(df["weight"], labels=df["ticker"], autopct="%1.1f%%")
ax1.set_title("Portfolio Distribution")
st.pyplot(fig1)

# PERFORMANCE
tickers = df["ticker"].tolist()
start_date = min(asset["date"] for asset in portfolio)

prices = yf.download(tickers, start=start_date, progress=False)["Close"]

if isinstance(prices, pd.Series):
    prices = prices.to_frame()

portfolio_series = pd.DataFrame(index=prices.index)

for i, row in df.iterrows():
    if row["ticker"] in prices.columns:
        portfolio_series[row["ticker"]] = prices[row["ticker"]] * row["quantity"]

portfolio_series["Total"] = portfolio_series.sum(axis=1)

sp500 = yf.download("^GSPC", start=start_date, progress=False)["Close"]

portfolio_norm = portfolio_series["Total"] / portfolio_series["Total"].iloc[0] * 100
sp500_norm = sp500 / sp500.iloc[0] * 100

fig2, ax2 = plt.subplots()
ax2.plot(portfolio_norm, label="Portfolio")
ax2.plot(sp500_norm, label="S&P 500")
ax2.legend()
ax2.set_title("Performance vs S&P 500")

st.pyplot(fig2)

# RISK
returns = prices.pct_change().dropna()
returns = returns[df["ticker"]]

weights = df["weight"].values

mean_returns = returns.mean()
expected_return = np.dot(weights, mean_returns) * 252

cov_matrix = returns.cov()
variance = np.dot(weights, np.dot(cov_matrix, weights)) * 252
std_dev = np.sqrt(variance)

portfolio_returns = portfolio_series["Total"].pct_change().dropna()
sp500_returns = sp500.pct_change().dropna()

portfolio_returns, sp500_returns = portfolio_returns.align(sp500_returns, join='inner')

cov = np.cov(portfolio_returns, sp500_returns)
beta = cov[0][1] / cov[1][1]

risk_free = 0.02
market_return = sp500_returns.mean() * 252

alpha = expected_return - (risk_free + beta * (market_return - risk_free))

st.subheader("📉 Risk Metrics")

st.write(f"Expected Return: {expected_return:.2%}")
st.write(f"Volatility: {std_dev:.2%}")
st.write(f"Beta: {beta:.2f}")
st.write(f"Alpha: {alpha:.2%}")
