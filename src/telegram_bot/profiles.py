# Работа с профилями пользователей Telegram-бота DMarket
import json
import os
import time

from .constants import USER_PROFILES_FILE

USER_PROFILES = {}


def save_user_profiles():
    """Сохраняет профили пользователей в файл"""
    try:
        with open(USER_PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(USER_PROFILES, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка при сохранении профилей: {e!s}")


def load_user_profiles():
    """Загружает профили пользователей из файла"""
    global USER_PROFILES
    try:
        if os.path.exists(USER_PROFILES_FILE):
            with open(USER_PROFILES_FILE, encoding="utf-8") as f:
                USER_PROFILES = json.load(f)
    except Exception as e:
        print(f"Ошибка при загрузке профилей: {e!s}")
        USER_PROFILES = {}


def get_user_profile(user_id: int) -> dict:
    """Получает профиль пользователя или создает новый.

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
                "risk_level": "medium",
            },
            "last_activity": time.time(),
        }
        save_user_profiles()
    USER_PROFILES[user_id_str]["last_activity"] = time.time()
    return USER_PROFILES[user_id_str]
