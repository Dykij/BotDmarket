"""
Тесты для модуля auto_arbitrage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from src.telegram_bot.auto_arbitrage import format_results


@pytest.mark.asyncio
async def test_format_results_empty():
    """Тестирование форматирования пустых результатов."""
    result = await format_results([], "auto_medium", "csgo")
    
    # Проверяем, что результат содержит сообщение о пустом результате
    assert "Нет данных" in result


@pytest.mark.asyncio
async def test_format_results_with_items():
    """Тестирование форматирования результатов с данными."""
    items = [
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
    
    result = await format_results(items, "auto_medium", "csgo")
    
    # Проверяем, что результат содержит заголовок и данные
    assert "Результаты автоматического арбитража" in result
    assert "Test Item 1" in result
    assert "Test Item 2" in result
    assert "$10.00" in result   # Цена первого предмета
    assert "$20.00" in result   # Цена второго предмета
    assert "Test Item 1" in result
    assert "Test Item 2" in result
    assert "$10.00" in result  # Цена первого предмета
    assert "$20.00" in result  # Цена второго предмета
    assert "$1.00" in result   # Прибыль первого предмета
    assert "$2.00" in result   # Прибыль второго предмета
