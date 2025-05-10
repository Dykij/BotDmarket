"""Упрощенные тесты для модуля arbitrage_scanner.

Этот модуль содержит базовые тесты для проверки функциональности модуля arbitrage_scanner,
фокусируясь на основных функциях и правильном обращении с API.
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram_bot.arbitrage_scanner import (
    find_arbitrage_opportunities_async,
)


@pytest.fixture
def mock_arbitrage_data() -> List[Dict[str, Any]]:
    """Создает фиктивные данные для тестирования."""
    return [
        {
            "id": "item1",
            "title": "AK-47 | Redline",
            "price": {"amount": 1000},  # $10.00
            "profit": 200,  # $2.00 прибыль
            "profit_percent": 10.0,
            "game": "csgo",
        },
        {
            "id": "item2",
            "title": "AWP | Asiimov",
            "price": {"amount": 5000},  # $50.00
            "profit": 800,  # $8.00 прибыль
            "profit_percent": 16.0,
            "game": "csgo",
        },
        {
            "id": "item3",
            "title": "Desert Eagle | Blaze",
            "price": {"amount": 3000},  # $30.00
            "profit": 500,  # $5.00 прибыль
            "profit_percent": 16.7,
            "game": "csgo",
        },
    ]


@pytest.mark.asyncio
async def test_find_arbitrage_opportunities_async_low_mode(mock_arbitrage_data):
    """Тест поиска арбитражных возможностей в режиме low."""
    # Патчим функции арбитража
    with patch("src.telegram_bot.arbitrage_scanner.arbitrage_boost", return_value=mock_arbitrage_data) as mock_boost:
        with patch("src.telegram_bot.arbitrage_scanner.arbitrage_mid") as mock_mid:
            with patch("src.telegram_bot.arbitrage_scanner.arbitrage_pro") as mock_pro:
                
                # Вызываем функцию
                result = await find_arbitrage_opportunities_async(game="csgo", mode="low", max_items=2)
                
                # Проверяем, что была вызвана правильная функция
                mock_boost.assert_called_once_with("csgo")
                mock_mid.assert_not_called()
                mock_pro.assert_not_called()
                
                # Проверяем результат
                assert len(result) == 2
                assert result[0]["id"] == "item1"
                assert result[1]["id"] == "item2"
                
                # Дополнительные проверки
                assert "title" in result[0]
                assert "price" in result[0]
                assert "profit" in result[0]
                assert "profit_percent" in result[0]


@pytest.mark.asyncio
async def test_find_arbitrage_opportunities_async_medium_mode(mock_arbitrage_data):
    """Тест поиска арбитражных возможностей в режиме medium."""
    # Патчим функции арбитража
    with patch("src.telegram_bot.arbitrage_scanner.arbitrage_boost") as mock_boost:
        with patch("src.telegram_bot.arbitrage_scanner.arbitrage_mid", return_value=mock_arbitrage_data) as mock_mid:
            with patch("src.telegram_bot.arbitrage_scanner.arbitrage_pro") as mock_pro:
                
                # Вызываем функцию
                result = await find_arbitrage_opportunities_async(game="csgo", mode="medium", max_items=3)
                
                # Проверяем, что была вызвана правильная функция
                mock_boost.assert_not_called()
                mock_mid.assert_called_once_with("csgo")
                mock_pro.assert_not_called()
                
                # Проверяем результат
                assert len(result) == 3
                assert [item["id"] for item in result] == ["item1", "item2", "item3"]


@pytest.mark.asyncio
async def test_find_arbitrage_opportunities_async_high_mode(mock_arbitrage_data):
    """Тест поиска арбитражных возможностей в режиме high."""
    # Патчим функции арбитража
    with patch("src.telegram_bot.arbitrage_scanner.arbitrage_boost") as mock_boost:
        with patch("src.telegram_bot.arbitrage_scanner.arbitrage_mid") as mock_mid:
            with patch("src.telegram_bot.arbitrage_scanner.arbitrage_pro", return_value=mock_arbitrage_data) as mock_pro:
                
                # Вызываем функцию
                result = await find_arbitrage_opportunities_async(game="csgo", mode="high", max_items=1)
                
                # Проверяем, что была вызвана правильная функция
                mock_boost.assert_not_called()
                mock_mid.assert_not_called()
                mock_pro.assert_called_once_with("csgo")
                
                # Проверяем результат
                assert len(result) == 1
                assert result[0]["id"] == "item1"


@pytest.mark.asyncio
async def test_find_arbitrage_opportunities_async_error_handling():
    """Тест обработки ошибок при поиске арбитражных возможностей."""
    # Патчим функцию, чтобы она вызывала исключение
    with patch("src.telegram_bot.arbitrage_scanner.arbitrage_mid", side_effect=Exception("API Error")):
        with patch("src.telegram_bot.arbitrage_scanner.rate_limiter") as mock_rate_limiter:
            mock_rate_limiter.wait_if_needed = AsyncMock()
            
            # Вызываем функцию
            result = await find_arbitrage_opportunities_async(game="csgo", mode="medium", max_items=10)
            
            # Проверяем, что при ошибке функция возвращает пустой список
            assert result == [] 