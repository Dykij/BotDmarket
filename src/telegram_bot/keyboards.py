"""Модуль клавиатур для Telegram бота.

Данный модуль содержит функции для создания клавиатур
различных типов (стандартные и инлайн) для Telegram бота,
согласно официальным рекомендациям Telegram Bot API.
"""

import logging
from typing import List, Optional, Union, Dict, Any

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LoginUrl,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
    ForceReply,
)

from src.dmarket.arbitrage import GAMES

logger = logging.getLogger(__name__)

# Константы для callback_data
CB_CANCEL = "cancel"
CB_BACK = "back"
CB_NEXT_PAGE = "next_page"
CB_PREV_PAGE = "prev_page"
CB_GAME_PREFIX = "game_"
CB_HELP = "help"
CB_SETTINGS = "settings"

# Основные клавиатуры бота


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Создает основное меню бота в виде inline клавиатуры."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Баланс", callback_data="balance"),
            InlineKeyboardButton("🔍 Поиск", callback_data="search"),
        ],
        [
            InlineKeyboardButton("💰 Арбитраж", callback_data="arbitrage"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
        ],
        [
            InlineKeyboardButton("📈 Рыночные тренды", callback_data="market_trends"),
            InlineKeyboardButton("🔔 Оповещения", callback_data="alerts"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру настроек бота."""
    keyboard = [
        [
            InlineKeyboardButton("🔑 API ключи", callback_data="settings_api_keys"),
            InlineKeyboardButton("🌐 Proxy", callback_data="settings_proxy"),
        ],
        [
            InlineKeyboardButton("💵 Валюта", callback_data="settings_currency"),
            InlineKeyboardButton("⏰ Интервалы", callback_data="settings_intervals"),
        ],
        [
            InlineKeyboardButton("📋 Фильтры", callback_data="settings_filters"),
            InlineKeyboardButton("🔄 Авто-обновление", callback_data="settings_auto_refresh"),
        ],
        [
            InlineKeyboardButton("« Назад", callback_data="back_to_main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_games_keyboard(callback_prefix: str = "game") -> InlineKeyboardMarkup:
    """Создает клавиатуру выбора игры.

    Args:
        callback_prefix: Префикс для callback_data

    Returns:
        InlineKeyboardMarkup с кнопками выбора игр

    """
    keyboard = []
    row = []

    game_icons = {
        "csgo": "🔫 CS:GO",
        "dota2": "🏆 Dota 2",
        "rust": "🏜️ Rust",
        "tf2": "🎯 TF2",
    }

    for i, game in enumerate(GAMES):
        button_text = game_icons.get(game, game)
        row.append(InlineKeyboardButton(button_text, callback_data=f"{callback_prefix}_{game}"))

        # По две кнопки в ряд
        if (i + 1) % 2 == 0 or i == len(GAMES) - 1:
            keyboard.append(row)
            row = []

    # Добавляем кнопку назад
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_main")])

    return InlineKeyboardMarkup(keyboard)


def get_arbitrage_keyboard():
    """Создает основную клавиатуру арбитража."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚀 Разгон баланса", callback_data="arbitrage_boost")],
            [InlineKeyboardButton("💼 Средний трейдер", callback_data="arbitrage_mid")],
            [InlineKeyboardButton("💎 Pro Арбитраж", callback_data="arbitrage_pro")],
            [InlineKeyboardButton("🤖 Автоматический арбитраж", callback_data="auto_arbitrage")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")],
        ]
    )


def get_price_range_keyboard(min_price: int = 0, max_price: int = 1000) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора ценового диапазона.

    Args:
        min_price: Минимальная цена в USD
        max_price: Максимальная цена в USD

    Returns:
        InlineKeyboardMarkup с кнопками ценовых диапазонов

    """
    # Создаем диапазоны в зависимости от максимальной цены
    if max_price <= 100:
        ranges = [(0, 10), (10, 25), (25, 50), (50, 100)]
    elif max_price <= 500:
        ranges = [(0, 20), (20, 50), (50, 100), (100, 200), (200, 500)]
    else:
        ranges = [(0, 50), (50, 100), (100, 300), (300, 500), (500, 1000), (1000, 2000)]

    keyboard = []
    row = []

    for i, (low, high) in enumerate(ranges):
        # Пропускаем диапазоны выше максимальной цены
        if low > max_price:
            continue

        adjusted_high = min(high, max_price)
        row.append(
            InlineKeyboardButton(
                f"${low}-${adjusted_high}",
                callback_data=f"price_{low}_{adjusted_high}",
            )
        )

        # По две кнопки в ряд
        if (i + 1) % 2 == 0 or i == len(ranges) - 1:
            keyboard.append(row)
            row = []

    # Добавляем произвольный диапазон
    keyboard.append([InlineKeyboardButton("Другой диапазон", callback_data="price_custom")])

    # Добавляем кнопку назад
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_filters")])

    return InlineKeyboardMarkup(keyboard)


def get_confirm_cancel_keyboard(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками подтверждения и отмены.

    Args:
        confirm_data: callback_data для кнопки подтверждения
        cancel_data: callback_data для кнопки отмены

    Returns:
        InlineKeyboardMarkup с кнопками

    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=confirm_data),
            InlineKeyboardButton("❌ Отмена", callback_data=cancel_data),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# Клавиатуры для фильтров


def get_filter_keyboard(game: str = "csgo") -> InlineKeyboardMarkup:
    """Создает клавиатуру с фильтрами для выбранной игры.

    Args:
        game: Код игры (csgo, dota2, rust, tf2)

    Returns:
        InlineKeyboardMarkup с кнопками фильтров

    """
    keyboard = [
        [
            InlineKeyboardButton("💰 Цена", callback_data=f"filter_{game}_price"),
            InlineKeyboardButton("🔄 Предложения", callback_data=f"filter_{game}_offers"),
        ],
    ]

    # Добавляем специфичные для игры фильтры
    if game == "csgo":
        keyboard.extend(
            [
                [
                    InlineKeyboardButton(
                        "🔫 Тип оружия", callback_data=f"filter_{game}_weapon_type"
                    ),
                    InlineKeyboardButton("🎨 Редкость", callback_data=f"filter_{game}_rarity"),
                ],
                [
                    InlineKeyboardButton("✨ Внешний вид", callback_data=f"filter_{game}_exterior"),
                    InlineKeyboardButton("🎭 Коллекции", callback_data=f"filter_{game}_collection"),
                ],
            ]
        )
    elif game == "dota2":
        keyboard.extend(
            [
                [
                    InlineKeyboardButton("👤 Герой", callback_data=f"filter_{game}_hero"),
                    InlineKeyboardButton("🎨 Редкость", callback_data=f"filter_{game}_rarity"),
                ],
                [
                    InlineKeyboardButton("🧩 Слот", callback_data=f"filter_{game}_slot"),
                    InlineKeyboardButton("🎭 Турниры", callback_data=f"filter_{game}_tournament"),
                ],
            ]
        )
    elif game == "rust":
        keyboard.extend(
            [
                [
                    InlineKeyboardButton("🔧 Категория", callback_data=f"filter_{game}_category"),
                    InlineKeyboardButton("🎨 Редкость", callback_data=f"filter_{game}_rarity"),
                ],
            ]
        )

    # Добавляем общие кнопки фильтров
    keyboard.extend(
        [
            [
                InlineKeyboardButton("🔍 Поиск по названию", callback_data=f"filter_{game}_search"),
                InlineKeyboardButton("🔄 Сброс фильтров", callback_data=f"filter_{game}_reset"),
            ],
            [
                InlineKeyboardButton("✅ Применить фильтры", callback_data=f"filter_{game}_apply"),
                InlineKeyboardButton("« Назад", callback_data="back_to_games"),
            ],
        ]
    )

    return InlineKeyboardMarkup(keyboard)


def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    items_per_page: int = 10,
    prefix: str = "page",
) -> InlineKeyboardMarkup:
    """Устаревшая функция для создания клавиатуры пагинации (для обратной совместимости).
    
    Использует новую унифицированную create_pagination_keyboard.

    Args:
        current_page: Текущая страница (начиная с 1)
        total_pages: Общее количество страниц
        items_per_page: Количество элементов на странице (не используется)
        prefix: Префикс для callback_data

    Returns:
        InlineKeyboardMarkup с кнопками навигации
    """
    # Конвертируем с 1-индексации на 0-индексацию для внутренней логики
    return create_pagination_keyboard(
        current_page - 1,  # конвертируем в 0-индексацию
        total_pages,
        prefix=prefix + "_",
        with_nums=True,
        back_button=True,
        back_text="« Назад",
        back_callback="back_to_filters",
        include_first_last=True
    )


def get_alert_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления оповещениями."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Создать оповещение", callback_data="alert_create"),
            InlineKeyboardButton("👁️ Мои оповещения", callback_data="alert_list"),
        ],
        [
            InlineKeyboardButton("⚙️ Настройки оповещений", callback_data="alert_settings"),
            InlineKeyboardButton("« Назад", callback_data="back_to_main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_alert_type_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора типа оповещения."""
    keyboard = [
        [
            InlineKeyboardButton("📉 Падение цены", callback_data="alert_type_price_drop"),
            InlineKeyboardButton("📈 Рост цены", callback_data="alert_type_price_rise"),
        ],
        [
            InlineKeyboardButton("📊 Изменение тренда", callback_data="alert_type_trend_change"),
            InlineKeyboardButton("💰 Выгодное предложение", callback_data="alert_type_good_deal"),
        ],
        [
            InlineKeyboardButton("« Назад", callback_data="back_to_alerts"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_alert_actions_keyboard(alert_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления конкретным оповещением.

    Args:
        alert_id: ID оповещения

    Returns:
        InlineKeyboardMarkup с кнопками действий

    """
    keyboard = [
        [
            InlineKeyboardButton("✏️ Изменить", callback_data=f"alert_edit_{alert_id}"),
            InlineKeyboardButton("❌ Удалить", callback_data=f"alert_delete_{alert_id}"),
        ],
        [
            InlineKeyboardButton("⏸️ Приостановить", callback_data=f"alert_pause_{alert_id}"),
            InlineKeyboardButton("« Назад", callback_data="back_to_alert_list"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# Клавиатуры для создания / редактирования фильтров


def get_csgo_exterior_keyboard(callback_prefix: str = "exterior") -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора внешнего вида предметов CS:GO.

    Args:
        callback_prefix: Префикс для callback_data

    Returns:
        InlineKeyboardMarkup с кнопками выбора внешнего вида

    """
    exteriors = [
        ("Factory New", "FN"),
        ("Minimal Wear", "MW"),
        ("Field-Tested", "FT"),
        ("Well-Worn", "WW"),
        ("Battle-Scarred", "BS"),
    ]

    keyboard = []
    row = []

    for i, (name, code) in enumerate(exteriors):
        row.append(InlineKeyboardButton(name, callback_data=f"{callback_prefix}_{code}"))

        # По две кнопки в ряд
        if (i + 1) % 2 == 0 or i == len(exteriors) - 1:
            keyboard.append(row)
            row = []

    # Добавляем кнопку "Все внешние виды"
    keyboard.append(
        [InlineKeyboardButton("Все внешние виды", callback_data=f"{callback_prefix}_all")]
    )

    # Добавляем кнопку назад
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_csgo_filters")])

    return InlineKeyboardMarkup(keyboard)


def get_rarity_keyboard(game: str, callback_prefix: str = "rarity") -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора редкости предметов.

    Args:
        game: Код игры (csgo, dota2, rust, tf2)
        callback_prefix: Префикс для callback_data

    Returns:
        InlineKeyboardMarkup с кнопками выбора редкости

    """
    rarities = []

    if game == "csgo":
        rarities = [
            ("🔴 Тайное", "Covert"),
            ("🟣 Засекреченное", "Classified"),
            ("🔵 Запрещенное", "Restricted"),
            ("🟢 Промышленное", "Mil-Spec Grade"),
            ("⚪ Ширпотреб", "Consumer Grade"),
            ("⭐ Исключительное", "Extraordinary"),
            ("🟡 Контрабанда", "Contraband"),
        ]
    elif game == "dota2":
        rarities = [
            ("🟣 Arcana", "Arcana"),
            ("🔴 Immortal", "Immortal"),
            ("🟡 Legendary", "Legendary"),
            ("🟠 Mythical", "Mythical"),
            ("🔵 Rare", "Rare"),
            ("🟢 Uncommon", "Uncommon"),
            ("⚪ Common", "Common"),
        ]
    elif game == "rust":
        rarities = [
            ("🔴 Extraordinary", "Extraordinary"),
            ("🟣 High End", "High End"),
            ("🟠 Elite", "Elite"),
            ("🟡 Rare", "Rare"),
            ("🔵 Uncommon", "Uncommon"),
            ("⚪ Common", "Common"),
        ]

    keyboard = []
    row = []

    for i, (name, code) in enumerate(rarities):
        row.append(InlineKeyboardButton(name, callback_data=f"{callback_prefix}_{code}"))

        # По две кнопки в ряд
        if (i + 1) % 2 == 0 or i == len(rarities) - 1:
            keyboard.append(row)
            row = []

    # Добавляем кнопку "Все редкости"
    keyboard.append([InlineKeyboardButton("Все редкости", callback_data=f"{callback_prefix}_all")])

    # Добавляем кнопку назад
    keyboard.append([InlineKeyboardButton("« Назад", callback_data=f"back_to_{game}_filters")])

    return InlineKeyboardMarkup(keyboard)


def get_csgo_weapon_type_keyboard(callback_prefix: str = "weapon") -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора типа оружия CS:GO.

    Args:
        callback_prefix: Префикс для callback_data

    Returns:
        InlineKeyboardMarkup с кнопками выбора типа оружия

    """
    weapon_types = [
        ("🔪 Ножи", "Knife"),
        ("🔫 Пистолеты", "Pistol"),
        ("🔫 Винтовки", "Rifle"),
        ("🔫 Снайперские", "Sniper Rifle"),
        ("🔫 Пистолеты-пулеметы", "SMG"),
        ("🔫 Дробовики", "Shotgun"),
        ("🔫 Пулеметы", "Machinegun"),
        ("🧤 Перчатки", "Gloves"),
        ("🥽 Наклейки", "Sticker"),
        ("📦 Контейнеры", "Container"),
    ]

    keyboard = []
    row = []

    for i, (name, code) in enumerate(weapon_types):
        row.append(InlineKeyboardButton(name, callback_data=f"{callback_prefix}_{code}"))

        # По две кнопки в ряд
        if (i + 1) % 2 == 0 or i == len(weapon_types) - 1:
            keyboard.append(row)
            row = []

    # Добавляем кнопку "Все типы"
    keyboard.append([InlineKeyboardButton("Все типы", callback_data=f"{callback_prefix}_all")])

    # Добавляем кнопку назад
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_csgo_filters")])

    return InlineKeyboardMarkup(keyboard)


# Новые функции для современных возможностей Telegram


def get_webapp_keyboard(title: str, webapp_url: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой открытия WebApp.

    Args:
        title (str): Текст кнопки
        webapp_url (str): URL для WebApp

    Returns:
        InlineKeyboardMarkup: Клавиатура с WebApp кнопкой

    """
    keyboard = [
        [
            InlineKeyboardButton(
                title,
                web_app=WebAppInfo(url=webapp_url),
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_dmarket_webapp_keyboard():
    """Создает клавиатуру с WebApp DMarket."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🌐 Открыть DMarket",
                    web_app=WebAppInfo(url="https://dmarket.com"),
                )
            ],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")],
        ]
    )


def get_payment_keyboard(title: str, payment_provider_token: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой оплаты.

    Args:
        title (str): Текст кнопки
        payment_provider_token (str): Токен платежного провайдера

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой оплаты

    """
    keyboard = [
        [InlineKeyboardButton(title, pay=True)],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_login_keyboard(
    title: str, login_url: str, forward_text: str = None
) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой для входа через Telegram Login Widget.

    Args:
        title (str): Текст кнопки
        login_url (str): URL для авторизации
        forward_text (str, optional): Текст после авторизации

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой входа

    """
    login_info = LoginUrl(
        url=login_url,
        forward_text=forward_text,
        bot_username=None,
    )

    keyboard = [
        [InlineKeyboardButton(title, login_url=login_info)],
    ]
    return InlineKeyboardMarkup(keyboard)


def remove_keyboard() -> ReplyKeyboardRemove:
    """Удаляет клавиатуру.

    Returns:
        ReplyKeyboardRemove: Объект удаления клавиатуры

    """
    return ReplyKeyboardRemove()


def get_request_contact_keyboard(text: str = "Поделиться контактом") -> ReplyKeyboardMarkup:
    """Создает клавиатуру с кнопкой запроса контакта.

    Args:
        text (str): Текст кнопки

    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой запроса контакта

    """
    keyboard = [
        [KeyboardButton(text, request_contact=True)],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_request_location_keyboard(text: str = "Поделиться местоположением") -> ReplyKeyboardMarkup:
    """Создает клавиатуру с кнопкой запроса местоположения.

    Args:
        text (str): Текст кнопки

    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой запроса местоположения

    """
    keyboard = [
        [KeyboardButton(text, request_location=True)],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_combined_web_app_keyboard(items: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру с несколькими WebApp кнопками.

    Args:
        items (List[Tuple[str, str]]): Список пар (текст кнопки, URL)

    Returns:
        InlineKeyboardMarkup: Клавиатура с WebApp кнопками

    """
    keyboard = []
    row = []

    for i, (text, url) in enumerate(items):
        row.append(
            InlineKeyboardButton(
                text,
                web_app=WebAppInfo(url=url),
            )
        )

        # По две кнопки в ряд
        if (i + 1) % 2 == 0 or i == len(items) - 1:
            keyboard.append(row)
            row = []

    # Добавляем кнопку назад
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_main")])

    return InlineKeyboardMarkup(keyboard)


def get_marketplace_comparison_keyboard():
    """Создает клавиатуру сравнения маркетплейсов."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔫 CS2 - Steam/DMarket", callback_data="compare:csgo:steam_dmarket"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔫 CS2 - Skinport/DMarket", callback_data="compare:csgo:skinport_dmarket"
                )
            ],
            [
                InlineKeyboardButton(
                    "🏆 Dota 2 - Steam/DMarket", callback_data="compare:dota2:steam_dmarket"
                )
            ],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")],
        ]
    )


def get_modern_arbitrage_keyboard():
    """Создает современную клавиатуру с функциями арбитража."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔍 DMarket Арбитраж", callback_data="dmarket_arbitrage")],
            [InlineKeyboardButton("💰 Лучшие предложения", callback_data="best_opportunities")],
            [
                InlineKeyboardButton("🎮 Выбор игры", callback_data="game_selection"),
                InlineKeyboardButton("⚙️ Фильтры", callback_data="filter:"),
            ],
            [InlineKeyboardButton("🤖 Автоматический арбитраж", callback_data="auto_arbitrage")],
            [
                InlineKeyboardButton("📊 Анализ рынка", callback_data="market_analysis"),
                InlineKeyboardButton("📈 Сравнение", callback_data="market_comparison"),
            ],
            [InlineKeyboardButton("🌐 Открыть DMarket WebApp", callback_data="open_webapp")],
        ]
    )


def get_auto_arbitrage_keyboard():
    """Создает клавиатуру выбора режима автоматического арбитража."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🚀 Boost (Низкая прибыль)", callback_data="auto_start:boost_low"
                )
            ],
            [
                InlineKeyboardButton(
                    "💰 Medium (Средняя прибыль)", callback_data="auto_start:mid_medium"
                )
            ],
            [InlineKeyboardButton("💎 Pro (Высокая прибыль)", callback_data="auto_start:pro_high")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")],
        ]
    )


def get_game_selection_keyboard():
    """Создает клавиатуру выбора игры."""
    games = {
        "csgo": "CS2",
        "dota2": "Dota 2",
        "rust": "Rust",
        "tf2": "Team Fortress 2",
    }
    keyboard = []
    icons = {"csgo": "🔫", "dota2": "🏆", "rust": "🏝️", "tf2": "🎩"}

    for game_code, game_name in games.items():
        icon = icons.get(game_code, "🎮")
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{icon} {game_name}", callback_data=f"game_selected:{game_code}"
                )
            ]
        )

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_back_to_arbitrage_keyboard():
    """Создает клавиатуру с кнопкой возврата к арбитражу."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⬅️ Вернуться к арбитражу", callback_data="arbitrage")],
        ]
    )


def get_webapp_button():
    """Создает кнопку для открытия WebApp."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🌐 Открыть DMarket",
                    web_app=WebAppInfo(url="https://dmarket.com"),
                )
            ],
        ]
    )


def get_permanent_reply_keyboard() -> ReplyKeyboardMarkup:
    """Создает постоянную клавиатуру для основных функций бота.

    Returns:
        ReplyKeyboardMarkup с основными функциями

    """
    keyboard = [
        [
            KeyboardButton("📊 Баланс"),
            KeyboardButton("🔍 Поиск"),
        ],
        [
            KeyboardButton("💰 Арбитраж"),
            KeyboardButton("⚙️ Настройки"),
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,  # Заменено с is_persistent на противоположное значение
        input_field_placeholder="Выберите функцию или введите команду",
    )


def create_main_keyboard(include_all_buttons: bool = True) -> ReplyKeyboardMarkup:
    """Создает основную клавиатуру бота.
    
    Args:
        include_all_buttons: Включать ли все кнопки или только основные
        
    Returns:
        ReplyKeyboardMarkup: Основная клавиатура
    """
    if include_all_buttons:
        keyboard = [
            [
                KeyboardButton("📊 Баланс"),
                KeyboardButton("🔍 Поиск"),
            ],
            [
                KeyboardButton("💰 Арбитраж"),
                KeyboardButton("📈 Аналитика"),
            ],
            [
                KeyboardButton("⚙️ Настройки"),
                KeyboardButton("ℹ️ Помощь"),
            ],
        ]
    else:
        keyboard = [
            [
                KeyboardButton("📊 Баланс"),
                KeyboardButton("🔍 Поиск"),
            ],
            [
                KeyboardButton("💰 Арбитраж"),
                KeyboardButton("⚙️ Настройки"),
            ],
        ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,  # Заменено с is_persistent на противоположное значение
        input_field_placeholder="Выберите функцию или введите команду",
    )


def create_game_selection_keyboard() -> InlineKeyboardMarkup:
    """Создает инлайн-клавиатуру выбора игры.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с играми
    """
    keyboard = [
        [
            InlineKeyboardButton("CS:GO", callback_data=f"{CB_GAME_PREFIX}csgo"),
            InlineKeyboardButton("Dota 2", callback_data=f"{CB_GAME_PREFIX}dota2")
        ],
        [
            InlineKeyboardButton("Rust", callback_data=f"{CB_GAME_PREFIX}rust"),
            InlineKeyboardButton("Team Fortress 2", callback_data=f"{CB_GAME_PREFIX}tf2")
        ],
        [InlineKeyboardButton("Отмена", callback_data=CB_CANCEL)]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_settings_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру настроек.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура настроек
    """
    keyboard = [
        [
            InlineKeyboardButton("API ключи", callback_data="settings_api_keys"),
            InlineKeyboardButton("Уведомления", callback_data="settings_notifications")
        ],
        [
            InlineKeyboardButton("Автоматизация", callback_data="settings_automation"),
            InlineKeyboardButton("Языки", callback_data="settings_language")
        ],
        [InlineKeyboardButton("Назад", callback_data=CB_BACK)]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def create_confirm_keyboard(
    confirm_text: str = "Подтвердить", 
    cancel_text: str = "Отмена",
    confirm_data: str = "confirm",
    cancel_data: str = CB_CANCEL
) -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения действия.
    
    Args:
        confirm_text: Текст кнопки подтверждения
        cancel_text: Текст кнопки отмены
        confirm_data: callback_data для подтверждения
        cancel_data: callback_data для отмены
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками подтверждения и отмены
    """
    keyboard = [
        [
            InlineKeyboardButton(confirm_text, callback_data=confirm_data),
            InlineKeyboardButton(cancel_text, callback_data=cancel_data)
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


# Унифицированная клавиатура пагинации
def create_pagination_keyboard(
    current_page: int,
    total_pages: int,
    prefix: str = "",
    with_nums: bool = True,
    back_button: bool = True,
    back_text: str = "« Назад",
    back_callback: str = CB_BACK,
    include_first_last: bool = False
) -> InlineKeyboardMarkup:
    """Создает клавиатуру с пагинацией.
    
    Args:
        current_page: Текущая страница (начиная с 0)
        total_pages: Общее количество страниц
        prefix: Префикс для callback_data
        with_nums: Добавлять ли номера страниц
        back_button: Добавлять ли кнопку "Назад"
        back_text: Текст кнопки "Назад"
        back_callback: callback_data для кнопки "Назад"
        include_first_last: Добавлять ли кнопки "Первая" и "Последняя"
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с пагинацией
    """
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    
    # Кнопки "В начало" и "Первая" если не на первой странице и если запрошено
    if include_first_last and current_page > 0:
        nav_buttons.append(
            InlineKeyboardButton("« Первая", callback_data=f"{prefix}{CB_PREV_PAGE}_0")
        )
    
    # Кнопка "Назад"
    if current_page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                "◀️", 
                callback_data=f"{prefix}{CB_PREV_PAGE}_{current_page}"
            )
        )
    
    # Номер страницы (если запрошено)
    if with_nums:
        nav_buttons.append(
            InlineKeyboardButton(
                f"{current_page + 1}/{total_pages}",
                callback_data=f"page_info_{current_page}"
            )
        )
    
    # Кнопка "Вперед"
    if current_page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                "▶️", 
                callback_data=f"{prefix}{CB_NEXT_PAGE}_{current_page}"
            )
        )
    
    # Кнопка "В конец" и "Последняя" если не на последней странице и если запрошено
    if include_first_last and current_page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                "Последняя »", 
                callback_data=f"{prefix}{CB_NEXT_PAGE}_{total_pages - 1}"
            )
        )
    
    keyboard.append(nav_buttons)
    
    # Кнопка "Назад к меню"
    if back_button:
        keyboard.append([InlineKeyboardButton(back_text, callback_data=back_callback)])
    
    return InlineKeyboardMarkup(keyboard)


# Функции для создания специализированных клавиатур

def create_arbitrage_keyboard(
    include_auto: bool = True,
    include_analysis: bool = True
) -> InlineKeyboardMarkup:
    """Создает клавиатуру для арбитража.
    
    Args:
        include_auto: Включать ли автоматический арбитраж
        include_analysis: Включать ли анализ арбитража
        
    Returns:
        InlineKeyboardMarkup: Клавиатура арбитража
    """
    keyboard = []
    
    # Основные режимы арбитража
    keyboard.append([
        InlineKeyboardButton("Низкий 🔎 ($1-5)", callback_data="arbitrage_low"),
        InlineKeyboardButton("Средний 💰 ($5-20)", callback_data="arbitrage_mid")
    ])
    
    keyboard.append([
        InlineKeyboardButton("Высокий 💎 ($20-100)", callback_data="arbitrage_high"),
        InlineKeyboardButton("Настраиваемый ⚙️", callback_data="arbitrage_custom")
    ])
    
    # Автоматический арбитраж (если включен)
    if include_auto:
        keyboard.append([
            InlineKeyboardButton("Автоматический арбитраж 🤖", callback_data="arbitrage_auto")
        ])
    
    # Анализ арбитража (если включен)
    if include_analysis:
        keyboard.append([
            InlineKeyboardButton("Анализ возможностей 📊", callback_data="arbitrage_analysis")
        ])
    
    # Кнопка назад
    keyboard.append([InlineKeyboardButton("Назад", callback_data=CB_BACK)])
    
    return InlineKeyboardMarkup(keyboard)

def create_market_analysis_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для анализа рынка.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура анализа рынка
    """
    keyboard = [
        [
            InlineKeyboardButton("Изменения цен 📈", callback_data="analysis_price_changes"),
            InlineKeyboardButton("Тренды 🔥", callback_data="analysis_trends")
        ],
        [
            InlineKeyboardButton("Волатильность 📊", callback_data="analysis_volatility"),
            InlineKeyboardButton("Отчёт 📝", callback_data="analysis_report")
        ],
        [
            InlineKeyboardButton("Недооцененные предметы 🔍", callback_data="analysis_undervalued"),
            InlineKeyboardButton("Инвестиции 💼", callback_data="analysis_investments")
        ],
        [InlineKeyboardButton("Назад", callback_data=CB_BACK)]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def create_price_alerts_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для оповещений о ценах.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура оповещений о ценах
    """
    keyboard = [
        [
            InlineKeyboardButton("Добавить оповещение ➕", callback_data="alerts_add"),
            InlineKeyboardButton("Мои оповещения 📋", callback_data="alerts_list")
        ],
        [
            InlineKeyboardButton("Удалить оповещение ❌", callback_data="alerts_remove"),
            InlineKeyboardButton("Настройки оповещений ⚙️", callback_data="alerts_settings")
        ],
        [InlineKeyboardButton("Назад", callback_data=CB_BACK)]
    ]
    
    return InlineKeyboardMarkup(keyboard)

# Вспомогательные функции

def force_reply() -> ForceReply:
    """Создает объект принудительного ответа.
    
    Returns:
        ForceReply: Объект принудительного ответа
    """
    return ForceReply(selective=True)

def extract_callback_data(callback_data: str, prefix: str) -> str:
    """Извлекает данные из callback_data, удаляя префикс.
    
    Args:
        callback_data: Исходный callback_data
        prefix: Префикс для удаления
        
    Returns:
        str: callback_data без префикса
    """
    if callback_data and callback_data.startswith(prefix):
        return callback_data[len(prefix):]
    return callback_data

def build_menu(
    buttons: List[InlineKeyboardButton],
    n_cols: int = 2,
    header_buttons: Optional[List[InlineKeyboardButton]] = None,
    footer_buttons: Optional[List[InlineKeyboardButton]] = None
) -> List[List[InlineKeyboardButton]]:
    """Создает меню с кнопками в указанном количестве столбцов.
    
    Args:
        buttons: Список кнопок InlineKeyboardButton
        n_cols: Количество столбцов
        header_buttons: Кнопки заголовка (отдельная строка)
        footer_buttons: Кнопки футера (отдельная строка)
        
    Returns:
        List[List[InlineKeyboardButton]]: Двумерный список кнопок для InlineKeyboardMarkup
    """
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    
    if header_buttons:
        menu.insert(0, header_buttons)
    
    if footer_buttons:
        menu.append(footer_buttons)
    
    return menu
