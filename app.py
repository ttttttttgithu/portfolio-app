import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Sayfa Genişliği
st.set_page_config(page_title="Portfolio Analyzer", layout="wide")
st.title("📊 Portfolio Analyzer")

# -------------------------
# VARLIK LİSTELERİ
# -------------------------
stocks = ["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","BRK-B","JPM","JNJ","V","PG","UNH","HD","MA","DIS","ADBE","NFLX","KO","PEP","XOM","CVX","ABBV","MRK","PFE"]
crypto = ["BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD","ADA-USD","DOGE-USD","DOT-USD","MATIC-USD","LTC-USD","TRX-USD","AVAX-USD","SHIB-USD","LINK-USD","ATOM-USD","XLM-USD","ETC-USD","ICP-USD","FIL-USD","APT-USD","ARB-USD","OP-USD","NEAR-USD","ALGO-USD","VET-USD"]
bonds = ["TLT","IEF","SHY","BND","AGG","LQD","HYG","TIP","MUB","VGIT","VCIT","VCSH","BLV","BSV","SCHZ","SPTL","SPSB","IGSB","FLOT","USIG","TFLO","VTIP","BIV","TLH","EDV"]

tickers = stocks + crypto + bonds

# -------------------------
# MARKET VERİSİ ÇEKME (GARANTİ YÖNTEM)
# -------------------------
@st.cache_data(ttl=600)
def get_all_market_data(ticker_list):
    data_list = []
    # İlerleme çubuğu
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(ticker_list):
        try:
            status_text.text(f"Veri çekiliyor: {t}")
            # Son 2 aylık veriyi çekiyoruz (değişim oranları için yeterli)
            df_temp = yf.download(t, period="2mo", progress=False)
            
            if not df_temp.empty:
                # Sütun yapısını düzelt (MultiIndex gelirse sadece Close al)
                if isinstance(df_temp.columns, pd.MultiIndex):
                    df_close = df_temp['Close'][t]
                else:
                    df_close = df_temp['Close']
                
                # Fiyat ve Değişimler
                last_price = float(df_close.iloc[-1])
                ret_1d = ((df_close.iloc[-1] / df_close.iloc[-2]) - 1) * 100 if len(df_close) > 1 else 0
                ret_1w = ((df_close.iloc[-1] / df_close.iloc[-6]) - 1) * 100 if len(df_close) > 5 else 0
                ret_1m = ((df_close.iloc[-1] / df_close.iloc[-22]) - 1) * 100 if len(df_close) > 21 else 0
                
                data_list.append({
                    "Ticker": t,
                    "Price": last_price,
                    "1D %": ret_1d,
                    "1W %": ret_1w,
                    "1M %": ret_1m,
                    "Asset Type": "Stock" if t in stocks else ("Crypto" if t in crypto else "Bond")
                })
        except Exception as e:
            continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(data_list)

# Veriyi Göster
market_df = get_all_market_data(tickers)

if not market_df.empty:
    st.subheader("📈 Market Overview")
    
    # Stil verme (Renkler)
    def color_negative_positive(val):
        if isinstance(val, (int, float)):
            color = 'red' if val < 0 else 'green'
            return f'color: {color}'
        return ''

    st.dataframe(market_df.style.applymap(color_negative_positive, subset=['1D %', '1W %', '1M %'])
                 .format({"Price": "{:.2f}", "1D %": "{:+.2f}%", "1W %": "{:+.2f}%", "1M %": "{:+.2f}%"}), 
                 use_container_width=True, height=400)

# -------------------------
# PORTFÖY GİRİŞİ
# -------------------------
st.divider()
st.subheader("💼 Add Portfolio")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

col1, col2, col3 = st.columns(3)
with col1:
    ticker_input = st.text_input("Ticker (örn: NVDA)").strip().upper()
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
# HESAPLAMALAR VE ANALİZ
# -------------------------
if st.session_state.portfolio:
    valid_assets = []
    for asset in st.session_state.portfolio:
        try:
            # Alış fiyatı (o günkü veri)
            h = yf.download(asset["ticker"], start=asset["date"] - pd.Timedelta(days=5), 
                            end=asset["date"] + pd.Timedelta(days=5), progress=False)['Close']
            
            # Güncel fiyat
            c = yf.download(asset["ticker"], period="1d", progress=False)['Close']
            
            if not h.empty and not c.empty:
                b_price = float(h.iloc[-1])
                c_price = float(c.iloc[-1])
                
                valid_assets.append({
                    "ticker": asset["ticker"],
                    "value": c_price * asset["quantity"],
                    "cost": b_price * asset["quantity"],
                    "pnl": (c_price - b_price) * asset["quantity"],
                    "pnl_pct": ((c_price / b_price) - 1) * 100
                })
        except: continue

    if valid_assets:
        res_df = pd.DataFrame(valid_assets)
        st.divider()
        st.subheader("📊 Portfolio Summary")
        
        c1, c2, c3 = st.columns(3)
        total_val = res_df['value'].sum()
        total_pnl = res_df['pnl'].sum()
        total_pnl_p = (total_pnl / res_df['cost'].sum()) * 100
        
        c1.metric("Total Value", f"${total_val:,.2f}")
        c2.metric("Total PnL ($)", f"${total_pnl:,.2f}")
        c3.metric("Total PnL (%)", f"{total_pnl_p:.2f}%")
        
        # Grafik
        fig, ax = plt.subplots(figsize=(6,3))
        ax.pie(res_df['value'], labels=res_df['ticker'], autopct='%1.1f%%')
        st.pyplot(fig)
