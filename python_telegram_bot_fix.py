#!/usr/bin/env python
"""Fix for python-telegram-bot 20.0+ with APScheduler timezone issues."""

# Try to monkey patch the get_localzone function
try:
    import pytz
    import tzlocal

    original_get_localzone = tzlocal.get_localzone

    def patched_get_localzone():
        return pytz.timezone("Europe/Moscow")

    tzlocal.get_localzone = patched_get_localzone
    print("✅ Successfully patched tzlocal.get_localzone")
except Exception as e:
    print(f"❌ Failed to patch tzlocal.get_localzone: {e}")

# Set the TZ environment variable
import os

os.environ["TZ"] = "Europe/Moscow"
print("✅ Set TZ environment variable to Europe/Moscow")

# Create a minimal bot
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! I'm a test bot.")

def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No token provided")
        return

    # Try different approaches to create the Application
    try:
        application = Application.builder().token(token).build()
        logger.info("✅ Created application with default builder")
    except Exception as e1:
        logger.error(f"❌ Failed with default builder: {e1}")

        try:
            # Try with job_queue=None
            application = Application.builder().token(token).job_queue(None).build()
            logger.info("✅ Created application with job_queue=None")
        except Exception as e2:
            logger.error(f"❌ Failed with job_queue=None: {e2}")
            return

    # Add handlers
    application.add_handler(CommandHandler("start", start))

    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
