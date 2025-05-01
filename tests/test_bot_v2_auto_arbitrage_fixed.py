"""
Тесты для функций автоматического арбитража в модуле auto_arbitrage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, CallbackQuery, InlineKeyboardMarkup
from telegram.ext import CallbackContext


@pytest.fixture
def mock_query():
    """Создает мок объекта callback query."""
    query = MagicMock(spec=CallbackQuery)
    query.data = "test_callback"
    query.from_user = MagicMock()
    query.from_user.id = 12345
    query.message = MagicMock()
    query.message.chat_id = 12345
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    
    return query


@pytest.fixture
def mock_context():
    """Создает мок объекта контекста."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}
    return context


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
@patch("src.telegram_bot.auto_arbitrage.show_auto_stats_with_pagination")
async def test_handle_pagination_next(mock_show_stats, mock_pagination_manager, mock_query, mock_context):
    """Тест функции для обработки пагинации - следующая страница."""
    # Импортируем функцию из auto_arbitrage
    from src.telegram_bot.auto_arbitrage import handle_pagination
    
    # Вызов тестируемой функции
    await handle_pagination(mock_query, mock_context, "next", "auto_medium")
    
    # Проверки
    mock_pagination_manager.next_page.assert_called_once_with(12345)
    mock_show_stats.assert_called_once_with(mock_query, mock_context)


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
@patch("src.telegram_bot.auto_arbitrage.show_auto_stats_with_pagination")
async def test_handle_pagination_prev(mock_show_stats, mock_pagination_manager, mock_query, mock_context):
    """Тест функции для обработки пагинации - предыдущая страница."""
    # Импортируем функцию из auto_arbitrage
    from src.telegram_bot.auto_arbitrage import handle_pagination
    
    # Вызов тестируемой функции
    await handle_pagination(mock_query, mock_context, "prev", "auto_medium")
    
    # Проверки
    mock_pagination_manager.prev_page.assert_called_once_with(12345)
    mock_show_stats.assert_called_once_with(mock_query, mock_context)


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.format_results")
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
@patch("src.telegram_bot.auto_arbitrage.InlineKeyboardMarkup")
async def test_show_auto_stats_with_items(mock_markup, mock_pagination_manager, mock_format, mock_query, mock_context):
    """Тест функции показа статистики автоарбитража с данными."""
    # Импортируем функцию из auto_arbitrage
    from src.telegram_bot.auto_arbitrage import show_auto_stats_with_pagination
    
    # Настройка моков
    mock_pagination_manager.get_page.return_value = (
        [{"title": "Test Item", "price": {"amount": 1000}, "profit": 100}],  # items
        0,  # current_page
        2   # total_pages
    )
    
    mock_pagination_manager.get_mode.return_value = "auto_medium"
    mock_format.return_value = "Форматированный текст"
    mock_markup.return_value = MagicMock()
    
    # Вызов тестируемой функции
    await show_auto_stats_with_pagination(mock_query, mock_context)
    
    # Проверки
    mock_pagination_manager.get_page.assert_called_once_with(12345)
    mock_pagination_manager.get_mode.assert_called_once_with(12345)
    mock_format.assert_called_once()
    mock_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.get_back_to_arbitrage_keyboard")
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
async def test_show_auto_stats_no_items(mock_pagination_manager, mock_get_keyboard, mock_query, mock_context):
    """Тест функции показа статистики автоарбитража без данных."""
    # Импортируем функцию из auto_arbitrage
    from src.telegram_bot.auto_arbitrage import show_auto_stats_with_pagination
    
    # Настройка моков
    mock_pagination_manager.get_page.return_value = (
        [],  # items
        0,   # current_page
        0    # total_pages
    )
    
    mock_pagination_manager.get_mode.return_value = "auto_medium"
    mock_get_keyboard.return_value = MagicMock()
    
    # Вызов тестируемой функции
    await show_auto_stats_with_pagination(mock_query, mock_context)
    
    # Проверки
    mock_pagination_manager.get_page.assert_called_once_with(12345)
    mock_query.edit_message_text.assert_called_once()
    # Проверяем, что текст содержит сообщение об отсутствии данных
    args, kwargs = mock_query.edit_message_text.call_args
    assert "Нет данных" in kwargs.get("text", "")
