"""
Тесты для модуля arbitrage_scanner.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, List, Any

from src.telegram_bot.arbitrage_scanner import (
    find_arbitrage_opportunities_async,
    find_multi_game_arbitrage_opportunities,
    auto_trade_items
)


@pytest.fixture
def mock_arbitrage_data():
    """Создает фиктивные данные для тестирования."""
    return [
        {
            "id": "item1",
            "title": "AK-47 | Redline",
            "price": {"amount": 1000},  # $10.00
            "profit": 200,              # $2.00 прибыль
            "game": "csgo"
        },
        {
            "id": "item2",
            "title": "AWP | Asiimov",
            "price": {"amount": 5000},  # $50.00
            "profit": 800,              # $8.00 прибыль
            "game": "csgo"
        },
        {
            "id": "item3",
            "title": "Desert Eagle | Blaze",
            "price": {"amount": 3000},  # $30.00
            "profit": 500,              # $5.00 прибыль
            "game": "csgo"
        }
    ]
