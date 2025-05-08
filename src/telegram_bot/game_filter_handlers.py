"""
Модуль для обработки фильтров игр в Telegram боте.

Предоставляет обработчики для работы с фильтрами предметов в разных играх
через интерфейс Telegram бота.

Документация Telegram Bot API: https://core.telegram.org/bots/api
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union, Tuple

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    CallbackQuery
)
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters
)

from src.dmarket.game_filters import (
    get_csgo_filters,
    get_dota2_filters,
    get_rust_filters,
    apply_filters_to_query
)
from src.telegram_bot.keyboards import (
    get_games_keyboard,
    get_filter_keyboard,
    get_csgo_exterior_keyboard,
    get_csgo_weapon_type_keyboard,
    get_rarity_keyboard,
    get_price_range_keyboard,
    get_pagination_keyboard
)

# Настройка логирования
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(
    SELECT_GAME,
    APPLY_FILTERS,
    SET_PRICE_RANGE,
    SET_WEAPON_TYPE,
    SET_EXTERIOR,
    SET_RARITY,
    SET_COLLECTION,
    SET_HERO,
    SET_SLOT,
    SET_TOURNAMENT,
    SET_CUSTOM_FILTER,
    SEARCH_BY_NAME
) = range(12)

# Каталог для хранения пользовательских фильтров
USER_FILTERS_DIR = Path(__file__).parents[2] / "data" / "user_filters"
# Создаем директорию, если её нет
USER_FILTERS_DIR.mkdir(parents=True, exist_ok=True)

# Словарь с активными фильтрами пользователей
# Формат: {user_id: {game: {filter_name: filter_value}}}
_user_filters = {}


def get_user_filters_file(user_id: int) -> Path:
    """Возвращает путь к файлу с фильтрами пользователя."""
    return USER_FILTERS_DIR / f"user_{user_id}_filters.json"


def load_user_filters(user_id: int) -> Dict[str, Dict[str, Any]]:
    """
    Загружает сохраненные фильтры пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        
    Returns:
        Словарь с фильтрами пользователя по играм
    """
    filters_file = get_user_filters_file(user_id)
    
    if filters_file.exists():
        try:
            with open(filters_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке фильтров пользователя {user_id}: {e}")
    
    # Если файл не существует или произошла ошибка, возвращаем пустой словарь
    return {}


def save_user_filters(user_id: int, filters_data: Dict[str, Dict[str, Any]]) -> None:
    """
    Сохраняет фильтры пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        filters_data: Словарь с фильтрами пользователя по играм
    """
    filters_file = get_user_filters_file(user_id)
    
    try:
        with open(filters_file, "w", encoding="utf-8") as f:
            json.dump(filters_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка при сохранении фильтров пользователя {user_id}: {e}")


def get_active_filters(user_id: int, game: str) -> Dict[str, Any]:
    """
    Возвращает активные фильтры пользователя для указанной игры.
    
    Args:
        user_id: ID пользователя в Telegram
        game: Код игры (csgo, dota2, rust, tf2)
        
    Returns:
        Словарь с активными фильтрами
    """
    global _user_filters
    
    # Если фильтры пользователя еще не загружены, загружаем их
    if user_id not in _user_filters:
        _user_filters[user_id] = load_user_filters(user_id)
    
    # Если фильтры для игры не инициализированы, создаем пустой словарь
    if game not in _user_filters[user_id]:
        _user_filters[user_id][game] = {}
    
    return _user_filters[user_id][game]


def update_filter(user_id: int, game: str, filter_name: str, filter_value: Any) -> None:
    """
    Обновляет фильтр пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        game: Код игры (csgo, dota2, rust, tf2)
        filter_name: Имя фильтра
        filter_value: Значение фильтра
    """
    global _user_filters
    
    # Получаем текущие фильтры
    filters_data = get_active_filters(user_id, game)
    
    # Обновляем фильтр
    filters_data[filter_name] = filter_value
    
    # Сохраняем обновленные фильтры
    _user_filters[user_id][game] = filters_data
    save_user_filters(user_id, _user_filters[user_id])


def reset_filters(user_id: int, game: str) -> None:
    """
    Сбрасывает фильтры пользователя для указанной игры.
    
    Args:
        user_id: ID пользователя в Telegram
        game: Код игры (csgo, dota2, rust, tf2)
    """
    global _user_filters
    
    # Очищаем фильтры для игры
    if user_id in _user_filters and game in _user_filters[user_id]:
        _user_filters[user_id][game] = {}
        save_user_filters(user_id, _user_filters[user_id])


def format_filters_summary(filters_data: Dict[str, Any], game: str) -> str:
    """
    Форматирует сводку активных фильтров для отображения пользователю.
    
    Args:
        filters_data: Словарь с фильтрами
        game: Код игры (csgo, dota2, rust, tf2)
        
    Returns:
        Отформатированная строка с фильтрами
    """
    if not filters_data:
        return "🔍 Фильтры не установлены"
    
    summary = "🔍 Активные фильтры:\n"
    
    # Форматирование разных типов фильтров
    for filter_name, filter_value in filters_data.items():
        if filter_name == "price_range":
            min_price, max_price = filter_value
            summary += f"💰 Цена: ${min_price} - ${max_price}\n"
        elif filter_name == "exterior" and game == "csgo":
            summary += f"✨ Внешний вид: {filter_value}\n"
        elif filter_name == "weapon_type" and game == "csgo":
            summary += f"🔫 Тип оружия: {filter_value}\n"
        elif filter_name == "rarity":
            summary += f"🎨 Редкость: {filter_value}\n"
        elif filter_name == "search_query":
            summary += f"🔍 Поиск: {filter_value}\n"
        # Добавьте обработку других типов фильтров по необходимости
    
    return summary


# Обработчики для фильтров

async def start_filters(update: Update, context: CallbackContext) -> int:
    """
    Начинает процесс настройки фильтров.
    Показывает список доступных игр.
    """
    query = update.callback_query
    if query:
        await query.answer()
    
    # Показываем клавиатуру выбора игры
    keyboard = get_games_keyboard(callback_prefix="filter_game")
    
    # Если это новое сообщение
    if update.message:
        await update.message.reply_text(
            "🎮 Выберите игру для настройки фильтров:",
            reply_markup=keyboard
        )
    # Если это ответ на колбэк
    elif query:
        await query.edit_message_text(
            "🎮 Выберите игру для настройки фильтров:",
            reply_markup=keyboard
        )
    
    return SELECT_GAME


async def select_game(update: Update, context: CallbackContext) -> int:
    """Обрабатывает выбор игры для фильтров."""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем выбранную игру из callback_data
    game = query.data.split("_")[-1]
    
    # Сохраняем выбранную игру в контексте
    context.user_data["selected_game"] = game
    
    # Получаем активные фильтры пользователя
    user_id = update.effective_user.id
    filters_data = get_active_filters(user_id, game)
    
    # Формируем сводку активных фильтров
    filters_summary = format_filters_summary(filters_data, game)
    
    # Показываем клавиатуру с фильтрами для выбранной игры
    keyboard = get_filter_keyboard(game)
    
    await query.edit_message_text(
        f"🎮 Настройка фильтров для {game.upper()}\n\n{filters_summary}",
        reply_markup=keyboard
    )
    
    return APPLY_FILTERS


async def handle_filter_selection(update: Update, context: CallbackContext) -> int:
    """Обрабатывает выбор конкретного фильтра."""
    query = update.callback_query
    await query.answer()
    
    # Разбираем callback_data
    # Формат: filter_GAME_FILTER_TYPE
    parts = query.data.split("_")
    game = parts[1]
    filter_type = parts[2]
    
    # Сохраняем тип фильтра в контексте
    context.user_data["filter_type"] = filter_type
    
    # Обрабатываем разные типы фильтров
    if filter_type == "price":
        # Показываем клавиатуру для выбора ценового диапазона
        keyboard = get_price_range_keyboard()
        await query.edit_message_text(
            "💰 Выберите ценовой диапазон:",
            reply_markup=keyboard
        )
        return SET_PRICE_RANGE
        
    elif filter_type == "weapon_type" and game == "csgo":
        # Показываем клавиатуру для выбора типа оружия
        keyboard = get_csgo_weapon_type_keyboard()
        await query.edit_message_text(
            "🔫 Выберите тип оружия:",
            reply_markup=keyboard
        )
        return SET_WEAPON_TYPE
        
    elif filter_type == "exterior" and game == "csgo":
        # Показываем клавиатуру для выбора внешнего вида
        keyboard = get_csgo_exterior_keyboard()
        await query.edit_message_text(
            "✨ Выберите внешний вид:",
            reply_markup=keyboard
        )
        return SET_EXTERIOR
        
    elif filter_type == "rarity":
        # Показываем клавиатуру для выбора редкости
        keyboard = get_rarity_keyboard(game)
        await query.edit_message_text(
            "🎨 Выберите редкость предметов:",
            reply_markup=keyboard
        )
        return SET_RARITY
        
    elif filter_type == "search":
        # Запрашиваем поисковый запрос
        await query.edit_message_text(
            "🔍 Введите поисковый запрос для названия предмета:"
        )
        return SEARCH_BY_NAME
        
    elif filter_type == "reset":
        # Сбрасываем фильтры пользователя
        user_id = update.effective_user.id
        reset_filters(user_id, game)
        
        # Показываем обновленную клавиатуру фильтров
        keyboard = get_filter_keyboard(game)
        await query.edit_message_text(
            f"🎮 Настройка фильтров для {game.upper()}\n\n🔍 Фильтры сброшены",
            reply_markup=keyboard
        )
        return APPLY_FILTERS
        
    elif filter_type == "apply":
        # Применяем фильтры и возвращаемся к предыдущему состоянию
        user_id = update.effective_user.id
        filters_data = get_active_filters(user_id, game)
        
        # Формируем сообщение с примененными фильтрами
        filters_summary = format_filters_summary(filters_data, game)
        
        # Возвращаемся к основному меню фильтров
        keyboard = get_filter_keyboard(game)
        await query.edit_message_text(
            f"🎮 Фильтры применены для {game.upper()}\n\n{filters_summary}",
            reply_markup=keyboard
        )
        return APPLY_FILTERS
    
    # По умолчанию возвращаемся к выбору фильтров
    return APPLY_FILTERS


async def handle_price_range(update: Update, context: CallbackContext) -> int:
    """Обрабатывает выбор ценового диапазона."""
    query = update.callback_query
    await query.answer()
    
    # Получаем данные из контекста
    game = context.user_data.get("selected_game", "csgo")
    
    # Обрабатываем случай, когда пользователь хочет вернуться назад
    if query.data == "back_to_filters":
        keyboard = get_filter_keyboard(game)
        
        user_id = update.effective_user.id
        filters_data = get_active_filters(user_id, game)
        filters_summary = format_filters_summary(filters_data, game)
        
        await query.edit_message_text(
            f"🎮 Настройка фильтров для {game.upper()}\n\n{filters_summary}",
            reply_markup=keyboard
        )
        return APPLY_FILTERS
    
    # Обрабатываем случай, когда пользователь выбирает произвольный диапазон
    if query.data == "price_custom":
        await query.edit_message_text(
            "💰 Введите ценовой диапазон в формате:\n"
            "МИН МАКС\n\n"
            "Например: 10 50 (для диапазона от $10 до $50)"
        )
        return SET_PRICE_RANGE
    
    # Обрабатываем выбор предустановленного диапазона
    # Формат: price_MIN_MAX
    parts = query.data.split("_")
    if len(parts) == 3 and parts[0] == "price":
        try:
            min_price = float(parts[1])
            max_price = float(parts[2])
            
            # Сохраняем ценовой диапазон в фильтрах пользователя
            user_id = update.effective_user.id
            update_filter(user_id, game, "price_range", (min_price, max_price))
            
            # Возвращаемся к меню фильтров
            keyboard = get_filter_keyboard(game)
            
            filters_data = get_active_filters(user_id, game)
            filters_summary = format_filters_summary(filters_data, game)
            
            await query.edit_message_text(
                f"🎮 Настройка фильтров для {game.upper()}\n\n"
                f"💰 Установлен ценовой диапазон: ${min_price} - ${max_price}\n\n"
                f"{filters_summary}",
                reply_markup=keyboard
            )
            return APPLY_FILTERS
            
        except (ValueError, IndexError):
            # В случае ошибки показываем сообщение об ошибке
            await query.edit_message_text(
                "❌ Неверный формат ценового диапазона.\n"
                "Попробуйте еще раз.",
                reply_markup=get_price_range_keyboard()
            )
            return SET_PRICE_RANGE
    
    # По умолчанию остаемся в том же состоянии
    return SET_PRICE_RANGE


async def handle_custom_price_range(update: Update, context: CallbackContext) -> int:
    """Обрабатывает ввод произвольного ценового диапазона."""
    message = update.message.text.strip()
    game = context.user_data.get("selected_game", "csgo")
    
    try:
        # Разбираем введенный диапазон
        parts = message.split()
        if len(parts) != 2:
            raise ValueError("Неверное количество аргументов")
            
        min_price = float(parts[0])
        max_price = float(parts[1])
        
        if min_price < 0 or max_price < 0 or min_price > max_price:
            raise ValueError("Некорректный диапазон")
        
        # Сохраняем ценовой диапазон в фильтрах пользователя
        user_id = update.effective_user.id
        update_filter(user_id, game, "price_range", (min_price, max_price))
        
        # Показываем обновленное меню фильтров
        keyboard = get_filter_keyboard(game)
        
        filters_data = get_active_filters(user_id, game)
        filters_summary = format_filters_summary(filters_data, game)
        
        await update.message.reply_text(
            f"🎮 Настройка фильтров для {game.upper()}\n\n"
            f"💰 Установлен ценовой диапазон: ${min_price} - ${max_price}\n\n"
            f"{filters_summary}",
            reply_markup=keyboard
        )
        return APPLY_FILTERS
        
    except Exception as e:
        logger.error(f"Ошибка при обработке ценового диапазона: {e}")
        
        # В случае ошибки показываем сообщение об ошибке
        await update.message.reply_text(
            "❌ Неверный формат ценового диапазона.\n"
            "Введите два числа через пробел (минимум и максимум).\n"
            "Например: 10 50",
        )
        return SET_PRICE_RANGE


async def handle_weapon_type(update: Update, context: CallbackContext) -> int:
    """Обрабатывает выбор типа оружия для CS:GO."""
    query = update.callback_query
    await query.answer()
    
    game = context.user_data.get("selected_game", "csgo")
    
    # Обрабатываем случай, когда пользователь хочет вернуться назад
    if query.data == "back_to_csgo_filters":
        keyboard = get_filter_keyboard(game)
        
        user_id = update.effective_user.id
        filters_data = get_active_filters(user_id, game)
        filters_summary = format_filters_summary(filters_data, game)
        
        await query.edit_message_text(
            f"🎮 Настройка фильтров для {game.upper()}\n\n{filters_summary}",
            reply_markup=keyboard
        )
        return APPLY_FILTERS
    
    # Обрабатываем выбор типа оружия
    # Формат: weapon_TYPE
    parts = query.data.split("_")
    if len(parts) >= 2 and parts[0] == "weapon":
        weapon_type = parts[1]
        
        # Сохраняем тип оружия в фильтрах пользователя
        user_id = update.effective_user.id
        
        if weapon_type == "all":
            # Если выбраны все типы, удаляем фильтр
            filters_data = get_active_filters(user_id, game)
            if "weapon_type" in filters_data:
                del filters_data["weapon_type"]
                _user_filters[user_id][game] = filters_data
                save_user_filters(user_id, _user_filters[user_id])
        else:
            # Иначе устанавливаем фильтр
            update_filter(user_id, game, "weapon_type", weapon_type)
        
        # Возвращаемся к меню фильтров
        keyboard = get_filter_keyboard(game)
        
        filters_data = get_active_filters(user_id, game)
        filters_summary = format_filters_summary(filters_data, game)
        
        await query.edit_message_text(
            f"🎮 Настройка фильтров для {game.upper()}\n\n{filters_summary}",
            reply_markup=keyboard
        )
        return APPLY_FILTERS
    
    # По умолчанию остаемся в том же состоянии
    return SET_WEAPON_TYPE


async def handle_exterior(update: Update, context: CallbackContext) -> int:
    """Обрабатывает выбор внешнего вида для CS:GO."""
    query = update.callback_query
    await query.answer()
    
    game = context.user_data.get("selected_game", "csgo")
    
    # Обрабатываем случай, когда пользователь хочет вернуться назад
    if query.data == "back_to_csgo_filters":
        keyboard = get_filter_keyboard(game)
        
        user_id = update.effective_user.id
        filters_data = get_active_filters(user_id, game)
        filters_summary = format_filters_summary(filters_data, game)
        
        await query.edit_message_text(
            f"🎮 Настройка фильтров для {game.upper()}\n\n{filters_summary}",
            reply_markup=keyboard
        )
        return APPLY_FILTERS
    
    # Обрабатываем выбор внешнего вида
    # Формат: exterior_TYPE
    parts = query.data.split("_")
    if len(parts) >= 2 and parts[0] == "exterior":
        exterior = parts[1]
        
        # Сохраняем внешний вид в фильтрах пользователя
        user_id = update.effective_user.id
        
        if exterior == "all":
            # Если выбраны все типы, удаляем фильтр
            filters_data = get_active_filters(user_id, game)
            if "exterior" in filters_data:
                del filters_data["exterior"]
                _user_filters[user_id][game] = filters_data
                save_user_filters(user_id, _user_filters[user_id])
        else:
            # Иначе устанавливаем фильтр
            update_filter(user_id, game, "exterior", exterior)
        
        # Возвращаемся к меню фильтров
        keyboard = get_filter_keyboard(game)
        
        filters_data = get_active_filters(user_id, game)
        filters_summary = format_filters_summary(filters_data, game)
        
        await query.edit_message_text(
            f"🎮 Настройка фильтров для {game.upper()}\n\n{filters_summary}",
            reply_markup=keyboard
        )
        return APPLY_FILTERS
    
    # По умолчанию остаемся в том же состоянии
    return SET_EXTERIOR


async def handle_rarity(update: Update, context: CallbackContext) -> int:
    """Обрабатывает выбор редкости предметов."""
    query = update.callback_query
    await query.answer()
    
    game = context.user_data.get("selected_game", "csgo")
    
    # Обрабатываем случай, когда пользователь хочет вернуться назад
    if query.data.startswith("back_to_"):
        keyboard = get_filter_keyboard(game)
        
        user_id = update.effective_user.id
        filters_data = get_active_filters(user_id, game)
        filters_summary = format_filters_summary(filters_data, game)
        
        await query.edit_message_text(
            f"🎮 Настройка фильтров для {game.upper()}\n\n{filters_summary}",
            reply_markup=keyboard
        )
        return APPLY_FILTERS
    
    # Обрабатываем выбор редкости
    # Формат: rarity_TYPE
    parts = query.data.split("_")
    if len(parts) >= 2 and parts[0] == "rarity":
        rarity = parts[1]
        
        # Сохраняем редкость в фильтрах пользователя
        user_id = update.effective_user.id
        
        if rarity == "all":
            # Если выбраны все типы, удаляем фильтр
            filters_data = get_active_filters(user_id, game)
            if "rarity" in filters_data:
                del filters_data["rarity"]
                _user_filters[user_id][game] = filters_data
                save_user_filters(user_id, _user_filters[user_id])
        else:
            # Иначе устанавливаем фильтр
            update_filter(user_id, game, "rarity", rarity)
        
        # Возвращаемся к меню фильтров
        keyboard = get_filter_keyboard(game)
        
        filters_data = get_active_filters(user_id, game)
        filters_summary = format_filters_summary(filters_data, game)
        
        await query.edit_message_text(
            f"🎮 Настройка фильтров для {game.upper()}\n\n{filters_summary}",
            reply_markup=keyboard
        )
        return APPLY_FILTERS
    
    # По умолчанию остаемся в том же состоянии
    return SET_RARITY


async def handle_search_query(update: Update, context: CallbackContext) -> int:
    """Обрабатывает ввод поискового запроса для названия предмета."""
    message = update.message.text.strip()
    game = context.user_data.get("selected_game", "csgo")
    
    if not message:
        await update.message.reply_text(
            "❌ Поисковый запрос не может быть пустым.\n"
            "Введите часть названия предмета для поиска:"
        )
        return SEARCH_BY_NAME
    
    # Сохраняем поисковый запрос в фильтрах пользователя
    user_id = update.effective_user.id
    update_filter(user_id, game, "search_query", message)
    
    # Показываем обновленное меню фильтров
    keyboard = get_filter_keyboard(game)
    
    filters_data = get_active_filters(user_id, game)
    filters_summary = format_filters_summary(filters_data, game)
    
    await update.message.reply_text(
        f"🎮 Настройка фильтров для {game.upper()}\n\n"
        f"🔍 Установлен поисковый запрос: {message}\n\n"
        f"{filters_summary}",
        reply_markup=keyboard
    )
    return APPLY_FILTERS


async def cancel_filters(update: Update, context: CallbackContext) -> int:
    """Отменяет настройку фильтров и возвращается в главное меню."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "❌ Настройка фильтров отменена."
        )
    else:
        await update.message.reply_text(
            "❌ Настройка фильтров отменена."
        )
    
    return ConversationHandler.END


# Создание обработчика фильтров
def get_filters_conversation_handler() -> ConversationHandler:
    """Создает и возвращает ConversationHandler для настройки фильтров."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("filters", start_filters),
            CallbackQueryHandler(start_filters, pattern="^filters$")
        ],
        states={
            SELECT_GAME: [
                CallbackQueryHandler(select_game, pattern="^filter_game_")
            ],
            APPLY_FILTERS: [
                CallbackQueryHandler(handle_filter_selection, pattern="^filter_"),
                CallbackQueryHandler(start_filters, pattern="^back_to_games$"),
                CallbackQueryHandler(cancel_filters, pattern="^back_to_main$")
            ],
            SET_PRICE_RANGE: [
                CallbackQueryHandler(handle_price_range, pattern="^(price_|back_to_filters)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_price_range)
            ],
            SET_WEAPON_TYPE: [
                CallbackQueryHandler(handle_weapon_type, pattern="^(weapon_|back_to_csgo_filters)")
            ],
            SET_EXTERIOR: [
                CallbackQueryHandler(handle_exterior, pattern="^(exterior_|back_to_csgo_filters)")
            ],
            SET_RARITY: [
                CallbackQueryHandler(handle_rarity, pattern="^(rarity_|back_to_)")
            ],
            SEARCH_BY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_query)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_filters),
            CallbackQueryHandler(cancel_filters, pattern="^cancel$")
        ],
        name="filters_conversation",
        persistent=False
    )
