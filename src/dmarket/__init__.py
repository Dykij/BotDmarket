"""This module contains initialization logic for the dmarket package."""

__version__ = "0.1.0"

# Импортируем основные компоненты для удобства использования
# Больше не требуется применение патчей, так как все необходимое
# реализовано в моках для тестов
import logging

from .api import DMarketAPI
from .arbitrage import GAMES

logging.getLogger(__name__).info("DMarketAPI с улучшенным балансом загружен успешно")


# Явно экспортируем функцию find_arbitrage_opportunities
def find_arbitrage_opportunities(min_profit_percentage: float = 10.0, max_results: int = 5):
    """Находит арбитражные возможности с минимальной прибылью и максимальным количеством результатов.

    Args:
        min_profit_percentage: Минимальный процент прибыли
        max_results: Максимальное количество результатов

    Returns:
        Список найденных возможностей для арбитража

    """
    # В реальном проекте здесь будет код для сравнения цен на разных площадках
    # Для демонстрации создаем тестовые данные

    # Тестовые данные
    test_data = [
        {
            "item_title": "AK-47 | Redline (Field-Tested)",
            "market_from": "Steam Market",
            "market_to": "DMarket",
            "buy_price": 12.50,
            "sell_price": 15.75,
            "profit_amount": 3.25,
            "profit_percentage": 26.0,
        },
        {
            "item_title": "AWP | Asiimov (Field-Tested)",
            "market_from": "DMarket",
            "market_to": "Skinport",
            "buy_price": 45.00,
            "sell_price": 54.99,
            "profit_amount": 9.99,
            "profit_percentage": 22.2,
        },
        {
            "item_title": "Butterfly Knife | Doppler (Factory New)",
            "market_from": "Skinport",
            "market_to": "Steam Market",
            "buy_price": 850.00,
            "sell_price": 935.00,
            "profit_amount": 85.00,
            "profit_percentage": 10.0,
        },
        {
            "item_title": "Glock-18 | Fade (Factory New)",
            "market_from": "DMarket",
            "market_to": "Skinbid",
            "buy_price": 220.00,
            "sell_price": 253.00,
            "profit_amount": 33.00,
            "profit_percentage": 15.0,
        },
        {
            "item_title": "M4A4 | Howl (Minimal Wear)",
            "market_from": "Skinbid",
            "market_to": "DMarket",
            "buy_price": 1200.00,
            "sell_price": 1380.00,
            "profit_amount": 180.00,
            "profit_percentage": 15.0,
        },
    ]

    # Фильтруем по минимальному проценту прибыли
    filtered_opportunities = [
        opp for opp in test_data if opp["profit_percentage"] >= min_profit_percentage
    ]

    # Сортируем по проценту прибыли (по убыванию)
    sorted_opportunities = sorted(
        filtered_opportunities,
        key=lambda x: x["profit_percentage"],
        reverse=True,
    )

    # Возвращаем ограниченное количество результатов
    return sorted_opportunities[:max_results]
