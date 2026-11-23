# ₹200 Market Coach

A beginner-friendly Streamlit dashboard that screens a small NSE watchlist against a user-set budget of up to ₹200. It calculates simple trend/momentum/volatility indicators and illustrates position sizing, a hypothetical stop and target.

## Important limitations

- **Not investment advice.** A score is not a prediction, recommendation, or promise of profit.
- It does not predict the opening price or tell you a guaranteed best time to sell.
- Data comes from Yahoo Finance through `yfinance`, not an official real-time exchange feed. It may be delayed, missing, adjusted, or unavailable.
- The app does not connect to Groww, place orders, or store credentials.
- ₹200 is generally too small for frequent intraday trading: transaction taxes, brokerage, spread and slippage can overwhelm small gains. Use paper trading first.
- No F&O, options, leverage, margin, short selling or automatic trading.

## Why Groww API is not enabled by default

Groww publishes a Trading API for market data and order functions. Its official pricing page currently advertises a paid API plan (₹499/month plus taxes after the listed offer), which is disproportionate to a ₹200 trading budget. See [Groww Trading API](https://groww.in/trade-api) and [official docs](https://groww.in/trade-api/docs). Do not scrape Groww's website or enter your Groww password into this app.

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (usually http://localhost:8501).

## Deploy on Render

1. Push this folder to a GitHub repository.
2. In Render, choose **New → Web Service** and connect the repository.
3. Runtime: Python. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. No secrets or environment variables are required.

## Screening logic

- Price above 20-day moving average
- 20-day moving average above 50-day moving average
- RSI(14) in a neutral-to-positive band (45–65)
- 20-day annualised historical volatility below 60%

These are deliberately simple educational filters, not a validated trading strategy. Backtest and paper trade before risking money. The illustrative stop and target are percentages from the last available close; real fills can differ.

## Market timing

NSE equity regular trading is generally 9:15 AM to 3:30 PM on trading days, preceded by a 9:00–9:15 AM pre-open session. Always check the current NSE holiday calendar and segment-specific rules.

## Project structure

- `app.py` — dashboard and UI
- `analyzer.py` — indicators and budget sizing
- `requirements.txt` — Python dependencies
