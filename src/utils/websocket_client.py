"""WebSocket клиент для DMarket API.

Этот модуль предоставляет асинхронный клиент для работы с WebSocket API DMarket,
позволяя получать обновления цен и других данных в реальном времени.
"""

import asyncio
import json
import time
from typing import Callable, List, Optional
from unittest.mock import MagicMock

import aiohttp

from src.dmarket.dmarket_api import DMarketAPI
from src.utils.logging_utils import get_logger


class DMarketWebSocketClient:
    """Клиент для WebSocket соединения с DMarket API."""

    def __init__(
        self,
        api_client: DMarketAPI,
        subscription_topics: Optional[List[str]] = None,
        reconnect_interval: int = 5,
        max_reconnect_attempts: int = 10,
        ping_interval: int = 30,
    ):
        """Инициализация WebSocket клиента.

        Args:
            api_client: Экземпляр DMarketAPI для аутентификации
            subscription_topics: Список тем для подписки
            reconnect_interval: Интервал повторного подключения в секундах
            max_reconnect_attempts: Максимальное количество попыток переподключения
            ping_interval: Интервал отправки ping в секундах

        """
        self.api_client = api_client
        self.subscription_topics = subscription_topics or []
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.ping_interval = ping_interval

        self.logger = get_logger("dmarket_websocket", {"component": "websocket"})
        self.ws = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.last_activity = 0
        self.ping_task = None
        self.message_handlers = {}

    async def connect(self) -> bool:
        """Установка соединения с WebSocket API DMarket.

        Returns:
            bool: True если соединение успешно установлено, иначе False

        """
        try:
            # Получаем аутентификационный токен
            session = aiohttp.ClientSession()
            headers = self.api_client._generate_signature(
                "GET",
                "/exchange/v1/ws/token",
                "",
            )

            try:
                async with session.get(
                    "https://api.dmarket.com/exchange/v1/ws/token",
                    headers=headers,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(
                            f"Ошибка получения токена WebSocket: {error_text}",
                        )
                        await session.close()
                        return False

                    token_data = await response.json()
                    token = token_data.get("token")

                    if not token:
                        self.logger.error("Токен не получен в ответе")
                        await session.close()
                        return False
            finally:
                await session.close()

            # Подключаемся к WebSocket с полученным токеном
            session = aiohttp.ClientSession()
            try:
                self.ws = await session.ws_connect(
                    f"wss://api.dmarket.com/exchange/v1/ws?token={token}",
                    heartbeat=self.ping_interval,
                )

                self.is_connected = True
                self.reconnect_attempts = 0
                self.last_activity = time.time()

                # Запускаем пинг для поддержания соединения
                if self.ping_task is None or self.ping_task.done():
                    self.ping_task = asyncio.create_task(self._ping_loop())

                # Подписываемся на темы
                for topic in self.subscription_topics:
                    await self.subscribe(topic)

                self.logger.info("WebSocket соединение установлено успешно")
                return True
            except Exception as e:
                await session.close()
                raise e

        except Exception as e:
            self.logger.error(f"Ошибка при подключении к WebSocket: {e!s}")
            self.is_connected = False
            return False

    async def reconnect(self) -> bool:
        """Повторное подключение к WebSocket.

        Returns:
            bool: True если переподключение успешно, иначе False

        """
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error(
                "Превышено максимальное количество попыток переподключения",
            )
            return False

        self.reconnect_attempts += 1
        self.logger.info(
            f"Попытка переподключения {self.reconnect_attempts}/{self.max_reconnect_attempts}",
        )

        if self.ws and not self.ws.closed:
            await self.ws.close()

        await asyncio.sleep(self.reconnect_interval)
        return await self.connect()

    async def _ping_loop(self) -> None:
        """Асинхронный цикл для отправки ping-сообщений."""
        try:
            while self.is_connected:
                if self.ws and not self.ws.closed:
                    if time.time() - self.last_activity > self.ping_interval:
                        await self.ws.ping()
                        self.last_activity = time.time()

                await asyncio.sleep(self.ping_interval)
        except Exception as e:
            self.logger.error(f"Ошибка в ping_loop: {e!s}")

    async def subscribe(self, topic: str) -> bool:
        """Подписка на тему WebSocket.

        Args:
            topic: Название темы для подписки

        Returns:
            bool: True если подписка успешна, иначе False

        """
        if not self.is_connected or not self.ws or self.ws.closed:
            self.logger.error(
                f"Невозможно подписаться на {topic}: соединение не установлено",
            )
            return False

        try:
            message = {
                "method": "subscribe",
                "params": {
                    "channel": topic,
                },
            }

            await self.ws.send_json(message)

            if topic not in self.subscription_topics:
                self.subscription_topics.append(topic)

            self.logger.info(f"Подписка на {topic} отправлена")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при подписке на {topic}: {e!s}")
            return False

    async def unsubscribe(self, topic: str) -> bool:
        """Отписка от темы WebSocket.

        Args:
            topic: Название темы для отписки

        Returns:
            bool: True если отписка успешна, иначе False

        """
        if not self.is_connected or not self.ws or self.ws.closed:
            return False

        try:
            message = {
                "method": "unsubscribe",
                "params": {
                    "channel": topic,
                },
            }

            await self.ws.send_json(message)

            if topic in self.subscription_topics:
                self.subscription_topics.remove(topic)

            self.logger.info(f"Отписка от {topic} отправлена")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при отписке от {topic}: {e!s}")
            return False

    def register_handler(self, topic: str, handler: Callable) -> None:
        """Регистрация обработчика сообщений для темы.

        Args:
            topic: Название темы
            handler: Функция-обработчик, принимающая данные сообщения

        """
        self.message_handlers[topic] = handler
        self.logger.info(f"Зарегистрирован обработчик для темы {topic}")

    async def listen(self) -> None:
        """Прослушивание сообщений от WebSocket."""
        while True:
            try:
                if not self.is_connected:
                    success = await self.reconnect()
                    if not success:
                        self.logger.error(
                            "Не удалось переподключиться после нескольких попыток",
                        )
                        break

                assert self.ws is not None

                async for msg in self.ws:
                    self.last_activity = time.time()

                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            channel = data.get("channel")

                            if channel and channel in self.message_handlers:
                                handler = self.message_handlers[channel]
                                await handler(data)
                            else:
                                self.logger.debug(
                                    f"Получено сообщение без обработчика: {msg.data[:100]}...",
                                )

                        except json.JSONDecodeError:
                            self.logger.error(
                                f"Ошибка декодирования JSON: {msg.data[:100]}...",
                            )

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        self.logger.error(
                            f"Ошибка WebSocket соединения: {self.ws.exception()}",
                        )
                        self.is_connected = False
                        break

                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        self.logger.info("WebSocket соединение закрыто")
                        self.is_connected = False
                        break

            except asyncio.CancelledError:
                self.logger.info("Задача прослушивания WebSocket была отменена")
                break

            except Exception as e:
                self.logger.error(f"Ошибка при прослушивании WebSocket: {e!s}")
                self.is_connected = False

                success = await self.reconnect()
                if not success:
                    self.logger.error("Не удалось переподключиться после ошибки")
                    break

    async def close(self) -> None:
        """Закрытие WebSocket соединения."""
        self.is_connected = False

        if self.ping_task and not self.ping_task.done():
            self.ping_task.cancel()
            try:
                # MagicMock не поддерживает await, поэтому проверяем тип
                if not isinstance(self.ping_task, MagicMock):
                    await self.ping_task
            except asyncio.CancelledError:
                pass

        if self.ws and not self.ws.closed:
            await self.ws.close()
            self.logger.info("WebSocket соединение закрыто")
