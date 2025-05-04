"""Тесты для модуля arbitrage_scanner."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, List, Any

from src.telegram_bot.arbitrage_scanner import (
    find_arbitrage_opportunities_async,
    find_multi_game_arbitrage_opportunities,
    auto_trade_items
)


@pytest.fixture
def mock_arbitrage_data() -> List[Dict[str, Any]]:
    """Создает фиктивные данные для тестирования."""
    return [
        {
            "id": "item1",
            "title": "AK-47 | Redline",
            "price": {"amount": 1000},  # $10.00
            "profit": 200,              # $2.00 прибыль
            "game": "csgo",
        },
        {
            "id": "item2",
            "title": "AWP | Asiimov",
            "price": {"amount": 5000},  # $50.00
            "profit": 800,              # $8.00 прибыль
            "game": "csgo",
        },
        {
            "id": "item3",
            "title": "Desert Eagle | Blaze",
            "price": {"amount": 3000},  # $30.00
            "profit": 500,              # $5.00 прибыль
            "game": "csgo",
        }
    ]


@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_boost")
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_mid")
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_pro")
async def test_find_arbitrage_opportunities_async_low_mode(
    mock_arbitrage_pro, 
    mock_arbitrage_mid, 
    mock_arbitrage_boost, 
    mock_arbitrage_data
):
    """Тест поиска арбитражных возможностей в режиме low."""
    # Настраиваем мок
    mock_arbitrage_boost.return_value = mock_arbitrage_data
    
    # Вызываем функцию
    result = await find_arbitrage_opportunities_async(game="csgo", mode="low", max_items=2)
    
    # Проверяем, что была вызвана правильная функция
    mock_arbitrage_boost.assert_called_once_with("csgo")
    mock_arbitrage_mid.assert_not_called()
    mock_arbitrage_pro.assert_not_called()
    
    # Проверяем результат
    assert len(result) == 2
    assert result[0]["id"] == "item1"
    assert result[1]["id"] == "item2"


@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_boost")
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_mid")
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_pro")
async def test_find_arbitrage_opportunities_async_medium_mode(
    mock_arbitrage_pro, 
    mock_arbitrage_mid, 
    mock_arbitrage_boost, 
    mock_arbitrage_data
):
    """Тест поиска арбитражных возможностей в режиме medium."""
    # Настраиваем мок
    mock_arbitrage_mid.return_value = mock_arbitrage_data
    
    # Вызываем функцию
    result = await find_arbitrage_opportunities_async(game="csgo", mode="medium", max_items=3)
    
    # Проверяем, что была вызвана правильная функция
    mock_arbitrage_boost.assert_not_called()
    mock_arbitrage_mid.assert_called_once_with("csgo")
    mock_arbitrage_pro.assert_not_called()
    
    # Проверяем результат
    assert len(result) == 3
    assert [item["id"] for item in result] == ["item1", "item2", "item3"]


@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_boost")
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_mid")
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_pro")
async def test_find_arbitrage_opportunities_async_high_mode(
    mock_arbitrage_pro, 
    mock_arbitrage_mid, 
    mock_arbitrage_boost, 
    mock_arbitrage_data
):
    """Тест поиска арбитражных возможностей в режиме high."""
    # Настраиваем мок
    mock_arbitrage_pro.return_value = mock_arbitrage_data
    
    # Вызываем функцию
    result = await find_arbitrage_opportunities_async(game="csgo", mode="high", max_items=1)
    
    # Проверяем, что была вызвана правильная функция
    mock_arbitrage_boost.assert_not_called()
    mock_arbitrage_mid.assert_not_called()
    mock_arbitrage_pro.assert_called_once_with("csgo")
    
    # Проверяем результат
    assert len(result) == 1
    assert result[0]["id"] == "item1"


@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_mid")
@patch("src.telegram_bot.arbitrage_scanner.rate_limiter")
async def test_find_arbitrage_opportunities_async_error_handling(
    mock_rate_limiter, 
    mock_arbitrage_mid
):
    """Тест обработки ошибок при поиске арбитражных возможностей."""
    # Настраиваем мок, чтобы он вызывал исключение
    mock_arbitrage_mid.side_effect = Exception("API Error")
    mock_rate_limiter.wait_if_needed = AsyncMock()
    
    # Вызываем функцию
    result = await find_arbitrage_opportunities_async(game="csgo", mode="medium", max_items=10)
    
    # Проверяем, что при ошибке функция возвращает пустой список
    assert result == []


@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.find_arbitrage_opportunities_async")
@patch("src.telegram_bot.arbitrage_scanner.rate_limiter")
async def test_find_multi_game_arbitrage_opportunities(
    mock_rate_limiter, 
    mock_find_arbitrage, 
    mock_arbitrage_data
):
    """Тест поиска арбитражных возможностей в нескольких играх."""
    # Настраиваем моки
    mock_rate_limiter.wait_if_needed = AsyncMock()
    mock_find_arbitrage.side_effect = [
        mock_arbitrage_data[:2],  # csgo - первые 2 предмета
        mock_arbitrage_data[2:],  # dota2 - последний предмет
        []  # rust - пустой результат
    ]
    
    # Вызываем функцию
    games = ["csgo", "dota2", "rust"]
    result = await find_multi_game_arbitrage_opportunities(
        games=games,
        mode="medium",
        max_items_per_game=2
    )
    
    # Проверяем, что функция find_arbitrage_opportunities_async была вызвана для каждой игры
    assert mock_find_arbitrage.call_count == 3
    
    # Проверяем результаты
    assert len(result["csgo"]) == 2
    assert len(result["dota2"]) == 1
    assert len(result["rust"]) == 0
    
    # Проверяем конкретные элементы для первой игры
    assert result["csgo"][0]["id"] == "item1"
    assert result["csgo"][1]["id"] == "item2"


@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.DMarketAPI")
@patch("src.telegram_bot.arbitrage_scanner.rate_limiter")
async def test_auto_trade_items(mock_rate_limiter, mock_dmarket_api, mock_arbitrage_data):
    """Тест автоматической торговли предметами."""
    # Настраиваем моки
    mock_api_instance = MagicMock()
    mock_dmarket_api.return_value = mock_api_instance
    mock_rate_limiter.wait_if_needed = AsyncMock()
    
    # Настраиваем тестовые данные
    items_by_game = {
        "csgo": mock_arbitrage_data
    }
    
    # Вызываем функцию
    purchases, sales, profit = await auto_trade_items(
        items_by_game=items_by_game,
        min_profit=1.0,
        max_price=40.0
    )
    
    # Проверяем результаты
    # Должны быть обработаны только первый и третий предметы,
    # так как второй предмет стоит $50, что выше max_price=40.0
    assert purchases == 2
    assert sales == 2
    assert profit == 7.0  # $2.00 + $5.00
    
    # Проверяем, что rate_limiter.wait_if_needed был вызван дважды для каждого обработанного предмета
    assert mock_rate_limiter.wait_if_needed.call_count == 4


@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.DMarketAPI")
@patch("src.telegram_bot.arbitrage_scanner.rate_limiter")
async def test_auto_trade_items_with_min_profit_filter(
    mock_rate_limiter, mock_dmarket_api, mock_arbitrage_data
):
    """Тест автоматической торговли предметами с фильтром по минимальной прибыли."""
    # Настраиваем моки
    mock_api_instance = MagicMock()
    mock_dmarket_api.return_value = mock_api_instance
    mock_rate_limiter.wait_if_needed = AsyncMock()
    
    # Настраиваем тестовые данные
    items_by_game = {
        "csgo": mock_arbitrage_data
    }
    
    # Вызываем функцию с высоким порогом минимальной прибыли
    purchases, sales, profit = await auto_trade_items(
        items_by_game=items_by_game,
        min_profit=3.0,  # Отсечет первый предмет ($2.00)
        max_price=100.0
    )
    
    # Проверяем результаты
    # Должны быть обработаны только второй и третий предметы с прибылью >= $3.00
    assert purchases == 2
    assert sales == 2
    assert profit == 13.0  # $8.00 + $5.00
