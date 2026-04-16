import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(layout="wide", page_title="Terminal", page_icon="📊")

# -------------------------
# BLOOMBERG STYLE CSS
# -------------------------
st.markdown("""
<style>

/* MAIN BACKGROUND */
.stApp {
    background-color: #0a0a0a;
    color: #00ff9f;
    font-family: monospace;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background-color: #111;
}

/* PANELS */
.panel {
    background-color: #111;
    padding: 15px;
    border-radius: 8px;
    border: 1px solid #222;
}

/* TITLE */
.title {
    font-size: 28px;
    font-weight: bold;
    color: #00ff9f;
}

/* METRICS */
.metric {
    font-size: 20px;
    font-weight: bold;
}

.green { color: #00ff9f; }
.red { color: #ff4d4d; }

/* TABLE */
[data-testid="stDataFrame"] {
    background-color: #111;
    border-radius: 8px;
}

</style>
""", unsafe_allow_html=True)

# -------------------------
# HEADER
# -------------------------
st.markdown('<div class="title">📊 BLOOMBERG TERMINAL</div>', unsafe_allow_html=True)

# -------------------------
# SIDEBAR
# -------------------------
st.sidebar.title("TERMINAL")

asset_type = st.sidebar.selectbox(
    "Asset Type",
    ["All", "Stock", "Crypto", "Bond"]
)

# -------------------------
# ASSETS
# -------------------------
stocks = ["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA"]
crypto = ["BTC-USD","ETH-USD","SOL-USD"]
bonds = ["TLT","IEF","BND"]

tickers = stocks + crypto + bonds

# -------------------------
# LOAD DATA
# -------------------------
data = {}

for t in tickers:
    try:
        df = yf.download(t, period="1mo", progress=False)["Close"]
        if not df.empty:
            data[t] = df
    except:
        pass

prices = pd.DataFrame(data)

# -------------------------
# GRID LAYOUT
# -------------------------
col1, col2 = st.columns([2,1])

# -------------------------
# LEFT PANEL (MARKET)
# -------------------------
with col1:
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    st.subheader("MARKET DATA")

    latest = prices.iloc[-1]
    ret = prices.pct_change().iloc[-1] * 100

    df = pd.DataFrame({
        "Ticker": latest.index,
        "Price": latest.values,
        "%": ret.values
    })

    df["Type"] = df["Ticker"].apply(
        lambda x: "Stock" if x in stocks else ("Crypto" if x in crypto else "Bond")
    )

    if asset_type != "All":
        df = df[df["Type"] == asset_type]

    st.dataframe(df, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# RIGHT PANEL (METRICS)
# -------------------------
with col2:
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    st.subheader("MARKET SUMMARY")

    try:
        sp = yf.download("^GSPC", period="5d", progress=False)["Close"]
        change = (sp.iloc[-1] / sp.iloc[0] - 1) * 100

        color = "green" if change > 0 else "red"

        st.markdown(f'<div class="metric {color}">S&P 500: {change:.2f}%</div>', unsafe_allow_html=True)

    except:
        st.write("No data")

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# PORTFOLIO
# -------------------------
st.markdown('<div class="panel">', unsafe_allow_html=True)

st.subheader("PORTFOLIO")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

c1, c2 = st.columns(2)

with c1:
    ticker = st.text_input("Ticker").upper()

with c2:
    qty = st.number_input("Quantity", min_value=0.0)

if st.button("ADD"):
    if ticker and qty > 0:
        st.session_state.portfolio.append((ticker, qty))

portfolio = st.session_state.portfolio

# -------------------------
# PORTFOLIO CALC
# -------------------------
if portfolio:

    values = []
    labels = []

    for t, q in portfolio:
        try:
            price = yf.download(t, period="1d", progress=False)["Close"].iloc[-1]
            values.append(price * q)
            labels.append(t)
        except:
            pass

    total = sum(values)

    st.markdown(f"<div class='metric green'>Total Value: ${total:,.2f}</div>", unsafe_allow_html=True)

    # PIE
    fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# PERFORMANCE CHART
# -------------------------
st.markdown('<div class="panel">', unsafe_allow_html=True)

st.subheader("PERFORMANCE")

if portfolio:

    tick_list = [t for t, q in portfolio]

    df = yf.download(tick_list, period="1mo", progress=False)["Close"]

    if isinstance(df, pd.Series):
        df = df.to_frame()

    norm = df / df.iloc[0] * 100

    fig = go.Figure()

    for col in norm.columns:
        fig.add_trace(go.Scatter(x=norm.index, y=norm[col], name=col))

    fig.update_layout(template="plotly_dark")

    st.plotly_chart(fig, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)
