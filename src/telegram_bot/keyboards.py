"""
Модуль с функциями для создания клавиатур для Telegram-бота.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.dmarket.arbitrage import GAMES


def get_arbitrage_keyboard():
    """Создает клавиатуру для выбора режима арбитража."""
    keyboard = [
        [
            InlineKeyboardButton("🚀 Разгон баланса", callback_data="arbitrage_boost"),
            InlineKeyboardButton("💼 Средний трейдер", callback_data="arbitrage_mid")
        ],
        [
            InlineKeyboardButton("💰 Trade Pro", callback_data="arbitrage_pro"),
            InlineKeyboardButton("🌟 Лучшие возможности", 
                               callback_data="best_opportunities")
        ],
        [
            InlineKeyboardButton("🤖 Авто-арбитраж", callback_data="auto_arbitrage")
        ],
        [
            InlineKeyboardButton("🎮 Выбрать игру", callback_data="select_game")
        ],
        [
            InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_game_selection_keyboard():
    """Создает клавиатуру для выбора игры."""
    keyboard = []
    
    # Добавляем кнопки для каждой игры (по 2 в строке)
    game_buttons = []
    for game_code, game_name in GAMES.items():
        game_buttons.append(
            InlineKeyboardButton(game_name, callback_data=f"game:{game_code}")
        )
        
        # Каждые 2 кнопки добавляем новую строку в клавиатуру
        if len(game_buttons) == 2:
            keyboard.append(game_buttons)
            game_buttons = []
    
    # Если остались непарные кнопки
    if game_buttons:
        keyboard.append(game_buttons)
    
    # Добавляем кнопку возврата
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад", callback_data="arbitrage")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_auto_arbitrage_keyboard():
    """Создает клавиатуру для выбора режима автоматического арбитража."""
    keyboard = [
        [
            InlineKeyboardButton("💰 Мин. прибыль", 
                               callback_data="auto_start:auto_low")
        ],
        [
            InlineKeyboardButton("💰💰 Средняя прибыль", 
                               callback_data="auto_start:auto_medium")
        ],
        [
            InlineKeyboardButton("💰💰💰 Высокая прибыль", 
                               callback_data="auto_start:auto_high")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="auto_stats")
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data="arbitrage")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_arbitrage_keyboard():
    """Создает клавиатуру с кнопкой возврата к меню арбитража."""
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Назад к меню арбитража", 
                               callback_data="arbitrage")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard(auto_trading_enabled=False):
    """
    Создает клавиатуру для меню настроек.
    
    Args:
        auto_trading_enabled: Флаг, включена ли автоматическая торговля
        
    Returns:
        Разметка клавиатуры с кнопками для настроек пользователя
    """
    keyboard = [
        [
            InlineKeyboardButton("🔑 API ключи", callback_data="settings_api_keys")
        ],
        [
            InlineKeyboardButton("🌐 Язык", callback_data="settings_language")
        ],
        [
            InlineKeyboardButton(
                "🤖 Авто-торговля: " + ("✅ Вкл." if auto_trading_enabled else "❌ Выкл."), 
                callback_data="settings_toggle_trading"
            )
        ],
        [
            InlineKeyboardButton("💰 Лимиты торговли", callback_data="settings_limits")
        ],
        [
            InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_language_keyboard(current_language="ru"):
    """
    Создает клавиатуру для выбора языка интерфейса.
    
    Args:
        current_language: Текущий выбранный язык
        
    Returns:
        Разметка клавиатуры с кнопками для выбора языка
    """
    # Поддерживаемые языки
    languages = {
        "ru": "🇷🇺 Русский",
        "en": "🇬🇧 English",
        "es": "🇪🇸 Español",
        "de": "🇩🇪 Deutsch"
    }
    
    keyboard = []
    # Добавляем кнопки для каждого языка (по 2 в строке)
    lang_buttons = []
    
    for lang_code, lang_name in languages.items():
        # Добавляем отметку к текущему выбранному языку
        button_text = f"{lang_name} ✅" if lang_code == current_language else lang_name
        
        lang_buttons.append(
            InlineKeyboardButton(button_text, callback_data=f"language:{lang_code}")
        )
        
        # Каждые 2 кнопки добавляем новую строку в клавиатуру
        if len(lang_buttons) == 2:
            keyboard.append(lang_buttons)
            lang_buttons = []
    
    # Если остались непарные кнопки
    if lang_buttons:
        keyboard.append(lang_buttons)
    
    # Добавляем кнопку возврата в настройки
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад к настройкам", callback_data="settings")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_risk_profile_keyboard(current_profile="medium"):
    """
    Создает клавиатуру для выбора профиля риска арбитражной торговли.
    
    Args:
        current_profile: Текущий выбранный профиль риска
        
    Returns:
        Разметка клавиатуры с кнопками для выбора профиля риска
    """
    profiles = {
        "low": "🟢 Низкий риск",
        "medium": "🟡 Средний риск",
        "high": "🔴 Высокий риск",
    }
    
    keyboard = []
    
    for profile_code, profile_name in profiles.items():
        # Добавляем отметку к текущему выбранному профилю
        button_text = f"{profile_name} ✅" if profile_code == current_profile else profile_name
        
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"risk:{profile_code}")
        ])
    
    # Добавляем кнопку возврата в настройки торговли
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад к настройкам торговли", callback_data="settings_limits")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_back_to_settings_keyboard():
    """
    Создает клавиатуру с кнопкой возврата в настройки.
    
    Returns:
        Разметка клавиатуры с кнопкой возврата
    """
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Назад к настройкам", callback_data="settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
