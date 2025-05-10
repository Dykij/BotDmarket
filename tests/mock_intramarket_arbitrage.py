"""Мок-модуль intramarket_arbitrage для тестирования.
"""

from typing import Any

from tests.mock_dmarket_api import DMarketAPI

# Константы для модуля
SUPPORTED_GAMES = ["csgo", "dota2", "rust", "tf2"]
DEFAULT_PROFIT_THRESHOLD = 0.05  # 5%
DEFAULT_PRICE_DIFF_THRESHOLD = 0.1  # 10%
DEFAULT_SALES_THRESHOLD = 5  # Минимум 5 продаж для предмета


async def find_intramarket_opportunities(
    api_client: DMarketAPI,
    game: str = "csgo",
    limit: int = 10,
    profit_threshold: float = DEFAULT_PROFIT_THRESHOLD,
    price_min: float | None = None,
    price_max: float | None = None,
) -> list[dict[str, Any]]:
    """Находит возможности для внутрирыночного арбитража (модельный метод).

    Args:
        api_client: Клиент DMarket API
        game: Игра
        limit: Лимит результатов
        profit_threshold: Порог прибыли
        price_min: Минимальная цена
        price_max: Максимальная цена

    Returns:
        List[Dict[str, Any]]: Список возможностей

    """
    # Мок-данные для тестирования
    opportunities = [
        {
            "title": "AK-47 | Redline (Field-Tested)",
            "buy_price": 20.00,
            "sell_price": 22.00,
            "profit": 1.00,
            "profit_percent": 5.0,
            "sales_per_day": 12.5,
            "lowest_float": 0.15,
            "highest_float": 0.35,
            "game": game,
        },
        {
            "title": "AWP | Asiimov (Field-Tested)",
            "buy_price": 45.00,
            "sell_price": 49.50,
            "profit": 2.50,
            "profit_percent": 5.5,
            "sales_per_day": 8.3,
            "lowest_float": 0.18,
            "highest_float": 0.38,
            "game": game,
        },
    ]

    # Фильтрация по порогу прибыли
    opportunities = [
        item for item in opportunities if item["profit_percent"] >= profit_threshold * 100
    ]

    # Фильтрация по цене
    if price_min is not None:
        opportunities = [item for item in opportunities if item["buy_price"] >= price_min]

    if price_max is not None:
        opportunities = [item for item in opportunities if item["buy_price"] <= price_max]

    # Возвращаем с ограничением по limit
    return opportunities[:limit]


async def get_potential_profit(
    api_client: DMarketAPI,
    item_name: str,
    game: str = "csgo",
) -> dict[str, Any]:
    """Получает потенциальную прибыль для предмета (модельный метод).

    Args:
        api_client: Клиент DMarket API
        item_name: Название предмета
        game: Игра

    Returns:
        Dict[str, Any]: Информация о потенциальной прибыли

    """
    # Мок-данные для тестирования
    return {
        "title": item_name,
        "buy_price": 20.00,
        "sell_price": 22.00,
        "profit": 1.00,
        "profit_percent": 5.0,
        "sales_per_day": 12.5,
        "success_chance": "высокая",
        "game": game,
    }


def get_sales_history_for_game(game: str, days: int = 7) -> dict[str, Any]:
    """Получает историю продаж для игры (модельный метод).

    Args:
        game: Игра
        days: Количество дней

    Returns:
        Dict[str, Any]: История продаж

    """
    # Мок-данные для тестирования
    return {
        "game": game,
        "days": days,
        "items": {
            "AK-47 | Redline (Field-Tested)": {
                "total_sales": 875,
                "avg_price": 19.75,
                "min_price": 18.50,
                "max_price": 22.00,
                "sales_per_day": 125.0,
            },
            "AWP | Asiimov (Field-Tested)": {
                "total_sales": 583,
                "avg_price": 47.25,
                "min_price": 44.50,
                "max_price": 51.00,
                "sales_per_day": 83.3,
            },
        },
    }
