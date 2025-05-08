"""
Модуль для отправки уведомлений о значительных изменениях на рынке.

Этот модуль предоставляет функции для отслеживания рынка и отправки
уведомлений о важных событиях, таких как резкие изменения цен,
появление выгодных предложений или новые арбитражные возможности.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Set, Callable, Tuple
import datetime

from telegram import Bot

from src.dmarket.dmarket_api_fixed import DMarketAPI
from src.dmarket.market_analysis import (
    analyze_price_changes,
    find_trending_items,
    analyze_market_volatility
)

# Настройка логирования
logger = logging.getLogger(__name__)


class MarketAlertsManager:
    """Менеджер уведомлений о событиях на рынке."""

    def __init__(self, bot: Bot, dmarket_api: DMarketAPI):
        """
        Инициализирует менеджер уведомлений.
        
        Args:
            bot: Объект Telegram-бота для отправки сообщений
            dmarket_api: Экземпляр API DMarket для получения данных
        """
        self.bot = bot
        self.dmarket_api = dmarket_api
        self.subscribers: Dict[str, Set[int]] = {
            "price_changes": set(),  # Пользователи, подписанные на изменения цен
            "trending": set(),       # Пользователи, подписанные на трендовые предметы
            "volatility": set(),     # Пользователи, подписанные на волатильность
            "arbitrage": set()       # Пользователи, подписанные на арбитражные возможности
        }
        self.active_alerts: Dict[str, Dict[int, List[Dict[str, Any]]]] = {
            "price_changes": {},  # user_id -> список активных оповещений
            "trending": {},
            "volatility": {},
            "arbitrage": {}
        }
        
        # Настройки порогов для уведомлений
        self.alert_thresholds = {
            "price_change_percent": 15.0,     # Процент изменения цены для уведомления
            "trending_popularity": 50.0,      # Показатель популярности для уведомления о тренде
            "volatility_threshold": 25.0,     # Порог волатильности для уведомления
            "arbitrage_profit_percent": 10.0  # Минимальный процент прибыли для арбитражных уведомлений
        }
        
        # Время последней проверки для каждого типа уведомлений
        self.last_check_time: Dict[str, float] = {
            "price_changes": 0,
            "trending": 0,
            "volatility": 0,
            "arbitrage": 0
        }
        
        # Интервалы проверки (в секундах)
        self.check_intervals: Dict[str, int] = {
            "price_changes": 3600,    # Раз в час
            "trending": 7200,         # Раз в 2 часа
            "volatility": 14400,      # Раз в 4 часа
            "arbitrage": 1800         # Раз в 30 минут
        }
        
        # Словарь с последними отправленными уведомлениями для предотвращения дублирования
        self.sent_alerts: Dict[str, Dict[int, Set[str]]] = {
            alert_type: {} for alert_type in self.subscribers.keys()
        }
        
        # Флаг для управления фоновой задачей
        self.running = False
        self.background_task = None

    async def start_monitoring(self) -> None:
        """Запускает фоновый мониторинг рынка."""
        if self.running:
            logger.warning("Мониторинг рынка уже запущен")
            return
            
        self.running = True
        logger.info("Запуск мониторинга рынка")
        
        # Запускаем фоновую задачу
        self.background_task = asyncio.create_task(self._monitor_market())
        
    async def stop_monitoring(self) -> None:
        """Останавливает фоновый мониторинг рынка."""
        if not self.running:
            logger.warning("Мониторинг рынка не запущен")
            return
            
        logger.info("Остановка мониторинга рынка")
        self.running = False
        
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Мониторинг рынка остановлен")
            
    async def _monitor_market(self) -> None:
        """Фоновая задача для мониторинга рынка."""
        logger.info("Фоновый мониторинг рынка запущен")
        
        try:
            while self.running:
                # Проверяем наличие подписчиков
                if not any(subscribers for subscribers in self.subscribers.values()):
                    logger.debug("Нет активных подписчиков, пропускаем проверку")
                    await asyncio.sleep(60)  # Спим минуту и проверяем снова
                    continue
                
                current_time = time.time()
                
                # Проверяем изменения цен при необходимости
                if (self.subscribers["price_changes"] and 
                    current_time - self.last_check_time["price_changes"] >= self.check_intervals["price_changes"]):
                    
                    await self._check_price_changes()
                    self.last_check_time["price_changes"] = current_time
                
                # Проверяем трендовые предметы при необходимости
                if (self.subscribers["trending"] and 
                    current_time - self.last_check_time["trending"] >= self.check_intervals["trending"]):
                    
                    await self._check_trending_items()
                    self.last_check_time["trending"] = current_time
                
                # Проверяем волатильность при необходимости
                if (self.subscribers["volatility"] and 
                    current_time - self.last_check_time["volatility"] >= self.check_intervals["volatility"]):
                    
                    await self._check_volatility()
                    self.last_check_time["volatility"] = current_time
                
                # Проверяем арбитражные возможности при необходимости
                if (self.subscribers["arbitrage"] and 
                    current_time - self.last_check_time["arbitrage"] >= self.check_intervals["arbitrage"]):
                    
                    await self._check_arbitrage()
                    self.last_check_time["arbitrage"] = current_time
                
                # Ждем перед следующей проверкой
                await asyncio.sleep(30)  # Проверяем подписки каждые 30 секунд
                
        except asyncio.CancelledError:
            logger.info("Задача мониторинга рынка отменена")
        except Exception as e:
            logger.error(f"Ошибка в задаче мониторинга рынка: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Перезапускаем мониторинг после паузы
            if self.running:
                logger.info("Перезапуск мониторинга через 60 секунд...")
                await asyncio.sleep(60)
                self.background_task = asyncio.create_task(self._monitor_market())
    
    async def _check_price_changes(self) -> None:
        """Проверяет изменения цен и отправляет уведомления."""
        logger.info("Проверка изменений цен")
        
        try:
            # Анализируем изменения цен для CS2
            price_changes = await analyze_price_changes(
                game="csgo",
                period="24h",
                min_change_percent=self.alert_thresholds["price_change_percent"],
                dmarket_api=self.dmarket_api,
                limit=10
            )
            
            if not price_changes:
                logger.info("Значительных изменений цен не обнаружено")
                return
                
            # Отправляем уведомления подписчикам
            for user_id in self.subscribers["price_changes"]:
                # Проверяем, какие изменения еще не были отправлены этому пользователю
                if user_id not in self.sent_alerts["price_changes"]:
                    self.sent_alerts["price_changes"][user_id] = set()
                    
                alert_count = 0
                
                for item in price_changes:
                    # Создаем уникальный идентификатор для уведомления
                    item_id = f"{item['market_hash_name']}_{int(item['change_percent'])}"
                    
                    # Пропускаем, если уведомление уже было отправлено
                    if item_id in self.sent_alerts["price_changes"][user_id]:
                        continue
                        
                    # Отправляем не более 3 уведомлений за раз
                    if alert_count >= 3:
                        break
                    
                    # Форматируем сообщение
                    direction = "выросла" if item["direction"] == "up" else "упала"
                    icon = "🔼" if item["direction"] == "up" else "🔽"
                    
                    message = (
                        f"{icon} *Изменение цены!*\n\n"
                        f"Цена на *{item['market_hash_name']}* {direction} на "
                        f"{abs(item['change_percent']):.1f}%\n\n"
                        f"• Текущая цена: ${item['current_price']:.2f}\n"
                        f"• Предыдущая цена: ${item['old_price']:.2f}\n"
                        f"• Изменение: ${abs(item['change_amount']):.2f}\n\n"
                        f"[Посмотреть на DMarket]({item['item_url']})"
                    )
                    
                    # Отправляем уведомление
                    try:
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode="Markdown",
                            disable_web_page_preview=True
                        )
                        
                        # Запоминаем, что отправили это уведомление
                        self.sent_alerts["price_changes"][user_id].add(item_id)
                        alert_count += 1
                        
                        # Небольшая пауза между сообщениями
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
                        
            logger.info(f"Отправлены уведомления об изменениях цен {len(self.subscribers['price_changes'])} пользователям")
            
        except Exception as e:
            logger.error(f"Ошибка при проверке изменений цен: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _check_trending_items(self) -> None:
        """Проверяет трендовые предметы и отправляет уведомления."""
        logger.info("Проверка трендовых предметов")
        
        try:
            # Анализируем трендовые предметы для CS2
            trending_items = await find_trending_items(
                game="csgo",
                min_price=5.0,  # Минимальная цена $5
                dmarket_api=self.dmarket_api,
                limit=10,
                min_sales=10  # Минимум 10 продаж
            )
            
            if not trending_items:
                logger.info("Значимых трендовых предметов не обнаружено")
                return
                
            # Фильтруем по порогу популярности
            trending_items = [
                item for item in trending_items
                if item.get("popularity_score", 0) >= self.alert_thresholds["trending_popularity"]
            ]
            
            if not trending_items:
                logger.info("Нет трендовых предметов, превышающих порог популярности")
                return
                
            # Отправляем уведомления подписчикам
            for user_id in self.subscribers["trending"]:
                # Проверяем, какие тренды еще не были отправлены этому пользователю
                if user_id not in self.sent_alerts["trending"]:
                    self.sent_alerts["trending"][user_id] = set()
                    
                alert_count = 0
                
                for item in trending_items:
                    # Создаем уникальный идентификатор для уведомления
                    item_id = f"{item['market_hash_name']}_{int(item['popularity_score'])}"
                    
                    # Пропускаем, если уведомление уже было отправлено
                    if item_id in self.sent_alerts["trending"][user_id]:
                        continue
                        
                    # Отправляем не более 3 уведомлений за раз
                    if alert_count >= 3:
                        break
                    
                    # Форматируем сообщение
                    message = (
                        f"🔥 *Трендовый предмет!*\n\n"
                        f"*{item['market_hash_name']}* набирает популярность\n\n"
                        f"• Цена: ${item['price']:.2f}\n"
                        f"• Объем продаж: {item['sales_volume']}\n"
                        f"• Предложений: {item.get('offers_count', 0)}\n\n"
                        f"[Посмотреть на DMarket]({item['item_url']})"
                    )
                    
                    # Отправляем уведомление
                    try:
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode="Markdown",
                            disable_web_page_preview=True
                        )
                        
                        # Запоминаем, что отправили это уведомление
                        self.sent_alerts["trending"][user_id].add(item_id)
                        alert_count += 1
                        
                        # Небольшая пауза между сообщениями
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления о тренде пользователю {user_id}: {e}")
            
            logger.info(f"Отправлены уведомления о трендах {len(self.subscribers['trending'])} пользователям")
            
        except Exception as e:
            logger.error(f"Ошибка при проверке трендовых предметов: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _check_volatility(self) -> None:
        """Проверяет волатильность предметов и отправляет уведомления."""
        logger.info("Проверка волатильности предметов")
        
        try:
            # Анализируем волатильные предметы для CS2
            volatile_items = await analyze_market_volatility(
                game="csgo",
                min_price=10.0,  # Минимальная цена $10
                max_price=500.0,  # Максимальная цена $500
                dmarket_api=self.dmarket_api,
                limit=10
            )
            
            if not volatile_items:
                logger.info("Значимых волатильных предметов не обнаружено")
                return
                
            # Фильтруем по порогу волатильности
            volatile_items = [
                item for item in volatile_items
                if item.get("volatility_score", 0) >= self.alert_thresholds["volatility_threshold"]
            ]
            
            if not volatile_items:
                logger.info("Нет волатильных предметов, превышающих порог")
                return
                
            # Отправляем уведомления о рыночной волатильности подписчикам
            market_update_message = (
                f"📊 *Обновление о волатильности рынка*\n\n"
                f"На рынке {len(volatile_items)} предметов с высокой волатильностью. "
                f"Это может указывать на возможности для краткосрочной торговли или увеличенный риск.\n\n"
                f"Топ-3 волатильных предмета:\n"
            )
            
            # Добавляем информацию о топ-3 предметах
            for i, item in enumerate(volatile_items[:3], 1):
                name = item.get("market_hash_name", "Неизвестный предмет")
                price = item.get("current_price", 0)
                volatility = item.get("volatility_score", 0)
                market_update_message += f"{i}. {name} - ${price:.2f} (волатильность: {volatility:.1f})\n"
                
            market_update_message += "\nДля получения полного отчета используйте /market_analysis"
            
            # Отправляем уведомления подписчикам
            for user_id in self.subscribers["volatility"]:
                try:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=market_update_message,
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления о волатильности пользователю {user_id}: {e}")
            
            logger.info(f"Отправлены уведомления о волатильности {len(self.subscribers['volatility'])} пользователям")
            
        except Exception as e:
            logger.error(f"Ошибка при проверке волатильности: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _check_arbitrage(self) -> None:
        """Проверяет арбитражные возможности и отправляет уведомления."""
        logger.info("Проверка арбитражных возможностей")
        
        try:
            # Импортируем функцию для поиска арбитражных возможностей
            from src.telegram_bot.enhanced_auto_arbitrage import start_auto_arbitrage_enhanced
            
            # Ищем арбитражные возможности
            arbitrage_items = await start_auto_arbitrage_enhanced(
                games=["csgo"],
                mode="high",  # Используем высокий режим для уведомлений
                max_items=10
            )
            
            if not arbitrage_items:
                logger.info("Значимых арбитражных возможностей не обнаружено")
                return
                
            # Фильтруем по порогу прибыли
            arbitrage_items = [
                item for item in arbitrage_items
                if item.get("profit_percent", 0) >= self.alert_thresholds["arbitrage_profit_percent"]
            ]
            
            if not arbitrage_items:
                logger.info("Нет арбитражных возможностей, превышающих порог прибыли")
                return
                
            # Отправляем уведомления подписчикам
            for user_id in self.subscribers["arbitrage"]:
                # Проверяем, какие возможности еще не были отправлены этому пользователю
                if user_id not in self.sent_alerts["arbitrage"]:
                    self.sent_alerts["arbitrage"][user_id] = set()
                    
                alert_count = 0
                
                for item in arbitrage_items:
                    # Создаем уникальный идентификатор для уведомления
                    item_name = item.get("title", "Unknown")
                    profit_percent = item.get("profit_percent", 0)
                    item_id = f"{item_name}_{int(profit_percent * 100)}"
                    
                    # Пропускаем, если уведомление уже было отправлено
                    if item_id in self.sent_alerts["arbitrage"][user_id]:
                        continue
                        
                    # Отправляем не более 3 уведомлений за раз
                    if alert_count >= 3:
                        break
                    
                    # Извлекаем данные о предмете
                    price_obj = item.get("price", {})
                    price = float(price_obj.get("amount", 0)) / 100 if isinstance(price_obj, dict) else 0
                    profit = item.get("profit", 0)
                    
                    # Форматируем сообщение
                    message = (
                        f"💰 *Найдена арбитражная возможность!*\n\n"
                        f"*{item_name}*\n\n"
                        f"• Цена покупки: ${price:.2f}\n"
                        f"• Прибыль: ${profit:.2f} ({profit_percent:.1f}%)\n"
                        f"• Игра: {item.get('game', 'CSGO')}\n\n"
                        f"Для использования этой возможности выберите 'Авто Арбитраж' в меню бота."
                    )
                    
                    # Отправляем уведомление
                    try:
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode="Markdown"
                        )
                        
                        # Запоминаем, что отправили это уведомление
                        self.sent_alerts["arbitrage"][user_id].add(item_id)
                        alert_count += 1
                        
                        # Небольшая пауза между сообщениями
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления об арбитраже пользователю {user_id}: {e}")
            
            logger.info(f"Отправлены уведомления об арбитраже {len(self.subscribers['arbitrage'])} пользователям")
            
        except Exception as e:
            logger.error(f"Ошибка при проверке арбитражных возможностей: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def subscribe(self, user_id: int, alert_type: str) -> bool:
        """
        Подписывает пользователя на определенный тип уведомлений.
        
        Args:
            user_id: ID пользователя в Telegram
            alert_type: Тип уведомлений (price_changes, trending, volatility, arbitrage)
            
        Returns:
            True если подписка успешна, False в противном случае
        """
        if alert_type not in self.subscribers:
            logger.warning(f"Неизвестный тип уведомлений: {alert_type}")
            return False
            
        self.subscribers[alert_type].add(user_id)
        logger.info(f"Пользователь {user_id} подписался на уведомления типа '{alert_type}'")
        return True
    
    def unsubscribe(self, user_id: int, alert_type: str) -> bool:
        """
        Отписывает пользователя от определенного типа уведомлений.
        
        Args:
            user_id: ID пользователя в Telegram
            alert_type: Тип уведомлений (price_changes, trending, volatility, arbitrage)
            
        Returns:
            True если отписка успешна, False в противном случае
        """
        if alert_type not in self.subscribers:
            logger.warning(f"Неизвестный тип уведомлений: {alert_type}")
            return False
            
        if user_id in self.subscribers[alert_type]:
            self.subscribers[alert_type].remove(user_id)
            logger.info(f"Пользователь {user_id} отписался от уведомлений типа '{alert_type}'")
            return True
            
        return False
    
    def unsubscribe_all(self, user_id: int) -> bool:
        """
        Отписывает пользователя от всех типов уведомлений.
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            True если отписка успешна, False в противном случае
        """
        unsubscribed = False
        
        for alert_type in self.subscribers:
            if user_id in self.subscribers[alert_type]:
                self.subscribers[alert_type].remove(user_id)
                unsubscribed = True
                
        if unsubscribed:
            logger.info(f"Пользователь {user_id} отписался от всех уведомлений")
            
        return unsubscribed
    
    def get_user_subscriptions(self, user_id: int) -> List[str]:
        """
        Возвращает список типов уведомлений, на которые подписан пользователь.
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Список типов уведомлений
        """
        return [
            alert_type for alert_type in self.subscribers
            if user_id in self.subscribers[alert_type]
        ]
    
    def get_subscription_count(self, alert_type: Optional[str] = None) -> int:
        """
        Возвращает количество подписчиков для указанного типа уведомлений.
        Если тип не указан, возвращает общее количество уникальных подписчиков.
        
        Args:
            alert_type: Тип уведомлений или None для всех типов
            
        Returns:
            Количество подписчиков
        """
        if alert_type is not None:
            if alert_type in self.subscribers:
                return len(self.subscribers[alert_type])
            return 0
            
        # Считаем уникальных подписчиков на все типы уведомлений
        unique_subscribers = set()
        
        for subscribers in self.subscribers.values():
            unique_subscribers.update(subscribers)
            
        return len(unique_subscribers)
    
    def update_alert_threshold(self, alert_type: str, new_threshold: float) -> bool:
        """
        Обновляет порог для указанного типа уведомлений.
        
        Args:
            alert_type: Тип уведомлений
            new_threshold: Новое значение порога
            
        Returns:
            True если обновление успешно, False в противном случае
        """
        threshold_key = {
            "price_changes": "price_change_percent",
            "trending": "trending_popularity",
            "volatility": "volatility_threshold",
            "arbitrage": "arbitrage_profit_percent"
        }.get(alert_type)
        
        if not threshold_key or threshold_key not in self.alert_thresholds:
            logger.warning(f"Неизвестный тип порога для уведомлений: {alert_type}")
            return False
            
        # Проверяем допустимые значения
        if new_threshold <= 0:
            logger.warning(f"Недопустимое значение порога: {new_threshold}")
            return False
            
        self.alert_thresholds[threshold_key] = new_threshold
        logger.info(f"Порог для уведомлений типа '{alert_type}' обновлен до {new_threshold}")
        return True
    
    def update_check_interval(self, alert_type: str, new_interval: int) -> bool:
        """
        Обновляет интервал проверки для указанного типа уведомлений.
        
        Args:
            alert_type: Тип уведомлений
            new_interval: Новое значение интервала в секундах
            
        Returns:
            True если обновление успешно, False в противном случае
        """
        if alert_type not in self.check_intervals:
            logger.warning(f"Неизвестный тип уведомлений: {alert_type}")
            return False
            
        # Проверяем допустимые значения (минимум 5 минут)
        if new_interval < 300:
            logger.warning(f"Интервал проверки слишком мал: {new_interval} с")
            return False
            
        self.check_intervals[alert_type] = new_interval
        logger.info(f"Интервал проверки для уведомлений типа '{alert_type}' обновлен до {new_interval} с")
        return True
    
    def clear_sent_alerts(self, alert_type: Optional[str] = None, user_id: Optional[int] = None) -> None:
        """
        Очищает историю отправленных уведомлений.
        
        Args:
            alert_type: Тип уведомлений или None для всех типов
            user_id: ID пользователя или None для всех пользователей
        """
        if alert_type is not None:
            if alert_type not in self.sent_alerts:
                return
                
            if user_id is not None:
                # Очищаем для конкретного пользователя и типа
                if user_id in self.sent_alerts[alert_type]:
                    self.sent_alerts[alert_type][user_id].clear()
            else:
                # Очищаем для всех пользователей указанного типа
                self.sent_alerts[alert_type].clear()
        elif user_id is not None:
            # Очищаем для конкретного пользователя всех типов
            for alert_type in self.sent_alerts:
                if user_id in self.sent_alerts[alert_type]:
                    self.sent_alerts[alert_type][user_id].clear()
        else:
            # Очищаем все
            for alert_type in self.sent_alerts:
                self.sent_alerts[alert_type].clear()
        
        logger.info("История отправленных уведомлений очищена")
    
    def clear_old_alerts(self, max_age_days: int = 7) -> int:
        """
        Очищает старые отправленные уведомления из истории.
        
        Args:
            max_age_days: Максимальный возраст уведомлений в днях
            
        Returns:
            Количество удаленных уведомлений
        """
        # Эта функция не имеет реальной реализации, так как мы не храним даты отправки
        # В реальном приложении здесь была бы логика удаления старых уведомлений
        # На данный момент просто очищаем все
        total_cleared = 0
        
        for alert_type in self.sent_alerts:
            for user_id in list(self.sent_alerts[alert_type].keys()):
                count = len(self.sent_alerts[alert_type][user_id])
                self.sent_alerts[alert_type][user_id].clear()
                total_cleared += count
        
        logger.info(f"Очищено {total_cleared} старых уведомлений")
        return total_cleared


# Функция для создания глобального экземпляра менеджера уведомлений
_alerts_manager: Optional[MarketAlertsManager] = None

def get_alerts_manager(bot: Optional[Bot] = None, dmarket_api: Optional[DMarketAPI] = None) -> MarketAlertsManager:
    """
    Возвращает глобальный экземпляр менеджера уведомлений.
    
    Args:
        bot: Объект Telegram-бота (если экземпляр еще не создан)
        dmarket_api: Экземпляр API DMarket (если экземпляр еще не создан)
        
    Returns:
        Экземпляр менеджера уведомлений
    """
    global _alerts_manager
    
    if _alerts_manager is None:
        if bot is None or dmarket_api is None:
            raise ValueError("Для создания менеджера уведомлений требуются bot и dmarket_api")
            
        _alerts_manager = MarketAlertsManager(bot, dmarket_api)
        
    return _alerts_manager 