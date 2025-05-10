"""Объединенные тесты для DMarket API.

Этот модуль содержит тесты для проверки:
1. Основной функциональности DMarket API
2. Получения баланса пользователя
3. Получения предметов с маркета
4. Работы с лимитами запросов
5. Обработки ошибок API
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Импортируем необходимые модули для тестирования
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from dmarket.dmarket_api import DMarketAPI

# Тестовые константы
TEST_PUBLIC_KEY = "test_public_key"
TEST_SECRET_KEY = "test_secret_key"

# Фикстуры для тестирования


@pytest.fixture
def mock_client():
    """Создает мок для HTTP клиента."""
    client = AsyncMock()
    response = AsyncMock()
    response.status_code = 200
    response.json.return_value = {"success": True}
    client.request.return_value = response
    return client


@pytest.fixture
def api(mock_client):
    """Создает экземпляр API с моком клиента."""
    api = DMarketAPI(TEST_PUBLIC_KEY, TEST_SECRET_KEY)
    api._client = mock_client
    return api


@pytest.fixture
def balance_response():
    """Возвращает пример ответа на запрос баланса."""
    return {
        "usd": {
            "amount": 10000,  # 100 USD в центах
            "currency": "USD",
        },
        "has_funds": True,
        "available_balance": 100.0,
    }


@pytest.fixture
def market_items_response():
    """Возвращает пример ответа с предметами маркета."""
    return {
        "objects": [
            {
                "itemId": "item1",
                "title": "Test Item 1",
                "price": {
                    "USD": 1000,  # 10 USD в центах
                },
            },
            {
                "itemId": "item2",
                "title": "Test Item 2",
                "price": {
                    "USD": 2000,  # 20 USD в центах
                },
            },
        ],
        "total": 2,
    }


# Тесты основной функциональности API


@pytest.mark.asyncio
async def test_api_initialization():
    """Тестирует инициализацию API клиента."""
    api = DMarketAPI(TEST_PUBLIC_KEY, TEST_SECRET_KEY)
    assert api._public_key == TEST_PUBLIC_KEY
    assert api._secret_key == TEST_SECRET_KEY
    await api._close_client()  # Закрываем клиент после теста


@pytest.mark.asyncio
async def test_generate_headers(api):
    """Тестирует генерацию заголовков для запросов."""
    method = "GET"
    target = "/test"
    headers = api._generate_headers(method, target, "")
    assert "X-Api-Key" in headers
    assert "X-Request-Sign" in headers
    assert "X-Api-Key" in headers
    assert headers["X-Api-Key"] == TEST_PUBLIC_KEY


# Тесты для получения баланса


@pytest.mark.asyncio
async def test_get_user_balance(api, mock_client, balance_response):
    """Тестирует получение баланса пользователя."""
    # Устанавливаем мок-ответ
    response = AsyncMock()
    response.status_code = 200
    response.json.return_value = balance_response
    mock_client.request.return_value = response

    # Вызываем тестируемый метод
    result = await api.get_user_balance()

    # Проверяем результат
    assert result == balance_response
    assert mock_client.request.called
    args, kwargs = mock_client.request.call_args
    assert kwargs["method"] == "GET"
    assert "/account/v1/balance" in kwargs["url"]


@pytest.mark.asyncio
async def test_get_user_balance_error(api, mock_client):
    """Тестирует обработку ошибки при получении баланса."""
    # Устанавливаем мок-ответ с ошибкой
    response = AsyncMock()
    response.status_code = 401
    response.json.return_value = {"error": {"message": "Unauthorized"}}
    mock_client.request.return_value = response

    # Вызываем тестируемый метод
    with pytest.raises(Exception):
        await api.get_user_balance()


# Тесты для получения предметов с маркета


@pytest.mark.asyncio
async def test_get_market_items(api, mock_client, market_items_response):
    """Тестирует получение предметов с маркета."""
    # Устанавливаем мок-ответ
    response = AsyncMock()
    response.status_code = 200
    response.json.return_value = market_items_response
    mock_client.request.return_value = response

    # Вызываем тестируемый метод
    result = await api.get_market_items(game="csgo", limit=2)

    # Проверяем результат
    assert result == market_items_response
    assert mock_client.request.called
    args, kwargs = mock_client.request.call_args
    assert kwargs["method"] == "GET"
    assert "/exchange/v1/market/items" in kwargs["url"]
    assert "gameId=csgo" in kwargs["url"]
    assert "limit=2" in kwargs["url"]


# Тесты для обработки ошибок API


@pytest.mark.asyncio
async def test_handle_rate_limit(api, mock_client):
    """Тестирует обработку ограничения частоты запросов."""
    # Устанавливаем последовательность ответов: сначала 429, затем 200
    response_429 = AsyncMock()
    response_429.status_code = 429
    response_429.json.return_value = {"error": {"message": "Rate limit exceeded"}}

    response_200 = AsyncMock()
    response_200.status_code = 200
    response_200.json.return_value = {"success": True}

    mock_client.request.side_effect = [response_429, response_200]

    # Настраиваем API для повторных попыток
    api._max_retries = 1
    api._retry_delay = 0.1  # Уменьшаем задержку для ускорения теста

    # Вызываем метод, который должен обработать ограничение частоты запросов
    result = await api._request("GET", "/test", {})

    # Проверяем, что метод был вызван дважды и вернул успешный результат
    assert mock_client.request.call_count == 2
    assert result == {"success": True}


@pytest.mark.asyncio
async def test_api_timeout(api, mock_client):
    """Тестирует обработку тайм-аута API."""
    # Устанавливаем мок, который вызовет исключение тайм-аута
    mock_client.request.side_effect = asyncio.TimeoutError()

    # Настраиваем API для одной попытки
    api._max_retries = 0

    # Вызываем метод и проверяем, что он вызывает исключение
    with pytest.raises(asyncio.TimeoutError):
        await api._request("GET", "/test", {})


# Тесты для парсинга баланса


@pytest.mark.asyncio
async def test_parse_balance_format1(api):
    """Тестирует парсинг баланса в формате 1 (usdAvailableToWithdraw)."""
    balance_data = {
        "usdAvailableToWithdraw": "50.00",
        "usd": "$50.00",
    }

    result = await api.get_user_balance()

    # Используем патч для имитации ответа API
    with patch.object(api, "_request", return_value=balance_data):
        result = await api.get_user_balance()
        assert result["available_balance"] == 50.0
        assert result["has_funds"] == True
        assert result["usd"]["amount"] == 5000  # 50 USD в центах


@pytest.mark.asyncio
async def test_parse_balance_format2(api):
    """Тестирует парсинг баланса в формате 2 (USD)."""
    balance_data = {
        "USD": "25.00",
    }

    # Используем патч для имитации ответа API
    with patch.object(api, "_request", return_value=balance_data):
        result = await api.get_user_balance()
        assert result["available_balance"] == 25.0
        assert result["has_funds"] == True
        assert result["usd"]["amount"] == 2500  # 25 USD в центах


@pytest.mark.asyncio
async def test_parse_balance_empty(api):
    """Тестирует парсинг пустого ответа баланса."""
    balance_data = {}

    # Используем патч для имитации ответа API
    with patch.object(api, "_request", return_value=balance_data):
        result = await api.get_user_balance()
        assert result["available_balance"] == 0.0
        assert result["has_funds"] == False
