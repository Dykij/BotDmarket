"""
Константы для работы Telegram-бота.
"""

# Основные константы и настройки для Telegram-бота DMarket
import os

# Путь к .env файлу
ENV_PATH = os.path.join(os.path.dirname(__file__), '.env')

# Путь к файлу профилей пользователей
USER_PROFILES_FILE = os.path.join(os.path.dirname(__file__), "user_profiles.json")

# Поддерживаемые языки
LANGUAGES = {
    "ru": "Русский",
    "en": "English",
    "es": "Español",
    "de": "Deutsch"
}

# Названия режимов арбитража
ARBITRAGE_MODES = {
    "boost": "Разгон баланса",
    "mid": "Средний трейдер",
    "pro": "Trade Pro",
    "best": "Лучшие возможности",
    "auto": "Авто-арбитраж"
}

# Константы для хранения ценовых оповещений
PRICE_ALERT_STORAGE_KEY = "price_alerts"
PRICE_ALERT_HISTORY_KEY = "price_alert_history"

# Константы для пагинации
DEFAULT_PAGE_SIZE = 5
MAX_ITEMS_PER_PAGE = 10

# Константы для интерфейса
MAX_MESSAGE_LENGTH = 4096
