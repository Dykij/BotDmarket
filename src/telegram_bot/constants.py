
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
