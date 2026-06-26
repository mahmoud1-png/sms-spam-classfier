#!/usr/bin/env python3
"""
telegram_bot.py — Spam Classifier Telegram Bot
────────────────────────────────────────────────
Setup:
  pip install python-telegram-bot httpx

Run:
  BOT_TOKEN=your_token_here python telegram_bot.py
  or set API_URL if your classifier runs elsewhere:
  BOT_TOKEN=your_token API_URL=http://localhost:5000 python telegram_bot.py
"""

import os
import pathlib
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
    PicklePersistence,
)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set! "
                     "Set it in your .env file or shell before running.")

API_URL          = os.getenv("API_URL", "http://localhost:5000")
PERSISTENCE_PATH = os.getenv("PERSISTENCE_PATH", "bot_data.pkl")

# FIX 6: Match the bot's default threshold to the server default (0.35)
# so users get consistent results whether they call the API directly or via
# the bot.  The old hard-coded 0.5 produced silently different sensitivity.
BOT_DEFAULT_THRESHOLD = float(os.getenv("BOT_DEFAULT_THRESHOLD", "0.35"))

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ── Shared HTTP client (created once, reused across all requests) ─────────────
# FIX 5: The original code opened a new AsyncClient on every API call, which
#         tears down and rebuilds the TCP connection pool on each request.
#         A single module-level client reuses connections and is far more
#         efficient under load.  It is closed gracefully in post_shutdown.
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=30.0))
    return _http_client


# ── API helpers ───────────────────────────────────────────────────────────────
async def check_single(message: str, threshold: float = BOT_DEFAULT_THRESHOLD) -> dict:
    resp = await get_http_client().post(
        f"{API_URL}/predict",
        json={"message": message, "threshold": threshold},
    )
    resp.raise_for_status()
    return resp.json()


async def check_batch(messages: list, threshold: float = BOT_DEFAULT_THRESHOLD) -> dict:
    resp = await get_http_client().post(
        f"{API_URL}/predict/batch",
        json={"messages": messages, "threshold": threshold},
        timeout=httpx.Timeout(30.0, read=60.0),
    )
    resp.raise_for_status()
    return resp.json()


async def api_health() -> dict:
    resp = await get_http_client().get(f"{API_URL}/health", timeout=5)
    resp.raise_for_status()
    return resp.json()


# ── Formatting ────────────────────────────────────────────────────────────────
def format_result(result: dict) -> str:
    label = result["label"]
    prob  = result["spam_probability"]
    emoji = "🚨" if label == "SPAM" else "✅"
    bar   = build_bar(prob)
    return (
        f"{emoji} *{label}*\n"
        f"Spam probability: `{prob:.1%}`\n"
        f"{bar}"
    )


def build_bar(prob: float, length: int = 10) -> str:
    filled = round(prob * length)
    return "🟥" * filled + "⬜" * (length - filled)


# ── Handlers ──────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Spam Classifier Bot*\n\n"
        "Just send me any message and I'll tell you if it's spam.\n\n"
        "*Commands:*\n"
        "/start — show this help\n"
        "/health — check API status\n"
        "/threshold — set decision threshold (default 0.35)\n"
        "/batch — classify multiple messages at once\n"
        "/cancel — exit batch mode\n",
        parse_mode="Markdown"
    )


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        h      = await api_health()
        status = "🟢 Online"  if h["status"] == "ok" else "🔴 Degraded"
        model  = "✅ Loaded"  if h["model_loaded"]    else "❌ Not loaded"

        server_threshold = h["threshold"]
        user_threshold   = context.user_data.get("threshold")

        if user_threshold is not None:
            threshold_line = (
                f"Threshold: `{user_threshold}` _(your setting, matches server default)_"
                if user_threshold == server_threshold
                else f"Threshold: `{user_threshold}` _(your setting)_\n"
                     f"Server default: `{server_threshold}`"
            )
        else:
            threshold_line = f"Threshold: `{server_threshold}` _(server default)_"

        await update.message.reply_text(
            f"*API Health*\n"
            f"Status: {status}\n"
            f"Model: {model}\n"
            f"{threshold_line}",
            parse_mode="Markdown"
        )
    except Exception:
        log.exception("Health check failed")
        await update.message.reply_text(
            "❌ Could not reach the API. Please try again later.",
            parse_mode="Markdown"
        )


async def cmd_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("0.3  (catch more spam)", callback_data="thresh_0.3"),
            InlineKeyboardButton("0.4",                    callback_data="thresh_0.4"),
        ],
        [
            InlineKeyboardButton("0.5",                    callback_data="thresh_0.5"),
            InlineKeyboardButton("0.6",                    callback_data="thresh_0.6"),
        ],
        [
            InlineKeyboardButton("0.7  (fewer false alarms)", callback_data="thresh_0.7"),
        ],
    ]
    current = context.user_data.get("threshold", BOT_DEFAULT_THRESHOLD)
    await update.message.reply_text(
        f"Current threshold: `{current}`\n"
        "Higher = fewer false alarms, lower = catches more spam.\n"
        "Pick a new threshold:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def callback_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    value = float(query.data.split("_")[1])
    context.user_data["threshold"] = value
    await query.edit_message_text(
        f"✅ Threshold set to `{value}`",
        parse_mode="Markdown"
    )


async def cmd_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["batch_mode"] = True
    await update.message.reply_text(
        "📋 *Batch mode* — send messages one per line, then hit send.\n\n"
        "*Example:*\n"
        "`You won a FREE prize!\n"
        "Hey, see you at 6pm?\n"
        "Claim your reward now!`\n\n"
        "Type /cancel to exit batch mode without classifying.",
        parse_mode="Markdown"
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("batch_mode"):
        context.user_data["batch_mode"] = False
        await update.message.reply_text("❌ Batch mode cancelled. Back to single-message mode.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text      = update.message.text.strip()
    threshold = context.user_data.get("threshold", BOT_DEFAULT_THRESHOLD)

    # ── Batch mode ────────────────────────────────────────────────────────────
    if context.user_data.get("batch_mode"):
        context.user_data["batch_mode"] = False
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        if len(lines) < 2:
            await update.message.reply_text(
                "ℹ️ Only one line detected — classifying as a single message.\n"
                "Use /batch again and send multiple lines for batch mode."
            )
            try:
                result = await check_single(text, threshold)
                await update.message.reply_text(format_result(result), parse_mode="Markdown")
            except Exception:
                log.exception("Single classify failed in batch fallback")
                await update.message.reply_text(
                    "❌ Could not classify the message. Please try again later."
                )
            return

        if len(lines) > 500:
            await update.message.reply_text(
                "⚠️ Too many lines — batch is limited to 500 messages. Please split your input."
            )
            return

        try:
            data       = await check_batch(lines, threshold)
            spam_count = data["spam_count"]
            ham_count  = data["ham_count"]
            lines_out  = [f"*Batch results* — {spam_count} spam / {ham_count} ham\n"]
            for r in data["results"]:
                emoji = "🚨" if r["label"] == "SPAM" else "✅"
                short = r["input"][:40] + ("…" if len(r["input"]) > 40 else "")
                lines_out.append(f"{emoji} `{r['spam_probability']:.0%}` — {short}")
            await update.message.reply_text("\n".join(lines_out), parse_mode="Markdown")
        except Exception:
            log.exception("Batch classify failed")
            await update.message.reply_text(
                "❌ Could not classify the messages. Please try again later."
            )
        return

    # ── Single message ────────────────────────────────────────────────────────
    try:
        result = await check_single(text, threshold)
        await update.message.reply_text(format_result(result), parse_mode="Markdown")
    except Exception:
        log.exception("Single classify failed")
        await update.message.reply_text(
            "❌ Could not classify the message. Please try again later."
        )


# ── Lifecycle hooks ───────────────────────────────────────────────────────────
async def post_init(application) -> None:
    """Clear any stale webhook before polling starts."""
    await application.bot.delete_webhook(drop_pending_updates=True)
    log.info("Webhook cleared. Starting long-poll loop.")


async def post_shutdown(application) -> None:
    """Close the shared HTTP client cleanly on shutdown."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        log.info("HTTP client closed.")


# ── Persistence helper ────────────────────────────────────────────────────────
def _init_persistence() -> "PicklePersistence | None":
    p = pathlib.Path(PERSISTENCE_PATH)

    if p.is_dir():
        log.error(
            "Persistence path '%s' is a directory — Docker created it before "
            "the file existed.  Fix: stop the containers, run  "
            "  rm -rf %s && touch %s  "
            "then restart.  Running with in-memory-only storage for now.",
            p, p, p,
        )
        return None

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.touch()
            log.info("Created persistence file '%s'.", p)
        return PicklePersistence(filepath=str(p))
    except OSError as exc:
        log.warning(
            "Could not initialise persistence at '%s': %s. "
            "User settings (threshold, batch_mode) will not survive restarts.",
            p, exc,
        )
        return None


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    persistence = _init_persistence()

    builder = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)   # FIX 5: close shared client on exit
    )
    if persistence is not None:
        builder = builder.persistence(persistence)
    else:
        log.warning("Running without persistence — user_data is in-memory only.")

    app = builder.build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("health",    cmd_health))
    app.add_handler(CommandHandler("threshold", cmd_threshold))
    app.add_handler(CommandHandler("batch",     cmd_batch))
    app.add_handler(CommandHandler("cancel",    cmd_cancel))
    app.add_handler(CallbackQueryHandler(callback_threshold, pattern="^thresh_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Bot started. Listening for messages…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()