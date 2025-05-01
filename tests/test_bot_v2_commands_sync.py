"""
Тесты для команд бота в модуле bot_v2.
"""

import pytest
from unittest.mock import MagicMock, patch
from telegram import Update
from telegram.ext import CallbackContext


@pytest.fixture
def mock_update():
    """Создает мок объекта Update."""
    update = MagicMock(spec=Update)
    update.message = MagicMock()
    update.message.reply_text = MagicMock()
    update.message.reply_html = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.mention_html = MagicMock(return_value="@username")
    update.message.from_user = MagicMock()
    update.message.from_user.id = 12345
    update.message.chat_id = 12345
    
    # Эти атрибуты нужны только для callback_queries
    update.callback_query = None
    
    return update


@pytest.fixture
def mock_context():
    """Создает мок объекта Context."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}
    return context


def test_start_command(mock_update, mock_context):
    """Тест команды /start."""
    # Импортируем тестируемую функцию
    from src.telegram_bot.bot_v2 import start
    
    # Вызываем тестируемую функцию (без await, так как функция не асинхронная)
    start(mock_update, mock_context)
    
    # Проверки
    mock_update.message.reply_html.assert_called_once()
    args, kwargs = mock_update.message.reply_html.call_args
    text = args[0]
    assert "Привет" in text
    assert "DMarket" in text


def test_help_command(mock_update, mock_context):
    """Тест команды /help."""
    # Импортируем тестируемую функцию
    from src.telegram_bot.bot_v2 import help_command
    
    # Вызываем тестируемую функцию (без await, так как функция не асинхронная)
    help_command(mock_update, mock_context)
    
    # Проверки
    mock_update.message.reply_text.assert_called_once()
    args, kwargs = mock_update.message.reply_text.call_args
    text = args[0]
    assert "Доступные команды" in text
    assert "/start" in text
    assert "/help" in text
    assert "/dmarket" in text
