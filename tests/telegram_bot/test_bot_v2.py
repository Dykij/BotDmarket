"""Тесты для модуля bot_v2.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import CallbackContext

from src.telegram_bot.bot_v2 import (
    arbitrage_callback,
    arbitrage_command,
    button_callback_handler,
    dmarket_status,
    help_command,
    start,
)


@pytest.fixture
def mock_update():
    """Создает мок объекта Update для тестирования."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.from_user = MagicMock(spec=User)
    update.message.chat = MagicMock(spec=Chat)
    update.message.reply_text = AsyncMock()
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Создает мок объекта CallbackContext для тестирования."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}
    return context


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Тестирует команду /start."""
    # Вызываем функцию start
    await start(mock_update, mock_context)

    # Проверяем, что был вызван reply_text
    mock_update.message.reply_text.assert_called_once()

    # Проверяем, что сообщение содержит ключевые слова
    args, kwargs = mock_update.message.reply_text.call_args
    message_text = args[0]
    assert "Добро пожаловать" in message_text
    assert "DMarket" in message_text


@pytest.mark.asyncio
async def test_help_command(mock_update, mock_context):
    """Тестирует команду /help."""
    # Вызываем функцию help_command
    await help_command(mock_update, mock_context)

    # Проверяем, что был вызван reply_text
    mock_update.message.reply_text.assert_called_once()

    # Проверяем содержимое сообщения
    args, kwargs = mock_update.message.reply_text.call_args
    message_text = args[0]
    assert "Список доступных команд" in message_text
    assert "/start" in message_text
    assert "/help" in message_text
    assert "/status" in message_text


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.DMARKET_PUBLIC_KEY", "test_key")
@patch("src.telegram_bot.bot_v2.DMARKET_SECRET_KEY", "test_secret")
async def test_dmarket_status_with_keys(mock_update, mock_context):
    """Тестирует команду /status с настроенными API ключами."""
    # Настраиваем мок для метода reply_text
    reply_message = AsyncMock()
    mock_update.message.reply_text.return_value = reply_message

    # Вызываем функцию dmarket_status
    await dmarket_status(mock_update, mock_context)

    # Проверяем, что был вызван reply_text и edit_text
    mock_update.message.reply_text.assert_called_once()
    reply_message.edit_text.assert_called_once()

    # Проверяем сообщение
    args, kwargs = reply_message.edit_text.call_args
    message_text = args[0]
    assert "API ключи настроены" in message_text


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.DMARKET_PUBLIC_KEY", "")
@patch("src.telegram_bot.bot_v2.DMARKET_SECRET_KEY", "")
async def test_dmarket_status_without_keys(mock_update, mock_context):
    """Тестирует команду /status без настроенных API ключей."""
    # Настраиваем мок для метода reply_text
    reply_message = AsyncMock()
    mock_update.message.reply_text.return_value = reply_message

    # Вызываем функцию dmarket_status
    await dmarket_status(mock_update, mock_context)

    # Проверяем сообщение
    args, kwargs = reply_message.edit_text.call_args
    message_text = args[0]
    assert "API ключи не настроены" in message_text


@pytest.mark.asyncio
async def test_arbitrage_command(mock_update, mock_context):
    """Тестирует команду /arbitrage."""
    # Вызываем функцию arbitrage_command
    await arbitrage_command(mock_update, mock_context)

    # Проверяем, что был вызван reply_text с клавиатурой
    mock_update.message.reply_text.assert_called_once()

    # Проверяем, что передан аргумент reply_markup
    args, kwargs = mock_update.message.reply_text.call_args
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_arbitrage_callback_general(mock_update, mock_context):
    """Тестирует обработку колбэка arbitrage."""
    # Настройка мока
    mock_update.callback_query.data = "arbitrage"

    # Вызываем функцию arbitrage_callback
    await arbitrage_callback(mock_update, mock_context)

    # Проверяем, что был вызван answer и edit_message_text
    mock_update.callback_query.answer.assert_called_once()
    mock_update.callback_query.edit_message_text.assert_called_once()

    # Проверяем аргументы edit_message_text
    args, kwargs = mock_update.callback_query.edit_message_text.call_args
    assert "reply_markup" in kwargs
    assert "Выберите режим арбитража" in args[0]


@pytest.mark.asyncio
async def test_button_callback_handler_arbitrage(mock_update, mock_context):
    """Тестирует обработку кнопок для арбитража."""
    # Настройка мока
    mock_update.callback_query.data = "arbitrage"

    # Мокируем функцию arbitrage_callback
    with patch("src.telegram_bot.bot_v2.arbitrage_callback") as mock_arbitrage_callback:
        # Вызываем функцию button_callback_handler
        await button_callback_handler(mock_update, mock_context)

        # Проверяем, что arbitrage_callback был вызван с правильными аргументами
        mock_arbitrage_callback.assert_called_once_with(mock_update, mock_context)
