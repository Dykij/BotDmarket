"""
Модуль для интеграции истории продаж в поиск арбитражных возможностей.

Этот модуль объединяет функциональность поиска арбитражных возможностей
с анализом истории продаж для предоставления более точных рекомендаций.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
import asyncio

from src.dmarket.dmarket_api import DMarketAPI
from src.dmarket.arbitrage import find_arbitrage_items
from src.dmarket.sales_history import (
    get_sales_history, 
    analyze_sales_history, 
    get_arbitrage_opportunities_with_sales_history
)

# Настройка логирования
logger = logging.getLogger(__name__)


async def enhanced_arbitrage_search(
    game: str = "csgo",
    max_items: int = 20,
    min_profit: float = 1.0,
    min_profit_percent: float = 5.0,
    min_sales_per_day: float = 0.5,
    price_trend_filter: Optional[str] = None,
    time_period_days: int = 7,
    api_client: Optional[DMarketAPI] = None
) -> Dict[str, Any]:
    """
    Выполняет улучшенный поиск арбитражных возможностей с учетом истории продаж.

    Args:
        game: Игра (csgo, dota2, и т.д.)
        max_items: Максимальное количество предметов для анализа
        min_profit: Минимальная прибыль в USD для фильтрации возможностей
        min_profit_percent: Минимальный процент прибыли для фильтрации
        min_sales_per_day: Минимальное количество продаж в день
        price_trend_filter: Фильтр по тренду цены (up, down, stable или None)
        time_period_days: Период анализа истории продаж в днях
        api_client: Клиент DMarket API (если None, будет создан новый)

    Returns:
        Dict с результатами поиска арбитражных возможностей
    """
    # Создаем клиента API, если не предоставлен
    if api_client is None:
        from src.dmarket.dmarket_api import create_api_client
        api_client = await create_api_client()
    
    # Получаем арбитражные возможности с учетом истории продаж
    opportunities = await get_arbitrage_opportunities_with_sales_history(
        game=game,
        max_items=max_items * 2,  # Берем больше, чтобы был запас после фильтрации
        min_sales_per_day=min_sales_per_day,
        price_trend_filter=price_trend_filter,
        api_client=api_client
    )
    
    # Фильтруем по минимальной прибыли и проценту прибыли
    filtered_opportunities = []
    for item in opportunities:
        profit = item.get("profit", 0)
        profit_percent = item.get("profit_percent", 0)
        
        if profit >= min_profit and profit_percent >= min_profit_percent:
            filtered_opportunities.append(item)
    
    # Ограничиваем количество результатов
    filtered_opportunities = filtered_opportunities[:max_items]
    
    # Формируем результат
    result = {
        "game": game,
        "count": len(filtered_opportunities),
        "opportunities": filtered_opportunities,
        "filters": {
            "min_profit": min_profit,
            "min_profit_percent": min_profit_percent,
            "min_sales_per_day": min_sales_per_day,
            "price_trend_filter": price_trend_filter,
            "time_period_days": time_period_days
        }
    }
    
    return result


async def get_sales_volume_stats(
    game: str = "csgo",
    top_items: int = 100,
    api_client: Optional[DMarketAPI] = None
) -> Dict[str, Any]:
    """
    Получает статистику по объему продаж популярных предметов.

    Args:
        game: Игра (csgo, dota2, и т.д.)
        top_items: Количество популярных предметов для анализа
        api_client: Клиент DMarket API (если None, будет создан новый)

    Returns:
        Dict со статистикой по объему продаж
    """
    # Создаем клиента API, если не предоставлен
    if api_client is None:
        from src.dmarket.dmarket_api import create_api_client
        api_client = await create_api_client()
    
    # Получаем популярные предметы
    popular_items = await api_client.get_market_items(
        game=game,
        limit=top_items,
        sort="popularity"
    )
    
    # Извлекаем названия предметов
    item_names = []
    for item in popular_items.get("objects", []):
        market_hash_name = item.get("title")
        if market_hash_name:
            item_names.append(market_hash_name)
    
    # Анализируем историю продаж для всех предметов
    sales_analysis_list = []
    
    # Группируем предметы по 10 для оптимизации запросов
    for i in range(0, len(item_names), 10):
        batch = item_names[i:i+10]
        
        # Собираем анализ для каждого предмета в группе
        analysis_tasks = []
        for item_name in batch:
            task = analyze_sales_history(
                item_name=item_name,
                days=7,
                api_client=api_client
            )
            analysis_tasks.append(task)
        
        # Выполняем все задачи для текущей группы и добавляем результаты
        batch_results = await asyncio.gather(*analysis_tasks)
        sales_analysis_list.extend(batch_results)
        
        # Делаем небольшую паузу между группами запросов
        await asyncio.sleep(1)
    
    # Фильтруем только элементы с данными и сортируем по объему продаж
    valid_analyses = [
        analysis for analysis in sales_analysis_list
        if analysis.get("has_data", False)
    ]
    
    # Сортируем по количеству продаж в день
    valid_analyses.sort(
        key=lambda x: x.get("sales_per_day", 0),
        reverse=True
    )
    
    # Формируем результат
    result = {
        "game": game,
        "count": len(valid_analyses),
        "items": valid_analyses,
        "summary": {
            "highest_sales_per_day": max([a.get("sales_per_day", 0) for a in valid_analyses]) 
                                     if valid_analyses else 0,
            "average_sales_per_day": sum([a.get("sales_per_day", 0) for a in valid_analyses]) / len(valid_analyses)
                                      if valid_analyses else 0,
            "up_trend_count": len([a for a in valid_analyses if a.get("price_trend") == "up"]),
            "down_trend_count": len([a for a in valid_analyses if a.get("price_trend") == "down"]),
            "stable_trend_count": len([a for a in valid_analyses if a.get("price_trend") == "stable"])
        }
    }
    
    return result


async def analyze_item_liquidity(
    item_name: str,
    game: str = "csgo",
    api_client: Optional[DMarketAPI] = None
) -> Dict[str, Any]:
    """
    Выполняет детальный анализ ликвидности предмета.

    Args:
        item_name: Название предмета для анализа
        game: Игра (csgo, dota2, и т.д.)
        api_client: Клиент DMarket API (если None, будет создан новый)

    Returns:
        Dict с результатами анализа ликвидности
    """
    # Создаем клиента API, если не предоставлен
    if api_client is None:
        from src.dmarket.dmarket_api import create_api_client
        api_client = await create_api_client()
    
    # Получаем анализ истории продаж
    sales_analysis = await analyze_sales_history(
        item_name=item_name,
        days=30,  # Анализируем за месяц для более полной картины
        api_client=api_client
    )
    
    # Получаем текущие рыночные данные
    market_data = await api_client.get_market_items(
        game=game,
        title=item_name,
        limit=10
    )
    
    # Определяем ликвидность
    liquidity_score = 0
    liquidity_category = "Низкая"
    
    # Анализ на основе продаж в день
    sales_per_day = sales_analysis.get("sales_per_day", 0)
    if sales_per_day >= 5:
        liquidity_score += 3
    elif sales_per_day >= 2:
        liquidity_score += 2
    elif sales_per_day >= 0.5:
        liquidity_score += 1
    
    # Анализ на основе количества предложений на рынке
    offers_count = len(market_data.get("objects", []))
    if offers_count >= 20:
        liquidity_score += 2
    elif offers_count >= 5:
        liquidity_score += 1
    
    # Анализ на основе тренда цены
    price_trend = sales_analysis.get("price_trend", "stable")
    if price_trend == "stable":
        liquidity_score += 2  # Стабильные предметы обычно более ликвидны
    elif price_trend == "up":
        liquidity_score += 1  # Растущие цены могут означать повышенный спрос
    
    # Определяем категорию ликвидности по итоговому баллу
    if liquidity_score >= 6:
        liquidity_category = "Очень высокая"
    elif liquidity_score >= 4:
        liquidity_category = "Высокая"
    elif liquidity_score >= 2:
        liquidity_category = "Средняя"
    else:
        liquidity_category = "Низкая"
    
    # Формируем результат
    result = {
        "item_name": item_name,
        "game": game,
        "liquidity_score": liquidity_score,
        "liquidity_category": liquidity_category,
        "sales_analysis": sales_analysis,
        "market_data": {
            "offers_count": offers_count,
            "lowest_price": market_data.get("objects", [{}])[0].get("price", {}).get("USD") if market_data.get("objects") else None,
            "highest_price": market_data.get("objects", [{}])[-1].get("price", {}).get("USD") if market_data.get("objects") else None
        }
    }
    
    return result
