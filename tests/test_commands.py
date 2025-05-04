"""
Тесты для обработчиков команд из модуля commands.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User

from src.telegram_bot.handlers.commands import (
    start,
    help_command,
    dmarket_status,
    arbitrage_command
)


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.commands.get_localized_text")
@patch("src.telegram_bot.handlers.commands.get_arbitrage_keyboard")
async def test_start_command(mock_get_keyboard, mock_get_localized_text):
    """Тест обработки команды /start."""
    # Подготавливаем моки
    mock_keyboard = MagicMock()
    mock_get_keyboard.return_value = mock_keyboard
    mock_get_localized_text.return_value = "Тестовое приветственное сообщение"

    # Создаем моки для update и context
    user = MagicMock(spec=User)
    user.id = 12345
    user.mention_html.return_value = "<i>@test_user</i>"

    update = MagicMock(spec=Update)
    update.effective_user = user
    update.message = AsyncMock()

    context = MagicMock()

    # Вызываем тестируемую функцию
    await start(update, context)

    # Проверки
    mock_get_localized_text.assert_called_once_with(12345, "welcome", user="<i>@test_user</i>")
    mock_get_keyboard.assert_called_once()
    update.message.reply_html.assert_called_once_with(
        "Тестовое приветственное сообщение",
        reply_markup=mock_keyboard
    )


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.commands.get_localized_text")
async def test_help_command(mock_get_localized_text):
    """Тест обработки команды /help."""
    # Подготавливаем моки
    mock_get_localized_text.return_value = "Справочная информация"

    # Создаем моки для update и context
    user = MagicMock(spec=User)
    user.id = 12345

    update = MagicMock(spec=Update)
    update.effective_user = user
    update.message = AsyncMock()

    context = MagicMock()

    # Вызываем тестируемую функцию
    await help_command(update, context)

    # Проверки
    mock_get_localized_text.assert_called_once_with(12345, "help")
    update.message.reply_text.assert_called_once_with("Справочная информация")


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.dmarket_status.dmarket_status_impl")
async def test_dmarket_status(mock_dmarket_status_impl):
    """Тест обработки команды /dmarket или /status."""
    # Создаем моки для update и context
    update = MagicMock(spec=Update)
    context = MagicMock()

    # Настраиваем поведение мока
    mock_dmarket_status_impl.return_value = None

    # Вызываем тестируемую функцию
    await dmarket_status(update, context)

    # Проверки
    mock_dmarket_status_impl.assert_called_once_with(update, context)


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.commands.get_arbitrage_keyboard")
async def test_arbitrage_command(mock_get_keyboard):
    """Тест обработки команды /arbitrage."""
    # Подготавливаем моки
    mock_keyboard = MagicMock()
    mock_get_keyboard.return_value = mock_keyboard

    # Создаем моки для update и context
    update = MagicMock(spec=Update)
    update.message = AsyncMock()

    context = MagicMock()

    # Вызываем тестируемую функцию
    await arbitrage_command(update, context)

    # Проверки
    mock_get_keyboard.assert_called_once()
    update.message.reply_text.assert_called_once_with(
        "📊 Выберите режим арбитража:",
        reply_markup=mock_keyboard
    )
