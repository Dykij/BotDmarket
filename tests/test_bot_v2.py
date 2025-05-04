"""
Тесты для Telegram бота версии 2.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, User, CallbackQuery, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from src.telegram_bot.bot_v2 import (
    start, help_command, dmarket_status, button_callback_handler
)


@pytest.fixture
def mock_update():
    """Create a mock Update object for message commands."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 12345
    update.message.chat_id = 12345

    # Эти атрибуты нужны только для callback_queries
    update.callback_query = None

    return update


@pytest.fixture
def mock_callback_query():
    """Create a mock Update object with CallbackQuery for button callbacks."""
    update = MagicMock(spec=Update)
    update.message = None

    query = MagicMock(spec=CallbackQuery)
    query.data = "test_callback"
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 12345
    query.message = MagicMock(spec=Message)
    query.message.chat_id = 12345
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()

    update.callback_query = query

    return update


@pytest.fixture
def mock_context():
    """Create a mock Context object."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}
    return context


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Тестирование команды /start."""
    await start(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    assert "Добро пожаловать" in args[0]
    assert "DMarket" in args[0]


@pytest.mark.asyncio
async def test_help_command(mock_update, mock_context):
    """Тестирование команды /help."""
    await help_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    assert "Список доступных команд" in args[0]
    assert "/start" in args[0]
    assert "/help" in args[0]
    assert "/dmarket" in args[0]


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.DMARKET_PUBLIC_KEY", "test_key")
@patch("src.telegram_bot.bot_v2.DMARKET_SECRET_KEY", "test_secret")
async def test_dmarket_status_with_keys(mock_update, mock_context):
    """Тестирование команды /dmarket при наличии ключей API."""
    # Создаем мок для возвращаемого сообщения
    message_mock = AsyncMock()
    mock_update.message.reply_text.return_value = message_mock

    await dmarket_status(mock_update, mock_context)

    # Проверяем, что reply_text вызывается с правильным промежуточным сообщением
    mock_update.message.reply_text.assert_called_once_with("Проверка статуса API DMarket...")

    # Проверяем вызов edit_text на возвращенном сообщении
    message_mock.edit_text.assert_called_once()
    args, _ = message_mock.edit_text.call_args
    assert "✅ API ключи настроены!" in args[0]
    assert "API endpoint доступен" in args[0]


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.DMARKET_PUBLIC_KEY", "")
@patch("src.telegram_bot.bot_v2.DMARKET_SECRET_KEY", "")
async def test_dmarket_status_without_keys(mock_update, mock_context):
    """Тестирование команды /dmarket без ключей API."""
    # Создаем мок для возвращаемого сообщения
    message_mock = AsyncMock()
    mock_update.message.reply_text.return_value = message_mock

    await dmarket_status(mock_update, mock_context)

    # Проверяем, что reply_text вызывается с правильным промежуточным сообщением
    mock_update.message.reply_text.assert_called_once_with("Проверка статуса API DMarket...")

    # Проверяем вызов edit_text на возвращенном сообщении
    message_mock.edit_text.assert_called_once()
    args, _ = message_mock.edit_text.call_args
    assert "❌ API ключи не настроены" in args[0]
    assert "Пожалуйста, установите" in args[0]


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.get_arbitrage_keyboard")
async def test_button_callback_arbitrage(mock_get_keyboard, mock_callback_query, mock_context):
    """Тестирование обработки коллбэка для кнопки арбитража."""
    mock_callback_query.callback_query.data = "arbitrage"
    mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)

    await button_callback_handler(mock_callback_query, mock_context)

    mock_callback_query.callback_query.answer.assert_called_once()
    mock_callback_query.callback_query.edit_message_text.assert_called_once()
    mock_get_keyboard.assert_called_once()

    args, _ = mock_callback_query.callback_query.edit_message_text.call_args
    assert "Выберите режим арбитража" in args[0]


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.get_game_selection_keyboard")
async def test_button_callback_select_game(mock_get_keyboard, mock_callback_query, mock_context):
    """Тестирование обработки коллбэка для выбора игры."""
    mock_callback_query.callback_query.data = "select_game"
    mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)

    await button_callback_handler(mock_callback_query, mock_context)

    mock_callback_query.callback_query.answer.assert_called_once()
    mock_callback_query.callback_query.edit_message_text.assert_called_once()
    mock_get_keyboard.assert_called_once()

    args, _ = mock_callback_query.callback_query.edit_message_text.call_args
    assert "Выберите игру" in args[0]


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.start_auto_trading")
async def test_button_callback_auto_start(mock_start_auto, mock_callback_query, mock_context):
    """Тестирование обработки коллбэка для запуска автоматического арбитража."""
    mock_callback_query.callback_query.data = "auto_start:auto_medium"

    await button_callback_handler(mock_callback_query, mock_context)

    mock_start_auto.assert_called_once_with(
        mock_callback_query.callback_query, mock_context, "auto_medium"
    )


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.pagination_manager")
@patch("src.telegram_bot.bot_v2.show_auto_stats")
async def test_button_callback_paginate(mock_show_stats, mock_pagination_manager, mock_callback_query, mock_context):
    """Тестирование обработки коллбэка для пагинации."""
    mock_callback_query.callback_query.data = "paginate:next:auto_medium"

    await button_callback_handler(mock_callback_query, mock_context)

    # Для auto режима должен быть вызван show_auto_stats
    mock_show_stats.assert_called_once_with(
        mock_callback_query.callback_query, mock_context
    )
