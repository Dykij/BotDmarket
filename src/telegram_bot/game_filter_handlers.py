"""
Обработчики команд Telegram-бота для работы с фильтрами предметов по играм.
"""
import logging
from typing import Dict, List, Any, Optional, Union, cast
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from src.dmarket.arbitrage import find_arbitrage_items
from src.dmarket.game_filters import (
    FilterFactory, apply_filters_to_items, build_api_params_for_game
)
from src.utils.api_error_handling import APIError
from src.utils.dmarket_api_utils import execute_api_request

# Настройка логирования
logger = logging.getLogger(__name__)

# Константы
GAMES_MAPPING = {
    "csgo": "CS2",
    "dota2": "Dota 2",
    "tf2": "Team Fortress 2",
    "rust": "Rust"
}

# Конфигурации фильтров по умолчанию для разных игр
DEFAULT_FILTERS = {
    "csgo": {
        "float_min": 0.0,
        "float_max": 1.0,
        "min_price": 1.0,
        "max_price": 500.0
    },
    "dota2": {
        "min_price": 1.0,
        "max_price": 500.0
    },
    "tf2": {
        "min_price": 1.0,
        "max_price": 300.0
    },
    "rust": {
        "min_price": 1.0,
        "max_price": 200.0
    }
}

# Фильтры по экстерьеру для CS2
CS2_EXTERIORS = [
    "Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"
]

# Категории оружия для CS2
CS2_CATEGORIES = [
    "knife", "pistol", "rifle", "smg", "shotgun", "sniper rifle", 
    "machinegun", "container", "sticker", "gloves"
]

# Редкость предметов для CS2
CS2_RARITIES = [
    "Consumer", "Industrial", "Mil-Spec", "Restricted", "Classified", 
    "Covert", "Contraband"
]

# Популярные герои для Dota 2
DOTA2_HEROES = [
    "Pudge", "Invoker", "Anti-Mage", "Juggernaut", "Phantom Assassin", 
    "Drow Ranger", "Crystal Maiden", "Axe", "Sniper", "Techies"
]

# Редкость предметов для Dota 2
DOTA2_RARITIES = [
    "Common", "Uncommon", "Rare", "Mythical", "Immortal", "Legendary", 
    "Arcana", "Ancient"
]

# Классы персонажей для TF2
TF2_CLASSES = [
    "Scout", "Soldier", "Pyro", "Demoman", "Heavy", "Engineer", 
    "Medic", "Sniper", "Spy", "All Classes"
]


async def handle_game_filters(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает команду /filters для настройки фильтров предметов по играм.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    # Получаем текущую игру из контекста или используем CSGO по умолчанию
    game = "csgo"
    if hasattr(context, 'user_data') and "current_game" in context.user_data:
        game = context.user_data["current_game"]
    
    # Получаем текущие фильтры для этой игры или значения по умолчанию
    filters = DEFAULT_FILTERS.get(game, {}).copy()
    if hasattr(context, 'user_data') and "game_filters" in context.user_data:
        user_filters = context.user_data["game_filters"].get(game, {})
        filters.update(user_filters)
    
    # Создаем фильтр для выбранной игры
    game_filter = FilterFactory.get_filter(game)
    filter_description = game_filter.get_filter_description(filters)
    
    # Создаем сообщение с информацией о текущих фильтрах
    game_name = GAMES_MAPPING.get(game, game)
    message_text = (
        f"⚙️ Настройка фильтров для игры *{game_name}*\n\n"
        f"Текущие фильтры:\n{filter_description}\n\n"
        "Выберите действие:"
    )
    
    # Создаем клавиатуру с доступными действиями
    keyboard = []
    
    # Добавляем кнопки в зависимости от игры
    if game == "csgo":
        keyboard.extend([
            [
                InlineKeyboardButton("💰 Цена", callback_data=f"filter:price:{game}"),
                InlineKeyboardButton("🔍 Float", callback_data=f"filter:float:{game}")
            ],
            [
                InlineKeyboardButton("🧩 Категория", callback_data=f"filter:category:{game}"),
                InlineKeyboardButton("✨ Редкость", callback_data=f"filter:rarity:{game}")
            ],
            [
                InlineKeyboardButton("🔶 Внешний вид", callback_data=f"filter:exterior:{game}"),
                InlineKeyboardButton("📊 StatTrak", callback_data=f"filter:stattrak:{game}")
            ]
        ])
    elif game == "dota2":
        keyboard.extend([
            [
                InlineKeyboardButton("💰 Цена", callback_data=f"filter:price:{game}"),
                InlineKeyboardButton("🦸‍♂️ Герой", callback_data=f"filter:hero:{game}")
            ],
            [
                InlineKeyboardButton("✨ Редкость", callback_data=f"filter:rarity:{game}"),
                InlineKeyboardButton("🧩 Слот", callback_data=f"filter:slot:{game}")
            ]
        ])
    elif game == "tf2":
        keyboard.extend([
            [
                InlineKeyboardButton("💰 Цена", callback_data=f"filter:price:{game}"),
                InlineKeyboardButton("👨‍🚒 Класс", callback_data=f"filter:class:{game}")
            ],
            [
                InlineKeyboardButton("✨ Качество", callback_data=f"filter:quality:{game}"),
                InlineKeyboardButton("🧩 Тип", callback_data=f"filter:type:{game}")
            ]
        ])
    elif game == "rust":
        keyboard.extend([
            [
                InlineKeyboardButton("💰 Цена", callback_data=f"filter:price:{game}"),
                InlineKeyboardButton("🧩 Категория", callback_data=f"filter:category:{game}")
            ],
            [
                InlineKeyboardButton("✨ Редкость", callback_data=f"filter:rarity:{game}")
            ]
        ])
    
    # Общие кнопки для всех игр
    keyboard.extend([
        [
            InlineKeyboardButton("🔄 Сбросить", callback_data=f"filter:reset:{game}"),
            InlineKeyboardButton("🎮 Сменить игру", callback_data="filter:change_game")
        ],
        [
            InlineKeyboardButton("🔍 Поиск с фильтрами", callback_data=f"filter:search:{game}")
        ]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_filter_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает callback-запросы для настройки фильтров.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем данные callback
    # Формат: "filter:action:game"
    callback_data = query.data.split(":")
    
    if len(callback_data) < 3:
        await query.edit_message_text(
            "❌ Ошибка: неверный формат данных callback.",
            parse_mode="Markdown"
        )
        return
    
    action = callback_data[1]
    game = callback_data[2] if len(callback_data) > 2 else "csgo"
    
    # Обрабатываем различные действия
    if action == "price":
        # Настройка диапазона цен
        await handle_price_filter(update, context, game)
        
    elif action == "float" and game == "csgo":
        # Настройка диапазона float для CS2
        await handle_float_filter(update, context)
        
    elif action == "category" and game == "csgo":
        # Выбор категории оружия для CS2
        await handle_category_filter(update, context)
        
    elif action == "rarity":
        # Выбор редкости предмета
        await handle_rarity_filter(update, context, game)
        
    elif action == "exterior" and game == "csgo":
        # Выбор внешнего вида для CS2
        await handle_exterior_filter(update, context)
        
    elif action == "stattrak" and game == "csgo":
        # Включение/выключение фильтра StatTrak для CS2
        await handle_stattrak_filter(update, context)
        
    elif action == "hero" and game == "dota2":
        # Выбор героя для Dota 2
        await handle_hero_filter(update, context)
        
    elif action == "class" and game == "tf2":
        # Выбор класса для TF2
        await handle_class_filter(update, context)
        
    elif action == "reset":
        # Сброс фильтров для игры
        await handle_reset_filters(update, context, game)
        
    elif action == "change_game":
        # Смена игры для фильтрации
        await handle_change_game_filter(update, context)
        
    elif action == "search":
        # Поиск предметов с применением фильтров
        await handle_search_with_filters(update, context, game)
        
    else:
        # Неизвестное действие
        await query.edit_message_text(
            f"⚠️ Действие '{action}' для игры {game} не поддерживается.",
            parse_mode="Markdown"
        )


async def handle_price_filter(update: Update, context: CallbackContext, game: str) -> None:
    """
    Обрабатывает настройку диапазона цен.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
        game: Код игры
    """
    query = update.callback_query
    
    # Получаем текущие фильтры для этой игры или значения по умолчанию
    filters = DEFAULT_FILTERS.get(game, {}).copy()
    if hasattr(context, 'user_data') and "game_filters" in context.user_data:
        user_filters = context.user_data["game_filters"].get(game, {})
        filters.update(user_filters)
    
    # Получаем текущие значения цен
    min_price = filters.get("min_price", 1.0)
    max_price = filters.get("max_price", 500.0)
    
    # Создаем сообщение для настройки цены
    message_text = (
        f"💰 Настройка диапазона цен для игры *{GAMES_MAPPING.get(game, game)}*\n\n"
        f"Текущий диапазон: ${min_price:.2f} - ${max_price:.2f}\n\n"
        "Выберите действие:"
    )
    
    # Создаем клавиатуру с вариантами диапазонов цен
    keyboard = [
        [
            InlineKeyboardButton("$1-10", callback_data=f"price_range:{game}:1:10"),
            InlineKeyboardButton("$10-50", callback_data=f"price_range:{game}:10:50"),
            InlineKeyboardButton("$50-100", callback_data=f"price_range:{game}:50:100")
        ],
        [
            InlineKeyboardButton("$100-250", callback_data=f"price_range:{game}:100:250"),
            InlineKeyboardButton("$250-500", callback_data=f"price_range:{game}:250:500"),
            InlineKeyboardButton("$500+", callback_data=f"price_range:{game}:500:10000")
        ],
        [
            InlineKeyboardButton("« Назад", callback_data=f"back_to_filters:{game}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_float_filter(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает настройку диапазона float для CS2.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    game = "csgo"
    
    # Получаем текущие фильтры для CS2 или значения по умолчанию
    filters = DEFAULT_FILTERS.get(game, {}).copy()
    if hasattr(context, 'user_data') and "game_filters" in context.user_data:
        user_filters = context.user_data["game_filters"].get(game, {})
        filters.update(user_filters)
    
    # Получаем текущие значения float
    float_min = filters.get("float_min", 0.0)
    float_max = filters.get("float_max", 1.0)
    
    # Создаем сообщение для настройки float
    message_text = (
        f"🔍 Настройка диапазона Float для игры *CS2*\n\n"
        f"Текущий диапазон: {float_min:.3f} - {float_max:.3f}\n\n"
        "Выберите диапазон Float:"
    )
    
    # Создаем клавиатуру с вариантами диапазонов float
    keyboard = [
        [
            InlineKeyboardButton("0.00-0.07 (FN)", callback_data="float_range:csgo:0:0.07"),
            InlineKeyboardButton("0.07-0.15 (MW)", callback_data="float_range:csgo:0.07:0.15")
        ],
        [
            InlineKeyboardButton("0.15-0.38 (FT)", callback_data="float_range:csgo:0.15:0.38"),
            InlineKeyboardButton("0.38-0.45 (WW)", callback_data="float_range:csgo:0.38:0.45")
        ],
        [
            InlineKeyboardButton("0.45-1.00 (BS)", callback_data="float_range:csgo:0.45:1.0"),
            InlineKeyboardButton("Все (0.00-1.00)", callback_data="float_range:csgo:0:1")
        ],
        [
            InlineKeyboardButton("« Назад", callback_data="back_to_filters:csgo")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_category_filter(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор категории оружия для CS2.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    
    # Создаем сообщение для выбора категории
    message_text = (
        "🧩 Выберите категорию предметов для *CS2*:\n\n"
        "Текущие категории предметов CS2:"
    )
    
    # Создаем клавиатуру с вариантами категорий
    keyboard = []
    row = []
    
    for i, category in enumerate(CS2_CATEGORIES):
        # По 2 кнопки в ряду
        if i % 2 == 0 and i > 0:
            keyboard.append(row)
            row = []
        
        row.append(InlineKeyboardButton(
            category.capitalize(), 
            callback_data=f"set_category:csgo:{category}"
        ))
    
    # Добавляем последний ряд, если он не пустой
    if row:
        keyboard.append(row)
    
    # Добавляем кнопку "Назад"
    keyboard.append([
        InlineKeyboardButton("« Назад", callback_data="back_to_filters:csgo")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_rarity_filter(update: Update, context: CallbackContext, game: str) -> None:
    """
    Обрабатывает выбор редкости предмета.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
        game: Код игры
    """
    query = update.callback_query
    
    # Определяем список редкостей в зависимости от игры
    rarities = []
    if game == "csgo":
        rarities = CS2_RARITIES
    elif game == "dota2":
        rarities = DOTA2_RARITIES
    else:
        # Для других игр - базовые редкости
        rarities = ["Common", "Uncommon", "Rare", "Mythical", "Legendary"]
    
    # Создаем сообщение для выбора редкости
    message_text = (
        f"✨ Выберите редкость предмета для *{GAMES_MAPPING.get(game, game)}*:"
    )
    
    # Создаем клавиатуру с вариантами редкости
    keyboard = []
    row = []
    
    for i, rarity in enumerate(rarities):
        # По 2 кнопки в ряду
        if i % 2 == 0 and i > 0:
            keyboard.append(row)
            row = []
        
        row.append(InlineKeyboardButton(
            rarity, 
            callback_data=f"set_rarity:{game}:{rarity}"
        ))
    
    # Добавляем последний ряд, если он не пустой
    if row:
        keyboard.append(row)
    
    # Добавляем кнопку "Назад"
    keyboard.append([
        InlineKeyboardButton("« Назад", callback_data=f"back_to_filters:{game}")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_exterior_filter(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор внешнего вида для CS2.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    
    # Создаем сообщение для выбора внешнего вида
    message_text = (
        "🔶 Выберите внешний вид предмета для *CS2*:"
    )
    
    # Создаем клавиатуру с вариантами внешнего вида
    keyboard = []
    
    for exterior in CS2_EXTERIORS:
        keyboard.append([
            InlineKeyboardButton(
                exterior, 
                callback_data=f"set_exterior:csgo:{exterior}"
            )
        ])
    
    # Добавляем кнопку "Назад"
    keyboard.append([
        InlineKeyboardButton("« Назад", callback_data="back_to_filters:csgo")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_stattrak_filter(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает включение/выключение фильтра StatTrak для CS2.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    
    # Получаем текущие фильтры для CS2
    if not hasattr(context, 'user_data'):
        context.user_data = {}
        
    if "game_filters" not in context.user_data:
        context.user_data["game_filters"] = {}
        
    if "csgo" not in context.user_data["game_filters"]:
        context.user_data["game_filters"]["csgo"] = {}
    
    # Переключаем значение stattrak
    current_value = context.user_data["game_filters"]["csgo"].get("stattrak", False)
    context.user_data["game_filters"]["csgo"]["stattrak"] = not current_value
    
    # Получаем обновленное значение
    stattrak_enabled = context.user_data["game_filters"]["csgo"]["stattrak"]
    
    # Создаем сообщение с информацией о фильтре
    message_text = (
        "📊 Фильтр StatTrak для CS2\n\n"
        f"StatTrak: {'✅ Включен' if stattrak_enabled else '❌ Выключен'}\n\n"
        "Выберите действие:"
    )
    
    # Создаем клавиатуру
    keyboard = [
        [
            InlineKeyboardButton(
                "🔄 Переключить StatTrak", 
                callback_data="filter:stattrak:csgo"
            )
        ],
        [
            InlineKeyboardButton(
                "« Назад к фильтрам", 
                callback_data="back_to_filters:csgo"
            )
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup
    )


async def handle_hero_filter(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор героя для Dota 2.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    
    # Создаем сообщение для выбора героя
    message_text = (
        "🦸‍♂️ Выберите героя для Dota 2:\n\n"
        "Выберите одного из популярных героев или введите имя героя вручную"
    )
    
    # Создаем клавиатуру с вариантами героев
    keyboard = []
    row = []
    
    for i, hero in enumerate(DOTA2_HEROES):
        # По 2 кнопки в ряду
        if i % 2 == 0 and i > 0:
            keyboard.append(row)
            row = []
        
        row.append(InlineKeyboardButton(
            hero, 
            callback_data=f"set_hero:dota2:{hero}"
        ))
    
    # Добавляем последний ряд, если он не пустой
    if row:
        keyboard.append(row)
    
    # Добавляем кнопку "Назад"
    keyboard.append([
        InlineKeyboardButton("« Назад", callback_data="back_to_filters:dota2")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_class_filter(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор класса для TF2.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    
    # Создаем сообщение для выбора класса
    message_text = (
        "👨‍🚒 Выберите класс для Team Fortress 2:"
    )
    
    # Создаем клавиатуру с вариантами классов
    keyboard = []
    row = []
    
    for i, tf_class in enumerate(TF2_CLASSES):
        # По 2 кнопки в ряду
        if i % 2 == 0 and i > 0:
            keyboard.append(row)
            row = []
        
        row.append(InlineKeyboardButton(
            tf_class, 
            callback_data=f"set_class:tf2:{tf_class}"
        ))
    
    # Добавляем последний ряд, если он не пустой
    if row:
        keyboard.append(row)
    
    # Добавляем кнопку "Назад"
    keyboard.append([
        InlineKeyboardButton("« Назад", callback_data="back_to_filters:tf2")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_reset_filters(update: Update, context: CallbackContext, game: str) -> None:
    """
    Обрабатывает сброс фильтров для игры.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
        game: Код игры
    """
    query = update.callback_query
    
    # Сбрасываем фильтры для указанной игры
    if hasattr(context, 'user_data') and "game_filters" in context.user_data:
        if game in context.user_data["game_filters"]:
            context.user_data["game_filters"][game] = {}
    
    # Создаем сообщение о сбросе фильтров
    message_text = (
        f"🔄 Фильтры для игры *{GAMES_MAPPING.get(game, game)}* сброшены!\n\n"
        "Выберите действие:"
    )
    
    # Создаем клавиатуру
    keyboard = [
        [
            InlineKeyboardButton(
                "« Назад к фильтрам", 
                callback_data=f"back_to_filters:{game}"
            )
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_change_game_filter(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает смену игры для фильтрации.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    
    # Создаем сообщение для выбора игры
    message_text = (
        "🎮 Выберите игру для настройки фильтров:"
    )
    
    # Создаем клавиатуру с вариантами игр
    keyboard = [
        [
            InlineKeyboardButton("🔫 CS2", callback_data="select_game_filter:csgo"),
            InlineKeyboardButton("🏆 Dota 2", callback_data="select_game_filter:dota2")
        ],
        [
            InlineKeyboardButton("🎭 Team Fortress 2", callback_data="select_game_filter:tf2"),
            InlineKeyboardButton("🏝️ Rust", callback_data="select_game_filter:rust")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup
    )


async def handle_search_with_filters(update: Update, context: CallbackContext, game: str) -> None:
    """
    Обрабатывает поиск предметов с применением фильтров.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
        game: Код игры
    """
    query = update.callback_query
    
    # Получаем текущие фильтры для игры
    filters = DEFAULT_FILTERS.get(game, {}).copy()
    if hasattr(context, 'user_data') and "game_filters" in context.user_data:
        user_filters = context.user_data["game_filters"].get(game, {})
        filters.update(user_filters)
    
    # Создаем фильтр для выбранной игры
    game_filter = FilterFactory.get_filter(game)
    filter_description = game_filter.get_filter_description(filters)
    
    # Отправляем сообщение о начале поиска
    await query.edit_message_text(
        f"🔍 Поиск предметов для {GAMES_MAPPING.get(game, game)} с фильтрами:\n"
        f"{filter_description}\n\n"
        "⏳ Пожалуйста, подождите...",
        parse_mode="Markdown"
    )
    
    try:
        # Преобразуем фильтры в параметры API
        api_params = build_api_params_for_game(game, filters)
        
        # Создаем функцию для поиска предметов
        async def search_items():
            # Получаем предметы с учетом фильтров API
            items = await find_arbitrage_items(
                game=game,
                min_price=filters.get("min_price", 0),
                max_price=filters.get("max_price", 500),
                limit=50,
                extra_params=api_params
            )
            
            # Применяем фильтрацию на стороне клиента
            filtered_items = apply_filters_to_items(items, game, filters)
            
            return filtered_items
        
        # Выполняем поиск с обработкой ошибок API
        items = await execute_api_request(
            request_func=search_items,
            endpoint_type="market",
            max_retries=2
        )
        
        # Проверяем результаты
        if not items:
            await query.edit_message_text(
                f"⚠️ Не найдено предметов для {GAMES_MAPPING.get(game, game)} "
                f"с указанными фильтрами:\n{filter_description}\n\n"
                "Попробуйте изменить параметры фильтрации.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "« Назад к фильтрам", 
                        callback_data=f"back_to_filters:{game}"
                    )]
                ]),
                parse_mode="Markdown"
            )
            return
        
        # Ограничиваем количество предметов для отображения
        display_items = items[:10]
        
        # Формируем сообщение с найденными предметами
        message_text = (
            f"✅ Найдено {len(items)} предметов для {GAMES_MAPPING.get(game, game)} "
            f"с фильтрами:\n{filter_description}\n\n"
        )
        
        # Добавляем информацию о предметах
        for i, item in enumerate(display_items, 1):
            # Получаем основную информацию о предмете
            title = item.get("title", item.get("name", "Неизвестный предмет"))
            price = float(item.get("price", {}).get("USD", 0))
            
            # Получаем дополнительную информацию о предмете в зависимости от игры
            extra_info = []
            
            if game == "csgo":
                if "float" in item:
                    extra_info.append(f"Float: {item['float']:.3f}")
                if "exterior" in item:
                    extra_info.append(f"Exterior: {item['exterior']}")
                if "category" in item:
                    extra_info.append(f"Category: {item['category']}")
            
            elif game == "dota2":
                if "hero" in item:
                    extra_info.append(f"Герой: {item['hero']}")
                if "rarity" in item:
                    extra_info.append(f"Редкость: {item['rarity']}")
            
            # Форматируем вывод предмета
            extra_text = f" ({', '.join(extra_info)})" if extra_info else ""
            message_text += f"{i}. `{title}`{extra_text} - ${price:.2f}\n"
            
        # Если найдено больше предметов, чем отображается
        if len(items) > len(display_items):
            message_text += f"\n_Показано {len(display_items)} из {len(items)} найденных предметов_\n"
        
        # Создаем клавиатуру для дальнейших действий
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔄 Обновить", 
                    callback_data=f"filter:search:{game}"
                ),
                InlineKeyboardButton(
                    "« Назад к фильтрам", 
                    callback_data=f"back_to_filters:{game}"
                )
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем результат
        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    except APIError as e:
        logger.error(f"Ошибка API при поиске предметов: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при поиске предметов: {e}\n\n"
            "Попробуйте повторить запрос позже.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "« Назад к фильтрам", 
                    callback_data=f"back_to_filters:{game}"
                )]
            ]),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.exception(f"Ошибка при поиске предметов: {str(e)}")
        await query.edit_message_text(
            f"❌ Произошла ошибка при поиске: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "« Назад к фильтрам", 
                    callback_data=f"back_to_filters:{game}"
                )]
            ])
        )


# Обработчики дополнительных callback-запросов

async def handle_price_range_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор диапазона цен.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем данные callback
    # Формат: "price_range:game:min:max"
    callback_data = query.data.split(":")
    
    if len(callback_data) < 4:
        await query.edit_message_text(
            "❌ Ошибка: неверный формат данных callback для диапазона цен.",
            parse_mode="Markdown"
        )
        return
    
    game = callback_data[1]
    min_price = float(callback_data[2])
    max_price = float(callback_data[3])
    
    # Сохраняем выбранный диапазон цен
    if not hasattr(context, 'user_data'):
        context.user_data = {}
        
    if "game_filters" not in context.user_data:
        context.user_data["game_filters"] = {}
        
    if game not in context.user_data["game_filters"]:
        context.user_data["game_filters"][game] = {}
    
    context.user_data["game_filters"][game]["min_price"] = min_price
    context.user_data["game_filters"][game]["max_price"] = max_price
    
    # Возвращаемся к настройке фильтров
    await query.edit_message_text(
        f"✅ Диапазон цен для {GAMES_MAPPING.get(game, game)} установлен: "
        f"${min_price:.2f} - ${max_price:.2f}\n\n"
        "Возврат к настройке фильтров...",
        parse_mode="Markdown"
    )
    
    # Симулируем callback для возврата к фильтрам
    query.data = f"back_to_filters:{game}"
    await handle_back_to_filters_callback(update, context)


async def handle_float_range_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор диапазона float.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем данные callback
    # Формат: "float_range:game:min:max"
    callback_data = query.data.split(":")
    
    if len(callback_data) < 4:
        await query.edit_message_text(
            "❌ Ошибка: неверный формат данных callback для диапазона float.",
            parse_mode="Markdown"
        )
        return
    
    game = callback_data[1]
    float_min = float(callback_data[2])
    float_max = float(callback_data[3])
    
    # Сохраняем выбранный диапазон float
    if not hasattr(context, 'user_data'):
        context.user_data = {}
        
    if "game_filters" not in context.user_data:
        context.user_data["game_filters"] = {}
        
    if game not in context.user_data["game_filters"]:
        context.user_data["game_filters"][game] = {}
    
    context.user_data["game_filters"][game]["float_min"] = float_min
    context.user_data["game_filters"][game]["float_max"] = float_max
    
    # Определяем название внешнего вида по диапазону float
    exterior = "All"
    if float_min == 0.0 and float_max == 0.07:
        exterior = "Factory New"
    elif float_min == 0.07 and float_max == 0.15:
        exterior = "Minimal Wear"
    elif float_min == 0.15 and float_max == 0.38:
        exterior = "Field-Tested"
    elif float_min == 0.38 and float_max == 0.45:
        exterior = "Well-Worn"
    elif float_min == 0.45 and float_max == 1.0:
        exterior = "Battle-Scarred"
    
    # Возвращаемся к настройке фильтров
    await query.edit_message_text(
        f"✅ Диапазон Float для CS2 установлен: "
        f"{float_min:.3f} - {float_max:.3f} ({exterior})\n\n"
        "Возврат к настройке фильтров...",
        parse_mode="Markdown"
    )
    
    # Симулируем callback для возврата к фильтрам
    query.data = f"back_to_filters:{game}"
    await handle_back_to_filters_callback(update, context)


async def handle_set_category_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор категории.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем данные callback
    # Формат: "set_category:game:category"
    callback_data = query.data.split(":", 2)
    
    if len(callback_data) < 3:
        await query.edit_message_text(
            "❌ Ошибка: неверный формат данных callback для установки категории.",
            parse_mode="Markdown"
        )
        return
    
    game = callback_data[1]
    category = callback_data[2]
    
    # Сохраняем выбранную категорию
    if not hasattr(context, 'user_data'):
        context.user_data = {}
        
    if "game_filters" not in context.user_data:
        context.user_data["game_filters"] = {}
        
    if game not in context.user_data["game_filters"]:
        context.user_data["game_filters"][game] = {}
    
    context.user_data["game_filters"][game]["category"] = category
    
    # Возвращаемся к настройке фильтров
    await query.edit_message_text(
        f"✅ Категория для {GAMES_MAPPING.get(game, game)} установлена: {category}\n\n"
        "Возврат к настройке фильтров...",
        parse_mode="Markdown"
    )
    
    # Симулируем callback для возврата к фильтрам
    query.data = f"back_to_filters:{game}"
    await handle_back_to_filters_callback(update, context)


async def handle_set_rarity_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор редкости.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем данные callback
    # Формат: "set_rarity:game:rarity"
    callback_data = query.data.split(":", 2)
    
    if len(callback_data) < 3:
        await query.edit_message_text(
            "❌ Ошибка: неверный формат данных callback для установки редкости.",
            parse_mode="Markdown"
        )
        return
    
    game = callback_data[1]
    rarity = callback_data[2]
    
    # Сохраняем выбранную редкость
    if not hasattr(context, 'user_data'):
        context.user_data = {}
        
    if "game_filters" not in context.user_data:
        context.user_data["game_filters"] = {}
        
    if game not in context.user_data["game_filters"]:
        context.user_data["game_filters"][game] = {}
    
    context.user_data["game_filters"][game]["rarity"] = rarity
    
    # Возвращаемся к настройке фильтров
    await query.edit_message_text(
        f"✅ Редкость для {GAMES_MAPPING.get(game, game)} установлена: {rarity}\n\n"
        "Возврат к настройке фильтров...",
        parse_mode="Markdown"
    )
    
    # Симулируем callback для возврата к фильтрам
    query.data = f"back_to_filters:{game}"
    await handle_back_to_filters_callback(update, context)


async def handle_set_exterior_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор внешнего вида.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем данные callback
    # Формат: "set_exterior:game:exterior"
    callback_data = query.data.split(":", 2)
    
    if len(callback_data) < 3:
        await query.edit_message_text(
            "❌ Ошибка: неверный формат данных callback для установки внешнего вида.",
            parse_mode="Markdown"
        )
        return
    
    game = callback_data[1]
    exterior = callback_data[2]
    
    # Сохраняем выбранный внешний вид
    if not hasattr(context, 'user_data'):
        context.user_data = {}
        
    if "game_filters" not in context.user_data:
        context.user_data["game_filters"] = {}
        
    if game not in context.user_data["game_filters"]:
        context.user_data["game_filters"][game] = {}
    
    context.user_data["game_filters"][game]["exterior"] = exterior
    
    # Устанавливаем соответствующий диапазон float
    if exterior == "Factory New":
        context.user_data["game_filters"][game]["float_min"] = 0.0
        context.user_data["game_filters"][game]["float_max"] = 0.07
    elif exterior == "Minimal Wear":
        context.user_data["game_filters"][game]["float_min"] = 0.07
        context.user_data["game_filters"][game]["float_max"] = 0.15
    elif exterior == "Field-Tested":
        context.user_data["game_filters"][game]["float_min"] = 0.15
        context.user_data["game_filters"][game]["float_max"] = 0.38
    elif exterior == "Well-Worn":
        context.user_data["game_filters"][game]["float_min"] = 0.38
        context.user_data["game_filters"][game]["float_max"] = 0.45
    elif exterior == "Battle-Scarred":
        context.user_data["game_filters"][game]["float_min"] = 0.45
        context.user_data["game_filters"][game]["float_max"] = 1.0
    
    # Возвращаемся к настройке фильтров
    await query.edit_message_text(
        f"✅ Внешний вид для CS2 установлен: {exterior}\n\n"
        "Возврат к настройке фильтров...",
        parse_mode="Markdown"
    )
    
    # Симулируем callback для возврата к фильтрам
    query.data = f"back_to_filters:{game}"
    await handle_back_to_filters_callback(update, context)


async def handle_set_hero_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор героя.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем данные callback
    # Формат: "set_hero:game:hero"
    callback_data = query.data.split(":", 2)
    
    if len(callback_data) < 3:
        await query.edit_message_text(
            "❌ Ошибка: неверный формат данных callback для установки героя.",
            parse_mode="Markdown"
        )
        return
    
    game = callback_data[1]
    hero = callback_data[2]
    
    # Сохраняем выбранного героя
    if not hasattr(context, 'user_data'):
        context.user_data = {}
        
    if "game_filters" not in context.user_data:
        context.user_data["game_filters"] = {}
        
    if game not in context.user_data["game_filters"]:
        context.user_data["game_filters"][game] = {}
    
    context.user_data["game_filters"][game]["hero"] = hero
    
    # Возвращаемся к настройке фильтров
    await query.edit_message_text(
        f"✅ Герой для Dota 2 установлен: {hero}\n\n"
        "Возврат к настройке фильтров...",
        parse_mode="Markdown"
    )
    
    # Симулируем callback для возврата к фильтрам
    query.data = f"back_to_filters:{game}"
    await handle_back_to_filters_callback(update, context)


async def handle_set_class_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор класса.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем данные callback
    # Формат: "set_class:game:class"
    callback_data = query.data.split(":", 2)
    
    if len(callback_data) < 3:
        await query.edit_message_text(
            "❌ Ошибка: неверный формат данных callback для установки класса.",
            parse_mode="Markdown"
        )
        return
    
    game = callback_data[1]
    tf_class = callback_data[2]
    
    # Сохраняем выбранный класс
    if not hasattr(context, 'user_data'):
        context.user_data = {}
        
    if "game_filters" not in context.user_data:
        context.user_data["game_filters"] = {}
        
    if game not in context.user_data["game_filters"]:
        context.user_data["game_filters"][game] = {}
    
    context.user_data["game_filters"][game]["class"] = tf_class
    
    # Возвращаемся к настройке фильтров
    await query.edit_message_text(
        f"✅ Класс для Team Fortress 2 установлен: {tf_class}\n\n"
        "Возврат к настройке фильтров...",
        parse_mode="Markdown"
    )
    
    # Симулируем callback для возврата к фильтрам
    query.data = f"back_to_filters:{game}"
    await handle_back_to_filters_callback(update, context)


async def handle_select_game_filter_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор игры для фильтрации.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем данные callback
    # Формат: "select_game_filter:game"
    callback_data = query.data.split(":")
    
    if len(callback_data) < 2:
        await query.edit_message_text(
            "❌ Ошибка: неверный формат данных callback для выбора игры.",
            parse_mode="Markdown"
        )
        return
    
    game = callback_data[1]
    
    # Устанавливаем выбранную игру в контексте пользователя
    if not hasattr(context, 'user_data'):
        context.user_data = {}
    
    context.user_data["current_game"] = game
    
    # Возвращаемся к настройке фильтров
    query.data = f"back_to_filters:{game}"
    await handle_back_to_filters_callback(update, context)


async def handle_back_to_filters_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает возврат к настройке фильтров.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем данные callback
    # Формат: "back_to_filters:game"
    callback_data = query.data.split(":")
    
    if len(callback_data) < 2:
        # По умолчанию используем CSGO
        game = "csgo"
    else:
        game = callback_data[1]
    
    # Обновляем сообщение с настройкой фильтров
    update.message = query.message
    await handle_game_filters(update, context)
