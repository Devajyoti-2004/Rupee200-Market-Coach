import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analyzer import (
    add_indicators, analyse_symbol, exit_monitor, get_candidate_symbols,
    get_history, get_market_overview, market_session, opening_check,
    premarket_summary, rupee, simple_backtest
)

st.set_page_config(page_title="₹200 Market Coach V3", page_icon="📈", layout="wide")
TZ = ZoneInfo("Asia/Kolkata")
LEDGER = Path("paper_trades.csv")
st.title("📈 ₹200 Market Coach — V3")
st.caption("NSE cash-equity decision support • ₹200 budget cap • Paper-trading first")

with st.sidebar:
    st.header("Capital & watchlist")
    budget = st.number_input("Maximum total budget (₹)", min_value=1, max_value=200, value=200, step=10)
    risk_pct = st.slider("Minimum stop-distance floor (%)", 1, 5, 2)
    cost_buffer = st.slider("Estimated cost buffer (%)", 0.0, 2.0, 0.5, 0.1,
                            help="Planning buffer only; actual Groww/exchange charges vary.")
    symbols_text = st.text_area("NSE symbols (one per line)", "\n".join(get_candidate_symbols()))
    symbols = get_candidate_symbols(symbols_text.splitlines(), limit=30)
    st.caption("Data provider: Yahoo Finance via yfinance; not an official live NSE feed.")

now = datetime.now(TZ)
a, b, c = st.columns(3)
a.metric("India time", now.strftime("%d %b %Y • %I:%M %p"))
b.metric("Market session", market_session(now))
c.metric("Available capital", rupee(budget))
st.warning("No guaranteed trades or returns. A signal is a screening result, not a personalized instruction. With ₹200, charges and spread can outweigh small gains. Never exceed your budget.")

tabs = st.tabs(["🧭 Today's Plan", "🌅 Pre-market", "🔎 Stock Scanner", "⏱ Opening & Exit Monitor", "📈 Charts", "🧪 Backtest", "📝 Paper Journal"])

with tabs[0]:
    st.subheader("Today's decision plan")
    st.write("The app ranks a watchlist, checks the latest available daily trend, then asks for intraday confirmation. It may correctly recommend NO TRADE.")
    if st.button("Build today's plan", type="primary"):
        rows, progress = [], st.progress(0)
        for i, symbol in enumerate(symbols):
            try:
                rows.append(analyse_symbol(symbol, budget, risk_pct, cost_buffer))
            except Exception as exc:
                rows.append({"Symbol": symbol, "Screen status": f"Unavailable: {str(exc)[:100]}", "Score / 5": -1})
            progress.progress((i + 1) / max(1, len(symbols)))
        st.session_state["daily_plan"] = rows
    if "daily_plan" in st.session_state:
        plan = pd.DataFrame(st.session_state["daily_plan"])
        if "Score / 5" in plan:
            plan = plan.sort_values("Score / 5", ascending=False)
        st.dataframe(plan, use_container_width=True, hide_index=True)
        candidates = plan[plan.get("Screen status", pd.Series(dtype=str)).astype(str).str.startswith("WATCH")]
        if candidates.empty:
            st.info("No daily candidate passed the screen. Keeping the ₹200 uninvested is a valid result.")
        else:
            st.success("Daily trend candidates found. They are WATCHLIST candidates only; wait for opening confirmation and verify the live quote before any order.")
        st.download_button("Download today's plan CSV", plan.to_csv(index=False).encode(), "todays_plan.csv", "text/csv")
    else:
        st.info("Press “Build today's plan” to scan the watchlist. No scan runs automatically in the background.")

with tabs[1]:
    st.subheader("Pre-market context")
    st.write("This section shows the latest available daily index closes and their prior-session changes. Yahoo Finance does not provide a dependable official NSE pre-open feed here.")
    if st.button("Refresh market context"):
        with st.spinner("Fetching latest available index data..."):
            st.session_state["market_context"] = premarket_summary()
    if "market_context" in st.session_state:
        context = st.session_state["market_context"]
        st.metric("Previous-session context", context["bias"])
        st.write(context["message"])
        st.dataframe(context["overview"], use_container_width=True, hide_index=True)
    else:
        st.info("Refresh to load Nifty, Sensex and selected global-market context. These are latest available daily values, not live pre-market indications.")

with tabs[2]:
    st.subheader("Multi-factor NSE cash-market scanner")
    st.write("Trend, RSI, volume, ATR and budget fit. Ranking does not predict returns.")
    if st.button("Scan watchlist now"):
        results, progress = [], st.progress(0)
        for i, symbol in enumerate(symbols):
            try:
                results.append(analyse_symbol(symbol, budget, risk_pct, cost_buffer))
            except Exception as exc:
                results.append({"Symbol": symbol, "Screen status": f"Unavailable: {str(exc)[:100]}", "Score / 5": -1})
            progress.progress((i + 1) / max(1, len(symbols)))
        st.session_state["scan_results"] = results
    if "scan_results" in st.session_state:
        df = pd.DataFrame(st.session_state["scan_results"]).sort_values("Score / 5", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Download scan CSV", df.to_csv(index=False).encode(), "nse_scan.csv", "text/csv")
    st.caption("Quantity is calculated using the latest available daily close and a configurable cost buffer. Recalculate using the actual live quote before placing any order.")

with tabs[3]:
    st.subheader("Intraday entry confirmation")
    st.write("Run after 9:30 AM IST. The check uses the latest session's available 5-minute candles, session VWAP and prior-candle breakout. Delayed or stale candles can produce misleading results.")
    chosen = st.selectbox("Stock to check", symbols, key="opening_symbol")
    if st.button("Check entry conditions"):
        try:
            st.session_state["opening_check"] = opening_check(chosen, budget, cost_buffer)
        except Exception as exc:
            st.error(f"Intraday check unavailable: {exc}")
    if "opening_check" in st.session_state:
        item = st.session_state["opening_check"]
        st.dataframe(pd.DataFrame([item]), use_container_width=True, hide_index=True)
        st.info("Even SETUP WATCH is not an instruction to buy. Verify live quote, liquidity, spread and charges in Groww.")
    st.divider()
    st.subheader("Monitor a position you already hold (manual inputs)")
    x1, x2, x3 = st.columns(3)
    with x1:
        pos_symbol = st.selectbox("Held stock", symbols, key="held_symbol")
        pos_qty = st.number_input("Quantity held", min_value=1, max_value=10000, value=1)
    with x2:
        entry = st.number_input("Your entry price (₹)", min_value=0.01, value=10.0)
        stop = st.number_input("Your stop level (₹)", min_value=0.01, value=9.5)
    with x3:
        target = st.number_input("Your target level (₹)", min_value=0.01, value=11.0)
    if st.button("Check exit conditions"):
        try:
            st.session_state["exit_check"] = exit_monitor(pos_symbol, pos_qty, entry, stop, target)
        except Exception as exc:
            st.error(f"Exit check unavailable: {exc}")
    if "exit_check" in st.session_state:
        st.dataframe(pd.DataFrame([st.session_state["exit_check"]]), use_container_width=True, hide_index=True)
        st.caption("Exit checks use the latest available 5-minute data, which may be delayed. A stop level is not a guaranteed execution price.")

with tabs[4]:
    st.subheader("Price chart and indicators")
    chart_symbol = st.selectbox("Chart stock", symbols, key="chart_symbol")
    period = st.selectbox("Period", ["3mo", "6mo", "1y", "2y"], index=2)
    if st.button("Load chart"):
        try:
            data = add_indicators(get_history(chart_symbol, period, "1d")).dropna(subset=["SMA20", "SMA50"])
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=data.index, open=data["Open"], high=data["High"], low=data["Low"], close=data["Close"], name="Price"))
            fig.add_trace(go.Scatter(x=data.index, y=data["SMA20"], name="SMA20"))
            fig.add_trace(go.Scatter(x=data.index, y=data["SMA50"], name="SMA50"))
            fig.update_layout(height=520, xaxis_rangeslider_visible=False, title=f"{chart_symbol} — daily")
            st.plotly_chart(fig, use_container_width=True)
            last = data.iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("Latest close", rupee(last["Close"]))
            m2.metric("RSI", f"{last['RSI']:.1f}")
            m3.metric("ATR", rupee(last["ATR"]))
        except Exception as exc:
            st.error(f"Chart unavailable: {exc}")

with tabs[5]:
    st.subheader("Historical strategy test")
    bt_symbol = st.selectbox("Backtest stock", symbols, key="bt_symbol")
    bt_period = st.selectbox("History", ["1y", "2y", "5y"], index=1, key="bt_period")
    if st.button("Run backtest"):
        try:
            result = simple_backtest(bt_symbol, bt_period)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Strategy return", f"{result['total_return']:.2f}%")
            m2.metric("Buy & hold", f"{result['buy_hold']:.2f}%")
            m3.metric("Max drawdown", f"{result['max_drawdown']:.2f}%")
            m4.metric("Entries", result["trades"])
            st.line_chart(result["equity"])
            st.caption("Illustrative daily strategy only; excludes transaction costs, taxes, slippage and market impact. Past performance is not predictive.")
        except Exception as exc:
            st.error(f"Backtest failed: {exc}")

with tabs[6]:
    st.subheader("Paper-trading journal")
    st.caption("The free Render filesystem may reset on redeploy or restart. Download your CSV regularly; use a managed database before relying on long-term records.")
    with st.form("paper_trade"):
        f1, f2, f3 = st.columns(3)
        with f1:
            trade_symbol = st.selectbox("Symbol", symbols, key="paper_symbol")
            trade_date = st.date_input("Trade date", value=now.date())
        with f2:
            qty = st.number_input("Quantity", min_value=1, max_value=10000, value=1)
            buy_price = st.number_input("Entry price (₹)", min_value=0.01, value=10.0, key="paper_buy")
        with f3:
            sell_price = st.number_input("Exit price (₹)", min_value=0.01, value=10.0, key="paper_sell")
            note = st.text_input("Notes")
        submitted = st.form_submit_button("Save closed paper trade")
    if submitted:
        profit = (sell_price - buy_price) * qty
        new_row = pd.DataFrame([{"Date": str(trade_date), "Symbol": trade_symbol, "Qty": qty,
                                 "Entry": buy_price, "Exit": sell_price,
                                 "P/L before charges": round(profit, 2), "Notes": note}])
        old = pd.read_csv(LEDGER) if LEDGER.exists() else pd.DataFrame()
        pd.concat([old, new_row], ignore_index=True).to_csv(LEDGER, index=False)
        st.success("Paper trade recorded for this running instance.")
    if LEDGER.exists():
        journal = pd.read_csv(LEDGER)
        st.dataframe(journal, use_container_width=True, hide_index=True)
        pnl = pd.to_numeric(journal["P/L before charges"], errors="coerce").fillna(0).sum()
        st.metric("Cumulative paper P/L before charges", rupee(pnl))
        st.download_button("Download journal CSV", journal.to_csv(index=False).encode(), "paper_trades.csv", "text/csv")

st.divider()
st.subheader("Risk rules")
st.markdown("""
- NSE listed cash-equity only; no F&O, options, futures, leverage, margin or short selling.
- A WATCH/SETUP WATCH is not a BUY order. Verify current prices and liquidity in Groww.
- Never spend more than the ₹200 cap, including a buffer for charges.
- No trade is better than a low-quality setup.
- This app does not connect to Groww, place orders or guarantee alerts.
""")
st.caption("Educational decision-support software, not investment advice. Market data is sourced from Yahoo Finance and may be delayed, incomplete or unavailable.")
