import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# -------------------------
# PAGE CONFIG + STYLE
# -------------------------
st.set_page_config(page_title="Portfolio Analyzer", page_icon="📊", layout="wide")

st.markdown("""
<style>
body {background-color: #0E1117; color: white;}
.metric-box {
    background-color: #1c1f26;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.5);
}
h1, h2, h3 {color: #00FFAA;}
</style>
""", unsafe_allow_html=True)

st.title("📊 Portfolio Analyzer")

# -------------------------
# SIDEBAR
# -------------------------
st.sidebar.title("📊 Controls")
selected_type = st.sidebar.selectbox(
    "Asset Type Filter",
    ["All", "Stock", "Crypto", "Bond"]
)

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

# -------------------------
# MARKET DATA
# -------------------------
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

    if selected_type != "All":
        df = df[df["Asset Type"] == selected_type]

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
    ticker = st.text_input("Ticker").upper().strip()

with col2:
    date = st.date_input("Buy Date")

with col3:
    quantity = st.number_input("Quantity", min_value=0.0)

if st.button("Add Asset"):
    if ticker and quantity > 0:
        st.session_state.portfolio.append({
            "ticker": ticker,
            "date": pd.to_datetime(date),
            "quantity": quantity
        })

portfolio = st.session_state.portfolio

# -------------------------
# CALCULATIONS
# -------------------------
valid_assets = []

for asset in portfolio:
    t = asset["ticker"]
    d = asset["date"]

    try:
        hist = yf.download(t, start=d - pd.Timedelta(days=10), end=d + pd.Timedelta(days=10), progress=False)

        if hist.empty:
            continue

        hist = hist.reset_index()
        hist["diff"] = (hist["Date"] - d).abs()
        row = hist.loc[hist["diff"].idxmin()]

        buy_price = float(row["Close"])
        current_price = float(yf.download(t, period="1d", progress=False)["Close"].iloc[-1])

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

    pnl = total_value - total_cost
    pnl_pct = (pnl / total_cost) * 100 if total_cost > 0 else 0

    st.subheader("📊 Portfolio Summary")

    c1, c2, c3 = st.columns(3)

    c1.markdown(f"<div class='metric-box'><h3>Total Value</h3><h2>${total_value:,.2f}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-box'><h3>PnL</h3><h2>${pnl:,.2f}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-box'><h3>PnL %</h3><h2>{pnl_pct:.2f}%</h2></div>", unsafe_allow_html=True)

    tick_list = [a["ticker"] for a in valid_assets]
    start_date = min(a["date"] for a in valid_assets)

    price_data = yf.download(tick_list, start=start_date, progress=False)["Close"]

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

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=portfolio_norm.index, y=portfolio_norm, name="Portfolio"))
    fig.add_trace(go.Scatter(x=sp500_norm.index, y=sp500_norm, name="S&P 500"))

    fig.update_layout(template="plotly_dark", height=400)

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Geçerli veri yok")
