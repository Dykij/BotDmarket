"""
Тесты для модуля dmarket_api_balance.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.dmarket.dmarket_api_balance import get_user_balance


class MockDMarketAPI:
    """Мок класса DMarketAPI для тестирования функции get_user_balance."""

    def __init__(self, response=None, exception=None):
        self._response = response
        self._exception = exception
        self._request = AsyncMock()
        if self._exception:
            self._request.side_effect = self._exception
        else:
            self._request.return_value = self._response


@pytest.mark.asyncio
async def test_get_user_balance_success():
    """Тест успешного получения баланса."""
    # Настройка мока с успешным ответом API
    api = MockDMarketAPI(response={"usd": "50.00"})

    # Вызываем тестируемую функцию
    result = await get_user_balance(api)

    # Проверки
    api._request.assert_called_once_with(
        "GET",
        "/v1/user/balance",
        params={}
    )

    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 5000.0  # 50.00 USD в центах


@pytest.mark.asyncio
async def test_get_user_balance_error():
    """Тест обработки ошибки API при получении баланса."""
    # Настройка мока с ответом, содержащим ошибку
    error_response = {
        "error": "Unauthorized",
        "details": json.dumps({"code": "InvalidToken", "message": "Token is invalid"})
    }
    api = MockDMarketAPI(response=error_response)

    # Вызываем тестируемую функцию
    result = await get_user_balance(api)

    # Проверки
    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 0  # При ошибке должен вернуться нулевой баланс


@pytest.mark.asyncio
async def test_get_user_balance_old_endpoint_fallback():
    """Тест использования старого эндпоинта в качестве запасного варианта."""
    # Настройка мока, который вызовет исключение при первом запросе
    api = MockDMarketAPI(exception=Exception("Endpoint not found"))

    # Подменяем метод _request, чтобы второй вызов вернул корректный ответ
    async def mock_request(method, endpoint, params):
        if endpoint == "/v1/user/balance":
            raise Exception("Endpoint not found")
        elif endpoint == "/account/v1/balance":
            return {"balance": {"usd": 3000}}
        return {}

    api._request = AsyncMock(side_effect=mock_request)

    # Вызываем тестируемую функцию
    result = await get_user_balance(api)

    # Проверки
    assert api._request.call_count == 2  # Проверяем, что было два вызова API
    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 3000  # 30 USD в центах


@pytest.mark.asyncio
async def test_get_user_balance_usd_number_format():
    """Тест обработки баланса в числовом формате."""
    # Настройка мока с балансом в числовом формате
    api = MockDMarketAPI(response={"usd": 25.50})

    # Вызываем тестируемую функцию
    result = await get_user_balance(api)

    # Проверки
    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 2550.0  # 25.50 USD в центах


@pytest.mark.asyncio
async def test_get_user_balance_correct_format():
    """Тест получения баланса в правильном формате."""
    # Настройка мока с уже корректным форматом ответа
    api = MockDMarketAPI(response={"usd": {"amount": 7500}})

    # Вызываем тестируемую функцию
    result = await get_user_balance(api)

    # Проверки
    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 7500  # 75 USD в центах


@pytest.mark.asyncio
async def test_get_user_balance_usdAvailableToWithdraw():
    """Тест обработки баланса из поля usdAvailableToWithdraw."""
    # Настройка мока с балансом в поле usdAvailableToWithdraw
    api = MockDMarketAPI(response={"usdAvailableToWithdraw": "100.00"})

    # Вызываем тестируемую функцию
    result = await get_user_balance(api)

    # Проверки
    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 10000.0  # 100.00 USD в центах


@pytest.mark.asyncio
async def test_get_user_balance_unauthorized():
    """Тест обработки ошибки авторизации."""
    # Настройка мока с ошибкой авторизации
    api = MockDMarketAPI(response={"code": "Unauthorized", "message": "Access denied"})

    # Вызываем тестируемую функцию
    result = await get_user_balance(api)

    # Проверки
    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 0  # При ошибке должен вернуться нулевой баланс
