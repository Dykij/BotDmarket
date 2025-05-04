"""
Тесты для модуля auto_arbitrage_scanner.py
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
import time

from src.telegram_bot.auto_arbitrage_scanner import (
    _get_cached_results,
    _save_to_cache,
    scan_game_for_arbitrage,
    check_user_balance
)


def test_cache_functionality():
    """Тест функций кеширования результатов сканирования."""
    # Подготовка тестовых данных
    cache_key = ("csgo", "medium", 0.0, 100.0)
    test_items = [
        {"title": "Item 1", "price": {"amount": 1000}, "profit": 100},
        {"title": "Item 2", "price": {"amount": 2000}, "profit": 200},
    ]
    
    # Сохраняем в кеш и сразу получаем результат
    with patch("src.telegram_bot.auto_arbitrage_scanner._scanner_cache", {}):
        with patch("src.telegram_bot.auto_arbitrage_scanner.time.time", return_value=1000.0):
            _save_to_cache(cache_key, test_items)
            result = _get_cached_results(cache_key)
            
            # Проверка возвращаемого значения
            assert result == test_items
    
    # Проверка работы TTL кеша
    with patch("src.telegram_bot.auto_arbitrage_scanner._scanner_cache", 
              {cache_key: (test_items, 1000.0)}):
        # Через 1 минуту кеш еще должен быть валидным (TTL=5 минут)
        with patch("src.telegram_bot.auto_arbitrage_scanner.time.time", return_value=1060.0):
            result = _get_cached_results(cache_key)
            assert result == test_items
            
        # Через 6 минут кеш уже должен стать невалидным
        with patch("src.telegram_bot.auto_arbitrage_scanner.time.time", return_value=1360.0):
            result = _get_cached_results(cache_key)
            assert result is None


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage_scanner._get_cached_results")
@patch("src.telegram_bot.auto_arbitrage_scanner._save_to_cache")
@patch("src.telegram_bot.auto_arbitrage_scanner.ArbitrageTrader")
@patch("src.telegram_bot.auto_arbitrage_scanner.rate_limiter")
async def test_scan_game_for_arbitrage_cached(
    mock_rate_limiter, mock_trader_class, mock_save_cache, mock_get_cache
):
    """Тест функции сканирования игры с использованием кеша."""
    # Настройка моков для кеша
    test_items = [
        {"title": "Cached Item 1", "price": {"amount": 1000}, "profit": 100},
        {"title": "Cached Item 2", "price": {"amount": 2000}, "profit": 200},
    ]
    mock_get_cache.return_value = test_items
    
    # Вызываем тестируемую функцию
    result = await scan_game_for_arbitrage("csgo", mode="medium", max_items=10)
    
    # Проверки
    mock_get_cache.assert_called_once()
    mock_trader_class.assert_not_called()  # API не должен вызываться, если данные в кеше
    
    # Проверяем возвращаемое значение
    assert result == test_items


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage_scanner._get_cached_results")
@patch("src.telegram_bot.auto_arbitrage_scanner._save_to_cache")
@patch("src.telegram_bot.auto_arbitrage_scanner.ArbitrageTrader")
@patch("src.telegram_bot.auto_arbitrage_scanner.rate_limiter")
async def test_scan_game_for_arbitrage_no_cache(
    mock_rate_limiter, mock_trader_class, mock_save_cache, mock_get_cache
):
    """Тест функции сканирования игры без использования кеша."""
    # Настройка моков
    mock_rate_limiter.wait_if_needed = AsyncMock()
    mock_get_cache.return_value = None  # Кеш пуст
    
    # Подготовка тестовых данных
    test_items = [
        {"title": "Fresh Item 1", "price": {"amount": 1000}, "profit": 100},
        {"title": "Fresh Item 2", "price": {"amount": 2000}, "profit": 200},
    ]
    
    # Настройка мока трейдера
    mock_trader_instance = MagicMock()
    mock_trader_instance.find_arbitrage_items = AsyncMock(return_value=test_items)
    mock_trader_class.return_value = mock_trader_instance
    
    # Вызываем тестируемую функцию
    result = await scan_game_for_arbitrage(
        "csgo", 
        mode="medium", 
        max_items=10,
        price_from=5.0,
        price_to=50.0
    )
    
    # Проверки
    mock_get_cache.assert_called_once()
    mock_trader_class.assert_called_once()
    mock_trader_instance.find_arbitrage_items.assert_called_once()
    mock_save_cache.assert_called_once()
    mock_rate_limiter.wait_if_needed.assert_called_once_with("market")
    
    # Проверяем возвращаемое значение
    assert result == test_items


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage_scanner._get_cached_results")
@patch("src.telegram_bot.auto_arbitrage_scanner._save_to_cache")
@patch("src.telegram_bot.auto_arbitrage_scanner.ArbitrageTrader")
@patch("src.telegram_bot.auto_arbitrage_scanner.rate_limiter")
async def test_scan_game_for_arbitrage_exception(
    mock_rate_limiter, mock_trader_class, mock_save_cache, mock_get_cache
):
    """Тест обработки исключений в функции сканирования игры."""
    # Настройка моков
    mock_rate_limiter.wait_if_needed = AsyncMock()
    mock_get_cache.return_value = None  # Кеш пуст
    
    # Настройка мока трейдера для вызова исключения
    mock_trader_instance = MagicMock()
    mock_trader_instance.find_arbitrage_items = AsyncMock(side_effect=Exception("API error"))
    mock_trader_class.return_value = mock_trader_instance
    
    # Вызываем тестируемую функцию
    result = await scan_game_for_arbitrage("csgo", mode="medium", max_items=10)
    
    # Проверяем, что функция возвращает пустой список при ошибке
    assert result == []
    # Проверяем, что кеш не обновляется при ошибке
    mock_save_cache.assert_not_called()


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage_scanner.DMarketAPI")
async def test_check_user_balance_success(mock_api_class):
    """Тест успешной проверки баланса пользователя."""
    # Настройка моков
    mock_api_instance = AsyncMock()
    mock_api_instance._request = AsyncMock(
        return_value={"usd": "50.00"}
    )
    
    # Вызываем тестируемую функцию
    has_funds, balance = await check_user_balance(mock_api_instance)
    
    # Проверки
    mock_api_instance._request.assert_called_once()
    assert has_funds is True
    assert balance == "50.00 USD"


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage_scanner.DMarketAPI")
async def test_check_user_balance_zero(mock_api_class):
    """Тест проверки нулевого баланса пользователя."""
    # Настройка моков
    mock_api_instance = AsyncMock()
    mock_api_instance._request = AsyncMock(
        return_value={"usd": "0.00"}
    )
    
    # Вызываем тестируемую функцию
    has_funds, balance = await check_user_balance(mock_api_instance)
    
    # Проверки
    assert has_funds is False
    assert balance == "0.00 USD"


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage_scanner.DMarketAPI")
async def test_check_user_balance_error(mock_api_class):
    """Тест обработки ошибок при проверке баланса."""
    # Настройка моков
    mock_api_instance = AsyncMock()
    mock_api_instance._request = AsyncMock(
        side_effect=Exception("API error")
    )
    
    # Вызываем тестируемую функцию
    has_funds, balance = await check_user_balance(mock_api_instance)
    
    # Проверки
    assert has_funds is None
    assert balance == "Недоступно"
