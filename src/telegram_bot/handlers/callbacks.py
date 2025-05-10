"""Обработчики callbacks для Telegram бота.

Этот модуль содержит функции обработки callback-запросов от inline-кнопок.
"""

import logging
import traceback

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.dmarket.arbitrage import GAMES, find_arbitrage_opportunities
from src.telegram_bot.auto_arbitrage import (
    handle_pagination,
    show_auto_stats_with_pagination,
    start_auto_trading,
)
from src.telegram_bot.keyboards import (
    get_auto_arbitrage_keyboard,
    get_back_to_arbitrage_keyboard,
    get_dmarket_webapp_keyboard,
    get_game_selection_keyboard,
    get_modern_arbitrage_keyboard,
    create_pagination_keyboard,
)
from src.telegram_bot.utils.formatters import format_opportunities
from src.telegram_bot.utils.api_client import setup_api_client
from src.utils.api_error_handling import APIError, handle_api_error

logger = logging.getLogger(__name__)


async def arbitrage_callback_impl(update, context):
    """Обрабатывает callback 'arbitrage'.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом

    """
    await update.callback_query.edit_message_text(
        "🔍 <b>Меню арбитража:</b>",
        reply_markup=get_modern_arbitrage_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def handle_dmarket_arbitrage_impl(update, context, mode="normal"):
    """Обрабатывает callback 'dmarket_arbitrage'.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом
        mode: Режим арбитража

    """
    query = update.callback_query
    # Сообщаем пользователю, что начался поиск возможностей
    await query.edit_message_text(
        "🔍 <b>Поиск арбитражных возможностей...</b>\n\n"
        "Это может занять некоторое время, пожалуйста, подождите.",
        parse_mode=ParseMode.HTML
    )
    
    # Получаем API клиент
    api_client = setup_api_client()
    if not api_client:
        await query.edit_message_text(
            "❌ <b>Ошибка</b>\n\n"
            "Не удалось инициализировать API клиент DMarket. "
            "Проверьте настройки API ключей.",
            reply_markup=get_back_to_arbitrage_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        # Поиск арбитражных возможностей
        async with api_client:
            opportunities = await find_arbitrage_opportunities(api_client, mode=mode)
        
        if not opportunities:
            await query.edit_message_text(
                "🔍 <b>Арбитражные возможности не найдены</b>\n\n"
                "Попробуйте изменить параметры поиска или повторить позже.",
                reply_markup=get_back_to_arbitrage_keyboard(),
                parse_mode=ParseMode.HTML
            )
            return
        
        # Сохраняем результаты в контексте для пагинации
        context.user_data["arbitrage_opportunities"] = opportunities
        context.user_data["arbitrage_page"] = 0
        context.user_data["arbitrage_mode"] = mode
        
        # Форматируем и отображаем результаты
        await show_arbitrage_opportunities(query, context)
    
    except Exception as e:
        logger.error(f"Ошибка при поиске арбитражных возможностей: {e}")
        logger.error(traceback.format_exc())
        
        await query.edit_message_text(
            f"❌ <b>Ошибка при поиске возможностей</b>\n\n"
            f"Произошла ошибка: {str(e)}",
            reply_markup=get_back_to_arbitrage_keyboard(),
            parse_mode=ParseMode.HTML
        )


async def show_arbitrage_opportunities(query, context, page=None):
    """Отображает результаты арбитража с пагинацией.
    
    Args:
        query: Объект callback_query
        context: Контекст взаимодействия с ботом
        page: Номер страницы (если None, берется из context.user_data)
    """
    # Получаем данные из контекста
    opportunities = context.user_data.get("arbitrage_opportunities", [])
    current_page = page if page is not None else context.user_data.get("arbitrage_page", 0)
    mode = context.user_data.get("arbitrage_mode", "normal")
    
    # Пересчитываем текущую страницу при необходимости
    total_pages = max(1, (len(opportunities) + 2) // 3)  # по 3 возможности на странице
    if current_page >= total_pages:
        current_page = 0
    
    # Сохраняем текущую страницу
    context.user_data["arbitrage_page"] = current_page
    
    # Форматируем результаты
    results_text = format_opportunities(opportunities, current_page, 3)
    
    # Создаем клавиатуру для пагинации
    keyboard = create_pagination_keyboard(
        current_page=current_page,
        total_pages=total_pages,
        prefix="arb_",
        with_nums=True,
        back_button=True,
        back_text="« Назад к меню",
        back_callback="back_to_menu"
    )
    
    # Отправляем сообщение
    await query.edit_message_text(
        results_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def handle_arbitrage_pagination(query, context, direction):
    """Обрабатывает пагинацию результатов арбитража.
    
    Args:
        query: Объект callback_query
        context: Контекст взаимодействия с ботом
        direction: Направление (next_page или prev_page)
    """
    current_page = context.user_data.get("arbitrage_page", 0)
    opportunities = context.user_data.get("arbitrage_opportunities", [])
    total_pages = max(1, (len(opportunities) + 2) // 3)
    
    if direction == "next_page" and current_page < total_pages - 1:
        current_page += 1
    elif direction == "prev_page" and current_page > 0:
        current_page -= 1
    
    context.user_data["arbitrage_page"] = current_page
    await show_arbitrage_opportunities(query, context, current_page)


async def handle_best_opportunities_impl(update, context):
    """Обрабатывает callback 'best_opportunities'.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом

    """
    # Перенаправляем на функцию поиска арбитражных возможностей с режимом "best"
    await handle_dmarket_arbitrage_impl(update, context, mode="best")


async def handle_game_selection_impl(update, context):
    """Обрабатывает callback 'game_selection'.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом

    """
    await update.callback_query.edit_message_text(
        "🎮 <b>Выберите игру для арбитража:</b>",
        reply_markup=get_game_selection_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def handle_game_selected_impl(update, context, game=None):
    """Обрабатывает callback 'game_selected:...'.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом
        game: Код выбранной игры

    """
    # Извлекаем код игры из callback_data
    if game is None and update.callback_query.data.startswith("game_selected:"):
        game = update.callback_query.data.split(":", 1)[1]

    # Сохраняем выбранную игру в контексте пользователя
    context.user_data["selected_game"] = game
    
    game_name = GAMES.get(game, "Неизвестная игра")
    await update.callback_query.edit_message_text(
        f"🎮 <b>Выбрана игра: {game_name}</b>\n\n"
        f"Выполняется поиск арбитражных возможностей для {game_name}...",
        parse_mode=ParseMode.HTML,
    )
    
    # Запускаем поиск арбитражных возможностей для выбранной игры
    await handle_dmarket_arbitrage_impl(update, context, mode=f"game_{game}")


async def handle_market_comparison_impl(update, context):
    """Обрабатывает callback 'market_comparison'.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом

    """
    from src.telegram_bot.keyboards import get_marketplace_comparison_keyboard

    await update.callback_query.edit_message_text(
        "📊 <b>Сравнение рынков</b>\n\n" "Выберите рынки для сравнения:",
        reply_markup=get_marketplace_comparison_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Общий обработчик колбэков от кнопок.

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
                parse_mode=ParseMode.HTML,
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

        # Обработка пагинации для арбитража
        elif callback_data.startswith("arb_next_page_") or callback_data.startswith("arb_prev_page_"):
            direction = "next_page" if callback_data.startswith("arb_next_page_") else "prev_page"
            await handle_arbitrage_pagination(query, context, direction)

        elif callback_data == "market_analysis":
            # Обработка для анализа рынка
            await query.edit_message_text(
                "📊 <b>Анализ рынка</b>\n\n" "Выберите игру для анализа рыночных тенденций и цен:",
                reply_markup=get_game_selection_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        elif callback_data == "filter:" or callback_data.startswith("filter:"):
            # Обработка фильтров
            await query.edit_message_text(
                "⚙️ <b>Настройка фильтров</b>\n\n" "Выберите игру для настройки фильтров:",
                reply_markup=get_game_selection_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        elif callback_data == "open_webapp":
            # Открытие WebApp с DMarket
            await query.edit_message_text(
                "🌐 <b>DMarket WebApp</b>\n\n"
                "Нажмите кнопку ниже, чтобы открыть DMarket прямо в Telegram:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_dmarket_webapp_keyboard(),
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
                    parse_mode=ParseMode.HTML,
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
                "👋 <b>Главное меню</b>\n\n" "Выберите действие:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_modern_arbitrage_keyboard(),
            )

        else:
            # Неизвестный callback
            logger.warning(f"Неизвестный callback_data: {callback_data}")
            await query.edit_message_text(
                "⚠️ <b>Неизвестная команда.</b>\n\nПожалуйста, вернитесь в главное меню:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_to_arbitrage_keyboard(),
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке callback {callback_data}: {e}")
        logger.error(traceback.format_exc())
        
        # Оповещение пользователя об ошибке
        try:
            await query.edit_message_text(
                f"❌ <b>Произошла ошибка при обработке команды</b>\n\n"
                f"Ошибка: {str(e)}\n\n"
                f"Пожалуйста, попробуйте позже или обратитесь к администратору.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_to_arbitrage_keyboard(),
            )
        except Exception as edit_error:
            logger.error(f"Ошибка при отправке сообщения об ошибке: {edit_error}")
            # Простое уведомление, если не удалось отредактировать сообщение
            await query.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")


# Экспортируем обработчики callbacks
__all__ = [
    "arbitrage_callback_impl",
    "button_callback_handler",
    "handle_best_opportunities_impl",
    "handle_dmarket_arbitrage_impl",
    "handle_game_selected_impl",
    "handle_game_selection_impl",
    "handle_market_comparison_impl",
]
