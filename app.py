import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, time
from zoneinfo import ZoneInfo
from analyzer import analyse_symbol, get_candidate_symbols, rupee, market_session

st.set_page_config(page_title="₹200 Market Coach", page_icon="📈", layout="wide")
st.title("📈 ₹200 Market Coach")
st.caption("A beginner-friendly market research dashboard — not an automated trading or guaranteed-profit system.")

with st.sidebar:
    st.header("Your practice settings")
    budget = st.number_input("Maximum amount (₹)", min_value=1, max_value=200, value=200, step=10)
    risk_pct = st.slider("Maximum planned loss per trade (%)", 1, 5, 2)
    watchlist_text = st.text_area("NSE symbols (one per line)", "IDEA\nYESBANK\nSUZLON\nNHPC\nIRFC\nIOC\nBANKBARODA\nPNB\nTATAPOWER\nONGC")
    st.caption("Symbols are examples for screening only, not recommendations.")
    run = st.button("Analyse watchlist", type="primary", use_container_width=True)

st.warning("₹200 is a very small trading budget. Brokerage, STT, exchange charges, GST, stamp duty and bid–ask spread can consume a large part of any tiny gain. Do not use intraday leverage, F&O, margin or borrowed money. Consider paper trading first.")

now = datetime.now(ZoneInfo("Asia/Kolkata"))
st.info(f"India time: {now:%d %b %Y, %I:%M:%S %p} · {market_session(now)} · NSE regular equity session is generally 9:15 AM–3:30 PM on trading days.")

st.subheader("How to use this")
st.markdown("""
1. Run the scan before the market opens or after 9:30 AM.
2. Review the data timestamp and the risk notes. Free Yahoo Finance data may be delayed or incomplete.
3. Treat every result as a **watchlist idea**, not a buy instruction. Confirm the live quote and charges inside Groww.
4. Start with paper trading. Never buy just because a score is high.
""")

symbols = [x.strip().upper() for x in watchlist_text.splitlines() if x.strip()]
if run or "results" not in st.session_state:
    with st.spinner("Fetching public market data and calculating simple indicators..."):
        rows = []
        for symbol in symbols[:25]:
            try:
                rows.append(analyse_symbol(symbol, budget, risk_pct))
            except Exception as e:
                rows.append({"Symbol": symbol, "Status": f"Data unavailable: {str(e)[:90]}"})
        st.session_state.results = rows

df = pd.DataFrame(st.session_state.results)
if not df.empty:
    st.subheader("Screening results")
    if "Score" in df.columns:
        df = df.sort_values("Score", ascending=False, na_position="last")
    st.dataframe(df, use_container_width=True, hide_index=True)
    valid = df[df.get("Status", pd.Series(index=df.index, dtype=str)).eq("Screened")].copy() if "Status" in df else pd.DataFrame()
    if not valid.empty:
        pick = st.selectbox("View chart", valid["Symbol"].tolist())
        hist = yf.Ticker(f"{pick}.NS").history(period="3mo", interval="1d", auto_adjust=True)
        if not hist.empty:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=hist.index, open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"], name=pick))
            fig.update_layout(height=420, xaxis_rangeslider_visible=False, title=f"{pick} · 3-month daily candles")
            st.plotly_chart(fig, use_container_width=True)
        st.caption("Indicator scores are simple educational filters. They do not predict tomorrow's opening price or the best time to sell.")

st.subheader("A sensible ₹200 beginner plan")
st.markdown("""
- Prefer **learning and paper trading** over frequent intraday trades.
- With ₹200, only consider a whole-share cash purchase if the share price plus estimated costs fits your budget. Fractional shares are generally not available for Indian listed equities.
- If the app says “No setup”, do nothing. Cash is a valid position.
- There is no reliable universal sell time. Decide an exit before entering; a stop-loss can still slip or fail to execute at the intended price.
- This app never places orders, never stores Groww credentials and never asks for an API token.
""")
st.caption("Data source: Yahoo Finance public endpoints via yfinance (not an official exchange feed). Verify all prices and order details in Groww before acting.")
