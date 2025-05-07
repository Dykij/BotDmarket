"""Тесты для модуля realtime_price_watcher.py"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dmarket.dmarket_api import DMarketAPI
from src.dmarket.realtime_price_watcher import PriceAlert, RealtimePriceWatcher
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
def mock_websocket_client():
    """Мок для DMarketWebSocketClient."""
    ws_client = MagicMock(spec=DMarketWebSocketClient)
    ws_client.connect = AsyncMock(return_value=True)
    ws_client.subscribe = AsyncMock(return_value=True)
    ws_client.unsubscribe = AsyncMock(return_value=True)
    ws_client.listen = AsyncMock()
    ws_client.close = AsyncMock()
    ws_client.register_handler = MagicMock()
    return ws_client


@pytest.fixture
def price_watcher(mock_api_client, mock_websocket_client):
    """Создает экземпляр RealtimePriceWatcher для тестирования."""
    with patch(
        "src.dmarket.realtime_price_watcher.DMarketWebSocketClient",
        return_value=mock_websocket_client,
    ):
        watcher = RealtimePriceWatcher(mock_api_client)
        return watcher


@pytest.mark.asyncio
async def test_start_watcher(price_watcher, mock_websocket_client):
    """Тест запуска наблюдателя за ценами."""
    result = await price_watcher.start()

    assert result is True
    assert price_watcher.is_running is True
    mock_websocket_client.register_handler.assert_called_once_with(
        "market:update",
        price_watcher._handle_market_update,
    )
    mock_websocket_client.connect.assert_called_once()
    assert isinstance(price_watcher.ws_task, asyncio.Task)


@pytest.mark.asyncio
async def test_stop_watcher(price_watcher, mock_websocket_client):
    """Тест остановки наблюдателя за ценами."""
    # Запускаем наблюдатель
    await price_watcher.start()

    # Останавливаем наблюдатель
    await price_watcher.stop()

    assert price_watcher.is_running is False
    mock_websocket_client.close.assert_called_once()
    assert price_watcher.ws_task.cancelled()


def test_watch_item(price_watcher):
    """Тест добавления предмета для отслеживания."""
    price_watcher.watch_item("123456", 100.0)

    assert "123456" in price_watcher.watched_items
    assert price_watcher.price_cache["123456"] == 100.0


def test_unwatch_item(price_watcher):
    """Тест удаления предмета из отслеживания."""
    # Добавляем предмет
    price_watcher.watch_item("123456", 100.0)

    # Удаляем предмет
    price_watcher.unwatch_item("123456")

    assert "123456" not in price_watcher.watched_items
    assert "123456" not in price_watcher.price_cache


def test_add_price_alert(price_watcher):
    """Тест добавления оповещения о цене."""
    alert = PriceAlert(
        item_id="123456",
        market_hash_name="AWP | Asiimov (Field-Tested)",
        target_price=50.0,
        condition="below",
    )

    price_watcher.add_price_alert(alert)

    assert alert in price_watcher.price_alerts["123456"]
    assert "123456" in price_watcher.watched_items


def test_remove_price_alert(price_watcher):
    """Тест удаления оповещения о цене."""
    alert = PriceAlert(
        item_id="123456",
        market_hash_name="AWP | Asiimov (Field-Tested)",
        target_price=50.0,
        condition="below",
    )

    # Добавляем оповещение
    price_watcher.add_price_alert(alert)

    # Удаляем оповещение
    price_watcher.remove_price_alert(alert)

    assert "123456" not in price_watcher.price_alerts
    # Предмет все еще отслеживается, даже после удаления оповещения
    assert "123456" in price_watcher.watched_items


def test_register_price_change_handler(price_watcher):
    """Тест регистрации обработчика изменения цены."""

    async def handler(item_id, old_price, new_price):
        pass

    price_watcher.register_price_change_handler(handler, "123456")

    assert handler in price_watcher.price_change_handlers["123456"]


def test_register_alert_handler(price_watcher):
    """Тест регистрации обработчика срабатывания оповещения."""

    async def handler(alert, current_price):
        pass

    price_watcher.register_alert_handler(handler)

    assert handler in price_watcher.alert_handlers


@pytest.mark.asyncio
async def test_handle_market_update(price_watcher):
    """Тест обработки сообщения об обновлении рынка."""
    # Добавляем предмет для отслеживания
    price_watcher.watch_item("123456")

    # Регистрируем обработчик изменения цены
    price_change_handler = AsyncMock()
    price_watcher.register_price_change_handler(price_change_handler, "123456")

    # Создаем тестовое сообщение
    message = {
        "channel": "market:update",
        "data": {
            "items": [
                {
                    "itemId": "123456",
                    "price": {
                        "USD": "100.00",
                    },
                },
            ],
        },
    }

    # Вызываем обработчик сообщения
    await price_watcher._handle_market_update(message)

    # Проверяем, что цена обновилась
    assert price_watcher.price_cache["123456"] == 100.0

    # Проверяем, что обработчик был вызван
    price_change_handler.assert_called_once_with("123456", None, 100.0)


@pytest.mark.asyncio
async def test_check_alerts(price_watcher):
    """Тест проверки оповещений."""
    # Создаем оповещение
    alert = PriceAlert(
        item_id="123456",
        market_hash_name="AWP | Asiimov (Field-Tested)",
        target_price=50.0,
        condition="below",
    )

    # Добавляем оповещение
    price_watcher.add_price_alert(alert)

    # Регистрируем обработчик оповещений
    alert_handler = AsyncMock()
    price_watcher.register_alert_handler(alert_handler)

    # Проверяем оповещение с ценой выше целевой
    await price_watcher._check_alerts("123456", 60.0)
    assert not alert_handler.called
    assert not alert.is_triggered

    # Проверяем оповещение с ценой ниже целевой
    await price_watcher._check_alerts("123456", 40.0)
    alert_handler.assert_called_once_with(alert, 40.0)
    assert alert.is_triggered


def test_price_alert_check_condition():
    """Тест проверки условия оповещения о цене."""
    # Оповещение для цены ниже целевой
    below_alert = PriceAlert(
        item_id="123456",
        market_hash_name="AWP | Asiimov (Field-Tested)",
        target_price=50.0,
        condition="below",
    )

    # Оповещение для цены выше целевой
    above_alert = PriceAlert(
        item_id="123456",
        market_hash_name="AWP | Asiimov (Field-Tested)",
        target_price=50.0,
        condition="above",
    )

    # Проверяем условие "below"
    assert below_alert.check_condition(40.0) is True
    assert below_alert.check_condition(50.0) is True
    assert below_alert.check_condition(60.0) is False

    # Проверяем условие "above"
    assert above_alert.check_condition(40.0) is False
    assert above_alert.check_condition(50.0) is True
    assert above_alert.check_condition(60.0) is True


@pytest.mark.asyncio
async def test_process_price_change(price_watcher):
    """Тест обработки изменения цены предмета."""
    # Регистрируем обработчик для конкретного предмета
    specific_handler = AsyncMock()
    price_watcher.register_price_change_handler(specific_handler, "123456")

    # Регистрируем глобальный обработчик
    global_handler = AsyncMock()
    price_watcher.register_price_change_handler(global_handler, "*")

    # Вызываем обработку изменения цены
    await price_watcher._process_price_change("123456", 100.0, 120.0)

    # Проверяем, что оба обработчика были вызваны
    specific_handler.assert_called_once_with("123456", 100.0, 120.0)
    global_handler.assert_called_once_with("123456", 100.0, 120.0)

    # Проверяем, что при одинаковой цене обработчики не вызываются
    specific_handler.reset_mock()
    global_handler.reset_mock()

    await price_watcher._process_price_change("123456", 120.0, 120.0)

    assert not specific_handler.called
    assert not global_handler.called
