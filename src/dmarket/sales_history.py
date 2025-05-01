"""
Модуль для работы с историей продаж предметов на DMarket.

Этот модуль предоставляет функции для получения и анализа историй продаж
отдельных предметов и категорий товаров на DMarket.
"""
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Union
import asyncio
from datetime import datetime, timedelta

from src.dmarket.dmarket_api import DMarketAPI
from src.utils.api_error_handling import APIError
from src.utils.dmarket_api_utils import execute_api_request

# Настройка логирования
logger = logging.getLogger(__name__)

# Определение типов
SalesHistoryItem = Dict[str, Any]
SalesAnalysis = Dict[str, Any]


async def get_sales_history(
    item_names: List[str], 
    limit: int = 100,
    offset: str = None,
    api_client: Optional[DMarketAPI] = None
) -> Dict[str, Any]:
    """
    Получает историю продаж для списка предметов.

    Args:
        item_names: Список названий предметов на рынке
        limit: Максимальное количество записей истории для каждого предмета
        offset: Смещение для постраничного запроса (если требуется)
        api_client: Клиент DMarket API (если None, будет создан новый)

    Returns:
        Dict с историей продаж для каждого предмета
    """
    if not item_names:
        logger.warning("Пустой список предметов для получения истории продаж")
        return {"LastSales": [], "Total": 0}

    # Ограничиваем количество предметов в одном запросе
    if len(item_names) > 50:
        logger.warning(f"Слишком много предметов ({len(item_names)}), ограничиваем до 50")
        item_names = item_names[:50]

    # Создаем клиента API, если не предоставлен
    if api_client is None:
        from src.dmarket.dmarket_api import create_api_client
        api_client = await create_api_client()

    # Определяем функцию для запроса
    async def fetch_sales_history():
        # Формируем параметры запроса
        params = {
            "Titles": item_names,
            "Limit": limit
        }
        
        # Добавляем смещение, если предоставлено
        if offset:
            params["Offset"] = offset
            
        # Выполняем запрос к API
        return await api_client.request(
            method="GET",
            endpoint="/price-aggregator/v1/last-sales",
            params=params
        )

    try:
        # Выполняем запрос через утилиту для обработки ошибок API
        result = await execute_api_request(
            request_func=fetch_sales_history,
            endpoint_type="last_sales",
            max_retries=2
        )
        
        return result
    except APIError as e:
        logger.error(f"Ошибка при получении истории продаж: {e}")
        return {"Error": str(e), "LastSales": [], "Total": 0}


async def analyze_sales_history(
    item_name: str,
    days: int = 7,
    api_client: Optional[DMarketAPI] = None
) -> SalesAnalysis:
    """
    Анализирует историю продаж для конкретного предмета.

    Args:
        item_name: Название предмета на рынке
        days: Количество дней для анализа (по умолчанию 7)
        api_client: Клиент DMarket API (если None, будет создан новый)

    Returns:
        Dict с результатами анализа истории продаж
    """
    # Получаем историю продаж
    sales_data = await get_sales_history(
        item_names=[item_name],
        limit=100,  # Берем большее количество для лучшей статистики
        api_client=api_client
    )
    
    # Проверяем наличие ошибок
    if "Error" in sales_data and sales_data["Error"]:
        return {
            "item_name": item_name,
            "error": sales_data["Error"],
            "has_data": False
        }
    
    # Инициализируем результат анализа
    analysis = {
        "item_name": item_name,
        "has_data": False,
        "total_sales": 0,
        "avg_price": 0.0,
        "min_price": 0.0,
        "max_price": 0.0,
        "price_trend": "stable",  # возможные значения: "up", "down", "stable"
        "sales_volume": 0,
        "sales_per_day": 0.0,
        "recent_sales": [],
        "period_days": days
    }
    
    # Проверяем наличие данных о продажах
    if not sales_data.get("LastSales"):
        return analysis
    
    # Находим наш предмет в данных
    item_sales = None
    for item in sales_data.get("LastSales", []):
        if item.get("MarketHashName") == item_name:
            item_sales = item
            break
    
    # Если данных по нашему предмету нет
    if not item_sales or not item_sales.get("Sales"):
        return analysis
    
    # Получаем все продажи
    sales = item_sales.get("Sales", [])
    
    # Отмечаем, что у нас есть данные
    analysis["has_data"] = True
    analysis["total_sales"] = len(sales)
    
    # Текущее время для фильтрации по дням
    current_time = time.time()
    cutoff_time = current_time - (days * 86400)  # 86400 секунд в дне
    
    # Фильтруем продажи по времени
    recent_sales = [
        sale for sale in sales 
        if sale.get("Timestamp", 0) > cutoff_time
    ]
    
    # Если нет недавних продаж, возвращаем базовый анализ
    if not recent_sales:
        return analysis
    
    # Конвертируем цены в числа
    prices = []
    for sale in recent_sales:
        try:
            # Предполагаем, что цена - это строка с числом
            price = float(sale.get("Price", "0"))
            if price > 0:
                prices.append(price)
                
                # Добавляем информацию о продаже в результат
                sale_info = {
                    "price": price,
                    "currency": sale.get("Currency", "USD"),
                    "timestamp": sale.get("Timestamp", 0),
                    "date": datetime.fromtimestamp(sale.get("Timestamp", 0)).strftime("%Y-%m-%d %H:%M"),
                    "order_type": sale.get("OrderType", "Unknown")
                }
                analysis["recent_sales"].append(sale_info)
        except (ValueError, TypeError):
            logger.warning(f"Не удалось преобразовать цену: {sale.get('Price')}")
    
    # Если после фильтрации нет действительных цен
    if not prices:
        return analysis
    
    # Рассчитываем базовую статистику
    analysis["avg_price"] = sum(prices) / len(prices)
    analysis["min_price"] = min(prices)
    analysis["max_price"] = max(prices)
    analysis["sales_volume"] = len(prices)
    analysis["sales_per_day"] = len(prices) / days
    
    # Анализ тренда цены
    # Для этого сравниваем среднюю цену первой и второй половины периода
    if len(prices) >= 4:
        mid_point = len(prices) // 2
        first_half = prices[:mid_point]
        second_half = prices[mid_point:]
        
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        
        # Определяем изменение в процентах
        price_change_percent = ((avg_second - avg_first) / avg_first) * 100
        
        # Классифицируем тренд
        if price_change_percent > 5:
            analysis["price_trend"] = "up"
        elif price_change_percent < -5:
            analysis["price_trend"] = "down"
        else:
            analysis["price_trend"] = "stable"
        
        analysis["price_change_percent"] = price_change_percent
    
    return analysis


async def get_arbitrage_opportunities_with_sales_history(
    game: str = "csgo",
    max_items: int = 50,
    min_sales_per_day: float = 0.5,  # Минимум 1 продажа за 2 дня
    price_trend_filter: Optional[str] = None,  # "up", "down", "stable" или None для всех
    api_client: Optional[DMarketAPI] = None
) -> List[Dict[str, Any]]:
    """
    Находит арбитражные возможности с учетом истории продаж.

    Args:
        game: Игра (csgo, dota2, и т.д.)
        max_items: Максимальное количество предметов для анализа
        min_sales_per_day: Минимальное количество продаж в день для фильтрации
        price_trend_filter: Фильтр по тренду цены (up, down, stable или None)
        api_client: Клиент DMarket API (если None, будет создан новый)

    Returns:
        Список предметов с арбитражными возможностями и историей продаж
    """
    from src.dmarket.arbitrage import find_arbitrage_items
    
    # Создаем клиента API, если не предоставлен
    if api_client is None:
        from src.dmarket.dmarket_api import create_api_client
        api_client = await create_api_client()
    
    # Находим базовые арбитражные возможности
    arbitrage_items = await find_arbitrage_items(
        game=game,
        max_items=max_items,
        api_client=api_client
    )
    
    # Если нет арбитражных возможностей, возвращаем пустой список
    if not arbitrage_items:
        return []
    
    # Обогащаем арбитражные возможности данными о продажах
    enriched_items = []
    
    # Получаем названия предметов для массового запроса истории продаж
    item_names = [item.get("market_hash_name", "") for item in arbitrage_items]
    
    # Выполняем анализ для каждого предмета
    for item in arbitrage_items:
        item_name = item.get("market_hash_name", "")
        if not item_name:
            continue
        
        # Анализируем историю продаж для этого предмета
        sales_analysis = await analyze_sales_history(
            item_name=item_name,
            days=7,  # Анализ за неделю
            api_client=api_client
        )
        
        # Объединяем данные арбитража и анализа продаж
        item_data = {**item, "sales_analysis": sales_analysis}
        
        # Применяем фильтры по истории продаж
        if sales_analysis.get("has_data", False):
            # Фильтр по количеству продаж в день
            if sales_analysis.get("sales_per_day", 0) < min_sales_per_day:
                continue
                
            # Фильтр по тренду цены, если указан
            if price_trend_filter and sales_analysis.get("price_trend") != price_trend_filter:
                continue
                
            # Добавляем в результаты
            enriched_items.append(item_data)
    
    # Сортируем результаты по количеству продаж в день (от большего к меньшему)
    enriched_items.sort(
        key=lambda x: x.get("sales_analysis", {}).get("sales_per_day", 0),
        reverse=True
    )
    
    return enriched_items
