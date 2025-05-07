"""Тесты для модуля dmarket_api.py.

Этот модуль тестирует базовые функции API клиента для DMarket.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dmarket.dmarket_api import DMarketAPI


@pytest.fixture
def mock_httpx_client():
    """Создает мок для httpx клиента."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock()
    mock_client.post = AsyncMock()
    mock_client.get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"Success": True}),
    )
    mock_client.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"Success": True}),
    )
    return mock_client


@pytest.fixture
def dmarket_api(mock_httpx_client):
    """Создает объект DMarketAPI с моком httpx клиента."""
    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        api = DMarketAPI("test_public_key", "test_secret_key")
        # Замена настоящего httpx клиента моком
        api._client = mock_httpx_client
        return api


@pytest.mark.asyncio
async def test_init_and_close():
    """Тестирует инициализацию и закрытие клиента."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.aclose = AsyncMock()

        api = DMarketAPI("test_public_key", "test_secret_key")
        await api._close_client()

        assert mock_instance.aclose.called


@pytest.mark.asyncio
async def test_generate_signature():
    """Тестирует генерацию заголовков."""
    api = DMarketAPI("test_public_key", "test_secret_key")
    headers = api._generate_signature("GET", "/test-endpoint")

    assert "X-Api-Key" in headers
    assert "X-Request-Sign" in headers
    assert "Content-Type" in headers


@pytest.mark.asyncio
async def test_get_client():
    """Тестирует получение клиента."""
    with patch("httpx.AsyncClient") as mock_client:
        api = DMarketAPI("test_public_key", "test_secret_key")
        client = await api._get_client()

        assert client is not None
        assert mock_client.called


@pytest.mark.asyncio
async def test_request_get_success(dmarket_api, mock_httpx_client):
    """Тестирует успешный GET запрос."""
    # Настраиваем мок для ответа
    mock_response = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"data": "test", "Success": True}),
    )
    mock_httpx_client.get.return_value = mock_response

    # Выполняем запрос
    result = await dmarket_api._request(
        method="GET",
        path="/items",
        params={"limit": 10},
    )

    # Проверяем результат
    assert result == {"data": "test", "Success": True}
    mock_httpx_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_request_post_success(dmarket_api, mock_httpx_client):
    """Тестирует успешный POST запрос."""
    # Настраиваем мок для ответа
    mock_response = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"data": "test", "Success": True}),
    )
    mock_httpx_client.post.return_value = mock_response

    # Выполняем запрос
    result = await dmarket_api._request(
        method="POST",
        path="/items/buy",
        data={"itemId": "123"},
    )

    # Проверяем результат
    assert result == {"data": "test", "Success": True}
    mock_httpx_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_request_error(dmarket_api, mock_httpx_client):
    """Тестирует обработку ошибок при запросе."""
    # Настраиваем мок для ответа с ошибкой
    mock_response = MagicMock(
        status_code=429,
        json=MagicMock(return_value={"error": "Rate limit exceeded"}),
        text="Rate limit exceeded",
        headers={"Retry-After": "30"},
    )
    mock_httpx_client.get.return_value = mock_response
    mock_httpx_client.get.side_effect = None

    # Проверяем, что метод обрабатывает ошибку корректно
    result = await dmarket_api._request(
        method="GET",
        path="/items",
        params={"limit": 10},
    )

    # Проверяем, что в результате есть информация об ошибке
    assert "error" in result
    assert "Rate limit exceeded" in result.get("error", "")


@pytest.mark.asyncio
async def test_get_balance(dmarket_api, mock_httpx_client):
    """Тестирует получение баланса."""
    # Настраиваем мок для ответа
    mock_response = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"usd": {"amount": 10000}}),  # $100 в центах
    )
    mock_httpx_client.get.return_value = mock_response

    # Выполняем запрос
    balance = await dmarket_api.get_balance()

    # Проверяем результат
    assert balance == {"usd": {"amount": 10000}}
    mock_httpx_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_market_items(dmarket_api, mock_httpx_client):
    """Тестирует получение предметов с маркета."""
    # Настраиваем мок для ответа
    mock_items = [
        {"itemId": "123", "price": {"amount": 1000, "currency": "USD"}},  # $10 в центах
        {"itemId": "456", "price": {"amount": 2000, "currency": "USD"}},  # $20 в центах
    ]
    mock_response = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"items": mock_items}),
    )
    mock_httpx_client.get.return_value = mock_response

    # Выполняем запрос
    items = await dmarket_api.get_market_items(
        game="csgo",
        title="AK-47 | Redline",
        limit=10,
    )

    # Проверяем результат
    assert items == {"items": mock_items}
    mock_httpx_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_balance(dmarket_api, mock_httpx_client):
    """Тестирует получение баланса пользователя."""
    # Настраиваем мок для ответа
    mock_response = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"usd": {"amount": 10000}}),  # $100 в центах
    )
    mock_httpx_client.get.return_value = mock_response

    # Выполняем запрос
    balance = await dmarket_api.get_user_balance()

    # Проверяем результат
    assert balance == {"usd": {"amount": 10000}}
    mock_httpx_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_suggested_price(dmarket_api, mock_httpx_client):
    """Тестирует получение рекомендованной цены."""
    # Настраиваем мок для ответа
    mock_items = [
        {
            "itemId": "123",
            "title": "AK-47 | Redline",
            "price": {"amount": 1000, "currency": "USD"},
            "suggestedPrice": {"amount": 1200, "currency": "USD"},
        },
    ]
    mock_response = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"items": mock_items}),
    )
    mock_httpx_client.get.return_value = mock_response

    # Выполняем запрос
    price = await dmarket_api.get_suggested_price("AK-47 | Redline", "csgo")

    # Проверяем результат - должно быть преобразование из центов в доллары
    assert price == 12.0  # $12
    mock_httpx_client.get.assert_called_once()
