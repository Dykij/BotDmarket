"""
Тесты для модуля arbitrage_sales_analysis.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from src.dmarket.arbitrage_sales_analysis import (
    enhanced_arbitrage_search,
    get_sales_volume_stats,
    analyze_item_liquidity
)


@pytest.mark.asyncio
@patch("src.dmarket.arbitrage_sales_analysis.get_arbitrage_opportunities_with_sales_history")
async def test_enhanced_arbitrage_search(mock_get_opportunities):
    """Тест функции enhanced_arbitrage_search."""
    # Настройка мока
    mock_get_opportunities.return_value = [
        {
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {"amount": 1000},  # 10 USD в центах
            "profit": 200,  # 2 USD в центах
            "profit_percent": 20.0,
            "sales_per_day": 2.5
        },
        {
            "title": "AWP | Asiimov (Field-Tested)",
            "price": {"amount": 5000},  # 50 USD в центах
            "profit": 50,  # 0.5 USD в центах
            "profit_percent": 1.0,
            "sales_per_day": 1.0
        }
    ]

    # Вызываем тестируемую функцию с настройками фильтра
    api_client = AsyncMock()
    result = await enhanced_arbitrage_search(
        game="csgo",
        max_items=10,
        min_profit=1.0,
        min_profit_percent=5.0,
        min_sales_per_day=0.5,
        api_client=api_client
    )

    # Проверки
    mock_get_opportunities.assert_called_once()

    # Проверяем, что только первый предмет прошел фильтрацию (profit_percent < 5.0 для второго)
    assert result["count"] == 1
    assert result["opportunities"][0]["title"] == "AK-47 | Redline (Field-Tested)"
    assert result["opportunities"][0]["profit"] == 200
    assert result["opportunities"][0]["profit_percent"] == 20.0

    assert "game" in result
    assert "filters" in result
    assert result["filters"]["min_profit"] == 1.0
    assert result["filters"]["min_profit_percent"] == 5.0


@pytest.mark.asyncio
@patch("src.dmarket.arbitrage_sales_analysis.analyze_sales_history")
@patch("src.dmarket.arbitrage_sales_analysis.asyncio.sleep")
async def test_get_sales_volume_stats(mock_sleep, mock_analyze_history):
    """Тест функции get_sales_volume_stats."""
    # Настройка моков
    api_client = AsyncMock()
    api_client.get_market_items.return_value = {
        "objects": [
            {"title": "AK-47 | Redline (Field-Tested)"},
            {"title": "AWP | Asiimov (Field-Tested)"},
            {"title": "M4A4 | Howl (Factory New)"}
        ]
    }

    # Настраиваем возвращаемые значения для analyze_sales_history
    mock_analyze_history.side_effect = [
        {
            "item_name": "AK-47 | Redline (Field-Tested)",
            "has_data": True,
            "sales_per_day": 3.5,
            "price_trend": "up"
        },
        {
            "item_name": "AWP | Asiimov (Field-Tested)",
            "has_data": True,
            "sales_per_day": 2.0,
            "price_trend": "stable"
        },
        {
            "item_name": "M4A4 | Howl (Factory New)",
            "has_data": True,
            "sales_per_day": 0.5,
            "price_trend": "down"
        }
    ]

    # Вызываем тестируемую функцию
    result = await get_sales_volume_stats(
        game="csgo",
        top_items=3,
        api_client=api_client
    )

    # Проверки
    api_client.get_market_items.assert_called_once()
    assert mock_analyze_history.call_count == 3
    mock_sleep.assert_called_once()

    assert result["game"] == "csgo"
    assert result["count"] == 3
    assert len(result["items"]) == 3

    # Проверяем сортировку по sales_per_day (убывание)
    assert result["items"][0]["sales_per_day"] == 3.5
    assert result["items"][1]["sales_per_day"] == 2.0
    assert result["items"][2]["sales_per_day"] == 0.5

    # Проверяем summary
    assert result["summary"]["highest_sales_per_day"] == 3.5
    assert result["summary"]["average_sales_per_day"] == 2.0  # (3.5 + 2.0 + 0.5) / 3
    assert result["summary"]["up_trend_count"] == 1
    assert result["summary"]["down_trend_count"] == 1
    assert result["summary"]["stable_trend_count"] == 1


@pytest.mark.asyncio
@patch("src.dmarket.arbitrage_sales_analysis.analyze_sales_history")
async def test_analyze_item_liquidity(mock_analyze_history):
    """Тест функции analyze_item_liquidity."""
    # Настройка моков
    api_client = AsyncMock()

    # Мок для analyze_sales_history
    mock_analyze_history.return_value = {
        "item_name": "AK-47 | Redline (Field-Tested)",
        "has_data": True,
        "sales_per_day": 3.5,
        "price_trend": "stable",
        "average_price": 1500  # 15 USD в центах
    }

    # Мок для get_market_items
    api_client.get_market_items.return_value = {
        "objects": [
            {
                "price": {"USD": 1400},  # 14 USD в центах
                "suggestedPrice": {"USD": 1500}  # 15 USD в центах
            },
            {
                "price": {"USD": 1600},  # 16 USD в центах
                "suggestedPrice": {"USD": 1700}  # 17 USD в центах
            }
        ]
    }

    # Вызываем тестируемую функцию
    result = await analyze_item_liquidity(
        item_name="AK-47 | Redline (Field-Tested)",
        game="csgo",
        api_client=api_client
    )

    # Проверки
    mock_analyze_history.assert_called_once()
    api_client.get_market_items.assert_called_once()

    assert result["item_name"] == "AK-47 | Redline (Field-Tested)"
    assert result["game"] == "csgo"

    # Проверяем расчет liquidity_score:
    # +2 или +3 за sales_per_day = 3.5 (может быть 2 или 3 в зависимости от реализации)
    # +1 за offers_count = 2
    # +2 за price_trend = "stable"
    # Итого: должно быть 4, 5 или 6 баллов
    assert 4 <= result["liquidity_score"] <= 6
    # Проверяем категорию ликвидности (зависит от конкретного балла)
    assert result["liquidity_category"] in ["Высокая", "Очень высокая"]

    assert "sales_analysis" in result
    assert "market_data" in result
    assert result["market_data"]["offers_count"] == 2
    assert result["market_data"]["lowest_price"] == 1400
    assert result["market_data"]["highest_price"] == 1600


@pytest.mark.asyncio
async def test_analyze_item_liquidity_low_liquidity():
    """Тест функции analyze_item_liquidity для предмета с низкой ликвидностью."""
    # Настройка моков
    api_client = AsyncMock()

    # Патчим вызов analyze_sales_history внутри функции
    with patch("src.dmarket.arbitrage_sales_analysis.analyze_sales_history") as mock_analyze_history:
        # Мок для analyze_sales_history с низкими продажами
        mock_analyze_history.return_value = {
            "item_name": "Rare Item (Souvenir)",
            "has_data": True,
            "sales_per_day": 0.1,  # Очень низкие продажи
            "price_trend": "down",  # Нисходящий тренд
            "average_price": 5000  # 50 USD в центах
        }

        # Мок для get_market_items с малым количеством предложений
        api_client.get_market_items.return_value = {
            "objects": [
                {
                    "price": {"USD": 5000},  # 50 USD в центах
                    "suggestedPrice": {"USD": 5500}  # 55 USD в центах
                }
            ]
        }

        # Вызываем тестируемую функцию
        result = await analyze_item_liquidity(
            item_name="Rare Item (Souvenir)",
            game="csgo",
            api_client=api_client
        )

        # Проверки
        assert result["liquidity_score"] == 0  # Низкий score из-за параметров
        assert result["liquidity_category"] == "Низкая"
        assert result["market_data"]["offers_count"] == 1
