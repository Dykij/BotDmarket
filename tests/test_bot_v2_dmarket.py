"""
Тесты для проверки функции dmarket_status в bot_v2.py
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from telegram import Update
from telegram.ext import CallbackContext


@pytest.fixture
def mock_update():
    """Создает мок объекта Update."""
    update = MagicMock(spec=Update)
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    # Мок для edit_text у возвращаемого сообщения
    fake_message = MagicMock()
    fake_message.edit_text = AsyncMock()
    update.message.reply_text.return_value = fake_message
    update._fake_message = fake_message  # для доступа в тестах
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



import pytest

@pytest.mark.asyncio
@patch("os.getenv")
async def test_dmarket_status_with_keys(mock_getenv, mock_update, mock_context):
    """Тест команды /dmarket при наличии API ключей."""
    # Настройка мока для имитации наличия API ключей
    mock_getenv.side_effect = lambda key: {
        "DMARKET_PUBLIC_KEY": "test_public_key",
        "DMARKET_SECRET_KEY": "test_secret_key",
    }.get(key)

    # Импортируем тестируемую функцию
    from src.telegram_bot.handlers.commands import dmarket_status

    # Вызываем тестируемую функцию
    await dmarket_status(mock_update, mock_context)
    # Проверяем, что был вызван edit_text с финальным статусом
    mock_update._fake_message.edit_text.assert_called()
    args, _ = mock_update._fake_message.edit_text.call_args
    text = args[0]
    # Проверяем наличие ключевых фраз (статус API и/или баланс)
    assert ("API" in text or "доступно" in text or "Авторизация" in text or "Баланс" in text)



@pytest.mark.asyncio
@patch("os.getenv")
async def test_dmarket_status_without_keys(mock_getenv, mock_update, mock_context):
    """Тест команды /dmarket без API ключей."""
    # Настройка мока для имитации отсутствия API ключей
    mock_getenv.side_effect = lambda key: {
        "DMARKET_PUBLIC_KEY": "",
        "DMARKET_SECRET_KEY": "",
    }.get(key)

    # Импортируем тестируемую функцию
    from src.telegram_bot.handlers.commands import dmarket_status

    # Вызываем тестируемую функцию
    await dmarket_status(mock_update, mock_context)
    # Проверяем, что был вызван edit_text с финальным статусом
    mock_update._fake_message.edit_text.assert_called()
    args, _ = mock_update._fake_message.edit_text.call_args
    text = args[0]
    # Проверяем наличие ключевых фраз (статус API и/или баланс)
    assert ("API" in text or "доступно" in text or "Авторизация" in text or "Баланс" in text)
