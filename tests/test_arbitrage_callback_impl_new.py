"""
Тесты для модуля arbitrage_callback_impl.py
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from telegram import CallbackQuery, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from src.telegram_bot.handlers.arbitrage_callback_impl import (
    handle_dmarket_arbitrage_impl, handle_best_opportunities_impl
)
from src.utils.api_error_handling import APIError

@pytest.mark.asyncio
@patch("src.dmarket.arbitrage.arbitrage_boost_async")
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_boost(mock_execute_api_request, mock_arbitrage_boost):
    """Тест функции handle_dmarket_arbitrage_impl для режима boost."""
    # Создаем тестовые данные
    results = [
        {"title": "Item 1", "profit": 100, "price": {"USD": 1000}},
        {"title": "Item 2", "profit": 200, "price": {"USD": 2000}}
    ]

    # Настраиваем моки
    mock_execute_api_request.return_value = results

    # Создаем мок для query и context
    query = AsyncMock(spec=CallbackQuery)
    query.from_user.id = 12345

    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}

    # Патчим форматирование результатов и клавиатуру        with patch("src.telegram_bot.pagination.pagination_manager") as mock_pagination_manager:
            with patch("src.telegram_bot.pagination.format_paginated_results") as mock_format_results:
                with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
                    # Настраиваем дополнительные моки
                    mock_pagination_manager.get_page.return_value = (results, 0, 1)
                    mock_format_results.return_value = "Formatted results"
                    mock_keyboard = MagicMock()
                    mock_keyboard.inline_keyboard = [[]]
                    mock_get_keyboard.return_value = mock_keyboard

                    # Вызываем тестируемую функцию
                    await handle_dmarket_arbitrage_impl(query, context, "boost")

                    # Проверяем вызовы функций
                    mock_execute_api_request.assert_called_once()
                    mock_pagination_manager.add_items_for_user.assert_called_once_with(12345, results, "boost")
                    mock_pagination_manager.get_page.assert_called_once()
                    mock_format_results.assert_called_once()

            # Проверяем сообщения
            assert query.edit_message_text.call_count == 2

            # Проверяем первый вызов - сообщение о поиске
            first_call = query.edit_message_text.call_args_list[0]
            assert "Поиск арбитражных возможностей" in first_call[1]["text"]

            # Проверяем последний вызов - результаты
            last_call = query.edit_message_text.call_args_list[1]
            assert "Formatted results" in last_call[1]["text"]
            assert last_call[1]["reply_markup"] == mock_keyboard

@pytest.mark.asyncio
@patch("src.dmarket.arbitrage.arbitrage_mid_async")
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_mid(mock_execute_api_request, mock_arbitrage_mid):
    """Тест функции handle_dmarket_arbitrage_impl для режима mid."""
    # Создаем тестовые данные
    results = [
        {"title": "Item 1", "profit": 100, "price": {"USD": 1000}},
        {"title": "Item 2", "profit": 200, "price": {"USD": 2000}}
    ]

    # Настраиваем моки
    mock_execute_api_request.return_value = results

    # Создаем мок для query и context
    query = AsyncMock(spec=CallbackQuery)
    query.from_user.id = 12345

    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "dota2"}

    # Патчим форматирование результатов
    with patch("src.telegram_bot.handlers.arbitrage_callback_impl.format_dmarket_results") as mock_format_results:
        with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
            # Настраиваем дополнительные моки
            mock_format_results.return_value = "Formatted results"
            mock_keyboard = MagicMock()
            mock_get_keyboard.return_value = mock_keyboard

            # Вызываем тестируемую функцию
            await handle_dmarket_arbitrage_impl(query, context, "mid")

            # Проверяем вызовы функций
            mock_format_results.assert_called_once_with(results, "mid", "dota2")

            # Проверяем сообщения
            assert query.edit_message_text.call_count == 2

            # Проверяем первый вызов - сообщение о поиске
            first_call = query.edit_message_text.call_args_list[0]
            assert "Поиск арбитражных возможностей" in first_call[1]["text"]

            # Проверяем последний вызов - результаты
            last_call = query.edit_message_text.call_args_list[1]
            assert "Formatted results" in last_call[1]["text"]
            assert last_call[1]["reply_markup"] == mock_keyboard

@pytest.mark.asyncio
@patch("src.dmarket.arbitrage.arbitrage_pro_async")
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_pro(mock_execute_api_request, mock_arbitrage_pro):
    """Тест функции handle_dmarket_arbitrage_impl для режима pro."""
    # Создаем тестовые данные
    results = [
        {"title": "Item 1", "profit": 100, "price": {"USD": 1000}},
        {"title": "Item 2", "profit": 200, "price": {"USD": 2000}}
    ]

    # Настраиваем моки
    mock_execute_api_request.return_value = results

    # Создаем мок для query и context
    query = AsyncMock(spec=CallbackQuery)
    query.from_user.id = 12345

    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "tf2"}

    # Патчим форматирование результатов
    with patch("src.telegram_bot.handlers.arbitrage_callback_impl.format_dmarket_results") as mock_format_results:
        with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
            # Настраиваем дополнительные моки
            mock_format_results.return_value = "Formatted results"
            mock_keyboard = MagicMock()
            mock_get_keyboard.return_value = mock_keyboard

            # Вызываем тестируемую функцию
            await handle_dmarket_arbitrage_impl(query, context, "pro")

            # Проверяем вызовы функций
            mock_format_results.assert_called_once_with(results, "pro", "tf2")

            # Проверяем сообщения
            assert query.edit_message_text.call_count == 2

            # Проверяем первый вызов - сообщение о поиске
            first_call = query.edit_message_text.call_args_list[0]
            assert "Поиск арбитражных возможностей" in first_call[1]["text"]

            # Проверяем последний вызов - результаты
            last_call = query.edit_message_text.call_args_list[1]
            assert "Formatted results" in last_call[1]["text"]
            assert last_call[1]["reply_markup"] == mock_keyboard

@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.format_dmarket_results")
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_no_results(mock_execute_api_request, mock_format_results):
    """Тест функции handle_dmarket_arbitrage_impl при отсутствии результатов."""
    # Настраиваем моки
    mock_execute_api_request.return_value = None
    mock_format_results.return_value = "No results found"

    # Создаем мок для query и context
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    # Патчим клавиатуру
    with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
        mock_keyboard = MagicMock()
        mock_get_keyboard.return_value = mock_keyboard

        # Вызываем тестируемую функцию
        await handle_dmarket_arbitrage_impl(query, context, "boost")

        # Проверяем вызовы функций
        mock_format_results.assert_called_once_with(None, "boost", "csgo")

        # Проверяем сообщения - вызывается дважды: для сообщения о поиске и для результатов
        assert query.edit_message_text.call_count == 2

        # Проверяем первый вызов - сообщение о поиске
        first_call = query.edit_message_text.call_args_list[0]
        assert "Поиск арбитражных возможностей" in first_call[1]["text"]

        # Проверяем последний вызов - результаты
        last_call = query.edit_message_text.call_args_list[1]
        assert "No results found" in last_call[1]["text"]
        assert last_call[1]["reply_markup"] == mock_keyboard

@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_api_error(mock_execute_api_request):
    """Тест функции handle_dmarket_arbitrage_impl при ошибке API."""
    # Настраиваем мок для вызова API с ошибкой
    mock_execute_api_request.side_effect = APIError("Rate limit exceeded", 429)

    # Создаем мок для query и context
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    # Вызываем тестируемую функцию
    await handle_dmarket_arbitrage_impl(query, context, "boost")

    # Проверяем, что сообщение об ошибке вызывается дважды
    assert query.edit_message_text.call_count == 2

    # Проверяем первый вызов - сообщение о поиске
    first_call = query.edit_message_text.call_args_list[0]
    assert "Поиск арбитражных возможностей" in first_call[1]["text"]

    # Проверяем последний вызов - сообщение об ошибке
    last_call = query.edit_message_text.call_args_list[1]
    assert "Превышен лимит запросов" in last_call[1]["text"]
    assert isinstance(last_call[1]["reply_markup"], InlineKeyboardMarkup)

@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_general_error(mock_execute_api_request):
    """Тест функции handle_dmarket_arbitrage_impl при общей ошибке."""
    # Настраиваем мок для вызова API с общей ошибкой
    mock_execute_api_request.side_effect = Exception("General error")

    # Создаем мок для query и context
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    # Вызываем тестируемую функцию
    await handle_dmarket_arbitrage_impl(query, context, "boost")

    # Проверяем, что сообщение об ошибке вызывается дважды
    assert query.edit_message_text.call_count == 2

    # Проверяем первый вызов - сообщение о поиске
    first_call = query.edit_message_text.call_args_list[0]
    assert "Поиск арбитражных возможностей" in first_call[1]["text"]

    # Проверяем последний вызов - сообщение об ошибке
    last_call = query.edit_message_text.call_args_list[1]
    assert "Неожиданная ошибка" in last_call[1]["text"]
    assert isinstance(last_call[1]["reply_markup"], InlineKeyboardMarkup)

@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.find_arbitrage_opportunities_async")
async def test_handle_best_opportunities_impl(mock_find_opportunities):
    """Тест функции handle_best_opportunities_impl."""
    # Создаем тестовые данные
    opportunities = [
        {"title": "Best Item 1", "profit": 500, "price": 10000},
        {"title": "Best Item 2", "profit": 600, "price": 20000}
    ]

    # Настраиваем мок
    mock_find_opportunities.return_value = opportunities

    # Создаем мок для query и context
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"game_filters": {"current_game": "rust"}}

    # Патчим форматирование и клавиатуру
    with patch("src.telegram_bot.handlers.arbitrage_callback_impl.format_best_opportunities") as mock_format_results:
        with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
            # Настраиваем дополнительные моки
            mock_format_results.return_value = "Best opportunities"
            mock_keyboard = MagicMock()
            mock_get_keyboard.return_value = mock_keyboard

            # Вызываем тестируемую функцию
            await handle_best_opportunities_impl(query, context)

            # Проверяем вызовы функций
            mock_find_opportunities.assert_called_once_with(
                game="rust",
                mode="medium",
                min_profit_percentage=5.0
            )
            mock_format_results.assert_called_once_with(opportunities, "rust")

            # Проверяем сообщения
            assert query.edit_message_text.call_count == 2

            # Проверяем последний вызов
            args, kwargs = query.edit_message_text.call_args
            assert "Best opportunities" in kwargs["text"]
            assert kwargs["reply_markup"] == mock_keyboard

@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.find_arbitrage_opportunities_async")
async def test_handle_best_opportunities_impl_error(mock_find_opportunities):
    """Тест функции handle_best_opportunities_impl при ошибке."""
    # Настраиваем мок для вызова с ошибкой
    mock_find_opportunities.side_effect = Exception("Opportunities search error")

    # Создаем мок для query и context
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"game_filters": {"current_game": "csgo"}}

    # Вызываем тестируемую функцию
    await handle_best_opportunities_impl(query, context)

    # Проверяем сообщения
    assert query.edit_message_text.call_count == 2

    # Проверяем последний вызов
    args, kwargs = query.edit_message_text.call_args
    assert "Ошибка при поиске" in kwargs["text"]
    assert isinstance(kwargs["reply_markup"], InlineKeyboardMarkup)
