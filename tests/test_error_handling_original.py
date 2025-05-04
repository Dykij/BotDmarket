"""
Тестирование модуля обработки ошибок (error_handling).
"""

import pytest
import logging
import json
from unittest.mock import patch, MagicMock, mock_open

from src.utils.error_handling import (
    categorize_error,
    log_error,
    format_error_for_user,
    clear_error_storage,
    get_error_analytics
)


@pytest.fixture
def mock_logger():
    """Создает мок объекта логгера для тестов."""
    logger = MagicMock(spec=logging.Logger)
    return logger


def test_categorize_error():
    """Тест функции categorize_error."""
    # Тестируем категорию NETWORK_ERROR
    assert categorize_error(Exception("connection timeout")) == "NETWORK_ERROR"
    assert categorize_error(Exception("socket error")) == "NETWORK_ERROR"

    # Тестируем категорию API_ERROR
    assert categorize_error(Exception("api request failed")) == "API_ERROR"
    assert categorize_error(Exception("Invalid response")) == "API_ERROR"

    # Тестируем категорию AUTH_ERROR
    assert categorize_error(Exception("unauthorized access")) == "AUTH_ERROR"
    assert categorize_error(Exception("invalid token")) == "AUTH_ERROR"

    # Тестируем категорию BALANCE_ERROR
    assert categorize_error(Exception("insufficient balance")) == "BALANCE_ERROR"

    # Тестируем категорию DATA_ERROR
    assert categorize_error(Exception("json parse error")) == "DATA_ERROR"

    # Тестируем категорию INTERNAL_ERROR (по умолчанию)
    assert categorize_error(ValueError("random error")) == "INTERNAL_ERROR"

    # Тестирование для None или пустых ошибок
    assert categorize_error(Exception("")) == "INTERNAL_ERROR"
    if categorize_error(None) != "Unknown" and categorize_error(None) != "INTERNAL_ERROR":
        assert False, "Некорректная категоризация None"


def test_log_error():
    """Тест функции log_error."""
    # Тестовые данные
    error = ValueError("Тестовая ошибка")
    context = {"module": "test_module", "function": "test_function"}

    # Просто проверяем, что функция выполняется без ошибок
    # Логирование проверяется через захваченный вывод pytest
    try:
        log_error(error, context)
        assert True  # Если дошли до этой строки, значит ошибки не было
    except Exception as e:
        assert False, f"log_error вызвал исключение {e}"


def test_format_error_for_user():
    """Тест функции format_error_for_user."""
    # Тестовые данные
    error = ValueError("Тестовая ошибка")
    context = {"module": "test_module", "function": "test_function"}

    # Вызываем тестируемую функцию для разных типов ошибок
    # API ошибка
    api_error = Exception("API error")
    api_error_message = format_error_for_user(api_error, context)
    assert "API" in api_error_message or "сервер" in api_error_message.lower()

    # Сетевая ошибка
    network_error = Exception("connection timeout")
    network_error_message = format_error_for_user(network_error, context)
    assert "ошибка сети" in network_error_message.lower() or "connection" in network_error_message.lower()

    # Внутренняя ошибка
    internal_error_message = format_error_for_user(error, context)
    assert "ошибка" in internal_error_message.lower()


@patch('src.utils.error_handling.error_storage', [])
def test_clear_error_storage():
    """Тест функции clear_error_storage."""
    # Создаем копию глобальной переменной
    with patch('src.utils.error_handling.error_storage', [{"error": ValueError()}]):
        # Вызываем тестируемую функцию
        clear_error_storage()

        # Проверяем, что хранилище ошибок очищено
        from src.utils.error_handling import error_storage
        assert error_storage == []


@patch('src.utils.error_handling.error_storage')
def test_get_error_analytics(mock_error_storage):
    """Тест функции get_error_analytics."""
    # Настраиваем мок хранилища ошибок
    mock_error_storage.__len__.return_value = 3
    error_data = [
        {
            "error": ValueError("Ошибка 1"),
            "category": "INTERNAL_ERROR",
            "context": {"module": "module_1"}
        },
        {
            "error": TypeError("Ошибка 2"),
            "category": "API_ERROR",
            "context": {"module": "module_2"}
        },
        {
            "error": ValueError("Ошибка 3"),
            "category": "INTERNAL_ERROR",
            "context": {"module": "module_1"}
        }
    ]
    mock_error_storage.__iter__.return_value = error_data
    mock_error_storage.__getitem__.return_value = error_data

    # Вызываем тестируемую функцию
    analytics = get_error_analytics()

    # Проверяем основные метрики в результате
    assert "total_errors" in analytics
    assert analytics["total_errors"] == 3

    # Проверяем статистику по категориям
    assert "category_stats" in analytics
    assert "INTERNAL_ERROR" in analytics["category_stats"]
    assert analytics["category_stats"]["INTERNAL_ERROR"] == 2
    assert "API_ERROR" in analytics["category_stats"]
    assert analytics["category_stats"]["API_ERROR"] == 1

    # Проверяем наличие последних ошибок
    assert "recent_errors" in analytics


if __name__ == "__main__":
    pytest.main()
