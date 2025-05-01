"""
Telegram Bot main module.
"""

import os
# Импорты telegram должны быть после стандартных библиотек
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Загрузка переменных окружения из .env файла (если есть)
try:
    from dotenv import load_dotenv
    load_dotenv()  # берёт переменные окружения из .env
except ImportError:
    # python-dotenv не установлен, продолжаем без него
    pass

# Токены и API ключи из переменных окружения
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_TOKEN_HERE")
DMARKET_PUBLIC_KEY = os.environ.get("DMARKET_PUBLIC_KEY", "")
DMARKET_SECRET_KEY = os.environ.get("DMARKET_SECRET_KEY", "")
DMARKET_API_URL = os.environ.get("DMARKET_API_URL", "https://api.dmarket.com")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    if update.message:
        await update.message.reply_text(
            "Hello! I am your Telegram bot. "
            "Use /help to see available commands."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a list of available commands when the /help command is issued."""
    if update.message:
        await update.message.reply_text(
            "Available commands:\n"
            "/start — welcome\n"
            "/help — show this help message\n"
            "/dmarket — check DMarket API status"
        )


async def dmarket_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check if Dmarket API keys are configured."""
    if update.message:
        if DMARKET_PUBLIC_KEY and DMARKET_SECRET_KEY:
            await update.message.reply_text(
                "DMarket API keys are configured.\n"
                "API endpoint: " + DMARKET_API_URL
            )
        else:
            await update.message.reply_text(
                "DMarket API keys are not configured.\n"
                "Please add them to your .env file."
            )


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("dmarket", dmarket_status))
    app.run_polling()
