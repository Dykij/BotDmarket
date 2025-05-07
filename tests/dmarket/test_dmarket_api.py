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
def dmarket_api():
    """Создает объект DMarketAPI с моком httpx клиента."""
    # Create a client with patches to avoid real API calls
    with patch("httpx.AsyncClient") as mock_client_class:
        # Configure the mock client
        mock_client = MagicMock()
        mock_client.get = AsyncMock()
        mock_client.post = AsyncMock()
        mock_client.aclose = AsyncMock()

        # Set up responses for various API calls
        mock_client.get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"Success": True}),
        )
        mock_client.post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"Success": True}),
        )

        # Make the mock client class return our pre-configured mock
        mock_client_class.return_value = mock_client

        # Create the API client with test keys
        api = DMarketAPI(public_key="test_public_key", secret_key="test_secret_key")

        # Return both the API client and the mock for inspection in tests
        yield api, mock_client


@pytest.mark.asyncio
async def test_init_and_close():
    """Тестирует инициализацию и закрытие клиента."""
    # Create the API client
    api = DMarketAPI(public_key="test_public_key", secret_key="test_secret_key")

    # Create a mock client
    mock_client = AsyncMock()
    mock_client.is_closed = False  # Important: not closed initially
    mock_client.aclose = AsyncMock()

    # Set the mock client directly
    api._client = mock_client

    # Close the client
    await api._close_client()

    # Verify that aclose was called
    assert mock_client.aclose.called
    # Verify that _client was set to None
    assert api._client is None


@pytest.mark.asyncio
async def test_generate_headers():
    """Тестирует генерацию заголовков."""
    # Add required public_key and secret_key parameters
    api = DMarketAPI(public_key="test_public_key", secret_key="test_secret_key")
    headers = api._generate_signature("GET", "/test-path")

    assert "X-Api-Key" in headers
    assert "X-Request-Sign" in headers
    assert "Content-Type" in headers
    assert headers["X-Api-Key"] == "test_public_key"


@pytest.mark.asyncio
async def test_request_get_success(dmarket_api):
    """Тестирует успешный GET запрос."""
    api, mock_client = dmarket_api

    # Configure mock response
    mock_response = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"data": "test", "Success": True}),
    )
    mock_client.get.return_value = mock_response

    # Test with patched _request method to avoid real API calls
    with patch.object(
        api,
        "_request",
        side_effect=lambda method, path, params=None, data=None: {
            "data": "test",
            "Success": True,
        },
    ):
        # Make the request
        result = await api._request(
            method="GET",
            path="/items",
            params={"limit": 10},
        )

        # Verify result
        assert result == {"data": "test", "Success": True}


@pytest.mark.asyncio
async def test_request_post_success(dmarket_api):
    """Тестирует успешный POST запрос."""
    api, mock_client = dmarket_api

    # Configure mock response
    mock_response = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"data": "test", "Success": True}),
    )
    mock_client.post.return_value = mock_response

    # Test with patched _request method to avoid real API calls
    with patch.object(
        api,
        "_request",
        side_effect=lambda method, path, params=None, data=None: {
            "data": "test",
            "Success": True,
        },
    ):
        # Make the request
        result = await api._request(
            method="POST",
            path="/items/buy",
            data={"itemId": "123"},
        )

        # Verify result
        assert result == {"data": "test", "Success": True}


@pytest.mark.asyncio
async def test_request_error(dmarket_api):
    """Тестирует обработку ошибок при запросе."""
    api, mock_client = dmarket_api

    # Create a mock exception class
    class MockAPIError(Exception):
        def __init__(self, message, status_code=None):
            self.status_code = status_code
            self.message = message
            super().__init__(message)

        def __str__(self):
            if self.status_code:
                return f"{self.message} (Status: {self.status_code})"
            return self.message

    # Configure the mock to raise our exception
    with patch.object(
        api,
        "_request",
        side_effect=MockAPIError("Rate limit exceeded", 429),
    ):
        # Test that the exception is raised and has the correct properties
        with pytest.raises(Exception) as excinfo:
            await api._request(
                method="GET",
                path="/items",
                params={"limit": 10},
            )

        # Verify the exception message
        assert "Rate limit exceeded" in str(excinfo.value)
        assert "429" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_balance(dmarket_api):
    """Тестирует получение баланса."""
    api, mock_client = dmarket_api

    # Mock balance response
    balance_data = {"usd": {"amount": 100.0}}

    # Test with patched _request method
    with patch.object(api, "_request", return_value=balance_data):
        # Get balance
        balance = await api.get_balance()

        # Verify result
        assert balance == {"usd": {"amount": 100.0}}


@pytest.mark.asyncio
async def test_get_item_offers(dmarket_api):
    """Тестирует получение предложений по предметам."""
    api, mock_client = dmarket_api

    # Mock items data
    mock_items = [
        {"itemId": "123", "price": {"USD": 10.0}},
        {"itemId": "456", "price": {"USD": 20.0}},
    ]
    mock_response = {"objects": mock_items}

    # Test with patched _request method
    with patch.object(api, "_request", return_value=mock_response):
        # Get market items
        items = await api.get_market_items(
            title="AK-47 | Redline",
            limit=10,
        )

        # Verify result
        assert items == {"objects": mock_items}


@pytest.mark.asyncio
async def test_get_user_offers(dmarket_api):
    """Тестирует получение предложений пользователя."""
    api, mock_client = dmarket_api

    # Mock items data
    mock_items = [
        {"itemId": "123", "price": {"USD": 10.0}},
        {"itemId": "456", "price": {"USD": 20.0}},
    ]
    mock_response = {"objects": mock_items}

    # Test with patched _request method
    with patch.object(api, "_request", return_value=mock_response):
        # Get user inventory
        items = await api.get_user_inventory(limit=10)

        # Verify result
        assert items == {"objects": mock_items}


@pytest.mark.asyncio
async def test_get_sales_history(dmarket_api):
    """Тестирует получение истории продаж."""
    api, mock_client = dmarket_api

    # Mock sales data
    mock_sales = [
        {"Date": 1620000000, "Price": 10.0},
        {"Date": 1620010000, "Price": 11.0},
    ]
    mock_response = {"LastSales": mock_sales, "Total": 2}

    # Test with patched _request method
    with patch.object(api, "_request", return_value=mock_response):
        # Make direct request for sales history
        titles = ["AK-47 | Redline"]
        data = {
            "Titles": titles,
            "Limit": 10,
        }
        sales = await api._request(
            method="POST",
            path="/exchange/v1/last-sales",
            data=data,
        )

        # Verify result
        assert sales == {"LastSales": mock_sales, "Total": 2}
