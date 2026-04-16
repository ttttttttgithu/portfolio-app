import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📊 Portfolio Analyzer")

# -------------------------
# MANUAL PORTFOLIO BUILDER (TOP - FINAL FIX)
# -------------------------
st.subheader("🛠️ Manual Portfolio Builder")

if "manual_portfolio" not in st.session_state:
    st.session_state.manual_portfolio = []

c1, c2, c3, c4 = st.columns(4)

with c1:
    asset_name = st.text_input("Asset Name", key="mp_name")

with c2:
    buy_price_manual = st.number_input("Buy Price", min_value=0.0, key="mp_price")

with c3:
    quantity_manual = st.number_input("Quantity", min_value=0.0, key="mp_qty")

with c4:
    add_manual = st.button("➕ Add", key="mp_add_btn")

if add_manual:
    if asset_name != "" and buy_price_manual > 0 and quantity_manual > 0:
        st.session_state.manual_portfolio.append({
            "name": asset_name.upper(),
            "price": buy_price_manual,
            "quantity": quantity_manual
        })
        st.success("Asset eklendi!")

manual_assets = st.session_state.manual_portfolio

if len(manual_assets) > 0:
    st.markdown("### 📋 Manual Portfolio")

    df_manual = pd.DataFrame(manual_assets)
    df_manual["Value"] = df_manual["price"] * df_manual["quantity"]

    st.dataframe(df_manual, use_container_width=True)

    total_value_manual = df_manual["Value"].sum()
    st.write(f"**Total Value: ${total_value_manual:,.2f}**")

    fig_manual, ax_manual = plt.subplots()
    ax_manual.pie(df_manual["Value"], labels=df_manual["name"], autopct="%1.1f%%")
    ax_manual.set_title("Manual Portfolio Allocation")
    st.pyplot(fig_manual)

# -------------------------
# MARKET OVERVIEW
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

all_data = {}

with st.spinner("Market data yükleniyor..."):
    for t in tickers:
        try:
            temp = yf.download(t, period="1mo", progress=False)["Close"]
            if not temp.empty:
                all_data[t] = temp
        except:
            continue

if len(all_data) > 0:
    close_prices = pd.DataFrame(all_data)

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
    st.dataframe(df, use_container_width=True)

# -------------------------
# ORIGINAL PORTFOLIO
# -------------------------
st.subheader("💼 Add Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

c1, c2, c3, c4 = st.columns(4)

with c1:
    ticker = st.text_input("Ticker", key="p_ticker").strip().upper()

with c2:
    date = st.date_input("Buy Date", key="p_date")
    if date > pd.Timestamp.today().date():
        date = pd.Timestamp.today().date()

with c3:
    quantity = st.number_input("Quantity", min_value=0.0, key="p_qty")

with c4:
    add_asset = st.button("➕ Add", key="p_add_btn")

if add_asset:
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
    try:
        t = asset["ticker"]
        d = asset["date"]

        hist = yf.download(t, start=d - pd.Timedelta(days=10), end=d + pd.Timedelta(days=10), progress=False)
        if hist.empty:
            continue

        hist = hist.reset_index()
        hist["diff"] = (hist["Date"] - d).abs()
        buy_price = float(hist.loc[hist["diff"].idxmin()]["Close"])

        current_price = float(yf.download(t, period="1d", progress=False)["Close"].dropna().iloc[-1])

        value = current_price * asset["quantity"]
        cost = buy_price * asset["quantity"]

        asset["value"] = value
        asset["cost"] = cost

        valid_assets.append(asset)

    except:
        continue

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

    fig, ax = plt.subplots()
    ax.pie([a["weight"] for a in valid_assets],
           labels=[a["ticker"] for a in valid_assets],
           autopct="%1.1f%%")
    st.pyplot(fig)

else:
    st.warning("Geçerli veri yok. Ticker doğru mu kontrol et (örn: AAPL, BTC-USD)")
