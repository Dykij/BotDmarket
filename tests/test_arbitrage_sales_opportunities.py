"""
Тесты для функции get_arbitrage_opportunities_with_sales_history из модуля sales_history.py.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from src.dmarket.sales_history import get_arbitrage_opportunities_with_sales_history
from src.dmarket.dmarket_api import DMarketAPI

# Создаем мок для функции create_api_client, которая отсутствует в коде
async def mock_create_api_client() -> DMarketAPI:
    """Мок для функции create_api_client."""
    return MagicMock(spec=DMarketAPI)


@pytest.mark.asyncio
async def test_get_arbitrage_opportunities_with_sales_history_no_items():
    """Проверяет возврат пустого списка, когда нет арбитражных возможностей."""
    # Создаем мок для API клиента
    api_client_mock = MagicMock(spec=DMarketAPI)

    # Мок для find_arbitrage_items, возвращающий пустой список
    with patch("src.dmarket.arbitrage.find_arbitrage_items") as mock_find_arbitrage_items:
        mock_find_arbitrage_items.return_value = []

        # Вызываем тестируемую функцию с передачей API клиента
        result = await get_arbitrage_opportunities_with_sales_history(api_client=api_client_mock)

        # Проверяем результат
        assert result == []


@pytest.mark.asyncio
async def test_get_arbitrage_opportunities_with_sales_history_with_items():
    """Проверяет обработку предметов с арбитражными возможностями."""
    # Создаем мок для API клиента
    api_client_mock = MagicMock(spec=DMarketAPI)

    # Тестовые данные
    test_arbitrage_items = [
        {"market_hash_name": "AK-47 | Redline", "price": 1000, "profit": 100},
        {"market_hash_name": "AWP | Asiimov", "price": 2000, "profit": 200}
    ]

    # Тестовые данные анализа продаж
    test_sales_analysis1 = {
        "item_name": "AK-47 | Redline",
        "has_data": True,
        "sales_per_day": 2.0,
        "price_trend": "stable"
    }

    test_sales_analysis2 = {
        "item_name": "AWP | Asiimov",
        "has_data": True,
        "sales_per_day": 0.1,  # Меньше min_sales_per_day
        "price_trend": "up"
    }

    with patch("src.dmarket.arbitrage.find_arbitrage_items") as mock_find_arbitrage_items, \
         patch("src.dmarket.sales_history.analyze_sales_history") as mock_analyze_sales_history:

        # Настраиваем моки
        mock_find_arbitrage_items.return_value = test_arbitrage_items
        mock_analyze_sales_history.side_effect = [test_sales_analysis1, test_sales_analysis2]

        # Вызываем тестируемую функцию с мин. кол-вом продаж в день = 0.5
        result = await get_arbitrage_opportunities_with_sales_history(
            min_sales_per_day=0.5,
            api_client=api_client_mock
        )

        # Проверяем, что функция find_arbitrage_items была вызвана правильно
        mock_find_arbitrage_items.assert_called_once()

        # Проверяем, что функция analyze_sales_history была вызвана для каждого предмета
        assert mock_analyze_sales_history.call_count == 2

        # Проверяем результат
        assert len(result) == 1  # Должен вернуться только один предмет (второй отфильтрован)
        assert result[0]["market_hash_name"] == "AK-47 | Redline"
        assert "sales_analysis" in result[0]
        assert result[0]["sales_analysis"]["sales_per_day"] == 2.0


@pytest.mark.asyncio
async def test_get_arbitrage_opportunities_with_sales_history_filter_by_trend():
    """Проверяет фильтрацию предметов по тренду цены."""
    # Создаем мок для API клиента
    api_client_mock = MagicMock(spec=DMarketAPI)

    # Тестовые данные
    test_arbitrage_items = [
        {"market_hash_name": "AK-47 | Redline", "price": 1000, "profit": 100},
        {"market_hash_name": "AWP | Asiimov", "price": 2000, "profit": 200},
        {"market_hash_name": "M4A4 | Howl", "price": 5000, "profit": 500}
    ]

    # Тестовые данные анализа продаж
    test_sales_analysis1 = {
        "item_name": "AK-47 | Redline",
        "has_data": True,
        "sales_per_day": 2.0,
        "price_trend": "up"
    }

    test_sales_analysis2 = {
        "item_name": "AWP | Asiimov",
        "has_data": True,
        "sales_per_day": 1.5,
        "price_trend": "down"
    }

    test_sales_analysis3 = {
        "item_name": "M4A4 | Howl",
        "has_data": True,
        "sales_per_day": 1.0,
        "price_trend": "stable"
    }

    with patch("src.dmarket.arbitrage.find_arbitrage_items") as mock_find_arbitrage_items, \
         patch("src.dmarket.sales_history.analyze_sales_history") as mock_analyze_sales_history:

        # Настраиваем моки
        mock_find_arbitrage_items.return_value = test_arbitrage_items
        mock_analyze_sales_history.side_effect = [test_sales_analysis1, test_sales_analysis2, test_sales_analysis3]

        # Вызываем тестируемую функцию с фильтром по тренду "up"
        result = await get_arbitrage_opportunities_with_sales_history(
            price_trend_filter="up",
            api_client=api_client_mock
        )

        # Проверяем результат
        assert len(result) == 1  # Должен вернуться только один предмет с трендом "up"
        assert result[0]["market_hash_name"] == "AK-47 | Redline"
        assert result[0]["sales_analysis"]["price_trend"] == "up"


@pytest.mark.asyncio
async def test_get_arbitrage_opportunities_with_sales_history_no_data():
    """Проверяет фильтрацию предметов без данных о продажах."""
    # Создаем мок для API клиента
    api_client_mock = MagicMock(spec=DMarketAPI)

    # Тестовые данные
    test_arbitrage_items = [
        {"market_hash_name": "AK-47 | Redline", "price": 1000, "profit": 100}
    ]

    # Тестовые данные анализа продаж (предмет без данных)
    test_sales_analysis = {
        "item_name": "AK-47 | Redline",
        "has_data": False
    }

    with patch("src.dmarket.arbitrage.find_arbitrage_items") as mock_find_arbitrage_items, \
         patch("src.dmarket.sales_history.analyze_sales_history") as mock_analyze_sales_history:

        # Настраиваем моки
        mock_find_arbitrage_items.return_value = test_arbitrage_items
        mock_analyze_sales_history.return_value = test_sales_analysis

        # Вызываем тестируемую функцию
        result = await get_arbitrage_opportunities_with_sales_history(api_client=api_client_mock)

        # Проверяем результат
        assert len(result) == 0  # Предмет без данных должен быть отфильтрован
