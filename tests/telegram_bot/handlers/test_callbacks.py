"""Тесты для модуля callbacks.py.

Этот модуль содержит тесты функций, которые являются обертками для реальных обработчиков.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from src.telegram_bot.handlers.callbacks import (
    arbitrage_callback,
    handle_best_opportunities,
    handle_dmarket_arbitrage,
)


@pytest.fixture
def mock_update():
    """Создает мок объекта Update для тестирования."""
    update = MagicMock(spec=Update)
    update.callback_query = MagicMock()
    update.callback_query.data = "arbitrage"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Создает мок объекта CallbackContext для тестирования."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}
    return context


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.callbacks.arbitrage_callback_impl")
async def test_arbitrage_callback(mock_arbitrage_impl, mock_update, mock_context):
    """Тестирует, что arbitrage_callback вызывает правильную реализацию."""
    # Настраиваем мок для возврата
    mock_arbitrage_impl.return_value = None

    # Вызываем тестируемую функцию
    await arbitrage_callback(mock_update, mock_context)

    # Проверяем, что была вызвана правильная функция с правильными аргументами
    mock_arbitrage_impl.assert_called_once_with(mock_update, mock_context)


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.callbacks.handle_dmarket_arbitrage_impl")
async def test_handle_dmarket_arbitrage(
    mock_dmarket_arbitrage_impl,
    mock_update,
    mock_context,
):
    """Тестирует, что handle_dmarket_arbitrage вызывает правильную реализацию."""
    # Настраиваем тестовые данные
    mode = "boost"
    query = mock_update.callback_query

    # Настраиваем мок для возврата
    mock_dmarket_arbitrage_impl.return_value = None

    # Вызываем тестируемую функцию
    await handle_dmarket_arbitrage(query, mock_context, mode)

    # Проверяем, что была вызвана правильная функция с правильными аргументами
    mock_dmarket_arbitrage_impl.assert_called_once_with(query, mock_context, mode)


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.callbacks.handle_best_opportunities_impl")
async def test_handle_best_opportunities(
    mock_best_opportunities_impl,
    mock_update,
    mock_context,
):
    """Тестирует, что handle_best_opportunities вызывает правильную реализацию."""
    # Настраиваем тестовые данные
    query = mock_update.callback_query

    # Настраиваем мок для возврата
    mock_best_opportunities_impl.return_value = None

    # Вызываем тестируемую функцию
    await handle_best_opportunities(query, mock_context)

    # Проверяем, что была вызвана правильная функция с правильными аргументами
    mock_best_opportunities_impl.assert_called_once_with(query, mock_context)


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.callbacks.handle_dmarket_arbitrage_impl")
async def test_handle_dmarket_arbitrage_different_modes(
    mock_dmarket_arbitrage_impl,
    mock_update,
    mock_context,
):
    """Тестирует, что handle_dmarket_arbitrage правильно передает разные режимы."""
    # Настраиваем тестовые данные
    query = mock_update.callback_query
    test_modes = ["boost", "mid", "pro"]

    # Настраиваем мок для возврата
    mock_dmarket_arbitrage_impl.return_value = None

    # Тестируем с разными режимами
    for mode in test_modes:
        # Вызываем тестируемую функцию с разными режимами
        await handle_dmarket_arbitrage(query, mock_context, mode)

        # Проверяем, что была вызвана правильная функция с правильными аргументами
        mock_dmarket_arbitrage_impl.assert_called_with(query, mock_context, mode)
