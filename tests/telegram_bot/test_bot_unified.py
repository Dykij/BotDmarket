"""Объединенные тесты для Telegram-бота DMarket.

Этот модуль содержит тесты для проверки:
1. Основной функциональности бота
2. Обработки команд
3. Форматирования сообщений
4. Пагинации
5. Обработки ошибок API
6. Интеграции с DMarket API
"""

import os

# Импортируем необходимые модули для тестирования
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User
from telegram.ext import Application, ContextTypes, ExtBot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from telegram_bot.bot_v2 import (
    balance_command,
    format_balance_message,
    handle_error,
    help_command,
    setup_command_handlers,
    setup_error_handlers,
    start_command,
)

# Фикстуры для тестирования


@pytest.fixture
def mock_update():
    """Создает мок объекта Update для Telegram."""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.chat = update.effective_chat
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 12345
    update.message.from_user.first_name = "Test User"
    update.message.from_user.username = "testuser"
    update.message.text = "/start"
    update.message.reply_text = AsyncMock()
    update.message.reply_html = AsyncMock()
    update.callback_query = None
    return update


@pytest.fixture
def mock_context():
    """Создает мок объекта Context для Telegram."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock(spec=ExtBot)
    context.bot.send_message = AsyncMock()
    return context


@pytest.fixture
def mock_callback_query(mock_update):
    """Создает мок объекта CallbackQuery для Telegram."""
    callback_query = MagicMock(spec=CallbackQuery)
    callback_query.message = mock_update.message
    callback_query.data = "test_data"
    callback_query.from_user = mock_update.message.from_user
    callback_query.answer = AsyncMock()
    mock_update.callback_query = callback_query
    return callback_query


@pytest.fixture
def mock_application():
    """Создает мок объекта Application для Telegram."""
    app = MagicMock(spec=Application)
    app.add_handler = MagicMock()
    app.add_error_handler = MagicMock()
    return app


# Тесты основных команд


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Тестирует команду /start."""
    await start_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    args = mock_update.message.reply_text.call_args[0][0]
    assert "Добро пожаловать" in args or "Welcome" in args


@pytest.mark.asyncio
async def test_help_command(mock_update, mock_context):
    """Тестирует команду /help."""
    await help_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    args = mock_update.message.reply_text.call_args[0][0]
    assert "команды" in args or "commands" in args or "help" in args


@pytest.mark.asyncio
async def test_balance_command_without_api_keys(mock_update, mock_context):
    """Тестирует команду /balance когда API ключи не настроены."""
    with patch.dict("os.environ", {"DMARKET_PUBLIC_KEY": "", "DMARKET_SECRET_KEY": ""}):
        await balance_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0][0]
        assert "ключи API не настроены" in args or "API keys are not configured" in args


# Тесты для обработки ошибок


@pytest.mark.asyncio
async def test_handle_error(mock_update, mock_context):
    """Тестирует обработку ошибок."""
    error = Exception("Test error")
    mock_context.error = error
    await handle_error(mock_update, mock_context)
    mock_context.bot.send_message.assert_called_once()


# Тесты для форматирования сообщений


def test_format_balance_message():
    """Тестирует форматирование сообщения о балансе."""
    balance_data = {
        "usd": {"amount": 10000},  # 100 USD в центах
        "has_funds": True,
        "available_balance": 100.0,
    }
    message = format_balance_message(balance_data)
    assert "$100.00" in message or "100.00 USD" in message
    assert "доступно" in message or "available" in message


# Тесты для настройки обработчиков


def test_setup_command_handlers(mock_application):
    """Тестирует настройку обработчиков команд."""
    setup_command_handlers(mock_application)
    assert (
        mock_application.add_handler.call_count >= 3
    )  # Минимум 3 обработчика (start, help, balance)


def test_setup_error_handlers(mock_application):
    """Тестирует настройку обработчиков ошибок."""
    setup_error_handlers(mock_application)
    mock_application.add_error_handler.assert_called_once()


# Тесты для интеграции с DMarket API


@pytest.mark.asyncio
async def test_balance_command_with_mock_api(mock_update, mock_context):
    """Тестирует команду /balance с моком API."""
    mock_api = AsyncMock()
    mock_api.get_user_balance.return_value = {
        "usd": {"amount": 10000},  # 100 USD в центах
        "has_funds": True,
        "available_balance": 100.0,
    }

    with patch("src.dmarket.dmarket_api.DMarketAPI", return_value=mock_api):
        with patch.dict("os.environ", {"DMARKET_PUBLIC_KEY": "test", "DMARKET_SECRET_KEY": "test"}):
            await balance_command(mock_update, mock_context)
            mock_update.message.reply_text.assert_called_once()
            args = mock_update.message.reply_text.call_args[0][0]
            assert "$100.00" in args or "100.00 USD" in args
