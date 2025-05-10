"""Демонстрационный скрипт для тестирования фильтров арбитража по играм.
"""

import asyncio
import os
import sys

# Добавляем корневой каталог проекта в путь импорта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.telegram_bot.arbitrage_scanner import ArbitrageScanner

# Тестовые данные: предметы CS:GO
CSGO_ITEMS = [
    {
        "title": "AK-47 | Redline (Field-Tested)",
        "category": "rifle",
        "float": "0.18",
        "rarity": "Classified",
        "buyPrice": "1000",
        "profit": "100",
    },
    {
        "title": "AWP | Asiimov (Field-Tested)",
        "category": "sniper rifle",
        "float": "0.25",
        "rarity": "Covert",
        "buyPrice": "3000",
        "profit": "300",
    },
    {
        "title": "★ Butterfly Knife | Doppler (Factory New)",
        "category": "knife",
        "float": "0.01",
        "rarity": "Covert",
        "buyPrice": "20000",
        "profit": "2500",
    },
    {
        "title": "StatTrak™ M4A4 | Neo-Noir (Minimal Wear)",
        "category": "rifle",
        "float": "0.09",
        "rarity": "Covert",
        "stattrak": True,
        "buyPrice": "5000",
        "profit": "500",
    },
]

# Тестовые данные: предметы Dota 2
DOTA2_ITEMS = [
    {
        "title": "Genuine Bow of the Howling Wind",
        "category": "weapon",
        "rarity": "Legendary",
        "quality": "genuine",
        "hero": "Drow Ranger",
        "buyPrice": "2000",
        "profit": "200",
    },
    {
        "title": "Inscribed Arcana Tempest Helm of the Thundergod",
        "category": "head",
        "rarity": "Arcana",
        "quality": "inscribed",
        "hero": "Zeus",
        "buyPrice": "6000",
        "profit": "900",
    },
]


async def test_filters():
    """Тестирование фильтрации предметов."""
    scanner = ArbitrageScanner()

    # Тестируем фильтры CS:GO
    print("=== Тестирование фильтров CS:GO ===")

    # Фильтр по float (изношенность)
    filters = {"float_min": 0.0, "float_max": 0.1}
    results = scanner._apply_game_specific_filters(CSGO_ITEMS, "csgo", filters)
    print(f"\nФильтр по float (0.0-0.1): {len(results)} результатов")
    for item in results:
        print(f"  - {item['title']} (float: {item.get('float', 'N/A')})")

    # Фильтр по типу предмета
    filters = {"item_type": "knife"}
    results = scanner._apply_game_specific_filters(CSGO_ITEMS, "csgo", filters)
    print(f"\nФильтр по типу (knife): {len(results)} результатов")
    for item in results:
        print(f"  - {item['title']}")

    # Фильтр по StatTrak
    filters = {"stattrak": True}
    results = scanner._apply_game_specific_filters(CSGO_ITEMS, "csgo", filters)
    print(f"\nФильтр по StatTrak: {len(results)} результатов")
    for item in results:
        print(f"  - {item['title']}")

    # Тестируем фильтры Dota 2
    print("\n=== Тестирование фильтров Dota 2 ===")

    # Фильтр по редкости
    filters = {"rarity": "Arcana"}
    results = scanner._apply_game_specific_filters(DOTA2_ITEMS, "dota2", filters)
    print(f"\nФильтр по редкости (Arcana): {len(results)} результатов")
    for item in results:
        print(f"  - {item['title']}")

    # Фильтр по герою
    filters = {"hero": "zeus"}
    results = scanner._apply_game_specific_filters(DOTA2_ITEMS, "dota2", filters)
    print(f"\nФильтр по герою (Zeus): {len(results)} результатов")
    for item in results:
        print(f"  - {item['title']}")

    # Комбинированные фильтры
    print("\n=== Тестирование комбинированных фильтров ===")
    filters = {"rarity": "Covert", "float_min": 0.0, "float_max": 0.1}
    results = scanner._apply_game_specific_filters(CSGO_ITEMS, "csgo", filters)
    print(f"\nФильтр по редкости (Covert) и float (0.0-0.1): {len(results)} результатов")
    for item in results:
        print(
            f"  - {item['title']} (float: {item.get('float', 'N/A')}, rarity: {item.get('rarity', 'N/A')})"
        )


if __name__ == "__main__":
    asyncio.run(test_filters())
