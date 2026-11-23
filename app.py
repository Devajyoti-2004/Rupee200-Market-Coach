import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from analyzer import (
    analyse_symbol,
    get_candidate_symbols,
    market_session,
    opening_check,
    simple_backtest,
    rupee,
    get_history,
    add_indicators
)

# ---------------------------------
# APP CONFIGURATION
# ---------------------------------

st.set_page_config(
    page_title="₹200 Market Coach",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ₹200 Market Coach")
st.caption(
    "NSE Cash Market | Beginner Friendly | AI-style Market Analysis"
)

TZ = ZoneInfo("Asia/Kolkata")
LEDGER = Path("paper_trades.csv")

# ---------------------------------
# SIDEBAR
# ---------------------------------

with st.sidebar:

    st.header("Your Investment Settings")

    budget = st.number_input(
        "Maximum Investment (₹)",
        min_value=1,
        max_value=200,
        value=200,
        step=10
    )

    risk_pct = st.slider(
        "Illustrative Stop Distance (%)",
        1,
        5,
        2
    )

    default_symbols = get_candidate_symbols()

    symbols_text = st.text_area(
        "NSE Watchlist",
        "\n".join(default_symbols)
    )

    symbols = get_candidate_symbols(
        symbols_text.splitlines(),
        limit=30
    )

    scan_button = st.button(
        "🔎 Scan Stock Market",
        type="primary",
        use_container_width=True
    )

    opening_button = st.button(
        "⏱ Opening Confirmation",
        use_container_width=True
    )

# ---------------------------------
# MARKET STATUS
# ---------------------------------

now = datetime.now(TZ)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Indian Time",
    now.strftime("%d %b %Y, %I:%M %p")
)

col2.metric(
    "Market Status",
    market_session(now)
)

col3.metric(
    "Your Capital",
    rupee(budget)
)

st.warning(
    "₹200 is a very small trading budget. Brokerage, taxes, "
    "spread and slippage can consume potential profits. "
    "Use paper trading before risking real money."
)

# ---------------------------------
# MAIN TABS
# ---------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Stock Scanner",
    "⏱ Opening Analysis",
    "📈 Charts",
    "🧪 Backtesting",
    "📝 Paper Trading"
])

# =================================
# TAB 1: STOCK SCANNER
# =================================

with tab1:

    st.subheader("NSE Multi-Factor Stock Scanner")

    st.write(
        "The scanner checks trend, momentum, volume and "
        "historical volatility-related indicators."
    )

    if scan_button or "scan_results" not in st.session_state:

        results = []

        progress = st.progress(0)

        for index, symbol in enumerate(symbols):

            try:

                result = analyse_symbol(
                    symbol,
                    budget,
                    risk_pct
                )

                results.append(result)

            except Exception as error:

                results.append({
                    "Symbol": symbol,
                    "Screen result": f"Unavailable: {str(error)[:100]}"
                })

            progress.progress(
                (index + 1) / max(len(symbols), 1)
            )

        st.session_state.scan_results = results

    results_df = pd.DataFrame(
        st.session_state.scan_results
    )

    if not results_df.empty:

        if "Score / 5" in results_df.columns:

            results_df = results_df.sort_values(
                "Score / 5",
                ascending=False
            )

        st.dataframe(
            results_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Scanner Results",
            results_df.to_csv(index=False).encode("utf-8"),
            "market_scan.csv",
            "text/csv"
        )

    st.info(
        "WATCH means investigate further. It is not a guaranteed "
        "BUY recommendation."
    )

# =================================
# TAB 2: OPENING ANALYSIS
# =================================

with tab2:

    st.subheader("Opening Market Confirmation")

    st.write("""
    Suggested routine:

    - 9:15 AM: Market opens.
    - 9:15–9:30 AM: Wait for initial volatility to settle.
    - After 9:30 AM: Run the opening confirmation.
    """)

    if opening_button:

        opening_results = []

        with st.spinner("Checking intraday candles..."):

            for symbol in symbols:

                try:

                    result = opening_check(
                        symbol,
                        budget
                    )

                    opening_results.append(result)

                except Exception as error:

                    opening_results.append({
                        "Symbol": symbol,
                        "Status": f"Unavailable: {str(error)[:100]}"
                    })

        st.session_state.opening_results = opening_results

    if "opening_results" in st.session_state:

        opening_df = pd.DataFrame(
            st.session_state.opening_results
        )

        st.dataframe(
            opening_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Opening Analysis",
            opening_df.to_csv(index=False).encode("utf-8"),
            "opening_analysis.csv",
            "text/csv"
        )

    st.warning(
        "Yahoo Finance intraday data may be delayed or unavailable. "
        "Confirm live prices inside Groww."
    )

# =================================
# TAB 3: CHARTS
# =================================

with tab3:

    st.subheader("Stock Charts and Indicators")

    selected_symbol = st.selectbox(
        "Select NSE Stock",
        symbols
    )

    chart_period = st.selectbox(
        "Chart Period",
        ["3mo", "6mo", "1y", "2y"],
        index=2
    )

    try:

        raw = get_history(
            selected_symbol,
            chart_period,
            "1d"
        )

        data = add_indicators(raw)

        data = data.dropna(
            subset=["SMA20", "SMA50"]
        )

        fig = go.Figure()

        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data["Open"],
                high=data["High"],
                low=data["Low"],
                close=data["Close"],
                name="Stock Price"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data["SMA20"],
                name="SMA 20"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data["SMA50"],
                name="SMA 50"
            )
        )

        fig.update_layout(
            title=selected_symbol + " Stock Chart",
            height=500,
            xaxis_rangeslider_visible=False
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        latest = data.iloc[-1]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Latest Close",
            rupee(latest["Close"])
        )

        c2.metric(
            "RSI",
            f"{latest['RSI']:.2f}"
        )

        c3.metric(
            "ATR",
            rupee(latest["ATR"])
        )

        c4.metric(
            "20-Day Return",
            f"{latest['Return20']:.2f}%"
        )

    except Exception as error:

        st.error(
            f"Chart unavailable: {error}"
        )

# =================================
# TAB 4: BACKTESTING
# =================================

with tab4:

    st.subheader("Historical Strategy Backtesting")

    st.write(
        "Test a simple trend-following strategy against historical data."
    )

    backtest_symbol = st.selectbox(
        "Select Stock",
        symbols,
        key="backtest_symbol"
    )

    backtest_period = st.selectbox(
        "Testing Period",
        ["1y", "2y", "5y"],
        index=1
    )

    if st.button("Run Backtest"):

        try:

            with st.spinner("Testing historical data..."):

                result = simple_backtest(
                    backtest_symbol,
                    backtest_period
                )

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Strategy Return",
                f"{result['total_return']:.2f}%"
            )

            c2.metric(
                "Buy & Hold Return",
                f"{result['buy_hold']:.2f}%"
            )

            c3.metric(
                "Maximum Drawdown",
                f"{result['max_drawdown']:.2f}%"
            )

            c4.metric(
                "Number of Entries",
                result["trades"]
            )

            st.line_chart(
                result["equity"]
            )

            st.caption(
                "Historical results exclude brokerage, taxes, "
                "slippage and market impact. Past performance "
                "does not predict future returns."
            )

        except Exception as error:

            st.error(
                f"Backtest failed: {error}"
            )

# =================================
# TAB 5: PAPER TRADING
# =================================

with tab5:

    st.subheader("Paper Trading Journal")

    st.write(
        "Record hypothetical trades and monitor your performance."
    )

    with st.form("paper_trade_form"):

        c1, c2, c3 = st.columns(3)

        with c1:

            trade_symbol = st.text_input(
                "Stock Symbol",
                value=symbols[0] if symbols else "NHPC"
            ).upper().strip()

            entry_price = st.number_input(
                "Entry Price (₹)",
                min_value=0.01,
                value=10.0
            )

        with c2:

            quantity = st.number_input(
                "Quantity",
                min_value=1,
                max_value=200,
                value=1
            )

            exit_price = st.number_input(
                "Exit Price (₹)",
                min_value=0.01,
                value=10.0
            )

        with c3:

            trade_date = st.date_input(
                "Trade Date",
                value=now.date()
            )

            notes = st.text_input(
                "Trade Notes"
            )

        save_trade = st.form_submit_button(
            "Save Paper Trade"
        )

    if save_trade:

        profit = (
            exit_price - entry_price
        ) * quantity

        new_trade = pd.DataFrame([{

            "Date": str(trade_date),
            "Symbol": trade_symbol,
            "Quantity": quantity,
            "Entry Price": entry_price,
            "Exit Price": exit_price,
            "Profit Before Charges": round(profit, 2),
            "Notes": notes

        }])

        if LEDGER.exists():

            old_trades = pd.read_csv(LEDGER)

            new_trade = pd.concat(
                [old_trades, new_trade],
                ignore_index=True
            )

        new_trade.to_csv(
            LEDGER,
            index=False
        )

        st.success(
            "Paper trade saved successfully!"
        )

    if LEDGER.exists():

        journal = pd.read_csv(LEDGER)

        st.dataframe(
            journal,
            use_container_width=True,
            hide_index=True
        )

        total_profit = pd.to_numeric(
            journal["Profit Before Charges"],
            errors="coerce"
        ).fillna(0).sum()

        st.metric(
            "Total Paper Profit / Loss",
            rupee(total_profit)
        )

        st.download_button(
            "Download Trading Journal",
            journal.to_csv(index=False).encode("utf-8"),
            "paper_trades.csv",
            "text/csv"
        )

# ---------------------------------
# FOOTER
# ---------------------------------

st.divider()

st.subheader("Beginner Trading Rules")

st.markdown("""
1. Prefer delivery/cash equity while learning.
2. Buy only whole shares within your budget.
3. Do not trade if the scanner shows no clear setup.
4. Stop-loss levels are not guaranteed execution prices.
5. Avoid F&O, options, futures, leverage and borrowed money.
6. Check live prices and all charges in Groww before placing an order.
""")

st.caption(
    "Market data: Yahoo Finance through yfinance. "
    "This application does not connect to Groww or place trades."
)
