"""
Тесты для модулей логирования и обработки ошибок.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock

from src.utils.exception_handling import (
    BaseAppException, APIError, ValidationError, BusinessLogicError,
    handle_exceptions, ErrorCode
)
from src.utils.logging_utils import get_logger, log_exceptions


@pytest.fixture
def mock_logger():
    """Создает мок объекта логгера для тестирования."""
    logger = MagicMock(spec=logging.Logger)
    return logger


def test_base_app_exception():
    """Тестирует базовый класс исключения."""
    # Создаем экземпляр исключения
    exception = BaseAppException(
        message="Test error",
        code=ErrorCode.BUSINESS_LOGIC_ERROR,
        details={"test_key": "test_value"}
    )

    # Проверяем атрибуты
    assert exception.message == "Test error"
    assert exception.code == ErrorCode.BUSINESS_LOGIC_ERROR.value
    assert "test_key" in exception.details
    assert exception.details["test_key"] == "test_value"

    # Проверяем to_dict
    result_dict = exception.to_dict()
    assert result_dict["code"] == ErrorCode.BUSINESS_LOGIC_ERROR.value
    assert result_dict["message"] == "Test error"
    assert "details" in result_dict
    assert result_dict["details"]["test_key"] == "test_value"


def test_api_error():
    """Тестирует класс исключения для API."""
    # Создаем экземпляр исключения
    exception = APIError(
        message="API error",
        status_code=429,
        details={"endpoint": "/items"},
        response_body='{"error": "Rate limit exceeded"}'
    )

    # Проверяем специфичные атрибуты
    assert exception.status_code == 429
    assert "status_code" in exception.details
    assert "response_body" in exception.details


def test_validation_error():
    """Тестирует класс исключения для ошибок валидации."""
    # Создаем экземпляр исключения
    exception = ValidationError(
        message="Invalid value",
        field="price",
        details={"min_value": 0, "max_value": 100}
    )

    # Проверяем специфичные атрибуты
    assert "field" in exception.details
    assert exception.details["field"] == "price"


def test_business_logic_error():
    """Тестирует класс исключения для ошибок бизнес-логики."""
    # Создаем экземпляр исключения
    exception = BusinessLogicError(
        message="Operation not allowed",
        operation="purchase_item",
        details={"reason": "insufficient_funds"}
    )

    # Проверяем специфичные атрибуты
    assert "operation" in exception.details
    assert exception.details["operation"] == "purchase_item"


def test_handle_exceptions_decorator(mock_logger):
    """Тестирует декоратор обработки исключений."""
    # Создаем функцию с декоратором
    @handle_exceptions(logger=mock_logger, default_error_message="Test error occurred")
    def failing_function():
        raise APIError("API failure", status_code=500)

    # Вызываем функцию и проверяем, что исключение перехватывается
    try:
        failing_function()
    except APIError:
        # Исключение должно быть перевыброшено по умолчанию
        pass

    # Проверяем, что логирование было вызвано
    mock_logger.error.assert_called_once()
    args, kwargs = mock_logger.error.call_args
    assert "Test error occurred" in args[0]
    assert "context" in kwargs["extra"]


def test_handle_exceptions_no_reraise(mock_logger):
    """Тестирует декоратор обработки исключений без перевыброса."""
    # Создаем функцию с декоратором
    @handle_exceptions(logger=mock_logger, reraise=False)
    def failing_function():
        raise ValidationError("Validation error", field="price")

    # Вызываем функцию - исключение не должно выбрасываться
    failing_function()

    # Проверяем, что логирование было вызвано
    mock_logger.error.assert_called_once()


def test_log_exceptions_decorator(mock_logger):
    """Тестирует декоратор логирования исключений."""
    with patch('src.utils.logging_utils.get_logger', return_value=mock_logger):
        # Создаем функцию с декоратором
        @log_exceptions
        def failing_function():
            raise ValueError("Test error")

        # Вызываем функцию и проверяем, что исключение перехватывается
        with pytest.raises(ValueError):
            failing_function()

        # Проверяем, что логирование было вызвано
        mock_logger.error.assert_called_once()


def test_get_logger():
    """Тестирует функцию получения логгера с контекстом."""
    # Создаем тестовый контекст
    test_context = {"user_id": 12345, "component": "test"}

    # Получаем логгер
    with patch('logging.Logger.addHandler') as mock_add_handler:
        logger = get_logger("test_module", test_context)

        # Проверяем, что логгер был создан правильно
        assert logger.extra["context"] == test_context

        # Проверяем, что добавляется обработчик
        assert mock_add_handler.called
