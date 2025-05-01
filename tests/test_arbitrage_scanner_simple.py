"""
Тесты для модуля arbitrage_scanner.
"""

import pytest
from unittest.mock import patch, AsyncMock

from src.telegram_bot.arbitrage_scanner import find_arbitrage_opportunities_async


@pytest.mark.asyncio
@patch('src.telegram_bot.arbitrage_scanner.arbitrage_pro')
@patch('src.telegram_bot.arbitrage_scanner.arbitrage_mid')
@patch('src.telegram_bot.arbitrage_scanner.arbitrage_boost')
async def test_find_arbitrage_opportunities_async_low_mode(mock_boost, mock_mid, mock_pro):
    """Тестирование функции поиска арбитражных возможностей в режиме low."""
    # Тестовые предметы
    test_items = [
        {
            "title": "Test Item 1",
            "price": {"amount": 1000},
            "profit": 100,
            "profit_percent": 10.0
        },
        {
            "title": "Test Item 2",
            "price": {"amount": 2000},
            "profit": 200,
            "profit_percent": 10.0
        }
    ]
    
    # Настройка мока
    mock_boost.return_value = test_items
    mock_mid.return_value = []
    mock_pro.return_value = []
    
    # Вызов тестируемой функции
    results = await find_arbitrage_opportunities_async(
        game="csgo", 
        mode="low", 
        max_items=1
    )
    
    # Проверки
    mock_boost.assert_called_once_with("csgo")
    mock_mid.assert_not_called()
    mock_pro.assert_not_called()
    assert len(results) == 1
    assert results[0]["title"] == "Test Item 1"


@pytest.mark.asyncio
@patch('src.telegram_bot.arbitrage_scanner.arbitrage_pro')
@patch('src.telegram_bot.arbitrage_scanner.arbitrage_mid')
@patch('src.telegram_bot.arbitrage_scanner.arbitrage_boost')
async def test_find_arbitrage_opportunities_async_medium_mode(mock_boost, mock_mid, mock_pro):
    """Тестирование функции поиска арбитражных возможностей в режиме medium."""
    test_items = [
        {
            "title": "Test Item 3",
            "price": {"amount": 3000},
            "profit": 300,
            "profit_percent": 10.0
        }
    ]
    
    # Настройка мока
    mock_boost.return_value = []
    mock_mid.return_value = test_items
    mock_pro.return_value = []
    
    # Вызов тестируемой функции
    results = await find_arbitrage_opportunities_async(
        game="csgo", 
        mode="medium"
    )
    
    # Проверки
    mock_boost.assert_not_called()
    mock_mid.assert_called_once_with("csgo")
    mock_pro.assert_not_called()
    assert len(results) == 1
    assert results[0]["title"] == "Test Item 3"
