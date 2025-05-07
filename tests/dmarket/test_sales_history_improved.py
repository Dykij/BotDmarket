"""Расширенные и улучшенные тесты для модуля sales_history.py.

Этот модуль содержит дополнительные тесты для повышения покрытия кода
функций в src.dmarket.sales_history.
"""

import time
from unittest.mock import AsyncMock, patch

import pytest

from src.dmarket.sales_history import (
    analyze_sales_history,
    get_arbitrage_opportunities_with_sales_history,
    get_sales_history,
)


@pytest.fixture
def mock_api_client():
    """Создает мок объект DMarket API клиента."""
    client = AsyncMock()
    client.request = AsyncMock()
    return client


@pytest.fixture
def mock_execute_api_request():
    """Создает мок для функции execute_api_request."""
    with patch("src.dmarket.sales_history.execute_api_request") as mock:
        yield mock


@pytest.fixture
def mock_current_time():
    """Создает фиксированное текущее время для тестов."""
    current_time = int(time.time())
    with patch("time.time", return_value=current_time):
        yield current_time


@pytest.mark.asyncio
async def test_get_sales_history_with_offset(mock_api_client):
    """Проверяет, что параметр offset корректно передается в запрос."""
    # Настраиваем мок для возврата данных
    expected_result = {
        "LastSales": [
            {"itemId": "123", "price": 10.5, "date": "2023-01-01"},
        ],
        "Total": 1,
    }
    mock_api_client.request.return_value = expected_result

    # Вызываем функцию с offset
    await get_sales_history(
        ["AK-47 | Redline"],
        offset="someOffsetValue",
        api_client=mock_api_client,
    )

    # Проверяем, что offset был передан в параметрах запроса
    call_args = mock_api_client.request.call_args[1]
    assert call_args["params"]["Offset"] == "someOffsetValue"


@pytest.mark.asyncio
async def test_get_sales_history_large_batches_with_error(mock_api_client):
    """Проверяет обработку ошибки при работе с большими батчами."""
    # Создаем список из 60 предметов
    items = [f"Item_{i}" for i in range(60)]

    # Настраиваем мок - первый запрос успешный, второй с ошибкой
    mock_response1 = {
        "LastSales": [{"item": f"Item_{i}", "price": i} for i in range(50)],
        "Total": 50,
    }
    mock_response2 = {
        "Error": "API Error in batch",
        "LastSales": [],
        "Total": 0,
    }

    # Обновляем side_effect для последовательных вызовов
    mock_api_client.request = AsyncMock(side_effect=[mock_response1, mock_response2])

    # Вызываем функцию с моком API
    result = await get_sales_history(items, api_client=mock_api_client)

    # Проверяем, что функция обнаружила ошибку и вернула её
    assert "Error" in result
    assert result["Error"] == "API Error in batch"


@pytest.mark.asyncio
async def test_get_sales_history_execute_api_request(
    mock_execute_api_request, mock_api_client
):
    """Проверяет, что функция execute_api_request вызывается с правильными параметрами."""
    # Настраиваем мок для возврата данных
    expected_result = {
        "LastSales": [
            {"itemId": "123", "price": 10.5, "date": "2023-01-01"},
        ],
        "Total": 1,
    }
    mock_execute_api_request.return_value = expected_result

    # Вызываем функцию
    result = await get_sales_history(["AK-47 | Redline"], api_client=mock_api_client)

    # Проверяем, что execute_api_request был вызван с правильными параметрами
    mock_execute_api_request.assert_called_once()
    call_args = mock_execute_api_request.call_args
    assert call_args[1]["endpoint_type"] == "last_sales"
    assert call_args[1]["max_retries"] == 2


@pytest.mark.asyncio
async def test_analyze_sales_history_price_trend_calculation(
    mock_api_client, mock_current_time
):
    """Проверяет корректный расчет тренда цены в разных сценариях."""
    with patch("src.dmarket.sales_history.get_sales_history") as mock_get_sales_history:
        day_in_seconds = 86400

        # Тренд растущих цен (первая половина периода с более низкими ценами)
        prices_up = [
            {
                "title": "Item1",
                "price": {"USD": 10.0},
                "date": mock_current_time - day_in_seconds * 6,
            },
            {
                "title": "Item1",
                "price": {"USD": 11.0},
                "date": mock_current_time - day_in_seconds * 5,
            },
            {
                "title": "Item1",
                "price": {"USD": 12.0},
                "date": mock_current_time - day_in_seconds * 4,
            },
            {
                "title": "Item1",
                "price": {"USD": 13.0},
                "date": mock_current_time - day_in_seconds * 3,
            },
            {
                "title": "Item1",
                "price": {"USD": 14.0},
                "date": mock_current_time - day_in_seconds * 2,
            },
            {
                "title": "Item1",
                "price": {"USD": 15.0},
                "date": mock_current_time - day_in_seconds * 1,
            },
        ]

        mock_get_sales_history.return_value = {
            "LastSales": prices_up,
            "Total": len(prices_up),
        }

        result = await analyze_sales_history("Item1", api_client=mock_api_client)
        assert result["price_trend"] == "up"

        # Тренд падающих цен (первая половина периода с более высокими ценами)
        prices_down = [
            {
                "title": "Item1",
                "price": {"USD": 15.0},
                "date": mock_current_time - day_in_seconds * 6,
            },
            {
                "title": "Item1",
                "price": {"USD": 14.0},
                "date": mock_current_time - day_in_seconds * 5,
            },
            {
                "title": "Item1",
                "price": {"USD": 13.0},
                "date": mock_current_time - day_in_seconds * 4,
            },
            {
                "title": "Item1",
                "price": {"USD": 12.0},
                "date": mock_current_time - day_in_seconds * 3,
            },
            {
                "title": "Item1",
                "price": {"USD": 11.0},
                "date": mock_current_time - day_in_seconds * 2,
            },
            {
                "title": "Item1",
                "price": {"USD": 10.0},
                "date": mock_current_time - day_in_seconds * 1,
            },
        ]

        mock_get_sales_history.return_value = {
            "LastSales": prices_down,
            "Total": len(prices_down),
        }

        result = await analyze_sales_history("Item1", api_client=mock_api_client)
        assert result["price_trend"] == "down"

        # Стабильный тренд цен (цены близки друг к другу)
        prices_stable = [
            {
                "title": "Item1",
                "price": {"USD": 10.0},
                "date": mock_current_time - day_in_seconds * 6,
            },
            {
                "title": "Item1",
                "price": {"USD": 10.1},
                "date": mock_current_time - day_in_seconds * 5,
            },
            {
                "title": "Item1",
                "price": {"USD": 10.0},
                "date": mock_current_time - day_in_seconds * 4,
            },
            {
                "title": "Item1",
                "price": {"USD": 10.2},
                "date": mock_current_time - day_in_seconds * 3,
            },
            {
                "title": "Item1",
                "price": {"USD": 10.1},
                "date": mock_current_time - day_in_seconds * 2,
            },
            {
                "title": "Item1",
                "price": {"USD": 10.0},
                "date": mock_current_time - day_in_seconds * 1,
            },
        ]

        mock_get_sales_history.return_value = {
            "LastSales": prices_stable,
            "Total": len(prices_stable),
        }

        result = await analyze_sales_history("Item1", api_client=mock_api_client)
        assert result["price_trend"] == "stable"


@pytest.mark.asyncio
async def test_analyze_sales_history_different_price_formats(
    mock_api_client, mock_current_time
):
    """Проверяет обработку различных форматов цен в истории продаж."""
    with patch("src.dmarket.sales_history.get_sales_history") as mock_get_sales_history:
        day_in_seconds = 86400

        # Разные форматы цен
        mixed_prices = [
            {
                "title": "Item1",
                "price": {"USD": 10.0},  # Цена как словарь
                "date": mock_current_time - day_in_seconds * 5,
            },
            {
                "title": "Item1",
                "price": 11.0,  # Цена как число
                "date": mock_current_time - day_in_seconds * 4,
            },
            {
                "title": "Item1",
                "price": "12.0",  # Цена как строка (хотя не поддерживается)
                "date": mock_current_time - day_in_seconds * 3,
            },
            {
                "title": "Item1",
                # Цена отсутствует
                "date": mock_current_time - day_in_seconds * 2,
            },
        ]

        mock_get_sales_history.return_value = {
            "LastSales": mixed_prices,
            "Total": len(mixed_prices),
        }

        result = await analyze_sales_history("Item1", api_client=mock_api_client)

        # Должно быть 2 валидных цены (словарь и число)
        assert result["total_sales"] == 4  # Все записи
        assert result["has_data"] == True
        # Цена как строка и отсутствующая цена не должны быть обработаны
        assert len(result["recent_sales"]) == 2


@pytest.mark.asyncio
async def test_analyze_sales_history_sale_format_from_api(
    mock_api_client, mock_current_time
):
    """Проверяет обработку формата данных из реального API DMarket."""
    with patch("src.dmarket.sales_history.get_sales_history") as mock_get_sales_history:
        day_in_seconds = 86400

        # Формат данных из реального API
        api_format_data = {
            "LastSales": [
                {
                    "MarketHashName": "AK-47 | Redline",
                    "Sales": [
                        {
                            "Price": 10.25,
                            "Currency": "USD",
                            "Timestamp": mock_current_time - day_in_seconds * 2,
                            "OrderType": "instant",
                        },
                        {
                            "Price": 10.50,
                            "Currency": "USD",
                            "Timestamp": mock_current_time - day_in_seconds * 1,
                            "OrderType": "market",
                        },
                    ],
                },
            ],
            "Total": 2,
        }

        mock_get_sales_history.return_value = api_format_data

        result = await analyze_sales_history(
            "AK-47 | Redline", api_client=mock_api_client
        )

        assert result["has_data"] == True
        assert len(result["recent_sales"]) == 2
        assert result["avg_price"] == 10.375  # (10.25 + 10.50) / 2


@pytest.mark.asyncio
async def test_get_arbitrage_opportunities_with_sales_history_filtering(
    mock_api_client,
):
    """Проверяет фильтрацию результатов по объему продаж и тренду."""
    # Патчим функции, на которые опирается тестируемый метод
    arbitrage_items = [
        {"market_hash_name": "Item1", "profit": 1.50},
        {"market_hash_name": "Item2", "profit": 2.00},
        {"market_hash_name": "Item3", "profit": 1.00},
        {"market_hash_name": "Item4", "profit": 3.00},
    ]

    # Мок для find_arbitrage_items
    with patch(
        "src.dmarket.arbitrage.find_arbitrage_items",
        AsyncMock(return_value=arbitrage_items),
    ):
        # Мок для analyze_sales_history с разными данными
        async def mock_analyze(item_name, days=None, api_client=None):
            analyses = {
                "Item1": {
                    "has_data": True,
                    "sales_per_day": 2.0,  # Больше минимума
                    "price_trend": "up",
                    "item_name": "Item1",
                    "avg_price": 10.0,
                },
                "Item2": {
                    "has_data": True,
                    "sales_per_day": 0.2,  # Меньше минимума, должен быть отфильтрован
                    "price_trend": "down",
                    "item_name": "Item2",
                    "avg_price": 20.0,
                },
                "Item3": {
                    "has_data": True,
                    "sales_per_day": 1.5,  # Больше минимума
                    "price_trend": "stable",
                    "item_name": "Item3",
                    "avg_price": 15.0,
                },
                "Item4": {
                    "has_data": False,  # Нет данных, должен быть отфильтрован
                    "item_name": "Item4",
                },
            }
            return analyses.get(item_name, {"has_data": False, "item_name": item_name})

        with patch("src.dmarket.sales_history.analyze_sales_history", mock_analyze):
            # Тест 1: Фильтр по минимальному объему продаж
            result1 = await get_arbitrage_opportunities_with_sales_history(
                min_sales_per_day=1.0,
                price_trend_filter=None,  # Без фильтра по тренду
                api_client=mock_api_client,
            )

            assert len(result1) == 2
            assert any(item["market_hash_name"] == "Item1" for item in result1)
            assert any(item["market_hash_name"] == "Item3" for item in result1)

            # Тест 2: Фильтр по тренду
            result2 = await get_arbitrage_opportunities_with_sales_history(
                min_sales_per_day=1.0,
                price_trend_filter="up",  # Только растущие
                api_client=mock_api_client,
            )

            assert len(result2) == 1
            assert result2[0]["market_hash_name"] == "Item1"

            # Тест 3: Фильтр по тренду "стабильный"
            result3 = await get_arbitrage_opportunities_with_sales_history(
                min_sales_per_day=1.0,
                price_trend_filter="stable",
                api_client=mock_api_client,
            )

            assert len(result3) == 1
            assert result3[0]["market_hash_name"] == "Item3"


@pytest.mark.asyncio
async def test_get_arbitrage_opportunities_no_arbitrage_items(mock_api_client):
    """Проверяет обработку случая, когда нет арбитражных возможностей."""
    # Мок для find_arbitrage_items - пустой список
    with patch(
        "src.dmarket.arbitrage.find_arbitrage_items",
        AsyncMock(return_value=[]),
    ):
        result = await get_arbitrage_opportunities_with_sales_history(
            api_client=mock_api_client,
        )

        assert result == []
        # Анализ истории продаж не должен вызываться
        with patch("src.dmarket.sales_history.analyze_sales_history") as mock_analyze:
            result = await get_arbitrage_opportunities_with_sales_history(
                api_client=mock_api_client,
            )
            assert not mock_analyze.called
