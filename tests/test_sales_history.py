"""
Тесты для модуля sales_history.py.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import time
from datetime import datetime, timedelta

from src.dmarket.sales_history import (
    get_sales_history,
    analyze_sales_history,
    get_arbitrage_opportunities_with_sales_history
)
from src.utils.api_error_handling import APIError


@pytest.mark.asyncio
async def test_get_sales_history_empty_items():
    """
    Проверяет, что при пустом списке предметов возвращается ожидаемое значение.
    """
    result = await get_sales_history([])

    assert result == {"LastSales": [], "Total": 0}


@pytest.mark.asyncio
async def test_get_sales_history_too_many_items():
    """
    Проверяет ограничение количества предметов в запросе.
    """
    # Создаем список из 60 предметов
    items = [f"Item_{i}" for i in range(60)]

    # Применяем мок для API клиента
    api_client_mock = AsyncMock()
    api_client_mock.request = AsyncMock(return_value={"LastSales": [], "Total": 0})

    with patch("src.dmarket.sales_history.execute_api_request") as mock_execute_api_request:
        mock_execute_api_request.return_value = {"LastSales": [], "Total": 0}

        # Вызываем тестируемую функцию
        await get_sales_history(items, api_client=api_client_mock)

        # Получаем аргументы, переданные в execute_api_request
        args, kwargs = mock_execute_api_request.call_args

        # Вызываем функцию запроса, чтобы увидеть, какие параметры будут переданы в API
        request_func = kwargs.get('request_func')

        # Проверяем, что request_func существует
        assert request_func is not None

        # Теперь мы можем вызвать эту функцию и посмотреть, какой запрос будет отправлен
        await request_func()

        # Проверяем, что API.request был вызван с правильным параметром Titles, содержащим не более 50 элементов
        api_client_mock.request.assert_called_once()
        params = api_client_mock.request.call_args[1]['params']
        assert len(params['Titles']) <= 50


@pytest.mark.asyncio
async def test_get_sales_history_api_error():
    """
    Проверяет обработку ошибок API при получении истории продаж.
    """
    # Создаем мок для API клиента
    api_client_mock = AsyncMock()
    api_client_mock.request = AsyncMock()        # Настраиваем execute_api_request, чтобы она вызывала исключение
    with patch("src.dmarket.sales_history.execute_api_request") as mock_execute_api_request:
        error_message = "API Error: Rate limit exceeded"
        mock_execute_api_request.side_effect = APIError(error_message)

        # Вызываем тестируемую функцию
        result = await get_sales_history(["AK-47 | Redline"], api_client=api_client_mock)

        # Проверяем, что результат содержит ошибку
        assert "Error" in result
        assert error_message in result["Error"]  # Проверяем, что исходное сообщение содержится в результате
        assert result["LastSales"] == []
        assert result["Total"] == 0


@pytest.mark.asyncio
async def test_get_sales_history_success():
    """
    Проверяет успешное получение истории продаж.
    """
    # Создаем мок для API клиента
    api_client_mock = AsyncMock()

    # Настраиваем execute_api_request, чтобы она возвращала тестовый ответ
    expected_result = {
        "LastSales": [
            {
                "MarketHashName": "AK-47 | Redline",
                "Sales": [
                    {"Price": "10.50", "Currency": "USD", "Timestamp": time.time(), "OrderType": "Sell"}
                ]
            }
        ],
        "Total": 1
    }

    with patch("src.dmarket.sales_history.execute_api_request") as mock_execute_api_request:
        mock_execute_api_request.return_value = expected_result

        # Вызываем тестируемую функцию
        result = await get_sales_history(["AK-47 | Redline"], api_client=api_client_mock)

        # Проверяем результат
        assert result == expected_result


@pytest.mark.asyncio
async def test_analyze_sales_history_empty_data():
    """
    Проверяет анализ пустой истории продаж.
    """
    # Создаем мок для get_sales_history
    with patch("src.dmarket.sales_history.get_sales_history") as mock_get_sales_history:
        mock_get_sales_history.return_value = {"LastSales": [], "Total": 0}

        # Вызываем тестируемую функцию
        result = await analyze_sales_history("AK-47 | Redline")

        # Проверяем результат
        assert result["item_name"] == "AK-47 | Redline"
        assert result["has_data"] == False
        assert result["total_sales"] == 0
        assert result["recent_sales"] == []


@pytest.mark.asyncio
async def test_analyze_sales_history_with_error():
    """
    Проверяет анализ при ошибке в истории продаж.
    """
    # Создаем мок для get_sales_history
    with patch("src.dmarket.sales_history.get_sales_history") as mock_get_sales_history:
        error_message = "API Error: Rate limit exceeded"
        mock_get_sales_history.return_value = {"Error": error_message, "LastSales": [], "Total": 0}

        # Вызываем тестируемую функцию
        result = await analyze_sales_history("AK-47 | Redline")

        # Проверяем результат
        assert result["item_name"] == "AK-47 | Redline"
        assert result["has_data"] == False
        assert result["error"] == error_message


@pytest.mark.asyncio
async def test_analyze_sales_history_with_data():
    """
    Проверяет анализ истории продаж с реальными данными.
    """
    # Текущее время для тестов
    current_time = time.time()

    # Создаем тестовые данные продаж
    test_sales = [
        {"Price": "10.50", "Currency": "USD", "Timestamp": current_time - 3600, "OrderType": "Sell"},
        {"Price": "11.00", "Currency": "USD", "Timestamp": current_time - 7200, "OrderType": "Sell"},
        {"Price": "9.75", "Currency": "USD", "Timestamp": current_time - 10800, "OrderType": "Sell"},
        {"Price": "12.25", "Currency": "USD", "Timestamp": current_time - 14400, "OrderType": "Sell"},
        # Очень старая продажа, которая должна быть отфильтрована при анализе за 7 дней
        {"Price": "8.00", "Currency": "USD", "Timestamp": current_time - (8 * 86400), "OrderType": "Sell"}
    ]

    # Создаем мок для get_sales_history
    with patch("src.dmarket.sales_history.get_sales_history") as mock_get_sales_history:
        mock_get_sales_history.return_value = {
            "LastSales": [
                {
                    "MarketHashName": "AK-47 | Redline",
                    "Sales": test_sales
                }
            ],
            "Total": 1
        }

        # Вызываем тестируемую функцию с периодом в 7 дней
        result = await analyze_sales_history("AK-47 | Redline", days=7)

        # Проверяем результат
        assert result["item_name"] == "AK-47 | Redline"
        assert result["has_data"] == True
        assert result["total_sales"] == 5  # Все продажи включены в общее количество
        assert len(result["recent_sales"]) == 4  # Старая продажа не включена в недавние продажи

        # Проверяем статистику
        assert 10.8 <= result["avg_price"] <= 11.0  # Примерно 10.875
        assert result["min_price"] == 9.75
        assert result["max_price"] == 12.25
        assert result["sales_volume"] == 4



