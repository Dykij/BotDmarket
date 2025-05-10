#!/usr/bin/env python3
"""Демонстрация работы с новой системой локализации и пользовательских профилей.
"""

import os
import sys

# Добавляем корневой каталог проекта в путь импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.telegram_bot.localization import LANGUAGES, LOCALIZATIONS


def simulate_user_interaction(user_id: int, name: str, language: str = "ru"):
    """Симулирует взаимодействие с пользователем на выбранном языке.

    Args:
        user_id: ID пользователя
        name: Имя пользователя
        language: Код языка

    """
    # Создаем профиль пользователя
    user_profile = {
        "language": language,
        "api_key": "demo_key",
        "api_secret": "demo_secret",
        "auto_trading_enabled": False,
        "trade_settings": {
            "min_profit": 2.0,
            "max_price": 50.0,
            "max_trades": 3,
            "risk_level": "medium",
        },
        "last_activity": 0,
    }

    # Сохраняем профиль в глобальный словарь профилей
    USER_PROFILES = {str(user_id): user_profile}

    # Определяем функцию для получения локализованного текста
    def get_localized_text(user_id: int, key: str, **kwargs) -> str:
        """Получает локализованный текст для пользователя.

        Args:
            user_id: ID пользователя Telegram
            key: Ключ локализации
            **kwargs: Дополнительные параметры для форматирования строки

        Returns:
            Локализованный текст

        """
        profile = USER_PROFILES.get(str(user_id))
        if not profile:
            return f"[No profile for user {user_id}]"

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

    # Получаем локализованное название языка
    display_language = LANGUAGES.get(language, language)

    # Выводим информацию о симуляции
    print("=== Симуляция взаимодействия с пользователем ===")
    print(f"ID пользователя: {user_id}")
    print(f"Имя: {name}")
    print(f"Язык: {display_language} ({language})")
    print("=" * 50)
    print()

    # Симулируем различные взаимодействия с ботом

    # 1. Приветствие
    welcome = get_localized_text(user_id, "welcome", user=name)
    print("1. Приветственное сообщение:")
    print(welcome)
    print("-" * 50)
    print()

    # 2. Помощь
    help_text = get_localized_text(user_id, "help")
    print("2. Сообщение справки:")
    print(help_text)
    print("-" * 50)
    print()

    # 3. Меню выбора режима арбитража
    select_mode = get_localized_text(user_id, "select_mode")
    print("3. Меню выбора режима арбитража:")
    print(select_mode)
    print()

    mode_options = [
        get_localized_text(user_id, "arbitrage_boost"),
        get_localized_text(user_id, "arbitrage_mid"),
        get_localized_text(user_id, "arbitrage_pro"),
        get_localized_text(user_id, "best_opportunities"),
        get_localized_text(user_id, "auto_arbitrage"),
    ]

    for option in mode_options:
        print(f"- {option}")
    print("-" * 50)
    print()

    # 4. Проверка статуса API
    checking_api = get_localized_text(user_id, "checking_api")
    api_ok = get_localized_text(user_id, "api_ok")

    print("4. Проверка статуса API:")
    print(checking_api)
    print("...")
    print(api_ok)
    print("-" * 50)
    print()

    # 5. Настройки
    settings = get_localized_text(user_id, "settings")
    language_text = get_localized_text(user_id, "language", lang=display_language)

    print("5. Настройки профиля:")
    print(settings)
    print()
    print(language_text)
    print("-" * 50)
    print()

    # 6. Автоматический арбитраж
    auto_searching = get_localized_text(user_id, "auto_searching")
    auto_found = get_localized_text(user_id, "auto_found", count=5)

    print("6. Автоматический арбитраж:")
    print(auto_searching)
    print("...")
    print(auto_found)
    print("-" * 50)
    print()

    # 7. Обработка ошибок
    error_text = get_localized_text(user_id, "error_general", error="Connection timeout")

    print("7. Обработка ошибок:")
    print(error_text)
    print("-" * 50)
    print()

    # 8. Финансовая информация
    balance = get_localized_text(user_id, "balance", balance=123.45)
    profit = get_localized_text(user_id, "profit", profit=15.75, percent=12.8)

    print("8. Финансовая информация:")
    print(balance)
    print(profit)
    print("-" * 50)
    print()


def main():
    """Основная функция демонстрации"""
    # Язык можно указать через аргументы командной строки
    if len(sys.argv) > 1 and sys.argv[1] in LANGUAGES:
        language = sys.argv[1]
    else:
        language = "ru"

    # Симулируем взаимодействие с пользователем
    simulate_user_interaction(
        user_id=123456789,
        name="Пользователь",
        language=language,
    )

    # Если указан второй язык, демонстрируем его тоже
    if len(sys.argv) > 2 and sys.argv[2] in LANGUAGES:
        print("\n\n")
        print("=" * 50)
        print(f"Переключаем на язык: {LANGUAGES[sys.argv[2]]}")
        print("=" * 50)
        print()

        simulate_user_interaction(
            user_id=987654321,
            name="User",
            language=sys.argv[2],
        )


if __name__ == "__main__":
    main()
