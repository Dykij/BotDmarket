"""Тесты для функции arbitrage_callback в модуле bot_v2."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, User, CallbackQuery, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from src.telegram_bot.bot_v2 import arbitrage_callback


@pytest.fixture
def mock_query():
    """Создает мок объекта callback query."""
    query = AsyncMock(spec=CallbackQuery)
    query.data = "test_callback"
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 12345
    query.message = AsyncMock(spec=Message)
    query.message.chat_id = 12345
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()

    return query


@pytest.fixture
def mock_context():
    """Создает мок объекта контекста."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}
    return context


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.get_arbitrage_keyboard")
async def test_arbitrage_callback_arbitrage(mock_get_keyboard, mock_query, mock_context):
    """Тест обработки коллбэка для кнопки арбитража."""
    # Настраиваем мок
    mock_query.data = "arbitrage"
    mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)

    # Создаем объект Update с callback_query
    update = MagicMock(spec=Update)
    update.callback_query = mock_query

    # Вызываем тестируемую функцию
    await arbitrage_callback(update, mock_context)

    # Проверки
    mock_query.answer.assert_called_once()
    mock_query.edit_message_text.assert_called_once()
    mock_get_keyboard.assert_called_once()

    # Проверяем параметры вызова edit_message_text
    args, kwargs = mock_query.edit_message_text.call_args
    assert "Выберите режим арбитража" in kwargs.get("text", "")


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.handle_dmarket_arbitrage_impl")
async def test_arbitrage_callback_boost(mock_handle_dmarket_arbitrage, mock_query, mock_context):
    """Тест обработки коллбэка для режима 'boost'."""
    # Настраиваем мок
    mock_query.data = "arbitrage_boost"

    # Создаем объект Update с callback_query
    update = MagicMock(spec=Update)
    update.callback_query = mock_query

    # Вызываем тестируемую функцию
    await arbitrage_callback(update, mock_context)

    # Проверки
    mock_query.answer.assert_called_once()
    mock_handle_dmarket_arbitrage.assert_called_once_with(mock_query, mock_context, "boost")


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.handle_dmarket_arbitrage_impl")
async def test_arbitrage_callback_mid(mock_handle_dmarket_arbitrage, mock_query, mock_context):
    """Тест обработки коллбэка для режима 'mid'."""
    # Настраиваем мок
    mock_query.data = "arbitrage_mid"

    # Создаем объект Update с callback_query
    update = MagicMock(spec=Update)
    update.callback_query = mock_query

    # Вызываем тестируемую функцию
    await arbitrage_callback(update, mock_context)

    # Проверки
    mock_query.answer.assert_called_once()
    mock_handle_dmarket_arbitrage.assert_called_once_with(mock_query, mock_context, "mid")


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.handle_dmarket_arbitrage_impl")
async def test_arbitrage_callback_pro(mock_handle_dmarket_arbitrage, mock_query, mock_context):
    """Тест обработки коллбэка для режима 'pro'."""
    # Настраиваем мок
    mock_query.data = "arbitrage_pro"

    # Вызываем тестируемую функцию
    await arbitrage_callback(Update(0, mock_query), mock_context)

    # Проверки
    mock_query.answer.assert_called_once()
    mock_handle_dmarket_arbitrage.assert_called_once_with(mock_query, mock_context, "pro")


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.handle_best_opportunities_impl")
async def test_arbitrage_callback_best_opportunities(
    mock_handle_best_opportunities, mock_query, mock_context
):
    """Тест обработки коллбэка для 'best_opportunities'."""
    # Настраиваем мок
    mock_query.data = "best_opportunities"

    # Вызываем тестируемую функцию
    await arbitrage_callback(Update(0, mock_query), mock_context)

    # Проверки
    mock_query.answer.assert_called_once()
    mock_handle_best_opportunities.assert_called_once_with(mock_query, mock_context)


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.get_game_selection_keyboard")
async def test_arbitrage_callback_select_game(mock_get_keyboard, mock_query, mock_context):
    """Тест обработки коллбэка для выбора игры."""
    # Настраиваем мок
    mock_query.data = "select_game"
    mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)

    # Вызываем тестируемую функцию
    await arbitrage_callback(Update(0, mock_query), mock_context)

    # Проверки
    mock_query.answer.assert_called_once()
    mock_query.edit_message_text.assert_called_once()
    mock_get_keyboard.assert_called_once()

    # Проверяем параметры вызова edit_message_text
    args, kwargs = mock_query.edit_message_text.call_args
    assert "Выберите игру" in kwargs.get("text", "")


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.get_arbitrage_keyboard")
@patch("src.telegram_bot.bot_v2.GAMES", {"csgo": "CS:GO", "dota2": "Dota 2"})
async def test_arbitrage_callback_game_selection(mock_get_keyboard, mock_query, mock_context):
    """Тест обработки коллбэка для выбора конкретной игры."""
    # Настраиваем мок
    mock_query.data = "game:dota2"
    mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)

    # Вызываем тестируемую функцию
    await arbitrage_callback(Update(0, mock_query), mock_context)

    # Проверки
    mock_query.answer.assert_called_once()
    mock_query.edit_message_text.assert_called_once()
    mock_get_keyboard.assert_called_once()

    # Проверяем, что игра сохранена в контексте пользователя
    assert mock_context.user_data.get("current_game") == "dota2"

    # Проверяем параметры вызова edit_message_text
    args, kwargs = mock_query.edit_message_text.call_args
    assert "Выбрана игра: Dota 2" in kwargs.get("text", "")


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.get_auto_arbitrage_keyboard")
async def test_arbitrage_callback_auto_arbitrage(mock_get_keyboard, mock_query, mock_context):
    """Тест обработки коллбэка для автоматического арбитража."""
    # Настраиваем мок
    mock_query.data = "auto_arbitrage"
    mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)

    # Вызываем тестируемую функцию
    await arbitrage_callback(Update(0, mock_query), mock_context)

    # Проверки
    mock_query.answer.assert_called_once()
    mock_query.edit_message_text.assert_called_once()
    mock_get_keyboard.assert_called_once()

    # Проверяем параметры вызова edit_message_text
    args, kwargs = mock_query.edit_message_text.call_args
    assert "автоматического арбитража" in kwargs.get("text", "")
