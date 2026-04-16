import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Portfolio Analyzer", layout="wide")
st.title("📊 Portfolio Analyzer")

# -------------------------
# ASSET LISTS
# -------------------------
stocks = ["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","BRK-B","JPM","JNJ","V","PG","UNH","HD","MA","DIS","ADBE","NFLX","KO","PEP","XOM","CVX","ABBV","MRK","PFE"]
crypto = ["BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD","ADA-USD","DOGE-USD","DOT-USD","MATIC-USD","LTC-USD","TRX-USD","AVAX-USD","SHIB-USD","LINK-USD","ATOM-USD","XLM-USD","ETC-USD","ICP-USD","FIL-USD","APT-USD","ARB-USD","OP-USD","NEAR-USD","ALGO-USD","VET-USD"]
bonds = ["TLT","IEF","SHY","BND","AGG","LQD","HYG","TIP","MUB","VGIT","VCIT","VCSH","BLV","BSV","SCHZ","SPTL","SPSB","IGSB","FLOT","USIG","TFLO","VTIP","BIV","TLH","EDV"]

tickers = stocks + crypto + bonds

# -------------------------
# MARKET OVERVIEW (FIXED DATA FETCHING)
# -------------------------
@st.cache_data(ttl=3600)
def load_market_data(ticker_list):
    # Toplu veri indirme (Daha hızlı ve stabil)
    raw_data = yf.download(ticker_list, period="2mo", progress=False)["Close"]
    
    # Veri temizleme: Eğer sütunlar MultiIndex ise düzelt
    if isinstance(raw_data.columns, pd.MultiIndex):
        raw_data.columns = raw_data.columns.get_level_values(1)
    
    return raw_data

with st.spinner("Market verileri güncelleniyor..."):
    close_prices = load_market_data(tickers)

if not close_prices.empty:
    # Son geçerli fiyatları al (NaN olmayan son satırlar)
    latest_prices = close_prices.ffill().iloc[-1]
    
    # Değişimleri hesapla
    returns_1d = close_prices.pct_change(1).iloc[-1] * 100
    returns_1w = close_prices.pct_change(5).iloc[-1] * 100
    returns_1m = close_prices.pct_change(21).iloc[-1] * 100

    df = pd.DataFrame({
        "Ticker": latest_prices.index,
        "Price": latest_prices.values,
        "1D %": returns_1d.values,
        "1W %": returns_1w.values,
        "1M %": returns_1m.values
    }).dropna(subset=["Price"]) # Fiyatı olmayanları listeden çıkar

    df["Asset Type"] = df["Ticker"].apply(
        lambda x: "Stock" if x in stocks else ("Crypto" if x in crypto else "Bond")
    )

    st.subheader("📈 Market Overview")
    st.dataframe(df.style.format({
        "Price": "{:.2f}",
        "1D %": "{:+.2f}%",
        "1W %": "{:+.2f}%",
        "1M %": "{:+.2f}%"
    }), use_container_width=True)

# -------------------------
# PORTFOLIO INPUT
# -------------------------
st.divider()
st.subheader("💼 Add Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

col1, col2, col3 = st.columns(3)
with col1:
    ticker_input = st.text_input("Ticker (örn: AAPL)").strip().upper()
with col2:
    buy_date = st.date_input("Buy Date")
with col3:
    quantity = st.number_input("Quantity", min_value=0.0, step=0.1)

if st.button("Add Asset"):
    if ticker_input != "" and quantity > 0:
        st.session_state.portfolio.append({
            "ticker": ticker_input,
            "date": pd.to_datetime(buy_date),
            "quantity": quantity
        })
        st.success(f"{ticker_input} eklendi!")

# -------------------------
# PORTFOLIO CALCULATIONS
# -------------------------
valid_assets = []
for asset in st.session_state.portfolio:
    t = asset["ticker"]
    d = asset["date"]
    
    try:
        # Alış fiyatı için o tarihe yakın veri çek
        hist = yf.download(t, start=d - pd.Timedelta(days=7), end=d + pd.Timedelta(days=7), progress=False)["Close"]
        if hist.empty: continue
        
        buy_price = float(hist.ffill().iloc[-1])
        
        # Güncel fiyat
        current_data = yf.download(t, period="1d", progress=False)["Close"]
        if current_data.empty: continue
        current_price = float(current_data.ffill().iloc[-1])
        
        asset["buy_price"] = buy_price
        asset["current_price"] = current_price
        asset["value"] = current_price * asset["quantity"]
        asset["cost"] = buy_price * asset["quantity"]
        valid_assets.append(asset)
    except:
        continue

if valid_assets:
    st.divider()
    st.subheader("📊 Portfolio Summary")
    
    total_value = sum(a["value"] for a in valid_assets)
    total_cost = sum(a["cost"] for a in valid_assets)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Value", f"${total_value:,.2f}")
    m2.metric("Total PnL", f"${total_pnl:,.2f}", f"{total_pnl_pct:.2f}%")
    
    # Pasta Grafiği
    fig1, ax1 = plt.subplots()
    ax1.pie([a["value"] for a in valid_assets], labels=[a["ticker"] for a in valid_assets], autopct='%1.1f%%')
    st.pyplot(fig1)

    # Risk Analizi (S&P 500 Karşılaştırmalı)
    tickers_p = [a["ticker"] for a in valid_assets]
    start_date = min(a["date"] for a in valid_assets)
    
    combined_data = yf.download(tickers_p + ["^GSPC"], start=start_date, progress=False)["Close"]
    if isinstance(combined_data, pd.Series): combined_data = combined_data.to_frame()
    
    # Portföy zaman serisi hesaplama
    portfolio_ts = pd.Series(0, index=combined_data.index)
    for a in valid_assets:
        if a["ticker"] in combined_data.columns:
            portfolio_ts += combined_data[a["ticker"]] * a["quantity"]
    
    # Normalizasyon (Başlangıç 100)
    port_norm = (portfolio_ts / portfolio_ts.iloc[0]) * 100
    sp500_norm = (combined_data["^GSPC"] / combined_data["^GSPC"].iloc[0]) * 100

    st.subheader("📈 Performance vs S&P 500")
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(port_norm, label="My Portfolio")
    ax2.plot(sp500_norm, label="S&P 500")
    ax2.legend()
    st.pyplot(fig2)

    # Risk Metrikleri
    returns = portfolio_ts.pct_change().dropna()
    market_returns = combined_data["^GSPC"].pct_change().dropna()
    
    # Verileri hizala
    df_risk = pd.concat([returns, market_returns], axis=1).dropna()
    df_risk.columns = ['port', 'mkt']
    
    if len(df_risk) > 5:
        beta = df_risk.cov().iloc[0,1] / df_risk['mkt'].var()
        vol = returns.std() * np.sqrt(252)
        st.subheader("📉 Risk Metrics")
        c1, c2 = st.columns(2)
        c1.write(f"**Beta:** {beta:.2f}")
        c2.write(f"**Annual Volatility:** {vol:.2%}")
else:
    st.info("Lütfen analiz için portföyünüze varlık ekleyin.")
