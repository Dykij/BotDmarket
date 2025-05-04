"""
Демонстрационный модуль для автоматического арбитража на DMarket.

Модуль имитирует работу автоматического арбитража с помощью генерации случайных предметов и демонстрирует различные режимы отбора арбитражных возможностей.
Содержит функции для генерации тестовых данных, фильтрации предметов по режимам, а также асинхронную демонстрацию работы.
"""

import asyncio
import logging
import random
from typing import Any, Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Симуляция данных с DMarket
GAMES = {
    "csgo": "CS:GO",
    "dota2": "Dota 2",
    "rust": "Rust",
    "tf2": "Team Fortress 2"
}


def generate_random_items(game: str, count: int = 10) -> List[Dict[str, Any]]:
    """
    Генерирует случайные предметы для тестирования арбитражных стратегий.

    Args:
        game (str): Код игры (например, 'csgo', 'dota2').
        count (int, optional): Количество предметов для генерации. По умолчанию 10.

    Returns:
        List[Dict[str, Any]]: Список сгенерированных предметов с параметрами для арбитража.
    """
    item_types = {
        "csgo": ["Нож", "AWP", "AK-47", "M4A4", "Desert Eagle", "Перчатки", "USP-S", "Glock-18"],
        "dota2": ["Аркана", "Иммортал", "Курьер", "Сет", "Редкий предмет", "Легендарный предмет"],
        "rust": ["Оружие", "Одежда", "Инструменты", "Ресурсы", "Декор"],
        "tf2": ["Шляпа", "Оружие", "Необычный предмет", "Редкий предмет"]
    }
    rarities = ["Обычный", "Необычный", "Редкий", "Мифический", "Легендарный", "Древний", "Бессмертный"]
    colors = ["Красный", "Синий", "Зелёный", "Жёлтый", "Чёрный", "Белый", "Розовый"]

    items = []
    item_types_for_game = item_types.get(game, ["Предмет"])

    for _ in range(count):
        item_type = random.choice(item_types_for_game)
        rarity = random.choice(rarities)
        color = random.choice(colors)
        buy_price = random.randint(100, 10000)  # цена в центах
        profit_percentage = random.uniform(5.0, 30.0)  # процент прибыли
        profit = int(buy_price * profit_percentage / 100)
        item_name = f"{rarity} {item_type} | {color}"
        item = {
            "title": item_name,
            "buyPrice": buy_price,
            "sellPrice": buy_price + profit,
            "profit": profit,
            "profitPercent": profit_percentage,
            "gameId": game,
            "rarity": rarity,
            "color": color
        }
        items.append(item)

    items.sort(key=lambda x: x["profitPercent"], reverse=True)
    return items


def arbitrage_boost(game: str) -> List[Dict[str, Any]]:
    """
    Возвращает предметы для арбитража в режиме 'Разгон баланса' (низкая прибыль, быстрые сделки).

    Args:
        game (str): Код игры.

    Returns:
        List[Dict[str, Any]]: Список предметов, подходящих для быстрого арбитража.
    """
    items = generate_random_items(game, count=15)
    # Фильтрация по низкой цене и минимальному проценту прибыли
    return [item for item in items if item["buyPrice"] < 500 and item["profitPercent"] >= 5.0]


def arbitrage_mid(game: str) -> List[Dict[str, Any]]:
    """
    Возвращает предметы для арбитража в режиме 'Средний трейдер' (средняя прибыль).

    Args:
        game (str): Код игры.

    Returns:
        List[Dict[str, Any]]: Список предметов для среднего арбитража.
    """
    items = generate_random_items(game, count=20)
    # Фильтрация по средней цене и проценту прибыли
    return [item for item in items if 500 <= item["buyPrice"] < 2000 and item["profitPercent"] >= 10.0]


def arbitrage_pro(game: str) -> List[Dict[str, Any]]:
    """
    Возвращает предметы для арбитража в режиме 'Trade Pro' (высокая прибыль).

    Args:
        game (str): Код игры.

    Returns:
        List[Dict[str, Any]]: Список предметов для арбитража с высокой прибылью.
    """
    items = generate_random_items(game, count=25)
    # Фильтрация по высокой цене и проценту прибыли
    return [item for item in items if item["buyPrice"] >= 2000 and item["profitPercent"] >= 15.0]


async def auto_arbitrage_demo(game: str = "csgo", mode: str = "medium", iterations: int = 5) -> None:
    """
    Демонстрирует работу автоматического арбитража для выбранной игры и режима.

    Args:
        game (str, optional): Код игры. По умолчанию 'csgo'.
        mode (str, optional): Режим арбитража ('low', 'medium', 'high'). По умолчанию 'medium'.
        iterations (int, optional): Количество итераций демонстрации. По умолчанию 5.
    """
    logger.info("Запуск автоматического арбитража для %s в режиме %s", GAMES.get(game, game), mode)
    try:
        for i in range(iterations):
            logger.info("Итерация %d из %d", i + 1, iterations)
            if mode == "low":
                items = arbitrage_boost(game)
            elif mode == "high":
                items = arbitrage_pro(game)
            else:
                items = arbitrage_mid(game)
            if items:
                logger.info("Найдено %d предметов для арбитража", len(items))
                for j, item in enumerate(items[:3], start=1):
                    name = item["title"]
                    buy_price = item["buyPrice"] / 100
                    profit = item["profit"] / 100
                    profit_percent = item["profitPercent"]
                    logger.info(
                        "%d. %s - $%.2f (Прибыль: $%.2f, %.1f%%)",
                        j, name, buy_price, profit, profit_percent)
            else:
                logger.info("Не найдено предметов, удовлетворяющих условиям")
            await asyncio.sleep(2)
    except Exception as e:
        logger.error("Ошибка при выполнении автоматического арбитража: %s", str(e))
    logger.info("Автоматический арбитраж завершён")


async def main() -> None:
    """
    Запускает демонстрацию автоматического арбитража для разных игр и режимов.
    """
    print("""
    =============================================================
    Демонстрация автоматического арбитража для DMarket
    =============================================================
    """)
    for game in ["csgo", "dota2"]:
        for mode in ["low", "medium", "high"]:
            print(f"\n----- Автоматический арбитраж: {GAMES[game]}, режим: {mode} -----")
            await auto_arbitrage_demo(game=game, mode=mode, iterations=3)
            print("-" * 70)


if __name__ == "__main__":
    # Точка входа: запуск асинхронной демонстрации автоматического арбитража
    asyncio.run(main())

