"""Модуль для автоматического арбитража на DMarket.

Модуль имитирует работу автоматического арбитража с помощью генерации случайных предметов 
и демонстрирует различные режимы отбора арбитражных возможностей.
Содержит функции для генерации тестовых данных, фильтрации предметов по режимам, 
а также асинхронную демонстрацию работы.
"""

import asyncio
import random
from typing import Any

GAMES = {
    "csgo": "Counter-Strike: Global Offensive",
    "dota2": "Dota 2",
}


def generate_random_items(game: str, count: int = 10) -> list[dict[str, Any]]:
    """Генерирует случайные предметы для тестирования арбитражных стратегий.

    Args:
        game (str): Код игры (например, 'csgo', 'dota2').
        count (int, optional): Количество предметов для генерации. По умолчанию 10.

    Returns:
        List[Dict[str, Any]]: Список сгенерированных предметов с параметрами для арбитража.

    """
    return [
        {
            "id": f"item_{i}",
            "game": game,
            "price": random.uniform(1, 100),
            "profit": random.uniform(-10, 10),
        }
        for i in range(count)
    ]


def arbitrage_boost(game: str) -> list[dict[str, Any]]:
    """Возвращает предметы для арбитража в режиме 'Разгон баланса' (низкая прибыль, быстрые сделки).

    Args:
        game (str): Код игры.

    Returns:
        List[Dict[str, Any]]: Список предметов, подходящих для быстрого арбитража.

    """
    items = generate_random_items(game)
    return [item for item in items if item["profit"] < 0]


def arbitrage_mid(game: str) -> list[dict[str, Any]]:
    """Возвращает предметы для арбитража в режиме 'Средний трейдер' (средняя прибыль).

    Args:
        game (str): Код игры.

    Returns:
        List[Dict[str, Any]]: Список предметов для среднего арбитража.

    """
    items = generate_random_items(game)
    return [item for item in items if 0 <= item["profit"] < 5]


def arbitrage_pro(game: str) -> list[dict[str, Any]]:
    """Возвращает предметы для арбитража в режиме 'Trade Pro' (высокая прибыль).

    Args:
        game (str): Код игры.

    Returns:
        List[Dict[str, Any]]: Список предметов для арбитража с высокой прибылью.

    """
    items = generate_random_items(game)
    return [item for item in items if item["profit"] >= 5]


async def auto_arbitrage_demo(
    game: str = "csgo", mode: str = "medium", iterations: int = 5
) -> None:
    """Демонстрирует работу автоматического арбитража для выбранной игры и режима.

    Args:
        game (str, optional): Код игры. По умолчанию 'csgo'.
        mode (str, optional): Режим арбитража ('low', 'medium', 'high'). По умолчанию 'medium'.
        iterations (int, optional): Количество итераций демонстрации. По умолчанию 5.

    """
    for _ in range(iterations):
        if mode == "low":
            items = arbitrage_boost(game)
        elif mode == "medium":
            items = arbitrage_mid(game)
        else:
            items = arbitrage_pro(game)

        print(f"Итерация арбитража для {GAMES[game]} в режиме {mode}:")
        for item in items:
            print(f"- {item['id']}: прибыль {item['profit']:.2f}, цена {item['price']:.2f}")
        await asyncio.sleep(1)


async def main() -> None:
    """Запускает демонстрацию автоматического арбитража для разных игр и режимов."""
    await auto_arbitrage_demo("csgo", "low")
    await auto_arbitrage_demo("csgo", "medium")
    await auto_arbitrage_demo("csgo", "high")
    await auto_arbitrage_demo("dota2", "low")
    await auto_arbitrage_demo("dota2", "medium")
    await auto_arbitrage_demo("dota2", "high")


if __name__ == "__main__":
    # Точка входа: запуск асинхронной демонстрации автоматического арбитража
    asyncio.run(main())
