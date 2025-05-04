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
    message_mock = MagicMock()

    # Настраиваем асинхронный мок для reply_text
    async def async_reply_text(*args, **kwargs):
        return message_mock

    update.message.reply_text = MagicMock(side_effect=async_reply_text)
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


@pytest.mark.asyncio
@patch("os.getenv")
async def test_dmarket_status(mock_getenv, mock_update, mock_context):
    """Тест команды /dmarket."""
    # Настройка мока для os.getenv
    mock_getenv.return_value = "test_key"

    # Сброс счетчиков вызовов
    mock_update.message.reply_text.reset_mock()

    # Создаем мок-объект сообщения для возврата из reply_text
    message_mock = MagicMock()
    async def async_edit_text(*args, **kwargs):
        return None
    message_mock.edit_text = MagicMock(side_effect=async_edit_text)

    # Настраиваем reply_text возвращать наш мок
    async def async_reply(*args, **kwargs):
        return message_mock
    mock_update.message.reply_text = MagicMock(side_effect=async_reply)

    # Импортируем тестируемую функцию
    from src.telegram_bot.bot_v2 import dmarket_status

    # Вызываем тестируемую функцию
    await dmarket_status(mock_update, mock_context)

    # Проверки
    mock_update.message.reply_text.assert_called_once_with("Проверка статуса API DMarket...")
    message_mock.edit_text.assert_called_once()
    args, _ = message_mock.edit_text.call_args
    text = args[0]
    assert "✅ API ключи настроены!" in text
    assert "API endpoint доступен" in text
