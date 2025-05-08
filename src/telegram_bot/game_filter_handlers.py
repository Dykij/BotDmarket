"""
Модуль для обработки фильтров игровых предметов.

Предоставляет обработчики для настройки и применения фильтров для разных игр:
- CS2/CSGO: качество, редкость, внешний вид, диапазоны float и цены
- Dota 2: герой, редкость, слот, качество
- Team Fortress 2: класс, качество, тип, эффект
- Rust: категория, тип, редкость
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple, cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, CallbackQuery
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

# Import filters from DMarket
from src.dmarket.game_filters import (
    FilterFactory,
    CS2Filter,
    Dota2Filter,
    TF2Filter,
    RustFilter,
)

# Logger
logger = logging.getLogger(__name__)

# Константы для фильтров

# CS2/CSGO константы
CS2_CATEGORIES = [
    "Pistol", "SMG", "Rifle", "Sniper Rifle", "Shotgun", 
    "Machinegun", "Knife", "Gloves", "Sticker", "Agent", "Case"
]

CS2_RARITIES = [
    "Consumer Grade", "Industrial Grade", "Mil-Spec Grade", 
    "Restricted", "Classified", "Covert", "Contraband"
]

CS2_EXTERIORS = [
    "Factory New", "Minimal Wear", "Field-Tested", 
    "Well-Worn", "Battle-Scarred"
]

# Dota 2 константы
DOTA2_HEROES = [
    "Axe", "Anti-Mage", "Crystal Maiden", "Drow Ranger", "Juggernaut", 
    "Pudge", "Lina", "Lion", "Sven", "Tiny", "Invoker", "Shadow Fiend"
    # Сокращено для примера
]

DOTA2_RARITIES = [
    "Common", "Uncommon", "Rare", "Mythical", 
    "Legendary", "Immortal", "Arcana"
]

DOTA2_SLOTS = [
    "Weapon", "Head", "Back", "Arms", "Shoulder", 
    "Belt", "Misc", "Taunt", "Courier", "Ward"
]

# TF2 константы
TF2_CLASSES = [
    "Scout", "Soldier", "Pyro", "Demoman", 
    "Heavy", "Engineer", "Medic", "Sniper", "Spy", "All Classes"
]

TF2_QUALITIES = [
    "Normal", "Unique", "Vintage", "Genuine", 
    "Strange", "Unusual", "Haunted", "Collectors"
]

TF2_TYPES = [
    "Hat", "Weapon", "Cosmetic", "Action", "Tool", "Taunt", "Crate", "Key"
]

# Rust константы
RUST_CATEGORIES = [
    "Weapon", "Clothing", "Tool", "Construction", "Misc"
]

RUST_TYPES = [
    "Assault Rifle", "Pistol", "Shotgun", "SMG", "Jacket", 
    "Pants", "Helmet", "Boots", "Gloves", "Door", "Box"
]

RUST_RARITIES = [
    "Common", "Uncommon", "Rare", "Epic", "Legendary"
]

# Значения по умолчанию для пользовательских фильтров
DEFAULT_FILTERS = {
    "csgo": {
        "min_price": 1.0,
        "max_price": 1000.0,
        "float_min": 0.0,
        "float_max": 1.0,
        "category": None,
        "rarity": None,
        "exterior": None,
        "stattrak": False,
        "souvenir": False
    },
    "dota2": {
        "min_price": 1.0,
        "max_price": 1000.0,
        "hero": None,
        "rarity": None,
        "slot": None,
        "quality": None,
        "tradable": True
    },
    "tf2": {
        "min_price": 1.0,
        "max_price": 1000.0,
        "class": None,
        "quality": None,
        "type": None,
        "effect": None,
        "killstreak": None,
        "australium": False
    },
    "rust": {
        "min_price": 1.0,
        "max_price": 1000.0,
        "category": None,
        "type": None,
        "rarity": None
    }
}

# Функции для работы с фильтрами

def get_current_filters(context: CallbackContext, game: str) -> Dict[str, Any]:
    """
    Получает текущие фильтры для игры из контекста пользователя.
    
    Args:
        context: Контекст обратного вызова
        game: Код игры (csgo, dota2, tf2, rust)
        
    Returns:
        Словарь с текущими фильтрами
    """
    # Получаем user_data из контекста
    user_data = context.user_data
    if not user_data:
        return DEFAULT_FILTERS.get(game, {}).copy()
    
    # Получаем фильтры из user_data
    filters = user_data.get("filters", {})
    game_filters = filters.get(game, {})
    
    # Если фильтры для данной игры не определены, используем значения по умолчанию
    if not game_filters:
        return DEFAULT_FILTERS.get(game, {}).copy()
    
    return game_filters.copy()

def update_filters(context: CallbackContext, game: str, new_filters: Dict[str, Any]) -> None:
    """
    Обновляет фильтры для игры в контексте пользователя.
    
    Args:
        context: Контекст обратного вызова
        game: Код игры (csgo, dota2, tf2, rust)
        new_filters: Новые значения фильтров
    """
    # Получаем user_data из контекста
    user_data = context.user_data
    if not user_data:
        user_data = {}
        context.user_data = user_data
    
    # Получаем текущие фильтры
    filters = user_data.get("filters", {})
    
    # Если фильтров нет, создаем пустой словарь
    if not filters:
        filters = {}
        user_data["filters"] = filters
    
    # Получаем текущие фильтры для игры
    game_filters = filters.get(game, {})
    
    # Если фильтров для данной игры нет, создаем пустой словарь
    if not game_filters:
        game_filters = {}
        filters[game] = game_filters
    
    # Обновляем фильтры новыми значениями
    game_filters.update(new_filters)

def get_game_filter_keyboard(game: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора фильтров игры.
    
    Args:
        game: Код игры (csgo, dota2, tf2, rust)
        
    Returns:
        Клавиатура с кнопками выбора фильтров
    """
    keyboard = []
    
    # Общие фильтры для всех игр
    keyboard.append([
        InlineKeyboardButton("💰 Диапазон цен", callback_data=f"price_range:{game}")
    ])
    
    # Специфические фильтры для каждой игры
    if game == "csgo":
        keyboard.extend([
            [InlineKeyboardButton("🔢 Диапазон Float", callback_data=f"float_range:{game}")],
            [InlineKeyboardButton("🔫 Категория", callback_data=f"set_category:{game}")],
            [InlineKeyboardButton("⭐ Редкость", callback_data=f"set_rarity:{game}")],
            [InlineKeyboardButton("🧩 Внешний вид", callback_data=f"set_exterior:{game}")],
            [InlineKeyboardButton("🔢 StatTrak™", callback_data=f"filter:stattrak:{game}")],
            [InlineKeyboardButton("🏆 Сувенир", callback_data=f"filter:souvenir:{game}")]
        ])
    elif game == "dota2":
        keyboard.extend([
            [InlineKeyboardButton("🦸 Герой", callback_data=f"set_hero:{game}")],
            [InlineKeyboardButton("⭐ Редкость", callback_data=f"set_rarity:{game}")],
            [InlineKeyboardButton("🧩 Слот", callback_data=f"set_slot:{game}")],
            [InlineKeyboardButton("🏆 Качество", callback_data=f"filter:quality:{game}")],
            [InlineKeyboardButton("🔄 Обмениваемость", callback_data=f"filter:tradable:{game}")]
        ])
    elif game == "tf2":
        keyboard.extend([
            [InlineKeyboardButton("👤 Класс", callback_data=f"set_class:{game}")],
            [InlineKeyboardButton("⭐ Качество", callback_data=f"filter:quality:{game}")],
            [InlineKeyboardButton("🔫 Тип", callback_data=f"set_type:{game}")],
            [InlineKeyboardButton("✨ Эффект", callback_data=f"filter:effect:{game}")],
            [InlineKeyboardButton("🔢 Killstreak", callback_data=f"filter:killstreak:{game}")],
            [InlineKeyboardButton("🔶 Australium", callback_data=f"filter:australium:{game}")]
        ])
    elif game == "rust":
        keyboard.extend([
            [InlineKeyboardButton("🔫 Категория", callback_data=f"set_category:{game}")],
            [InlineKeyboardButton("🧩 Тип", callback_data=f"set_type:{game}")],
            [InlineKeyboardButton("⭐ Редкость", callback_data=f"set_rarity:{game}")]
        ])
    
    # Кнопки сброса и возврата
    keyboard.extend([
        [InlineKeyboardButton("🔄 Сбросить фильтры", callback_data=f"filter:reset:{game}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_filters:main")]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_filter_description(game: str, filters: Dict[str, Any]) -> str:
    """
    Получает человекочитаемое описание фильтров.
    
    Args:
        game: Код игры (csgo, dota2, tf2, rust)
        filters: Словарь с фильтрами
        
    Returns:
        Строка с описанием фильтров
    """
    # Используем FilterFactory для получения соответствующего фильтра
    game_filter = FilterFactory.get_filter(game)
    return game_filter.get_filter_description(filters)

def build_api_params_for_game(game: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Строит параметры для DMarket API на основе фильтров.
    
    Args:
        game: Код игры (csgo, dota2, tf2, rust)
        filters: Словарь с фильтрами
        
    Returns:
        Словарь с параметрами для API
    """
    # Используем FilterFactory для получения соответствующего фильтра
    game_filter = FilterFactory.get_filter(game)
    return game_filter.build_api_params(filters)

# Обработчики для Telegram

async def handle_game_filters(update: Update, context: CallbackContext) -> None:
    """
    Обработчик команды /filters - показывает выбор игры для фильтрации.
    
    Args:
        update: Объект обновления
        context: Контекст обратного вызова
    """
    # Создаем клавиатуру для выбора игры
    keyboard = [
        [
            InlineKeyboardButton("🎮 CS2", callback_data="select_game_filter:csgo"),
            InlineKeyboardButton("🎮 Dota 2", callback_data="select_game_filter:dota2")
        ],
        [
            InlineKeyboardButton("🎮 TF2", callback_data="select_game_filter:tf2"),
            InlineKeyboardButton("🎮 Rust", callback_data="select_game_filter:rust")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="arbitrage")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Выберите игру для настройки фильтров:",
        reply_markup=reply_markup
    )

async def handle_select_game_filter_callback(update: Update, context: CallbackContext) -> None:
    """
    Обработчик выбора игры для фильтрации.
    
    Args:
        update: Объект обновления
        context: Контекст обратного вызова
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем код игры из callback_data
    data = query.data.split(":")
    game = data[1] if len(data) > 1 else "csgo"
    
    # Получаем текущие фильтры
    filters = get_current_filters(context, game)
    
    # Получаем описание фильтров
    description = get_filter_description(game, filters)
    
    # Создаем клавиатуру для выбора фильтров
    reply_markup = get_game_filter_keyboard(game)
    
    # Формируем текст сообщения
    game_names = {
        "csgo": "CS2 (CS:GO)",
        "dota2": "Dota 2",
        "tf2": "Team Fortress 2",
        "rust": "Rust"
    }
    
    game_name = game_names.get(game, game)
    
    message_text = f"🎮 Настройка фильтров для {game_name}:\n\n"
    
    if description:
        message_text += f"📋 Текущие фильтры:\n{description}\n"
    else:
        message_text += "📋 Текущие фильтры: не настроены\n"
    
    await query.edit_message_text(
        text=message_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def handle_price_range_callback(update: Update, context: CallbackContext) -> None:
    """
    Обработчик выбора диапазона цен.
    
    Args:
        update: Объект обновления
        context: Контекст обратного вызова
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем код игры из callback_data
    data = query.data.split(":")
    game = data[1] if len(data) > 1 else "csgo"
    
    # Получаем текущие фильтры
    filters = get_current_filters(context, game)
    
    # Создаем клавиатуру для выбора диапазона цен
    keyboard = [
        [
            InlineKeyboardButton("$1-10", callback_data=f"filter:price_range:1:10:{game}"),
            InlineKeyboardButton("$10-50", callback_data=f"filter:price_range:10:50:{game}")
        ],
        [
            InlineKeyboardButton("$50-100", callback_data=f"filter:price_range:50:100:{game}"),
            InlineKeyboardButton("$100-500", callback_data=f"filter:price_range:100:500:{game}")
        ],
        [
            InlineKeyboardButton("$500+", callback_data=f"filter:price_range:500:10000:{game}"),
            InlineKeyboardButton("Сбросить", callback_data=f"filter:price_range:reset:{game}")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"select_game_filter:{game}")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    min_price = filters.get("min_price", DEFAULT_FILTERS[game]["min_price"])
    max_price = filters.get("max_price", DEFAULT_FILTERS[game]["max_price"])
    
    await query.edit_message_text(
        text=f"💰 Настройка диапазона цен:\n\nТекущий диапазон: ${min_price:.2f} - ${max_price:.2f}\n\nВыберите новый диапазон цен:",
        reply_markup=reply_markup
    )

async def handle_float_range_callback(update: Update, context: CallbackContext) -> None:
    """
    Обработчик выбора диапазона Float (для CS2).
    
    Args:
        update: Объект обновления
        context: Контекст обратного вызова
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем код игры из callback_data
    data = query.data.split(":")
    game = data[1] if len(data) > 1 else "csgo"
    
    # Если игра не CS2, возвращаемся к выбору фильтров
    if game != "csgo":
        await query.edit_message_text(
            text="Диапазон Float доступен только для CS2.",
            reply_markup=get_game_filter_keyboard(game)
        )
        return
    
    # Получаем текущие фильтры
    filters = get_current_filters(context, game)
    
    # Создаем клавиатуру для выбора диапазона Float
    keyboard = [
        [
            InlineKeyboardButton("Factory New (0.00-0.07)", callback_data=f"filter:float_range:0.00:0.07:{game}"),
            InlineKeyboardButton("Minimal Wear (0.07-0.15)", callback_data=f"filter:float_range:0.07:0.15:{game}")
        ],
        [
            InlineKeyboardButton("Field-Tested (0.15-0.38)", callback_data=f"filter:float_range:0.15:0.38:{game}"),
            InlineKeyboardButton("Well-Worn (0.38-0.45)", callback_data=f"filter:float_range:0.38:0.45:{game}")
        ],
        [
            InlineKeyboardButton("Battle-Scarred (0.45-1.00)", callback_data=f"filter:float_range:0.45:1.00:{game}"),
            InlineKeyboardButton("Сбросить", callback_data=f"filter:float_range:reset:{game}")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"select_game_filter:{game}")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    float_min = filters.get("float_min", DEFAULT_FILTERS[game]["float_min"])
    float_max = filters.get("float_max", DEFAULT_FILTERS[game]["float_max"])
    
    await query.edit_message_text(
        text=f"🔢 Настройка диапазона Float:\n\nТекущий диапазон: {float_min:.2f} - {float_max:.2f}\n\nВыберите новый диапазон Float:",
        reply_markup=reply_markup
    )

async def handle_set_category_callback(update: Update, context: CallbackContext) -> None:
    """
    Обработчик выбора категории (для CS2).
    
    Args:
        update: Объект обновления
        context: Контекст обратного вызова
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем код игры из callback_data
    data = query.data.split(":")
    game = data[1] if len(data) > 1 else "csgo"
    
    # Получаем текущие фильтры
    filters = get_current_filters(context, game)
    
    # Создаем клавиатуру для выбора категории, зависящую от игры
    keyboard = []
    categories = []
    
    if game == "csgo":
        categories = CS2_CATEGORIES
    elif game == "rust":
        categories = RUST_CATEGORIES
    
    # Создаем кнопки по 2 в ряд
    row = []
    for i, category in enumerate(categories):
        row.append(InlineKeyboardButton(category, callback_data=f"filter:category:{category}:{game}"))
        
        # Каждые 2 элемента добавляем ряд и сбрасываем текущий
        if len(row) == 2 or i == len(categories) - 1:
            keyboard.append(row.copy())
            row = []
    
    # Добавляем кнопку сброса и возврата
    keyboard.append([InlineKeyboardButton("Сбросить", callback_data=f"filter:category:reset:{game}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"select_game_filter:{game}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_category = filters.get("category", "Не выбрано")
    category_type = "категории" if game == "csgo" else "категории"
    
    await query.edit_message_text(
        text=f"🔫 Выбор {category_type}:\n\nТекущая категория: {current_category}\n\nВыберите категорию:",
        reply_markup=reply_markup
    )

async def handle_set_rarity_callback(update: Update, context: CallbackContext) -> None:
    """
    Обработчик выбора редкости.
    
    Args:
        update: Объект обновления
        context: Контекст обратного вызова
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем код игры из callback_data
    data = query.data.split(":")
    game = data[1] if len(data) > 1 else "csgo"
    
    # Получаем текущие фильтры
    filters = get_current_filters(context, game)
    
    # Выбираем список редкостей в зависимости от игры
    if game == "csgo":
        rarities = CS2_RARITIES
    elif game == "dota2":
        rarities = DOTA2_RARITIES
    elif game == "rust":
        rarities = RUST_RARITIES
    else:
        rarities = []
    
    # Создаем клавиатуру для выбора редкости
    keyboard = []
    row = []
    
    for i, rarity in enumerate(rarities):
        row.append(InlineKeyboardButton(rarity, callback_data=f"filter:rarity:{rarity}:{game}"))
        
        # Каждые 2 элемента добавляем ряд и сбрасываем текущий
        if len(row) == 2 or i == len(rarities) - 1:
            keyboard.append(row.copy())
            row = []
    
    # Добавляем кнопку сброса и возврата
    keyboard.append([InlineKeyboardButton("Сбросить", callback_data=f"filter:rarity:reset:{game}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"select_game_filter:{game}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_rarity = filters.get("rarity", "Не выбрано")
    
    await query.edit_message_text(
        text=f"⭐ Выбор редкости:\n\nТекущая редкость: {current_rarity}\n\nВыберите редкость:",
        reply_markup=reply_markup
    )

async def handle_set_exterior_callback(update: Update, context: CallbackContext) -> None:
    """
    Обработчик выбора внешнего вида (для CS2).
    
    Args:
        update: Объект обновления
        context: Контекст обратного вызова
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем код игры из callback_data
    data = query.data.split(":")
    game = data[1] if len(data) > 1 else "csgo"
    
    # Если игра не CS2, возвращаемся к выбору фильтров
    if game != "csgo":
        await query.edit_message_text(
            text="Выбор внешнего вида доступен только для CS2.",
            reply_markup=get_game_filter_keyboard(game)
        )
        return
    
    # Получаем текущие фильтры
    filters = get_current_filters(context, game)
    
    # Создаем клавиатуру для выбора внешнего вида
    keyboard = []
    
    for exterior in CS2_EXTERIORS:
        keyboard.append([
            InlineKeyboardButton(exterior, callback_data=f"filter:exterior:{exterior}:{game}")
        ])
    
    # Добавляем кнопку сброса и возврата
    keyboard.append([InlineKeyboardButton("Сбросить", callback_data=f"filter:exterior:reset:{game}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"select_game_filter:{game}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_exterior = filters.get("exterior", "Не выбрано")
    
    await query.edit_message_text(
        text=f"🧩 Выбор внешнего вида:\n\nТекущий внешний вид: {current_exterior}\n\nВыберите внешний вид:",
        reply_markup=reply_markup
    )

async def handle_set_hero_callback(update: Update, context: CallbackContext) -> None:
    """
    Обработчик выбора героя (для Dota 2).
    
    Args:
        update: Объект обновления
        context: Контекст обратного вызова
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем код игры из callback_data
    data = query.data.split(":")
    game = data[1] if len(data) > 1 else "dota2"
    
    # Если игра не Dota 2, возвращаемся к выбору фильтров
    if game != "dota2":
        await query.edit_message_text(
            text="Выбор героя доступен только для Dota 2.",
            reply_markup=get_game_filter_keyboard(game)
        )
        return
    
    # Получаем текущие фильтры
    filters = get_current_filters(context, game)
    
    # Создаем клавиатуру для выбора героя
    keyboard = []
    row = []
    
    for i, hero in enumerate(DOTA2_HEROES):
        row.append(InlineKeyboardButton(hero, callback_data=f"filter:hero:{hero}:{game}"))
        
        # Каждые 2 элемента добавляем ряд и сбрасываем текущий
        if len(row) == 2 or i == len(DOTA2_HEROES) - 1:
            keyboard.append(row.copy())
            row = []
    
    # Добавляем кнопку сброса и возврата
    keyboard.append([InlineKeyboardButton("Сбросить", callback_data=f"filter:hero:reset:{game}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"select_game_filter:{game}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_hero = filters.get("hero", "Не выбрано")
    
    await query.edit_message_text(
        text=f"🦸 Выбор героя:\n\nТекущий герой: {current_hero}\n\nВыберите героя:",
        reply_markup=reply_markup
    )

async def handle_set_class_callback(update: Update, context: CallbackContext) -> None:
    """
    Обработчик выбора класса (для TF2).
    
    Args:
        update: Объект обновления
        context: Контекст обратного вызова
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем код игры из callback_data
    data = query.data.split(":")
    game = data[1] if len(data) > 1 else "tf2"
    
    # Если игра не TF2, возвращаемся к выбору фильтров
    if game != "tf2":
        await query.edit_message_text(
            text="Выбор класса доступен только для Team Fortress 2.",
            reply_markup=get_game_filter_keyboard(game)
        )
        return
    
    # Получаем текущие фильтры
    filters = get_current_filters(context, game)
    
    # Создаем клавиатуру для выбора класса
    keyboard = []
    
    for tf_class in TF2_CLASSES:
        keyboard.append([
            InlineKeyboardButton(tf_class, callback_data=f"filter:class:{tf_class}:{game}")
        ])
    
    # Добавляем кнопку сброса и возврата
    keyboard.append([InlineKeyboardButton("Сбросить", callback_data=f"filter:class:reset:{game}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"select_game_filter:{game}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_class = filters.get("class", "Не выбрано")
    
    await query.edit_message_text(
        text=f"👤 Выбор класса:\n\nТекущий класс: {current_class}\n\nВыберите класс:",
        reply_markup=reply_markup
    )

async def handle_filter_callback(update: Update, context: CallbackContext) -> None:
    """
    Обработчик для всех фильтров.
    
    Args:
        update: Объект обновления
        context: Контекст обратного вызова
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем данные из callback_data
    data = query.data.split(":")
    
    if len(data) < 3:
        await query.edit_message_text(
            text="Неверный формат данных фильтра.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="arbitrage")]])
        )
        return
    
    filter_type = data[1]
    filter_value = data[2]
    game = data[3] if len(data) > 3 else "csgo"
    
    # Получаем текущие фильтры
    filters = get_current_filters(context, game)
    
    # Обрабатываем различные типы фильтров
    
    # Диапазон цен
    if filter_type == "price_range":
        if filter_value == "reset":
            # Сбрасываем фильтры цены
            if "min_price" in filters:
                del filters["min_price"]
            if "max_price" in filters:
                del filters["max_price"]
        else:
            # Устанавливаем диапазон цен
            min_price = float(filter_value)
            max_price = float(data[3])
            filters["min_price"] = min_price
            filters["max_price"] = max_price
            game = data[4] if len(data) > 4 else "csgo"
    
    # Диапазон Float
    elif filter_type == "float_range":
        if filter_value == "reset":
            # Сбрасываем фильтры Float
            if "float_min" in filters:
                del filters["float_min"]
            if "float_max" in filters:
                del filters["float_max"]
        else:
            # Устанавливаем диапазон Float
            float_min = float(filter_value)
            float_max = float(data[3])
            filters["float_min"] = float_min
            filters["float_max"] = float_max
            game = data[4] if len(data) > 4 else "csgo"
    
    # Категория
    elif filter_type == "category":
        if filter_value == "reset":
            # Сбрасываем фильтр категории
            if "category" in filters:
                del filters["category"]
        else:
            # Устанавливаем категорию
            filters["category"] = filter_value
    
    # Редкость
    elif filter_type == "rarity":
        if filter_value == "reset":
            # Сбрасываем фильтр редкости
            if "rarity" in filters:
                del filters["rarity"]
        else:
            # Устанавливаем редкость
            filters["rarity"] = filter_value
    
    # Внешний вид
    elif filter_type == "exterior":
        if filter_value == "reset":
            # Сбрасываем фильтр внешнего вида
            if "exterior" in filters:
                del filters["exterior"]
        else:
            # Устанавливаем внешний вид
            filters["exterior"] = filter_value
    
    # Герой
    elif filter_type == "hero":
        if filter_value == "reset":
            # Сбрасываем фильтр героя
            if "hero" in filters:
                del filters["hero"]
        else:
            # Устанавливаем героя
            filters["hero"] = filter_value
    
    # Класс
    elif filter_type == "class":
        if filter_value == "reset":
            # Сбрасываем фильтр класса
            if "class" in filters:
                del filters["class"]
        else:
            # Устанавливаем класс
            filters["class"] = filter_value
    
    # Булевы фильтры (вкл/выкл)
    elif filter_type in ["stattrak", "souvenir", "tradable", "australium"]:
        # Переключаем значение фильтра
        filters[filter_type] = not filters.get(filter_type, False)
    
    # Полный сброс фильтров
    elif filter_type == "reset":
        # Устанавливаем значения по умолчанию
        filters = DEFAULT_FILTERS.get(game, {}).copy()
    
    # Обновляем фильтры в контексте
    update_filters(context, game, filters)
    
    # Возвращаемся к выбору фильтров
    await handle_select_game_filter_callback(update, context)

async def handle_back_to_filters_callback(update: Update, context: CallbackContext) -> None:
    """
    Обработчик кнопки "Назад" в фильтрах.
    
    Args:
        update: Объект обновления
        context: Контекст обратного вызова
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем данные из callback_data
    data = query.data.split(":")
    
    if len(data) < 2:
        # Если нет данных, возвращаемся к главному меню арбитража
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к арбитражу", callback_data="arbitrage")]
        ]
        await query.edit_message_text(
            text="Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Обрабатываем различные типы возврата
    back_type = data[1]
    
    if back_type == "main":
        # Возвращаемся к выбору игры
        await handle_game_filters(update, context)
    else:
        # По умолчанию возвращаемся к арбитражу
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к арбитражу", callback_data="arbitrage")]
        ]
        await query.edit_message_text(
            text="Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
