import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from analyzer import analyse_symbol, get_candidate_symbols, market_session, opening_check, premarket_summary

IST = ZoneInfo("Asia/Kolkata")


def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("Telegram not configured; report will only appear in the workflow log.")
        print(message)
        return
    import requests
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
        timeout=20,
    )
    response.raise_for_status()


def main():
    budget = min(200.0, max(1.0, float(os.getenv("BUDGET", "200"))))
    symbols = get_candidate_symbols(os.getenv("WATCHLIST", "").split(",") if os.getenv("WATCHLIST") else None, 30)
    now = datetime.now(IST)
    lines = [
        "₹200 Market Coach — scheduled market note",
        now.strftime("%d %b %Y, %I:%M %p IST"),
        f"Session: {market_session(now)}",
        f"Budget cap: ₹{budget:.2f}",
        "Yahoo Finance data can be delayed; verify all quotes in Groww.",
        ""
    ]
    if now.hour < 9 or (now.hour == 9 and now.minute < 15):
        context = premarket_summary()
        lines += [f"Previous-session context: {context['bias']}", context["message"], ""]
    candidates = []
    for symbol in symbols:
        try:
            result = analyse_symbol(symbol, budget)
            if str(result.get("Screen status", "")).startswith("WATCH"):
                candidates.append(result)
        except Exception as exc:
            print(f"{symbol}: {exc}")
    if candidates:
        candidates.sort(key=lambda x: x.get("Score / 5", 0), reverse=True)
        lines.append("Daily trend candidates (not buy calls):")
        for item in candidates[:5]:
            lines.append(
                f"{item['Symbol']}: close ₹{item['Latest daily close (₹)']:.2f}; "
                f"qty ceiling {item['Affordable qty']}; amount ₹{item['Estimated amount (₹)']:.2f}; "
                f"score {item['Score / 5']}/5. Wait for intraday confirmation."
            )
    else:
        lines.append("No daily candidates passed the screen. NO TRADE is acceptable.")
    if 9 <= now.hour < 15 and now.minute >= 25:
        lines.append("")
        lines.append("Intraday checks:")
        for symbol in symbols[:10]:
            try:
                item = opening_check(symbol, budget)
                if "SETUP WATCH" in item["Status"]:
                    lines.append(f"{symbol}: {item['Status']} at latest available ₹{item['Latest 5m price (₹)']:.2f}. Verify manually.")
            except Exception:
                pass
    lines += ["", "Not investment advice. No orders are placed. Do not rely on delayed scheduled messages for execution."]
    send_telegram("\n".join(lines))


if __name__ == "__main__":
    main()
