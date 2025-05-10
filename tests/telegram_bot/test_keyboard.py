"""Test script for the Telegram bot to verify keyboard functionality.
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(".") / ".env"
load_dotenv(dotenv_path=str(env_path))
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with a keyboard when the command /start is issued."""
    from src.telegram_bot.keyboards import get_permanent_reply_keyboard

    # Send a message with the keyboard
    await update.message.reply_text(
        "Testing permanent keyboard. Should appear below:",
        reply_markup=get_permanent_reply_keyboard(),
    )

    # Log that we've sent the keyboard
    logger.info(f"Sent keyboard to {update.effective_user.first_name}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle messages from the keyboard."""
    text = update.message.text
    logger.info(f"Received message: {text}")
    await update.message.reply_text(f"You pressed: {text}")


async def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TOKEN).build()

    # Try to set default settings to improve keyboard visibility
    application.bot.defaults.disable_web_page_preview = True
    application.bot.defaults.disable_notification = False

    # Add command handlers
    application.add_handler(CommandHandler("start", start))

    # Add message handler to handle keyboard presses
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    logger.info("Bot started successfully - press Ctrl+C to stop")
    try:
        # Keep the bot running until interrupted
        await asyncio.sleep(float("inf"))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot shutdown initiated")
    finally:
        # Graceful shutdown
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
