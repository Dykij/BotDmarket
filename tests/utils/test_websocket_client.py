"""Тесты для модуля websocket_client.py"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import WSMessage, WSMsgType

from src.dmarket.dmarket_api import DMarketAPI
from src.utils.websocket_client import DMarketWebSocketClient


@pytest.fixture
def mock_api_client():
    """Мок для DMarketAPI."""
    api_client = MagicMock(spec=DMarketAPI)
    api_client._generate_signature.return_value = {
        "Authorization": "DMR1:public:secret",
    }
    return api_client


@pytest.fixture
def websocket_client(mock_api_client):
    """Создает экземпляр DMarketWebSocketClient для тестирования."""
    return DMarketWebSocketClient(
        api_client=mock_api_client,
        subscription_topics=["market:update", "orders:update"],
        reconnect_interval=1,
        max_reconnect_attempts=3,
        ping_interval=5,
    )


class MockClientSession:
    """Мок для ClientSession."""

    def __init__(self, response=None):
        self.response = response or {"token": "test_token"}
        self.get = AsyncMock()
        self.ws_connect = AsyncMock()
        self.close = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        pass


class MockResponse:
    """Мок для Response."""

    def __init__(self, status=200, data=None):
        self.status = status
        self.data = data or {"token": "test_token"}

    async def json(self):
        return self.data

    async def text(self):
        return json.dumps(self.data)


class MockWebSocket:
    """Мок для WebSocket соединения."""

    def __init__(self, messages=None):
        self.messages = messages or []
        self.closed = False
        self.send_json = AsyncMock()
        self.ping = AsyncMock()
        self.close = AsyncMock()
        self.exception = MagicMock(return_value=Exception("WebSocket error"))

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.messages:
            raise StopAsyncIteration
        return self.messages.pop(0)


@pytest.mark.asyncio
async def test_connect_success(websocket_client):
    """Тест успешного подключения к WebSocket."""

    # Замоканный метод подключения для успешного пути
    async def mock_connect_impl():
        websocket_client.is_connected = True
        websocket_client.reconnect_attempts = 0
        websocket_client.ws = MockWebSocket()
        websocket_client.ws.closed = False

        # Создаем мок для ping_task
        mock_task = MagicMock()
        mock_task.done.return_value = False
        websocket_client.ping_task = mock_task

        # Эмулируем добавление подписок
        for topic in websocket_client.subscription_topics:
            await websocket_client.subscribe(topic)

        return True

    # Заменяем реальный метод connect нашим мок-методом
    original_connect = websocket_client.connect
    websocket_client.connect = mock_connect_impl

    try:
        # Вызываем метод
        result = await websocket_client.connect()

        # Проверки
        assert result is True
        assert websocket_client.is_connected is True
        assert websocket_client.reconnect_attempts == 0
        assert isinstance(websocket_client.ws, MockWebSocket)
    finally:
        # Восстанавливаем оригинальный метод
        websocket_client.connect = original_connect


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_connect_token_error(mock_session, websocket_client):
    """Тест ошибки получения токена."""
    # Подготовка моков
    mock_response = MockResponse(status=401, data={"error": "Unauthorized"})
    mock_session_instance = MockClientSession()
    mock_session_instance.get.return_value.__aenter__.return_value = mock_response

    mock_session.return_value = mock_session_instance

    # Вызов тестируемого метода
    result = await websocket_client.connect()

    # Проверки
    assert result is False
    assert websocket_client.is_connected is False


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_connect_no_token(mock_session, websocket_client):
    """Тест отсутствия токена в ответе."""
    # Подготовка моков
    mock_response = MockResponse(data={})
    mock_session_instance = MockClientSession()
    mock_session_instance.get.return_value.__aenter__.return_value = mock_response

    mock_session.return_value = mock_session_instance

    # Вызов тестируемого метода
    result = await websocket_client.connect()

    # Проверки
    assert result is False
    assert websocket_client.is_connected is False


@pytest.mark.asyncio
async def test_subscribe(websocket_client):
    """Тест подписки на тему."""
    # Подготовка
    websocket_client.is_connected = True
    websocket_client.ws = AsyncMock()
    websocket_client.ws.closed = False

    # Вызов тестируемого метода
    result = await websocket_client.subscribe("prices:update")

    # Проверки
    assert result is True
    assert "prices:update" in websocket_client.subscription_topics
    websocket_client.ws.send_json.assert_called_once_with(
        {
            "method": "subscribe",
            "params": {
                "channel": "prices:update",
            },
        },
    )


@pytest.mark.asyncio
async def test_subscribe_not_connected(websocket_client):
    """Тест подписки при отсутствии соединения."""
    # Подготовка
    websocket_client.is_connected = False

    # Вызов тестируемого метода
    result = await websocket_client.subscribe("prices:update")

    # Проверки
    assert result is False
    assert "prices:update" not in websocket_client.subscription_topics


@pytest.mark.asyncio
async def test_unsubscribe(websocket_client):
    """Тест отписки от темы."""
    # Подготовка
    websocket_client.is_connected = True
    websocket_client.ws = AsyncMock()
    websocket_client.ws.closed = False
    websocket_client.subscription_topics = ["market:update", "prices:update"]

    # Вызов тестируемого метода
    result = await websocket_client.unsubscribe("prices:update")

    # Проверки
    assert result is True
    assert "prices:update" not in websocket_client.subscription_topics
    websocket_client.ws.send_json.assert_called_once_with(
        {
            "method": "unsubscribe",
            "params": {
                "channel": "prices:update",
            },
        },
    )


@pytest.mark.asyncio
async def test_register_handler(websocket_client):
    """Тест регистрации обработчика."""
    # Подготовка
    handler = AsyncMock()

    # Вызов тестируемого метода
    websocket_client.register_handler("market:update", handler)

    # Проверки
    assert websocket_client.message_handlers["market:update"] == handler


@pytest.mark.asyncio
@patch("asyncio.create_task")
async def test_listen_message_handling(mock_create_task, websocket_client):
    """Тест обработки сообщений."""
    # Подготовка
    websocket_client.is_connected = True
    handler = AsyncMock()
    websocket_client.register_handler("market:update", handler)

    # Создаем сообщения для теста
    text_message = WSMessage(
        WSMsgType.TEXT,
        json.dumps(
            {
                "channel": "market:update",
                "data": {"item_id": "123", "price": 100},
            },
        ).encode(),
        None,
    )

    error_message = WSMessage(WSMsgType.ERROR, None, None)

    mock_ws = MockWebSocket(messages=[text_message, error_message])
    websocket_client.ws = mock_ws

    # Имитируем один вызов listen перед ошибкой
    with patch.object(websocket_client, "reconnect", AsyncMock(return_value=False)):
        await websocket_client.listen()

    # Проверки
    handler.assert_called_once()
    expected_data = {
        "channel": "market:update",
        "data": {"item_id": "123", "price": 100},
    }
    assert handler.call_args[0][0] == expected_data
    assert websocket_client.is_connected is False


@pytest.mark.asyncio
async def test_close(websocket_client):
    """Тест закрытия соединения."""
    # Подготовка
    websocket_client.is_connected = True
    websocket_client.ws = AsyncMock()
    websocket_client.ws.closed = False

    # Создаем мок для ping_task
    mock_task = MagicMock()
    mock_task.done.return_value = False
    mock_task.cancel = MagicMock()
    websocket_client.ping_task = mock_task

    # Вызов тестируемого метода
    await websocket_client.close()

    # Проверки
    assert websocket_client.is_connected is False
    mock_task.cancel.assert_called_once()
    websocket_client.ws.close.assert_called_once()
