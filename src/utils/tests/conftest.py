"""Конфигурация pytest для модуля utils.

Этот файл содержит фикстуры для тестирования модулей в директории src/utils.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_logger():
    """Создает мок объекта логгера для тестирования функций логирования и обработки ошибок."""
    logger = MagicMock(spec=logging.Logger)
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.critical = MagicMock()
    logger.exception = MagicMock()

    return logger


@pytest.fixture
def mock_http_response():
    """Создает мок HTTP ответа для тестирования функций обработки API ошибок."""
    response = MagicMock()
    response.status_code = 200
    response.json = MagicMock(return_value={"success": True, "data": {}})
    response.text = '{"success": true, "data": {}}'
    response.headers = {"Content-Type": "application/json"}

    return response


@pytest.fixture
def mock_http_error_response():
    """Создает мок HTTP ответа с ошибкой для тестирования обработки ошибок API."""
    response = MagicMock()
    response.status_code = 429
    response.json = MagicMock(return_value={"error": "Rate limit exceeded"})
    response.text = '{"error": "Rate limit exceeded"}'
    response.headers = {"Content-Type": "application/json", "Retry-After": "5"}

    return response


@pytest.fixture
def mock_async_client():
    """Создает мок для асинхронного HTTP клиента."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()

    return client


@pytest.fixture
def mock_api_error():
    """Создает экземпляр APIError для тестирования обработки ошибок."""
    from src.utils.api_error_handling import APIError

    return APIError(
        "Test API Error",
        status_code=400,
        response_data={"error": "Test error message", "code": "TEST_ERROR"},
    )


@pytest.fixture
def mock_rate_limiter():
    """Создает мок объекта RateLimiter для тестирования."""
    rate_limiter = MagicMock()
    rate_limiter.wait_if_needed = AsyncMock()
    rate_limiter.update_from_headers = MagicMock()
    rate_limiter.mark_rate_limited = MagicMock()
    rate_limiter.get_endpoint_type = MagicMock(return_value="market")

    return rate_limiter
