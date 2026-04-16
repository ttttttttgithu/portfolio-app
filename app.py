import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("📊 Portfolio Analyzer")

# -------------------------
# MARKET OVERVIEW (FIXED)
# -------------------------

stocks = [
"AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","BRK-B","JPM","JNJ",
"V","PG","UNH","HD","MA","DIS","ADBE","NFLX","KO","PEP",
"XOM","CVX","ABBV","MRK","PFE"
]

crypto = [
"BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD","ADA-USD","DOGE-USD",
"DOT-USD","MATIC-USD","LTC-USD","TRX-USD","AVAX-USD","SHIB-USD",
"LINK-USD","ATOM-USD","XLM-USD","ETC-USD","ICP-USD","FIL-USD",
"APT-USD","ARB-USD","OP-USD","NEAR-USD","ALGO-USD","VET-USD"
]

bonds = [
"TLT","IEF","SHY","BND","AGG","LQD","HYG","TIP","MUB","VGIT",
"VCIT","VCSH","BLV","BSV","SCHZ","SPTL","SPSB","IGSB","FLOT",
"USIG","TFLO","VTIP","BIV","TLH","EDV"
]

tickers = stocks + crypto + bonds

data_dict = {}

with st.spinner("Market data yükleniyor..."):
    for t in tickers:
        try:
            df = yf.Ticker(t).history(period="2mo")

            if df.empty:
                continue

            close = df["Close"].dropna()

            # minimum veri şartı
            if len(close) < 5:
                continue

            data_dict[t] = close

        except:
            continue

# -------------------------
# DATAFRAME BUILD
# -------------------------

if len(data_dict) > 0:

    close_prices = pd.DataFrame(data_dict)

    # eksikleri doldur
    close_prices = close_prices.ffill().dropna(how="all")

    latest_prices = close_prices.iloc[-1]

    def safe_return(period):
        if len(close_prices) > period:
            return close_prices.pct_change(period).iloc[-1] * 100
        else:
            return pd.Series(index=close_prices.columns, data=np.nan)

    returns_1d = safe_return(1)
    returns_1w = safe_return(5)
    returns_1m = safe_return(21)

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

    df = df.dropna(subset=["Price"])

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
    ticker = st.text_input("Ticker (örn: AAPL)").upper().strip()

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
        hist = yf.Ticker(t).history(start=d - pd.Timedelta(days=5),
                                    end=d + pd.Timedelta(days=5))

        if hist.empty:
            continue

        hist = hist.reset_index()
        hist["diff"] = (hist["Date"] - d).abs()
        row = hist.loc[hist["diff"].idxmin()]

        buy_price = float(row["Close"])

        current_data = yf.Ticker(t).history(period="1d")

        if current_data.empty:
            continue

        current_price = float(current_data["Close"].iloc[-1])

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

    for a in valid_assets:
        a["weight"] = a["value"] / total_value

    fig1, ax1 = plt.subplots()
    ax1.pie([a["weight"] for a in valid_assets],
            labels=[a["ticker"] for a in valid_assets],
            autopct='%1.1f%%')
    st.pyplot(fig1)

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

    fig2, ax2 = plt.subplots()
    ax2.plot(portfolio_norm, label="Portfolio")
    ax2.plot(sp500_norm, label="S&P 500")
    ax2.legend()
    st.pyplot(fig2)

else:
    st.warning("Geçerli veri yok.")
