import math
import pandas as pd
import yfinance as yf

from datetime import time
from zoneinfo import ZoneInfo


# =================================
# CURRENCY FORMAT
# =================================

def rupee(value):

    try:
        return f"₹{float(value):,.2f}"

    except (TypeError, ValueError):

        return "—"


# =================================
# NSE WATCHLIST
# =================================

def get_candidate_symbols(symbols=None, limit=30):

    defaults = [
        "NHPC",
        "IRFC",
        "IOC",
        "ONGC",
        "PNB",
        "BANKBARODA",
        "TATAPOWER",
        "SUZLON",
        "IDEA",
        "YESBANK"
    ]

    values = defaults if symbols is None else symbols

    cleaned = []

    for item in values:

        symbol = (
            str(item)
            .strip()
            .upper()
            .replace(".NS", "")
        )

        if symbol and symbol not in cleaned:

            cleaned.append(symbol)

    return cleaned[:max(1, int(limit))]


# =================================
# MARKET STATUS
# =================================

def market_session(now):

    if now.weekday() >= 5:

        return "Weekend — Market Closed"

    india_time = now.astimezone(
        ZoneInfo("Asia/Kolkata")
    ).time()

    if time(9, 0) <= india_time < time(9, 15):

        return "Pre-Open Session"

    if time(9, 15) <= india_time < time(15, 30):

        return "Regular NSE Session"

    return "Market Closed"


# =================================
# FETCH STOCK DATA
# =================================

def get_history(
    symbol,
    period="1y",
    interval="1d"
):

    ticker = yf.Ticker(
        f"{symbol}.NS"
    )

    data = ticker.history(
        period=period,
        interval=interval,
        auto_adjust=True
    )

    if data.empty:

        raise ValueError(
            "No market data available. Check the NSE symbol."
        )

    return data.dropna(
        subset=["Close"]
    ).copy()


# =================================
# TECHNICAL INDICATORS
# =================================

def add_indicators(data):

    df = data.copy()

    close = df["Close"]

    # Moving averages

    df["SMA20"] = close.rolling(20).mean()

    df["SMA50"] = close.rolling(50).mean()

    # Exponential moving averages

    df["EMA9"] = close.ewm(
        span=9,
        adjust=False
    ).mean()

    df["EMA21"] = close.ewm(
        span=21,
        adjust=False
    ).mean()

    # RSI

    delta = close.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        float("nan")
    )

    df["RSI"] = 100 - (
        100 / (1 + rs)
    )

    # ATR

    tr1 = df["High"] - df["Low"]

    tr2 = (
        df["High"] - df["Close"].shift()
    ).abs()

    tr3 = (
        df["Low"] - df["Close"].shift()
    ).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    df["ATR"] = true_range.rolling(14).mean()

    # Volume

    df["VolAvg20"] = (
        df["Volume"].rolling(20).mean()
    )

    # Returns

    df["Return20"] = (
        close.pct_change(20) * 100
    )

    return df


# =================================
# STOCK ANALYSIS
# =================================

def analyse_symbol(
    symbol,
    budget,
    risk_pct=2
):

    raw = get_history(
        symbol,
        "1y",
        "1d"
    )

    df = add_indicators(raw)

    df = df.dropna(
        subset=["SMA20", "SMA50", "RSI", "ATR"]
    )

    if len(df) < 2:

        raise ValueError(
            "Insufficient historical data."
        )

    latest = df.iloc[-1]

    price = float(latest["Close"])

    rsi = float(latest["RSI"])

    sma20 = float(latest["SMA20"])

    sma50 = float(latest["SMA50"])

    ema9 = float(latest["EMA9"])

    ema21 = float(latest["EMA21"])

    volume = float(latest["Volume"])

    average_volume = float(
        latest["VolAvg20"]
    )

    atr = float(latest["ATR"])

    # Analysis conditions

    checks = {

        "Price above SMA20":
            price > sma20,

        "SMA20 above SMA50":
            sma20 > sma50,

        "EMA9 above EMA21":
            ema9 > ema21,

        "RSI between 45 and 65":
            45 <= rsi <= 65,

        "Volume above average":
            volume > average_volume

    }

    score = sum(
        checks.values()
    )

    # Budget calculation

    quantity = int(
        budget // price
    )

    investment = quantity * price

    # Illustrative ATR levels

    stop_loss = max(
        0.01,
        price - (1.5 * atr)
    )

    target = price + (2 * atr)

    risk_per_share = (
        price - stop_loss
    )

    total_risk = (
        risk_per_share * quantity
    )

    # Result

    if quantity < 1:

        verdict = "SKIP — Stock exceeds budget"

    elif rsi >= 72:

        verdict = "AVOID CHASING — Momentum stretched"

    elif score >= 4:

        verdict = "WATCH — Conditions align"

    else:

        verdict = "NO CLEAR SETUP"

    passed = ", ".join(
        name
        for name, value in checks.items()
        if value
    )

    failed = ", ".join(
        name
        for name, value in checks.items()
        if not value
    )

    return {

        "Symbol": symbol,

        "Latest Close (₹)": round(price, 2),

        "Affordable Quantity": quantity,

        "Investment Value (₹)": round(
            investment,
            2
        ),

        "RSI": round(rsi, 2),

        "SMA20 (₹)": round(sma20, 2),

        "SMA50 (₹)": round(sma50, 2),

        "ATR (₹)": round(atr, 2),

        "Score / 5": score,

        "Screen result": verdict,

        "Conditions Passed": passed,

        "Conditions Failed": failed,

        "Illustrative Stop (₹)": round(
            stop_loss,
            2
        ),

        "Illustrative Target (₹)": round(
            target,
            2
        ),

        "Estimated Position Risk (₹)": round(
            total_risk,
            2
        ),

        "Data Date": str(
            df.index[-1].date()
        )

    }


# =================================
# OPENING CONFIRMATION
# =================================

def opening_check(
    symbol,
    budget
):

    df = get_history(
        symbol,
        "5d",
        "5m"
    )

    if len(df) < 5:

        raise ValueError(
            "Insufficient intraday candles."
        )

    recent = df.tail(12)

    typical_price = (
        recent["High"]
        + recent["Low"]
        + recent["Close"]
    ) / 3

    volume = recent["Volume"].fillna(0)

    if volume.sum() > 0:

        vwap = float(
            (typical_price * volume).sum()
            / volume.sum()
        )

    else:

        vwap = float(
            typical_price.mean()
        )

    latest_price = float(
        df["Close"].iloc[-1]
    )

    previous_price = float(
        df["Close"].iloc[-2]
    )

    quantity = int(
        budget // latest_price
    )

    above_vwap = (
        latest_price > vwap
    )

    rising = (
        latest_price > previous_price
    )

    if quantity < 1:

        status = "SKIP — Unaffordable"

    elif above_vwap and rising:

        status = "WATCH ONLY — Conditions align"

    else:

        status = "WAIT — No confirmation"

    return {

        "Symbol": symbol,

        "Latest 5m Price (₹)": round(
            latest_price,
            2
        ),

        "Approx VWAP (₹)": round(
            vwap,
            2
        ),

        "Above VWAP": above_vwap,

        "Last Candle Rising": rising,

        "Affordable Quantity": quantity,

        "Status": status,

        "Timestamp": str(
            df.index[-1]
        )

    }


# =================================
# HISTORICAL BACKTEST
# =================================

def simple_backtest(
    symbol,
    period="2y"
):

    raw = get_history(
        symbol,
        period,
        "1d"
    )

    df = add_indicators(raw)

    df = df.dropna(
        subset=["SMA20", "SMA50", "RSI"]
    ).copy()

    entry_signal = (

        (df["Close"] > df["SMA50"])

        & (df["EMA9"] > df["EMA21"])

        & (df["RSI"] > 45)

        & (df["RSI"] < 68)

    )

    exit_signal = (

        (df["Close"] < df["SMA20"])

        | (df["RSI"] > 75)

    )

    state = False

    positions = []

    # Use previous day's signal to avoid same-day signal execution.

    entries = entry_signal.shift(1).fillna(False)

    exits = exit_signal.shift(1).fillna(False)

    for enter, exit_trade in zip(
        entries,
        exits
    ):

        if exit_trade:

            state = False

        elif enter:

            state = True

        positions.append(
            1.0 if state else 0.0
        )

    position = pd.Series(
        positions,
        index=df.index
    )

    daily_returns = (
        df["Close"].pct_change().fillna(0)
    )

    strategy_returns = (
        position.shift(1).fillna(0)
        * daily_returns
    )

    equity = (
        1 + strategy_returns
    ).cumprod()

    peak = equity.cummax()

    drawdown = (
        equity / peak - 1
    ) * 100

    strategy_return = (
        equity.iloc[-1] - 1
    ) * 100

    buy_hold_return = (

        df["Close"].iloc[-1]
        / df["Close"].iloc[0]
        - 1

    ) * 100

    trades = int(
        (position.diff() == 1).sum()
    )

    return {

        "total_return": float(
            strategy_return
        ),

        "buy_hold": float(
            buy_hold_return
        ),

        "max_drawdown": float(
            drawdown.min()
        ),

        "trades": trades,

        "equity": equity,

        "data": df

    }
# =================================
# NSE CANDIDATE SYMBOLS
# =================================

def get_candidate_symbols(symbols=None, limit=30):

    defaults = [
        "NHPC",
        "IRFC",
        "IOC",
        "ONGC",
        "PNB",
        "BANKBARODA",
        "TATAPOWER",
        "SUZLON",
        "IDEA",
        "YESBANK"
    ]

    values = defaults if symbols is None else symbols

    cleaned = []

    for item in values:

        symbol = (
            str(item)
            .strip()
            .upper()
            .replace(".NS", "")
        )

        if symbol and symbol not in cleaned:
            cleaned.append(symbol)

    return cleaned[:max(1, int(limit))]
