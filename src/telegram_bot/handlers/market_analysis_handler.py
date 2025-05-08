"""
Обработчики команд для анализа рынка и отслеживания тенденций.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from src.dmarket.arbitrage import GAMES
from src.dmarket.dmarket_api_fixed import DMarketAPI
from src.dmarket.market_analysis import (
    analyze_price_changes,
    find_trending_items,
    analyze_market_volatility,
    generate_market_report
)
# Импортируем новые функции из улучшенного анализатора цен
from src.utils.price_analyzer import (
    find_undervalued_items,
    get_investment_recommendations,
    calculate_price_trend,
    analyze_supply_demand
)
from src.telegram_bot.keyboards import get_back_to_arbitrage_keyboard
from src.telegram_bot.pagination import pagination_manager

# Настройка логирования
logger = logging.getLogger(__name__)


async def market_analysis_command(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает команду /market_analysis для начала анализа рынка.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    # Создаем клавиатуру с опциями анализа
    keyboard = [
        [
            InlineKeyboardButton("📈 Изменения цен", callback_data="analysis:price_changes:csgo"),
            InlineKeyboardButton("🔥 Трендовые предметы", callback_data="analysis:trending:csgo")
        ],
        [
            InlineKeyboardButton("📊 Волатильность", callback_data="analysis:volatility:csgo"),
            InlineKeyboardButton("📑 Полный отчет", callback_data="analysis:report:csgo")
        ],
        [
            InlineKeyboardButton("💰 Недооцененные предметы", callback_data="analysis:undervalued:csgo"),
            InlineKeyboardButton("📊 Рекомендации", callback_data="analysis:recommendations:csgo")
        ],
        [
            InlineKeyboardButton("⬅️ Назад к арбитражу", callback_data="arbitrage")
        ]
    ]
    
    # Добавляем выбор игры
    game_row = []
    for game_code, game_name in GAMES.items():
        game_row.append(
            InlineKeyboardButton(
                game_name, 
                callback_data=f"analysis:select_game:{game_code}"
            )
        )
        
        # Создаем новую строку после каждой второй игры
        if len(game_row) == 2:
            keyboard.insert(-2, game_row)
            game_row = []
    
    # Добавляем оставшиеся игры, если есть
    if game_row:
        keyboard.insert(-2, game_row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔎 *Анализ рынка DMarket*\n\n"
        "Выберите тип анализа и игру для исследования тенденций рынка "
        "и поиска выгодных возможностей.\n\n"
        "Текущая игра: *CS2*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def market_analysis_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает колбэки для анализа рынка.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Разбираем данные колбэка
    parts = query.data.split(":")
    
    if len(parts) < 2:
        return
    
    action = parts[1]
    game = parts[2] if len(parts) > 2 else "csgo"
    
    # Инициализируем данные пользователя, если их нет
    if not context.user_data.get("market_analysis"):
        context.user_data["market_analysis"] = {
            "current_game": "csgo",
            "period": "24h",
            "min_price": 1.0,
            "max_price": 500.0
        }
    
    # Обновляем текущую игру
    if action == "select_game":
        context.user_data["market_analysis"]["current_game"] = game
        
        # Обновляем сообщение с новой выбранной игрой
        keyboard = [
            [
                InlineKeyboardButton("📈 Изменения цен", callback_data=f"analysis:price_changes:{game}"),
                InlineKeyboardButton("🔥 Трендовые предметы", callback_data=f"analysis:trending:{game}")
            ],
            [
                InlineKeyboardButton("📊 Волатильность", callback_data=f"analysis:volatility:{game}"),
                InlineKeyboardButton("📑 Полный отчет", callback_data=f"analysis:report:{game}")
            ],
            [
                InlineKeyboardButton("💰 Недооцененные предметы", callback_data=f"analysis:undervalued:{game}"),
                InlineKeyboardButton("📊 Рекомендации", callback_data=f"analysis:recommendations:{game}")
            ]
        ]
        
        # Добавляем выбор игры
        game_row = []
        for game_code, game_name in GAMES.items():
            # Отмечаем выбранную игру
            button_text = f"✅ {game_name}" if game_code == game else game_name
            
            game_row.append(
                InlineKeyboardButton(
                    button_text, 
                    callback_data=f"analysis:select_game:{game_code}"
                )
            )
            
            # Создаем новую строку после каждой второй игры
            if len(game_row) == 2:
                keyboard.append(game_row)
                game_row = []
        
        # Добавляем оставшиеся игры, если есть
        if game_row:
            keyboard.append(game_row)
            
        # Добавляем кнопку возврата
        keyboard.append([
            InlineKeyboardButton("⬅️ Назад к арбитражу", callback_data="arbitrage")
        ])
        
        game_name = GAMES.get(game, game)
        
        await query.edit_message_text(
            f"🔎 *Анализ рынка DMarket*\n\n"
            f"Выберите тип анализа и игру для исследования тенденций рынка "
            f"и поиска выгодных возможностей.\n\n"
            f"Текущая игра: *{game_name}*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return
    
    # Получаем текущие настройки пользователя
    user_settings = context.user_data["market_analysis"]
    current_game = user_settings.get("current_game", game)
    
    # Показываем сообщение о загрузке
    await query.edit_message_text(
        f"⏳ Загрузка данных анализа рынка для {GAMES.get(current_game, current_game)}...",
        parse_mode='Markdown'
    )
    
    # Создаем API клиент
    try:
        from os import environ
        api_client = DMarketAPI(
            environ.get("DMARKET_PUBLIC_KEY", ""),
            environ.get("DMARKET_SECRET_KEY", ""),
            environ.get("DMARKET_API_URL", "https://api.dmarket.com"),
        )
        
        # Выполняем запрошенный анализ
        if action == "price_changes":
            # Анализ изменений цен
            results = await analyze_price_changes(
                game=current_game,
                period=user_settings.get("period", "24h"),
                min_price=user_settings.get("min_price", 1.0),
                max_price=user_settings.get("max_price", 500.0),
                dmarket_api=api_client,
                limit=20
            )
            
            # Сохраняем результаты для пагинации
            pagination_manager.set_items(user_id, results, "price_changes")
            
            # Отображаем результаты
            await show_price_changes_results(query, context, current_game)
            
        elif action == "trending":
            # Поиск трендовых предметов
            results = await find_trending_items(
                game=current_game,
                min_price=user_settings.get("min_price", 1.0),
                max_price=user_settings.get("max_price", 500.0),
                dmarket_api=api_client,
                limit=20
            )
            
            # Сохраняем результаты для пагинации
            pagination_manager.set_items(user_id, results, "trending")
            
            # Отображаем результаты
            await show_trending_items_results(query, context, current_game)
            
        elif action == "volatility":
            # Анализ волатильности
            results = await analyze_market_volatility(
                game=current_game,
                min_price=user_settings.get("min_price", 1.0),
                max_price=user_settings.get("max_price", 500.0),
                dmarket_api=api_client,
                limit=20
            )
            
            # Сохраняем результаты для пагинации
            pagination_manager.set_items(user_id, results, "volatility")
            
            # Отображаем результаты
            await show_volatility_results(query, context, current_game)
            
        elif action == "report":
            # Полный отчет о рынке
            report = await generate_market_report(
                game=current_game,
                dmarket_api=api_client
            )
            
            # Отображаем отчет
            await show_market_report(query, context, report)
            
        elif action == "undervalued":
            # Поиск недооцененных предметов с помощью нового модуля price_analyzer
            results = await find_undervalued_items(
                api_client,
                game=current_game,
                price_from=user_settings.get("min_price", 1.0),
                price_to=user_settings.get("max_price", 500.0),
                discount_threshold=15.0,  # Минимальный процент скидки
                max_results=20
            )
            
            # Сохраняем результаты для пагинации
            pagination_manager.set_items(user_id, results, "undervalued")
            
            # Отображаем результаты
            await show_undervalued_items_results(query, context, current_game)
            
        elif action == "recommendations":
            # Получаем инвестиционные рекомендации с помощью нового модуля price_analyzer
            results = await get_investment_recommendations(
                api_client,
                game=current_game,
                budget=user_settings.get("max_price", 100.0),
                risk_level="medium"  # Средний уровень риска по умолчанию
            )
            
            # Сохраняем результаты для пагинации
            pagination_manager.set_items(user_id, results, "recommendations")
            
            # Отображаем результаты
            await show_investment_recommendations_results(query, context, current_game)
            
    except Exception as e:
        logger.error(f"Ошибка при анализе рынка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Отображаем сообщение об ошибке
        await query.edit_message_text(
            f"❌ Произошла ошибка при анализе рынка:\n\n{str(e)}",
            reply_markup=get_back_to_market_analysis_keyboard(current_game)
        )
    finally:
        # Закрываем клиент API
        if 'api_client' in locals() and hasattr(api_client, '_close_client'):
            try:
                await api_client._close_client()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии клиента API: {e}")


async def handle_pagination_analysis(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает пагинацию для результатов анализа рынка.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Разбираем данные колбэка
    parts = query.data.split(":")
    
    if len(parts) < 3:
        return
    
    direction = parts[1]  # next или prev
    mode = parts[2]  # price_changes, trending, volatility, undervalued, recommendations
    game = parts[3] if len(parts) > 3 else context.user_data.get("market_analysis", {}).get("current_game", "csgo")
    
    # Переходим на следующую/предыдущую страницу
    if direction == "next":
        pagination_manager.next_page(user_id)
    else:
        pagination_manager.prev_page(user_id)
    
    # Отображаем обновленные результаты в зависимости от режима
    if mode == "price_changes":
        await show_price_changes_results(query, context, game)
    elif mode == "trending":
        await show_trending_items_results(query, context, game)
    elif mode == "volatility":
        await show_volatility_results(query, context, game)
    elif mode == "undervalued":
        await show_undervalued_items_results(query, context, game)
    elif mode == "recommendations":
        await show_investment_recommendations_results(query, context, game)


async def show_price_changes_results(query, context, game: str) -> None:
    """
    Отображает результаты анализа изменений цен.
    
    Args:
        query: Объект запроса колбэка
        context: Контекст бота
        game: Код игры
    """
    user_id = query.from_user.id
    
    # Получаем данные из пагинации
    items, current_page, total_pages = pagination_manager.get_page(user_id)
    
    if not items:
        await query.edit_message_text(
            f"ℹ️ Нет данных об изменениях цен для {GAMES.get(game, game)}",
            reply_markup=get_back_to_market_analysis_keyboard(game)
        )
        return
    
    # Форматируем результаты
    period = context.user_data.get("market_analysis", {}).get("period", "24h")
    period_display = {
        "1h": "1 час",
        "3h": "3 часа",
        "6h": "6 часов",
        "12h": "12 часов",
        "24h": "24 часа",
        "7d": "7 дней",
        "30d": "30 дней"
    }.get(period, "24 часа")
    
    text = f"📈 *Изменения цен на {GAMES.get(game, game)}*\n" \
           f"За период: {period_display}\n\n"
    
    # Добавляем информацию о предметах
    for item in items:
        name = item.get("market_hash_name", "Неизвестный предмет")
        current_price = item.get("current_price", 0)
        old_price = item.get("old_price", 0)
        change_amount = item.get("change_amount", 0)
        change_percent = item.get("change_percent", 0)
        
        # Определяем иконку в зависимости от направления изменения
        icon = "🔼" if change_percent > 0 else "🔽"
        
        # Форматируем текст предмета
        item_text = f"{icon} *{name}*\n" \
                    f"   Цена: ${current_price:.2f} (было ${old_price:.2f})\n" \
                    f"   Изменение: ${change_amount:.2f} ({change_percent:.1f}%)\n\n"
        
        text += item_text
    
    # Добавляем информацию о странице
    text += f"Страница {current_page + 1} из {total_pages}"
    
    # Создаем клавиатуру с пагинацией
    keyboard = []
    
    # Кнопки пагинации
    pagination_row = []
    if current_page > 0:
        pagination_row.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"analysis_page:prev:price_changes:{game}")
        )
    
    if current_page < total_pages - 1:
        pagination_row.append(
            InlineKeyboardButton("➡️ Вперед", callback_data=f"analysis_page:next:price_changes:{game}")
        )
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Кнопки выбора периода
    period_row = []
    for p_code, p_name in [("24h", "24ч"), ("7d", "7д"), ("30d", "30д")]:
        period_text = f"✅ {p_name}" if p_code == period else p_name
        period_row.append(
            InlineKeyboardButton(period_text, callback_data=f"analysis_period:{p_code}:{game}")
        )
    
    keyboard.append(period_row)
    
    # Кнопка возврата к анализу
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад к анализу", callback_data=f"analysis:select_game:{game}")
    ])
    
    # Отображаем результаты
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def show_trending_items_results(query, context, game: str) -> None:
    """
    Отображает результаты анализа трендовых предметов.
    
    Args:
        query: Объект запроса колбэка
        context: Контекст бота
        game: Код игры
    """
    user_id = query.from_user.id
    
    # Получаем данные из пагинации
    items, current_page, total_pages = pagination_manager.get_page(user_id)
    
    if not items:
        await query.edit_message_text(
            f"ℹ️ Нет данных о трендовых предметах для {GAMES.get(game, game)}",
            reply_markup=get_back_to_market_analysis_keyboard(game)
        )
        return
    
    # Форматируем результаты
    text = f"🔥 *Трендовые предметы на {GAMES.get(game, game)}*\n\n"
    
    # Добавляем информацию о предметах
    for i, item in enumerate(items, 1):
        name = item.get("market_hash_name", "Неизвестный предмет")
        price = item.get("price", 0)
        sales_volume = item.get("sales_volume", 0)
        offers_count = item.get("offers_count", 0)
        popularity_score = item.get("popularity_score", 0)
        
        # Определяем уровень популярности
        if popularity_score > 100:
            popularity_level = "Очень высокая"
        elif popularity_score > 50:
            popularity_level = "Высокая"
        elif popularity_score > 20:
            popularity_level = "Средняя"
        else:
            popularity_level = "Низкая"
        
        # Форматируем текст предмета
        item_text = f"{i}. *{name}*\n" \
                    f"   💰 Цена: ${price:.2f}\n" \
                    f"   📊 Объем продаж: {sales_volume}\n" \
                    f"   🔄 Предложений: {offers_count}\n" \
                    f"   ⭐ Популярность: {popularity_level}\n\n"
        
        text += item_text
    
    # Добавляем информацию о странице
    text += f"Страница {current_page + 1} из {total_pages}"
    
    # Создаем клавиатуру с пагинацией
    keyboard = []
    
    # Кнопки пагинации
    pagination_row = []
    if current_page > 0:
        pagination_row.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"analysis_page:prev:trending:{game}")
        )
    
    if current_page < total_pages - 1:
        pagination_row.append(
            InlineKeyboardButton("➡️ Вперед", callback_data=f"analysis_page:next:trending:{game}")
        )
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Кнопка возврата к анализу
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад к анализу", callback_data=f"analysis:select_game:{game}")
    ])
    
    # Отображаем результаты
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def show_volatility_results(query, context, game: str) -> None:
    """
    Отображает результаты анализа волатильности рынка.
    
    Args:
        query: Объект запроса колбэка
        context: Контекст бота
        game: Код игры
    """
    user_id = query.from_user.id
    
    # Получаем данные из пагинации
    items, current_page, total_pages = pagination_manager.get_page(user_id)
    
    if not items:
        await query.edit_message_text(
            f"ℹ️ Нет данных о волатильности для {GAMES.get(game, game)}",
            reply_markup=get_back_to_market_analysis_keyboard(game)
        )
        return
    
    # Форматируем результаты
    text = f"📊 *Анализ волатильности {GAMES.get(game, game)}*\n\n"
    
    # Добавляем информацию о предметах
    for i, item in enumerate(items, 1):
        name = item.get("market_hash_name", "Неизвестный предмет")
        current_price = item.get("current_price", 0)
        change_24h = item.get("change_24h_percent", 0)
        change_7d = item.get("change_7d_percent", 0)
        volatility_score = item.get("volatility_score", 0)
        
        # Определяем уровень волатильности
        if volatility_score > 30:
            volatility_level = "Очень высокая"
        elif volatility_score > 20:
            volatility_level = "Высокая"
        elif volatility_score > 10:
            volatility_level = "Средняя"
        else:
            volatility_level = "Низкая"
        
        # Форматируем текст предмета
        item_text = f"{i}. *{name}*\n" \
                    f"   💰 Цена: ${current_price:.2f}\n" \
                    f"   📈 Изменение (24ч): {change_24h:.1f}%\n" \
                    f"   📈 Изменение (7д): {change_7d:.1f}%\n" \
                    f"   🔄 Волатильность: {volatility_level} ({volatility_score:.1f})\n\n"
        
        text += item_text
    
    # Добавляем информацию о странице
    text += f"Страница {current_page + 1} из {total_pages}"
    
    # Создаем клавиатуру с пагинацией
    keyboard = []
    
    # Кнопки пагинации
    pagination_row = []
    if current_page > 0:
        pagination_row.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"analysis_page:prev:volatility:{game}")
        )
    
    if current_page < total_pages - 1:
        pagination_row.append(
            InlineKeyboardButton("➡️ Вперед", callback_data=f"analysis_page:next:volatility:{game}")
        )
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Кнопка возврата к анализу
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад к анализу", callback_data=f"analysis:select_game:{game}")
    ])
    
    # Отображаем результаты
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def show_market_report(query, context, report: Dict[str, Any]) -> None:
    """
    Отображает полный отчет о состоянии рынка.
    
    Args:
        query: Объект запроса колбэка
        context: Контекст бота
        report: Словарь с данными отчета
    """
    game = report.get("game", "csgo")
    game_name = GAMES.get(game, game)
    
    # Проверяем наличие ошибки
    if "error" in report:
        await query.edit_message_text(
            f"❌ Произошла ошибка при создании отчета:\n\n{report['error']}",
            reply_markup=get_back_to_market_analysis_keyboard(game)
        )
        return
    
    # Форматируем отчет
    market_summary = report.get("market_summary", {})
    
    # Определяем общее направление рынка
    market_direction = market_summary.get("price_change_direction", "stable")
    direction_icon = {
        "up": "🔼 Растущий",
        "down": "🔽 Падающий",
        "stable": "➡️ Стабильный"
    }.get(market_direction, "➡️ Стабильный")
    
    # Определяем волатильность рынка
    volatility_level = market_summary.get("market_volatility_level", "low")
    volatility_display = {
        "low": "Низкая",
        "medium": "Средняя",
        "high": "Высокая"
    }.get(volatility_level, "Низкая")
    
    # Получаем популярные категории
    trending_categories = market_summary.get("top_trending_categories", ["Нет данных"])
    
    # Получаем рекомендации
    recommendations = market_summary.get("recommended_actions", ["Нет рекомендаций"])
    
    # Форматируем текст отчета
    text = f"📑 *Отчет о состоянии рынка {game_name}*\n\n" \
           f"*Общее направление рынка:* {direction_icon}\n" \
           f"*Волатильность:* {volatility_display}\n" \
           f"*Популярные категории:* {', '.join(trending_categories)}\n\n" \
           f"*Рекомендации:*\n"
    
    # Добавляем рекомендации
    for i, rec in enumerate(recommendations, 1):
        text += f"{i}. {rec}\n"
    
    # Добавляем краткую статистику по изменениям цен
    price_changes = report.get("price_changes", [])
    if price_changes:
        text += f"\n*Топ изменения цен:*\n"
        for i, item in enumerate(price_changes[:3], 1):
            name = item.get("market_hash_name", "")
            change_percent = item.get("change_percent", 0)
            direction = "🔼" if change_percent > 0 else "🔽"
            text += f"{i}. {name}: {direction} {abs(change_percent):.1f}%\n"
    
    # Добавляем краткую статистику по трендовым предметам
    trending_items = report.get("trending_items", [])
    if trending_items:
        text += f"\n*Топ трендовые предметы:*\n"
        for i, item in enumerate(trending_items[:3], 1):
            name = item.get("market_hash_name", "")
            sales = item.get("sales_volume", 0)
            text += f"{i}. {name}: {sales} продаж\n"
    
    # Создаем клавиатуру
    keyboard = [
        [
            InlineKeyboardButton("📈 Подробные изменения цен", callback_data=f"analysis:price_changes:{game}")
        ],
        [
            InlineKeyboardButton("🔥 Все трендовые предметы", callback_data=f"analysis:trending:{game}")
        ],
        [
            InlineKeyboardButton("⬅️ Назад к анализу", callback_data=f"analysis:select_game:{game}")
        ]
    ]
    
    # Отображаем отчет
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_period_change(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает изменение периода анализа.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Разбираем данные колбэка
    parts = query.data.split(":")
    
    if len(parts) < 2:
        return
    
    period = parts[1]
    game = parts[2] if len(parts) > 2 else "csgo"
    
    # Обновляем период в настройках пользователя
    if not context.user_data.get("market_analysis"):
        context.user_data["market_analysis"] = {}
    
    context.user_data["market_analysis"]["period"] = period
    
    # Запускаем новый анализ с обновленным периодом
    await query.answer("Период анализа обновлен")
    
    # Симулируем нажатие на кнопку анализа изменений цен
    query.data = f"analysis:price_changes:{game}"
    await market_analysis_callback(update, context)


def get_back_to_market_analysis_keyboard(game: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для возврата к анализу рынка.
    
    Args:
        game: Код игры
        
    Returns:
        Клавиатура с кнопкой возврата
    """
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Назад к анализу рынка", callback_data=f"analysis:select_game:{game}")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def register_market_analysis_handlers(dispatcher):
    """
    Регистрирует обработчики для анализа рынка.
    
    Args:
        dispatcher: Диспетчер для регистрации обработчиков
    """
    dispatcher.add_handler(CommandHandler("market_analysis", market_analysis_command))
    dispatcher.add_handler(CallbackQueryHandler(market_analysis_callback, pattern="^analysis:"))
    dispatcher.add_handler(CallbackQueryHandler(handle_pagination_analysis, pattern="^analysis_page:"))
    dispatcher.add_handler(CallbackQueryHandler(handle_period_change, pattern="^analysis_period:"))
    # Добавляем обработчик для изменения уровня риска
    dispatcher.add_handler(CallbackQueryHandler(handle_risk_level_change, pattern="^analysis_risk:"))


async def show_undervalued_items_results(query, context, game: str) -> None:
    """
    Отображает результаты поиска недооцененных предметов.
    
    Args:
        query: Объект запроса колбэка
        context: Контекст бота
        game: Код игры
    """
    user_id = query.from_user.id
    
    # Получаем данные из пагинации
    items, current_page, total_pages = pagination_manager.get_page(user_id)
    
    if not items:
        await query.edit_message_text(
            f"ℹ️ Не найдено недооцененных предметов для {GAMES.get(game, game)}",
            reply_markup=get_back_to_market_analysis_keyboard(game)
        )
        return
    
    # Форматируем результаты
    text = f"💰 *Недооцененные предметы на {GAMES.get(game, game)}*\n\n"
    
    # Добавляем информацию о предметах
    for i, item in enumerate(items, 1):
        name = item.get("title", "Неизвестный предмет")
        current_price = item.get("current_price", 0)
        avg_price = item.get("avg_price", 0)
        discount = item.get("discount", 0)
        trend = item.get("trend", "stable")
        volume = item.get("volume", 0)
        
        # Определяем иконку тренда
        trend_icon = "➡️"
        if trend == "upward":
            trend_icon = "🔼"
        elif trend == "downward":
            trend_icon = "🔽"
        
        # Форматируем текст предмета
        item_text = f"{i}. *{name}*\n" \
                    f"   💰 Цена: ${current_price:.2f} (средняя: ${avg_price:.2f})\n" \
                    f"   🔖 Скидка: {discount:.1f}%\n" \
                    f"   {trend_icon} Тренд: {trend}\n" \
                    f"   📊 Объем продаж: {volume}\n\n"
        
        text += item_text
    
    # Добавляем информацию о странице
    text += f"Страница {current_page + 1} из {total_pages}"
    
    # Создаем клавиатуру с пагинацией
    keyboard = []
    
    # Кнопки пагинации
    pagination_row = []
    if current_page > 0:
        pagination_row.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"analysis_page:prev:undervalued:{game}")
        )
    
    if current_page < total_pages - 1:
        pagination_row.append(
            InlineKeyboardButton("➡️ Вперед", callback_data=f"analysis_page:next:undervalued:{game}")
        )
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Кнопка возврата к анализу
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад к анализу", callback_data=f"analysis:select_game:{game}")
    ])
    
    # Отображаем результаты
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def show_investment_recommendations_results(query, context, game: str) -> None:
    """
    Отображает результаты инвестиционных рекомендаций.
    
    Args:
        query: Объект запроса колбэка
        context: Контекст бота
        game: Код игры
    """
    user_id = query.from_user.id
    
    # Получаем данные из пагинации
    items, current_page, total_pages = pagination_manager.get_page(user_id)
    
    if not items:
        await query.edit_message_text(
            f"ℹ️ Не удалось сформировать инвестиционные рекомендации для {GAMES.get(game, game)}",
            reply_markup=get_back_to_market_analysis_keyboard(game)
        )
        return
    
    # Форматируем результаты
    text = f"💼 *Инвестиционные рекомендации для {GAMES.get(game, game)}*\n\n"
    
    # Добавляем информацию о рекомендациях
    for i, item in enumerate(items, 1):
        name = item.get("title", "Неизвестный предмет")
        current_price = item.get("current_price", 0)
        discount = item.get("discount", 0)
        liquidity = item.get("liquidity", "low")
        investment_score = item.get("investment_score", 0)
        reason = item.get("reason", "Нет информации")
        
        # Определяем иконку ликвидности
        liquidity_icon = "🟡"  # Средняя ликвидность
        if liquidity == "high":
            liquidity_icon = "🟢"  # Высокая ликвидность
        elif liquidity == "low":
            liquidity_icon = "🔴"  # Низкая ликвидность
        
        # Форматируем текст рекомендации
        item_text = f"{i}. *{name}*\n" \
                    f"   💰 Цена: ${current_price:.2f}\n" \
                    f"   🔖 Скидка: {discount:.1f}%\n" \
                    f"   {liquidity_icon} Ликвидность: {liquidity}\n" \
                    f"   ⭐ Оценка: {investment_score:.1f}\n" \
                    f"   📝 Почему: {reason}\n\n"
        
        text += item_text
    
    # Добавляем информацию о странице
    text += f"Страница {current_page + 1} из {total_pages}"
    
    # Создаем клавиатуру с пагинацией
    keyboard = []
    
    # Кнопки пагинации
    pagination_row = []
    if current_page > 0:
        pagination_row.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"analysis_page:prev:recommendations:{game}")
        )
    
    if current_page < total_pages - 1:
        pagination_row.append(
            InlineKeyboardButton("➡️ Вперед", callback_data=f"analysis_page:next:recommendations:{game}")
        )
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Добавляем кнопки для выбора уровня риска
    risk_row = []
    for risk, label in [("low", "🔵 Низкий"), ("medium", "🟡 Средний"), ("high", "🔴 Высокий")]:
        risk_row.append(
            InlineKeyboardButton(label, callback_data=f"analysis_risk:{risk}:{game}")
        )
    
    keyboard.append(risk_row)
    
    # Кнопка возврата к анализу
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад к анализу", callback_data=f"analysis:select_game:{game}")
    ])
    
    # Отображаем результаты
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_risk_level_change(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает изменение уровня риска для инвестиционных рекомендаций.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Разбираем данные колбэка
    parts = query.data.split(":")
    
    if len(parts) < 3:
        return
    
    risk_level = parts[1]  # low, medium, high
    game = parts[2]
    
    # Обновляем уровень риска в настройках пользователя
    if not context.user_data.get("market_analysis"):
        context.user_data["market_analysis"] = {}
    
    context.user_data["market_analysis"]["risk_level"] = risk_level
    
    # Запускаем новый анализ с обновленным уровнем риска
    await query.answer(f"Уровень риска обновлен: {risk_level}")
    
    # Симулируем нажатие на кнопку рекомендаций
    query.data = f"analysis:recommendations:{game}"
    await market_analysis_callback(update, context) 