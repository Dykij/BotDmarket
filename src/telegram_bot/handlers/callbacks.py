from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from src.telegram_bot.keyboards import get_arbitrage_keyboard, get_auto_arbitrage_keyboard, get_game_selection_keyboard
from src.dmarket.arbitrage import GAMES
from src.telegram_bot.utils.formatting import format_dmarket_results, format_best_opportunities

async def arbitrage_callback(update: Update, context: CallbackContext) -> None:
    from src.telegram_bot.handlers.arbitrage_callback_impl import arbitrage_callback_impl
    await arbitrage_callback_impl(update, context)

async def handle_dmarket_arbitrage(query, context: CallbackContext, mode: str) -> None:
    from src.telegram_bot.handlers.arbitrage_callback_impl import handle_dmarket_arbitrage_impl
    await handle_dmarket_arbitrage_impl(query, context, mode)

async def handle_best_opportunities(query, context: CallbackContext) -> None:
    from src.telegram_bot.handlers.arbitrage_callback_impl import handle_best_opportunities_impl
    await handle_best_opportunities_impl(query, context)
