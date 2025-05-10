"""Тесты для класса ArbitrageTrader из модуля arbitrage.py
"""
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Добавляем корневой каталог проекта в путь импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.dmarket.arbitrage import (
    ArbitrageTrader,
    _get_cached_results,
    _save_to_cache,
    arbitrage_boost_async,
    find_arbitrage_opportunities_async,
)


@pytest.fixture
def mock_dmarket_api():
    """Фикстура, которая создает мок DMarketAPI для тестирования."""
    with patch("src.dmarket.arbitrage.DMarketAPI") as mock_api:
        # Настраиваем мок для асинхронного контекстного менеджера
        async_mock = AsyncMock()
        mock_api.return_value.__aenter__.return_value = async_mock
        mock_api.return_value.__aexit__.return_value = None

        # Настраиваем мок для get_market_items
        market_items_response = {
            "objects": [
                {
                    "itemId": "test-item-1",
                    "title": "Test Item 1",
                    "price": {"amount": "1000"},  # 10 USD в центах
                    "suggestedPrice": {"amount": "1200"},  # 12 USD в центах
                    "extra": {"popularity": 0.8},
                },
                {
                    "itemId": "test-item-2",
                    "title": "Test Item 2",
                    "price": {"amount": "2000"},  # 20 USD в центах
                    "suggestedPrice": {"amount": "2500"},  # 25 USD в центах
                    "extra": {"popularity": 0.5},
                },
                {
                    "itemId": "test-item-3",
                    "title": "Test Item 3",
                    "price": {"amount": "5000"},  # 50 USD в центах
                    "extra": {"popularity": 0.3},
                },
            ],
        }

        async_mock.get_market_items.return_value = market_items_response

        # Мок для получения баланса
        async_mock.get_user_balance.return_value = {
            "usd": {"amount": 10000},  # 100 USD в центах
        }

        # Мок для покупки предмета
        async_mock.buy_item.return_value = {
            "itemId": "test-item-1",
            "status": "success",
        }

        # Мок для продажи предмета
        async_mock.sell_item.return_value = {
            "transactionId": "test-transaction-1",
            "status": "success",
        }

        # Мок для получения информации о цене
        async_mock.get_price_info.return_value = {
            "recommendedPrice": 1500,  # 15 USD в центах
        }

        yield mock_api


@pytest.mark.asyncio
async def test_get_cached_results():
    """Тестирование функции получения кэшированных результатов"""
    # Очищаем кэш перед тестом
    from src.dmarket.arbitrage import _arbitrage_cache

    _arbitrage_cache.clear()

    # Проверяем, что функция возвращает None для отсутствующего ключа
    cache_key = ("csgo", "boost", 0, 100)
    result = _get_cached_results(cache_key)
    assert result is None

    # Добавляем запись в кэш
    test_items = [{"name": "Test Item"}]
    _save_to_cache(cache_key, test_items)

    # Проверяем, что функция возвращает кэшированные данные
    result = _get_cached_results(cache_key)
    assert result == test_items


@pytest.mark.asyncio
async def test_arbitrage_boost_async(mock_dmarket_api):
    """Тестирование функции arbitrage_boost_async"""
    # Настраиваем мок для fetch_market_items
    with patch("src.dmarket.arbitrage.fetch_market_items") as mock_fetch:
        # Имитируем возврат предметов
        mock_fetch.return_value = [
            {
                "itemId": "test-boost-1",
                "title": "Test Boost Item",
                "price": {"amount": 300},
                "suggestedPrice": {"amount": 400},
                "extra": {"popularity": 0.8},
            },
        ]

        # Вызываем тестируемую функцию
        items = await arbitrage_boost_async(game="csgo")

        # Проверяем результаты
        assert len(items) > 0
        assert mock_fetch.called

        # Проверяем параметры вызова fetch_market_items
        mock_fetch.assert_called_once()
        args, kwargs = mock_fetch.call_args
        assert kwargs.get("game") == "csgo"


@pytest.mark.asyncio
async def test_find_arbitrage_opportunities_async(mock_dmarket_api):
    """Тестирование функции find_arbitrage_opportunities_async"""
    # Настраиваем мок для fetch_market_items
    with patch("src.dmarket.arbitrage.fetch_market_items") as mock_fetch:
        # Имитируем возврат предметов
        mock_fetch.return_value = [
            {
                "itemId": "test-opp-1",
                "title": "Test Opportunity Item",
                "price": {"amount": 1000},  # 10 USD
                "suggestedPrice": {"amount": 1200},  # 12 USD
                "extra": {"popularity": 0.8},
            },
        ]

        # Вызываем тестируемую функцию
        opportunities = await find_arbitrage_opportunities_async(
            min_profit_percentage=5.0,
            max_results=5,
            game="csgo",
        )

        # Проверяем результаты
        assert isinstance(opportunities, list)
        assert mock_fetch.called

        # Проверяем параметры вызова fetch_market_items
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_arbitrage_trader_check_balance(mock_dmarket_api):
    """Тестирование метода check_balance класса ArbitrageTrader"""
    # Создаем экземпляр ArbitrageTrader
    trader = ArbitrageTrader(
        public_key="test_public_key",
        secret_key="test_secret_key",
        api_url="https://api.test.com",
    )

    # Вызываем тестируемый метод
    has_funds, balance = await trader.check_balance()

    # Проверяем результаты
    assert has_funds is True
    assert balance == 100.0  # 10000 центов = 100 долларов

    # Проверяем, что API был вызван корректно
    assert trader.api.get_user_balance.called


@pytest.mark.asyncio
async def test_arbitrage_trader_find_profitable_items(mock_dmarket_api):
    """Тестирование метода find_profitable_items класса ArbitrageTrader"""
    # Создаем экземпляр ArbitrageTrader
    trader = ArbitrageTrader(
        public_key="test_public_key",
        secret_key="test_secret_key",
        api_url="https://api.test.com",
    )

    # Вызываем тестируемый метод
    items = await trader.find_profitable_items(
        game="csgo",
        min_profit_percentage=5.0,
        max_items=10,
    )

    # Проверяем результаты
    assert isinstance(items, list)

    # Проверяем, что API был вызван корректно
    trader.api.get_market_items.assert_called_once()
    args, kwargs = trader.api.get_market_items.call_args
    assert kwargs.get("game") == "csgo"


@pytest.mark.asyncio
async def test_arbitrage_trader_execute_trade(mock_dmarket_api):
    """Тестирование метода execute_arbitrage_trade класса ArbitrageTrader"""
    # Создаем экземпляр ArbitrageTrader
    trader = ArbitrageTrader(
        public_key="test_public_key",
        secret_key="test_secret_key",
        api_url="https://api.test.com",
    )

    # Создаем тестовый предмет для торговли
    test_item = {
        "name": "Test Trade Item",
        "buy_price": 10.0,
        "sell_price": 12.0,
        "profit": 2.0,
        "profit_percentage": 20.0,
        "market_hash_name": "Test Trade Item",
        "game": "csgo",
    }

    # Тестируем различные сценарии

    # 1. Успешная торговля
    result = await trader.execute_arbitrage_trade(test_item)
    assert result["success"] is True
    assert result["item_name"] == "Test Trade Item"
    assert "transaction_id" in result

    # Проверяем вызовы API
    trader.api.buy_item.assert_called_once()
    trader.api.sell_item.assert_called_once()


@pytest.mark.asyncio
async def test_arbitrage_trader_limits(mock_dmarket_api):
    """Тестирование лимитов торговли ArbitrageTrader"""
    # Создаем экземпляр ArbitrageTrader с низкими лимитами
    trader = ArbitrageTrader(
        public_key="test_public_key",
        secret_key="test_secret_key",
        api_url="https://api.test.com",
    )

    # Устанавливаем низкие лимиты
    trader.set_trading_limits(max_trade_value=5.0, daily_limit=20.0)

    # Создаем тестовый предмет, превышающий лимит
    expensive_item = {
        "name": "Expensive Item",
        "buy_price": 10.0,  # Выше лимита max_trade_value
        "sell_price": 12.0,
        "profit": 2.0,
        "profit_percentage": 20.0,
        "market_hash_name": "Expensive Item",
        "game": "csgo",
    }

    # Пытаемся торговать предметом
    result = await trader.execute_arbitrage_trade(expensive_item)

    # Проверяем, что торговля не выполнена из-за превышения лимита
    assert result["success"] is False
    assert "превышены лимиты торговли" in " ".join(result["errors"]).lower()

    # Проверяем, что API не был вызван
    assert not trader.api.buy_item.called
    assert not trader.api.sell_item.called


# Дополнительные тесты для кэширования


@pytest.mark.asyncio
async def test_cache_expiration():
    """Тестирование истечения срока действия кэша"""
    # Очищаем кэш перед тестом
    from src.dmarket.arbitrage import _arbitrage_cache

    _arbitrage_cache.clear()

    # Добавляем запись в кэш
    cache_key = ("csgo", "expiration", 0, 100)
    test_items = [{"name": "Expiring Item"}]

    # Сохраняем с истекшим временем
    import time

    expired_time = time.time() - 500  # 500 секунд назад
    _arbitrage_cache[cache_key] = (test_items, expired_time)

    # Проверяем, что функция возвращает None для истекшего кэша
    result = _get_cached_results(cache_key)
    assert result is None
