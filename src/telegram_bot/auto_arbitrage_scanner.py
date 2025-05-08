"""
Модуль для сканирования нескольких игр и автоматической торговли.
"""

import logging
import os
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple

from src.dmarket.arbitrage import (
    arbitrage_boost_async,
    arbitrage_mid_async,
    arbitrage_pro_async,
    ArbitrageTrader
)
from src.dmarket.dmarket_api_fixed import DMarketAPI
from src.utils.rate_limiter import RateLimiter

# Настраиваем логирование
logger = logging.getLogger(__name__)

# Создаем ограничитель скорости запросов
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
        
        # Создаем или используем предоставленный API-клиент
        if dmarket_api is None:
            dmarket_api = DMarketAPI(
                public_key=os.getenv("DMARKET_PUBLIC_KEY", ""),
                secret_key=os.getenv("DMARKET_SECRET_KEY", ""),
                api_url=os.getenv("DMARKET_API_URL", "https://api.dmarket.com"),
                max_retries=3
            )
            close_api = True
        else:
            close_api = False
        
        try:
            # Создаем ArbitrageTrader для поиска предметов
            trader = ArbitrageTrader()
            
            # Получаем предметы с маркета с учетом фильтров
            items = await trader.find_profitable_items(
                game=game,
                min_profit_percentage=min_profit,  # Минимальный процент прибыли
                max_items=100,
                min_price=price_from or 1.0,
                max_price=price_to or 100.0
            )
            
            # Фильтруем по диапазону прибыли в зависимости от режима
            filtered_items = []
            for item in items:
                # Проверяем, не является ли item кортежем
                if isinstance(item, tuple):
                    # Преобразуем кортеж в словарь
                    item_dict = {
                        "name": item[0] if len(item) > 0 else "Unknown item",
                        "buy_price": item[1] if len(item) > 1 else 0,
                        "sell_price": item[2] if len(item) > 2 else 0,
                        "profit": item[3] if len(item) > 3 else 0,
                        "profit_percentage": item[4] if len(item) > 4 else 0,
                        "itemId": "",
                        "game": game
                    }
                    item = item_dict
                
                # Теперь безопасно используем get()
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
        finally:
            # Закрываем API клиент, если он был создан в этой функции
            if close_api and hasattr(dmarket_api, "_close_client"):
                try:
                    await dmarket_api._close_client()
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии API клиента: {e}")
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
        public_key=os.getenv("DMARKET_PUBLIC_KEY", ""),
        secret_key=os.getenv("DMARKET_SECRET_KEY", ""),
        api_url=os.getenv("DMARKET_API_URL", "https://api.dmarket.com"),
        max_retries=3
    )
    
    try:
        tasks = []
        for game in games:
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
            
            # Создаем задачу для сканирования игры
            task = scan_game_for_arbitrage(
                game=game,
                mode=mode,
                max_items=max_items_per_game,
                price_from=current_price_from,
                price_to=current_price_to,
                dmarket_api=dmarket_api
            )
            tasks.append((game, asyncio.create_task(task)))
        
        # Ожидаем завершения всех задач
        for game, task in tasks:
            try:
                results[game] = await task
                logger.info(f"Найдено {len(results[game])} предметов для {game}")
            except Exception as e:
                logger.error(f"Ошибка при сканировании игры {game}: {str(e)}")
                results[game] = []
    
    finally:
        # Закрываем API клиент
        if hasattr(dmarket_api, "_close_client"):
            try:
                await dmarket_api._close_client()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии API клиента: {e}")

    return results


async def check_user_balance(dmarket_api: DMarketAPI) -> Dict[str, Any]:
    """
    Проверяет баланс пользователя DMarket с расширенной диагностикой.
    
    Args:
        dmarket_api: Экземпляр DMarketAPI для запроса
        
    Returns:
        Словарь с балансом и детальной информацией
    """
    min_required_balance = 1.0  # Минимальный требуемый баланс в USD
    
    try:
        # Получаем информацию о балансе через API
        balance_response = await dmarket_api._request(
            method="GET",
            path="/account/v1/balance",
            params={}
        )
        
        if not balance_response:
            logger.error("Не удалось получить баланс пользователя (пустой ответ)")
            return {
                "has_funds": False, 
                "balance": 0.0,
                "available_balance": 0.0,
                "total_balance": 0.0,
                "min_required": min_required_balance,
                "error": True,
                "error_message": "Пустой ответ от API при запросе баланса",
                "display_message": "Не удалось получить баланс (пустой ответ)",
                "diagnosis": "api_error"
            }
        
        # Проверяем на наличие ошибки в ответе
        if "error" in balance_response or not balance_response.get("usd"):
            error_message = balance_response.get("error", {}).get("message", "Неизвестная ошибка")
            logger.error(f"Ошибка при получении баланса: {error_message}")
            
            diagnosis = "unknown_error"
            display_message = "Ошибка при получении баланса"
            
            # Определяем тип ошибки для диагностики
            if "unauthorized" in str(error_message).lower() or "авторизации" in str(error_message).lower():
                diagnosis = "auth_error"
                display_message = "Ошибка авторизации: проверьте ключи API"
            elif "ключи" in str(error_message).lower() or "api key" in str(error_message).lower():
                diagnosis = "missing_keys"
                display_message = "Отсутствуют ключи API"
            elif "timeout" in str(error_message).lower() or "время" in str(error_message).lower():
                diagnosis = "timeout_error"
                display_message = "Таймаут при запросе баланса: возможны проблемы с сетью"
            elif "404" in str(error_message) or "не найден" in str(error_message).lower():
                diagnosis = "endpoint_error"
                display_message = "Ошибка API: эндпоинт баланса недоступен"
                
                return {
                "has_funds": False, 
                "balance": 0.0,
                "available_balance": 0.0,
                "total_balance": 0.0,
                "min_required": min_required_balance,
                "error": True,
                "error_message": str(error_message),
                "display_message": display_message,
                "diagnosis": diagnosis
                }
            
        # Извлекаем значения баланса из полученных данных
        # DMarket API возвращает баланс в формате {"usd": {"available": 1000, "frozen": 200}}
        usd_balance = balance_response.get("usd", {})
        available_amount = usd_balance.get("available", 0)
        frozen_amount = usd_balance.get("frozen", 0)
        
        # Преобразуем из центов в доллары
        available_balance = float(available_amount) / 100
        frozen_balance = float(frozen_amount) / 100
        total_balance = available_balance + frozen_balance
        
        # Проверяем, достаточно ли средств на балансе
        has_funds = available_balance >= min_required_balance
        
        # Собираем дополнительную диагностическую информацию
        diagnosis = "sufficient_funds" if has_funds else "insufficient_funds"
        
        # Формируем сообщение для пользователя
        if has_funds:
            display_message = f"Баланс DMarket: ${available_balance:.2f} USD (достаточно для арбитража)"
        else:
            # Различаем случаи полного отсутствия средств и недостаточного баланса
            if available_balance <= 0:
                display_message = f"На балансе DMarket нет средств. Необходимо минимум ${min_required_balance:.2f} USD"
                diagnosis = "zero_balance"
            else:
                display_message = (
                    f"Недостаточно средств на балансе DMarket.\n"
                    f"Доступно: ${available_balance:.2f} USD\n"
                    f"Необходимо минимум: ${min_required_balance:.2f} USD"
                )
                
            # Если есть заблокированные средства, указываем на это
            if frozen_balance > 0.01:  # Если различие значимое
                display_message += f"\nЗаблокировано: ${frozen_balance:.2f} USD"
                diagnosis = "funds_frozen"
            
        # Формируем финальный результат
        logger.info(
            f"Результат проверки баланса: has_funds={has_funds}, "
            f"balance=${available_balance:.2f}, available=${available_balance:.2f}, "
            f"total=${total_balance:.2f}, diagnosis={diagnosis}"
        )
        
        return {
            "has_funds": has_funds,
            "balance": available_balance,
            "available_balance": available_balance,
            "total_balance": total_balance,
            "frozen_balance": frozen_balance,
            "min_required": min_required_balance,
            "error": False,
            "error_message": "",
            "display_message": display_message,
            "diagnosis": diagnosis
        }
        
    except Exception as e:
        logger.error(f"Неожиданная ошибка при проверке баланса: {str(e)}")
        import traceback
        logger.error(f"Стек вызовов: {traceback.format_exc()}")
        
        return {
            "has_funds": False,
            "balance": 0.0,
            "available_balance": 0.0,
            "total_balance": 0.0,
            "min_required": min_required_balance,
            "error": True,
            "error_message": str(e),
            "display_message": f"Ошибка при проверке баланса: {str(e)}",
            "diagnosis": "exception"
        }


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
    balance_data = await check_user_balance(dmarket_api)
    balance = balance_data.get("balance", 0.0)
    has_funds = balance_data.get("has_funds", False)
    
    if not has_funds or balance < 1.0:
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
    
    # Создаем ArbitrageTrader для выполнения торговли с расширенными методами
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
    
    # Сортируем по прибыльности (от большей к меньшей)
    sorted_items = sorted(
        all_items,
        key=lambda x: x.get("profit", 0),
        reverse=True
    )
    
    # Проходим по отсортированному списку и торгуем предметами
    for item in sorted_items:
        # Проверяем лимиты
        if trades_count >= max_trades:
            logger.info(f"Достигнут лимит сделок ({max_trades})")
            break
        
        if remaining_balance < 1.0:
            logger.info(f"Недостаточно баланса для продолжения торговли")
            break
        
        # Получаем текущую информацию о предмете
        item_id = item.get("itemId")
        if not item_id:
            logger.warning(f"Пропуск предмета без ID: {item.get('title', 'Неизвестный предмет')}")
            continue
            
        # Получаем текущие данные о предмете через API
        current_data = await trader.get_current_item_data(item_id, item.get("game", "csgo"))
        
        if not current_data:
            logger.warning(f"Не удалось получить текущие данные для {item.get('title', 'Unknown')}")
            continue
            
        # Проверяем, что предмет все еще доступен и цена не изменилась
        current_price = current_data.get("price", 0)
        expected_price = item.get("price", {}).get("amount", 0) / 100  # конвертируем из центов
        
        # Если цена существенно изменилась, пропускаем предмет
        if abs(current_price - expected_price) > 0.05:  # 5 центов погрешности
            logger.warning(
                f"Цена изменилась для {item.get('title', 'Unknown')}: "
                f"${expected_price:.2f} -> ${current_price:.2f}"
            )
            continue
            
        # Вычисляем цену продажи
        markup_factor = 1.15  # +15% наценка
        sell_price = current_price * markup_factor
        
        # Рассчитываем прибыль с учетом комиссии
        fee = item.get("fee", 7.0) / 100  # комиссия в процентах
        expected_profit = sell_price * (1 - fee) - current_price
        
        # Проверяем, достаточно ли прибыли
        if expected_profit < min_profit:
            logger.info(
                f"Пропуск предмета {item.get('title', 'Unknown')} из-за малой прибыли: "
                f"${expected_profit:.2f}"
            )
            continue
            
        logger.info(
            f"Попытка покупки предмета {item.get('title', 'Unknown')} "
            f"за ${current_price:.2f} с ожидаемой прибылью ${expected_profit:.2f}"
        )
        
        # Пробуем купить предмет
        purchase_result = await trader.purchase_item(item_id, current_price, dmarket_api)
        
        if not purchase_result["success"]:
            logger.warning(
                f"Ошибка при покупке {item.get('title', 'Unknown')}: "
                f"{purchase_result.get('error', 'Неизвестная ошибка')}"
            )
            continue
            
        # Успешная покупка!
        purchases += 1
        remaining_balance -= current_price
        trades_count += 1
        
        # Получаем ID купленного предмета
        bought_item_id = purchase_result.get("new_item_id", "")
        
        if not bought_item_id:
            logger.error("Не удалось получить ID купленного предмета!")
            continue
            
        logger.info(
            f"Успешно куплен предмет {item.get('title', 'Unknown')} "
            f"за ${current_price:.2f}"
        )
        
        # Даем время на обновление инвентаря
        await asyncio.sleep(3)
        
        # Теперь выставляем предмет на продажу
        sell_result = await trader.list_item_for_sale(bought_item_id, sell_price, dmarket_api)
        
        if not sell_result["success"]:
            logger.warning(
                f"Ошибка при выставлении на продажу {item.get('title', 'Unknown')}: "
                f"{sell_result.get('error', 'Неизвестная ошибка')}"
            )
            continue
            
        # Успешно выставлен на продажу!
        sales += 1
        total_profit += expected_profit
        
        logger.info(
            f"Успешно выставлен на продажу {item.get('title', 'Unknown')} "
            f"за ${sell_price:.2f} с ожидаемой прибылью ${expected_profit:.2f}"
        )
        
        # Небольшая пауза между сделками
        await asyncio.sleep(3)
    
    logger.info(
        f"Итоги автоторговли: {purchases} покупок, {sales} продаж, "
        f"общая прибыль ${total_profit:.2f}"
    )
    
    return purchases, sales, total_profit
