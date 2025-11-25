import os
import logging
import requests

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ------------ Logging ------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ------------ Env vars ------------
load_dotenv()  # local .env ke liye; Railway pe env vars se kaam ho jayega

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY")

MOONSHOT_BASE_URL = "https://api.moonshot.ai/v1"

# Yahan apna sahi Kimi K2 model id daalo, jaise:
# "kimi-k2-0711-preview" ya "kimi-k2-thinking" (docs se check karo)
KIMI_MODEL = "kimi-k2-0711-preview"


# ------------ Moonshot / Kimi K2 function ------------

def call_kimi_k2(user_message: str, user_id: int | None = None) -> str:
    """
    User ka message Moonshot Kimi K2 ko bhejta hai aur reply return karta hai.
    """
    if not MOONSHOT_API_KEY:
        raise RuntimeError("MOONSHOT_API_KEY env var set nahi hai.")

    url = f"{MOONSHOT_BASE_URL}/chat/completions"

    headers = {
        "Authorization": f"Bearer {MOONSHOT_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": KIMI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an AI assistant inside a Telegram bot. "
                    "Reply in short, clear Hinglish (Hindi + English mix)."
                ),
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
        "max_tokens": 512,
        "temperature": 0.7,
    }

    # HTTP request
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
    except Exception as e:
        logger.exception("Moonshot API request fail hua: %s", e)
        return "Moonshot API se connect nahi ho pa raha 😅. Internet ya API service check karo."

    # Agar HTTP status 200 nahi hai to error handle karo
    if not resp.ok:
        try:
            err_json = resp.json()
        except Exception:
            err_json = None

        logger.error(
            "Moonshot API error: status=%s, body=%s",
            resp.status_code,
            err_json,
        )

        if resp.status_code in (401, 403):
            return (
                "Moonshot API key ya billing me problem lag rahi hai "
                f"(HTTP {resp.status_code}). Dashboard me API key / billing check karo."
            )

        if resp.status_code == 429:
            return (
                "Moonshot API limit cross ho gayi (429). "
                "Thodi der baad try karo ya usage/billing badhao."
            )

        return (
            f"Moonshot API se error aa gaya (HTTP {resp.status_code}). "
            "Key, model name ya billing check karo."
        )

    # Successful response
    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("Unexpected response from Moonshot: %s", resp.text)
        return "Moonshot se ajeeb response aaya 😅. Thodi der baad try karo."


# ------------ Telegram handlers ------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Namaste! 👋\n\n"
        "Main Kimi K2 powered Telegram bot hoon.\n"
        "Jo bhi sawaal hai, yahan bhejo 🙂"
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "/start – bot shuru karo\n"
        "Bas message bhejo, main Kimi K2 se reply launga."
    )
    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    user_id = update.effective_user.id if update.effective_user else None

    logger.info("User %s: %s", user_id, user_text)

    try:
        reply_text = call_kimi_k2(user_text, user_id)
    except Exception:
        logger.exception("Moonshot API error")
        reply_text = (
            "Backend me kuch error aa gaya 😅\n"
            "Thodi der baad dobara try kar lena."
        )

    await update.message.reply_text(reply_text)


# ------------ Main (no asyncio.run) ------------

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN env var set nahi hai.")

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("Bot started on Railway (run_polling)...")
    application.run_polling()


if __name__ == "__main__":
    main()
