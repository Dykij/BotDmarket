"""Модуль для отслеживания цен на DMarket в реальном времени.

Этот модуль использует WebSocket соединение для получения обновлений
о ценах предметов на маркетплейсе DMarket в режиме реального времени.
"""

import asyncio
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from src.dmarket.dmarket_api import DMarketAPI
from src.utils.logging_utils import get_logger
from src.utils.websocket_client import DMarketWebSocketClient


class PriceAlert:
    """Класс для представления оповещения о цене."""

    def __init__(
        self,
        item_id: str,
        market_hash_name: str,
        target_price: float,
        condition: str = "below",
        game: str = "csgo",
    ):
        """Инициализация оповещения о цене.

        Args:
            item_id: ID предмета в DMarket
            market_hash_name: Полное название предмета
            target_price: Целевая цена для оповещения
            condition: Условие срабатывания ('below' или 'above')
            game: Игра, к которой относится предмет

        """
        self.item_id = item_id
        self.market_hash_name = market_hash_name
        self.target_price = target_price
        self.condition = condition
        self.game = game
        self.is_triggered = False

    def check_condition(self, current_price: float) -> bool:
        """Проверка условия срабатывания оповещения.

        Args:
            current_price: Текущая цена предмета

        Returns:
            bool: True если условие сработало, иначе False

        """
        if (self.condition == "below" and current_price <= self.target_price) or (
            self.condition == "above" and current_price >= self.target_price
        ):
            return True
        return False


class RealtimePriceWatcher:
    """Класс для отслеживания цен в реальном времени."""

    def __init__(self, api_client: DMarketAPI):
        """Инициализация наблюдателя за ценами.

        Args:
            api_client: Экземпляр DMarketAPI для работы с API

        """
        self.api_client = api_client
        self.websocket_client = DMarketWebSocketClient(api_client)
        self.logger = get_logger(
            "realtime_price_watcher", {"component": "price_watcher"}
        )

        # Словарь для отслеживания цен {item_id: latest_price}
        self.price_cache = {}

        # Словарь для хранения оповещений {item_id: [alert1, alert2, ...]}
        self.price_alerts = defaultdict(list)

        # Список обработчиков событий изменения цен {item_id: [handler1, handler2, ...]}
        self.price_change_handlers = defaultdict(list)

        # Список обработчиков срабатывания оповещений
        self.alert_handlers = []

        # Множество отслеживаемых предметов
        self.watched_items = set()

        # Задачи
        self.ws_task = None
        self.is_running = False

    async def start(self) -> bool:
        """Запуск наблюдателя за ценами.

        Returns:
            bool: True если запуск успешен, иначе False

        """
        if self.is_running:
            self.logger.warning("Наблюдатель за ценами уже запущен")
            return True

        # Регистрируем обработчик сообщений WebSocket
        self.websocket_client.register_handler(
            "market:update", self._handle_market_update
        )

        # Подключаемся к WebSocket
        connected = await self.websocket_client.connect()
        if not connected:
            self.logger.error("Не удалось подключиться к WebSocket API DMarket")
            return False

        # Запускаем задачу прослушивания
        self.ws_task = asyncio.create_task(self.websocket_client.listen())
        self.is_running = True

        self.logger.info("Наблюдатель за ценами успешно запущен")
        return True

    async def stop(self) -> None:
        """Остановка наблюдателя за ценами."""
        if not self.is_running:
            return

        self.is_running = False

        # Отменяем задачу прослушивания
        if self.ws_task and not self.ws_task.done():
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass

        # Закрываем WebSocket соединение
        await self.websocket_client.close()

        self.logger.info("Наблюдатель за ценами остановлен")

    async def _handle_market_update(self, message: Dict[str, Any]) -> None:
        """Обработка сообщения об обновлении рынка.

        Args:
            message: Сообщение от WebSocket API

        """
        try:
            data = message.get("data", {})

            # Обрабатываем обновления цен
            if "items" in data:
                for item in data["items"]:
                    item_id = item.get("itemId")
                    price = item.get("price", {}).get("USD")

                    if not item_id or price is None:
                        continue

                    # Преобразуем цену в float
                    try:
                        price_float = float(price)
                    except (ValueError, TypeError):
                        continue

                    # Если этот предмет отслеживается
                    if item_id in self.watched_items:
                        old_price = self.price_cache.get(item_id)
                        self.price_cache[item_id] = price_float

                        # Запускаем обработчики изменения цены
                        await self._process_price_change(
                            item_id, old_price, price_float
                        )

                        # Проверяем оповещения
                        await self._check_alerts(item_id, price_float)

        except Exception as e:
            self.logger.error(f"Ошибка при обработке сообщения обновления рынка: {e!s}")

    async def _process_price_change(
        self,
        item_id: str,
        old_price: Optional[float],
        new_price: float,
    ) -> None:
        """Обработка изменения цены предмета.

        Args:
            item_id: ID предмета
            old_price: Предыдущая цена предмета
            new_price: Новая цена предмета

        """
        # Если цена не изменилась, ничего не делаем
        if old_price == new_price:
            return

        # Выполняем все обработчики изменения цены для данного предмета
        handlers = self.price_change_handlers.get(item_id, [])
        handlers.extend(
            self.price_change_handlers.get("*", [])
        )  # Глобальные обработчики

        for handler in handlers:
            try:
                await handler(item_id, old_price, new_price)
            except Exception as e:
                self.logger.error(f"Ошибка в обработчике изменения цены: {e!s}")

    async def _check_alerts(self, item_id: str, current_price: float) -> None:
        """Проверка оповещений для предмета.

        Args:
            item_id: ID предмета
            current_price: Текущая цена предмета

        """
        alerts = self.price_alerts.get(item_id, [])

        for alert in alerts:
            # Проверяем условие и не сработало ли оповещение ранее
            if not alert.is_triggered and alert.check_condition(current_price):
                alert.is_triggered = True

                # Запускаем обработчики оповещений
                for handler in self.alert_handlers:
                    try:
                        await handler(alert, current_price)
                    except Exception as e:
                        self.logger.error(f"Ошибка в обработчике оповещения: {e!s}")

    def watch_item(self, item_id: str, initial_price: Optional[float] = None) -> None:
        """Добавить предмет для отслеживания.

        Args:
            item_id: ID предмета для отслеживания
            initial_price: Начальная цена предмета (если известна)

        """
        self.watched_items.add(item_id)

        if initial_price is not None:
            self.price_cache[item_id] = initial_price

        self.logger.debug(f"Предмет {item_id} добавлен для отслеживания")

    def unwatch_item(self, item_id: str) -> None:
        """Удалить предмет из отслеживания.

        Args:
            item_id: ID предмета для удаления из отслеживания

        """
        if item_id in self.watched_items:
            self.watched_items.remove(item_id)

        # Удаляем из кеша цен
        if item_id in self.price_cache:
            del self.price_cache[item_id]

        self.logger.debug(f"Предмет {item_id} удален из отслеживания")

    def add_price_alert(self, alert: PriceAlert) -> None:
        """Добавить оповещение о цене.

        Args:
            alert: Оповещение о цене для добавления

        """
        self.price_alerts[alert.item_id].append(alert)

        # Добавляем предмет для отслеживания
        self.watch_item(alert.item_id)

        self.logger.info(
            f"Добавлено оповещение для {alert.market_hash_name} "
            f"({alert.condition} {alert.target_price})",
        )

    def remove_price_alert(self, alert: PriceAlert) -> None:
        """Удалить оповещение о цене.

        Args:
            alert: Оповещение о цене для удаления

        """
        if alert.item_id in self.price_alerts:
            if alert in self.price_alerts[alert.item_id]:
                self.price_alerts[alert.item_id].remove(alert)

            # Если больше нет оповещений для этого предмета, удаляем ключ
            if not self.price_alerts[alert.item_id]:
                del self.price_alerts[alert.item_id]

        self.logger.debug(f"Удалено оповещение для {alert.market_hash_name}")

    def register_price_change_handler(
        self,
        handler: Callable[[str, Optional[float], float], None],
        item_id: str = "*",
    ) -> None:
        """Регистрация обработчика изменения цены.

        Args:
            handler: Функция-обработчик, которая будет вызвана при изменении цены
            item_id: ID предмета для отслеживания или "*" для всех предметов

        """
        self.price_change_handlers[item_id].append(handler)

    def register_alert_handler(
        self,
        handler: Callable[[PriceAlert, float], None],
    ) -> None:
        """Регистрация обработчика срабатывания оповещения.

        Args:
            handler: Функция-обработчик, которая будет вызвана при срабатывании оповещения

        """
        self.alert_handlers.append(handler)

    def get_current_price(self, item_id: str) -> Optional[float]:
        """Получить текущую цену предмета из кеша.

        Args:
            item_id: ID предмета

        Returns:
            Optional[float]: Текущая цена предмета или None, если предмет не отслеживается

        """
        return self.price_cache.get(item_id)

    def get_all_alerts(self) -> Dict[str, List[PriceAlert]]:
        """Получить все активные оповещения.

        Returns:
            Dict[str, List[PriceAlert]]: Словарь оповещений по ID предметов

        """
        return self.price_alerts


# Пример использования:
"""
async def main():
    from src.dmarket.dmarket_api import DMarketAPI
    from src.utils.logging_utils import setup_logging
    
    # Настройка логирования
    setup_logging()
    
    # Инициализация API клиента
    api_client = DMarketAPI(public_key="your_public_key", secret_key="your_secret_key")
    
    # Создание наблюдателя за ценами
    watcher = RealtimePriceWatcher(api_client)
    
    # Обработчик изменения цены
    async def on_price_change(item_id, old_price, new_price):
        change = ((new_price - old_price) / old_price) * 100 if old_price else 0
        print(f"Цена изменилась: {item_id}, {old_price} -> {new_price} ({change:.2f}%)")
    
    # Обработчик срабатывания оповещения
    async def on_alert_triggered(alert, current_price):
        print(f"Оповещение сработало! {alert.market_hash_name}: {alert.target_price} {alert.condition} {current_price}")
    
    # Регистрация обработчиков
    watcher.register_price_change_handler(on_price_change)
    watcher.register_alert_handler(on_alert_triggered)
    
    # Добавление оповещений
    alert1 = PriceAlert(
        item_id="123456",
        market_hash_name="AWP | Asiimov (Field-Tested)",
        target_price=50.0,
        condition="below"
    )
    watcher.add_price_alert(alert1)
    
    # Запуск наблюдателя
    await watcher.start()
    
    try:
        # Ожидаем событий
        await asyncio.sleep(3600)  # 1 час
    finally:
        # Останавливаем наблюдатель
        await watcher.stop()

if __name__ == "__main__":
    asyncio.run(main())
"""
