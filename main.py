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
load_dotenv()  # local .env ke liye, Railway pe env vars se kaam ho jayega

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY")

MOONSHOT_BASE_URL = "https://api.moonshot.ai/v1"
KIMI_MODEL = "kimi-k2-0711-preview"  # docs ke hisab se; chahe to kimi-k2-thinking bhi use kar sakte ho


# ------------ Moonshot / Kimi K2 function ------------

def call_kimi_k2(user_message: str, user_id: int | None = None) -> str:
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
                    "Reply in short, clear Hinglish (Hindi + English)."
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

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("Unexpected response from Moonshot: %s", data)
        return "Backend se ajeeb response aaya 😅 thodi der baad try karna."


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


# ------------ Main app ------------

async def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN env var set nahi hai.")

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started on Railway... Press Ctrl+C to stop (locally).")
    await application.run_polling(close_loop=False)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
