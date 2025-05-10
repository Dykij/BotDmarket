"""Объединенные тесты для DMarket API.

Этот модуль содержит тесты для проверки:
1. Основной функциональности DMarket API
2. Получения баланса пользователя
3. Получения предметов с маркета
4. Работы с лимитами запросов
5. Обработки ошибок API
6. Интеграции с игровыми сервисами
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Импортируем необходимые модули для тестирования
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.dmarket.dmarket_api import DMarketAPI

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


@pytest.fixture
def inventory_items_response():
    """Возвращает пример ответа с предметами инвентаря."""
    return {
        "objects": [
            {
                "itemId": "inv_item1",
                "title": "Inventory Item 1",
                "price": {
                    "USD": 1500,  # 15 USD в центах
                },
                "status": "active",
            },
            {
                "itemId": "inv_item2",
                "title": "Inventory Item 2",
                "price": {
                    "USD": 2500,  # 25 USD в центах
                },
                "status": "active",
            },
        ],
        "total": 2,
    }


# Тесты основной функциональности API


@pytest.mark.asyncio
async def test_api_initialization():
    """Тестирует инициализацию API клиента."""
    api = DMarketAPI(TEST_PUBLIC_KEY, TEST_SECRET_KEY)
    assert api.public_key == TEST_PUBLIC_KEY
    assert api.secret_key == TEST_SECRET_KEY.encode("utf-8")
    await api._close_client()  # Закрываем клиент после теста


@pytest.mark.asyncio
async def test_generate_signature(api):
    """Тестирует генерацию заголовков для запросов."""
    method = "GET"
    path = "/test"
    headers = api._generate_signature(method, path, "")
    assert "X-Api-Key" in headers
    assert "X-Request-Sign" in headers
    assert headers["X-Api-Key"] == TEST_PUBLIC_KEY


# Тесты для получения баланса


@pytest.mark.asyncio
async def test_get_user_balance(api, balance_response):
    """Тестирует получение баланса пользователя."""
    # Патчим метод _request, чтобы он возвращал наш мок-ответ
    with patch.object(api, '_request', return_value=balance_response):
        # Вызываем тестируемый метод
        result = await api.get_user_balance()
        
        # Проверяем результат
        assert "available_balance" in result
        assert result["available_balance"] == balance_response["available_balance"]
        assert "has_funds" in result
        assert result["has_funds"] == balance_response["has_funds"]
        assert "usd" in result
        assert result["usd"]["amount"] == balance_response["usd"]["amount"]


@pytest.mark.asyncio
async def test_get_user_balance_error(api):
    """Тестирует обработку ошибки при получении баланса."""
    # Устанавливаем мок-ответ с ошибкой
    error_response = {"error": {"message": "Unauthorized"}}
    
    # Патчим метод _request, чтобы он вызывал исключение
    with patch.object(api, '_request', side_effect=Exception("Unauthorized")):
        # Вызываем тестируемый метод и проверяем, что он корректно обрабатывает ошибку
        result = await api.get_user_balance()
        assert result["error"] == True
        assert "error_message" in result


# Тесты для получения предметов с маркета


@pytest.mark.asyncio
async def test_get_market_items(api, market_items_response):
    """Тестирует получение предметов с маркета."""
    # Патчим метод _request, чтобы он возвращал наш мок-ответ
    with patch.object(api, '_request', return_value=market_items_response):
        # Вызываем тестируемый метод
        result = await api.get_market_items(game="csgo", limit=2)
        
        # Проверяем результат
        assert result == market_items_response
        assert "objects" in result
        assert len(result["objects"]) == 2
        assert result["total"] == 2


@pytest.mark.asyncio
async def test_get_market_items_with_filters(api, market_items_response):
    """Тестирует получение предметов с маркета с фильтрами."""
    # Патчим метод _request, чтобы он возвращал наш мок-ответ
    with patch.object(api, '_request', return_value=market_items_response):
        # Проверяем, что метод вызывается с правильными параметрами
        with patch.object(api, '_request', return_value=market_items_response) as mock_request:
            # Вызываем тестируемый метод с фильтрами
            result = await api.get_market_items(
                game="csgo", 
                limit=2, 
                price_from=5.0,  # От $5
                price_to=15.0,   # До $15
                title="AK-47",
            )
            
            # Проверяем результат
            assert result == market_items_response
            
            # Проверяем параметры вызова _request
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            assert args[0] == "GET"
            assert api.ENDPOINT_MARKET_ITEMS in args[1]
            assert kwargs["params"]["gameId"] == "csgo"
            assert kwargs["params"]["limit"] == 2
            assert kwargs["params"]["priceFrom"] == "500"  # 500 центов = $5
            assert kwargs["params"]["priceTo"] == "1500"  # 1500 центов = $15
            assert kwargs["params"]["title"] == "AK-47"


# Тесты для получения инвентаря пользователя


@pytest.mark.asyncio
async def test_get_user_inventory(api, inventory_items_response):
    """Тестирует получение инвентаря пользователя."""
    # Патчим метод _request, чтобы он возвращал наш мок-ответ
    with patch.object(api, '_request', return_value=inventory_items_response) as mock_request:
        # Вызываем тестируемый метод
        result = await api.get_user_inventory(game="csgo", limit=10)
        
        # Проверяем результат
        assert result == inventory_items_response
        
        # Проверяем параметры вызова _request
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert api.ENDPOINT_USER_INVENTORY in args[1]


# Тесты для операций покупки и продажи


@pytest.mark.asyncio
async def test_buy_item(api):
    """Тестирует покупку предмета."""
    # Мок-ответ на запрос покупки
    buy_response = {"result": {"status": "SUCCESS"}}
    
    # Создаем патч для функции get_market_items, чтобы она возвращала нужные данные
    market_items_mock = {
        "objects": [
            {
                "itemId": "test_item_id",
                "title": "Test Item",
                "price": {"USD": 1000},
            }
        ]
    }
    
    # Патчим метод _request, чтобы он возвращал наш мок-ответ
    with patch.object(api, 'get_market_items', return_value=market_items_mock), \
         patch.object(api, '_request', return_value=buy_response) as mock_request:
        # Вызываем тестируемый метод
        result = await api.buy_item(market_hash_name="Test Item", price=10.0)
        
        # Проверяем результат
        assert "result" in result
        assert result["result"]["status"] == "SUCCESS"
        
        # Проверяем параметры вызова _request
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert api.ENDPOINT_PURCHASE in args[1]


@pytest.mark.asyncio
async def test_sell_item(api):
    """Тестирует выставление предмета на продажу."""
    # Мок-ответ на запрос продажи
    sell_response = {"result": {"status": "SUCCESS"}}
    
    # Создаем патч для функции get_user_inventory, чтобы она возвращала нужные данные
    inventory_mock = {
        "objects": [
            {
                "itemId": "user_item_id",
                "title": "Inventory Item",
                "status": "active",
            }
        ]
    }
    
    # Патчим метод _request, чтобы он возвращал наш мок-ответ
    with patch.object(api, 'get_user_inventory', return_value=inventory_mock), \
         patch.object(api, '_request', return_value=sell_response) as mock_request:
        # Вызываем тестируемый метод
        result = await api.sell_item(item_id="user_item_id", price=15.0)
        
        # Проверяем результат
        assert "result" in result
        assert result["result"]["status"] == "SUCCESS"
        
        # Проверяем параметры вызова _request
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert api.ENDPOINT_SELL in args[1]


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
    api.max_retries = 1

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
    api.max_retries = 0

    # Вызываем метод и проверяем, что он вызывает исключение
    with pytest.raises(asyncio.TimeoutError):
        await api._request("GET", "/test", {})


@pytest.mark.asyncio
async def test_handle_server_error(api, mock_client):
    """Тестирует обработку ошибки сервера (5xx)."""
    # Устанавливаем последовательность ответов: сначала 503, затем 200
    response_503 = AsyncMock()
    response_503.status_code = 503
    response_503.json.return_value = {"error": {"message": "Service unavailable"}}

    response_200 = AsyncMock()
    response_200.status_code = 200
    response_200.json.return_value = {"success": True}

    mock_client.request.side_effect = [response_503, response_200]

    # Настраиваем API для повторных попыток
    api.max_retries = 1

    # Вызываем метод, который должен обработать ошибку сервера
    result = await api._request("GET", "/test", {})

    # Проверяем, что метод был вызван дважды и вернул успешный результат
    assert mock_client.request.call_count == 2
    assert result == {"success": True} 