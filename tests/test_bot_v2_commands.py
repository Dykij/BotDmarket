"""
Тесты для команд бота в модуле bot_v2.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update
from telegram.ext import CallbackContext


@pytest.fixture
def mock_update():
    """Создает мок объекта Update."""
    update = MagicMock(spec=Update)
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
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


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Тест команды /start."""
    # Импортируем тестируемую функцию
    from src.telegram_bot.bot_v2 import start
    
    # Вызываем тестируемую функцию
    await start(mock_update, mock_context)
    
    # Проверки
    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    text = args[0]
    assert "Добро пожаловать" in text
    assert "DMarket" in text


@pytest.mark.asyncio
async def test_help_command(mock_update, mock_context):
    """Тест команды /help."""
    # Импортируем тестируемую функцию
    from src.telegram_bot.bot_v2 import help_command
    
    # Вызываем тестируемую функцию
    await help_command(mock_update, mock_context)
    
    # Проверки
    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    text = args[0]
    assert "Список доступных команд" in text
    assert "/start" in text
    assert "/help" in text
    assert "/dmarket" in text


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.DMARKET_PUBLIC_KEY", "test_key")
@patch("src.telegram_bot.bot_v2.DMARKET_SECRET_KEY", "test_secret")
async def test_dmarket_status_with_keys(mock_update, mock_context):
    """Тест команды /dmarket при наличии API ключей."""
    # Импортируем тестируемую функцию
    from src.telegram_bot.bot_v2 import dmarket_status
    
    # Вызываем тестируемую функцию
    await dmarket_status(mock_update, mock_context)
    
    # Проверки
    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    text = args[0]
    assert "API ключи настроены" in text


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.DMARKET_PUBLIC_KEY", "")
@patch("src.telegram_bot.bot_v2.DMARKET_SECRET_KEY", "")
async def test_dmarket_status_without_keys(mock_update, mock_context):
    """Тест команды /dmarket без API ключей."""
    # Импортируем тестируемую функцию
    from src.telegram_bot.bot_v2 import dmarket_status
    
    # Вызываем тестируемую функцию
    await dmarket_status(mock_update, mock_context)
    
    # Проверки
    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    text = args[0]
    assert "API ключи не настроены" in text
