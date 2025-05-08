"""
Мок-модуль auto_arbitrage_scanner для тестирования.
"""

from typing import List, Dict, Any, Optional
from tests.mock_dmarket_api import DMarketAPI


async def scan_multiple_games(
    api_client: DMarketAPI,
    games: List[str],
    mode: str,
    limit: int = 10,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Мок-функция сканирования нескольких игр для арбитража.
    
    Args:
        api_client: Клиент DMarket API
        games: Список игр для сканирования
        mode: Режим арбитража
        limit: Лимит предметов
        price_min: Минимальная цена
        price_max: Максимальная цена
        
    Returns:
        List[Dict[str, Any]]: Список арбитражных возможностей
    """
    # Мок-данные для тестирования
    results = [
        {
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {"amount": 2000},  # $20 в центах
            "profit": 400,  # $4 в центах
            "profit_percent": 20.0,
            "game": "csgo",
            "liquidity": "high"
        },
        {
            "title": "AWP | Asiimov (Field-Tested)",
            "price": {"amount": 7500},  # $75 в центах
            "profit": 1125,  # $11.25 в центах
            "profit_percent": 15.0,
            "game": "csgo",
            "liquidity": "medium"
        }
    ]
    
    # Фильтрация по режиму арбитража (если необходимо)
    if mode == "boost_low":
        # Только дешевые предметы для режима boost_low
        results = [item for item in results if item["price"]["amount"] < 5000]
    elif mode == "mid_medium":
        # Только предметы среднего ценового диапазона для режима mid_medium
        results = [item for item in results if 5000 <= item["price"]["amount"] < 10000]
    elif mode == "pro_high":
        # Только дорогие предметы для режима pro_high
        results = [item for item in results if item["price"]["amount"] >= 10000]
    
    # Применение ценовых фильтров, если они указаны
    if price_min is not None:
        price_min_cents = int(price_min * 100)
        results = [item for item in results if item["price"]["amount"] >= price_min_cents]
    
    if price_max is not None:
        price_max_cents = int(price_max * 100)
        results = [item for item in results if item["price"]["amount"] <= price_max_cents]
    
    # Ограничиваем результаты по лимиту
    return results[:limit]


async def auto_trade_items(
    api_client: DMarketAPI,
    items: List[Dict[str, Any]],
    mode: str,
) -> Dict[str, Any]:
    """
    Мок-функция автоматической торговли предметами.
    
    Args:
        api_client: Клиент DMarket API
        items: Список предметов для торговли
        mode: Режим арбитража
        
    Returns:
        Dict[str, Any]: Результаты торговли
    """
    # Мок результаты торговли
    return {
        "success": True,
        "traded_items": len(items),
        "total_profit": sum(item.get("profit", 0) for item in items),
        "mode": mode
    }


async def check_user_balance(api_client: DMarketAPI) -> Dict[str, Any]:
    """
    Мок-функция проверки баланса пользователя.
    
    Args:
        api_client: Клиент DMarket API
        
    Returns:
        Dict[str, Any]: Информация о балансе пользователя
    """
    # Перенаправляем на реальный метод в моке DMarketAPI
    return await api_client.get_user_balance() 