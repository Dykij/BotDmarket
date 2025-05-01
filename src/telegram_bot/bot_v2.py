"""
Модуль Telegram-бота для арбитража DMarket.
"""

import asyncio
import logging
import os
import sys
import json
import time
from typing import Dict, List, Any, Optional, Tuple

# Добавляем корневой каталог проекта в путь импорта
python_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if python_path not in sys.path:
    sys.path.insert(0, python_path)

# Импортируем компоненты telegram-бота с новым API (версия 20+)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, CallbackContext, MessageHandler, filters
)
from dotenv import load_dotenv

from src.dmarket.arbitrage import arbitrage_boost_async, arbitrage_mid_async, arbitrage_pro_async, GAMES
from src.telegram_bot.keyboards import (
    get_arbitrage_keyboard, get_game_selection_keyboard,
    get_auto_arbitrage_keyboard, get_back_to_arbitrage_keyboard,
    get_settings_keyboard, get_language_keyboard
)
from src.utils.api_error_handling import APIError, handle_response, retry_request
from src.utils.dmarket_api_utils import execute_api_request
# Обработчики для автоматического арбитража
from src.telegram_bot.auto_arbitrage import start_auto_trading, stop_auto_trading, show_auto_stats
# Обработчики для фильтров по играм
from src.telegram_bot.game_filter_handlers import (
    handle_game_filters, handle_filter_callback, handle_price_range_callback,
    handle_float_range_callback, handle_set_category_callback, 
    handle_set_rarity_callback, handle_set_exterior_callback,
    handle_set_hero_callback, handle_set_class_callback,
    handle_select_game_filter_callback, handle_back_to_filters_callback
)

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из локального .env файла
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
logger.info(f"Загружен токен из {env_path}: {TOKEN}")

# Поддерживаемые языки
LANGUAGES = {
    "ru": "Русский",
    "en": "English",
    "es": "Español",
    "de": "Deutsch"
}

# Локализованные строки (базовый русский язык)
LOCALIZATIONS = {
    "ru": {
        "welcome": "Привет, {user}! 👋\n\nЯ бот для арбитража DMarket. Помогу найти выгодные сделки.\n\nИспользуйте меню для выбора желаемой операции:",
        "help": "Доступные команды:\n\n/start - Начать работу с ботом\n/arbitrage - Открыть меню арбитража\n/dmarket - Проверить статус DMarket API\n/settings - Настройки профиля\n/help - Показать эту справку",
        "select_mode": "📊 Выберите режим арбитража:",
        "checking_api": "🔍 Проверяю статус DMarket API...",
        "api_ok": "✅ API работает нормально.\n\n🕒 Последнее обновление: только что",
        "settings": "⚙️ Настройки профиля",
        "language": "🌐 Текущий язык: {lang}\n\nВыберите язык интерфейса:",
        "language_set": "✅ Язык установлен: {lang}",
        "balance": "💰 Баланс: ${balance:.2f}",
        "insufficient_balance": "⚠️ Недостаточно средств: ${balance:.2f}"
    },
    "en": {
        "welcome": "Hello, {user}! 👋\n\nI'm a DMarket arbitrage bot. I'll help you find profitable deals.\n\nUse the menu to select your desired operation:",
        "help": "Available commands:\n\n/start - Start working with the bot\n/arbitrage - Open arbitrage menu\n/dmarket - Check DMarket API status\n/settings - Profile settings\n/help - Show this help",
        "select_mode": "📊 Select arbitrage mode:",
        "checking_api": "🔍 Checking DMarket API status...",
        "api_ok": "✅ API is working normally.\n\n🕒 Last update: just now",
        "settings": "⚙️ Profile settings",
        "language": "🌐 Current language: {lang}\n\nSelect interface language:",
        "language_set": "✅ Language set to: {lang}",
        "balance": "💰 Balance: ${balance:.2f}",
        "insufficient_balance": "⚠️ Insufficient balance: ${balance:.2f}"
    }
}

# Кэш пользовательских профилей
USER_PROFILES = {}
USER_PROFILES_FILE = os.path.join(os.path.dirname(__file__), "user_profiles.json")

def save_user_profiles():
    """Сохраняет профили пользователей в файл"""
    try:
        with open(USER_PROFILES_FILE, 'w', encoding='utf-8') as f:
            json.dump(USER_PROFILES, f, ensure_ascii=False, indent=2)
        logger.info(f"Сохранено {len(USER_PROFILES)} пользовательских профилей")
    except Exception as e:
        logger.error(f"Ошибка при сохранении профилей: {str(e)}")

def load_user_profiles():
    """Загружает профили пользователей из файла"""
    global USER_PROFILES
    try:
        if os.path.exists(USER_PROFILES_FILE):
            with open(USER_PROFILES_FILE, 'r', encoding='utf-8') as f:
                USER_PROFILES = json.load(f)
            logger.info(f"Загружено {len(USER_PROFILES)} пользовательских профилей")
    except Exception as e:
        logger.error(f"Ошибка при загрузке профилей: {str(e)}")
        USER_PROFILES = {}

def get_user_profile(user_id: int) -> Dict:
    """
    Получает профиль пользователя или создает новый.
    
    Args:
        user_id: ID пользователя Telegram
        
    Returns:
        Словарь с данными профиля
    """
    user_id_str = str(user_id)
    
    if user_id_str not in USER_PROFILES:
        USER_PROFILES[user_id_str] = {
            "language": "ru",
            "api_key": "",
            "api_secret": "",
            "auto_trading_enabled": False,
            "trade_settings": {
                "min_profit": 2.0,
                "max_price": 50.0,
                "max_trades": 3,
                "risk_level": "medium"
            },
            "last_activity": time.time()
        }
        # Сохраняем новый профиль
        save_user_profiles()
        
    # Обновляем время последней активности
    USER_PROFILES[user_id_str]["last_activity"] = time.time()
    
    return USER_PROFILES[user_id_str]

def get_localized_text(user_id: int, key: str, **kwargs) -> str:
    """
    Получает локализованный текст для пользователя.
    
    Args:
        user_id: ID пользователя Telegram
        key: Ключ локализации
        **kwargs: Дополнительные параметры для форматирования строки
        
    Returns:
        Локализованный текст
    """
    profile = get_user_profile(user_id)
    lang = profile["language"]
    
    # Если язык не поддерживается, используем русский
    if lang not in LOCALIZATIONS:
        lang = "ru"
        
    # Если ключ не найден, ищем в русской локализации
    if key not in LOCALIZATIONS[lang]:
        if key in LOCALIZATIONS["ru"]:
            text = LOCALIZATIONS["ru"][key]
        else:
            text = f"[Missing: {key}]"
    else:
        text = LOCALIZATIONS[lang][key]
        
    # Форматируем строку с переданными параметрами
    if kwargs:
        text = text.format(**kwargs)
        
    return text

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    user_id = user.id
    
    # Получаем локализованное приветствие
    welcome_message = get_localized_text(
        user_id, "welcome", user=user.mention_html()
    )
    
    # Создаем клавиатуру
    keyboard = get_arbitrage_keyboard()
    
    # Отправляем приветственное сообщение с клавиатурой
    await update.message.reply_html(welcome_message, reply_markup=keyboard)


async def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help."""
    user_id = update.effective_user.id
    help_text = get_localized_text(user_id, "help")
    
    await update.message.reply_text(help_text)


async def dmarket_status(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /dmarket для проверки статуса API."""
    # Отправляем начальное сообщение
    message = await update.message.reply_text(
        "🔍 Проверяю статус DMarket API..."
    )
    
    try:
        # Импортируем необходимые модули для проверки API
        from src.dmarket.dmarket_api import DMarketAPI
        from src.utils.rate_limiter import RateLimiter
        
        # Создаем экземпляр лимитера для запросов
        limiter = RateLimiter(is_authorized=False)
        
        # Создаем функцию для запроса к API
        async def check_api_health(**kwargs):
            api = DMarketAPI()
            return await api.ping()
        
        # Выполняем запрос с использованием retry_request
        result = await retry_request(
            check_api_health,
            limiter=limiter,
            endpoint_type="other",
            max_retries=1
        )
        
        # Проверяем результат
        if result and getattr(result, "status", 0) == 200:
            # API работает нормально
            await message.edit_text(
                "✅ API DMarket работает нормально.\n\n"
                "🕒 Последнее обновление: только что\n\n"
                "🔄 Лимиты запросов в норме."
            )
        else:
            # Есть проблемы с API
            await message.edit_text(
                "⚠️ API DMarket отвечает с ошибками.\n\n"
                f"Статус: {getattr(result, 'status', 'неизвестен')}\n"
                "🕒 Последнее обновление: только что"
            )
            
    except Exception as e:
        # Логируем ошибку и информируем пользователя
        logger.error(f"Ошибка при проверке статуса API: {str(e)}")
        await message.edit_text(
            "❌ Ошибка при проверке статуса DMarket API.\n\n"
            f"Ошибка: {str(e)}\n\n"
            "🕒 Последнее обновление: только что"
        )


async def arbitrage_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /arbitrage."""
    keyboard = get_arbitrage_keyboard()
    await update.message.reply_text(
        "📊 Выберите режим арбитража:",
        reply_markup=keyboard
    )


def format_dmarket_results(results: List[Dict], mode: str, game: str) -> str:
    """
    Форматирует результаты арбитража для отображения в сообщении.
    
    Args:
        results: Список результатов арбитража
        mode: Режим арбитража
        game: Код игры
        
    Returns:
        Отформатированный текст с результатами
    """
    mode_display = {
        "boost": "Разгон баланса",
        "mid": "Средний трейдер",
        "pro": "Trade Pro",
        "best": "Лучшие возможности",
        "auto": "Авто-арбитраж"
    }
    
    if not results:
        return (f"{mode_display.get(mode, mode)}: не найдено подходящих "
                f"скинов для {GAMES.get(game, game)}.")
    
    game_name = GAMES.get(game, game)
    header = f"📊 {mode_display.get(mode, mode)} | {game_name}\n\n"
    result_texts = []
    
    for i, item in enumerate(results[:5], start=1):
        name = item.get("title", "Неизвестный предмет")
        buy_price = item.get("price", {}).get("amount", "0")
        profit = item.get("profit", 0)
        
        # Цены обычно в центах
        buy_price_usd = float(buy_price) / 100
        profit_usd = float(profit) / 100
        
        result_text = (
            f"{i}. {name}\n"
            f"   💵 Цена: ${buy_price_usd:.2f}\n"
            f"   💰 Прибыль: ${profit_usd:.2f}\n"
        )
        result_texts.append(result_text)
    
    if len(results) > 5:
        result_texts.append(f"... и еще {len(results) - 5} предметов")
    
    return header + "\n".join(result_texts)


def format_best_opportunities(opportunities: List[Dict], game: str) -> str:
    """
    Форматирует лучшие арбитражные возможности для отображения.
    
    Args:
        opportunities: Список лучших арбитражных возможностей
        game: Код игры
        
    Returns:
        Отформатированный текст с результатами
    """
    if not opportunities:
        return f"Не найдено подходящих арбитражных возможностей для {GAMES.get(game, game)}."
    
    game_name = GAMES.get(game, game)
    header = f"🌟 Лучшие арбитражные возможности | {game_name}\n\n"
    result_texts = []
    
    for i, opp in enumerate(opportunities[:10], start=1):
        name = opp.get("title", "Неизвестный предмет")
        buy_price = float(opp.get("buyPrice", 0)) / 100  # Цены обычно в центах
        sell_price = float(opp.get("sellPrice", 0)) / 100
        profit_amount = float(opp.get("profit", 0)) / 100
        profit_percentage = opp.get("profitPercent", 0)
        
        result_text = (
            f"{i}. {name}\n"
            f"   💵 Купить: ${buy_price:.2f}\n"
            f"   💸 Продать: ${sell_price:.2f}\n"
            f"   💰 Прибыль: ${profit_amount:.2f} ({profit_percentage:.1f}%)\n"
        )
        result_texts.append(result_text)
    
    return header + "\n".join(result_texts)


async def arbitrage_callback(update: Update, context: CallbackContext) -> None:
    """Обработчик callback-запросов."""
    query = update.callback_query
    await query.answer()
    
    # Получаем callback_data
    data = query.data
    
    # Обрабатываем различные callback-запросы
    if data == "arbitrage":
        # Показываем меню арбитража
        keyboard = get_arbitrage_keyboard()
        await query.edit_message_text(
            text="📊 Выберите режим арбитража:",
            reply_markup=keyboard
        )
    elif data == "arbitrage_boost":
        # Разгон баланса
        await handle_dmarket_arbitrage(query, context, "boost")
    elif data == "arbitrage_mid":
        # Средний трейдер
        await handle_dmarket_arbitrage(query, context, "mid")
    elif data == "arbitrage_pro":
        # Trade Pro
        await handle_dmarket_arbitrage(query, context, "pro")
    elif data == "best_opportunities":
        # Лучшие возможности
        await handle_best_opportunities(query, context)
    elif data == "select_game":
        # Выбор игры
        keyboard = get_game_selection_keyboard()
        await query.edit_message_text(
            text="🎮 Выберите игру:",
            reply_markup=keyboard
        )
    elif data.startswith("game:"):
        # Обработка выбора игры
        game = data.split(":")[1]
        # Сохраняем выбранную игру в контексте пользователя
        if not hasattr(context, 'user_data'):
            context.user_data = {}
        context.user_data["current_game"] = game
          # Возвращаемся в меню арбитража
        keyboard = get_arbitrage_keyboard()
        await query.edit_message_text(
            text=f"🎮 Выбрана игра: {GAMES.get(game, game)}\n\n📊 Выберите режим арбитража:",
            reply_markup=keyboard
        )
    elif data == "auto_arbitrage":
        # Показываем меню автоматического арбитража
        keyboard = get_auto_arbitrage_keyboard()
        await query.edit_message_text(
            text="🤖 Выберите режим автоматического арбитража:",
            reply_markup=keyboard
        )
    elif data.startswith("auto_start:"):
        # Запуск автоматического арбитража в выбранном режиме
        mode = data.split(":")[1]
        # Импортируем функцию здесь, чтобы избежать циклического импорта
        try:
            from src.telegram_bot.auto_arbitrage import start_auto_trading
            await start_auto_trading(query, context, mode)
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Ошибка в auto_start: {str(e)}\n{error_traceback}")
            
            # Показываем подробную информацию об ошибке
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="auto_arbitrage")],
                [InlineKeyboardButton("⬅️ Назад в меню", callback_data="arbitrage")]
            ])
            
            await query.edit_message_text(
                text=f"❌ Произошла ошибка при запуске автоматического арбитража:\n"
                     f"{str(e)}\n\n"
                     f"Пожалуйста, проверьте журнал для получения дополнительной информации.",
                reply_markup=keyboard
            )
    elif data == "auto_stop":
        # Остановка автоматического арбитража
        from src.telegram_bot.auto_arbitrage import stop_auto_trading
        await stop_auto_trading(query, context)
    elif data == "auto_stats":
        # Показать статистику автоматического арбитража
        from src.telegram_bot.auto_arbitrage import show_auto_stats
        await show_auto_stats(query, context)
    elif data.startswith("paginate:"):
        # Обработка пагинации результатов
        parts = data.split(":")
        action = parts[1]  # "next" или "prev"
        mode = parts[2] if len(parts) > 2 else "auto"
        
        # Обрабатываем разные режимы пагинации
        if mode.startswith("auto"):
            # Для автоарбитража используем специальный обработчик
            from src.telegram_bot.auto_arbitrage import show_auto_stats
            await show_auto_stats(query, context)
        else:
            # Для других режимов продолжаем использовать стандартную пагинацию
            from src.telegram_bot.pagination import pagination_manager
              # Получаем идентификатор пользователя для работы с пагинацией
            user_id = query.from_user.id
            
            # В зависимости от действия переходим к следующей или предыдущей странице
            if action == "next":
                items, current_page, total_pages = pagination_manager.next_page(user_id)
            else:  # prev
                items, current_page, total_pages = pagination_manager.prev_page(user_id)
            
        # Получаем текущую игру
        game = "csgo"
        if hasattr(context, 'user_data') and "current_game" in context.user_data:
            game = context.user_data["current_game"]
            
        # Форматируем результаты для отображения
        from src.telegram_bot.pagination import format_paginated_results
        formatted_text = format_paginated_results(
            items, game, mode, current_page, total_pages
        )
        
        # Создаем клавиатуру с кнопками пагинации
        keyboard = []
        
        # Кнопки пагинации
        pagination_row = []
        if current_page > 0:
            pagination_row.append(
                InlineKeyboardButton("⬅️ Предыдущая", callback_data=f"paginate:prev:{mode}")
            )
        
        if current_page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton("Следующая ➡️", callback_data=f"paginate:next:{mode}")
            )
        
        if pagination_row:
            keyboard.append(pagination_row)
        
        # Кнопка назад к меню
        keyboard.append([
            InlineKeyboardButton("⬅️ Назад к меню", callback_data="arbitrage")
        ])
        
        # Отображаем результаты с пагинацией
        await query.edit_message_text(
            text=formatted_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    elif data == "back_to_menu":
        # Возврат в главное меню
        await query.edit_message_text(
            text="Выберите действие с помощью команды:\n\n"
                "/arbitrage - Открыть меню арбитража\n"
                "/dmarket - Проверить статус DMarket API\n"
                "/help - Показать справку"
        )
    else:
        # Неизвестный callback-запрос
        await query.edit_message_text(
            text=f"⚠️ Неизвестная команда: {data}"
        )


async def handle_dmarket_arbitrage(query, context: CallbackContext, mode: str) -> None:
    """
    Обрабатывает запрос на поиск арбитражных возможностей на DMarket.
    
    Args:
        query: Объект callback-запроса
        context: Контекст бота
        mode: Режим арбитража ("boost", "mid", "pro")
    """
    # Получаем текущую выбранную игру или используем CSGO по умолчанию
    game = "csgo"
    if hasattr(context, 'user_data') and "current_game" in context.user_data:
        game = context.user_data["current_game"]
    
    # Сохраняем последний режим арбитража
    if not hasattr(context, 'user_data'):
        context.user_data = {}
    context.user_data["last_arbitrage_mode"] = mode
    
    # Словарь для отображения названий режимов
    mode_display = {
        "boost": "Разгон баланса",
        "mid": "Средний трейдер",
        "pro": "Trade Pro"
    }
    
    # Показываем сообщение о процессе поиска
    await query.edit_message_text(
        text=f"🔍 Поиск арбитражных возможностей ({mode_display.get(mode, mode)}) "
             f"для игры {GAMES.get(game, game)}...",
        reply_markup=None,
        parse_mode='HTML'
    )
    
    try:
        # Настраиваем функцию запроса с использованием execute_api_request
        async def get_arbitrage_data():
            if mode == "boost":
                return await arbitrage_boost_async(game)
            elif mode == "pro":
                return await arbitrage_pro_async(game)
            else:  # mid
                return await arbitrage_mid_async(game)
        
        # Выполняем запрос через утилиту для обработки ошибок API
        results = await execute_api_request(
            request_func=get_arbitrage_data,
            endpoint_type="market",  # Используем рыночную категорию для лимита
            max_retries=2  # Сократим количество повторных попыток для быстрого ответа
        )
            
        # Если результаты есть, сохраняем их для пагинации
        if results:
            # Импортируем менеджер пагинации
            from src.telegram_bot.pagination import pagination_manager
            
            # Сохраняем результаты в менеджере пагинации
            user_id = query.from_user.id
            pagination_manager.add_items_for_user(user_id, results, mode)
            
            # Получаем первую страницу
            page_items, current_page, total_pages = pagination_manager.get_page(user_id)
                  # Форматируем результаты для отображения с пагинацией
            from src.telegram_bot.pagination import format_paginated_results
            formatted_text = format_paginated_results(
                page_items, game, mode, current_page, total_pages
            )
            
            # Создаем клавиатуру с пагинацией, если страниц больше одной
            keyboard = []
            
            # Кнопки пагинации
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
            
            # Добавляем кнопки основного меню
            arbitrage_keyboard = get_arbitrage_keyboard().inline_keyboard
            keyboard.extend(arbitrage_keyboard)
            
            # Отображаем результаты с пагинацией
            await query.edit_message_text(
                text=formatted_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        else:
            # Если нет результатов
            formatted_text = format_dmarket_results(results, mode, game)
            keyboard = get_arbitrage_keyboard()
            await query.edit_message_text(
                text=formatted_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
    except APIError as e:
        # Обработка ошибок API DMarket
        logger.error(f"Ошибка API при поиске арбитражных возможностей: {e.message}")
        
        # Формируем понятное сообщение об ошибке для пользователя
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
        logger.error(f"Ошибка при поиске арбитражных возможностей: {str(e)}")
        # Показываем сообщение об ошибке
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="arbitrage")]
        ])
        error_message = f"❌ Неожиданная ошибка: {str(e)}"
        await query.edit_message_text(
            text=error_message, 
            reply_markup=keyboard, 
            parse_mode='HTML'
        )


async def handle_best_opportunities(query, context: CallbackContext) -> None:
    """
    Обрабатывает запрос на поиск лучших арбитражных возможностей.
    
    Args:
        query: Объект callback-запроса
        context: Контекст бота
    """
    # Получаем текущую выбранную игру или используем CSGO по умолчанию
    game = "csgo"
    if hasattr(context, 'user_data') and "current_game" in context.user_data:
        game = context.user_data["current_game"]
    
    # Показываем сообщение о процессе поиска
    await query.edit_message_text(
        text=f"🔍 Поиск лучших арбитражных возможностей для {GAMES.get(game, game)}...",
        reply_markup=None
    )
    
    try:
        # Импортируем функцию поиска арбитражных возможностей
        from src.telegram_bot.arbitrage_scanner import find_arbitrage_opportunities
        
        # Находим лучшие арбитражные возможности
        opportunities = find_arbitrage_opportunities(
            game=game,
            min_profit_percentage=5.0,  # Используем небольшой порог, чтобы найти больше возможностей
            max_items=10  # Показываем до 10 лучших возможностей
        )
        
        # Форматируем и показываем результаты
        formatted_text = format_best_opportunities(opportunities, game)
        keyboard = get_arbitrage_keyboard()
        await query.edit_message_text(
            text=formatted_text,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при поиске лучших арбитражных возможностей: {str(e)}")
        # Показываем сообщение об ошибке
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="arbitrage")]
        ])
        error_message = f"❌ Ошибка при поиске лучших арбитражных возможностей: {str(e)}"
        await query.edit_message_text(text=error_message, reply_markup=keyboard)


async def error_handler(update: Optional[Update], context: CallbackContext) -> None:
    """Обработчик ошибок."""
    error = context.error
    logger.error(f"Ошибка: {error}")
    
    # Обрабатываем разные типы ошибок
    error_message = "😔 Произошла ошибка при обработке вашего запроса. Попробуйте позже."
    
    # Проверяем, является ли ошибка APIError из нашего модуля api_error_handling
    if isinstance(error, APIError):
        # Разные сообщения для разных типов API-ошибок
        if error.status_code == 429:  # RateLimitExceeded
            error_message = "⏱️ Превышен лимит запросов к DMarket API. Пожалуйста, подождите несколько минут."
        elif error.status_code == 401:  # AuthenticationError
            error_message = "🔑 Ошибка авторизации в DMarket API. Проверьте API-ключи в настройках."
        elif error.status_code == 404:  # NotFoundError
            error_message = "🔍 Запрашиваемый ресурс не найден в DMarket."
        elif error.status_code >= 500:  # ServerError
            error_message = "🛑 Серверная ошибка DMarket API. Пожалуйста, попробуйте позже."
        else:
            # Для других ошибок API используем сообщение из исключения
            error_message = f"❌ Ошибка DMarket API: {error.message}"
    
    # Отправляем сообщение пользователю, если возможно
    if update and update.effective_message:
        await update.effective_message.reply_text(error_message)


def main() -> None:
    """Запускает бота."""
    try:
        if TOKEN is None or TOKEN == "YOUR_TOKEN_HERE":
            logger.error("Токен бота не настроен! Укажите TELEGRAM_BOT_TOKEN в .env файле")
            return
        
        # Создаем приложение и добавляем обработчики
        application = Application.builder().token(TOKEN).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("dmarket", dmarket_status))
        application.add_handler(CommandHandler("arbitrage", arbitrage_command))
        application.add_handler(CommandHandler("filters", handle_game_filters))
        
        # Добавляем обработчики callback-запросов для основного меню
        application.add_handler(CallbackQueryHandler(arbitrage_callback, pattern=r"^(?!filter:|price_range:|float_range:|set_|back_to_filters:|select_game)"))
        
        # Добавляем обработчики callback-запросов для фильтрации
        application.add_handler(CallbackQueryHandler(handle_filter_callback, pattern=r"^filter:"))
        application.add_handler(CallbackQueryHandler(handle_price_range_callback, pattern=r"^price_range:"))
        application.add_handler(CallbackQueryHandler(handle_float_range_callback, pattern=r"^float_range:"))
        application.add_handler(CallbackQueryHandler(handle_set_category_callback, pattern=r"^set_category:"))
        application.add_handler(CallbackQueryHandler(handle_set_rarity_callback, pattern=r"^set_rarity:"))
        application.add_handler(CallbackQueryHandler(handle_set_exterior_callback, pattern=r"^set_exterior:"))
        application.add_handler(CallbackQueryHandler(handle_set_hero_callback, pattern=r"^set_hero:"))
        application.add_handler(CallbackQueryHandler(handle_set_class_callback, pattern=r"^set_class:"))
        application.add_handler(CallbackQueryHandler(handle_select_game_filter_callback, pattern=r"^select_game_filter:"))
        application.add_handler(CallbackQueryHandler(handle_back_to_filters_callback, pattern=r"^back_to_filters:"))
        
        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)
        
        # Запускаем бота
        logger.info("Бот запущен")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {str(e)}")


if __name__ == '__main__':
    # Загружаем профили пользователей при старте
    load_user_profiles()
    
    main()
