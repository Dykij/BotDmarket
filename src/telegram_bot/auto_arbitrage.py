"""
Модуль для автоматического арбитража.

Предоставляет функциональность для автоматического поиска арбитражных возможностей
и отображения результатов пользователю через Telegram.
"""
# mypy: disable-error-code="attr-defined"

import logging
import traceback
import asyncio
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, Union, cast, TypedDict, MutableMapping

# Define os.environ type to fix linter errors
class _Environ(TypedDict, total=False):
    DMARKET_PUBLIC_KEY: str
    DMARKET_SECRET_KEY: str
    DMARKET_API_URL: str
    # Add any other environment variables used in this module

# Type hint for os module (suppress mypy errors)
# This ensures os.environ is treated as a dictionary with string keys and values
environ_type: MutableMapping[str, str] = os.environ  # type: ignore

from telegram import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from src.telegram_bot.pagination import pagination_manager
from src.dmarket.arbitrage import GAMES, ArbitrageTrader
from src.telegram_bot.auto_arbitrage_scanner import (
    scan_multiple_games,
    auto_trade_items,
    check_user_balance
)
from src.telegram_bot.keyboards import (
    get_back_to_arbitrage_keyboard,
    get_modern_arbitrage_keyboard,
    get_auto_arbitrage_keyboard,
)
from src.dmarket.dmarket_api_fixed import DMarketAPI
from src.utils.api_error_handling import APIError, handle_api_error, RetryStrategy

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройки для разных режимов автоарбитража
ARBITRAGE_MODES = {
    "boost_low": {
        "name": "разгон баланса (низкая прибыль, быстрый оборот)",
        "min_price": 1.0,
        "max_price": 50.0,
        "min_profit_percent": 5.0,
        "min_profit_amount": 0.5,
        "trade_strategy": "fast_turnover"
    },
    "mid_medium": {
        "name": "средний трейдер (средняя прибыль, сбалансированный риск)",
        "min_price": 10.0,
        "max_price": 200.0,
        "min_profit_percent": 10.0,
        "min_profit_amount": 2.0,
        "trade_strategy": "balanced"
    },
    "pro_high": {
        "name": "Trade Pro (высокая прибыль, высокий риск)",
        "min_price": 50.0,
        "max_price": 1000.0,
        "min_profit_percent": 15.0,
        "min_profit_amount": 5.0,
        "trade_strategy": "high_profit"
    }
}


async def format_results(
    items: List[Dict[str, Any]],
    mode: str,
    default_game: str = "csgo"
) -> str:
    """
    Форматирует результаты автоматического арбитража для отображения.
    
    Args:
        items: Список найденных предметов
        mode: Режим автоарбитража (auto_low, auto_medium, auto_high)
        default_game: Код игры по умолчанию
        
    Returns:
        Отформатированный текст для отображения
    """
    # Получаем отображаемое имя режима
    mode_parts = mode.split('_')
    mode_type = mode_parts[0] if len(mode_parts) > 0 else mode
    mode_level = mode_parts[1] if len(mode_parts) > 1 else "medium"
    
    mode_key = f"{mode_type}_{mode_level}"
    mode_display = ARBITRAGE_MODES.get(mode_key, {}).get("name", mode)
    
    if not items:
        return f"ℹ️ Нет данных об автоматическом арбитраже ({mode_display})"
    
    header = f"🤖 <b>Результаты автоматического арбитража ({mode_display}):</b>\n\n"
    items_text = []
    for i, item in enumerate(items, start=1):
        name = item.get("title", "Неизвестный предмет")
        
        # Обрабатываем значение цены
        price_value = item.get("price", {})
        if isinstance(price_value, dict):
            price = float(price_value.get("amount", 0)) / 100
        else:
            try:
                price_str = str(item.get("price", "0"))
                price_str = price_str.replace('$', '').strip()
                price = float(price_str)
            except (ValueError, TypeError):
                price = float(price_value) / 100 if isinstance(price_value, (int, float)) else 0
        
        # Обрабатываем значение прибыли
        profit_value = item.get("profit", 0)
        if isinstance(profit_value, str) and '$' in profit_value:
            profit = float(profit_value.replace('$', '').strip())
        else:
            profit = float(profit_value) / 100 if isinstance(profit_value, (int, float)) else 0
            
        profit_percent = item.get("profit_percent", 0)
        
        game = item.get("game", default_game)
        game_display = GAMES.get(game, game)
        
        # Получаем дополнительную информацию о риске
        risk_level = "средний"
        if profit > 10 and profit_percent > 20:
            risk_level = "высокий"
        elif profit < 2 or profit_percent < 5:
            risk_level = "низкий"
            
        liquidity = item.get("liquidity", "medium")
        liquidity_display = {
            "high": "высокая",
            "medium": "средняя",
            "low": "низкая"
        }.get(liquidity, "средняя")
        
        # Используем HTML-форматирование
        item_text = (
            f"{i}. <b>{name}</b>\n"
            f"   🎮 Игра: <b>{game_display}</b>\n"
            f"   💰 Цена: <b>${price:.2f}</b>\n"
            f"   💵 Прибыль: <b>${profit:.2f}</b> (<b>{profit_percent:.1f}%</b>)\n"
            f"   🔄 Ликвидность: <b>{liquidity_display}</b>\n"
            f"   ⚠️ Риск: <b>{risk_level}</b>\n"
        )
        items_text.append(item_text)
    
    return header + "\n".join(items_text)


async def show_auto_stats_with_pagination(query: CallbackQuery, context: CallbackContext) -> None:
    """
    Отображает результаты автоматического арбитража с пагинацией.
    
    Args:
        query: Объект запроса обратного вызова
        context: Контекст обратного вызова
    """
    user_id = query.from_user.id
    
    # Получаем текущую страницу предметов
    items, current_page, total_pages = pagination_manager.get_page(user_id)
    
    # Получаем режим для форматирования
    mode = pagination_manager.get_mode(user_id)
    game = context.user_data.get("current_game", "csgo") if hasattr(context, "user_data") else "csgo"
    
    if not items:
        await query.edit_message_text(
            text="ℹ️ Нет данных об автоматическом арбитраже",
            reply_markup=get_back_to_arbitrage_keyboard()
        )
        return
    
    # Форматируем результаты для отображения
    formatted_text = await format_results(items, mode, game)
    
    # Создаем клавиатуру с пагинацией, если есть несколько страниц
    keyboard = []
    
    # Кнопки пагинации
    pagination_row = []
    if current_page > 0:
        pagination_row.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"paginate:prev:{mode}")
        )
    
    if total_pages > 1:
        pagination_row.append(
            InlineKeyboardButton(f"{current_page + 1}/{total_pages}", callback_data="page_info")
        )
    
    if current_page < total_pages - 1:
        pagination_row.append(
            InlineKeyboardButton("➡️ Вперед", callback_data=f"paginate:next:{mode}")
        )
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Кнопка назад к арбитражу
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад к арбитражу", callback_data="arbitrage")
    ])
    
    # Добавляем статус страницы, если не добавлен через номер страницы
    if total_pages <= 1:
        page_status = f"📄 Страница {current_page + 1} из {total_pages}"
        formatted_text += f"\n\n{page_status}"
    
    # Отображаем результаты
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=formatted_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def handle_pagination(
    query: CallbackQuery,
    context: CallbackContext,
    direction: str,
    mode: str = "auto"
) -> None:
    """
    Обрабатывает пагинацию результатов автоматического арбитража.
    
    Args:
        query: Объект запроса обратного вызова
        context: Контекст обратного вызова
        direction: Направление пагинации (next/prev)
        mode: Режим автоарбитража
    """
    user_id = query.from_user.id
    
    if direction == "next":
        pagination_manager.next_page(user_id)
    else:
        pagination_manager.prev_page(user_id)
    
    # Показываем обновленную страницу
    await show_auto_stats_with_pagination(query, context)


async def create_dmarket_api_client(context: CallbackContext) -> Optional[DMarketAPI]:
    """
    Создает и настраивает клиент DMarket API.
    
    Args:
        context: Контекст обратного вызова
        
    Returns:
        Настроенный клиент DMarketAPI или None в случае ошибки
    """
    # Загружаем ключи DMarket API из контекста бота или из переменных окружения
    public_key = context.bot_data.get('dmarket_public_key', '')
    secret_key = context.bot_data.get('dmarket_secret_key', '')
    
    if not public_key or not secret_key:
        # Пробуем получить из переменных окружения
        try:
            # Use the properly typed environ_type
            public_key = environ_type.get('DMARKET_PUBLIC_KEY', '')
            secret_key = environ_type.get('DMARKET_SECRET_KEY', '')
        except Exception as e:
            logger.error(f"Ошибка при получении ключей API из окружения: {e}")
            return None

    if not public_key or not secret_key:
        logger.error("API ключи не найдены ни в контексте, ни в переменных окружения")
        return None
    
    try:
        # Создаем API клиент с улучшенной стратегией повторных попыток
        retry_strategy = RetryStrategy(
            max_retries=3,
            initial_delay=1.0,
            max_delay=30.0,
            backoff_factor=2.0,
            status_codes_to_retry=[429, 500, 502, 503, 504]
        )
        
        # Use the properly typed environ_type
        api_url = environ_type.get('DMARKET_API_URL', 'https://api.dmarket.com')
        
        api_client = DMarketAPI(
            public_key=public_key,
            secret_key=secret_key,
            api_url=api_url,
            max_retries=3
        )
        
        logger.info("API клиент DMarket успешно создан")
        return api_client
    except Exception as e:
        logger.error(f"Ошибка при создании API клиента: {e}")
        return None


async def start_auto_trading(
    query: CallbackQuery,
    context: CallbackContext,
    mode: str
) -> None:
    """
    Запускает автоматический арбитраж и отображает результаты.
    
    Args:
        query: Объект запроса обратного вызова
        context: Контекст обратного вызова
        mode: Режим автоарбитража:
            - boost_low: Режим разгона баланса с низким порогом прибыли
            - mid_medium: Режим среднего трейдера со средней прибылью
            - pro_high: Режим профессионала с высокой прибылью
    """
    user_id = query.from_user.id
    
    # Отображаем сообщение о начале сканирования
    await query.edit_message_text(
        text=(
            "🔍 <b>Запускаем комплексное сканирование нескольких игр...</b>\n\n"
            "📊 Это займет некоторое время. Идет поиск для CS2, Dota 2, "
            "Rust и TF2..."
        ),
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Определяем параметры поиска в зависимости от режима
        mode_parts = mode.split('_')
        if len(mode_parts) < 2:
            # Если формат неверный, используем значения по умолчанию
            mode_type = "mid"
            profit_level = "medium"
        else:
            mode_type, profit_level = mode_parts
            
        # Получаем настройки режима
        mode_key = f"{mode_type}_{profit_level}"
        mode_settings = ARBITRAGE_MODES.get(mode_key, ARBITRAGE_MODES["mid_medium"])
        
        min_price = mode_settings["min_price"]
        max_price = mode_settings["max_price"]
        min_profit_percent = mode_settings["min_profit_percent"]
        min_profit_amount = mode_settings["min_profit_amount"]
        trade_strategy = mode_settings["trade_strategy"]
        display_mode = mode_settings["name"]
        
        # Всегда сканируем все игры
        games_to_scan = list(GAMES.keys())  # ["csgo", "dota2", "rust", "tf2"]
        
        await query.edit_message_text(
            text=(
                f"🔍 <b>Ищем возможности для режима {display_mode}...</b>\n\n"
                f"💼 Сканируем все игры (CS2, Dota 2, Rust, TF2)\n"
                f"⏳ Это может занять некоторое время..."
            ),
            parse_mode=ParseMode.HTML
        )
        
        # Создаем API клиент
        api_client = await create_dmarket_api_client(context)
        if not api_client:
            await query.edit_message_text(
                text="⚠️ <b>Не удалось создать API-клиент DMarket.</b>\n\nПроверьте настройки API ключей.",
                reply_markup=get_back_to_arbitrage_keyboard(),
                parse_mode=ParseMode.HTML
            )
            return
        
        # Проверяем баланс пользователя перед началом сканирования
        try:
            balance_info = await check_user_balance(api_client)
            available_balance = balance_info.get('balance', 0)
            
            if available_balance < min_price:
                await query.edit_message_text(
                    text=(
                        f"⚠️ <b>Недостаточно средств на балансе DMarket.</b>\n"
                        f"Доступно: <b>${available_balance:.2f}</b>\n"
                        f"Необходимо минимум: <b>${min_price:.2f}</b>"
                    ),
                    reply_markup=get_back_to_arbitrage_keyboard(),
                    parse_mode=ParseMode.HTML
                )
                return
        except APIError as e:
            error_message = await handle_api_error(e)
            await query.edit_message_text(
                text=f"❌ <b>Ошибка при проверке баланса:</b>\n\n{error_message}",
                reply_markup=get_back_to_arbitrage_keyboard(),
                parse_mode=ParseMode.HTML
            )
            return
        except Exception as e:
            await query.edit_message_text(
                text=f"❌ <b>Неизвестная ошибка при проверке баланса:</b>\n\n{str(e)}",
                reply_markup=get_back_to_arbitrage_keyboard(),
                parse_mode=ParseMode.HTML
            )
            return
        
        # Интегрируем внутренний арбитраж DMarket
        try:
            from src.dmarket.intramarket_arbitrage import (
                find_price_anomalies,
                find_trending_items,
                find_mispriced_rare_items,
                scan_for_intramarket_opportunities
            )
        except ImportError:
            logger.warning("Модуль intramarket_arbitrage не найден, будет использоваться только межплатформенный арбитраж")
        
        # Создаем задачи для параллельного выполнения
        tasks = []
        
        # Добавляем задачу для сканирования между площадками
        tasks.append(
            scan_multiple_games(
                games=games_to_scan,
                mode=profit_level,
                max_items_per_game=20,
                price_from=min_price,
                price_to=max_price
            )
        )
        
        # Добавляем задачи для внутреннего арбитража DMarket в зависимости от стратегии
        if 'find_price_anomalies' in locals():
            if mode_type == "boost":
                # Для режима разгона ищем ценовые аномалии
                tasks.append(
                    find_price_anomalies(
                        game="csgo",
                        similarity_threshold=0.9,
                        price_diff_percent=min_profit_percent,
                        max_results=30,
                        min_price=min_price,
                        max_price=max_price,
                        dmarket_api=api_client
                    )
                )
                
                for game in games_to_scan[1:]:  # Остальные игры кроме csgo
                    tasks.append(
                        find_price_anomalies(
                            game=game,
                            similarity_threshold=0.9,
                            price_diff_percent=min_profit_percent,
                            max_results=10,
                            min_price=min_price,
                            max_price=max_price,
                            dmarket_api=api_client
                        )
                    )
            
            elif mode_type == "mid":
                # Для среднего режима ищем как аномалии, так и трендовые предметы
                for game in games_to_scan:
                    tasks.append(
                        find_price_anomalies(
                            game=game,
                            similarity_threshold=0.85,
                            price_diff_percent=min_profit_percent,
                            max_results=10,
                            min_price=min_price,
                            max_price=max_price,
                            dmarket_api=api_client
                        )
                    )
                    
                    if 'find_trending_items' in locals():
                        tasks.append(
                            find_trending_items(
                                game=game,
                                min_price=min_price,
                                max_price=max_price,
                                max_results=10,
                                dmarket_api=api_client
                            )
                        )
            
            elif mode_type == "pro" and 'scan_for_intramarket_opportunities' in locals():
                # Для профессионального режима ищем все типы возможностей
                tasks.append(
                    scan_for_intramarket_opportunities(
                        games=games_to_scan,
                        max_results_per_game=10,
                        min_price=min_price,
                        max_price=max_price,
                        include_anomalies=True,
                        include_trending=True,
                        include_rare=True,
                        dmarket_api=api_client
                    )
                )
        
        # Показываем прогресс
        progress_msg = await query.edit_message_text(
            text=(
                f"🔍 <b>Сканирование активно ({len(tasks)} задач)...</b>\n\n"
                f"⏳ Прогресс: 0% - Ожидайте результаты..."
            ),
            parse_mode=ParseMode.HTML
        )
        
        # Выполняем все задачи параллельно
        start_time = datetime.now()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Обрабатываем результаты
        all_items = []
        
        # Результаты межплатформенного арбитража
        platform_arbitrage_results = results[0]
        if isinstance(platform_arbitrage_results, list):
            all_items.extend(platform_arbitrage_results)
        
        # Результаты внутреннего арбитража
        for result in results[1:]:
            if isinstance(result, Exception):
                logger.error(f"Ошибка при сканировании: {result}")
                continue
                
            if isinstance(result, dict):
                # Результат scan_for_intramarket_opportunities
                for game, game_results in result.items():
                    for category, items in game_results.items():
                        # Преобразуем формат для совместимости
                        for item in items:
                            if category == "price_anomalies":
                                # Ценовые аномалии
                                all_items.append({
                                    "title": item.get("item_to_buy", {}).get("title", "Неизвестный предмет"),
                                    "price": item.get("buy_price", 0) * 100,  # Конвертируем в центы
                                    "profit": item.get("profit_after_fee", 0) * 100,  # Конвертируем в центы
                                    "profit_percent": item.get("profit_percentage", 0),
                                    "game": item.get("game", "csgo"),
                                    "source": "dmarket_internal",
                                    "strategy": "price_anomaly",
                                    "item_id": item.get("item_to_buy", {}).get("itemId", ""),
                                    "liquidity": "high"
                                })
                            elif category == "trending_items":
                                # Трендовые предметы
                                all_items.append({
                                    "title": item.get("item", {}).get("title", "Неизвестный предмет"),
                                    "price": item.get("current_price", 0) * 100,  # Конвертируем в центы
                                    "profit": (item.get("projected_price", 0) - item.get("current_price", 0)) * 100,
                                    "profit_percent": item.get("potential_profit_percent", 0),
                                    "game": item.get("game", "csgo"),
                                    "source": "dmarket_internal",
                                    "strategy": "trending",
                                    "item_id": item.get("item", {}).get("itemId", ""),
                                    "liquidity": "medium"
                                })
                            elif category == "rare_mispriced":
                                # Редкие неправильно оцененные предметы
                                all_items.append({
                                    "title": item.get("item", {}).get("title", "Неизвестный предмет"),
                                    "price": item.get("current_price", 0) * 100,  # Конвертируем в центы
                                    "profit": (item.get("estimated_value", 0) - item.get("current_price", 0)) * 100,
                                    "profit_percent": item.get("price_difference_percent", 0),
                                    "game": item.get("game", "csgo"),
                                    "source": "dmarket_internal",
                                    "strategy": "rare_item",
                                    "item_id": item.get("item", {}).get("itemId", ""),
                                    "liquidity": "low",
                                    "rare_traits": item.get("rare_traits", [])
                                })
            elif isinstance(result, list):
                # Результаты find_price_anomalies или find_trending_items
                for item in result:
                    if "item_to_buy" in item:
                        # Ценовые аномалии
                        all_items.append({
                            "title": item.get("item_to_buy", {}).get("title", "Неизвестный предмет"),
                            "price": item.get("buy_price", 0) * 100,  # Конвертируем в центы
                            "profit": item.get("profit_after_fee", 0) * 100,  # Конвертируем в центы
                            "profit_percent": item.get("profit_percentage", 0),
                            "game": item.get("game", "csgo"),
                            "source": "dmarket_internal",
                            "strategy": "price_anomaly",
                            "item_id": item.get("item_to_buy", {}).get("itemId", ""),
                            "liquidity": "high"
                        })
                    elif "item" in item and "projected_price" in item:
                        # Трендовые предметы
                        all_items.append({
                            "title": item.get("item", {}).get("title", "Неизвестный предмет"),
                            "price": item.get("current_price", 0) * 100,  # Конвертируем в центы
                            "profit": (item.get("projected_price", 0) - item.get("current_price", 0)) * 100,
                            "profit_percent": item.get("potential_profit_percent", 0),
                            "game": item.get("game", "csgo"),
                            "source": "dmarket_internal",
                            "strategy": "trending",
                            "item_id": item.get("item", {}).get("itemId", ""),
                            "liquidity": "medium"
                        })
                    elif "item" in item and "estimated_value" in item:
                        # Редкие неправильно оцененные предметы
                        all_items.append({
                            "title": item.get("item", {}).get("title", "Неизвестный предмет"),
                            "price": item.get("current_price", 0) * 100,  # Конвертируем в центы
                            "profit": (item.get("estimated_value", 0) - item.get("current_price", 0)) * 100,
                            "profit_percent": item.get("price_difference_percent", 0),
                            "game": item.get("game", "csgo"),
                            "source": "dmarket_internal",
                            "strategy": "rare_item",
                            "item_id": item.get("item", {}).get("itemId", ""),
                            "liquidity": "low",
                            "rare_traits": item.get("rare_traits", [])
                        })
        
        # Фильтруем результаты по минимальной прибыли и проценту
        filtered_items = [
            item for item in all_items 
            if (item.get("profit", 0) / 100 >= min_profit_amount and 
                item.get("profit_percent", 0) >= min_profit_percent)
        ]
        
        # Сортируем по проценту прибыли (от большего к меньшему)
        filtered_items.sort(key=lambda x: x.get("profit_percent", 0), reverse=True)
        
        if not filtered_items:
            await query.edit_message_text(
                text=(
                    f"ℹ️ <b>Не найдено подходящих предметов для режима {display_mode}.</b>\n\n"
                    f"Попробуйте изменить параметры поиска или выбрать другой режим."
                ),
                reply_markup=get_back_to_arbitrage_keyboard(),
                parse_mode=ParseMode.HTML
            )
            return
        
        # Сохраняем результаты в менеджере пагинации
        pagination_manager.add_items_for_user(user_id, filtered_items, mode)
        
        # Отображаем результаты с пагинацией
        items, current_page, total_pages = pagination_manager.get_page(user_id)
        formatted_results = await format_results(items, mode)
        
        # Создаем клавиатуру с пагинацией
        keyboard = []
        
        # Кнопки пагинации
        if total_pages > 1:
            pagination_row = []
            if current_page > 0:
                pagination_row.append(
                    InlineKeyboardButton("⬅️ Назад", callback_data=f"paginate:prev:{mode}")
                )
            
            pagination_row.append(
                InlineKeyboardButton(f"{current_page + 1}/{total_pages}", callback_data="page_info")
            )
            
            if current_page < total_pages - 1:
                pagination_row.append(
                    InlineKeyboardButton("➡️ Вперед", callback_data=f"paginate:next:{mode}")
                )
            
            keyboard.append(pagination_row)
        
        # Кнопка запуска автоматической торговли (если доступна)
        public_key = context.bot_data.get('dmarket_public_key', '')
        secret_key = context.bot_data.get('dmarket_secret_key', '')
        if not public_key or not secret_key:
            try:
                # Use the properly typed environ_type
                public_key = environ_type.get('DMARKET_PUBLIC_KEY', '')
                secret_key = environ_type.get('DMARKET_SECRET_KEY', '')
            except Exception:
                pass
                
        if (mode_type in ["mid", "pro"] and
            public_key and secret_key and 
            available_balance >= min_price):
            
            keyboard.append([
                InlineKeyboardButton(
                    "🤖 Запустить авто-торговлю", 
                    callback_data=f"auto_trade:{mode}"
                )
            ])
        
        # Кнопка назад к выбору режима
        keyboard.append([
            InlineKeyboardButton("⬅️ Назад к выбору режима", callback_data="auto_arbitrage")
        ])
        
        # Отображаем результаты
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Добавляем информацию о найденных предметах
        info_text = (
            f"🔍 <b>Найдено {len(filtered_items)} предметов для режима {display_mode}.</b>\n"
            f"💰 Доступный баланс: <b>${available_balance:.2f}</b>\n"
            f"⏱️ Время выполнения: <b>{execution_time:.1f}с</b>\n\n"
        )
        
        await query.edit_message_text(
            text=info_text + formatted_results,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Ошибка при запуске автоматического арбитража: {e}")
        logger.error(traceback.format_exc())
        
        await query.edit_message_text(
            text=(
                f"⚠️ <b>Произошла ошибка при поиске предметов:</b>\n\n"
                f"{str(e)}\n\n"
                f"Пожалуйста, попробуйте еще раз или обратитесь к администратору."
            ),
            reply_markup=get_back_to_arbitrage_keyboard(),
            parse_mode=ParseMode.HTML
        )


async def check_balance_command(message: Union[CallbackQuery, Update], context: CallbackContext) -> None:
    """
    Проверяет баланс DMarket и связь с API, а также показывает статистику аккаунта.
    
    Args:
        message: Исходное сообщение или объект запроса обратного вызова
        context: Контекст обратного вызова
    """
    # Определяем, является ли message объектом CallbackQuery или Update
    is_callback = isinstance(message, CallbackQuery)
    
    if is_callback:
        # Для обратного вызова отправляем временное сообщение о проверке
        await message.edit_message_text(
            text="🔄 <b>Проверка подключения к DMarket API...</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        # Для обычного сообщения отправляем временное сообщение о проверке
        processing_message = await message.reply_text(
            text="🔄 <b>Проверка подключения к DMarket API...</b>",
            parse_mode=ParseMode.HTML
        )
    
    try:
        # Создаем API клиент с улучшенными настройками повторных попыток
        api_client = await create_dmarket_api_client(context)
        
        if not api_client:
            error_text = (
                "❌ <b>Ошибка подключения:</b>\n\n"
                "Не удалось создать клиент DMarket API. "
                "Проверьте, что ключи API настроены правильно."
            )
            
            if is_callback:
                await message.edit_message_text(
                    text=error_text,
                    reply_markup=get_back_to_arbitrage_keyboard(),
                    parse_mode=ParseMode.HTML
                )
            else:
                await processing_message.edit_text(
                    text=error_text,
                    parse_mode=ParseMode.HTML
                )
            return
        
        # Обновляем статус
        status_text = "🔄 <b>Проверка баланса DMarket...</b>"
        if is_callback:
            await message.edit_message_text(
                text=status_text, 
                parse_mode=ParseMode.HTML
            )
        else:
            await processing_message.edit_text(
                text=status_text, 
                parse_mode=ParseMode.HTML
            )
        
        # Проверяем баланс через оптимизированную функцию прямого запроса
        # Используем несколько попыток с разными эндпоинтами для надежности
        try:
            # Сначала пробуем через новый эндпоинт баланса
            balance_result = await api_client.get_user_balance()
            
            # Проверяем, есть ли ошибка в ответе API
            if balance_result.get("error", False):
                error_msg = balance_result.get("error_message", "Неизвестная ошибка API")
                error_code = balance_result.get("status_code", "неизвестный код")
                
                error_text = (
                    f"❌ <b>Ошибка при получении баланса:</b>\n\n"
                    f"Код: {error_code}\n"
                    f"Сообщение: {error_msg}\n\n"
                    f"Проверьте настройки API ключей и попробуйте снова."
                )
                
                if is_callback:
                    await message.edit_message_text(
                        text=error_text,
                        reply_markup=get_back_to_arbitrage_keyboard(),
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await processing_message.edit_text(
                        text=error_text,
                        parse_mode=ParseMode.HTML
                    )
                return
            
            # Извлекаем данные о балансе
            available_balance = balance_result.get("available_balance", 0)
            total_balance = balance_result.get("total_balance", 0)
            has_funds = balance_result.get("has_funds", False)
            
            # Получаем дополнительную информацию об аккаунте
            account_info = await api_client.get_account_details()
            username = account_info.get("username", "Неизвестный")
            
            # Получаем статистику активных предложений
            offers_info = await api_client.get_active_offers(limit=1)
            total_offers = offers_info.get("total", 0)
            
            # Проверяем, достаточно ли средств для арбитража
            min_required_balance = ARBITRAGE_MODES["boost_low"]["min_price"]
            
            if available_balance < min_required_balance:
                warning_text = (
                    f"⚠️ <b>Предупреждение:</b> Баланс меньше минимального "
                    f"рекомендуемого значения (${min_required_balance:.2f}) для арбитража."
                )
            else:
                warning_text = ""
            
            # Определяем статус баланса
            if has_funds and available_balance >= 5.0:
                balance_status = "✅ <b>Достаточно для арбитража</b>"
            elif has_funds:
                balance_status = "⚠️ <b>Низкий, но можно использовать</b>"
            else:
                balance_status = "❌ <b>Недостаточно для арбитража</b>"
            
            # Формируем итоговое сообщение
            response_text = (
                f"📊 <b>Информация о DMarket аккаунте</b>\n\n"
                f"👤 <b>Пользователь:</b> {username}\n"
                f"💰 <b>Доступный баланс:</b> ${available_balance:.2f}\n"
                f"💵 <b>Общий баланс:</b> ${total_balance:.2f}\n"
                f"📦 <b>Активные предложения:</b> {total_offers}\n"
                f"🔋 <b>Статус баланса:</b> {balance_status}\n\n"
            )
            
            if warning_text:
                response_text += f"{warning_text}\n\n"
            
            current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            response_text += f"⏱️ <b>Обновлено:</b> {current_time}"
            
            # Добавляем подробную информацию для отладки только в лог
            logger.info(
                f"Баланс DMarket: ${available_balance:.2f} доступно, "
                f"${total_balance:.2f} всего. "
                f"Пользователь: {username}. "
                f"Активных предложений: {total_offers}."
            )
            
            # Отправляем результат
            reply_markup = get_back_to_arbitrage_keyboard() if is_callback else None
            
            if is_callback:
                await message.edit_message_text(
                    text=response_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            else:
                await processing_message.edit_text(
                    text=response_text,
                    parse_mode=ParseMode.HTML
                )
            
        except APIError as e:
            error_message = await handle_api_error(e)
            error_text = (
                f"❌ <b>Ошибка при проверке баланса:</b>\n\n{error_message}\n\n"
                f"Возможно, проблема с подключением к DMarket API. "
                f"Проверьте настройки API ключей и повторите попытку."
            )
            
            if is_callback:
                await message.edit_message_text(
                    text=error_text,
                    reply_markup=get_back_to_arbitrage_keyboard(),
                    parse_mode=ParseMode.HTML
                )
            else:
                await processing_message.edit_text(
                    text=error_text,
                    parse_mode=ParseMode.HTML
                )
                
    except Exception as e:
        # Обрабатываем общую ошибку и показываем подробную информацию
        logger.error(f"Ошибка при проверке баланса: {e}")
        logger.error(traceback.format_exc())
        
        error_text = (
            f"❌ <b>Ошибка при проверке баланса:</b>\n\n"
            f"Тип ошибки: {type(e).__name__}\n"
            f"Сообщение: {str(e)}\n\n"
            f"Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
        
        if is_callback:
            await message.edit_message_text(
                text=error_text,
                reply_markup=get_back_to_arbitrage_keyboard(),
                parse_mode=ParseMode.HTML
            )
        else:
            await processing_message.edit_text(
                text=error_text,
                parse_mode=ParseMode.HTML
            )


async def show_auto_stats(query: CallbackQuery, context: CallbackContext) -> None:
    """
    Показывает статистику автоматического арбитража.
    
    Args:
        query: Объект запроса обратного вызова
        context: Контекст обратного вызова
    """
    # Эта функция просто отображает текущие результаты автоматического арбитража
    await show_auto_stats_with_pagination(query, context)


async def stop_auto_trading(query: CallbackQuery, context: CallbackContext) -> None:
    """
    Останавливает процесс автоматического арбитража.
    
    Args:
        query: Объект запроса обратного вызова
        context: Контекст обратного вызова
    """
    user_id = query.from_user.id
    
    # Отключение автоторговли в настройках пользователя
    if hasattr(context, "user_data"):
        context.user_data["auto_trading_enabled"] = False
    
    # Создаем клавиатуру для возврата
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="arbitrage")]
    ])
    
    # Отображаем сообщение о остановке
    await query.edit_message_text(
        text=(
            "🛑 <b>Автоматическая торговля отключена.</b>\n\n"
            "Все текущие операции будут завершены, но новые торговые операции "
            "выполняться не будут."
        ),
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    logger.info(f"Автоторговля отключена для пользователя {user_id}")


async def handle_auto_trade(query, context, mode: str):
    """
    Запускает автоматическую торговлю для выбранного режима.
    
    Args:
        query: Объект запроса обратного вызова
        context: Контекст обратного вызова
        mode: Режим автоарбитража (low, medium, high)
    """
    from src.telegram_bot.utils.api_client import setup_api_client
    from src.utils.api_error_handling import APIError, handle_api_error
    from telegram.constants import ChatAction
    from telegram import ParseMode
    from src.telegram_bot.keyboards import get_back_to_arbitrage_keyboard
    from src.telegram_bot.auto_arbitrage_scanner import scan_multiple_games, check_user_balance
    from src.telegram_bot.pagination import pagination_manager
    from src.dmarket.arbitrage import GAMES
    
    # Проверяем баланс перед запуском
    api_client = setup_api_client()
    if not api_client:
        await query.edit_message_text(
            "❌ <b>Не удалось создать API-клиент.</b>\n\n"
            "Проверьте корректность API ключей и доступность сервера.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_to_arbitrage_keyboard()
        )
        return
        
    try:
        # Проверяем баланс пользователя
        balance_data = await check_user_balance(api_client)
        
        if not balance_data.get("has_funds", False):
            available = balance_data.get("available_balance", 0.0)
            await query.edit_message_text(
                f"⚠️ <b>Недостаточно средств для автоматической торговли</b>\n\n"
                f"Доступно: ${available:.2f} USD\n"
                f"Необходимо минимум: $1.00 USD",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_to_arbitrage_keyboard()
            )
            return
            
        # Отправка индикатора загрузки
        await query.message.chat.send_action(ChatAction.TYPING)
        
        # Все доступные игры для сканирования
        games = ["csgo", "dota2", "rust", "tf2"]
        
        # Настраиваем параметры в зависимости от режима
        if mode == "low":
            min_profit = 5.0
            max_price = 20.0
            risk_level = "low"
        elif mode == "high":
            min_profit = 20.0
            max_price = 100.0
            risk_level = "high"
        else:  # medium
            min_profit = 10.0
            max_price = 50.0
            risk_level = "medium"
        
        # Сообщаем пользователю о начале сканирования
        await query.edit_message_text(
            f"🔍 <b>Начинаем полное сканирование DMarket...</b>\n\n"
            f"🎮 Игры: {', '.join(GAMES.get(g, g) for g in games)}\n"
            f"💰 Минимальная прибыль: {min_profit}%\n"
            f"⏳ Это может занять некоторое время...",
            parse_mode=ParseMode.HTML
        )
        
        # Запускаем сканирование
        results = await scan_multiple_games(
            games=games,
            mode=mode,
            max_items_per_game=15,
            price_from=1.0,
            price_to=max_price
        )
        
        # Обрабатываем результаты
        total_items = sum(len(items) for items in results.values())
        
        if total_items == 0:
            await query.edit_message_text(
                "ℹ️ <b>Не найдено выгодных предметов для автоматической торговли.</b>\n\n"
                "Попробуйте изменить параметры поиска или повторить позже.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_to_arbitrage_keyboard()
            )
            return
        
        # Преобразуем результаты в плоский список для пагинации
        all_items = []
        for game, items in results.items():
            for item in items:
                item["game"] = game  # Добавляем код игры в элемент
                all_items.append(item)
        
        # Сохраняем результаты в менеджере пагинации
        pagination_manager.add_items(query.from_user.id, all_items, mode)
        
        # Показываем первую страницу результатов
        await show_auto_stats_with_pagination(query, context)
        
    except APIError as e:
        # Используем улучшенную обработку ошибок API
        error_message = await handle_api_error(e)
        await query.edit_message_text(
            f"❌ <b>Ошибка API DMarket при сканировании:</b>\n\n{error_message}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_to_arbitrage_keyboard()
        )
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при автоторговле: {e}")
        tb_string = traceback.format_exc()
        logger.error(f"Traceback: {tb_string}")
        
        await query.edit_message_text(
            f"❌ <b>Ошибка при выполнении автоматического сканирования:</b>\n\n{str(e)}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_to_arbitrage_keyboard()
        )

# Export all functions
__all__ = [
    'start_auto_trading',
    'stop_auto_trading',
    'check_balance_command',
    'handle_pagination',
    'show_auto_stats_with_pagination',
    'handle_auto_trade',
]
