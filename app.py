import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(layout="wide")

# 🔥 HARD OVERRIDE (KESİN ÇALIŞIR)
st.markdown("""
<style>
/* EVERYTHING */
* {
    background-color: #000000 !important;
    color: #00FF9F !important;
    font-family: monospace !important;
}

/* APP */
.stApp {
    background-color: #000000 !important;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background-color: #050505 !important;
}

/* INPUT */
input, textarea {
    background-color: #111 !important;
    color: #00FF9F !important;
    border: 1px solid #00FF9F !important;
}

/* BUTTON */
button {
    background-color: #111 !important;
    color: #00FF9F !important;
    border: 1px solid #00FF9F !important;
}

/* DATAFRAME */
[data-testid="stDataFrame"] {
    background-color: #000 !important;
}

/* PANELS */
.panel {
    border: 1px solid #00FF9F;
    padding: 15px;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Portfolio Analyzer")

# -------------------------
# SIDEBAR
# -------------------------
st.sidebar.title("TERMINAL")
search = st.sidebar.text_input("Search")
asset_filter = st.sidebar.selectbox("Type", ["All","Stock","Crypto","Bond"])

# -------------------------
# ASSETS
# -------------------------
stocks = ["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA"]
crypto = ["BTC-USD","ETH-USD","SOL-USD"]
bonds = ["TLT","IEF","BND"]

tickers = stocks + crypto + bonds

# -------------------------
# DATA
# -------------------------
data = {}
for t in tickers:
    try:
        d = yf.download(t, period="1mo", progress=False)["Close"]
        if not d.empty:
            data[t] = d
    except:
        pass

prices = pd.DataFrame(data)

# -------------------------
# MARKET + HEATMAP
# -------------------------
c1, c2 = st.columns([2,1])

with c1:
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    latest = prices.iloc[-1]
    ret = prices.pct_change().iloc[-1]*100

    df = pd.DataFrame({
        "Ticker": latest.index,
        "Price": latest.values,
        "%": ret.values
    })

    df["Type"] = df["Ticker"].apply(
        lambda x: "Stock" if x in stocks else ("Crypto" if x in crypto else "Bond")
    )

    if asset_filter!="All":
        df = df[df["Type"]==asset_filter]

    if search:
        df = df[df["Ticker"].str.contains(search.upper())]

    st.subheader("Market")
    st.dataframe(df, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    fig = px.treemap(
        df,
        path=["Type","Ticker"],
        values="Price",
        color="%",
        color_continuous_scale="RdYlGn"
    )
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# PORTFOLIO
# -------------------------
st.subheader("Portfolio")

if "p" not in st.session_state:
    st.session_state.p = []

t = st.text_input("Ticker").upper()
q = st.number_input("Qty", min_value=0.0)

if st.button("Add"):
    if t and q>0:
        st.session_state.p.append((t,q))

# -------------------------
# CALC
# -------------------------
if st.session_state.p:

    vals = []
    labs = []

    for t,q in st.session_state.p:
        try:
            p = yf.download(t, period="1d", progress=False)["Close"].iloc[-1]
            vals.append(p*q)
            labs.append(t)
        except:
            pass

    total = sum(vals)

    st.write(f"Total: ${total:,.2f}")

    fig = go.Figure(data=[go.Pie(labels=labs, values=vals)])
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig)

    dfp = yf.download(labs, period="1mo", progress=False)["Close"]

    if isinstance(dfp, pd.Series):
        dfp = dfp.to_frame()

    norm = dfp/dfp.iloc[0]*100

    fig = go.Figure()
    for col in norm.columns:
        fig.add_trace(go.Scatter(x=norm.index,y=norm[col],name=col))

    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig)
