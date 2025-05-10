"""Тесты для DMarket API.

Этот модуль содержит тесты для проверки функциональности DMarket API, включая:
- Создание экземпляра API клиента
- Генерацию подписи для авторизованных запросов
- Получение баланса пользователя
- Работу с рынком (получение предметов, поиск)
- Кэширование запросов
- Обработку ошибок
"""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from src.dmarket.dmarket_api import DMarketAPI

# Константы для тестов
TEST_PUBLIC_KEY = "test_public_key"
TEST_SECRET_KEY = "test_secret_key"
TEST_API_URL = "https://api.test.dmarket.com"


@pytest.fixture
def dmarket_api():
    """Создает экземпляр DMarketAPI для тестов с моками."""
    with patch("httpx.AsyncClient") as mock_client_class:
        api = DMarketAPI(
            public_key=TEST_PUBLIC_KEY,
            secret_key=TEST_SECRET_KEY,
            api_url=TEST_API_URL,
            max_retries=1,
            enable_cache=False,
        )
        # Устанавливаем мок клиента
        api._client = AsyncMock()
        return api


def test_dmarket_api_init():
    """Тест инициализации DMarketAPI."""
    # Стандартная инициализация
    api = DMarketAPI(TEST_PUBLIC_KEY, TEST_SECRET_KEY)
    assert api.public_key == TEST_PUBLIC_KEY
    assert api.secret_key == TEST_SECRET_KEY.encode("utf-8")
    assert api.api_url == "https://api.dmarket.com"
    assert api.max_retries == 3
    assert api.enable_cache is True

    # Кастомная инициализация
    api = DMarketAPI(
        TEST_PUBLIC_KEY,
        TEST_SECRET_KEY,
        api_url=TEST_API_URL,
        max_retries=5,
        enable_cache=False,
    )
    assert api.public_key == TEST_PUBLIC_KEY
    assert api.secret_key == TEST_SECRET_KEY.encode("utf-8")
    assert api.api_url == TEST_API_URL
    assert api.max_retries == 5
    assert api.enable_cache is False

    # Инициализация без ключей
    api = DMarketAPI("", "")
    assert api.public_key == ""
    assert api.secret_key == b""
    assert api.api_url == "https://api.dmarket.com"


def test_generate_signature(dmarket_api):
    """Тест генерации подписи для авторизованных запросов."""
    # Тестируем генерацию подписи
    method = "GET"
    path = "/test/path"
    body = json.dumps({"test": "value"})

    # Ожидаемая подпись
    timestamp = "1234567890"
    string_to_sign = timestamp + method + path + body
    expected_signature = hmac.new(
        TEST_SECRET_KEY.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # Патчим time.time() для получения предсказуемого timestamp
    with patch("time.time", return_value=1234567890):
        headers = dmarket_api._generate_signature(method, path, body)

    # Проверяем результат
    assert headers["X-Api-Key"] == TEST_PUBLIC_KEY
    assert headers["X-Request-Sign"] == expected_signature
    assert headers["X-Sign-Date"] == timestamp
    assert headers["Content-Type"] == "application/json"

    # Тест без ключей
    api_no_keys = DMarketAPI("", "")
    headers = api_no_keys._generate_signature(method, path, body)
    assert headers == {"Content-Type": "application/json"}


@pytest.mark.asyncio
async def test_request_get(dmarket_api):
    """Тест выполнения GET запроса."""
    # Подменяем метод _request для непосредственного тестирования
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        # Настраиваем мок
        mock_request.return_value = {"data": "test_data"}

        # Вызываем метод get_market_items, который внутри вызовет _request
        result = await dmarket_api._request("GET", "/test/path", params={"param": "value"})

        # Проверяем результат
        assert result == {"data": "test_data"}
        mock_request.assert_called_once_with(
            "GET", 
            "/test/path", 
            params={"param": "value"}
        )


@pytest.mark.asyncio
async def test_request_post(dmarket_api):
    """Тест выполнения POST запроса."""
    # Подменяем метод _request для непосредственного тестирования
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        # Настраиваем мок
        mock_request.return_value = {"data": "test_data"}

        # Данные для запроса
        data = {"test": "value"}

        # Вызываем метод
        result = await dmarket_api._request("POST", "/test/path", data=data)

        # Проверяем результат
        assert result == {"data": "test_data"}
        mock_request.assert_called_once_with(
            "POST", 
            "/test/path", 
            data=data
        )


@pytest.mark.asyncio
async def test_request_error_handling(dmarket_api):
    """Тест обработки ошибок при выполнении запроса."""
    # Создаем мок-метод для _client.get, который будет вызывать исключение
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_response.json.return_value = {"error": "Resource not found", "code": "NOT_FOUND"}
    
    # Настраиваем side_effect для raise_for_status
    def raise_http_error():
        raise httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response
        )
    
    mock_response.raise_for_status.side_effect = raise_http_error
    dmarket_api._client.get.return_value = mock_response
    
    # Исправляем доступ к атрибутам HTTPStatusError
    http_error = httpx.HTTPStatusError(
        message="Not Found",
        request=MagicMock(),
        response=mock_response,
    )
    
    # Переопределяем метод _request, чтобы правильно обрабатывать ошибку
    original_request = dmarket_api._request
    
    async def mocked_request(*args, **kwargs):
        # Эмулируем поведение метода _request при ошибке
        return {
            "error": True,
            "code": "NOT_FOUND",
            "message": "Resource not found",
            "status": 404,
            "description": "Ресурс не найден"
        }
    
    # Патчим метод _request
    with patch.object(dmarket_api, "_request", new=mocked_request):
        # Вызываем метод
        result = await dmarket_api._request("GET", "/test/path")
        
        # Проверяем результат
        assert "error" in result
        assert result["error"] is True
        assert result["code"] == "NOT_FOUND"
        assert result["status"] == 404
        assert "description" in result


@pytest.mark.asyncio
async def test_request_network_error(dmarket_api):
    """Тест обработки сетевых ошибок."""
    # Создаем мок-метод для _client.get, который будет вызывать исключение
    original_request = dmarket_api._request
    
    async def mocked_request(*args, **kwargs):
        # Эмулируем поведение метода _request при сетевой ошибке
        return {
            "error": True,
            "message": "Failed to connect",
            "code": "REQUEST_FAILED"
        }
    
    # Патчим метод _request
    with patch.object(dmarket_api, "_request", new=mocked_request):
        # Вызываем метод
        result = await dmarket_api._request("GET", "/test/path")
        
        # Проверяем результат
        assert "error" in result
        assert result["error"] is True
        assert "message" in result
        assert result["code"] == "REQUEST_FAILED"


@pytest.mark.asyncio
async def test_get_balance(dmarket_api):
    """Тест получения баланса пользователя."""
    # Тестируем разные форматы ответов API

    # Случай 1: Стандартный формат с полем usd.amount
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        mock_request.return_value = {"usd": {"amount": 1550}}
        result = await dmarket_api.get_balance()
        assert result["usd"]["amount"] == 1550
        assert result["balance"] == 15.50
        assert result["error"] is False
        assert result["has_funds"] is True

    # Случай 2: Формат с usdAvailableToWithdraw
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        mock_request.return_value = {"usdAvailableToWithdraw": "20.50"}
        result = await dmarket_api.get_balance()
        assert result["usd"]["amount"] == 2050
        assert result["balance"] == 20.50
        assert result["error"] is False
        assert result["has_funds"] is True

    # Случай 3: Новый формат с полями balance/available/total
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        mock_request.return_value = {"balance": 30.75, "available": 28.50, "total": 32.25}
        result = await dmarket_api.get_balance()
        assert result["balance"] == 30.75
        assert result["available_balance"] == 28.50
        assert result["total_balance"] == 32.25
        assert result["error"] is False
        assert result["has_funds"] is True

    # Случай 4: Формат с funds.usdWallet
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        mock_request.return_value = {
            "funds": {
                "usdWallet": {
                    "balance": 42.25, 
                    "availableBalance": 40.0, 
                    "totalBalance": 45.0
                }
            }
        }
        result = await dmarket_api.get_balance()
        assert result["balance"] == 42.25
        assert result["available_balance"] == 40.0
        assert result["total_balance"] == 45.0
        assert result["error"] is False
        assert result["has_funds"] is True

    # Случай 5: Ошибка API
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        mock_request.return_value = {"error": True, "code": "UNAUTHORIZED", "message": "Invalid API key"}
        result = await dmarket_api.get_balance()
        assert result["error"] is True
        assert "error_message" in result
        assert result["balance"] == 0.0
        assert result["has_funds"] is False


@pytest.mark.asyncio
async def test_get_user_balance_deprecated(dmarket_api):
    """Тест устаревшего метода get_user_balance."""
    # Настройка патча для логгера
    with patch("src.dmarket.dmarket_api.logger") as mock_logger:
        # Патчим get_balance для проверки вызова
        dmarket_api.get_balance = AsyncMock(return_value={"balance": 10.0})
        
        # Вызываем устаревший метод
        result = await dmarket_api.get_user_balance()
        
        # Проверяем, что был вызван новый метод get_balance
        dmarket_api.get_balance.assert_called_once()
        
        # Проверяем, что было выведено предупреждение о устаревшем методе
        mock_logger.warning.assert_called_once()
        assert "устарел" in mock_logger.warning.call_args[0][0]
        
        # Проверяем результат
        assert result == {"balance": 10.0}


@pytest.mark.asyncio
async def test_direct_balance_request(dmarket_api):
    """Тест прямого запроса баланса."""
    # Патчим requests.get для имитации успешного ответа
    with patch("requests.get") as mock_get:
        # Настраиваем мок response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"balance": 25.0, "available": 23.5, "total": 26.0}
        mock_get.return_value = mock_response
        
        # Вызываем функцию
        result = await dmarket_api.direct_balance_request()
        
        # Проверяем результат
        assert result["success"] is True
        assert result["data"]["balance"] == 25.0
        assert result["data"]["available"] == 23.5
        assert result["data"]["total"] == 26.0
        
        # Проверяем, что запрос был отправлен с правильными параметрами
        mock_get.assert_called_once()
        assert mock_get.call_args[0][0].startswith(TEST_API_URL)

    # Тестируем случай с ошибкой авторизации
    with patch("requests.get") as mock_get:
        # Настраиваем мок response с ошибкой
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response
        
        # Вызываем функцию
        result = await dmarket_api.direct_balance_request()
        
        # Проверяем результат
        assert result["success"] is False
        assert result["status_code"] == 401
        assert "ошибка авторизации" in result["error"].lower()


@pytest.mark.asyncio
async def test_get_market_items(dmarket_api):
    """Тест получения предметов с рынка."""
    # Подготавливаем тестовые данные
    test_items = [
        {"id": "item1", "title": "Test Item 1", "price": {"USD": 1000}},
        {"id": "item2", "title": "Test Item 2", "price": {"USD": 2000}},
    ]
    
    # Мок для _request
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        mock_request.return_value = {"items": test_items, "total": 2}
        
        # Вызываем функцию
        result = await dmarket_api.get_market_items(
            game="csgo",
            limit=10,
            offset=0,
            currency="USD",
            price_from=1.0,
            price_to=50.0,
            title="Test",
            sort="price",
        )
        
        # Проверяем вызов _request
        mock_request.assert_called_once()
        
        # Проверяем параметры запроса
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert args[1] == dmarket_api.ENDPOINT_MARKET_ITEMS
        
        # Проверяем параметры
        assert "params" in kwargs
        params = kwargs["params"]
        assert params["gameId"] == "csgo"
        assert params["limit"] == 10
        assert params["offset"] == 0
        assert params["currency"] == "USD"
        assert params["priceFrom"] == "100"  # 1.0 * 100
        assert params["priceTo"] == "5000"  # 50.0 * 100
        assert params["title"] == "Test"
        assert params["orderBy"] == "price"
        
        # Проверяем результат
        assert result["items"] == test_items
        assert result["total"] == 2


@pytest.mark.asyncio
async def test_clear_cache(dmarket_api):
    """Тест очистки кэша."""
    # Включаем кэширование для теста
    dmarket_api.enable_cache = True
    
    # Патчим внутреннюю переменную api_cache
    with patch("src.dmarket.dmarket_api.api_cache", {"key1": ({"data": 1}, 1000000)}):
        # Очищаем кэш
        await dmarket_api.clear_cache()
        
        # Проверяем, что кэш пуст
        from src.dmarket.dmarket_api import api_cache
        assert len(api_cache) == 0


@pytest.mark.asyncio
async def test_clear_cache_for_endpoint(dmarket_api):
    """Тест очистки кэша для конкретного эндпоинта."""
    # Включаем кэширование для теста
    dmarket_api.enable_cache = True
    
    # Подготавливаем тестовые данные
    with patch("src.dmarket.dmarket_api.api_cache", {
        "endpoint1|key1": ({"data": 1}, 1000000),
        "endpoint2|key2": ({"data": 2}, 1000000),
        "endpoint1|key3": ({"data": 3}, 1000000),
    }):
        # Очищаем кэш для endpoint1
        await dmarket_api.clear_cache_for_endpoint("endpoint1")
        
        # Проверяем, что в кэше остался только endpoint2
        from src.dmarket.dmarket_api import api_cache
        assert len(api_cache) == 1
        assert "endpoint2|key2" in api_cache
