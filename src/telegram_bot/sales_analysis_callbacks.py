"""Обработчики Callback-запросов для модуля анализа продаж.
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from src.dmarket.arbitrage_sales_analysis import (
    analyze_item_liquidity,
    enhanced_arbitrage_search,
    get_sales_volume_stats,
)
from src.dmarket.sales_history import analyze_sales_history, get_sales_history
from src.telegram_bot.sales_analysis_handlers import get_liquidity_emoji, get_trend_emoji
from src.utils.api_error_handling import APIError
from src.utils.dmarket_api_utils import execute_api_request

# Настройка логирования
logger = logging.getLogger(__name__)


async def handle_sales_history_callback(update: Update, context: CallbackContext) -> None:
    """Обрабатывает запрос на просмотр истории продаж."""
    query = update.callback_query
    await query.answer()

    # Извлекаем название предмета из callback_data
    # Формат: "sales_history:item_name"
    callback_data = query.data.split(":", 1)
    if len(callback_data) < 2:
        await query.edit_message_text(
            "❌ Ошибка: некорректные данные запроса.",
            parse_mode="Markdown",
        )
        return

    item_name = callback_data[1]

    # Отправляем сообщение о начале запроса
    await query.edit_message_text(
        f"🔍 Получение истории продаж для предмета:\n`{item_name}`\n\n" "⏳ Пожалуйста, подождите...",
        parse_mode="Markdown",
    )

    try:
        # Создаем функцию для запроса истории продаж
        async def fetch_history():
            result = await get_sales_history(
                item_names=[item_name],
                limit=20,
            )
            return result

        # Выполняем запрос с использованием обработки ошибок API
        sales_data = await execute_api_request(
            request_func=fetch_history,
            endpoint_type="last_sales",
            max_retries=2,
        )

        # Проверяем результаты запроса
        if "Error" in sales_data:
            await query.edit_message_text(
                f"❌ Ошибка при получении истории продаж: {sales_data['Error']}",
                parse_mode="Markdown",
            )
            return

        # Находим данные для нашего предмета
        item_sales = None
        for item in sales_data.get("LastSales", []):
            if item.get("MarketHashName") == item_name:
                item_sales = item
                break

        # Если данных по предмету нет
        if not item_sales or not item_sales.get("Sales"):
            await query.edit_message_text(
                f"⚠️ Не удалось найти историю продаж для предмета:\n`{item_name}`",
                parse_mode="Markdown",
            )
            return

        # Форматируем результаты
        formatted_message = (
            f"📊 История продаж: `{item_name}`\n\n"
            f"Последние {len(item_sales['Sales'])} продаж:\n\n"
        )

        for i, sale in enumerate(item_sales.get("Sales", [])[:20], 1):
            # Преобразуем timestamp в дату
            from datetime import datetime

            date_str = datetime.fromtimestamp(sale.get("Timestamp", 0)).strftime("%Y-%m-%d %H:%M")

            # Добавляем информацию о продаже
            price = float(sale.get("Price", 0))
            formatted_message += (
                f"{i}. {date_str}\n"
                f"   💰 Цена: ${price:.2f} {sale.get('Currency', 'USD')}\n"
                f"   🔖 Тип: {sale.get('OrderType', 'Unknown')}\n\n"
            )

        # Добавляем кнопки управления
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📊 Анализ продаж",
                        callback_data=f"refresh_sales:{item_name}",
                    ),
                    InlineKeyboardButton(
                        "💧 Анализ ликвидности",
                        callback_data=f"liquidity:{item_name}",
                    ),
                ],
            ]
        )

        # Отправляем результаты
        await query.edit_message_text(
            text=formatted_message,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    except APIError as e:
        # Обработка ошибок API
        logger.error(f"Ошибка API при получении истории продаж: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при получении истории продаж: {e.message}",
            parse_mode="Markdown",
        )
    except Exception as e:
        # Обработка прочих ошибок
        logger.exception(f"Ошибка при получении истории продаж: {e!s}")
        await query.edit_message_text(
            f"❌ Произошла ошибка: {e!s}",
            parse_mode="Markdown",
        )


async def handle_liquidity_callback(update: Update, context: CallbackContext) -> None:
    """Обрабатывает запрос на анализ ликвидности предмета."""
    query = update.callback_query
    await query.answer()

    # Извлекаем название предмета из callback_data
    # Формат: "liquidity:item_name"
    callback_data = query.data.split(":", 1)
    if len(callback_data) < 2:
        await query.edit_message_text(
            "❌ Ошибка: некорректные данные запроса.",
            parse_mode="Markdown",
        )
        return

    item_name = callback_data[1]
    game = "csgo"  # По умолчанию

    # Получаем игру из контекста, если доступна
    if hasattr(context, "user_data") and "current_game" in context.user_data:
        game = context.user_data["current_game"]

    # Отправляем сообщение о начале анализа
    await query.edit_message_text(
        f"🔍 Анализ ликвидности предмета:\n`{item_name}`\n\n" "⏳ Пожалуйста, подождите...",
        parse_mode="Markdown",
    )

    try:
        # Создаем функцию для запроса анализа ликвидности
        async def get_liquidity_analysis():
            return await analyze_item_liquidity(
                item_name=item_name,
                game=game,
            )

        # Выполняем запрос с использованием обработки ошибок API
        analysis = await execute_api_request(
            request_func=get_liquidity_analysis,
            endpoint_type="market",
            max_retries=2,
        )

        # Проверяем результаты анализа
        sales_analysis = analysis.get("sales_analysis", {})
        if not sales_analysis.get("has_data"):
            await query.edit_message_text(
                f"⚠️ Не удалось найти данные о продажах для предмета:\n`{item_name}`\n\n"
                "Возможно, предмет редко продается или название указано неверно.",
                parse_mode="Markdown",
            )
            return

        # Получаем эмодзи для категории ликвидности
        liquidity_emoji = get_liquidity_emoji(analysis.get("liquidity_category", "Низкая"))

        # Форматируем результаты анализа
        formatted_message = (
            f"💧 Анализ ликвидности: `{item_name}`\n\n"
            f"{liquidity_emoji} Категория: {analysis['liquidity_category']}\n"
            f"📊 Оценка: {analysis['liquidity_score']}/7\n\n"
            f"📈 Тренд цены: {get_trend_emoji(sales_analysis.get('price_trend', 'stable'))}\n"
            f"🔄 Продаж в день: {sales_analysis.get('sales_per_day', 0):.2f}\n"
            f"📆 Всего продаж: {sales_analysis.get('sales_volume', 0)}\n"
            f"💰 Средняя цена: ${sales_analysis.get('avg_price', 0):.2f}\n\n"
        )

        # Добавляем информацию о рынке
        market_data = analysis.get("market_data", {})
        formatted_message += (
            f"🛒 Предложений на рынке: {market_data.get('offers_count', 0)}\n"
            f"⬇️ Минимальная цена: ${market_data.get('lowest_price', 0):.2f}\n"
            f"⬆️ Максимальная цена: ${market_data.get('highest_price', 0):.2f}\n\n"
        )

        # Добавляем рекомендацию по арбитражу
        if analysis["liquidity_category"] in ["Очень высокая", "Высокая"]:
            formatted_message += "✅ *Рекомендация*: Отлично подходит для арбитража!\n"
        elif analysis["liquidity_category"] == "Средняя":
            formatted_message += (
                "⚠️ *Рекомендация*: Может подойти для арбитража, но с осторожностью.\n"
            )
        else:
            formatted_message += (
                "❌ *Рекомендация*: Не рекомендуется для арбитража из-за низкой ликвидности.\n"
            )

        # Добавляем кнопки управления
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📊 История продаж",
                        callback_data=f"sales_history:{item_name}",
                    ),
                    InlineKeyboardButton(
                        "🔍 Обновить анализ",
                        callback_data=f"refresh_liquidity:{item_name}",
                    ),
                ],
            ]
        )

        # Отправляем результаты анализа
        await query.edit_message_text(
            text=formatted_message,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    except APIError as e:
        # Обработка ошибок API
        logger.error(f"Ошибка API при анализе ликвидности: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при анализе ликвидности: {e.message}",
            parse_mode="Markdown",
        )
    except Exception as e:
        # Обработка прочих ошибок
        logger.exception(f"Ошибка при анализе ликвидности: {e!s}")
        await query.edit_message_text(
            f"❌ Произошла ошибка: {e!s}",
            parse_mode="Markdown",
        )


async def handle_refresh_sales_callback(update: Update, context: CallbackContext) -> None:
    """Обрабатывает запрос на обновление анализа продаж."""
    query = update.callback_query
    await query.answer()

    # Извлекаем название предмета из callback_data
    # Формат: "refresh_sales:item_name"
    callback_data = query.data.split(":", 1)
    if len(callback_data) < 2:
        await query.edit_message_text(
            "❌ Ошибка: некорректные данные запроса.",
            parse_mode="Markdown",
        )
        return

    item_name = callback_data[1]

    # Отправляем сообщение о начале анализа
    await query.edit_message_text(
        f"🔍 Обновление анализа продаж для:\n`{item_name}`\n\n" "⏳ Пожалуйста, подождите...",
        parse_mode="Markdown",
    )

    try:
        # Создаем функцию для запроса анализа продаж
        async def get_analysis():
            return await analyze_sales_history(
                item_name=item_name,
                days=14,  # Анализируем за 2 недели
            )

        # Выполняем запрос с использованием обработки ошибок API
        analysis = await execute_api_request(
            request_func=get_analysis,
            endpoint_type="last_sales",
            max_retries=2,
        )

        # Проверяем результаты анализа
        if not analysis.get("has_data"):
            await query.edit_message_text(
                f"⚠️ Не удалось найти данные о продажах для предмета:\n`{item_name}`\n\n"
                "Возможно, предмет редко продается или название указано неверно.",
                parse_mode="Markdown",
            )
            return

        # Форматируем результаты анализа
        formatted_message = (
            f"📊 Анализ продаж: `{item_name}`\n\n"
            f"💰 Средняя цена: ${analysis['avg_price']:.2f}\n"
            f"⬆️ Максимальная цена: ${analysis['max_price']:.2f}\n"
            f"⬇️ Минимальная цена: ${analysis['min_price']:.2f}\n"
            f"📈 Тренд цены: {get_trend_emoji(analysis['price_trend'])}\n"
            f"🔄 Продаж за период: {analysis['sales_volume']}\n"
            f"📆 Продаж в день: {analysis['sales_per_day']:.2f}\n"
            f"⏱️ Период анализа: {analysis['period_days']} дней\n\n"
        )

        # Добавляем информацию о последних продажах
        if analysis["recent_sales"]:
            formatted_message += "🕒 Последние продажи:\n"
            # Показываем до 5 последних продаж
            for sale in analysis["recent_sales"][:5]:
                formatted_message += f"• {sale['date']} - ${sale['price']:.2f} {sale['currency']}\n"

        # Добавляем кнопку для показа полной истории продаж
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📊 Подробная история",
                        callback_data=f"sales_history:{item_name}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "💧 Анализ ликвидности",
                        callback_data=f"liquidity:{item_name}",
                    ),
                ],
            ]
        )

        # Отправляем результаты анализа
        await query.edit_message_text(
            text=formatted_message,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    except APIError as e:
        # Обработка ошибок API
        logger.error(f"Ошибка API при обновлении анализа продаж: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при получении данных о продажах: {e.message}",
            parse_mode="Markdown",
        )
    except Exception as e:
        # Обработка прочих ошибок
        logger.exception(f"Ошибка при обновлении анализа продаж: {e!s}")
        await query.edit_message_text(
            f"❌ Произошла ошибка: {e!s}",
            parse_mode="Markdown",
        )


async def handle_refresh_liquidity_callback(update: Update, context: CallbackContext) -> None:
    """Обрабатывает запрос на обновление анализа ликвидности."""
    # Просто перенаправляем на основной обработчик анализа ликвидности
    # Так как логика полностью совпадает
    update.callback_query.data = update.callback_query.data.replace(
        "refresh_liquidity:", "liquidity:"
    )
    await handle_liquidity_callback(update, context)


async def handle_all_arbitrage_sales_callback(update: Update, context: CallbackContext) -> None:
    """Обрабатывает запрос на просмотр всех арбитражных возможностей с учетом продаж."""
    query = update.callback_query
    await query.answer()

    # Извлекаем игру из callback_data
    # Формат: "all_arbitrage_sales:game"
    callback_data = query.data.split(":", 1)
    if len(callback_data) < 2:
        await query.edit_message_text(
            "❌ Ошибка: некорректные данные запроса.",
            parse_mode="Markdown",
        )
        return

    game = callback_data[1]

    # Отправляем сообщение о начале запроса
    await query.edit_message_text(
        f"🔍 Получение всех арбитражных возможностей с учетом продаж для {game}...\n\n"
        "⏳ Пожалуйста, подождите...",
        parse_mode="Markdown",
    )

    try:
        # Создаем функцию для запроса арбитражных возможностей
        async def search_arbitrage():
            return await enhanced_arbitrage_search(
                game=game,
                max_items=20,  # Получаем больше предметов
                min_profit=1.0,
                min_profit_percent=5.0,
                min_sales_per_day=0.3,  # Минимум 1 продажа за 3 дня
                time_period_days=7,
            )

        # Выполняем запрос с использованием обработки ошибок API
        results = await execute_api_request(
            request_func=search_arbitrage,
            endpoint_type="market",
            max_retries=2,
        )

        # Проверяем результаты поиска
        opportunities = results.get("opportunities", [])
        if not opportunities:
            await query.edit_message_text(
                f"⚠️ Не найдено арбитражных возможностей с учетом истории продаж для {game}.\n\n"
                "Попробуйте изменить параметры фильтрации или выбрать другую игру.",
                parse_mode="Markdown",
            )
            return

        # Форматируем результаты поиска
        formatted_message = (
            f"📊 Все арбитражные возможности с учетом продаж для {game}\n\n"
            f"🔎 Найдено предметов: {len(opportunities)}\n"
            f"📆 Период анализа: {results['filters']['time_period_days']} дней\n\n"
        )

        # Добавляем информацию о найденных предметах
        for i, item in enumerate(opportunities, 1):
            sales_analysis = item.get("sales_analysis", {})

            formatted_message += (
                f"🏆 {i}. `{item['market_hash_name']}`\n"
                f"💰 Прибыль: ${item['profit']:.2f} ({item['profit_percent']:.1f}%)\n"
                f"🛒 Цена покупки: ${item['buy_price']:.2f}\n"
                f"💵 Цена продажи: ${item['sell_price']:.2f}\n"
                f"📈 Тренд: {get_trend_emoji(sales_analysis.get('price_trend', 'stable'))}\n"
                f"🔄 Продаж в день: {sales_analysis.get('sales_per_day', 0):.2f}\n\n"
            )

            # Если список слишком длинный, добавляем кнопку "Показать еще"
            if i == 10 and len(opportunities) > 10:
                formatted_message += (
                    f"_Показаны 10 из {len(opportunities)} найденных возможностей._\n\n"
                )
                break

        # Добавляем кнопки управления
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔍 Обновить",
                        callback_data=f"refresh_arbitrage_sales:{game}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "⚙️ Настроить фильтры",
                        callback_data=f"setup_sales_filters:{game}",
                    ),
                ],
            ]
        )

        # Отправляем результаты поиска
        await query.edit_message_text(
            text=formatted_message,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    except APIError as e:
        # Обработка ошибок API
        logger.error(f"Ошибка API при получении всех арбитражных возможностей: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при поиске арбитражных возможностей: {e.message}",
            parse_mode="Markdown",
        )
    except Exception as e:
        # Обработка прочих ошибок
        logger.exception(f"Ошибка при получении всех арбитражных возможностей: {e!s}")
        await query.edit_message_text(
            f"❌ Произошла ошибка: {e!s}",
            parse_mode="Markdown",
        )


async def handle_refresh_arbitrage_sales_callback(update: Update, context: CallbackContext) -> None:
    """Обрабатывает запрос на обновление арбитражных возможностей с учетом продаж."""
    query = update.callback_query
    await query.answer()

    # Извлекаем игру из callback_data
    # Формат: "refresh_arbitrage_sales:game"
    callback_data = query.data.split(":", 1)
    if len(callback_data) < 2:
        await query.edit_message_text(
            "❌ Ошибка: некорректные данные запроса.",
            parse_mode="Markdown",
        )
        return

    game = callback_data[1]

    # Обновляем текущую игру в контексте пользователя
    if hasattr(context, "user_data"):
        context.user_data["current_game"] = game

    # Имитируем сообщение для обработчика команды
    update.message = query.message
    await handle_arbitrage_with_sales(update, context)


async def handle_setup_sales_filters_callback(update: Update, context: CallbackContext) -> None:
    """Обрабатывает запрос на настройку фильтров арбитража с учетом продаж."""
    query = update.callback_query
    await query.answer()

    # Извлекаем игру из callback_data
    # Формат: "setup_sales_filters:game"
    callback_data = query.data.split(":", 1)
    if len(callback_data) < 2:
        game = "csgo"  # По умолчанию
    else:
        game = callback_data[1]

    # Обновляем текущую игру в контексте пользователя
    if hasattr(context, "user_data"):
        context.user_data["current_game"] = game

    # Получаем текущие настройки фильтров из контекста пользователя или используем значения по умолчанию
    user_data = getattr(context, "user_data", {})
    filters = user_data.get("sales_filters", {})

    min_profit = filters.get("min_profit", 1.0)
    min_profit_percent = filters.get("min_profit_percent", 5.0)
    min_sales_per_day = filters.get("min_sales_per_day", 0.3)
    price_trend = filters.get("price_trend", "all")

    # Формируем текстовое сообщение с настройками фильтров
    formatted_message = (
        f"⚙️ Настройка фильтров арбитража с учетом продаж для {game}\n\n"
        f"📊 Текущие настройки:\n"
        f"• Минимальная прибыль: ${min_profit:.2f}\n"
        f"• Минимальный процент прибыли: {min_profit_percent:.1f}%\n"
        f"• Минимум продаж в день: {min_sales_per_day:.1f}\n"
        f"• Фильтр по тренду цены: {price_trend_to_text(price_trend)}\n\n"
        "Выберите параметр для изменения:"
    )

    # Создаем клавиатуру для настройки фильтров
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💰 Мин. прибыль",
                    callback_data=f"filter_sales:profit:{game}",
                ),
                InlineKeyboardButton(
                    "📈 Мин. процент",
                    callback_data=f"filter_sales:percent:{game}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔄 Мин. продаж/день",
                    callback_data=f"filter_sales:sales:{game}",
                ),
                InlineKeyboardButton(
                    "📊 Фильтр по тренду",
                    callback_data=f"filter_sales:trend:{game}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "✅ Сохранить и применить",
                    callback_data=f"apply_sales_filters:{game}",
                ),
            ],
        ]
    )

    # Отправляем сообщение с настройками
    await query.edit_message_text(
        text=formatted_message,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def handle_all_volume_stats_callback(update: Update, context: CallbackContext) -> None:
    """Обрабатывает запрос на просмотр всей статистики объема продаж."""
    query = update.callback_query
    await query.answer()

    # Извлекаем игру из callback_data
    # Формат: "all_volume_stats:game"
    callback_data = query.data.split(":", 1)
    if len(callback_data) < 2:
        await query.edit_message_text(
            "❌ Ошибка: некорректные данные запроса.",
            parse_mode="Markdown",
        )
        return

    game = callback_data[1]

    # Отправляем сообщение о начале запроса
    await query.edit_message_text(
        f"🔍 Получение подробной статистики объема продаж для {game}...\n\n"
        "⏳ Пожалуйста, подождите...",
        parse_mode="Markdown",
    )

    try:
        # Создаем функцию для запроса статистики объема продаж
        async def get_volume_stats():
            return await get_sales_volume_stats(
                game=game,
                top_items=30,  # Анализируем 30 популярных предметов
            )

        # Выполняем запрос с использованием обработки ошибок API
        stats = await execute_api_request(
            request_func=get_volume_stats,
            endpoint_type="market",
            max_retries=2,
        )

        # Проверяем результаты запроса
        items = stats.get("items", [])
        if not items:
            await query.edit_message_text(
                f"⚠️ Не удалось получить статистику объема продаж для {game}.",
                parse_mode="Markdown",
            )
            return

        # Форматируем результаты
        formatted_message = (
            f"📊 Полная статистика объема продаж для {game}\n\n"
            f"🔎 Проанализировано предметов: {stats['count']}\n"
            f"⬆️ Предметов с растущей ценой: {stats['summary']['up_trend_count']}\n"
            f"⬇️ Предметов с падающей ценой: {stats['summary']['down_trend_count']}\n"
            f"➡️ Предметов со стабильной ценой: {stats['summary']['stable_trend_count']}\n\n"
            f"📈 Все предметы по объему продаж:\n\n"
        )

        # Добавляем информацию о всех предметах
        for i, item in enumerate(items, 1):
            formatted_message += (
                f"{i}. `{item['item_name']}`\n"
                f"   🔄 Продаж в день: {item['sales_per_day']:.2f}\n"
                f"   💰 Средняя цена: ${item['avg_price']:.2f}\n"
                f"   📈 Тренд: {get_trend_emoji(item['price_trend'])}\n\n"
            )

            # Если список слишком длинный, добавляем кнопку "Показать еще"
            if i == 15 and len(items) > 15:
                formatted_message += f"_Показаны 15 из {len(items)} предметов._\n\n"
                break

        # Добавляем кнопки управления
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔍 Обновить",
                        callback_data=f"refresh_volume_stats:{game}",
                    ),
                ],
            ]
        )

        # Отправляем результаты
        await query.edit_message_text(
            text=formatted_message,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    except APIError as e:
        # Обработка ошибок API
        logger.error(f"Ошибка API при получении подробной статистики объема продаж: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при получении статистики: {e.message}",
            parse_mode="Markdown",
        )
    except Exception as e:
        # Обработка прочих ошибок
        logger.exception(f"Ошибка при получении подробной статистики объема продаж: {e!s}")
        await query.edit_message_text(
            f"❌ Произошла ошибка: {e!s}",
            parse_mode="Markdown",
        )


async def handle_refresh_volume_stats_callback(update: Update, context: CallbackContext) -> None:
    """Обрабатывает запрос на обновление статистики объема продаж."""
    query = update.callback_query
    await query.answer()

    # Извлекаем игру из callback_data
    # Формат: "refresh_volume_stats:game"
    callback_data = query.data.split(":", 1)
    if len(callback_data) < 2:
        await query.edit_message_text(
            "❌ Ошибка: некорректные данные запроса.",
            parse_mode="Markdown",
        )
        return

    game = callback_data[1]

    # Обновляем текущую игру в контексте пользователя
    if hasattr(context, "user_data"):
        context.user_data["current_game"] = game

    # Имитируем сообщение для обработчика команды
    update.message = query.message
    await handle_sales_volume_stats(update, context)


# Вспомогательные функции


def price_trend_to_text(trend: str) -> str:
    """Преобразует код тренда цены в человекочитаемый текст."""
    if trend == "up":
        return "⬆️ Растущая цена"
    if trend == "down":
        return "⬇️ Падающая цена"
    if trend == "stable":
        return "➡️ Стабильная цена"
    return "🔄 Любой тренд"
