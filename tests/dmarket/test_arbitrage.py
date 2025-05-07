"""Тесты для модуля arbitrage.py."""

from unittest.mock import AsyncMock, patch

import pytest

from src.dmarket.arbitrage import (
    _find_arbitrage_async,
    arbitrage_boost_async,
    fetch_market_items,
    find_arbitrage_items,
)


@pytest.fixture
def mock_dmarket_api():
    """Создает мок объект DMarket API клиента."""
    mock_api = AsyncMock()
    # Настройка методов API
    mock_api.get_market_items = AsyncMock()
    mock_api.get_user_inventory = AsyncMock()
    return mock_api


@pytest.mark.asyncio
async def test_fetch_market_items(mock_dmarket_api):
    """Тестирует получение предметов с рынка."""
    # Тестовые данные
    market_data = {
        "objects": [
            {"title": "Test Item", "price": {"USD": 1000}},  # Цена в центах
            {"title": "Another Item", "price": {"USD": 2000}},
        ],
    }

    # Настраиваем мок
    mock_dmarket_api.get_market_items.return_value = market_data

    # Тестируем получение предметов
    items = await fetch_market_items(
        game="csgo",
        limit=10,
        price_from=5.0,
        price_to=20.0,
        dmarket_api=mock_dmarket_api,
    )

    # Проверяем результаты
    assert len(items) == 2
    assert items[0]["title"] == "Test Item"
    assert items[1]["title"] == "Another Item"

    # Проверяем, что API был вызван с правильными параметрами
    mock_dmarket_api.get_market_items.assert_called_once_with(
        game="csgo",
        limit=10,
        price_from=500,  # Преобразовано в центы
        price_to=2000,  # Преобразовано в центы
    )


@pytest.mark.asyncio
async def test_find_arbitrage_async():
    """Тестирует поиск арбитражных предметов."""
    # Мокаем fetch_market_items
    with patch("src.dmarket.arbitrage.fetch_market_items") as mock_fetch:
        # Настраиваем мок
        mock_fetch.return_value = [
            {
                "title": "Item 1",
                "price": {"USD": 10000},  # $100
                "marketHashName": "Item 1",
            },
            {
                "title": "Item 2",
                "price": {"USD": 20000},  # $200
                "marketHashName": "Item 2",
            },
        ]

        # Вызываем функцию поиска арбитражных возможностей
        results = await _find_arbitrage_async(
            min_profit=10.0,
            max_profit=50.0,
            game="csgo",
            price_from=5.0,
            price_to=200.0,
        )

        # Проверяем, что fetch_market_items был вызван с правильными параметрами
        mock_fetch.assert_called_once_with(
            game="csgo",
            limit=100,
            price_from=5.0,
            price_to=200.0,
        )


@pytest.mark.asyncio
async def test_arbitrage_boost_async():
    """Тестирует функцию арбитража для режима boost."""
    # Мокаем _find_arbitrage_async
    with patch("src.dmarket.arbitrage._find_arbitrage_async") as mock_find:
        # Настраиваем мок для возврата списка предметов
        mock_find.return_value = [{"name": "Test Item", "profit": 15.0}]

        # Вызываем функцию
        items = await arbitrage_boost_async(game="csgo")

        # Проверяем, что _find_arbitrage_async был вызван
        mock_find.assert_called_once()

        # Проверяем возвращаемое значение
        assert len(items) > 0


@pytest.mark.asyncio
async def test_find_arbitrage_items():
    """Тестирует поиск арбитражных возможностей для режима boost."""
    # Мокаем arbitrage_boost_async вместо проверки api_client
    with patch("src.dmarket.arbitrage.arbitrage_boost_async") as mock_boost:
        # Настраиваем возвращаемое значение
        mock_boost.return_value = [
            {"name": "Boost Item", "profit": 5.0},
        ]

        # Вызываем функцию с режимом 'boost'
        items = await find_arbitrage_items(
            game="csgo",
            mode="boost",
            min_price=1.0,
            max_price=100.0,
        )

        # Проверяем, что вызвана нужная функция и есть результаты
        mock_boost.assert_called_once()
        assert len(items) > 0
