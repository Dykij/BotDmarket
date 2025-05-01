"""
Тесты для проверки функции dmarket_status в bot_v2.py
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


@patch("src.telegram_bot.bot_v2.os.getenv")
def test_dmarket_status_with_keys(mock_getenv, mock_update, mock_context):
    """Тест команды /dmarket при наличии API ключей."""
    # Настройка мока для имитации наличия API ключей
    mock_getenv.side_effect = lambda key: {
        "DMARKET_PUBLIC_KEY": "test_public_key",
        "DMARKET_SECRET_KEY": "test_secret_key",
    }.get(key)
    
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


@patch("src.telegram_bot.bot_v2.os.getenv")
def test_dmarket_status_without_keys(mock_getenv, mock_update, mock_context):
    """Тест команды /dmarket без API ключей."""
    # Настройка мока для имитации отсутствия API ключей
    mock_getenv.side_effect = lambda key: {
        "DMARKET_PUBLIC_KEY": "",
        "DMARKET_SECRET_KEY": "",
    }.get(key)
    
    # Импортируем тестируемую функцию
    from src.telegram_bot.bot_v2 import dmarket_status
    
    # Вызываем тестируемую функцию
    dmarket_status(mock_update, mock_context)
      # Проверки
    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    text = args[0]
    assert "API работает нормально" in text
