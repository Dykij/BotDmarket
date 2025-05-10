"""Модуль обработки callback запросов арбитража.

Реализует:
- Обработку колбэков для различных режимов арбитража
- Пагинацию результатов
- Форматирование ответов с HTML разметкой
- Индикацию действий через ChatAction
"""

import logging

from telegram import CallbackQuery, ChatAction, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from src.dmarket.arbitrage import GAMES
from src.telegram_bot.keyboards import (
    get_arbitrage_keyboard,
    get_game_selection_keyboard,
    get_marketplace_comparison_keyboard,
    get_modern_arbitrage_keyboard,
)
from src.telegram_bot.utils.formatting import format_best_opportunities, format_dmarket_results
from src.utils.api_error_handling import APIError
from src.utils.dmarket_api_utils import execute_api_request

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
SELECTING_GAME, SELECTING_MODE, CONFIRMING_ACTION = range(3)


async def arbitrage_callback_impl(update: Update, context: CallbackContext) -> int | None:
    """Реализация обработки кнопки арбитража.

    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика

    Returns:
        int: Следующее состояние разговора или None

    """
    query = update.callback_query
    await query.answer()

    # Показываем индикатор, что бот печатает
    await update.effective_chat.send_action(ChatAction.TYPING)

    # Проверяем, использует ли пользователь современный UI
    user_id = query.from_user.id
    user_data = context.user_data or {}

    # Если у пользователя есть настройка современного UI, используем её
    use_modern_ui = user_data.get("use_modern_ui", False)

    if use_modern_ui:
        keyboard = get_modern_arbitrage_keyboard()
    else:
        keyboard = get_arbitrage_keyboard()

    await query.edit_message_text(
        text="🔍 <b>Выберите режим арбитража:</b>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )

    # Возвращаем состояние выбора режима
    return SELECTING_MODE


async def handle_dmarket_arbitrage_impl(
    query: CallbackQuery, context: CallbackContext, mode: str
) -> None:
    """Обрабатывает запрос на поиск арбитражных возможностей на DMarket.

    Args:
        query: Объект callback-запроса
        context: Контекст бота
        mode: Режим арбитража ("boost", "mid", "pro")

    """
    # Получаем выбранную игру
    user_data = context.user_data or {}
    game = user_data.get("current_game", "csgo")

    # Сохраняем последний выбранный режим
    user_data["last_arbitrage_mode"] = mode

    # Словарь для отображения режимов на русском языке
    mode_display = {
        "boost": "Разгон баланса",
        "mid": "Средний трейдер",
        "pro": "Trade Pro",
    }

    # Показываем, что запрос обрабатывается
    await query.message.chat.send_action(ChatAction.TYPING)

    # Редактируем сообщение, показывая процесс поиска
    await query.edit_message_text(
        text=(
            f"🔍 <b>Поиск арбитражных возможностей</b>\n\n"
            f"Режим: <b>{mode_display.get(mode, mode)}</b>\n"
            f"Игра: <b>{GAMES.get(game, game)}</b>\n\n"
            f"<i>Пожалуйста, подождите...</i>"
        ),
        reply_markup=None,
        parse_mode=ParseMode.HTML,
    )

    try:
        # Показываем индикатор загрузки
        await query.message.chat.send_action(ChatAction.TYPING)

        # Определяем функцию для получения данных арбитража
        async def get_arbitrage_data():
            from src.dmarket.arbitrage import (
                arbitrage_boost_async,
                arbitrage_mid_async,
                arbitrage_pro_async,
            )

            if mode == "boost":
                return await arbitrage_boost_async(game)
            if mode == "pro":
                return await arbitrage_pro_async(game)
            return await arbitrage_mid_async(game)

        # Выполняем API запрос с обработкой ошибок и лимитов
        results = await execute_api_request(
            request_func=get_arbitrage_data,
            endpoint_type="market",
            max_retries=2,
        )

        # Если получены результаты
        if results:
            from src.telegram_bot.pagination import format_paginated_results, pagination_manager

            # Подготавливаем пагинацию результатов
            user_id = query.from_user.id
            pagination_manager.add_items_for_user(user_id, results, mode)
            page_items, current_page, total_pages = pagination_manager.get_page(user_id)

            # Форматируем текст с результатами
            formatted_text = format_paginated_results(
                page_items,
                game,
                mode,
                current_page,
                total_pages,
            )

            # Создаем клавиатуру с кнопками пагинации
            keyboard = []

            # Добавляем кнопки пагинации, если страниц больше одной
            if total_pages > 1:
                pagination_row = []

                if current_page > 0:
                    pagination_row.append(
                        InlineKeyboardButton(
                            "⬅️ Пред.",
                            callback_data=f"paginate:prev:{mode}",
                        ),
                    )

                # Добавляем индикатор текущей страницы
                pagination_row.append(
                    InlineKeyboardButton(
                        f"{current_page + 1}/{total_pages}",
                        callback_data="page_info",
                    ),
                )

                if current_page < total_pages - 1:
                    pagination_row.append(
                        InlineKeyboardButton(
                            "След. ➡️",
                            callback_data=f"paginate:next:{mode}",
                        ),
                    )

                if pagination_row:
                    keyboard.append(pagination_row)

            # Добавляем кнопки действий с результатами
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "📊 Подробный анализ",
                        callback_data=f"analyze:{mode}",
                    ),
                    InlineKeyboardButton(
                        "🔄 Обновить",
                        callback_data=f"refresh:{mode}",
                    ),
                ]
            )

            # Добавляем кнопку открытия DMarket
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "🌐 Открыть DMarket",
                        web_app={"url": "https://dmarket.com"},
                    ),
                ]
            )

            # Добавляем стандартные кнопки меню арбитража
            arbitrage_keyboard = get_arbitrage_keyboard().inline_keyboard
            keyboard.extend(arbitrage_keyboard[-1:])  # Только кнопка "Назад"

            # Отправляем сообщение с результатами
            await query.edit_message_text(
                text=formatted_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
        else:
            # Если результатов нет, показываем соответствующее сообщение
            formatted_text = format_dmarket_results(results, mode, game)
            keyboard = get_arbitrage_keyboard()

            await query.edit_message_text(
                text=formatted_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )

    except APIError as e:
        # Обрабатываем ошибки API
        logger.error(f"Ошибка API при поиске арбитражных возможностей: {e.message}")

        # Формируем сообщение об ошибке в зависимости от статус-кода
        if e.status_code == 429:
            error_message = (
                "⏱️ <b>Превышен лимит запросов к DMarket API.</b>\n\n"
                "Пожалуйста, подождите немного и попробуйте снова."
            )
        elif e.status_code == 401:
            error_message = (
                "🔐 <b>Ошибка авторизации в DMarket API.</b>\n\n" "Проверьте настройки API ключей."
            )
        elif e.status_code == 404:
            error_message = (
                "🔍 <b>Запрашиваемые данные не найдены в DMarket API.</b>\n\n"
                "Возможно, указаны неверные параметры запроса."
            )
        elif e.status_code >= 500:
            error_message = (
                f"🔧 <b>Сервер DMarket временно недоступен.</b>\n\n"
                f"Статус: {e.status_code}\n"
                f"Попробуйте повторить запрос позже."
            )
        else:
            error_message = (
                f"❌ <b>Ошибка DMarket API:</b>\n\n"
                f"Код: {e.status_code}\n"
                f"Сообщение: {e.message}"
            )

        # Создаем клавиатуру с кнопкой повтора
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="arbitrage")],
                [InlineKeyboardButton("« Назад", callback_data="back_to_menu")],
            ]
        )

        # Отправляем сообщение об ошибке
        await query.edit_message_text(
            text=error_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )

    except Exception as e:
        # Обрабатываем непредвиденные ошибки
        logger.error(f"Ошибка при поиске арбитражных возможностей: {e!s}")

        # Создаем клавиатуру с кнопкой повтора
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="arbitrage")],
                [InlineKeyboardButton("« Назад", callback_data="back_to_menu")],
            ]
        )

        # Отправляем сообщение об ошибке
        error_message = (
            f"❌ <b>Непредвиденная ошибка:</b>\n\n"
            f"<code>{e!s}</code>\n\n"
            f"Пожалуйста, сообщите об этой ошибке разработчикам."
        )

        await query.edit_message_text(
            text=error_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )


async def handle_best_opportunities_impl(query: CallbackQuery, context: CallbackContext) -> None:
    """Обрабатывает запрос на поиск лучших арбитражных возможностей.

    Args:
        query: Объект callback-запроса
        context: Контекст бота

    """
    # Получаем выбранную игру
    user_data = context.user_data or {}
    game = user_data.get("current_game", "csgo")

    # Показываем, что запрос обрабатывается
    await query.message.chat.send_action(ChatAction.TYPING)

    # Редактируем сообщение, показывая процесс поиска
    await query.edit_message_text(
        text=(
            f"🔍 <b>Поиск лучших арбитражных возможностей</b>\n\n"
            f"Игра: <b>{GAMES.get(game, game)}</b>\n\n"
            f"<i>Идет анализ рынка, пожалуйста подождите...</i>"
        ),
        reply_markup=None,
        parse_mode=ParseMode.HTML,
    )

    try:
        # Показываем индикатор загрузки
        await query.message.chat.send_action(ChatAction.TYPING)

        # Получаем арбитражные возможности
        from src.telegram_bot.arbitrage_scanner import find_arbitrage_opportunities

        # Отображаем прогресс
        await query.edit_message_text(
            text=(
                f"🔍 <b>Поиск лучших арбитражных возможностей</b>\n\n"
                f"Игра: <b>{GAMES.get(game, game)}</b>\n\n"
                f"<i>Анализ цен... (1/3)</i>"
            ),
            parse_mode=ParseMode.HTML,
        )

        # Находим арбитражные возможности
        opportunities = await find_arbitrage_opportunities(
            game=game,
            min_profit_percentage=5.0,
            max_items=10,
        )

        # Обновляем прогресс
        await query.edit_message_text(
            text=(
                f"🔍 <b>Поиск лучших арбитражных возможностей</b>\n\n"
                f"Игра: <b>{GAMES.get(game, game)}</b>\n\n"
                f"<i>Подготовка результатов... (3/3)</i>"
            ),
            parse_mode=ParseMode.HTML,
        )

        # Форматируем результаты
        formatted_text = format_best_opportunities(opportunities, game)

        # Создаем клавиатуру с кнопками действий
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔄 Обновить", callback_data="best_opportunities"),
                    InlineKeyboardButton("🌐 DMarket", web_app={"url": "https://dmarket.com"}),
                ],
                [InlineKeyboardButton("« Назад", callback_data="arbitrage")],
            ]
        )

        # Отправляем результаты
        await query.edit_message_text(
            text=formatted_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )

    except Exception as e:
        # Обрабатываем ошибки
        logger.error(f"Ошибка при поиске лучших арбитражных возможностей: {e!s}")

        # Создаем клавиатуру с кнопкой повтора
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="best_opportunities")],
                [InlineKeyboardButton("« Назад", callback_data="arbitrage")],
            ]
        )

        # Отправляем сообщение об ошибке
        error_message = (
            f"❌ <b>Ошибка при поиске лучших арбитражных возможностей:</b>\n\n" f"<code>{e!s}</code>"
        )

        await query.edit_message_text(
            text=error_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )


async def handle_game_selection_impl(query: CallbackQuery, context: CallbackContext) -> int | None:
    """Обрабатывает выбор игры для арбитража.

    Args:
        query: Объект callback-запроса
        context: Контекст бота

    Returns:
        int: Следующее состояние разговора или None

    """
    await query.answer()

    # Показываем индикатор, что бот печатает
    await query.message.chat.send_action(ChatAction.TYPING)

    # Получаем клавиатуру выбора игры
    keyboard = get_game_selection_keyboard()

    # Отправляем сообщение с выбором игры
    await query.edit_message_text(
        text=(
            "🎮 <b>Выберите игру для арбитража:</b>\n\n"
            "<i>Для каждой игры доступны свои рынки и возможности</i>"
        ),
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )

    # Возвращаем состояние выбора игры
    return SELECTING_GAME


async def handle_game_selected_impl(
    query: CallbackQuery, context: CallbackContext, game: str
) -> int | None:
    """Обрабатывает выбор конкретной игры.

    Args:
        query: Объект callback-запроса
        context: Контекст бота
        game: Выбранная игра

    Returns:
        int: Следующее состояние разговора или None

    """
    await query.answer()

    # Сохраняем выбранную игру
    if not hasattr(context, "user_data"):
        context.user_data = {}

    context.user_data["current_game"] = game

    # Показываем индикатор, что бот печатает
    await query.message.chat.send_action(ChatAction.TYPING)

    # Получаем клавиатуру арбитража
    keyboard = get_arbitrage_keyboard()

    # Отправляем сообщение с подтверждением выбора
    await query.edit_message_text(
        text=(
            f"✅ <b>Выбрана игра:</b> {GAMES.get(game, game)}\n\n"
            f"Теперь выберите режим арбитража:"
        ),
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )

    # Возвращаем состояние выбора режима
    return SELECTING_MODE


async def handle_market_comparison_impl(query: CallbackQuery, context: CallbackContext) -> None:
    """Показывает сравнение различных торговых площадок.

    Args:
        query: Объект callback-запроса
        context: Контекст бота

    """
    await query.answer()

    # Показываем индикатор, что бот печатает
    await query.message.chat.send_action(ChatAction.TYPING)

    # Получаем клавиатуру сравнения маркетплейсов
    keyboard = get_marketplace_comparison_keyboard()

    # Отправляем сообщение с выбором маркетплейса
    await query.edit_message_text(
        text=(
            "🔄 <b>Сравнение торговых площадок</b>\n\n"
            "Выберите площадку для просмотра:\n\n"
            "<i>Вы можете открыть любую из этих площадок прямо в Telegram</i>"
        ),
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )
