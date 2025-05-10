"""Упрощенные тесты для DMarket API.

Этот модуль содержит базовые тесты для проверки функциональности DMarket API,
фокусируясь на основных функциях и правильном обращении с API.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dmarket.dmarket_api import DMarketAPI


@pytest.fixture
def dmarket_api():
    """Создает экземпляр DMarketAPI для тестов с моками."""
    with patch("httpx.AsyncClient"):
        api = DMarketAPI(
            public_key="test_public_key",
            secret_key="test_secret_key",
            api_url="https://api.test.dmarket.com",
            max_retries=1,
            enable_cache=False,
        )
        # Заменяем httpx клиент на мок
        api._client = AsyncMock()
        return api


def test_dmarket_api_init():
    """Тест инициализации DMarketAPI с различными параметрами."""
    # Стандартная инициализация
    api = DMarketAPI("test_public_key", "test_secret_key")
    assert api.public_key == "test_public_key"
    assert api.secret_key == b"test_secret_key"
    assert api.api_url == "https://api.dmarket.com"
    assert api.max_retries == 3
    assert api.enable_cache is True

    # Кастомная инициализация
    api = DMarketAPI(
        "test_public_key",
        "test_secret_key",
        api_url="https://api.custom.com",
        max_retries=5,
        enable_cache=False,
    )
    assert api.public_key == "test_public_key"
    assert api.secret_key == b"test_secret_key"
    assert api.api_url == "https://api.custom.com"
    assert api.max_retries == 5
    assert api.enable_cache is False

    # Инициализация без ключей
    api = DMarketAPI("", "")
    assert api.public_key == ""
    assert api.secret_key == b""


@pytest.mark.asyncio
async def test_get_balance_success(dmarket_api):
    """Тест успешного получения баланса."""
    # Патчим внутренний метод _request, чтобы избежать реальных запросов
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        # Имитируем ответ API с балансом
        mock_request.return_value = {"usd": {"amount": 1550}}
        
        # Вызываем метод get_balance
        result = await dmarket_api.get_balance()
        
        # Проверяем, что метод _request был вызван с правильными параметрами
        mock_request.assert_called_once_with(
            "GET", "/account/v1/balance"
        )
        
        # Проверяем результат
        assert result["usd"]["amount"] == 1550
        assert result["balance"] == 15.50
        assert result["error"] is False
        assert result["has_funds"] is True


@pytest.mark.asyncio
async def test_get_balance_alternative_format(dmarket_api):
    """Тест получения баланса в альтернативном формате."""
    # Патчим внутренний метод _request
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        # Имитируем ответ API с балансом в формате usdAvailableToWithdraw
        mock_request.return_value = {"usdAvailableToWithdraw": "20.50"}
        
        # Вызываем метод get_balance
        result = await dmarket_api.get_balance()
        
        # Проверяем результат
        assert result["usd"]["amount"] == 2050
        assert result["balance"] == 20.50
        assert result["error"] is False
        assert result["has_funds"] is True


@pytest.mark.asyncio
async def test_get_balance_new_format(dmarket_api):
    """Тест получения баланса в новом формате с полями balance/available/total."""
    # Патчим внутренний метод _request
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        # Имитируем ответ API с балансом в новом формате
        mock_request.return_value = {"balance": 30.75, "available": 28.50, "total": 32.25}
        
        # Вызываем метод get_balance
        result = await dmarket_api.get_balance()
        
        # Проверяем результат
        assert result["balance"] == 30.75
        assert result["available_balance"] == 28.50
        assert result["total_balance"] == 32.25
        assert result["error"] is False
        assert result["has_funds"] is True


@pytest.mark.asyncio
async def test_get_balance_error(dmarket_api):
    """Тест получения баланса с ошибкой."""
    # Патчим внутренний метод _request
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        # Имитируем ответ API с ошибкой
        mock_request.return_value = {
            "error": True,
            "code": "UNAUTHORIZED",
            "message": "Invalid API key"
        }
        
        # Вызываем метод get_balance
        result = await dmarket_api.get_balance()
        
        # Проверяем результат
        assert result["error"] is True
        assert "error_message" in result
        assert result["balance"] == 0.0
        assert result["has_funds"] is False


@pytest.mark.asyncio
async def test_get_user_balance_deprecated(dmarket_api):
    """Тест устаревшего метода get_user_balance."""
    # Патчим метод get_balance и логгер
    with patch.object(dmarket_api, "get_balance", new=AsyncMock()) as mock_get_balance:
        with patch("src.dmarket.dmarket_api.logger") as mock_logger:
            # Настраиваем мок
            mock_get_balance.return_value = {"balance": 10.0}
            
            # Вызываем устаревший метод
            result = await dmarket_api.get_user_balance()
            
            # Проверяем, что был вызван новый метод
            mock_get_balance.assert_called_once()
            
            # Проверяем, что было выведено предупреждение
            mock_logger.warning.assert_called_once()
            assert "устарел" in mock_logger.warning.call_args[0][0]
            
            # Проверяем результат
            assert result == {"balance": 10.0}


@pytest.mark.asyncio
async def test_get_market_items(dmarket_api):
    """Тест получения предметов с рынка."""
    # Патчим внутренний метод _request
    with patch.object(dmarket_api, "_request", new=AsyncMock()) as mock_request:
        # Данные для ответа API
        test_items = [
            {"id": "item1", "title": "Test Item 1", "price": {"USD": 1000}},
            {"id": "item2", "title": "Test Item 2", "price": {"USD": 2000}},
        ]
        mock_request.return_value = {"items": test_items, "total": 2}
        
        # Вызываем метод
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
        
        # Проверяем параметры запроса
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert args[1] == "/exchange/v1/market/items"  # Используем прямой путь
        
        # Проверяем параметры запроса
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
    # Включаем кэширование
    dmarket_api.enable_cache = True
    
    # Патчим внутреннюю переменную api_cache
    with patch("src.dmarket.dmarket_api.api_cache", {"key1": ({"data": 1}, 1000000)}):
        # Очищаем кэш
        await dmarket_api.clear_cache()
        
        # Проверяем, что кэш пуст
        from src.dmarket.dmarket_api import api_cache
        assert len(api_cache) == 0 