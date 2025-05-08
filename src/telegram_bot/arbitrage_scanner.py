"""
Модуль для поиска арбитражных возможностей между DMarket и другими платформами.

Используется для автоматического поиска предметов, которые можно купить 
на одной площадке и продать на другой с прибылью.

Документация DMarket API: https://docs.dmarket.com/v1/swagger.html
"""

import asyncio
import logging
import os
import time
from typing import List, Dict, Any, Optional, Tuple, Set

from src.dmarket.arbitrage import (
    arbitrage_boost, arbitrage_mid, arbitrage_pro, GAMES, ArbitrageTrader
)
from src.dmarket.dmarket_api_fixed import DMarketAPI
from src.utils.rate_limiter import RateLimiter

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем ограничитель скорости запросов
rate_limiter = RateLimiter(is_authorized=True)


class ArbitrageScanner:
    """
    Класс для сканирования арбитражных возможностей между DMarket и другими платформами.
    
    Основные возможности:
    - Поиск предметов для арбитража в разных режимах (низкий, средний, высокий профит)
    - Поддержка нескольких игр (CS:GO, Dota 2, Rust, TF2 и др.)
    - Кеширование результатов для оптимизации запросов к API
    - Автоматическая торговля найденными предметами
    - Настройка ограничений для управления рисками
    
    Пример использования:
        scanner = ArbitrageScanner()
        opportunities = await scanner.scan_game("csgo", "medium", 10)
    """
    
    def __init__(self, api_client: Optional[DMarketAPI] = None):
        """
        Инициализирует сканер арбитража.
        
        Args:
            api_client: Предварительно созданный клиент DMarketAPI или None 
                        для создания нового при необходимости
        """
        self.api_client = api_client
        self._cache = {}  # Кеш для результатов сканирования
        self._cache_ttl = 300  # Время жизни кеша в секундах (5 минут)
        
        # Ограничения для управления рисками
        self.min_profit = 0.5  # Минимальная прибыль в USD
        self.max_price = 50.0  # Максимальная цена покупки в USD
        self.max_trades = 5    # Максимальное количество сделок за раз
        
        # Статистика работы
        self.total_scans = 0
        self.total_items_found = 0
        self.successful_trades = 0
        self.total_profit = 0.0
        
    def _get_cached_results(self, cache_key: Tuple) -> Optional[List[Dict[str, Any]]]:
        """
        Получает результаты из кеша, если они не устарели.
        
        Args:
            cache_key: Ключ кеша (game, mode, price_from, price_to)
            
        Returns:
            Список предметов из кеша или None, если кеш устарел/отсутствует
        """
        if cache_key not in self._cache:
            return None
            
        items, timestamp = self._cache[cache_key]
        current_time = time.time()
        
        # Проверяем, не устарел ли кеш
        if current_time - timestamp > self._cache_ttl:
            return None
            
        return items
        
    def _save_to_cache(self, cache_key: Tuple, items: List[Dict[str, Any]]) -> None:
        """
        Сохраняет результаты в кеш.
        
        Args:
            cache_key: Ключ кеша
            items: Список предметов для кеширования
        """
        self._cache[cache_key] = (items, time.time())
        logger.debug(f"Кэшировано {len(items)} предметов для {cache_key}")
    
    async def get_api_client(self) -> DMarketAPI:
        """
        Получает экземпляр DMarketAPI клиента.
        
        Returns:
            Экземпляр DMarketAPI, существующий или новый
        """
        if self.api_client is None:
            # Создаем новый клиент с ключами из переменных окружения
            self.api_client = DMarketAPI(
                public_key=os.getenv("DMARKET_PUBLIC_KEY", ""),
                secret_key=os.getenv("DMARKET_SECRET_KEY", ""),
                api_url=os.getenv("DMARKET_API_URL", "https://api.dmarket.com"),
                max_retries=3
            )
        return self.api_client
    
    async def scan_game(
        self,
        game: str,
        mode: str = "medium",
        max_items: int = 20,
        price_from: Optional[float] = None,
        price_to: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Сканирует одну игру для поиска арбитражных возможностей.
        
        Args:
            game: Код игры (например, "csgo", "dota2", "rust", "tf2")
            mode: Режим поиска ("low", "medium", "high")
            max_items: Максимальное количество предметов в результате
            price_from: Минимальная цена предмета (в USD)
            price_to: Максимальная цена предмета (в USD)
            
        Returns:
            Список найденных предметов для арбитража
        """
        # Создаем ключ кеша
        cache_key = (game, mode, price_from or 0, price_to or float('inf'))
        
        # Проверяем кеш
        cached_results = self._get_cached_results(cache_key)
        if cached_results:
            logger.debug(f"Использую кэшированные данные для {game} в режиме {mode}")
            return cached_results[:max_items]
        
        try:
            # Увеличиваем счетчик сканирований
            self.total_scans += 1
            
            # Соблюдаем ограничения API
            await rate_limiter.wait_if_needed("market")
            
            # Пробуем два метода поиска арбитражных возможностей:
            # 1. Встроенные функции для быстрого поиска
            # 2. ArbitrageTrader для более детального поиска
            
            # Метод 1: Используем встроенные функции
            if price_from is None and price_to is None:
                try:
                    if mode == "low":
                        items = arbitrage_boost(game)
                    elif mode == "medium":
                        items = arbitrage_mid(game)
                    elif mode == "high":
                        items = arbitrage_pro(game)
                    else:
                        # По умолчанию используем средний режим
                        items = arbitrage_mid(game)
                    
                    # Если нашли достаточно предметов, возвращаем результат
                    if len(items) >= max_items:
                        results = items[:max_items]
                        self._save_to_cache(cache_key, results)
                        self.total_items_found += len(results)
                        return results
                except Exception as e:
                    logger.warning(f"Ошибка при использовании встроенных функций арбитража: {str(e)}")
                    items = []
            
            # Метод 2: Используем ArbitrageTrader для более детального поиска
            try:
                # Определяем диапазоны прибыли в зависимости от режима
                min_profit = 1.0
                max_profit = 5.0
                
                if mode == "medium":
                    min_profit = 5.0
                    max_profit = 20.0
                elif mode == "high":
                    min_profit = 20.0
                    max_profit = 100.0
                
                # Определяем диапазоны цен, если не указаны явно
                current_price_from = price_from
                current_price_to = price_to
                
                if price_from is None and price_to is None:
                    if mode == "low":
                        current_price_to = 20.0  # До $20 для низкого режима
                    elif mode == "medium":
                        current_price_from = 20.0
                        current_price_to = 100.0  # $20-$100 для среднего режима
                    elif mode == "high":
                        current_price_from = 100.0  # От $100 для высокого режима
                
                # Создаем ArbitrageTrader для поиска предметов
                trader = ArbitrageTrader()
                
                # Получаем предметы с маркета с учетом фильтров
                items_from_trader = await trader.find_profitable_items(
                    game=game,
                    min_profit_percentage=min_profit,  # Минимальный процент прибыли
                    max_items=100,
                    min_price=current_price_from or 1.0,
                    max_price=current_price_to or 100.0
                )
                
                # Фильтруем и стандартизируем формат данных
                items.extend(self._standardize_items(items_from_trader, game, min_profit, max_profit))
            except Exception as e:
                logger.warning(f"Ошибка при использовании ArbitrageTrader: {str(e)}")
            
            # Ограничиваем количество предметов в результате
            results = items[:max_items]
            
            # Сортируем по прибыльности (от большей к меньшей)
            results.sort(key=lambda x: x.get('profit', 0), reverse=True)
            
            # Сохраняем в кэш
            self._save_to_cache(cache_key, results)
            
            # Обновляем статистику
            self.total_items_found += len(results)
            
            return results
        except Exception as e:
            logger.error(f"Ошибка при сканировании игры {game}: {str(e)}")
            return []
    
    def _standardize_items(
        self, 
        items: List, 
        game: str, 
        min_profit: float, 
        max_profit: float
    ) -> List[Dict[str, Any]]:
        """
        Приводит предметы к стандартному формату и фильтрует по прибыли.
        
        Args:
            items: Список предметов из разных источников
            game: Код игры
            min_profit: Минимальная прибыль
            max_profit: Максимальная прибыль
            
        Returns:
            Список стандартизированных предметов
        """
        standardized_items = []
        
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
                standardized_items.append({
                    "title": item.get("name", item.get("title", "Unknown item")),
                    "price": {"amount": int(item.get("buy_price", 0) * 100)},  # В центах
                    "profit": profit,
                    "profit_percent": item.get("profit_percentage", 0),
                    "itemId": item.get("itemId", item.get("id", "")),
                    "game": game,
                    "fee": item.get("fee", 7.0),
                    "liquidity": item.get("liquidity", "medium")
                })
        
        return standardized_items
    
    async def scan_multiple_games(
        self,
        games: List[str] = None,
        mode: str = "medium",
        max_items_per_game: int = 10,
        price_from: Optional[float] = None,
        price_to: Optional[float] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Сканирует несколько игр для поиска арбитражных возможностей.
        
        Args:
            games: Список кодов игр для сканирования (по умолчанию все доступные)
            mode: Режим поиска ("low", "medium", "high")
            max_items_per_game: Максимальное количество предметов на игру
            price_from: Минимальная цена предмета (в USD)
            price_to: Максимальная цена предмета (в USD)
            
        Returns:
            Словарь с кодами игр и списками найденных предметов
        """
        if games is None:
            games = list(GAMES.keys())
        
        results = {}
        
        for game in games:
            try:
                logger.info(f"Поиск арбитражных возможностей для {game} в режиме {mode}")
                
                # Сканируем игру с указанными параметрами
                items = await self.scan_game(
                    game=game,
                    mode=mode,
                    max_items=max_items_per_game,
                    price_from=price_from,
                    price_to=price_to
                )
                
                results[game] = items
                logger.info(f"Найдено {len(items)} предметов для {game}")
            except Exception as e:
                logger.error(f"Ошибка при сканировании игры {game}: {str(e)}")
                results[game] = []
        
        return results
    
    async def check_user_balance(self) -> Dict[str, Any]:
        """
        Проверяет баланс пользователя DMarket с расширенной диагностикой.
        
        Returns:
            Словарь с балансом и детальной информацией
        """
        min_required_balance = 1.0  # Минимальный требуемый баланс в USD
        
        try:
            # Получаем API-клиент
            api_client = await self.get_api_client()
            
            # Получаем информацию о балансе через расширенный метод
            balance_data = await api_client.get_user_balance()
            
            if not balance_data:
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
            if balance_data.get("error", False):
                error_message = balance_data.get("error_message", "Неизвестная ошибка")
                logger.error(f"Ошибка при получении баланса: {error_message}")
                
                diagnosis = "unknown_error"
                display_message = "Ошибка при получении баланса"
                
                # Определяем тип ошибки для диагностики
                if "unauthorized" in error_message.lower() or "авторизации" in error_message.lower():
                    diagnosis = "auth_error"
                    display_message = "Ошибка авторизации: проверьте ключи API"
                elif "ключи" in error_message.lower() or "api key" in error_message.lower():
                    diagnosis = "missing_keys"
                    display_message = "Отсутствуют ключи API"
                elif "timeout" in error_message.lower() or "время" in error_message.lower():
                    diagnosis = "timeout_error"
                    display_message = "Таймаут при запросе баланса: возможны проблемы с сетью"
                elif "404" in error_message or "не найден" in error_message.lower():
                    diagnosis = "endpoint_error"
                    display_message = "Ошибка API: эндпоинт баланса недоступен"
                    
                return {
                    "has_funds": False, 
                    "balance": 0.0,
                    "available_balance": 0.0,
                    "total_balance": 0.0,
                    "min_required": min_required_balance,
                    "error": True,
                    "error_message": error_message,
                    "display_message": display_message,
                    "diagnosis": diagnosis
                }
                
            # Извлекаем значения баланса из полученных данных
            balance = balance_data.get("balance", 0.0)  # Основной баланс
            available_balance = balance_data.get("available_balance", balance)  # Доступный баланс
            total_balance = balance_data.get("total_balance", balance)  # Полный баланс
            
            # Если available_balance не определен, но есть balance
            if available_balance == 0.0 and balance > 0.0:
                available_balance = balance
                logger.info(f"Используем основной баланс {balance:.2f} в качестве доступного")
                
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
                if total_balance > available_balance:
                    frozen_funds = total_balance - available_balance
                    if frozen_funds > 0.01:  # Если различие значимое
                        display_message += f"\nЗаблокировано: ${frozen_funds:.2f} USD"
                        diagnosis = "funds_frozen"
                
            # Формируем финальный результат
            logger.info(
                f"Результат проверки баланса: has_funds={has_funds}, "
                f"balance=${balance:.2f}, available=${available_balance:.2f}, "
                f"total=${total_balance:.2f}, diagnosis={diagnosis}"
            )
            
            return {
                "has_funds": has_funds,
                "balance": balance,
                "available_balance": available_balance,
                "total_balance": total_balance,
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
        self,
        items_by_game: Dict[str, List[Dict[str, Any]]],
        min_profit: Optional[float] = None,
        max_price: Optional[float] = None,
        max_trades: Optional[int] = None,
        risk_level: str = "medium"
    ) -> Tuple[int, int, float]:
        """
        Автоматически торгует предметами, найденными в арбитраже.
        
        Args:
            items_by_game: Словарь с предметами по играм
            min_profit: Минимальная прибыль для покупки (в USD)
            max_price: Максимальная цена покупки (в USD)
            max_trades: Максимальное количество сделок за один запуск
            risk_level: Уровень риска (low, medium, high)
            
        Returns:
            Кортеж (количество покупок, количество продаж, общая прибыль)
        """
        # Используем значения по умолчанию, если не указаны
        min_profit = min_profit or self.min_profit
        max_price = max_price or self.max_price
        max_trades = max_trades or self.max_trades
        
        # Получаем API-клиент
        api_client = await self.get_api_client()
        
        # Проверяем баланс пользователя
        balance_data = await self.check_user_balance()
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
                
            # Проверяем, соответствует ли предмет критериям
            buy_price = item.get("price", {}).get("amount", 0) / 100.0  # Цена в USD
            profit = item.get("profit", 0)
            
            if buy_price > max_price:
                logger.debug(f"Предмет '{item.get('title', '')}' пропущен: цена ${buy_price:.2f} выше лимита ${max_price:.2f}")
                continue
                
            if profit < min_profit:
                logger.debug(f"Предмет '{item.get('title', '')}' пропущен: прибыль ${profit:.2f} ниже минимальной ${min_profit:.2f}")
                continue
                
            if buy_price > remaining_balance:
                logger.debug(f"Предмет '{item.get('title', '')}' пропущен: цена ${buy_price:.2f} выше остатка баланса ${remaining_balance:.2f}")
                continue
            
            # Пробуем купить предмет
            try:
                # Получаем текущую цену и проверяем, не изменилась ли она
                updated_item = await trader.get_current_item_data(
                    item_id=item.get("itemId", ""),
                    game=item.get("game", "csgo")
                )
                
                if not updated_item:
                    logger.warning(f"Предмет '{item.get('title', '')}' недоступен (не найден)")
                    continue
                    
                current_price = updated_item.get("price", buy_price)
                if current_price > buy_price * 1.05:  # Цена выросла более чем на 5%
                    logger.warning(f"Предмет '{item.get('title', '')}' пропущен: цена выросла с ${buy_price:.2f} до ${current_price:.2f}")
                    continue
                
                # Покупаем предмет
                purchase_result = await trader.purchase_item(
                    item_id=item.get("itemId", ""),
                    max_price=buy_price * 1.02,  # Допускаем небольшое повышение цены
                    dmarket_api=api_client
                )
                
                if purchase_result.get("success", False):
                    purchases += 1
                    remaining_balance -= buy_price
                    logger.info(f"Успешно куплен предмет '{item.get('title', '')}' за ${buy_price:.2f}")
                    
                    # Пробуем сразу выставить на продажу
                    sell_price = buy_price + profit
                    sell_result = await trader.list_item_for_sale(
                        item_id=purchase_result.get("new_item_id", ""),
                        price=sell_price,
                        dmarket_api=api_client
                    )
                    
                    if sell_result.get("success", False):
                        sales += 1
                        total_profit += profit
                        logger.info(f"Предмет '{item.get('title', '')}' выставлен на продажу за ${sell_price:.2f} (прибыль ${profit:.2f})")
                    else:
                        logger.warning(f"Не удалось выставить предмет '{item.get('title', '')}' на продажу: {sell_result.get('error', 'Неизвестная ошибка')}")
                else:
                    logger.warning(f"Не удалось купить предмет '{item.get('title', '')}': {purchase_result.get('error', 'Неизвестная ошибка')}")
                    
                # Увеличиваем счетчик сделок независимо от результата
                trades_count += 1
                
                # Делаем небольшую паузу между сделками
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Ошибка при торговле предметом '{item.get('title', '')}': {str(e)}")
                trades_count += 1
        
        # Обновляем статистику
        self.successful_trades += sales
        self.total_profit += total_profit
        
        # Возвращаем результаты торговли
        logger.info(f"Итоги торговли: куплено {purchases}, выставлено на продажу {sales}, ожидаемая прибыль ${total_profit:.2f}")
        return purchases, sales, total_profit
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику работы сканера.
        
        Returns:
            Словарь со статистикой
        """
        return {
            "total_scans": self.total_scans,
            "total_items_found": self.total_items_found,
            "successful_trades": self.successful_trades,
            "total_profit": self.total_profit,
            "cache_size": len(self._cache),
            "cache_ttl": self._cache_ttl
        }
    
    def clear_cache(self) -> None:
        """Очищает кеш результатов сканирования."""
        self._cache.clear()
        logger.info("Кеш результатов сканирования очищен")


# Функции-обертки для обратной совместимости

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
    scanner = ArbitrageScanner()
    return await scanner.scan_game(game, mode, max_items)


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
    scanner = ArbitrageScanner()
    return await scanner.scan_multiple_games(games, mode, max_items_per_game)


async def scan_game_for_arbitrage(
    game: str,
    mode: str = "medium",
    max_items: int = 20,
    price_from: Optional[float] = None,
    price_to: Optional[float] = None,
    dmarket_api: Optional[DMarketAPI] = None
) -> List[Dict[str, Any]]:
    """
    Сканирует одну игру для поиска арбитражных возможностей (функция для обратной совместимости).
    
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
    scanner = ArbitrageScanner(api_client=dmarket_api)
    return await scanner.scan_game(game, mode, max_items, price_from, price_to)


async def scan_multiple_games(
    games: List[str] = ["csgo", "dota2", "rust", "tf2"],
    mode: str = "medium",
    max_items_per_game: int = 10,
    price_from: Optional[float] = None,
    price_to: Optional[float] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Сканирует несколько игр для поиска арбитражных возможностей (функция для обратной совместимости).
    
    Args:
        games: Список кодов игр для сканирования
        mode: Режим поиска ("low", "medium", "high")
        max_items_per_game: Максимальное количество предметов на игру
        price_from: Минимальная цена предмета (в USD)
        price_to: Максимальная цена предмета (в USD)
        
    Returns:
        Словарь с кодами игр и списками найденных предметов
    """
    scanner = ArbitrageScanner()
    return await scanner.scan_multiple_games(games, mode, max_items_per_game, price_from, price_to)


async def check_user_balance(dmarket_api: DMarketAPI) -> Dict[str, Any]:
    """
    Проверяет баланс пользователя DMarket с расширенной диагностикой (функция для обратной совместимости).
    
    Args:
        dmarket_api: Экземпляр DMarketAPI для запроса
        
    Returns:
        Словарь с балансом и детальной информацией
    """
    scanner = ArbitrageScanner(api_client=dmarket_api)
    return await scanner.check_user_balance()


async def auto_trade_items(
    items_by_game: Dict[str, List[Dict[str, Any]]],
    min_profit: float = 0.5,  # мин. прибыль в USD
    max_price: float = 50.0,  # макс. цена покупки в USD
    dmarket_api: Optional[DMarketAPI] = None,
    max_trades: int = 5,  # максимальное количество сделок
    risk_level: str = "medium"  # уровень риска (low, medium, high)
) -> Tuple[int, int, float]:
    """
    Автоматически торгует предметами, найденными в арбитраже (функция для обратной совместимости).
    
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
    scanner = ArbitrageScanner(api_client=dmarket_api)
    return await scanner.auto_trade_items(
        items_by_game=items_by_game,
        min_profit=min_profit,
        max_price=max_price,
        max_trades=max_trades,
        risk_level=risk_level
    )
