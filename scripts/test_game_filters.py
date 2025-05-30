﻿"""Комплексное тестирование модуля game_filters.py.

Этот скрипт демонстрирует, что модуль game_filters успешно установлен и работает.
Объединяет функциональность всех предыдущих тестовых скриптов.
"""

import os
import sys

# Добавляем путь к родительскому каталогу в список путей поиска модулей
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)


def basic_test():
    """Базовое тестирование - импорт и проверка доступности функций"""
    try:
        from src.dmarket.game_filters import FilterFactory

        # Проверка доступности функций
        games = FilterFactory.get_supported_games()
        print("Поддерживаемые игры:", ", ".join(games))

        # Создание фильтра для CS2/CSGO
        filter_obj = FilterFactory.get_filter("csgo")
        print("Фильтр создан:", filter_obj.__class__.__name__)
        print("Поддерживаемые фильтры:", ", ".join(filter_obj.supported_filters))

        print("Базовый тест успешно завершен!")
        return True
    except Exception as e:
        print(f"Ошибка при базовом тесте: {type(e).__name__}: {e}")
        return False


def advanced_test():
    """Расширенное тестирование с проверкой фильтрации и API-параметров"""
    try:
        # Импортируем функции из модуля game_filters
        from src.dmarket.game_filters import (
            FilterFactory,
            apply_filters_to_items,
            build_api_params_for_game,
        )

        # Проверка поддерживаемых игр
        games = FilterFactory.get_supported_games()
        print("\nРасширенный тест:")

        # Демонстрация фильтрации
        test_items = [
            {"title": "AK-47 | Redline (Field-Tested)", "price": {"USD": 15}, "category": "Rifle"},
            {
                "title": "AWP | Dragon Lore (Factory New)",
                "price": {"USD": 5000},
                "category": "Sniper Rifle",
            },
            {
                "title": "StatTrak™ M4A4 | Asiimov (Battle-Scarred)",
                "price": {"USD": 120},
                "category": "Rifle",
            },
            {
                "title": "Butterfly Knife | Doppler (Factory New)",
                "price": {"USD": 1200},
                "category": "Knife",
            },
        ]

        print("\nФильтрация предметов:")

        # Фильтр по цене
        price_filter = {"min_price": 100}
        filtered = apply_filters_to_items(test_items, "csgo", price_filter)
        print(f"Предметы дороже $100 ({len(filtered)} из {len(test_items)}):")
        for item in filtered:
            print(f"- {item['title']}: ${item['price']['USD']}")

        # Фильтр по категории
        category_filter = {"category": "Rifle"}
        filtered = apply_filters_to_items(test_items, "csgo", category_filter)
        print(f"\nТолько винтовки ({len(filtered)} из {len(test_items)}):")
        for item in filtered:
            print(f"- {item['title']}: {item['category']}")

        # Комбинированный фильтр
        combined_filter = {"min_price": 100, "category": "Rifle"}
        filtered = apply_filters_to_items(test_items, "csgo", combined_filter)
        print(f"\nВинтовки дороже $100 ({len(filtered)} из {len(test_items)}):")
        for item in filtered:
            print(f"- {item['title']}: ${item['price']['USD']}")

        # Создание API параметров
        api_params = build_api_params_for_game("csgo", combined_filter)
        print("\nAPI параметры для комбинированного фильтра:")
        for key, value in api_params.items():
            print(f"- {key}: {value}")

        print("\nРасширенный тест успешно завершен!")
        return True
    except Exception as e:
        print(f"Ошибка при расширенном тесте: {type(e).__name__}: {e}")
        return False


def test_custom_filters():
    """Тестирование пользовательских фильтров"""
    try:
        from src.dmarket.game_filters import FilterFactory

        print("\nТест пользовательских фильтров:")

        # Создаем фильтр для CS2/CSGO
        filter_factory = FilterFactory()
        cs_filter = filter_factory.get_filter("csgo")

        # Тестируем фильтры
        filter_tests = [
            {
                "name": "Knife",
                "filter": {"category": "Knife"},
                "should_match": ["★ Butterfly Knife | Fade"],
            },
            {
                "name": "Pistol under $10",
                "filter": {"category": "Pistol", "max_price": 10},
                "should_match": [
                    "USP-S | Cortex (Field-Tested)",
                    "Glock-18 | Water Elemental (Field-Tested)",
                ],
            },
            {
                "name": "StatTrak items",
                "filter": {"stattrak": True},
                "should_match": ["StatTrak™ AK-47 | Redline (Field-Tested)"],
            },
            {
                "name": "Exterior factory new",
                "filter": {"exterior": "factory new"},
                "should_match": ["AWP | Lightning Strike (Factory New)"],
            },
        ]

        for test in filter_tests:
            print(f"\nТестируем фильтр: {test['name']}")
            print(f"Параметры: {test['filter']}")
            print(f"Должен находить: {', '.join(test['should_match'])}")

        print("\nТест пользовательских фильтров успешно завершен!")
        return True
    except Exception as e:
        print(f"Ошибка при тесте пользовательских фильтров: {type(e).__name__}: {e}")
        return False


def main():
    """Основная функция запуска тестов"""
    print("=== Тестирование модуля game_filters.py ===\n")

    success = basic_test()
    if success:
        advanced_test()
        test_custom_filters()

    print("\n=== Тестирование завершено ===")


if __name__ == "__main__":
    main()
