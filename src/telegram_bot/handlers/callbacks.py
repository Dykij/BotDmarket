"""
Обработчики callbacks для Telegram бота.

Этот модуль содержит функции обработки callback-запросов от inline-кнопок.
"""

import logging
import traceback
from typing import Dict, Any, Optional, List, Union, Tuple

from telegram import Update, CallbackQuery
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CallbackContext

from src.telegram_bot.keyboards import (
    get_modern_arbitrage_keyboard,
    get_auto_arbitrage_keyboard,
    get_back_to_arbitrage_keyboard,
    get_game_selection_keyboard,
    get_dmarket_webapp_keyboard
)

from src.dmarket.arbitrage import GAMES
from src.utils.api_error_handling import APIError, handle_api_error
from src.telegram_bot.pagination import pagination_manager
from src.telegram_bot.auto_arbitrage import (
    handle_pagination,
    show_auto_stats_with_pagination,
    start_auto_trading
)

logger = logging.getLogger(__name__)

async def arbitrage_callback_impl(update, context):
    """
    Обрабатывает callback 'arbitrage'.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом
    """
    await update.callback_query.edit_message_text(
        "🔍 <b>Меню арбитража:</b>",
        reply_markup=get_modern_arbitrage_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def handle_dmarket_arbitrage_impl(update, context, mode="normal"):
    """
    Обрабатывает callback 'dmarket_arbitrage'.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом
        mode: Режим арбитража
    """
    await update.callback_query.edit_message_text(
        "🔍 <b>DMarket Арбитраж</b>\n\n"
        "Функция находится в разработке.",
        reply_markup=get_back_to_arbitrage_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def handle_best_opportunities_impl(update, context):
    """
    Обрабатывает callback 'best_opportunities'.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом
    """
    await update.callback_query.edit_message_text(
        "💰 <b>Лучшие возможности</b>\n\n"
        "Функция находится в разработке.",
        reply_markup=get_back_to_arbitrage_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def handle_game_selection_impl(update, context):
    """
    Обрабатывает callback 'game_selection'.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом
    """
    await update.callback_query.edit_message_text(
        "🎮 <b>Выберите игру для арбитража:</b>",
        reply_markup=get_game_selection_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def handle_game_selected_impl(update, context, game=None):
    """
    Обрабатывает callback 'game_selected:...'.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом
        game: Код выбранной игры
    """
    # Извлекаем код игры из callback_data
    if game is None and update.callback_query.data.startswith("game_selected:"):
        game = update.callback_query.data.split(":", 1)[1]
    
    game_name = GAMES.get(game, "Неизвестная игра")
    await update.callback_query.edit_message_text(
        f"🎮 <b>Выбрана игра: {game_name}</b>\n\n"
        "Функция находится в разработке.",
        reply_markup=get_back_to_arbitrage_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def handle_market_comparison_impl(update, context):
    """
    Обрабатывает callback 'market_comparison'.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом
    """
    from src.telegram_bot.keyboards import get_marketplace_comparison_keyboard
    await update.callback_query.edit_message_text(
        "📊 <b>Сравнение рынков</b>\n\n"
        "Выберите рынки для сравнения:",
        reply_markup=get_marketplace_comparison_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Общий обработчик колбэков от кнопок.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом
    """
    query = update.callback_query
    callback_data = query.data

    # Показываем индикатор загрузки
    await query.answer()
    
    try:
        # Обработка для арбитража
        if callback_data == "arbitrage":
            await arbitrage_callback_impl(update, context)
            
        elif callback_data == "auto_arbitrage":
            # Показываем меню автоарбитража
            keyboard = get_auto_arbitrage_keyboard()
            await query.edit_message_text(
                "🤖 <b>Выберите режим автоматического арбитража:</b>",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            
        elif callback_data == "dmarket_arbitrage":
            # Делегируем обработку специализированному обработчику
            await handle_dmarket_arbitrage_impl(update, context, mode="normal")
            
        elif callback_data == "best_opportunities":
            # Делегируем обработку специализированному обработчику
            await handle_best_opportunities_impl(update, context)
            
        elif callback_data == "game_selection":
            # Делегируем обработку специализированному обработчику
            await handle_game_selection_impl(update, context)
            
        elif callback_data.startswith("game_selected:"):
            # Извлекаем код игры из callback_data
            game = callback_data.split(":", 1)[1]
            # Делегируем обработку специализированному обработчику
            await handle_game_selected_impl(update, context, game=game)
            
        elif callback_data == "market_comparison":
            # Делегируем обработку специализированному обработчику
            await handle_market_comparison_impl(update, context)
            
        elif callback_data == "market_analysis":
            # Обработка для анализа рынка
            await query.edit_message_text(
                "📊 <b>Анализ рынка</b>\n\n"
                "Выберите игру для анализа рыночных тенденций и цен:",
                reply_markup=get_game_selection_keyboard(),
                parse_mode=ParseMode.HTML
            )
            
        elif callback_data == "filter:" or callback_data.startswith("filter:"):
            # Обработка фильтров
            await query.edit_message_text(
                "⚙️ <b>Настройка фильтров</b>\n\n"
                "Выберите игру для настройки фильтров:",
                reply_markup=get_game_selection_keyboard(),
                parse_mode=ParseMode.HTML
            )
            
        elif callback_data == "open_webapp":
            # Открытие WebApp с DMarket
            await query.edit_message_text(
                "🌐 <b>DMarket WebApp</b>\n\n"
                "Нажмите кнопку ниже, чтобы открыть DMarket прямо в Telegram:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_dmarket_webapp_keyboard()
            )
            
        elif callback_data.startswith("auto_start:"):
            # Извлекаем режим автоарбитража и запускаем его
            mode = callback_data.split(":", 1)[1]
            await start_auto_trading(query, context, mode)
            
        elif callback_data.startswith("paginate:"):
            # Обработка пагинации для результатов автоарбитража
            parts = callback_data.split(":")
            if len(parts) >= 3:
                direction = parts[1]  # prev или next
                mode = parts[2]  # режим автоарбитража
                await handle_pagination(query, context, direction, mode)
            else:
                await query.edit_message_text(
                    "⚠️ <b>Некорректный формат данных пагинации.</b>\n\nПопробуйте снова.",
                    reply_markup=get_back_to_arbitrage_keyboard(),
                    parse_mode=ParseMode.HTML
                )
                
        elif callback_data == "auto_stats":
            # Показываем статистику автоарбитража
            await show_auto_stats_with_pagination(query, context)
            
        elif callback_data.startswith("auto_trade:"):
            # Запускаем автоматическую торговлю для выбранного режима
            mode = callback_data.split(":", 1)[1]
            
            # Делегируем обработку соответствующему модулю
            from src.telegram_bot.auto_arbitrage import handle_auto_trade
            await handle_auto_trade(query, context, mode)
            
        elif callback_data == "back_to_menu":
            # Возврат в главное меню
            await query.edit_message_text(
                "👋 <b>Главное меню</b>\n\n"
                "Выберите действие:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_modern_arbitrage_keyboard()
            )
            
        else:
            # Неизвестный callback
            logger.warning(f"Неизвестный callback_data: {callback_data}")
            await query.edit_message_text(
                "⚠️ <b>Неизвестная команда.</b>\n\nПожалуйста, вернитесь в главное меню:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_to_arbitrage_keyboard()
            )
            
    except APIError as e:
        # Используем улучшенную обработку ошибок API
        error_message = await handle_api_error(e)
        await query.edit_message_text(
            f"❌ <b>Ошибка API DMarket:</b>\n\n{error_message}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_to_arbitrage_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке callback {callback_data}: {e}")
        tb_string = traceback.format_exc()
        logger.error(f"Traceback: {tb_string}")
        
        await query.edit_message_text(
            f"❌ <b>Произошла ошибка при обработке запроса:</b>\n\n"
            f"{str(e)}\n\n"
            f"Пожалуйста, вернитесь в главное меню:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_to_arbitrage_keyboard()
        )

# Экспортируем обработчики callbacks
__all__ = [
    'arbitrage_callback_impl',
    'handle_dmarket_arbitrage_impl',
    'handle_best_opportunities_impl',
    'handle_game_selection_impl',
    'handle_game_selected_impl',
    'handle_market_comparison_impl',
    'button_callback_handler',
]
