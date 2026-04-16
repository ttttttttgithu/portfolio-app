import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(layout="wide")

# 🔥 FORCE TERMINAL THEME
st.markdown("""
<style>
html, body, [class*="css"]  {
    background-color: #000000 !important;
    color: #00FF9F !important;
    font-family: monospace !important;
}
.block-container {
    background-color: #000000 !important;
}
section[data-testid="stSidebar"] {
    background-color: #0a0a0a !important;
}
h1, h2, h3, h4, h5, h6, p, div {
    color: #00FF9F !important;
}
[data-testid="stDataFrame"] {
    background-color: #0a0a0a !important;
    color: #00FF9F !important;
}
input, textarea {
    background-color: #111 !important;
    color: #00FF9F !important;
}
button {
    background-color: #111 !important;
    color: #00FF9F !important;
    border: 1px solid #00FF9F !important;
}
.panel {
    background-color: #0a0a0a;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #00FF9F;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Portfolio Analyzer")

# -------------------------
# SIDEBAR
# -------------------------
st.sidebar.title("🔎 Terminal Controls")
search = st.sidebar.text_input("Search Ticker")
asset_filter = st.sidebar.selectbox("Asset Type", ["All", "Stock", "Crypto", "Bond"])

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
# DATA
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

# -------------------------
# MARKET + HEATMAP
# -------------------------
col1, col2 = st.columns([2,1])

with col1:
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    if len(all_data) > 0:
        close_prices = pd.DataFrame(all_data)

        latest_prices = close_prices.iloc[-1]
        returns_1d = close_prices.pct_change(1).iloc[-1] * 100

        df = pd.DataFrame({
            "Ticker": latest_prices.index,
            "Price": latest_prices.values,
            "1D %": returns_1d.values
        })

        df["Asset Type"] = df["Ticker"].apply(
            lambda x: "Stock" if x in stocks else ("Crypto" if x in crypto else "Bond")
        )

        if asset_filter != "All":
            df = df[df["Asset Type"] == asset_filter]

        if search:
            df = df[df["Ticker"].str.contains(search.upper())]

        st.subheader("📈 Market Overview")
        st.dataframe(df, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    if len(all_data) > 0 and not df.empty:
        fig = px.treemap(
            df,
            path=["Asset Type", "Ticker"],
            values="Price",
            color="1D %",
            color_continuous_scale="RdYlGn"
        )
        fig.update_layout(template="plotly_dark", margin=dict(t=20,l=0,r=0,b=0))
        st.subheader("🔥 Heatmap")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# PORTFOLIO INPUT
# -------------------------
st.markdown('<div class="panel">', unsafe_allow_html=True)

st.subheader("💼 Add Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

c1, c2, c3 = st.columns(3)

with c1:
    ticker = st.text_input("Ticker").upper().strip()

with c2:
    date = st.date_input("Buy Date")

with c3:
    quantity = st.number_input("Quantity", min_value=0.0)

if st.button("Add Asset"):
    if ticker and quantity > 0:
        st.session_state.portfolio.append({
            "ticker": ticker,
            "date": pd.to_datetime(date),
            "quantity": quantity
        })

portfolio = st.session_state.portfolio
st.markdown('</div>', unsafe_allow_html=True)

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

    st.markdown('<div class="panel">', unsafe_allow_html=True)

    total_value = sum(a["value"] for a in valid_assets)
    total_cost = sum(a["cost"] for a in valid_assets)
    pnl = total_value - total_cost

    st.subheader("📊 Portfolio Summary")
    st.write(f"Total Value: ${total_value:,.2f}")
    st.write(f"PnL: ${pnl:,.2f}")

    values = [a["value"] for a in valid_assets]
    labels = [a["ticker"] for a in valid_assets]

    fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # PERFORMANCE
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    tickers = [a["ticker"] for a in valid_assets]
    start_date = min(a["date"] for a in valid_assets)

    price_data = yf.download(tickers, start=start_date, progress=False)["Close"]

    if isinstance(price_data, pd.Series):
        price_data = price_data.to_frame()

    norm = price_data / price_data.iloc[0] * 100

    fig = go.Figure()

    for col in norm.columns:
        fig.add_trace(go.Scatter(x=norm.index, y=norm[col], name=col))

    fig.update_layout(template="plotly_dark")

    st.subheader("📈 Performance")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.warning("Geçerli veri yok")
