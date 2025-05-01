"""
Модуль для сканирования нескольких игр и автоматической торговли.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple

from src.dmarket.arbitrage import ArbitrageTrader, GAMES, fetch_market_items
from src.dmarket.dmarket_api import DMarketAPI
from src.utils.rate_limiter import RateLimiter

# Настраиваем логирование
logger = logging.getLogger(__name__)

# Создаем экземпляр ограничителя скорости запросов
rate_limiter = RateLimiter(is_authorized=True)

# Кеш для хранения результатов сканирования
# Ключ: (game, mode, price_from, price_to), Значение: (items, timestamp)
_scanner_cache = {}
_cache_ttl = 300  # Время жизни кеша в секундах (5 минут)


def _get_cached_results(cache_key: Tuple[str, str, float, float]) -> Optional[List[Dict[str, Any]]]:
    """
    Получить кэшированные результаты сканирования.
    
    Args:
        cache_key: Ключ кэша (game, mode, price_from, price_to)
        
    Returns:
        Список предметов из кэша или None, если кэш устарел
    """
    if cache_key not in _scanner_cache:
        return None
        
    items, timestamp = _scanner_cache[cache_key]
    current_time = time.time()
    
    # Проверяем, не устарел ли кэш
    if current_time - timestamp > _cache_ttl:
        return None
        
    return items


def _save_to_cache(
    cache_key: Tuple[str, str, float, float],
    items: List[Dict[str, Any]]
) -> None:
    """
    Сохранить результаты в кэш.
    
    Args:
        cache_key: Ключ кэша (game, mode, price_from, price_to)
        items: Список предметов для кэширования
    """
    _scanner_cache[cache_key] = (items, time.time())
    logger.debug(f"Кэшировано {len(items)} предметов для {cache_key[0]}")


async def scan_game_for_arbitrage(
    game: str,
    mode: str = "medium",
    max_items: int = 20,
    price_from: Optional[float] = None,
    price_to: Optional[float] = None,
    dmarket_api: Optional[DMarketAPI] = None
) -> List[Dict[str, Any]]:
    """
    Сканирует одну игру для поиска арбитражных возможностей.
    
    Args:
        game: Код игры (например, "csgo", "dota2", "rust", "tf2")
        mode: Режим поиска ("low", "medium", "high")
        max_items: Максимальное количество предметов в результате
        price_from: Минимальная цена предмета (в USD)
        price_to: Максимальная цена предмета (в USD)
        dmarket_api: Экземпляр API DMarket или None для создания нового
        
    Returns:
        Список найденных предметов для арбитража
    """
    # Создаем ключ кэша
    cache_key = (game, mode, price_from or 0, price_to or float('inf'))
    
    # Проверяем кэш
    cached_results = _get_cached_results(cache_key)
    if cached_results:
        logger.debug(f"Использую кэшированные данные для {game} в режиме {mode}")
        return cached_results[:max_items]
    
    try:
        # Соблюдаем ограничения API
        await rate_limiter.wait_if_needed("market")
        
        # Определяем диапазоны прибыли в зависимости от режима
        min_profit = 1.0
        max_profit = 5.0
        
        if mode == "medium":
            min_profit = 5.0
            max_profit = 20.0
        elif mode == "high":
            min_profit = 20.0
            max_profit = 100.0
        
        # Создаем ArbitrageTrader для поиска предметов
        trader = ArbitrageTrader()
        
        # Получаем предметы с маркета с учетом фильтров
        items = await trader.find_profitable_items(
            game=game,
            min_profit_percentage=5.0,  # Минимальный процент прибыли
            max_items=100,
            min_price=price_from or 1.0,
            max_price=price_to or 100.0
        )
        
        # Фильтруем по диапазону прибыли в зависимости от режима
        filtered_items = []
        for item in items:
            profit = item.get("profit", 0)
            if isinstance(profit, str) and '$' in profit:
                profit = float(profit.replace('$', '').strip())
                
            if min_profit <= profit <= max_profit:
                # Приводим к единому формату данных
                filtered_items.append({
                    "title": item.get("name", "Unknown item"),
                    "price": {"amount": int(item.get("buy_price", 0) * 100)},  # В центах
                    "profit": profit,
                    "profit_percent": item.get("profit_percentage", 0),
                    "itemId": item.get("itemId", ""),
                    "game": game,
                    "fee": item.get("fee", 7.0),
                    "liquidity": item.get("liquidity", "medium")
                })
                
        # Ограничиваем количество предметов в результате
        result = filtered_items[:max_items]
        
        # Сохраняем в кэш
        _save_to_cache(cache_key, result)
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при сканировании игры {game}: {str(e)}")
        return []


async def scan_multiple_games(
    games: List[str] = ["csgo", "dota2", "rust", "tf2"],
    mode: str = "medium",
    max_items_per_game: int = 10,
    price_from: Optional[float] = None,
    price_to: Optional[float] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Сканирует несколько игр для поиска арбитражных возможностей.
    
    Args:
        games: Список кодов игр для сканирования
        mode: Режим поиска ("low", "medium", "high")
        max_items_per_game: Максимальное количество предметов на игру
        price_from: Минимальная цена предмета (в USD)
        price_to: Максимальная цена предмета (в USD)
        
    Returns:
        Словарь с кодами игр и списками найденных предметов
    """
    results = {}
    
    # Создаем один экземпляр API для всех запросов
    dmarket_api = DMarketAPI(
        os.environ.get("DMARKET_PUBLIC_KEY", ""),
        os.environ.get("DMARKET_SECRET_KEY", ""),
        os.environ.get("DMARKET_API_URL", "https://api.dmarket.com"),
        max_retries=3
    )
    
    for game in games:
        try:
            logger.info(f"Поиск арбитражных возможностей для {game} в режиме {mode}")
            
            # Определяем диапазоны цен в зависимости от режима
            current_price_from = price_from
            current_price_to = price_to
            
            if not price_from and not price_to:
                if mode == "low":
                    current_price_to = 20.0  # До $20 для низкого режима
                elif mode == "medium":
                    current_price_from = 20.0
                    current_price_to = 100.0  # $20-$100 для среднего режима
                elif mode == "high":
                    current_price_from = 100.0  # От $100 для высокого режима
            
            # Сканируем игру с указанными параметрами
            async with dmarket_api:
                items = await scan_game_for_arbitrage(
                    game=game,
                    mode=mode,
                    max_items=max_items_per_game,
                    price_from=current_price_from,
                    price_to=current_price_to,
                    dmarket_api=dmarket_api
                )
            
            results[game] = items
            logger.info(f"Найдено {len(items)} предметов для {game}")
        except Exception as e:
            logger.error(f"Ошибка при сканировании игры {game}: {str(e)}")
            results[game] = []
    
    return results


async def check_user_balance(dmarket_api: DMarketAPI) -> Tuple[bool, float]:
    """
    Проверяет баланс пользователя.
    
    Args:
        dmarket_api: Экземпляр DMarketAPI для запроса
        
    Returns:
        Кортеж (достаточно средств, текущий баланс)
    """
    try:
        async with dmarket_api:
            balance_data = await dmarket_api.get_user_balance()
        
        logger.debug(f"Полученные данные баланса: {balance_data}")
        
        if not balance_data:
            logger.error("Не удалось получить данные о балансе (ответ пустой)")
            return False, 0.0
            
        if "usd" not in balance_data:
            logger.error(f"В данных баланса отсутствует ключ 'usd': {balance_data}")
            return False, 0.0
            
        # Получаем баланс в центах, затем конвертируем в доллары
        try:
            if isinstance(balance_data["usd"], dict) and "amount" in balance_data["usd"]:
                balance = float(balance_data["usd"]["amount"]) / 100  # центы в доллары
            elif isinstance(balance_data["usd"], (int, float)):
                balance = float(balance_data["usd"])  # уже в долларах
            elif isinstance(balance_data["usd"], str):
                balance = float(balance_data["usd"])  # строковое представление долларов
            else:
                logger.error(f"Неизвестный формат поля 'usd': {balance_data['usd']}")
                return False, 0.0
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка преобразования баланса: {e}, данные: {balance_data['usd']}")
            return False, 0.0
        
        # Проверяем, достаточно ли средств для минимальной сделки
        if balance < 1.0:  # Предполагаем минимальную сумму сделки $1
            logger.warning(f"Недостаточно средств на балансе: ${balance:.2f}")
            return False, balance
            
        logger.info(f"Баланс достаточен для торговли: ${balance:.2f}")
        return True, balance
    except Exception as e:
        logger.error(f"Ошибка при проверке баланса: {str(e)}")
        return False, 0.0


async def auto_trade_items(
    items_by_game: Dict[str, List[Dict[str, Any]]],
    min_profit: float = 0.5,  # мин. прибыль в USD
    max_price: float = 50.0,  # макс. цена покупки в USD
    dmarket_api: Optional[DMarketAPI] = None,
    max_trades: int = 5,  # максимальное количество сделок
    risk_level: str = "medium"  # уровень риска (low, medium, high)
) -> Tuple[int, int, float]:
    """
    Автоматически торгует предметами, найденными в арбитраже.
    
    Args:
        items_by_game: Словарь с предметами по играм
        min_profit: Минимальная прибыль для покупки (в USD)
        max_price: Максимальная цена покупки (в USD)
        dmarket_api: Экземпляр DMarketAPI для выполнения операций (обязательный)
        max_trades: Максимальное количество сделок за один запуск
        risk_level: Уровень риска (low, medium, high)
        
    Returns:
        Кортеж (количество покупок, количество продаж, общая прибыль)
    """
    # Проверяем, что API-клиент передан
    if dmarket_api is None:
        raise ValueError("DMarketAPI обязательно должен быть передан в auto_trade_items")
    
    # Проверяем баланс пользователя
    has_funds, balance = await check_user_balance(dmarket_api)
    if not has_funds:
        logger.warning(f"Автоторговля невозможна: недостаточно средств (${balance:.2f})")
        return 0, 0, 0.0
    
    # Настройки управления рисками в зависимости от уровня
    if risk_level == "low":
        max_trades = min(max_trades, 2)  # Не более 2 сделок
        max_price = min(max_price, 20.0)  # Не более $20 за предмет
        min_profit = max(min_profit, 1.0)  # Минимум $1 прибыли
    elif risk_level == "medium":
        max_trades = min(max_trades, 5)  # Не более 5 сделок
        max_price = min(max_price, 50.0)  # Не более $50 за предмет
    elif risk_level == "high":
        max_price = min(max_price, balance * 0.8)  # Не более 80% баланса
        
    # Лимит на общую сумму торговли
    total_trade_limit = balance * 0.9  # Не использовать более 90% баланса
    
    logger.info(
        f"Параметры торговли: риск = {risk_level}, баланс = ${balance:.2f}, "
        f"макс. сделок = {max_trades}, макс. цена = ${max_price:.2f}"
    )
    
    # Создаем ArbitrageTrader для выполнения торговли
    trader = ArbitrageTrader()
    trader.set_trading_limits(max_trade_value=max_price, daily_limit=total_trade_limit)
    
    purchases = 0
    sales = 0
    total_profit = 0.0
    trades_count = 0
    remaining_balance = balance
    
    # Собираем все предметы из всех игр в один список для сортировки
    all_items = []
    for game_code, items in items_by_game.items():
        for item in items:
            item["game"] = game_code
            all_items.append(item)
    
    # Сортируем по прибыльности (по убыванию)
    all_items = sorted(
        all_items,
        key=lambda x: x.get("profit", 0),
        reverse=True
    )
    
    # Обрабатываем предметы
    for item in all_items:
        try:
            if trades_count >= max_trades:
                logger.info(f"Достигнут лимит количества сделок ({max_trades})")
                break
            
            # Извлекаем информацию о предмете
            title = item.get("title", "Unknown item")
            
            # Обрабатываем цену
            price_value = item.get("price", {})
            if isinstance(price_value, dict):
                price = float(price_value.get("amount", 0)) / 100
            else:
                price_str = str(price_value)
                price_str = price_str.replace('$', '').strip()
                price = float(price_str)
                
            # Обрабатываем прибыль
            profit_value = item.get("profit", 0)
            if isinstance(profit_value, str) and '$' in profit_value:
                profit = float(profit_value.replace('$', '').strip())
            else:
                profit = float(profit_value)
            
            # Проверяем, соответствует ли предмет критериям
            if profit < min_profit or price > max_price or price > remaining_balance:
                logger.debug(
                    f"Пропуск {title}: прибыль ${profit:.2f}, "
                    f"цена ${price:.2f}, баланс ${remaining_balance:.2f}"
                )
                continue
            
            # Соблюдаем ограничения API
            await rate_limiter.wait_if_needed("market")
            
            logger.info(f"Покупка {title} за ${price:.2f}")
            
            # Создаем элемент для торговли
            trade_item = {
                "name": title,
                "buy_price": price,
                "sell_price": price + profit,
                "profit": profit,
                "profit_percentage": item.get("profit_percent", 0),
                "itemId": item.get("itemId", ""),
                "market_hash_name": title,
                "game": item.get("game", "csgo")
            }
            
            # Выполняем сделку
            trade_result = await trader.execute_arbitrage_trade(trade_item)
            
            if trade_result.get("success"):
                purchases += 1
                sales += 1
                total_profit += profit
                remaining_balance -= price
                trades_count += 1
                logger.info(
                    f"Успешная сделка с {title}: "
                    f"куплено за ${price:.2f}, прибыль ${profit:.2f}"
                )
            else:
                errors = trade_result.get("errors", [])
                error_msg = ", ".join(errors) if errors else "Неизвестная ошибка"
                logger.warning(f"Ошибка при торговле {title}: {error_msg}")
                
                if trade_result.get("bought"):
                    purchases += 1
                    logger.warning(
                        f"Предмет {title} был куплен за ${price:.2f}, "
                        f"но не был продан!"
                    )
                    remaining_balance -= price
        except Exception as e:
            logger.error(f"Ошибка при торговле предметом {item.get('title', '')}: {str(e)}")
    
    return purchases, sales, total_profit


# Добавляем импорт os, который используется в функции scan_multiple_games
import os
