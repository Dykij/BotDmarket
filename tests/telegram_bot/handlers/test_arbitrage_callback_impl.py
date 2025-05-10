"""Тесты для обработчиков callback-запросов арбитражных функций.

Этот модуль содержит тесты для функций в src.telegram_bot.handlers.arbitrage_callback_impl.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram_bot.handlers.arbitrage_callback_impl import (
    handle_best_opportunities_impl,
    handle_dmarket_arbitrage_impl,
)
from src.utils.api_error_handling import APIError


@pytest.fixture
def mock_query():
    """Создает мок для объекта callback_query."""
    query = MagicMock()
    query.edit_message_text = AsyncMock()
    query.from_user = MagicMock()
    query.from_user.id = 12345
    return query


@pytest.fixture
def mock_context():
    """Создает мок для объекта context."""
    context = MagicMock()
    context.user_data = {"current_game": "csgo"}
    return context


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_success(
    mock_execute_api_request,
    mock_query,
    mock_context,
):
    """Тестирует успешную обработку запроса арбитража с результатами."""
    # Настройка мока для возврата результатов
    mock_results = [
        {"market_hash_name": "Item1", "profit": 1.50},
        {"market_hash_name": "Item2", "profit": 2.00},
    ]
    mock_execute_api_request.return_value = mock_results

    # Мокируем пагинацию
    with patch(
        "src.telegram_bot.handlers.arbitrage_callback_impl.pagination_manager",
    ) as mock_pagination:
        # Настройка возвращаемого значения для get_page
        mock_pagination.get_page.return_value = (mock_results, 0, 1)

        # Вызываем тестируемую функцию
        await handle_dmarket_arbitrage_impl(mock_query, mock_context, "boost")

        # Проверяем вызовы методов
        mock_query.edit_message_text.assert_called()
        mock_pagination.add_items_for_user.assert_called_once_with(
            mock_query.from_user.id,
            mock_results,
            "boost",
        )
        mock_pagination.get_page.assert_called_once_with(mock_query.from_user.id)

        # Проверяем, что режим арбитража сохранен в user_data
        assert mock_context.user_data["last_arbitrage_mode"] == "boost"

        # Проверяем финальный вызов edit_message_text
        args, kwargs = mock_query.edit_message_text.call_args_list[-1]
        assert "reply_markup" in kwargs
        assert "parse_mode" in kwargs
        assert kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_pagination(
    mock_execute_api_request,
    mock_query,
    mock_context,
):
    """Тестирует пагинацию в результатах арбитража."""
    # Настройка мока для возврата результатов
    mock_results = [{"market_hash_name": f"Item{i}", "profit": i} for i in range(1, 21)]
    mock_execute_api_request.return_value = mock_results

    # Мокируем пагинацию
    with patch(
        "src.telegram_bot.handlers.arbitrage_callback_impl.pagination_manager",
    ) as mock_pagination:
        # Настройка возвращаемого значения для get_page - много страниц
        mock_pagination.get_page.return_value = (mock_results[:5], 0, 4)

        # Вызываем тестируемую функцию
        await handle_dmarket_arbitrage_impl(mock_query, mock_context, "boost")

        # Проверяем финальный вызов edit_message_text
        args, kwargs = mock_query.edit_message_text.call_args_list[-1]

        # Проверяем наличие кнопки "Следующая" в клавиатуре
        keyboard = kwargs["reply_markup"].inline_keyboard
        assert any(
            button.text == "Следующая ➡️" and "paginate:next:boost" in button.callback_data
            for row in keyboard
            for button in row
        )


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_no_results(
    mock_execute_api_request,
    mock_query,
    mock_context,
):
    """Тестирует обработку запроса арбитража без результатов."""
    # Настройка мока для возврата пустого списка
    mock_execute_api_request.return_value = []

    # Вызываем тестируемую функцию
    await handle_dmarket_arbitrage_impl(mock_query, mock_context, "boost")

    # Проверяем финальный вызов edit_message_text
    mock_query.edit_message_text.assert_called()

    # Проверяем, что вызывается format_dmarket_results с пустыми результатами
    with patch(
        "src.telegram_bot.handlers.arbitrage_callback_impl.format_dmarket_results",
    ) as mock_format:
        mock_format.return_value = "Отформатированный результат"

        # Повторный вызов функции
        await handle_dmarket_arbitrage_impl(mock_query, mock_context, "boost")

        # Проверка вызова format_dmarket_results
        mock_format.assert_called_once_with([], "boost", "csgo")


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_api_error(
    mock_execute_api_request,
    mock_query,
    mock_context,
):
    """Тестирует обработку ошибки API при запросе арбитража."""
    # Настройка мока для генерации ошибки API
    mock_execute_api_request.side_effect = APIError(
        "Rate limit exceeded",
        status_code=429,
    )

    # Вызываем тестируемую функцию
    await handle_dmarket_arbitrage_impl(mock_query, mock_context, "boost")

    # Проверяем финальный вызов edit_message_text
    args, kwargs = mock_query.edit_message_text.call_args
    message_text = args[0] if args else kwargs.get("text", "")

    # Проверяем наличие сообщения об ошибке в тексте
    assert "Превышен лимит запросов" in message_text

    # Проверяем наличие кнопки для повторной попытки
    keyboard = kwargs.get("reply_markup")
    assert keyboard is not None
    assert any(
        button.text == "🔄 Попробовать снова" and button.callback_data == "arbitrage"
        for row in keyboard.inline_keyboard
        for button in row
    )


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_authorization_error(
    mock_execute_api_request,
    mock_query,
    mock_context,
):
    """Тестирует обработку ошибки авторизации при запросе арбитража."""
    # Настройка мока для генерации ошибки авторизации
    mock_execute_api_request.side_effect = APIError(
        "Unauthorized",
        status_code=401,
    )

    # Вызываем тестируемую функцию
    await handle_dmarket_arbitrage_impl(mock_query, mock_context, "mid")

    # Проверяем финальный вызов edit_message_text
    args, kwargs = mock_query.edit_message_text.call_args
    message_text = args[0] if args else kwargs.get("text", "")

    # Проверяем наличие сообщения об ошибке авторизации в тексте
    assert "Ошибка авторизации" in message_text


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_generic_exception(
    mock_execute_api_request,
    mock_query,
    mock_context,
):
    """Тестирует обработку общей ошибки при запросе арбитража."""
    # Настройка мока для генерации общей ошибки
    mock_execute_api_request.side_effect = Exception("Unexpected error")

    # Вызываем тестируемую функцию
    await handle_dmarket_arbitrage_impl(mock_query, mock_context, "boost")

    # Проверяем финальный вызов edit_message_text
    args, kwargs = mock_query.edit_message_text.call_args
    message_text = args[0] if args else kwargs.get("text", "")

    # Проверяем наличие сообщения об общей ошибке в тексте
    assert "Неожиданная ошибка" in message_text
    assert "Unexpected error" in message_text


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.find_arbitrage_opportunities")
async def test_handle_best_opportunities_impl_success(
    mock_find_opportunities,
    mock_query,
    mock_context,
):
    """Тестирует успешный поиск лучших арбитражных возможностей."""
    # Настройка мока для возврата возможностей
    mock_opportunities = [
        {"name": "Item1", "profit": 10.5, "percentage": 5.2},
        {"name": "Item2", "profit": 8.3, "percentage": 4.1},
    ]
    mock_find_opportunities.return_value = mock_opportunities

    # Мокируем функцию форматирования
    with patch(
        "src.telegram_bot.handlers.arbitrage_callback_impl.format_best_opportunities",
    ) as mock_format:
        mock_format.return_value = "Форматированные результаты"

        # Вызываем тестируемую функцию
        await handle_best_opportunities_impl(mock_query, mock_context)

        # Проверяем вызов функции поиска с правильными параметрами
        mock_find_opportunities.assert_called_once_with(
            game="csgo",
            min_profit_percentage=5.0,
            max_items=10,
        )

        # Проверяем вызов функции форматирования
        mock_format.assert_called_once_with(mock_opportunities, "csgo")

        # Проверяем финальный вызов edit_message_text с форматированными результатами
        args, kwargs = mock_query.edit_message_text.call_args_list[-1]
        assert kwargs.get("text") == "Форматированные результаты"
        assert "reply_markup" in kwargs


@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.find_arbitrage_opportunities")
async def test_handle_best_opportunities_impl_error(
    mock_find_opportunities,
    mock_query,
    mock_context,
):
    """Тестирует обработку ошибки при поиске лучших арбитражных возможностей."""
    # Настройка мока для генерации ошибки
    mock_find_opportunities.side_effect = Exception("Search error")

    # Вызываем тестируемую функцию
    await handle_best_opportunities_impl(mock_query, mock_context)

    # Проверяем финальный вызов edit_message_text
    args, kwargs = mock_query.edit_message_text.call_args
    message_text = args[0] if args else kwargs.get("text", "")

    # Проверяем наличие сообщения об ошибке в тексте
    assert "Ошибка" in message_text
    assert "Search error" in message_text

    # Проверяем наличие кнопки для повторной попытки
    keyboard = kwargs.get("reply_markup")
    assert keyboard is not None
    assert any(
        button.text == "🔄 Попробовать снова" and button.callback_data == "arbitrage"
        for row in keyboard.inline_keyboard
        for button in row
    )
