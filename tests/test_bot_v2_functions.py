"""
Модульные тесты для функции arbitrage_callback в модуле bot_v2.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, CallbackQuery
from telegram.ext import CallbackContext


@pytest.fixture
def mock_query():
    """Создает мок объекта callback query."""
    query = MagicMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


@pytest.fixture
def mock_context():
    """Создает мок объекта контекста."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}
    return context


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.format_dmarket_results")
@patch("src.telegram_bot.bot_v2.arbitrage_boost")
async def test_handle_dmarket_arbitrage_boost(mock_arbitrage_boost, mock_format, mock_query, mock_context):
    """Тест функции handle_dmarket_arbitrage для режима 'boost'."""
    # Импортируем тестируемую функцию
    from src.telegram_bot.bot_v2 import handle_dmarket_arbitrage
    
    # Настраиваем моки
    mock_arbitrage_boost.return_value = [
        {"title": "Test Item", "price": {"amount": 1000}, "profit": 100}
    ]
    mock_format.return_value = "Форматированный текст результатов"
    
    # Вызываем тестируемую функцию
    await handle_dmarket_arbitrage(mock_query, mock_context, "boost")
    
    # Проверки
    mock_arbitrage_boost.assert_called_once_with("csgo")
    mock_query.edit_message_text.assert_called()
    mock_format.assert_called()


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.format_best_opportunities")
@patch("src.telegram_bot.bot_v2.find_arbitrage_opportunities")
async def test_handle_best_opportunities(mock_find_opportunities, mock_format, mock_query, mock_context):
    """Тест функции handle_best_opportunities."""
    # Импортируем тестируемую функцию
    from src.telegram_bot.bot_v2 import handle_best_opportunities
    
    # Настраиваем моки
    mock_find_opportunities.return_value = [
        {"title": "Test Item", "buyPrice": 1000, "sellPrice": 1100, "profit": 100, "profitPercent": 10.0}
    ]
    mock_format.return_value = "Форматированный текст результатов"
    
    # Вызываем тестируемую функцию
    await handle_best_opportunities(mock_query, mock_context)
    
    # Проверки
    mock_find_opportunities.assert_called_once()
    args, kwargs = mock_find_opportunities.call_args
    assert kwargs["game"] == "csgo"
    assert kwargs["min_profit_percentage"] == 5.0
    assert kwargs["max_items"] == 10
    
    mock_format.assert_called_once()
    mock_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_help_command(mock_context):
    """Тест функции help_command."""
    # Импортируем тестируемую функцию
    from src.telegram_bot.bot_v2 import help_command
    
    # Создаем мок объекта Update
    update = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    
    # Вызываем тестируемую функцию
    await help_command(update, mock_context)
    
    # Проверки
    update.message.reply_text.assert_called_once()
    args, _ = update.message.reply_text.call_args
    text = args[0]
    assert "команды" in text.lower()
    assert "/start" in text
    assert "/help" in text
    assert "/dmarket" in text
    assert "/arbitrage" in text
