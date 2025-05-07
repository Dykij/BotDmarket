"""Minimal test bot to check if python-telegram-bot works correctly."""

import logging
import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO,
)
# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Define a few command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user

    # Create keyboard with buttons
    keyboard = [
        [
            InlineKeyboardButton("Option 1", callback_data="option1"),
            InlineKeyboardButton("Option 2", callback_data="option2"),
        ],
        [InlineKeyboardButton("Option 3", callback_data="option3")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send message with keyboard
    await update.message.reply_text(
        f"Hi {user.full_name}! Testing keyboard functionality:",
        reply_markup=reply_markup,
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses"""
    query = update.callback_query

    # Answer callback query
    await query.answer()

    # Get callback data
    data = query.data

    # Edit message based on which button was pressed
    await query.edit_message_text(text=f"Selected option: {data}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


def main() -> None:
    """Start the bot."""
    # Load environment variables from .env file
    load_dotenv()

    # Get the token from environment variables
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No token provided. Set TELEGRAM_BOT_TOKEN environment variable")
        return

    # Create the Application and pass it your bot's token
    application = Application.builder().token(token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Add callback query handler for button presses
    application.add_handler(CallbackQueryHandler(button_callback))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error running bot: {e}")


if __name__ == "__main__":
    main()
