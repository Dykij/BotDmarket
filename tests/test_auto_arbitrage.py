"""
Модульные тесты для модуля автоматического арбитража.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from src.telegram_bot.auto_arbitrage import (
    format_results, 
    show_auto_stats_with_pagination, 
    handle_pagination,
    start_auto_trading,
    stop_auto_trading
)


@pytest.fixture
def mock_query():
    """Создает мок объекта callback query."""
    query = MagicMock()
    query.from_user = MagicMock()
    query.from_user.id = 12345
    query.edit_message_text = AsyncMock()
    return query


@pytest.fixture
def mock_context():
    """Создает мок объекта контекста."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}
    return context


@pytest.mark.asyncio
async def test_format_results():
    """Тест функции форматирования результатов автоарбитража."""
    items = [
        {
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {"amount": 1000},
            "profit": 100,
            "profit_percent": 10.0
        },
        {
            "title": "AWP | Asiimov (Field-Tested)",
            "price": {"amount": 3000},
            "profit": 300,
            "profit_percent": 10.0
        }
    ]
    
    result = await format_results(items, "auto_medium", "csgo")
      # Проверяем, что результат содержит заголовок
    assert "🤖 Результаты автоматического арбитража" in result
    # Проверяем, что результат содержит названия предметов
    assert "AK-47 | Redline" in result
    assert "AWP | Asiimov" in result
    # Проверяем, что результат содержит информацию о цене и прибыли
    assert "$10.00" in result  # Цена AK-47
    assert "$30.00" in result  # Цена AWP
    assert "$1.00" in result   # Прибыль AK-47
    assert "$3.00" in result   # Прибыль AWP
    assert "10.0%" in result   # Процент прибыли


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
async def test_handle_pagination_next(mock_pagination_manager, mock_query, mock_context):
    """Тест обработки пагинации - следующая страница."""
    mock_pagination_manager.next_page = MagicMock()
    
    # Мокаем функцию show_auto_stats_with_pagination
    with patch("src.telegram_bot.auto_arbitrage.show_auto_stats_with_pagination", new=AsyncMock()) as mock_show:
        await handle_pagination(mock_query, mock_context, "next", "auto_medium")
        
        # Проверяем, что был вызван метод next_page менеджера пагинации
        mock_pagination_manager.next_page.assert_called_once_with(mock_query.from_user.id)
        # Проверяем, что была вызвана функция отображения результатов
        mock_show.assert_called_once_with(mock_query, mock_context)


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
async def test_handle_pagination_prev(mock_pagination_manager, mock_query, mock_context):
    """Тест обработки пагинации - предыдущая страница."""
    mock_pagination_manager.prev_page = MagicMock()
    
    # Мокаем функцию show_auto_stats_with_pagination
    with patch("src.telegram_bot.auto_arbitrage.show_auto_stats_with_pagination", new=AsyncMock()) as mock_show:
        await handle_pagination(mock_query, mock_context, "prev", "auto_medium")
        
        # Проверяем, что был вызван метод prev_page менеджера пагинации
        mock_pagination_manager.prev_page.assert_called_once_with(mock_query.from_user.id)
        # Проверяем, что была вызвана функция отображения результатов
        mock_show.assert_called_once_with(mock_query, mock_context)


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.format_results")
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
@patch("src.telegram_bot.auto_arbitrage.InlineKeyboardMarkup")
@patch("src.telegram_bot.auto_arbitrage.InlineKeyboardButton")
@patch("src.telegram_bot.auto_arbitrage.get_back_to_arbitrage_keyboard")
async def test_show_auto_stats_with_pagination_with_items(
    mock_get_keyboard, 
    mock_button, 
    mock_markup,
    mock_pagination_manager, 
    mock_format_results, 
    mock_query, 
    mock_context
):
    """Тест отображения статистики автоарбитража с пагинацией - с данными."""
    # Настройка моков
    mock_pagination_manager.get_page.return_value = (
        [{"title": "Test Item"}], 
        0,  # current_page
        2   # total_pages
    )
    
    mock_pagination_manager.get_mode.return_value = "auto_medium"
    mock_format_results.return_value = "Форматированный текст"
    mock_markup.return_value = "keyboard_markup"
    mock_get_keyboard.return_value = "back_keyboard"
    
    # Вызов тестируемой функции
    await show_auto_stats_with_pagination(mock_query, mock_context)
    
    # Проверки
    mock_pagination_manager.get_page.assert_called_once_with(mock_query.from_user.id)
    mock_format_results.assert_called_once()
    mock_query.edit_message_text.assert_called_once()
    
    # Проверяем наличие параметров в вызове edit_message_text
    call_kwargs = mock_query.edit_message_text.call_args[1]
    assert "text" in call_kwargs
    assert "reply_markup" in call_kwargs


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.format_results")
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
@patch("src.telegram_bot.auto_arbitrage.get_back_to_arbitrage_keyboard")
async def test_show_auto_stats_with_pagination_no_items(
    mock_get_keyboard, 
    mock_pagination_manager, 
    mock_format_results, 
    mock_query, 
    mock_context
):
    """Тест отображения статистики автоарбитража с пагинацией - без данных."""
    # Настройка моков
    mock_pagination_manager.get_page.return_value = (
        [],   # пустой список предметов
        0,    # current_page
        0     # total_pages
    )
    
    mock_pagination_manager.get_mode.return_value = "auto_medium"
    mock_get_keyboard.return_value = "back_keyboard"
    
    # Вызов тестируемой функции
    await show_auto_stats_with_pagination(mock_query, mock_context)
    
    # Проверки
    mock_pagination_manager.get_page.assert_called_once_with(mock_query.from_user.id)
    mock_format_results.assert_not_called()  # Не должно быть вызова, т.к. нет предметов
    
    # Проверяем параметры вызова edit_message_text
    mock_query.edit_message_text.assert_called_once()
    call_kwargs = mock_query.edit_message_text.call_args[1]
    assert "ℹ️ Нет данных об автоматическом арбитраже" in call_kwargs["text"]
    assert call_kwargs["reply_markup"] == "back_keyboard"
