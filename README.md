# ₹200 Market Coach V3

A Streamlit decision-support dashboard for a small NSE cash-equity watchlist and a maximum budget of ₹200.

## V3 features
- Daily trend/momentum scanner with budget-aware whole-share quantity and a configurable cost buffer.
- Previous-session context for Nifty, Sensex and selected global indices (not an official live pre-open feed).
- Intraday 5-minute VWAP / prior-candle confirmation check.
- Manual position exit-level monitor.
- Charts, a basic historical backtest, and paper-trade CSV journal.
- Optional scheduled Telegram market notes through GitHub Actions.

## Important limitations and safety
- **Not investment advice.** WATCH and SETUP WATCH are screening labels, not buy orders or predictions.
- Yahoo Finance via yfinance is unofficial, may be delayed, incomplete, stale, rate-limited or unavailable. It is not an official real-time NSE feed.
- The app does not connect to Groww, place orders, access credentials or guarantee the best entry/exit time.
- The GitHub Actions schedule is approximate; scheduled workflows can be delayed or skipped. Never rely on Telegram messages for live execution.
- The free Render filesystem can be ephemeral. Download the paper-trade CSV regularly; use a managed database if durable history is required.
- ₹200 may be insufficient for frequent trading after brokerage, taxes, exchange charges, spread and slippage. The cost buffer is only an estimate, not a quote of actual fees.
- Cash-equity screening only. No F&O, options, futures, margin, leverage, short selling or automatic trading.
- NO TRADE is a valid outcome.

## Deploy on Render
- Build: `pip install -r requirements.txt`
- Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- No secrets are required for the dashboard.

## Optional Telegram alerts
1. Create a Telegram bot with BotFather and obtain its bot token.
2. Start a chat with the bot and obtain your chat ID (for a group, add the bot and use the group chat ID).
3. In GitHub repository Settings → Secrets and variables → Actions, add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Enable GitHub Actions for the repository. The workflow `.github/workflows/market-alerts.yml` runs approximate reports at 08:45, 09:30, 10:00, 11:30, 13:30 and 14:45 IST on weekdays. You can also run it manually from the Actions tab.
5. If the Telegram secrets are absent, the workflow prints the report to its log and sends nothing.

Scheduled GitHub Actions are not guaranteed to run at the exact minute. This is a notification convenience, not a real-time alerting service.

## Local run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project files
- `app.py` — Streamlit dashboard
- `analyzer.py` — data retrieval, indicators, budget sizing, entry/exit checks and backtest
- `alerts.py` — scheduled market note / optional Telegram delivery
- `.github/workflows/market-alerts.yml` — weekday scheduled workflow
