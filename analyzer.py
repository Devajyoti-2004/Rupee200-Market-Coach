import math
import yfinance as yf
import pandas as pd
from datetime import time
from zoneinfo import ZoneInfo

def rupee(x):
    return f"₹{x:,.2f}" if pd.notna(x) else "—"

def market_session(now):
    if now.weekday() >= 5:
        return "Weekend — equity market normally closed"
    t = now.astimezone(ZoneInfo("Asia/Kolkata")).time()
    if time(9,0) <= t < time(9,15):
        return "Pre-open session"
    if time(9,15) <= t < time(15,30):
        return "Regular equity session"
    return "Market closed (check exchange holiday calendar)"

def analyse_symbol(symbol, budget, risk_pct):
    ticker = yf.Ticker(f"{symbol}.NS")
    hist = ticker.history(period="6mo", interval="1d", auto_adjust=True)
    if hist.empty or len(hist) < 30:
        raise ValueError("Insufficient price history")
    close = hist["Close"].dropna()
    price = float(close.iloc[-1])
    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = float((100 - (100 / (1 + rs))).iloc[-1])
    vol = float(close.pct_change().tail(20).std() * math.sqrt(252) * 100)
    qty = int(budget // price) if price > 0 else 0
    value = qty * price
    stop = price * (1 - risk_pct / 100)
    target = price * (1 + (risk_pct * 1.5) / 100)
    score = 0
    score += 1 if price > sma20 else 0
    score += 1 if sma20 > sma50 else 0
    score += 1 if 45 <= rsi <= 65 else 0
    score += 1 if vol < 60 else 0
    if rsi > 70: note = "Overbought risk; avoid chasing"
    elif rsi < 35: note = "Weak momentum; falling knife risk"
    elif qty == 0: note = "One share exceeds your budget"
    elif score >= 3: note = "Watch only; wait for live confirmation"
    else: note = "No clear setup; staying in cash is okay"
    status = "Screened"
    if qty == 0:
        note = "One share exceeds your budget; not affordable within budget"
    return {
        "Symbol": symbol, "Status": status, "Last close (₹)": round(price, 2),
        "Qty within budget": qty, "Estimated value (₹)": round(value, 2),
        "SMA20 (₹)": round(sma20, 2), "SMA50 (₹)": round(sma50, 2),
        "RSI(14)": round(rsi, 1), "20d annualised vol. (%)": round(vol, 1),
        "Score / 4": score, "Illustrative stop (₹)": round(stop, 2),
        "Illustrative target (₹)": round(target, 2), "Readout": note,
        "Data date": str(hist.index[-1].date())
    }
