"""Тесты для модуля arbitrage_scanner.

Этот модуль содержит комплексные тесты для функций арбитража, включая:
- Поиск арбитражных возможностей в разных режимах (low/medium/high)
- Поиск возможностей в нескольких играх одновременно
- Автоматическую торговлю предметами
- Обработку ошибок и граничных случаев
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram_bot.arbitrage_scanner import (
    auto_trade_items,
    find_arbitrage_opportunities_async,
    find_multi_game_arbitrage_opportunities,
)


@pytest.fixture
def mock_arbitrage_data() -> list[dict[str, Any]]:
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
            "profit_percent": 10.0,
            "game": "csgo",
        },
        {
            "id": "item3",
            "title": "Desert Eagle | Blaze",
            "price": {"amount": 3000},  # $30.00
            "profit": 500,  # $5.00 прибыль
            "profit_percent": 10.0,
            "game": "csgo",
        },
    ]


@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_boost")
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_mid")
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_pro")
async def test_find_arbitrage_opportunities_async_low_mode(
    mock_arbitrage_pro,
    mock_arbitrage_mid,
    mock_arbitrage_boost,
    mock_arbitrage_data,
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
    
    # Дополнительные проверки для совместимости с test_arbitrage_scanner_simple
    assert "title" in result[0]
    assert "price" in result[0]
    assert "profit" in result[0]
    assert "profit_percent" in result[0]


@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_boost")
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_mid")
@patch("src.telegram_bot.arbitrage_scanner.arbitrage_pro")
async def test_find_arbitrage_opportunities_async_medium_mode(
    mock_arbitrage_pro,
    mock_arbitrage_mid,
    mock_arbitrage_boost,
    mock_arbitrage_data,
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
    mock_arbitrage_data,
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
    mock_arbitrage_mid,
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
async def test_find_multi_game_arbitrage_opportunities(mock_arbitrage_data):
    """Тест поиска арбитражных возможностей в нескольких играх."""
    # Патчим find_arbitrage_opportunities_async напрямую для избежания проблем с event loop
    with patch("src.telegram_bot.arbitrage_scanner.find_arbitrage_opportunities_async") as mock_find_arbitrage:
        # Настраиваем асинхронный мок
        mock_find_arbitrage.side_effect = [
            mock_arbitrage_data[:2],  # csgo - первые 2 предмета
            mock_arbitrage_data[2:],  # dota2 - последний предмет
            [],  # rust - пустой результат
        ]
        
        # Патчим rate_limiter отдельно
        with patch("src.telegram_bot.arbitrage_scanner.rate_limiter") as mock_rate_limiter:
            mock_rate_limiter.wait_if_needed = AsyncMock()
            
            # Вызываем функцию
            games = ["csgo", "dota2", "rust"]
            result = await find_multi_game_arbitrage_opportunities(
                games=games,
                mode="medium",
                max_items_per_game=2,
            )
            
            # Проверяем, что функция find_arbitrage_opportunities_async была вызвана для каждой игры
            assert mock_find_arbitrage.call_count == 3
            
            # Проверяем, что параметры вызовов были правильными
            call_args_list = mock_find_arbitrage.call_args_list
            
            # Первый вызов - для csgo
            assert call_args_list[0][1]["game"] == "csgo"
            assert call_args_list[0][1]["mode"] == "medium"
            assert call_args_list[0][1]["max_items"] == 2
            
            # Второй вызов - для dota2
            assert call_args_list[1][1]["game"] == "dota2"
            assert call_args_list[1][1]["mode"] == "medium"
            assert call_args_list[1][1]["max_items"] == 2
            
            # Третий вызов - для rust
            assert call_args_list[2][1]["game"] == "rust"
            assert call_args_list[2][1]["mode"] == "medium"
            assert call_args_list[2][1]["max_items"] == 2

            # Проверяем результаты
            assert len(result["csgo"]) == 2
            assert len(result["dota2"]) == 1
            assert len(result["rust"]) == 0

            # Проверяем конкретные элементы для первой игры
            assert result["csgo"][0]["id"] == "item1"
            assert result["csgo"][1]["id"] == "item2"


@pytest.mark.asyncio
async def test_auto_trade_items(mock_arbitrage_data):
    """Тест автоматической торговли предметами."""
    # Настраиваем мок для DMarketAPI
    with patch("src.telegram_bot.arbitrage_scanner.DMarketAPI") as mock_dmarket_api:
        # Создаем мок для экземпляра API
        mock_api_instance = AsyncMock()
        mock_dmarket_api.return_value = mock_api_instance
        
        # Патчим check_user_balance для возврата положительного баланса
        with patch("src.telegram_bot.arbitrage_scanner.check_user_balance") as mock_check_balance:
            mock_check_balance.return_value = {"balance": 100.0, "has_funds": True, "error": False}
            
            # Настраиваем методы API
            mock_api_instance.buy_item = AsyncMock(return_value={"success": True})
            mock_api_instance.sell_item = AsyncMock(return_value={"success": True})
            
            # Патчим rate_limiter
            with patch("src.telegram_bot.arbitrage_scanner.rate_limiter") as mock_rate_limiter:
                mock_rate_limiter.wait_if_needed = AsyncMock()
                
                # Настраиваем тестовые данные
                items_by_game = {
                    "csgo": mock_arbitrage_data,
                }
                
                # Вызываем функцию
                purchases, sales, profit = await auto_trade_items(
                    items_by_game=items_by_game,
                    min_profit=1.0,
                    max_price=40.0,
                )
                
                # Проверяем результаты
                # Должны быть обработаны только первый и третий предметы,
                # так как второй предмет стоит $50, что выше max_price=40.0
                assert purchases == 2
                assert sales == 2
                assert profit == 7.0  # $2.00 + $5.00
                
                # Проверяем, что методы API были вызваны правильное количество раз
                assert mock_api_instance.buy_item.call_count == 2
                assert mock_api_instance.sell_item.call_count == 2
                
                # Проверяем, что методы API были вызваны с правильными параметрами
                # Первый вызов для item1
                assert mock_api_instance.buy_item.call_args_list[0][0][0] == "item1"
                
                # Второй вызов для item3 (не item2, т.к. item2 слишком дорогой)
                assert mock_api_instance.buy_item.call_args_list[1][0][0] == "item3"


@pytest.mark.asyncio
async def test_auto_trade_items_with_min_profit_filter(mock_arbitrage_data):
    """Тест автоматической торговли предметами с фильтром по минимальной прибыли."""
    # Настраиваем мок для DMarketAPI
    with patch("src.telegram_bot.arbitrage_scanner.DMarketAPI") as mock_dmarket_api:
        # Создаем мок для экземпляра API
        mock_api_instance = AsyncMock()
        mock_dmarket_api.return_value = mock_api_instance
        
        # Патчим check_user_balance для возврата положительного баланса
        with patch("src.telegram_bot.arbitrage_scanner.check_user_balance") as mock_check_balance:
            mock_check_balance.return_value = {"balance": 100.0, "has_funds": True, "error": False}
            
            # Настраиваем методы API
            mock_api_instance.buy_item = AsyncMock(return_value={"success": True})
            mock_api_instance.sell_item = AsyncMock(return_value={"success": True})
            
            # Патчим rate_limiter
            with patch("src.telegram_bot.arbitrage_scanner.rate_limiter") as mock_rate_limiter:
                mock_rate_limiter.wait_if_needed = AsyncMock()
                
                # Настраиваем тестовые данные
                items_by_game = {
                    "csgo": mock_arbitrage_data,
                }
                
                # Вызываем функцию с высоким порогом минимальной прибыли
                purchases, sales, profit = await auto_trade_items(
                    items_by_game=items_by_game,
                    min_profit=3.0,  # Отсечет первый предмет ($2.00)
                    max_price=100.0,
                )
                
                # Проверяем результаты
                # Должны быть обработаны только второй и третий предметы с прибылью >= $3.00
                assert purchases == 2
                assert sales == 2
                assert profit == 13.0  # $8.00 + $5.00
                
                # Проверяем, что методы API были вызваны с правильными параметрами
                # Первый вызов для item2 (не item1, т.к. прибыль item1 ниже порога)
                assert mock_api_instance.buy_item.call_args_list[0][0][0] == "item2"
                
                # Второй вызов для item3
                assert mock_api_instance.buy_item.call_args_list[1][0][0] == "item3"


@pytest.mark.asyncio
async def test_auto_trade_items_empty_list():
    """Тест автоматической торговли с пустым списком предметов."""
    # Настраиваем мок для DMarketAPI
    with patch("src.telegram_bot.arbitrage_scanner.DMarketAPI") as mock_dmarket_api:
        # Создаем мок для экземпляра API
        mock_api_instance = AsyncMock()
        mock_dmarket_api.return_value = mock_api_instance
        
        # Патчим check_user_balance для возврата положительного баланса
        with patch("src.telegram_bot.arbitrage_scanner.check_user_balance") as mock_check_balance:
            mock_check_balance.return_value = {"balance": 100.0, "has_funds": True, "error": False}
            
            # Настраиваем методы API
            mock_api_instance.buy_item = AsyncMock(return_value={"success": True})
            mock_api_instance.sell_item = AsyncMock(return_value={"success": True})
            
            # Патчим rate_limiter
            with patch("src.telegram_bot.arbitrage_scanner.rate_limiter") as mock_rate_limiter:
                mock_rate_limiter.wait_if_needed = AsyncMock()
                
                # Настраиваем тестовые данные - пустой список
                items_by_game = {
                    "csgo": [],
                }
                
                # Вызываем функцию
                purchases, sales, profit = await auto_trade_items(
                    items_by_game=items_by_game,
                    min_profit=1.0,
                    max_price=40.0,
                )
                
                # Проверяем результаты
                assert purchases == 0
                assert sales == 0
                assert profit == 0.0
                
                # Проверяем, что API не вызывался
                mock_api_instance.buy_item.assert_not_called()
                mock_api_instance.sell_item.assert_not_called()
