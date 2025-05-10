"""Тесты для модуля api_error_handling.py.

Этот модуль тестирует функциональность обработки ошибок API.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponse

from src.utils.api_error_handling import (
    APIError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    RateLimitExceeded,
    ServerError,
    handle_response,
    retry_request,
)


def test_api_error_init():
    """Тестирует инициализацию базового класса APIError."""
    # Базовый случай
    error = APIError("Test error")
    assert error.message == "Test error"
    assert error.status_code == 0
    assert error.response_data == {}

    # С дополнительными параметрами
    error = APIError("Test error", 400, {"error": "Bad request"})
    assert error.message == "Test error"
    assert error.status_code == 400
    assert error.response_data == {"error": "Bad request"}

    # Проверка строкового представления
    assert str(error) == "Test error (Статус: 400)"


def test_specialized_errors():
    """Тестирует специализированные классы ошибок."""
    # AuthenticationError
    auth_error = AuthenticationError("Auth failed", 401, {"error": "Unauthorized"})
    assert isinstance(auth_error, APIError)
    assert auth_error.status_code == 401

    # NotFoundError
    not_found_error = NotFoundError("Not found", 404, {"error": "Resource not found"})
    assert isinstance(not_found_error, APIError)
    assert not_found_error.status_code == 404

    # RateLimitExceeded
    rate_limit_error = RateLimitExceeded(
        "Rate limit exceeded",
        429,
        {"error": "Too many requests"},
        retry_after=30,
    )
    assert isinstance(rate_limit_error, APIError)
    assert rate_limit_error.status_code == 429
    assert rate_limit_error.retry_after == 30

    # ServerError
    server_error = ServerError("Server error", 500, {"error": "Internal server error"})
    assert isinstance(server_error, APIError)
    assert server_error.status_code == 500

    # BadRequestError
    bad_request_error = BadRequestError(
        "Bad request",
        400,
        {"error": "Invalid parameters"},
    )
    assert isinstance(bad_request_error, APIError)
    assert bad_request_error.status_code == 400


@pytest.mark.asyncio
async def test_handle_response_success():
    """Тестирует обработку успешного ответа API."""
    # Создаем мок успешного ответа
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"data": "test data"})

    # Вызываем функцию
    result = await handle_response(mock_response)

    # Проверяем результат
    assert result == {"data": "test data"}
    mock_response.json.assert_called_once()


@pytest.mark.asyncio
async def test_handle_response_auth_error():
    """Тестирует обработку ошибки авторизации (401)."""
    # Создаем мок ответа с ошибкой авторизации
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = 401
    mock_response.json = AsyncMock(return_value={"error": "Unauthorized"})

    # Проверяем, что вызывается исключение AuthenticationError
    with pytest.raises(AuthenticationError) as exc_info:
        await handle_response(mock_response)

    # Проверяем детали исключения
    assert exc_info.value.status_code == 401
    assert "авторизации" in exc_info.value.message


@pytest.mark.asyncio
async def test_handle_response_not_found():
    """Тестирует обработку ошибки "не найдено" (404)."""
    # Создаем мок ответа с ошибкой "не найдено"
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = 404
    mock_response.json = AsyncMock(return_value={"error": "Not found"})

    # Проверяем, что вызывается исключение NotFoundError
    with pytest.raises(NotFoundError) as exc_info:
        await handle_response(mock_response)

    # Проверяем детали исключения
    assert exc_info.value.status_code == 404
    assert "не найден" in exc_info.value.message


@pytest.mark.asyncio
async def test_handle_response_rate_limit():
    """Тестирует обработку ошибки превышения лимита запросов (429)."""
    # Создаем мок ответа с ошибкой превышения лимита
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = 429
    mock_response.json = AsyncMock(return_value={"error": "Rate limit exceeded"})
    mock_response.headers = {"Retry-After": "30"}

    # Проверяем, что вызывается исключение RateLimitExceeded
    with pytest.raises(RateLimitExceeded) as exc_info:
        await handle_response(mock_response)

    # Проверяем детали исключения
    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after == 30
    assert "Превышен лимит запросов" in exc_info.value.message


@pytest.mark.asyncio
async def test_handle_response_server_error():
    """Тестирует обработку серверной ошибки (5xx)."""
    # Создаем мок ответа с серверной ошибкой
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = 500
    mock_response.json = AsyncMock(return_value={"error": "Internal server error"})

    # Проверяем, что вызывается исключение ServerError
    with pytest.raises(ServerError) as exc_info:
        await handle_response(mock_response)

    # Проверяем детали исключения
    assert exc_info.value.status_code == 500
    assert "Серверная ошибка" in exc_info.value.message


@pytest.mark.asyncio
async def test_handle_response_bad_request():
    """Тестирует обработку ошибки неверного запроса (400)."""
    # Создаем мок ответа с ошибкой неверного запроса
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = 400
    mock_response.json = AsyncMock(return_value={"error": "Bad request"})

    # Проверяем, что вызывается исключение BadRequestError
    with pytest.raises(BadRequestError) as exc_info:
        await handle_response(mock_response)

    # Проверяем детали исключения
    assert exc_info.value.status_code == 400
    assert "Неверный запрос" in exc_info.value.message


@pytest.mark.asyncio
async def test_handle_response_unknown_error():
    """Тестирует обработку неизвестной ошибки."""
    # Создаем мок ответа с неизвестной ошибкой
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = 418  # I'm a teapot
    mock_response.json = AsyncMock(return_value={"error": "I'm a teapot"})

    # Проверяем, что вызывается базовое исключение APIError
    with pytest.raises(APIError) as exc_info:
        await handle_response(mock_response)

    # Проверяем детали исключения
    assert exc_info.value.status_code == 418
    assert "Ошибка API" in exc_info.value.message


@pytest.mark.asyncio
async def test_handle_response_json_error():
    """Тестирует обработку ошибки при разборе JSON ответа."""
    # Создаем мок ответа с ошибкой при разборе JSON
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = 200
    mock_response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))

    # Вызываем функцию и проверяем, что она обрабатывает ошибку
    result = await handle_response(mock_response)

    # Проверяем, что результат - пустой словарь
    assert result == {}


@pytest.mark.asyncio
async def test_retry_request_success():
    """Тестирует успешное выполнение запроса с помощью retry_request."""
    # Создаем мок функции запроса
    mock_request_func = AsyncMock(return_value={"data": "test data"})

    # Создаем мок лимитера
    mock_limiter = MagicMock()
    mock_limiter.wait_for_call = AsyncMock()
    mock_limiter.update_after_call = MagicMock()

    # Вызываем функцию
    result = await retry_request(
        request_func=mock_request_func,
        limiter=mock_limiter,
        endpoint_type="market",
        max_retries=3,
        param1="value1",
        param2="value2",
    )

    # Проверяем результат
    assert result == {"data": "test data"}
    mock_limiter.wait_for_call.assert_called_once_with("market")
    mock_limiter.update_after_call.assert_called_once_with("market")
    mock_request_func.assert_called_once_with(param1="value1", param2="value2")


@pytest.mark.asyncio
async def test_retry_request_with_retry():
    """Тестирует повторные попытки запроса при временных ошибках."""
    # Создаем мок функции запроса, которая сначала вызывает ошибку, а затем возвращает данные
    mock_request_func = AsyncMock(
        side_effect=[
            APIError("First attempt failed", 500),
            {"data": "test data"},
        ],
    )

    # Создаем мок лимитера
    mock_limiter = MagicMock()
    mock_limiter.wait_for_call = AsyncMock()
    mock_limiter.update_after_call = MagicMock()

    # Заменяем функцию sleep, чтобы тест не ждал
    with patch("asyncio.sleep", AsyncMock()):
        # Вызываем функцию
        result = await retry_request(
            request_func=mock_request_func,
            limiter=mock_limiter,
            endpoint_type="market",
            max_retries=3,
        )

    # Проверяем результат
    assert result == {"data": "test data"}
    assert mock_request_func.call_count == 2
    assert mock_limiter.wait_for_call.call_count == 2
    assert mock_limiter.update_after_call.call_count == 1


@pytest.mark.asyncio
async def test_retry_request_rate_limit():
    """Тестирует обработку ошибки превышения лимита запросов."""
    # Создаем исключение RateLimitExceeded
    rate_limit_error = RateLimitExceeded(
        "Rate limit exceeded",
        429,
        {"error": "Too many requests"},
        retry_after=5,
    )

    # Создаем мок функции запроса, которая всегда вызывает ошибку превышения лимита
    mock_request_func = AsyncMock(side_effect=rate_limit_error)

    # Создаем мок лимитера
    mock_limiter = MagicMock()
    mock_limiter.wait_for_call = AsyncMock()
    mock_limiter.mark_rate_limited = MagicMock()

    # Заменяем функцию sleep, чтобы тест не ждал
    with patch("asyncio.sleep", AsyncMock()):
        # Проверяем, что после нескольких попыток функция выбрасывает исключение
        with pytest.raises(RateLimitExceeded) as exc_info:
            await retry_request(
                request_func=mock_request_func,
                limiter=mock_limiter,
                endpoint_type="market",
                max_retries=2,
            )

    # Проверяем детали вызовов
    assert mock_request_func.call_count == 3  # Начальная попытка + 2 повтора
    assert mock_limiter.wait_for_call.call_count == 3
    assert mock_limiter.mark_rate_limited.call_count == 3
    assert exc_info.value.retry_after == 5


@pytest.mark.asyncio
async def test_retry_request_max_retries_exceeded():
    """Тестирует поведение, когда превышено максимальное количество повторов."""
    # Создаем мок функции запроса, которая всегда вызывает ошибку
    mock_request_func = AsyncMock(side_effect=APIError("Server error", 500))

    # Создаем мок лимитера
    mock_limiter = MagicMock()
    mock_limiter.wait_for_call = AsyncMock()

    # Заменяем функцию sleep, чтобы тест не ждал
    with patch("asyncio.sleep", AsyncMock()):
        # Проверяем, что после нескольких попыток функция выбрасывает исключение
        with pytest.raises(APIError) as exc_info:
            await retry_request(
                request_func=mock_request_func,
                limiter=mock_limiter,
                endpoint_type="market",
                max_retries=2,
            )

    # Проверяем детали исключения
    assert "Ошибка после 3 попыток" in exc_info.value.message
    assert mock_request_func.call_count == 3  # Начальная попытка + 2 повтора
