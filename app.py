import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("📊 Portfolio Analyzer")

# -------------------------
# ASSETS
# -------------------------

stocks = [
"AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","BRK-B","JPM","JNJ",
"V","PG","UNH","HD","MA","DIS","ADBE","NFLX","KO","PEP",
"XOM","CVX","ABBV","MRK","PFE"
]

crypto = [
"BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD","ADA-USD","DOGE-USD",
"MATIC-USD","LTC-USD","TRX-USD","AVAX-USD","SHIB-USD","LINK-USD",
"ATOM-USD","XLM-USD","ETC-USD","FIL-USD","HBAR-USD","EGLD-USD",
"XTZ-USD","THETA-USD","AAVE-USD","EOS-USD","NEO-USD","KSM-USD"
]

bonds = [
"TLT","IEF","SHY","BND","AGG","LQD","HYG","TIP","MUB","VGIT",
"VCIT","VCSH","BLV","BSV","SCHZ","SPTL","SPSB","IGSB","FLOT",
"USIG","TFLO","VTIP","BIV","TLH","EDV"
]

tickers = stocks + crypto + bonds

# -------------------------
# MARKET OVERVIEW (FINAL FIX)
# -------------------------

close_prices = pd.DataFrame()
base_index = None

for t in tickers:
    try:
        df_t = yf.download(t, period="3mo", progress=False)

        if df_t.empty:
            continue

        close = df_t["Close"].rename(t)

        # ilk gelen index
        if base_index is None:
            base_index = close.index

        # tümünü aynı indexe zorla
        close = close.reindex(base_index)

        close_prices[t] = close

    except:
        continue

# boşlukları doldur
close_prices = close_prices.ffill().bfill()

# zayıf kolonları kaldır
close_prices = close_prices.dropna(axis=1, thresh=20)

if not close_prices.empty:

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
    if date > pd.Timestamp.today().date():
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
        hist = yf.download(t, start=d - pd.Timedelta(days=10),
                           end=d + pd.Timedelta(days=10), progress=False)

        if hist.empty:
            continue

        hist = hist.reset_index()
        hist["diff"] = (hist["Date"] - d).abs()
        row = hist.loc[hist["diff"].idxmin()]

        buy_price = float(row["Close"])

        current_data = yf.download(t, period="5d", progress=False)
        current_price = float(current_data["Close"].dropna().iloc[-1])

    except:
        continue

    value = current_price * asset["quantity"]
    cost = buy_price * asset["quantity"]

    asset["value"] = value
    asset["cost"] = cost

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

    # PIE CHART
    for a in valid_assets:
        a["weight"] = a["value"] / total_value

    fig1, ax1 = plt.subplots(figsize=(4,4))
    ax1.pie([a["weight"] for a in valid_assets],
            labels=[a["ticker"] for a in valid_assets],
            autopct='%1.1f%%')
    st.pyplot(fig1)

    # PERFORMANCE (AYNI INDEX FIX)
    tickers_port = [a["ticker"] for a in valid_assets]
    start_date = min(a["date"] for a in valid_assets)

    price_data = pd.DataFrame()
    base_index = None

    for t in tickers_port:
        try:
            df_t = yf.download(t, start=start_date, progress=False)

            if df_t.empty:
                continue

            close = df_t["Close"].rename(t)

            if base_index is None:
                base_index = close.index

            close = close.reindex(base_index)

            price_data[t] = close

        except:
            continue

    price_data = price_data.ffill().bfill()

    portfolio_value = pd.DataFrame(index=price_data.index)

    for a in valid_assets:
        if a["ticker"] in price_data.columns:
            portfolio_value[a["ticker"]] = price_data[a["ticker"]] * a["quantity"]

    portfolio_value["Total"] = portfolio_value.sum(axis=1)

    sp500 = yf.download("^GSPC", start=start_date, progress=False)["Close"]
    sp500 = sp500.reindex(portfolio_value.index).ffill().bfill()

    portfolio_norm = portfolio_value["Total"] / portfolio_value["Total"].iloc[0] * 100
    sp500_norm = sp500 / sp500.iloc[0] * 100

    fig2, ax2 = plt.subplots(figsize=(6,3))
    ax2.plot(portfolio_norm, label="Portfolio")
    ax2.plot(sp500_norm, label="S&P 500")
    ax2.legend()
    st.pyplot(fig2)

    # RISK METRICS
    portfolio_returns = portfolio_value["Total"].pct_change()
    sp500_returns = sp500.pct_change()

    df_returns = pd.concat([portfolio_returns, sp500_returns], axis=1).dropna()
    df_returns.columns = ["portfolio", "market"]

    if len(df_returns) > 2:

        cov = df_returns["portfolio"].cov(df_returns["market"])
        var = df_returns["market"].var()

        beta = cov / var if var != 0 else 0

        expected_return = df_returns["portfolio"].mean() * 252
        volatility = df_returns["portfolio"].std() * np.sqrt(252)

        risk_free_rate = 0.02
        market_return = df_returns["market"].mean() * 252

        capm = risk_free_rate + beta * (market_return - risk_free_rate)
        alpha = expected_return - capm

        st.subheader("📉 Risk Metrics")
        st.write(f"Expected Return: {expected_return:.2%}")
        st.write(f"Volatility: {volatility:.2%}")
        st.write(f"Beta: {beta:.2f}")
        st.write(f"Alpha: {alpha:.2%}")
        st.write(f"CAPM: {capm:.2%}")

    else:
        st.warning("Risk metrics hesaplamak için yeterli veri yok")

else:
    st.warning("Geçerli veri yok. Ticker doğru mu kontrol et.")
