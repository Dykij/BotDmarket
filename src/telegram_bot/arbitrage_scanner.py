"""
Модуль для поиска арбитражных возможностей.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple

from src.dmarket.arbitrage import (
    arbitrage_boost, arbitrage_mid, arbitrage_pro, GAMES
)
from src.dmarket.dmarket_api import DMarketAPI
from src.utils.rate_limiter import RateLimiter

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем экземпляр ограничителя скорости запросов
rate_limiter = RateLimiter(is_authorized=True)


async def find_arbitrage_opportunities_async(
    game: str, 
    mode: str = "medium",
    max_items: int = 20
) -> List[Dict[str, Any]]:
    """
    Асинхронно находит арбитражные возможности для указанной игры в указанном режиме.
    
    Args:
        game: Код игры (например, csgo, dota2, rust, tf2)
        mode: Режим поиска (low, medium, high)
        max_items: Максимальное количество предметов в результате
        
    Returns:
        Список предметов, подходящих для арбитража
    """
    try:
        # В зависимости от режима вызываем соответствующую функцию арбитража
        items = []
        
        if mode == "low":
            items = arbitrage_boost(game)
        elif mode == "medium":
            items = arbitrage_mid(game)
        elif mode == "high":
            items = arbitrage_pro(game)
        else:
            # По умолчанию используем средний режим
            items = arbitrage_mid(game)
        
        # Ограничиваем количество предметов в результате
        return items[:max_items]
    except Exception as e:
        logger.error(f"Ошибка в find_arbitrage_opportunities_async: {str(e)}")
        return []


async def find_multi_game_arbitrage_opportunities(
    games: List[str] = ["csgo", "dota2", "rust", "tf2"],
    mode: str = "medium",
    max_items_per_game: int = 10
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Находит арбитражные возможности для нескольких игр.
    
    Args:
        games: Список кодов игр
        mode: Режим поиска (low, medium, high)
        max_items_per_game: Максимальное количество предметов на каждую игру
        
    Returns:
        Словарь с кодами игр и списками подходящих предметов
    """
    results = {}
    
    for game in games:
        try:
            # Ожидаем, если необходимо для соблюдения ограничений API
            await rate_limiter.wait_if_needed("market")
            
            logger.info(f"Поиск арбитражных возможностей для {game} в режиме {mode}")
            items = await find_arbitrage_opportunities_async(game, mode, max_items_per_game)
            results[game] = items
            
            logger.info(f"Найдено {len(items)} предметов для {game}")
        except Exception as e:
            logger.error(f"Ошибка при поиске для {game}: {str(e)}")
            results[game] = []
    
    return results


async def auto_trade_items(
    items_by_game: Dict[str, List[Dict[str, Any]]],
    min_profit: float = 0.5,  # мин. прибыль в USD
    max_price: float = 50.0   # макс. цена покупки в USD
) -> Tuple[int, int, float]:
    """
    Автоматически торгует предметами, найденными в арбитраже.
    
    Args:
        items_by_game: Словарь с предметами по играм
        min_profit: Минимальная прибыль для покупки (в USD)
        max_price: Максимальная цена покупки (в USD)
        
    Returns:
        Кортеж (количество покупок, количество продаж, общая прибыль)
    """
    api = DMarketAPI()
    purchases = 0
    sales = 0
    total_profit = 0.0
    
    for game, items in items_by_game.items():
        for item in items:
            try:
                # Извлекаем информацию о предмете
                item_id = item.get("id", "")
                title = item.get("title", "Unknown item")
                price = float(item.get("price", {}).get("amount", 0)) / 100
                profit = float(item.get("profit", 0)) / 100
                
                # Проверяем, соответствует ли предмет критериям
                if profit < min_profit or price > max_price:
                    logger.debug(f"Пропуск {title}: прибыль {profit} USD, цена {price} USD")
                    continue
                
                # Соблюдаем ограничения API
                await rate_limiter.wait_if_needed("market")
                
                # Эмулируем покупку предмета (в реальной системе - вызов API DMarket)
                logger.info(f"Покупка {title} за {price} USD")
                # success = await api.buy_item(item_id, price)
                success = True  # Эмуляция успешной покупки
                
                if success:
                    purchases += 1
                    
                    # Соблюдаем ограничения API
                    await rate_limiter.wait_if_needed("market")
                    
                    # Эмулируем выставление предмета на продажу
                    sell_price = price + profit
                    logger.info(f"Выставление {title} на продажу за {sell_price} USD")
                    # sale_success = await api.sell_item(item_id, sell_price)
                    sale_success = True  # Эмуляция успешной продажи
                    
                    if sale_success:
                        sales += 1
                        total_profit += profit
                
            except Exception as e:
                logger.error(f"Ошибка при торговле предметом {item.get('title', '')}: {str(e)}")
    
    return purchases, sales, total_profit
