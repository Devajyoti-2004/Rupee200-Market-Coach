import math
from datetime import time
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

IST = ZoneInfo("Asia/Kolkata")

DEFAULT_SYMBOLS = [
    "NHPC", "IRFC", "IOC", "ONGC", "PNB",
    "BANKBARODA", "TATAPOWER", "SUZLON", "IDEA", "YESBANK"
]

INDEX_TICKERS = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Nikkei 225": "^N225",
    "USD/INR": "INR=X",
}


def rupee(value):
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def get_candidate_symbols(symbols=None, limit=30):
    values = DEFAULT_SYMBOLS if symbols is None else symbols
    cleaned = []
    for item in values:
        symbol = str(item).strip().upper().replace(".NS", "")
        if symbol and symbol not in cleaned:
            cleaned.append(symbol)
    return cleaned[:max(1, int(limit))]


def market_session(now):
    local = now.astimezone(IST)
    if local.weekday() >= 5:
        return "Weekend — Market Closed"
    t = local.time()
    if time(9, 0) <= t < time(9, 15):
        return "Pre-open session"
    if time(9, 15) <= t < time(15, 30):
        return "Regular NSE session"
    return "Market closed"


def get_history(symbol, period="1y", interval="1d"):
    ticker = yf.Ticker(f"{symbol}.NS")
    data = ticker.history(period=period, interval=interval, auto_adjust=True)
    if data.empty:
        raise ValueError(f"No Yahoo Finance data returned for {symbol}.")
    required = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in data.columns]
    return data[required].dropna(subset=["Close"]).copy()


def add_indicators(data):
    df = data.copy()
    close = df["Close"].astype(float)
    df["SMA20"] = close.rolling(20).mean()
    df["SMA50"] = close.rolling(50).mean()
    df["EMA9"] = close.ewm(span=9, adjust=False).mean()
    df["EMA21"] = close.ewm(span=21, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    df["RSI"] = 100 - (100 / (1 + rs))
    df["RSI"] = df["RSI"].fillna(50)

    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs()
    ], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    df["VolAvg20"] = df["Volume"].rolling(20).mean()
    df["Return20"] = close.pct_change(20) * 100
    df["DailyChangePct"] = close.pct_change() * 100
    return df


def get_market_overview():
    rows = []
    for name, ticker_symbol in INDEX_TICKERS.items():
        try:
            data = yf.Ticker(ticker_symbol).history(period="5d", interval="1d", auto_adjust=True)
            if len(data) >= 2:
                last = float(data["Close"].iloc[-1])
                prev = float(data["Close"].iloc[-2])
                change = (last / prev - 1) * 100 if prev else 0
                rows.append({
                    "Market": name,
                    "Latest available": round(last, 2),
                    "Change %": round(change, 2),
                    "Data date": str(data.index[-1].date()),
                    "Direction": "Positive" if change > 0 else "Negative" if change < 0 else "Flat"
                })
            elif len(data) == 1:
                rows.append({"Market": name, "Latest available": round(float(data["Close"].iloc[-1]), 2),
                             "Change %": None, "Data date": str(data.index[-1].date()),
                             "Direction": "Insufficient history"})
        except Exception as exc:
            rows.append({"Market": name, "Latest available": None, "Change %": None,
                         "Data date": "Unavailable", "Direction": str(exc)[:80]})
    return pd.DataFrame(rows)


def premarket_summary():
    overview = get_market_overview()
    if overview.empty:
        return {"bias": "Unavailable", "message": "Market context data is unavailable.", "overview": overview}
    indian = overview[overview["Market"].isin(["NIFTY 50", "SENSEX"])]
    valid = pd.to_numeric(indian["Change %"], errors="coerce").dropna()
    if len(valid) == 0:
        bias = "Insufficient data"
        message = "No reliable previous-session Indian index change was returned."
    elif (valid > 0).all():
        bias = "Positive previous session"
        message = "Indian indices ended higher in the latest available daily data. This is not a live pre-open indication."
    elif (valid < 0).all():
        bias = "Negative previous session"
        message = "Indian indices ended lower in the latest available daily data. This is not a live pre-open indication."
    else:
        bias = "Mixed previous session"
        message = "Indian index direction was mixed in the latest available daily data."
    return {"bias": bias, "message": message, "overview": overview}


def analyse_symbol(symbol, budget, risk_pct=2, cost_buffer_pct=0.5):
    raw = get_history(symbol, "1y", "1d")
    df = add_indicators(raw).dropna(subset=["SMA20", "SMA50", "ATR"])
    if df.empty:
        raise ValueError("Insufficient daily history for indicators.")
    row = df.iloc[-1]
    price = float(row["Close"])
    rsi = float(row["RSI"])
    atr = float(row["ATR"])
    checks = {
        "Price above SMA20": price > float(row["SMA20"]),
        "SMA20 above SMA50": float(row["SMA20"]) > float(row["SMA50"]),
        "EMA9 above EMA21": float(row["EMA9"]) > float(row["EMA21"]),
        "RSI between 45 and 68": 45 <= rsi <= 68,
        "Volume above 20-day average": pd.notna(row["VolAvg20"]) and float(row["Volume"]) > float(row["VolAvg20"]),
    }
    score = sum(checks.values())
    budget_after_buffer = max(0.0, float(budget) / (1 + max(0.0, cost_buffer_pct) / 100))
    qty = int(budget_after_buffer // price) if price > 0 else 0
    investment = qty * price
    stop = max(0.01, price - max(atr * 1.2, price * risk_pct / 100))
    risk_per_share = max(0.0, price - stop)
    target = price + (risk_per_share * 1.5)
    if qty == 0:
        verdict = "SKIP — Above budget"
    elif score >= 4 and rsi < 68:
        verdict = "WATCH — Daily trend screen passed"
    elif rsi >= 72:
        verdict = "AVOID CHASING — RSI elevated"
    else:
        verdict = "WAIT — Daily conditions incomplete"
    return {
        "Symbol": symbol, "Latest daily close (₹)": round(price, 2),
        "Affordable qty": qty, "Estimated amount (₹)": round(investment, 2),
        "Budget left (₹)": round(float(budget) - investment, 2),
        "RSI": round(rsi, 2), "ATR (₹)": round(atr, 2),
        "Score / 5": score, "Screen status": verdict,
        "Illustrative stop (₹)": round(stop, 2),
        "Illustrative target (₹)": round(target, 2),
        "Data date": str(df.index[-1].date()),
        "Checks passed": ", ".join(k for k, v in checks.items() if v),
        "Checks missing": ", ".join(k for k, v in checks.items() if not v),
    }


def opening_check(symbol, budget, cost_buffer_pct=0.5):
    data = get_history(symbol, "5d", "5m")
    if len(data) < 3:
        raise ValueError("Not enough 5-minute candles.")
    idx = data.index
    if getattr(idx, "tz", None) is not None:
        local_dates = idx.tz_convert(IST).date
    else:
        local_dates = idx.date
    latest_date = local_dates[-1]
    session = data[pd.Index(local_dates) == latest_date].copy()
    if len(session) < 3:
        raise ValueError("Current/latest session has too few 5-minute candles.")
    typical = (session["High"] + session["Low"] + session["Close"]) / 3
    vol = session["Volume"].fillna(0)
    vwap = float((typical * vol).sum() / vol.sum()) if vol.sum() > 0 else float(typical.mean())
    last = session.iloc[-1]
    prev = session.iloc[-2]
    price = float(last["Close"])
    prev_high = float(prev["High"])
    above_vwap = price > vwap
    above_prev_high = price > prev_high
    rising = price > float(prev["Close"])
    qty = int((float(budget) / (1 + cost_buffer_pct / 100)) // price) if price > 0 else 0
    if qty < 1:
        status = "SKIP — One share exceeds budget"
    elif above_vwap and rising and above_prev_high:
        status = "SETUP WATCH — Confirm manually; not an order"
    elif above_vwap and rising:
        status = "WAIT — Above VWAP, breakout not confirmed"
    else:
        status = "WAIT — Opening conditions not aligned"
    return {
        "Symbol": symbol, "Latest 5m price (₹)": round(price, 2),
        "Session VWAP (₹)": round(vwap, 2), "Previous candle high (₹)": round(prev_high, 2),
        "Above VWAP": above_vwap, "Above previous candle high": above_prev_high,
        "Rising candle": rising, "Affordable qty": qty, "Status": status,
        "Latest candle": str(session.index[-1])
    }


def exit_monitor(symbol, quantity, entry_price, stop_price, target_price):
    data = get_history(symbol, "5d", "5m")
    latest = float(data["Close"].iloc[-1])
    if latest <= float(stop_price):
        status = "STOP LEVEL BREACHED — review exit promptly"
    elif latest >= float(target_price):
        status = "TARGET LEVEL REACHED — review exit"
    elif latest < float(entry_price):
        status = "BELOW ENTRY — monitor risk"
    else:
        status = "HOLDING ABOVE ENTRY — continue monitoring"
    return {
        "Symbol": symbol, "Quantity": int(quantity),
        "Latest available price (₹)": round(latest, 2),
        "Entry (₹)": round(float(entry_price), 2),
        "Stop (₹)": round(float(stop_price), 2),
        "Target (₹)": round(float(target_price), 2),
        "Unrealised P/L before charges (₹)": round((latest - float(entry_price)) * int(quantity), 2),
        "Status": status, "Data timestamp": str(data.index[-1])
    }


def simple_backtest(symbol, period="2y"):
    df = add_indicators(get_history(symbol, period, "1d"))
    df = df.dropna(subset=["SMA20", "SMA50", "ATR"]).copy()
    entry = ((df["Close"] > df["SMA50"]) & (df["EMA9"] > df["EMA21"]) &
             (df["RSI"] > 45) & (df["RSI"] < 68))
    exit_signal = (df["Close"] < df["SMA20"]) | (df["RSI"] > 75)
    entries = entry.shift(1).fillna(False)
    exits = exit_signal.shift(1).fillna(False)
    state, positions = False, []
    for enter, leave in zip(entries, exits):
        if leave:
            state = False
        elif enter:
            state = True
        positions.append(1.0 if state else 0.0)
    position = pd.Series(positions, index=df.index)
    returns = df["Close"].pct_change().fillna(0)
    strategy_returns = position.shift(1).fillna(0) * returns
    equity = (1 + strategy_returns).cumprod()
    drawdown = (equity / equity.cummax() - 1) * 100
    return {
        "total_return": float((equity.iloc[-1] - 1) * 100),
        "buy_hold": float((df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100),
        "max_drawdown": float(drawdown.min()),
        "trades": int((position.diff() == 1).sum()),
        "equity": equity, "data": df
    }
