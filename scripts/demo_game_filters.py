"""Демонстрационный скрипт для модуля game_filters.
"""
import json
import os
import sys

# Добавляем корневой каталог проекта в путь поиска модулей Python
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.dmarket.game_filters import (
    FilterFactory,
    apply_filters_to_items,
    build_api_params_for_game,
)


def print_separator() -> None:
    """Печатает разделительную линию."""
    print("-" * 60)


def print_section_header(title: str) -> None:
    """Печатает заголовок раздела."""
    print_separator()
    print(f"## {title}")
    print_separator()


def print_filter_support() -> None:
    """Выводит список поддерживаемых игр и фильтров."""
    print_section_header("Поддерживаемые игры")

    games = FilterFactory.get_supported_games()
    print(f"Поддерживаемые игры: {', '.join(games)}")

    print("\nПоддерживаемые фильтры для каждой игры:")
    for game in games:
        filter_obj = FilterFactory.get_filter(game)
        print(f"  - {game.upper()}: {', '.join(filter_obj.supported_filters)}")

    print("\nОбщие фильтры для всех игр:")
    base_filters = FilterFactory.get_filter("csgo").__class__.__base__.supported_filters
    print(f"  {', '.join(base_filters)}")


def demo_cs2_filters() -> None:
    """Демонстрация фильтров для CS2/CSGO."""
    print_section_header("Демонстрация фильтров CS2/CSGO")

    # Создаем список тестовых предметов
    items = [
        {
            "title": "AWP | Dragon Lore (Factory New)",
            "price": {"USD": 5000},
            "category": "Sniper Rifle",
            "rarity": "Covert",
            "float": 0.01,
        },
        {
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {"USD": 15},
            "category": "Rifle",
            "rarity": "Classified",
            "float": 0.25,
        },
        {
            "title": "StatTrak™ M4A4 | Asiimov (Battle-Scarred)",
            "price": {"USD": 120},
            "category": "Rifle",
            "rarity": "Covert",
            "float": 0.9,
        },
        {
            "title": "Butterfly Knife | Doppler (Factory New)",
            "price": {"USD": 1200},
            "category": "Knife",
            "rarity": "Covert",
            "float": 0.01,
        },
        {
            "title": "Souvenir AWP | Safari Mesh (Field-Tested)",
            "price": {"USD": 30},
            "category": "Sniper Rifle",
            "rarity": "Industrial Grade",
            "float": 0.3,
        },
    ]

    # Демонстрация различных фильтров
    filters = [
        {"min_price": 100, "description": "Предметы дороже $100"},
        {"category": "Rifle", "description": "Только винтовки"},
        {"rarity": "Covert", "description": "Только предметы редкости Covert"},
        {"exterior": "Factory New", "description": "Только Factory New"},
        {"float_max": 0.1, "description": "С флоатом не более 0.1"},
        {"stattrak": True, "description": "Только StatTrak"},
        {"souvenir": True, "description": "Только Souvenir"},
        {
            "min_price": 50,
            "category": "Sniper Rifle",
            "description": "Снайперские винтовки дороже $50",
        },
    ]

    print(f"Исходный список предметов ({len(items)} шт.):")
    for i, item in enumerate(items, 1):
        price = item["price"]["USD"]
        print(
            f"  {i}. {item['title']} - ${price} ({item['category']}, {item['rarity']}, float: {item['float']})"
        )

    print("\nПрименение различных фильтров:")
    for i, filter_dict in enumerate(filters, 1):
        description = filter_dict.pop("description", "")
        filtered_items = apply_filters_to_items(items, "csgo", filter_dict)

        print(f"\n{i}. {description} ({len(filtered_items)} шт.):")
        for j, item in enumerate(filtered_items, 1):
            price = item["price"]["USD"]
            print(f"  {j}. {item['title']} - ${price}")

        # Восстановим описание для последующего использования
        filter_dict["description"] = description

    # Демонстрация построения API параметров
    print("\nПостроение API параметров для запроса к DMarket:")
    api_filter = {
        "min_price": 50,
        "max_price": 500,
        "category": "Rifle",
        "exterior": "Field-Tested",
        "float_min": 0.15,
        "float_max": 0.37,
    }

    api_params = build_api_params_for_game("csgo", api_filter)
    print(f"Фильтр: {json.dumps(api_filter, indent=2)}")
    print(f"API параметры: {json.dumps(api_params, indent=2)}")


def demo_dota2_filters() -> None:
    """Демонстрация фильтров для Dota 2."""
    print_section_header("Демонстрация фильтров Dota 2")

    # Создаем список тестовых предметов
    items = [
        {
            "title": "Arcana Phantom Assassin",
            "price": {"USD": 35},
            "hero": "Phantom Assassin",
            "rarity": "Arcana",
            "slot": "Weapon",
            "quality": "Exalted",
            "tradable": True,
        },
        {
            "title": "Genuine Weather Rain",
            "price": {"USD": 5},
            "rarity": "Mythical",
            "slot": "Weather Effect",
            "quality": "Genuine",
            "tradable": True,
        },
        {
            "title": "Inscribed Pudge Hook",
            "price": {"USD": 120},
            "hero": "Pudge",
            "rarity": "Immortal",
            "slot": "Weapon",
            "quality": "Inscribed",
            "tradable": True,
        },
        {
            "title": "Unusual Courier",
            "price": {"USD": 80},
            "rarity": "Immortal",
            "slot": "Courier",
            "quality": "Unusual",
            "tradable": False,
        },
    ]

    # Демонстрация различных фильтров
    filters = [
        {"min_price": 30, "description": "Предметы дороже $30"},
        {"hero": "Pudge", "description": "Только предметы для Pudge"},
        {"rarity": "Immortal", "description": "Только Immortal предметы"},
        {"slot": "Weapon", "description": "Только оружие"},
        {"quality": "Unusual", "description": "Только Unusual качество"},
        {"tradable": True, "description": "Только обмениваемые предметы"},
        {
            "rarity": "Immortal",
            "tradable": True,
            "description": "Обмениваемые Immortal предметы",
        },
    ]

    print(f"Исходный список предметов ({len(items)} шт.):")
    for i, item in enumerate(items, 1):
        price = item["price"]["USD"]
        hero = item.get("hero", "Нет героя")
        print(f"  {i}. {item['title']} - ${price} ({hero}, {item['rarity']}, {item['quality']})")

    print("\nПрименение различных фильтров:")
    for i, filter_dict in enumerate(filters, 1):
        description = filter_dict.pop("description", "")
        filtered_items = apply_filters_to_items(items, "dota2", filter_dict)

        print(f"\n{i}. {description} ({len(filtered_items)} шт.):")
        for j, item in enumerate(filtered_items, 1):
            price = item["price"]["USD"]
            print(f"  {j}. {item['title']} - ${price}")

        # Восстановим описание для последующего использования
        filter_dict["description"] = description


def demo_filter_descriptions() -> None:
    """Демонстрация человеко-читаемых описаний фильтров."""
    print_section_header("Человеко-читаемые описания фильтров")

    filters_by_game = {
        "csgo": [
            {
                "min_price": 50,
                "max_price": 500,
                "category": "Rifle",
                "rarity": "Classified",
                "exterior": "Field-Tested",
                "float_min": 0.15,
                "float_max": 0.37,
            },
            {
                "min_price": 1000,
                "category": "Knife",
                "stattrak": True,
            },
            {
                "category": "Sniper Rifle",
                "rarity": "Covert",
                "souvenir": True,
            },
        ],
        "dota2": [
            {
                "min_price": 20,
                "hero": "Juggernaut",
                "rarity": "Immortal",
                "slot": "Weapon",
                "quality": "Genuine",
                "tradable": True,
            },
            {
                "min_price": 100,
                "rarity": "Arcana",
            },
        ],
        "tf2": [
            {
                "min_price": 5,
                "max_price": 50,
                "class": "Scout",
                "quality": "Unusual",
                "type": "Hat",
            },
            {
                "class": "Heavy",
                "effect": "Burning Flames",
                "killstreak": "Professional",
                "australium": True,
            },
        ],
        "rust": [
            {
                "min_price": 10,
                "category": "Weapon",
                "type": "Assault Rifle",
                "rarity": "Legendary",
            },
        ],
    }

    for game, filters in filters_by_game.items():
        print(f"\nОписания фильтров для {game.upper()}:")
        filter_obj = FilterFactory.get_filter(game)

        for i, filter_dict in enumerate(filters, 1):
            description = filter_obj.get_filter_description(filter_dict)
            print(f"  {i}. {description}")


def main() -> None:
    """Основная функция демонстрации."""
    print_section_header("Система фильтрации предметов DMarket")
    print(
        """Этот скрипт демонстрирует возможности системы фильтрации предметов
для различных игр на маркетплейсе DMarket. Система поддерживает
фильтрацию по различным параметрам для каждой игры, а также построение
параметров API для запросов к серверу DMarket."""
    )

    print_filter_support()
    demo_cs2_filters()
    demo_dota2_filters()
    demo_filter_descriptions()


if __name__ == "__main__":
    main()
