import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from flask import Flask, jsonify, request

from analyzer import (
    analyse_symbol, get_candidate_symbols, market_session,
    opening_check, premarket_summary,
)

app = Flask(__name__)
IST = ZoneInfo("Asia/Kolkata")
BUDGET = min(200.0, max(1.0, float(os.getenv("BUDGET", "200"))))
WATCHLIST = get_candidate_symbols(
    os.getenv("WATCHLIST", "NHPC,IRFC,IOC,ONGC,PNB,BANKBARODA,TATAPOWER,SUZLON,IDEA,YESBANK").split(","),
    30,
)


def telegram_send(chat_id, text):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    response.raise_for_status()


def market_report(premarket_only=False):
    now = datetime.now(IST)
    lines = [
        "₹200 Market Coach",
        now.strftime("%d %b %Y, %I:%M %p IST"),
        f"Session: {market_session(now)}",
        f"Budget cap: ₹{BUDGET:.2f}",
        "Data may be delayed. Verify prices and liquidity in Groww.",
        "",
    ]
    if premarket_only or now.hour < 9 or (now.hour == 9 and now.minute < 15):
        try:
            ctx = premarket_summary()
            lines += [f"Previous-session context: {ctx['bias']}", ctx["message"], ""]
            overview = ctx.get("overview")
            if overview is not None and not overview.empty:
                for _, row in overview.iterrows():
                    change = row.get("Change %")
                    change_text = f"{float(change):+.2f}%" if change is not None and str(change) != "nan" else "n/a"
                    lines.append(f"{row['Market']}: {row['Latest available']} ({change_text}), date {row['Data date']}")
                lines.append("")
        except Exception as exc:
            lines += [f"Market context unavailable: {str(exc)[:120]}", ""]

    candidates = []
    errors = []
    for symbol in WATCHLIST:
        try:
            item = analyse_symbol(symbol, BUDGET)
            if str(item.get("Screen status", "")).startswith("WATCH"):
                candidates.append(item)
        except Exception as exc:
            errors.append(f"{symbol}: {str(exc)[:60]}")
    candidates.sort(key=lambda x: x.get("Score / 5", 0), reverse=True)
    if candidates:
        lines.append("Daily trend candidates (not buy calls):")
        for item in candidates[:5]:
            lines.append(
                f"{item['Symbol']}: close ₹{item['Latest daily close (₹)']:.2f}; "
                f"qty ceiling {item['Affordable qty']}; amount ₹{item['Estimated amount (₹)']:.2f}; "
                f"score {item['Score / 5']}/5. Wait for intraday confirmation."
            )
    else:
        lines.append("No daily candidates passed the screen. NO TRADE is acceptable.")

    if not premarket_only and 9 <= now.hour < 15 and now.minute >= 25:
        lines += ["", "Latest available intraday checks (verify freshness):"]
        for symbol in WATCHLIST[:10]:
            try:
                item = opening_check(symbol, BUDGET)
                if "SETUP WATCH" in item["Status"] or "SKIP" in item["Status"]:
                    lines.append(f"{symbol}: {item['Status']}; price ₹{item['Latest 5m price (₹)']:.2f}; qty {item['Affordable qty']}.")
            except Exception:
                continue
    if errors and not candidates:
        lines += ["", "Some symbols could not be checked because data was unavailable."]
    lines += ["", "Screening only — not investment advice. No orders are placed. A WATCH is not a BUY signal."]
    return "\n".join(lines)


def command_help():
    return (
        "Available commands:\n"
        "/now — run a fresh available-data market scan\n"
        "/premarket — previous-session index context + stock scan\n"
        "/buy — show WATCH candidates and intraday confirmation status\n"
        "/portfolio — explain current tracking limitations\n"
        "/help — show this help\n\n"
        "₹200 max budget. Cash equity only. No orders are placed."
    )


def handle_command(text):
    command = (text or "").strip().split()[0].lower().split("@")[0] if (text or "").strip() else ""
    if command in ("/start", "/help"):
        return "Welcome to ₹200 Market Coach.\n\n" + command_help()
    if command == "/now":
        return market_report(False)
    if command == "/premarket":
        return market_report(True)
    if command == "/buy":
        report = market_report(False)
        return "Potential WATCH candidates only — NOT buy instructions. Confirm current Groww price, spread and intraday conditions yourself.\n\n" + report
    if command == "/portfolio":
        return (
            "Portfolio tracking is not connected yet. This bot cannot read your Groww holdings. "
            "Use the website's manual position monitor and do not send account credentials here."
        )
    return "I don't recognise that command. Send /help to see available commands."


@app.get("/")
def health():
    return jsonify({"status": "ok", "service": "rupee200-telegram-bot"})


@app.post("/telegram-webhook")
def telegram_webhook():
    expected = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not expected or supplied != expected:
        return jsonify({"ok": False}), 403

    update = request.get_json(silent=True) or {}
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id", ""))
    allowed_chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not chat_id or (allowed_chat and chat_id != allowed_chat):
        return jsonify({"ok": True, "ignored": True})

    incoming = message.get("text", "")
    try:
        reply = handle_command(incoming)
        telegram_send(chat_id, reply)
    except Exception as exc:
        try:
            telegram_send(chat_id, f"Sorry, the scan failed: {str(exc)[:180]}. Try again later.")
        except Exception:
            app.logger.exception("Could not send Telegram error reply")
    return jsonify({"ok": True})


def register_webhook():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL", "").strip()
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if not (token and webhook_url and secret):
        app.logger.warning("Webhook not registered: set TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_URL and TELEGRAM_WEBHOOK_SECRET.")
        return
    response = requests.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        data={
            "url": webhook_url.rstrip("/") + "/telegram-webhook",
            "secret_token": secret,
            "allowed_updates": '["message"]',
        },
        timeout=20,
    )
    response.raise_for_status()
    app.logger.info("Telegram webhook registration: %s", response.text)


# Gunicorn imports this module; register once at process startup.
try:
    register_webhook()
except Exception:
    app.logger.exception("Telegram webhook registration failed")
