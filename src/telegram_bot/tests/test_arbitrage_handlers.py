"""Тесты для модуля arbitrage_callback_impl.py.

Этот модуль тестирует функциональность обработчиков callback запросов для арбитража.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.telegram_bot.handlers.arbitrage_callback_impl import (
    handle_best_opportunities_impl,
    handle_dmarket_arbitrage_impl,
)


@pytest.mark.asyncio
async def test_handle_dmarket_arbitrage_impl_boost(
    mock_telegram_context,
    mock_arbitrage_functions,
):
    """Тестирует обработку запроса boost арбитража."""
    # Настраиваем запрос и контекст
    query = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user.id = 123456789

    # Подготавливаем контекст
    context = mock_telegram_context
    context.user_data = {"current_game": "csgo"}

    # Вызываем тестируемую функцию
    await handle_dmarket_arbitrage_impl(query, context, "boost")

    # Проверяем, что были вызваны нужные методы
    assert query.edit_message_text.call_count == 2  # Сначала сообщение о поиске, затем результаты
    mock_arbitrage_functions["boost"].assert_called_once_with("csgo")

    # Проверяем, что последний режим был сохранен в контексте
    assert context.user_data["last_arbitrage_mode"] == "boost"

    # Проверяем, что в результатах есть нужная информация
    message_text = query.edit_message_text.call_args_list[1][1]["text"]
    assert "Разгон баланса" in message_text
    assert "CSGO" in message_text.upper() or "CS:GO" in message_text


@pytest.mark.asyncio
async def test_handle_dmarket_arbitrage_impl_mid(
    mock_telegram_context,
    mock_arbitrage_functions,
):
    """Тестирует обработку запроса mid арбитража."""
    # Настраиваем запрос и контекст
    query = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user.id = 123456789

    # Подготавливаем контекст
    context = mock_telegram_context
    context.user_data = {"current_game": "csgo"}

    # Вызываем тестируемую функцию
    await handle_dmarket_arbitrage_impl(query, context, "mid")

    # Проверяем, что были вызваны нужные методы
    assert query.edit_message_text.call_count == 2
    mock_arbitrage_functions["mid"].assert_called_once_with("csgo")

    # Проверяем, что последний режим был сохранен в контексте
    assert context.user_data["last_arbitrage_mode"] == "mid"

    # Проверяем, что в результатах есть нужная информация
    message_text = query.edit_message_text.call_args_list[1][1]["text"]
    assert "Средний трейдер" in message_text


@pytest.mark.asyncio
async def test_handle_dmarket_arbitrage_impl_pro(
    mock_telegram_context,
    mock_arbitrage_functions,
):
    """Тестирует обработку запроса pro арбитража."""
    # Настраиваем запрос и контекст
    query = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user.id = 123456789

    # Подготавливаем контекст
    context = mock_telegram_context
    context.user_data = {"current_game": "csgo"}

    # Вызываем тестируемую функцию
    await handle_dmarket_arbitrage_impl(query, context, "pro")

    # Проверяем, что были вызваны нужные методы
    assert query.edit_message_text.call_count == 2
    mock_arbitrage_functions["pro"].assert_called_once_with("csgo")

    # Проверяем, что последний режим был сохранен в контексте
    assert context.user_data["last_arbitrage_mode"] == "pro"

    # Проверяем, что в результатах есть нужная информация
    message_text = query.edit_message_text.call_args_list[1][1]["text"]
    assert "Trade Pro" in message_text


@pytest.mark.asyncio
async def test_handle_dmarket_arbitrage_impl_api_error(mock_telegram_context):
    """Тестирует обработку ошибки API при запросе арбитража."""
    # Настраиваем запрос и контекст
    query = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user.id = 123456789

    # Подготавливаем контекст
    context = mock_telegram_context
    context.user_data = {"current_game": "csgo"}

    # Мок объекта APIError
    from src.utils.api_error_handling import APIError

    api_error = APIError("Rate limit exceeded", status_code=429)

    # Патчим функцию execute_api_request для вызова исключения
    with patch("src.utils.api_error_handling.APIError", return_value=api_error):
        with patch(
            "src.utils.dmarket_api_utils.execute_api_request",
            side_effect=APIError("Rate limit exceeded", status_code=429),
        ):

            # Вызываем тестируемую функцию
            await handle_dmarket_arbitrage_impl(query, context, "boost")

    # Проверяем, что сообщение об ошибке было отправлено
    message_text = query.edit_message_text.call_args_list[1][1]["text"]
    assert "Превышен лимит запросов" in message_text


@pytest.mark.asyncio
async def test_handle_best_opportunities_impl(
    mock_telegram_context,
    mock_arbitrage_functions,
):
    """Тестирует обработку запроса лучших возможностей."""
    # Настраиваем запрос и контекст
    query = AsyncMock()
    query.edit_message_text = AsyncMock()

    # Подготавливаем контекст
    context = mock_telegram_context
    context.user_data = {"current_game": "csgo"}

    # Мокируем функцию find_arbitrage_opportunities
    with patch(
        "src.telegram_bot.arbitrage_scanner.find_arbitrage_opportunities",
        return_value=mock_arbitrage_functions["opportunities"].return_value,
    ):

        # Вызываем тестируемую функцию
        await handle_best_opportunities_impl(query, context)

    # Проверяем, что были вызваны нужные методы
    assert query.edit_message_text.call_count == 2

    # Проверяем, что в результатах есть нужная информация
    message_text = query.edit_message_text.call_args_list[1][1]["text"]
    assert (
        "лучших арбитражных возможностей" in message_text.lower()
        or "арбитражные возможности" in message_text.lower()
    )


@pytest.mark.asyncio
async def test_handle_best_opportunities_impl_error(mock_telegram_context):
    """Тестирует обработку ошибки при запросе лучших возможностей."""
    # Настраиваем запрос и контекст
    query = AsyncMock()
    query.edit_message_text = AsyncMock()

    # Подготавливаем контекст
    context = mock_telegram_context
    context.user_data = {"current_game": "csgo"}

    # Мокируем функцию find_arbitrage_opportunities для вызова исключения
    with patch(
        "src.telegram_bot.arbitrage_scanner.find_arbitrage_opportunities",
        side_effect=Exception("Test error"),
    ):

        # Вызываем тестируемую функцию
        await handle_best_opportunities_impl(query, context)

    # Проверяем, что сообщение об ошибке было отправлено
    message_text = query.edit_message_text.call_args_list[1][1]["text"]
    assert "Ошибка" in message_text
