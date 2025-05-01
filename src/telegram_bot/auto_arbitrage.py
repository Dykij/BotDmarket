"""
Модуль для автоматического арбитража.
"""

import logging
import traceback
import asyncio
from typing import List, Dict, Any, Tuple, Optional

from telegram import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

from src.telegram_bot.pagination import pagination_manager
from src.dmarket.arbitrage import GAMES, ArbitrageTrader
from src.telegram_bot.auto_arbitrage_scanner import (
    scan_multiple_games,
    auto_trade_items,
    check_user_balance
)
from src.telegram_bot.keyboards import get_back_to_arbitrage_keyboard
from src.dmarket.dmarket_api import DMarketAPI

# Настройка логирования
logger = logging.getLogger(__name__)


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
    mode_display = {
        "auto_low": "минимальная прибыль",
        "auto_medium": "средняя прибыль",
        "auto_high": "высокая прибыль",
    }.get(mode, mode)
    
    if not items:
        return f"ℹ️ Нет данных об автоматическом арбитраже ({mode_display})"
    
    header = f"🤖 Результаты автоматического арбитража ({mode_display}):\n\n"
    items_text = []
    for i, item in enumerate(items, start=1):
        name = item.get("title", "Неизвестный предмет")
        
        # Обрабатываем значение цены
        price_value = item.get("price", {})
        if isinstance(price_value, dict):
            price = float(price_value.get("amount", 0)) / 100
        else:
            price_str = str(item.get("price", "0"))
            price_str = price_str.replace('$', '').strip()
            price = float(price_str)
        
        # Обрабатываем значение прибыли
        profit_value = item.get("profit", 0)
        if isinstance(profit_value, str) and '$' in profit_value:
            profit = float(profit_value.replace('$', '').strip())
        else:
            profit = float(profit_value)
            
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
        
        item_text = (
            f"{i}. {name}\n"
            f"   🎮 Игра: {game_display}\n"
            f"   💰 Цена: ${price:.2f}\n"
            f"   💵 Прибыль: ${profit:.2f} ({profit_percent:.1f}%)\n"
            f"   🔄 Ликвидность: {liquidity_display}\n"
            f"   ⚠️ Риск: {risk_level}\n"
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
    
    # Добавляем статус страницы
    page_status = f"📄 Страница {current_page + 1} из {total_pages}"
    formatted_text += f"\n\n{page_status}"
    
    # Отображаем результаты
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=formatted_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
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
        mode: Режим автоарбитража (auto_low, auto_medium, auto_high)
    """
    user_id = query.from_user.id
    
    # Проверяем, есть ли указанная игра в контексте
    selected_game = context.user_data.get(
        "current_game", "csgo"
    ) if hasattr(context, "user_data") else "csgo"
    
    # Отображаем сообщение о начале сканирования
    await query.edit_message_text(
        text=(
            "🔍 Запускаем автоматическое сканирование нескольких игр...\n\n"
            "📊 Это займет некоторое время. Идет поиск для CS2, Dota 2, "
            "Rust и TF2..."
        ),
        reply_markup=None
    )
    
    try:
        # Определяем параметры поиска в зависимости от режима
        search_mode = (
            "low" if mode == "auto_low" 
            else "medium" if mode == "auto_medium" 
            else "high"
        )
        
        # Определяем уровень риска для автоторговли
        risk_level = (
            "low" if mode == "auto_low"
            else "medium" if mode == "auto_medium"
            else "high"
        )
        
        # Проверяем, нужно ли искать для всех игр или только для выбранной
        if selected_game in GAMES:
            # Пользователь указал конкретную игру
            games_to_scan = [selected_game]
            await query.edit_message_text(
                text=(
                    f"🔍 Ищем возможности автоматического арбитража для "
                    f"{GAMES.get(selected_game, selected_game)}..."
                ),
                reply_markup=None
            )
        else:
            # Сканируем все поддерживаемые игры
            games_to_scan = list(GAMES.keys())  # ["csgo", "dota2", "tf2", "rust"]
        
        # Максимальное количество предметов для каждой игры
        max_items_per_game = 10
        
        # Получаем API ключи из пользовательских данных или окружения
        import os
        
        public_key = context.user_data.get("api_key", "") if hasattr(context, "user_data") else ""
        secret_key = context.user_data.get("api_secret", "") if hasattr(context, "user_data") else ""
        
        if not public_key or not secret_key:
            public_key = os.environ.get("DMARKET_PUBLIC_KEY", "")
            secret_key = os.environ.get("DMARKET_SECRET_KEY", "")
        
        if not public_key or not secret_key:
            logger.error("Отсутствуют API ключи DMarket")
            await query.edit_message_text(
                text=(
                    "❌ Ошибка: API ключи DMarket не настроены.\n\n"
                    "Для использования автоматического арбитража необходимо "
                    "указать API ключи DMarket с помощью команды /setup."
                ),
                reply_markup=get_back_to_arbitrage_keyboard()
            )
            return
        
        # Создаем API-клиент для всех операций
        api_client = DMarketAPI(
            public_key,
            secret_key,
            "https://api.dmarket.com",
            max_retries=3,
            connection_timeout=10.0,
            pool_limits=10
        )
        
        # Проверяем баланс пользователя перед началом
        has_funds, balance = await check_user_balance(api_client)
        
        if not has_funds:
            await query.edit_message_text(
                text=(
                    f"⚠️ Недостаточно средств для торговли.\n\n"
                    f"Текущий баланс: ${balance:.2f}\n"
                    f"Для торговли необходимо минимум $1.00"
                ),
                reply_markup=get_back_to_arbitrage_keyboard()
            )
            return
            
        # Информируем пользователя о начале поиска
        await query.edit_message_text(
            text=(
                f"💰 Текущий баланс: ${balance:.2f}\n\n"
                f"🔍 Запускаем поиск арбитражных возможностей..."
            ),
            reply_markup=None
        )
        
        # Запускаем поиск для всех указанных игр
        items_by_game = await scan_multiple_games(
            games=games_to_scan,
            mode=search_mode,
            max_items_per_game=max_items_per_game
        )
        
        # Информируем пользователя о найденных предметах
        found_count = sum(len(items) for items in items_by_game.values())
        
        if found_count == 0:
            await query.edit_message_text(
                text=(
                    "ℹ️ Не найдено предметов для арбитража.\n\n"
                    "Попробуйте изменить параметры поиска или выбрать другую игру."
                ),
                reply_markup=get_back_to_arbitrage_keyboard()
            )
            return
            
        await query.edit_message_text(
            text=(
                f"✅ Найдено {found_count} предметов для арбитража.\n"
                f"⏳ Обрабатываем и готовим к автоматической торговле..."
            ),
            reply_markup=None
        )
        
        # Объединяем все найденные предметы для отображения, сохраняя информацию о играх
        all_items = []
        for game, items in items_by_game.items():
            for item in items:
                # Добавляем игру к каждому предмету, если ещё не добавлена
                if "game" not in item:
                    item["game"] = game
                all_items.append(item)
        
        # Определяем параметры автоторговли в зависимости от режима
        min_profit = 0.5  # USD (низкая прибыль)
        max_price = 50.0  # USD (макс. цена покупки)
        max_trades = 2    # Макс. количество сделок (безопасный режим)
        
        if mode == "auto_medium":
            min_profit = 2.0  # USD (средняя прибыль)
            max_price = 100.0
            max_trades = 5
        elif mode == "auto_high":
            min_profit = 5.0  # USD (высокая прибыль)
            max_price = 200.0
            max_trades = 10
            
        # Проверяем, есть ли в контексте ограничения пользователя
        if hasattr(context, "user_data") and "trade_settings" in context.user_data:
            settings = context.user_data["trade_settings"]
            min_profit = settings.get("min_profit", min_profit)
            max_price = settings.get("max_price", max_price)
            max_trades = settings.get("max_trades", max_trades)
        
        # Выполняем автоматическую торговлю, если есть найденные предметы
        purchases = 0
        sales = 0
        total_profit = 0.0
        
        if all_items:
            # Выполняем автоматическую торговлю только если пользователь явно это запросил
            # В учебной версии не выполняем реальную торговлю, только показываем возможности
            if context.user_data.get("auto_trading_enabled", False) if hasattr(context, "user_data") else False:
                purchases, sales, total_profit = await auto_trade_items(
                    items_by_game,
                    min_profit=min_profit,
                    max_price=max_price,
                    dmarket_api=api_client,
                    max_trades=max_trades,
                    risk_level=risk_level
                )
            else:
                # Если автоторговля не включена, показываем только анализ возможностей
                await query.edit_message_text(
                    text=(
                        f"✅ Найдено {found_count} предметов для арбитража.\n\n"
                        f"📈 Автоторговля не включена. Показываем только анализ возможностей.\n"
                        f"Для включения автоторговли используйте /setup и включите опцию автоторговли."
                    ),
                    reply_markup=None
                )
        
        # Добавляем найденные предметы в менеджер пагинации с информацией о результатах
        pagination_manager.add_items_for_user(user_id, all_items, mode)
        
        # Обновляем статус для пользователя
        await query.edit_message_text(
            text=(
                f"✅ {'Автоматический арбитраж завершен!' if context.user_data.get('auto_trading_enabled', False) else 'Анализ возможностей арбитража завершен!'}\n\n"
                f"📈 Результаты:\n"
                f"- Найдено предметов: {found_count}\n"
                f"- Купленные предметы: {purchases}\n"
                f"- Проданные предметы: {sales}\n"
                f"- Общая прибыль: ${total_profit:.2f}\n\n"
                f"⏳ Загружаем подробные результаты..."
            ),
            reply_markup=None
        )
        
        # Отображаем результаты с пагинацией
        await show_auto_stats_with_pagination(query, context)
        
    except Exception as e:
        # Получаем полный трейс ошибки для диагностики
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в start_auto_trading: {str(e)}\n{error_traceback}")
        
        # Информируем пользователя об ошибке
        error_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="auto_arbitrage")],
            [InlineKeyboardButton("⬅️ Назад в меню", callback_data="arbitrage")]
        ])
        
        # Форматируем сообщение об ошибке для отображения
        error_message = str(e)
        # Обрезаем слишком длинное сообщение для Telegram
        if len(error_message) > 200:
            error_message = error_message[:200] + "..."
            
        await query.edit_message_text(
            text=f"❌ Произошла ошибка при автоматическом арбитраже:\n{error_message}",
            reply_markup=error_keyboard
        )


async def check_balance_command(query: CallbackQuery, context: CallbackContext) -> None:
    """
    Проверяет баланс пользователя на DMarket.
    
    Args:
        query: Объект запроса обратного вызова
        context: Контекст обратного вызова
    """
    # Получаем API ключи из контекста или окружения
    import os
    
    public_key = context.user_data.get("api_key", "") if hasattr(context, "user_data") else ""
    secret_key = context.user_data.get("api_secret", "") if hasattr(context, "user_data") else ""
    
    if not public_key or not secret_key:
        public_key = os.environ.get("DMARKET_PUBLIC_KEY", "")
        secret_key = os.environ.get("DMARKET_SECRET_KEY", "")
    
    if not public_key or not secret_key:
        await query.edit_message_text(
            text=(
                "❌ Ошибка: API ключи DMarket не настроены.\n\n"
                "Для проверки баланса необходимо указать API ключи DMarket "
                "с помощью команды /setup."
            ),
            reply_markup=get_back_to_arbitrage_keyboard()
        )
        return
    
    # Отображаем сообщение о начале проверки
    await query.edit_message_text(
        text="⏳ Проверяем баланс на DMarket...",
        reply_markup=None
    )
    
    try:
        # Создаем API-клиент
        api_client = DMarketAPI(
            public_key,
            secret_key,
            "https://api.dmarket.com",
            max_retries=3
        )
        
        # Проверяем баланс
        has_funds, balance = await check_user_balance(api_client)
        
        # Создаем клавиатуру для возврата
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад в меню", callback_data="arbitrage")]
        ])
          # Отображаем результат
        if has_funds:
            await query.edit_message_text(
                text=(
                    f"✅ Баланс на DMarket: ${balance:.2f}\n\n"
                    f"{'✅ Достаточно для торговли' if balance >= 1.0 else '⚠️ Недостаточно для торговли (мин. $1.00)'}"
                ),
                reply_markup=keyboard
            )
        elif balance > 0:
            # Есть баланс, но меньше минимального
            await query.edit_message_text(
                text=(
                    f"⚠️ Баланс на DMarket: ${balance:.2f}\n\n"
                    f"Недостаточно средств для торговли. "
                    f"Пополните баланс на DMarket."
                ),
                reply_markup=keyboard
            )
        else:
            # Баланс равен 0, возможно из-за проблем с API
            api_error_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Обновить API ключи", callback_data="setup")],
                [InlineKeyboardButton("⬅️ Назад в меню", callback_data="arbitrage")]
            ])
            
            await query.edit_message_text(
                text=(
                    "❌ Не удалось получить баланс DMarket\n\n"
                    "Возможные причины:\n"
                    "1. Неверные API ключи DMarket\n"
                    "2. Истек срок действия API ключей\n"
                    "3. Недостаточно прав доступа у API ключей\n\n"
                    "Обновите API ключи в настройках."
                ),
                reply_markup=api_error_keyboard
            )
    except Exception as e:
        logger.error(f"Ошибка при проверке баланса: {str(e)}")
        
        # Информируем пользователя об ошибке
        error_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="check_balance")],
            [InlineKeyboardButton("⬅️ Назад в меню", callback_data="arbitrage")]
        ])
        
        await query.edit_message_text(
            text=f"❌ Ошибка при проверке баланса:\n{str(e)}",
            reply_markup=error_keyboard
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
            "🛑 Автоматическая торговля отключена.\n\n"
            "Все текущие операции будут завершены, но новые торговые операции "
            "выполняться не будут."
        ),
        reply_markup=keyboard
    )
    
    logger.info(f"Автоторговля отключена для пользователя {user_id}")
