"""
Тесты для проверки функциональности модуля api_error_handling.
"""

import pytest
import aiohttp
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.utils.api_error_handling import (
    APIError, 
    handle_response, 
    retry_request
)
from src.utils.rate_limiter import RateLimiter


@pytest.fixture
def rate_limiter():
    """Фикстура для создания экземпляра RateLimiter."""
    return RateLimiter(is_authorized=True)


def test_api_error_creation():
    """Тест создания экземпляра APIError."""
    error = APIError("Тестовая ошибка", 429, {"error": "Rate limited"})
    
    assert error.message == "Тестовая ошибка"
    assert error.status_code == 429
    assert error.response_data == {"error": "Rate limited"}
    assert str(error) == "Тестовая ошибка (Статус: 429)"


@pytest.mark.asyncio
async def test_handle_response_success():
    """Тест обработки успешного ответа."""
    # Создаем мок успешного ответа
    response = AsyncMock()
    response.status = 200
    response.json.return_value = {"success": True, "data": "test"}
    
    # Вызываем функцию обработки ответа
    result = await handle_response(response)
    
    # Проверяем результат
    assert result == {"success": True, "data": "test"}
    assert response.json.called


@pytest.mark.asyncio
async def test_handle_response_error():
    """Тест обработки ошибочного ответа."""
    # Создаем мок ответа с ошибкой
    response = AsyncMock()
    response.status = 429
    response.json.return_value = {"error": "Rate limited"}
    response.headers = {"Retry-After": "30"}
    
    # Проверяем, что вызывается исключение с правильным сообщением
    with pytest.raises(APIError) as excinfo:
        await handle_response(response)
    
    # Проверяем атрибуты исключения
    assert excinfo.value.status_code == 429
    assert "Rate limited" in str(excinfo.value.response_data)
    assert hasattr(excinfo.value, "retry_after")
    assert excinfo.value.retry_after == 30


@pytest.mark.asyncio
async def test_retry_request_success():
    """Тест успешного выполнения запроса с первого раза."""
    # Создаем мок функции и лимитера
    mock_func = AsyncMock(return_value={"success": True})
    mock_limiter = MagicMock(spec=RateLimiter)
    mock_limiter.wait_for_call = AsyncMock()
    mock_limiter.update_after_call = MagicMock()
    
    # Вызываем функцию retry_request
    result = await retry_request(
        request_func=mock_func,
        limiter=mock_limiter,
        endpoint_type="market",
        max_retries=3
    )
    
    # Проверяем результат и вызовы
    assert result == {"success": True}
    assert mock_func.call_count == 1
    assert mock_limiter.wait_for_call.call_count == 1
    assert mock_limiter.update_after_call.call_count == 1


@pytest.mark.asyncio
async def test_retry_request_with_retry():
    """Тест выполнения запроса с повторными попытками."""
    # Создаем счетчик попыток
    attempt_counter = {'count': 0}
    
    # Создаем функцию, которая сначала вызывает исключение, а потом успешно возвращает результат
    async def mock_func_with_retry():
        attempt_counter['count'] += 1
        if attempt_counter['count'] < 2:
            raise aiohttp.ClientResponseError(
                status=500,
                message="Server Error",
                request_info=MagicMock(),
                history=()
            )
        return {"success": True, "attempt": attempt_counter['count']}
    
    # Создаем мок лимитера
    mock_limiter = MagicMock(spec=RateLimiter)
    mock_limiter.wait_for_call = AsyncMock()
    mock_limiter.update_after_call = MagicMock()
    
    # Вызываем функцию retry_request
    result = await retry_request(
        request_func=mock_func_with_retry,
        limiter=mock_limiter,
        endpoint_type="market",
        max_retries=3
    )
    
    # Проверяем результат и число попыток
    assert result == {"success": True, "attempt": 2}
    assert attempt_counter['count'] == 2
    assert mock_limiter.wait_for_call.call_count == 2


@pytest.mark.asyncio
async def test_retry_request_max_retries_exceeded():
    """Тест превышения максимального числа попыток."""
    # Создаем функцию, которая всегда вызывает исключение
    async def failing_func():
        raise aiohttp.ClientResponseError(
            status=500,
            message="Server Error",
            request_info=MagicMock(),
            history=()
        )
    
    # Создаем мок лимитера
    mock_limiter = MagicMock(spec=RateLimiter)
    mock_limiter.wait_for_call = AsyncMock()
    mock_limiter.update_after_call = MagicMock()
    
    # Проверяем, что после исчерпания попыток вызывается исключение
    with pytest.raises(APIError) as excinfo:
        await retry_request(
            request_func=failing_func,
            limiter=mock_limiter,
            endpoint_type="market",
            max_retries=2
        )
    
    # Проверяем атрибуты исключения
    assert excinfo.value.status_code == 500
    assert "Server Error" in str(excinfo.value)
    assert mock_limiter.wait_for_call.call_count == 3  # 1 оригинальная попытка + 2 повторные


@pytest.mark.asyncio
async def test_retry_request_rate_limit():
    """Тест обработки ошибки превышения лимита запросов."""
    # Создаем функцию, вызывающую ошибку превышения лимита
    async def rate_limited_func():
        response = AsyncMock()
        response.status = 429
        response.json.return_value = {"error": "Rate limited"}
        response.headers = {"Retry-After": "2"}
        raise aiohttp.ClientResponseError(
            status=429,
            message="Rate limit exceeded",
            request_info=MagicMock(),
            history=(),
            headers={"Retry-After": "2"}
        )
    
    # Создаем мок лимитера
    mock_limiter = MagicMock(spec=RateLimiter)
    mock_limiter.wait_for_call = AsyncMock()
    mock_limiter.update_after_call = MagicMock()
    mock_limiter.mark_rate_limited = MagicMock()
    
    # Проверяем, что после исчерпания попыток вызывается исключение
    with pytest.raises(APIError) as excinfo:
        # Устанавливаем короткий max_retries для быстрого выполнения теста
        await retry_request(
            request_func=rate_limited_func,
            limiter=mock_limiter,
            endpoint_type="market",
            max_retries=1
        )
    
    # Проверяем атрибуты исключения
    assert excinfo.value.status_code == 429
    assert "Rate limit exceeded" in str(excinfo.value)
    # Проверяем, что был вызван метод mark_rate_limited
    assert mock_limiter.mark_rate_limited.called
