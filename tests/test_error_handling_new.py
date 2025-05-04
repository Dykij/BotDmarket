"""
Тестирование модуля обработки ошибок (error_handling).
"""

import pytest
import logging
from typing import Dict, Any, Tuple
from unittest.mock import patch, MagicMock

from src.utils.error_handling import (
    categorize_error,
    log_error,
    format_error_for_user,
    should_retry,
    get_error_analytics,
    clear_error_storage
)


@pytest.fixture
def mock_logger():
    """Создает мок объекта логгера для тестов."""
    logger = MagicMock(spec=logging.Logger)
    return logger


def test_categorize_error():
    """Тест функции categorize_error."""
    # Тестирование категоризации разных типов ошибок
    assert categorize_error(ValueError("Тестовая ошибка")) == "ValueError"
    assert categorize_error(TypeError("Тестовая ошибка")) == "TypeError"
    assert categorize_error(Exception("Общая ошибка")) == "Exception"

    # Тестирование для ошибок без явного типа (None)
    assert categorize_error(None) == "Unknown"

    # Тестирование для пользовательских ошибок
    class CustomError(Exception):
        pass

    assert categorize_error(CustomError("Пользовательская ошибка")) == "CustomError"


def test_log_error(mock_logger):
    """Тест функции log_error."""
    error = ValueError("Тестовая ошибка")
    context = {"module": "test_module", "function": "test_function"}

    log_error(error, context, logger=mock_logger)

    # Проверяем, что была вызвана функция error() у логгера
    mock_logger.error.assert_called_once()

    # Проверяем содержание сообщения об ошибке
    error_message = mock_logger.error.call_args[0][0]
    assert "ValueError" in error_message
    assert "test_module" in error_message
    assert "test_function" in error_message


def test_format_error_for_user():
    """Тест функции format_error_for_user."""
    # Тест форматирования с контекстом
    error = ValueError("Тестовая ошибка")
    context = {"module": "test_module", "function": "test_function"}

    formatted_error = format_error_for_user(error, context)

    assert "Ошибка" in formatted_error
    assert "test_module" in formatted_error
    assert "test_function" in formatted_error

    # Тест форматирования без контекста
    formatted_error_no_context = format_error_for_user(error, None)

    assert "Ошибка" in formatted_error_no_context
    assert "ValueError" in formatted_error_no_context
    assert "Тестовая ошибка" in formatted_error_no_context


def test_should_retry():
    """Тест функции should_retry."""
    # Тест для ошибок, которые должны быть повторены
    retry_error_data = {
        "error": ConnectionError("Ошибка соединения"),
        "context": {"module": "api_call"}
    }
    should_retry_result, delay = should_retry(retry_error_data, 1)
    assert should_retry_result is True
    assert delay > 0

    # Тест для ошибок, которые не должны быть повторены
    no_retry_error_data = {
        "error": ValueError("Некорректное значение"),
        "context": {"module": "validation"}
    }
    should_retry_result, _ = should_retry(no_retry_error_data, 1)
    assert should_retry_result is False

    # Тест для превышения максимального количества попыток
    max_attempts_error_data = {
        "error": ConnectionError("Ошибка соединения"),
        "context": {"module": "api_call"}
    }
    should_retry_result, _ = should_retry(max_attempts_error_data, 5)
    assert should_retry_result is False


@patch('src.utils.error_handling.error_storage')
def test_get_error_analytics(mock_error_storage):
    """Тест функции get_error_analytics."""
    # Настраиваем мок хранилища ошибок
    mock_error_storage.__len__.return_value = 3
    mock_error_storage.__iter__.return_value = [
        {"error": ValueError("Ошибка 1"), "context": {"module": "module_1"}},
        {"error": TypeError("Ошибка 2"), "context": {"module": "module_2"}},
        {"error": ValueError("Ошибка 3"), "context": {"module": "module_1"}}
    ]

    # Вызываем тестируемую функцию
    analytics = get_error_analytics()

    # Проверяем результаты
    assert analytics["total_errors"] == 3
    assert analytics["error_types"]["ValueError"] == 2
    assert analytics["error_types"]["TypeError"] == 1
    assert analytics["modules"]["module_1"] == 2
    assert analytics["modules"]["module_2"] == 1


@patch('src.utils.error_handling.error_storage')
def test_clear_error_storage(mock_error_storage):
    """Тест функции clear_error_storage."""
    # Вызываем тестируемую функцию
    clear_error_storage()

    # Проверяем, что хранилище ошибок очищено
    mock_error_storage.clear.assert_called_once()


if __name__ == "__main__":
    pytest.main()
