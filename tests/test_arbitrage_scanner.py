"""
Модульные тесты для модуля arbitrage_scanner.
Проверяют функциональность поиска арбитражных возможностей.
"""

import json
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from typing import List, Dict, Any

from src.telegram_bot.arbitrage_scanner import find_arbitrage_opportunities_async


# Тестовые данные: предметы CS:GO
CSGO_ITEMS = [
    {
        "title": "AK-47 | Redline (Field-Tested)",
        "category": "rifle",
        "float": "0.18",
        "rarity": "Classified",
        "price": {"amount": 1000},
        "profit": 100,
        "profit_percent": 10.0,
    },
    {
        "title": "AWP | Asiimov (Field-Tested)",
        "category": "sniper rifle",
        "float": "0.25",
        "rarity": "Covert",
        "price": {"amount": 3000},
        "profit": 300,
        "profit_percent": 10.0,
    },
    {
        "title": "★ Butterfly Knife | Doppler (Factory New)",
        "category": "knife",
        "float": "0.01",
        "rarity": "Covert",
        "price": {"amount": 20000},
        "profit": 2500,
        "profit_percent": 12.5,
    },
    {
        "title": "StatTrak™ M4A4 | Neo-Noir (Minimal Wear)",
        "category": "rifle",
        "float": "0.09",
        "rarity": "Covert",
        "stattrak": True,
        "price": {"amount": 5000},
        "profit": 500,
        "profit_percent": 10.0,
    },
]

# Тестовые данные: предметы Dota 2
DOTA2_ITEMS = [
    {
        "title": "Genuine Bow of the Howling Wind",
        "category": "weapon",
        "rarity": "Legendary",
        "quality": "genuine",
        "hero": "Drow Ranger",
        "buyPrice": "2000",
        "profit": "200",
    },
    {
        "title": "Inscribed Arcana Tempest Helm of the Thundergod",
        "category": "head",
        "rarity": "Arcana",
        "quality": "inscribed",
        "hero": "Zeus",
        "buyPrice": "6000",
        "profit": "900",
    },
]


class TestArbitrageScanner:
    """
    Тесты для класса ArbitrageScanner.
    """

    def setup_method(self):
        """Инициализация для каждого теста."""
        self.scanner = ArbitrageScanner()

    def test_csgo_float_filter(self):
        """Тест фильтрации предметов CS:GO по float (изношенности)."""
        filters = {"float_min": 0.0, "float_max": 0.1}
        results = self.scanner._apply_game_specific_filters(CSGO_ITEMS, "csgo", filters)
        
        assert len(results) == 2
        assert "★ Butterfly Knife | Doppler" in results[0]["title"]
        assert "Neo-Noir" in results[1]["title"]

    def test_csgo_item_type_filter(self):
        """Тест фильтрации предметов CS:GO по типу предмета."""
        filters = {"item_type": "knife"}
        results = self.scanner._apply_game_specific_filters(CSGO_ITEMS, "csgo", filters)
        
        assert len(results) == 1
        assert "★ Butterfly Knife" in results[0]["title"]

    def test_csgo_stattrak_filter(self):
        """Тест фильтрации предметов CS:GO со StatTrak."""
        filters = {"stattrak": True}
        results = self.scanner._apply_game_specific_filters(CSGO_ITEMS, "csgo", filters)
        
        assert len(results) == 1
        assert "StatTrak™" in results[0]["title"]

    def test_dota2_rarity_filter(self):
        """Тест фильтрации предметов Dota 2 по редкости."""
        filters = {"rarity": "Arcana"}
        results = self.scanner._apply_game_specific_filters(DOTA2_ITEMS, "dota2", filters)
        
        assert len(results) == 1
        assert "Arcana" in results[0]["title"]

    def test_dota2_hero_filter(self):
        """Тест фильтрации предметов Dota 2 по герою."""
        filters = {"hero": "zeus"}
        results = self.scanner._apply_game_specific_filters(DOTA2_ITEMS, "dota2", filters)
        
        assert len(results) == 1
        assert "Zeus" in results[0]["title"]

    def test_multiple_filters(self):
        """Тест применения нескольких фильтров одновременно."""
        filters = {"rarity": "Covert", "float_min": 0.0, "float_max": 0.1}
        results = self.scanner._apply_game_specific_filters(CSGO_ITEMS, "csgo", filters)
        
        assert len(results) == 2
        assert "★ Butterfly Knife" in results[0]["title"]
        assert "Neo-Noir" in results[1]["title"]

    def test_no_matching_items(self):
        """Тест возврата пустого списка при отсутствии соответствующих предметов."""
        filters = {"rarity": "Ancient", "float_min": 0.0, "float_max": 0.001}
        results = self.scanner._apply_game_specific_filters(CSGO_ITEMS, "csgo", filters)
        
        assert len(results) == 0

    def test_empty_filters(self):
        """Тест возврата неизмененного списка при пустых фильтрах."""
        results = self.scanner._apply_game_specific_filters(CSGO_ITEMS, "csgo", {})
        
        assert len(results) == len(CSGO_ITEMS)
        assert results == CSGO_ITEMS
