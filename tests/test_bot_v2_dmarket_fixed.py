"""
Тесты для dmarket_status в модуле bot_v2.py
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


@patch("os.getenv")
def test_dmarket_status(mock_getenv, mock_update, mock_context):
    """Тест команды /dmarket."""
    # Настройка мока для os.getenv
    mock_getenv.return_value = "test_key"
    
    # Импортируем тестируемую функцию
    from src.telegram_bot.bot_v2 import dmarket_status
    
    # Вызываем тестируемую функцию
    dmarket_status(mock_update, mock_context)
    
    # Проверки
    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    text = args[0]
    assert "API работает нормально" in text
    assert "DMarket API" in text
    assert "Последнее обновление" in text
