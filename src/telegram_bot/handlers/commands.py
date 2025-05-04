from telegram import Update
from telegram.ext import CallbackContext
from src.telegram_bot.keyboards import get_arbitrage_keyboard
from src.telegram_bot.settings_handlers import get_localized_text
from src.telegram_bot.profiles import get_user_profile

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = user.id
    welcome_message = get_localized_text(user_id, "welcome", user=user.mention_html())
    keyboard = get_arbitrage_keyboard()
    await update.message.reply_html(welcome_message, reply_markup=keyboard)

async def help_command(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    help_text = get_localized_text(user_id, "help")
    await update.message.reply_text(help_text)

async def dmarket_status(update: Update, context: CallbackContext) -> None:
    from src.telegram_bot.handlers.dmarket_status import dmarket_status_impl
    await dmarket_status_impl(update, context)

async def arbitrage_command(update: Update, context: CallbackContext) -> None:
    keyboard = get_arbitrage_keyboard()
    await update.message.reply_text(
        "📊 Выберите режим арбитража:",
        reply_markup=keyboard
    )
