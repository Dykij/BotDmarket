"""
This module contains initialization logic for the dmarket package.
"""

__version__ = "0.1.0"

# Экспорт функций для использования
from .arbitrage import arbitrage_boost, arbitrage_mid, arbitrage_pro
from .arbitrage import arbitrage_boost_async, arbitrage_mid_async, arbitrage_pro_async
from .dmarket_api import DMarketAPI

# Применяем патч для DMarketAPI, добавляющий метод get_user_balance
try:
    # Попробуем загрузить и применить патч из dmarket_api_patch
    try:
        from .dmarket_api_patch import apply_patch
        # Применяем патч при импорте модуля
        apply_patch()
    except ImportError:
        # Если первый патч не найден, попробуем загрузить из dmarket_api_patches
        from .dmarket_api_patches import apply_balance_patch
        apply_balance_patch()
except ImportError:
    import logging
    logging.getLogger(__name__).warning("Не удалось загрузить патч для DMarketAPI")

# Явно экспортируем функцию find_arbitrage_opportunities
def find_arbitrage_opportunities(min_profit_percentage: float = 10.0, max_results: int = 5):
    """
    Находит арбитражные возможности с минимальной прибылью и максимальным количеством результатов.
    
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
            "profit_percentage": 26.0
        },
        {
            "item_title": "AWP | Asiimov (Field-Tested)",
            "market_from": "DMarket",
            "market_to": "Skinport",
            "buy_price": 45.00,
            "sell_price": 54.99,
            "profit_amount": 9.99,
            "profit_percentage": 22.2
        },
        {
            "item_title": "Butterfly Knife | Doppler (Factory New)",
            "market_from": "Skinport",
            "market_to": "Steam Market",
            "buy_price": 850.00,
            "sell_price": 935.00,
            "profit_amount": 85.00,
            "profit_percentage": 10.0
        },
        {
            "item_title": "Glock-18 | Fade (Factory New)",
            "market_from": "DMarket",
            "market_to": "Skinbid",
            "buy_price": 220.00,
            "sell_price": 253.00,
            "profit_amount": 33.00,
            "profit_percentage": 15.0
        },
        {
            "item_title": "M4A4 | Howl (Minimal Wear)",
            "market_from": "Skinbid",
            "market_to": "DMarket",
            "buy_price": 1200.00,
            "sell_price": 1380.00,
            "profit_amount": 180.00,
            "profit_percentage": 15.0
        }
    ]
    
    # Фильтруем по минимальному проценту прибыли
    filtered_opportunities = [
        opp for opp in test_data if opp["profit_percentage"] >= min_profit_percentage
    ]
    
    # Сортируем по проценту прибыли (по убыванию)
    sorted_opportunities = sorted(
        filtered_opportunities, 
        key=lambda x: x["profit_percentage"], 
        reverse=True
    )
    
    # Возвращаем ограниченное количество результатов
    return sorted_opportunities[:max_results]
