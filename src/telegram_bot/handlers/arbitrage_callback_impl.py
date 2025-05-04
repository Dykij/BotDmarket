from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.dmarket.arbitrage import GAMES
from src.telegram_bot.keyboards import get_arbitrage_keyboard, get_auto_arbitrage_keyboard, get_game_selection_keyboard
from src.telegram_bot.utils.formatting import format_dmarket_results, format_best_opportunities

async def arbitrage_callback_impl(update, context):
    # Скопировать сюда логику из arbitrage_callback
    pass

from src.utils.api_error_handling import APIError
from src.utils.dmarket_api_utils import execute_api_request
from telegram.ext import CallbackContext

async def handle_dmarket_arbitrage_impl(query, context: CallbackContext, mode: str):
    """
    Обрабатывает запрос на поиск арбитражных возможностей на DMarket.
    Args:
        query: Объект callback-запроса
        context: Контекст бота
        mode: Режим арбитража ("boost", "mid", "pro")
    """
    game = "csgo"
    if hasattr(context, 'user_data') and "current_game" in context.user_data:
        game = context.user_data["current_game"]
    if not hasattr(context, 'user_data'):
        context.user_data = {}
    context.user_data["last_arbitrage_mode"] = mode
    mode_display = {"boost": "Разгон баланса", "mid": "Средний трейдер", "pro": "Trade Pro"}
    await query.edit_message_text(
        text=f"🔍 Поиск арбитражных возможностей ({mode_display.get(mode, mode)}) "
             f"для игры {GAMES.get(game, game)}...",
        reply_markup=None,
        parse_mode='HTML'
    )
    try:
        async def get_arbitrage_data():
            from src.dmarket.arbitrage import arbitrage_boost_async, arbitrage_mid_async, arbitrage_pro_async
            if mode == "boost":
                return await arbitrage_boost_async(game)
            elif mode == "pro":
                return await arbitrage_pro_async(game)
            else:
                return await arbitrage_mid_async(game)
        results = await execute_api_request(
            request_func=get_arbitrage_data,
            endpoint_type="market",
            max_retries=2
        )
        if results:
            from src.telegram_bot.pagination import pagination_manager, format_paginated_results
            user_id = query.from_user.id
            pagination_manager.add_items_for_user(user_id, results, mode)
            page_items, current_page, total_pages = pagination_manager.get_page(user_id)
            formatted_text = format_paginated_results(
                page_items, game, mode, current_page, total_pages
            )
            keyboard = []
            if total_pages > 1:
                pagination_row = []
                if current_page > 0:
                    pagination_row.append(
                        InlineKeyboardButton(
                            "⬅️ Предыдущая",
                            callback_data=f"paginate:prev:{mode}"
                        )
                    )
                if current_page < total_pages - 1:
                    pagination_row.append(
                        InlineKeyboardButton(
                            "Следующая ➡️",
                            callback_data=f"paginate:next:{mode}"
                        )
                    )
                if pagination_row:
                    keyboard.append(pagination_row)
            arbitrage_keyboard = get_arbitrage_keyboard().inline_keyboard
            keyboard.extend(arbitrage_keyboard)
            await query.edit_message_text(
                text=formatted_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        else:
            formatted_text = format_dmarket_results(results, mode, game)
            keyboard = get_arbitrage_keyboard()
            await query.edit_message_text(
                text=formatted_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    except APIError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка API при поиске арбитражных возможностей: {e.message}")
        if e.status_code == 429:
            error_message = "⏱️ Превышен лимит запросов к DMarket API. Пожалуйста, подождите немного и попробуйте снова."
        elif e.status_code == 401:
            error_message = "🔐 Ошибка авторизации в DMarket API. Проверьте настройки API ключей."
        elif e.status_code == 404:
            error_message = "🔍 Запрашиваемые данные не найдены в DMarket API."
        elif e.status_code >= 500:
            error_message = f"🔧 Сервер DMarket временно недоступен. Попробуйте позже."
        else:
            error_message = f"❌ Ошибка DMarket API: {e.message}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="arbitrage")]
        ])
        await query.edit_message_text(
            text=error_message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при поиске арбитражных возможностей: {str(e)}")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="arbitrage")]
        ])
        error_message = f"❌ Неожиданная ошибка: {str(e)}"
        await query.edit_message_text(
            text=error_message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

async def handle_best_opportunities_impl(query, context):
    """
    Обрабатывает запрос на поиск лучших арбитражных возможностей.
    Args:
        query: Объект callback-запроса
        context: Контекст бота
    """
    game = "csgo"
    if hasattr(context, 'user_data') and "current_game" in context.user_data:
        game = context.user_data["current_game"]
    await query.edit_message_text(
        text=f"🔍 Поиск лучших арбитражных возможностей для {GAMES.get(game, game)}...",
        reply_markup=None
    )
    try:
        from src.telegram_bot.arbitrage_scanner import find_arbitrage_opportunities
        opportunities = find_arbitrage_opportunities(
            game=game,
            min_profit_percentage=5.0,
            max_items=10
        )
        formatted_text = format_best_opportunities(opportunities, game)
        keyboard = get_arbitrage_keyboard()
        await query.edit_message_text(
            text=formatted_text,
            reply_markup=keyboard
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при поиске лучших арбитражных возможностей: {str(e)}")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="arbitrage")]
        ])
        error_message = f"❌ Ошибка при поиске лучших арбитражных возможностей: {str(e)}"
        await query.edit_message_text(text=error_message, reply_markup=keyboard)
