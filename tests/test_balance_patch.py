"""Тестирование патча эндпоинта баланса в DMarket API.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.dmarket.balance_patch import apply_balance_patch
from src.dmarket.dmarket_api_balance_fix import patched_get_user_balance


@pytest.mark.asyncio
async def test_patched_get_user_balance_string_usd():
    """Проверяет корректное преобразование строкового значения баланса"""
    # Создаем мок объекта DMarketAPI
    mock_api = AsyncMock()
    mock_api._request = AsyncMock(return_value={"usd": "15.50"})

    # Вызываем тестируемую функцию
    result = await patched_get_user_balance(mock_api)

    # Проверяем, что _request был вызван с правильными параметрами
    mock_api._request.assert_called_once_with("GET", "/v1/user/balance", params={})

    # Проверяем результат
    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 1550  # 15.50 * 100


@pytest.mark.asyncio
async def test_patched_get_user_balance_number_usd():
    """Проверяет корректное преобразование числового значения баланса"""
    # Создаем мок объекта DMarketAPI
    mock_api = AsyncMock()
    mock_api._request = AsyncMock(return_value={"usd": 10.25})

    # Вызываем тестируемую функцию
    result = await patched_get_user_balance(mock_api)

    # Проверяем, что _request был вызван с правильными параметрами
    mock_api._request.assert_called_once_with("GET", "/v1/user/balance", params={})

    # Проверяем результат
    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 1025  # 10.25 * 100


@pytest.mark.asyncio
async def test_patched_get_user_balance_correct_format():
    """Проверяет обработку данных, уже находящихся в правильном формате"""
    # Создаем мок объекта DMarketAPI
    mock_api = AsyncMock()
    mock_api._request = AsyncMock(return_value={"usd": {"amount": 2000}})

    # Вызываем тестируемую функцию
    result = await patched_get_user_balance(mock_api)

    # Проверяем, что _request был вызван с правильными параметрами
    mock_api._request.assert_called_once_with("GET", "/v1/user/balance", params={})

    # Проверяем результат
    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 2000


@pytest.mark.asyncio
async def test_patched_get_user_balance_fallback_endpoint():
    """Проверяет использование запасного эндпоинта при ошибке основного"""
    # Создаем мок объекта DMarketAPI
    mock_api = AsyncMock()

    # Настраиваем mock, чтобы первый вызов вызвал исключение
    mock_api._request = AsyncMock(
        side_effect=[
            Exception("API Error"),  # первый вызов вызывает исключение
            {"balance": {"usd": 3000}},  # второй вызов возвращает баланс в другом формате
        ]
    )

    # Вызываем тестируемую функцию
    result = await patched_get_user_balance(mock_api)

    # Проверяем, что _request был вызван дважды с разными параметрами
    assert mock_api._request.call_count == 2
    mock_api._request.assert_any_call("GET", "/v1/user/balance", params={})
    mock_api._request.assert_any_call("GET", "/account/v1/balance", params={})

    # Проверяем результат
    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 3000


@pytest.mark.asyncio
async def test_patched_get_user_balance_usdAvailableToWithdraw():
    """Проверяет обработку баланса в формате usdAvailableToWithdraw"""
    # Создаем мок объекта DMarketAPI
    mock_api = AsyncMock()
    mock_api._request = AsyncMock(return_value={"usdAvailableToWithdraw": "25.75"})

    # Вызываем тестируемую функцию
    result = await patched_get_user_balance(mock_api)

    # Проверяем, что _request был вызван с правильными параметрами
    mock_api._request.assert_called_once_with("GET", "/v1/user/balance", params={})

    # Проверяем результат
    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 2575  # 25.75 * 100


@pytest.mark.asyncio
async def test_patched_get_user_balance_invalid_response():
    """Проверяет возврат нулевого баланса при некорректном ответе"""
    # Создаем мок объекта DMarketAPI
    mock_api = AsyncMock()
    mock_api._request = AsyncMock(return_value={"invalid_key": "value"})

    # Вызываем тестируемую функцию
    result = await patched_get_user_balance(mock_api)

    # Проверяем, что _request был вызван с правильными параметрами
    mock_api._request.assert_called_once_with("GET", "/v1/user/balance", params={})

    # Проверяем результат
    assert "usd" in result
    assert "amount" in result["usd"]
    assert result["usd"]["amount"] == 0


@patch("src.dmarket.dmarket_api_balance_fix.logger")
@patch("src.dmarket.dmarket_api.DMarketAPI")
def test_apply_balance_patch(mock_dmarket_api, mock_logger):
    """Проверяет корректное применение патча к классу DMarketAPI"""
    # Вызываем тестируемую функцию
    result = apply_balance_patch()

    # Проверяем, что функция возвращает True
    assert result is True

    # Проверяем, что логгер вызывается с правильными сообщениями
    mock_logger.info.assert_any_call(
        "Применяем патч для исправления эндпоинта баланса в DMarketAPI"
    )
    mock_logger.info.assert_any_call("Патч успешно применен")

    # Проверяем, что метод get_user_balance был заменен
    assert mock_dmarket_api.get_user_balance == patched_get_user_balance
