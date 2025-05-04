"""
Tests for the arbitrage callback implementation module.
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
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.format_dmarket_results")
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_no_results(mock_execute_api_request, mock_format_results):
    """Test handle_dmarket_arbitrage_impl function when there are no results."""
    # Configure mocks
    mock_execute_api_request.return_value = None
    mock_format_results.return_value = "No results found"

    # Create mock for query and context
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    # Patch keyboard
    with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
        mock_keyboard = MagicMock()
        mock_get_keyboard.return_value = mock_keyboard

        # Call the function being tested
        await handle_dmarket_arbitrage_impl(query, context, "boost")

        # Verify function calls
        mock_format_results.assert_called_once_with(None, "boost", "csgo")

        # Verify messages - called twice: search message and results
        assert query.edit_message_text.call_count == 2

        # Check first call - search message
        first_call = query.edit_message_text.call_args_list[0]
        assert "Поиск арбитражных возможностей" in first_call[1]["text"]

        # Check last call - results
        last_call = query.edit_message_text.call_args_list[1]
        assert "No results found" in last_call[1]["text"]
        assert last_call[1]["reply_markup"] == mock_keyboard

@pytest.mark.asyncio
@patch("src.dmarket.arbitrage.arbitrage_boost_async")
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_boost(mock_execute_api_request, mock_arbitrage_boost):
    """Test for the handle_dmarket_arbitrage_impl function in boost mode."""
    # Create test data
    results = [
        {"title": "Item 1", "profit": 100, "price": {"USD": 1000}},
        {"title": "Item 2", "profit": 200, "price": {"USD": 2000}}
    ]

    # Configure mocks
    mock_execute_api_request.return_value = results

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    query.from_user.id = 12345

    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}

    # Patch functions used inside handle_dmarket_arbitrage_impl
    with patch("src.telegram_bot.pagination.pagination_manager") as mock_pagination_manager:
        with patch("src.telegram_bot.pagination.format_paginated_results") as mock_format_results:
            with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
                # Configure additional mocks
                mock_pagination_manager.get_page.return_value = (results, 0, 1)
                mock_format_results.return_value = "Formatted results"
                mock_keyboard = MagicMock()
                mock_keyboard.inline_keyboard = [[]]
                mock_get_keyboard.return_value = mock_keyboard

                # Call the function being tested
                await handle_dmarket_arbitrage_impl(query, context, "boost")

                # Verify function calls
                mock_execute_api_request.assert_called_once()
                mock_pagination_manager.add_items_for_user.assert_called_once_with(12345, results, "boost")
                mock_pagination_manager.get_page.assert_called_once()
                mock_format_results.assert_called_once()

                # Verify messages
                assert query.edit_message_text.call_count == 2

                # Check first call - search message
                first_call = query.edit_message_text.call_args_list[0]
                assert "Поиск арбитражных возможностей" in first_call[1]["text"]

                # Check last call - results
                last_call = query.edit_message_text.call_args_list[1]
                assert "Formatted results" in last_call[1]["text"]

@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_api_error(mock_execute_api_request):
    """Test handle_dmarket_arbitrage_impl function when API error occurs."""
    # Configure mock to raise an APIError
    mock_execute_api_request.side_effect = APIError("Rate limit exceeded", 429)

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    # Call the function being tested
    await handle_dmarket_arbitrage_impl(query, context, "boost")

    # Verify messages - called twice: search message and error
    assert query.edit_message_text.call_count == 2

    # Check first call - search message
    first_call = query.edit_message_text.call_args_list[0]
    assert "Поиск арбитражных возможностей" in first_call[1]["text"]

    # Check last call - error message
    last_call = query.edit_message_text.call_args_list[1]
    assert "Превышен лимит запросов" in last_call[1]["text"]
    assert isinstance(last_call[1]["reply_markup"], InlineKeyboardMarkup)

@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_general_error(mock_execute_api_request):
    """Test handle_dmarket_arbitrage_impl function when a general error occurs."""
    # Configure mock to raise a generic exception
    mock_execute_api_request.side_effect = Exception("General error")

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    # Call the function being tested
    await handle_dmarket_arbitrage_impl(query, context, "boost")

    # Verify messages - called twice: search message and error
    assert query.edit_message_text.call_count == 2

    # Check first call - search message
    first_call = query.edit_message_text.call_args_list[0]
    assert "Поиск арбитражных возможностей" in first_call[1]["text"]

    # Check last call - error message
    last_call = query.edit_message_text.call_args_list[1]
    assert "Неожиданная ошибка" in last_call[1]["text"]
    assert isinstance(last_call[1]["reply_markup"], InlineKeyboardMarkup)

@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.find_arbitrage_opportunities", create=True)
async def test_handle_best_opportunities_impl(mock_find_opportunities):
    """Test handle_best_opportunities_impl function."""
    # Create test data
    opportunities = [
        {"title": "Best Item 1", "profit": 500, "price": 10000},
        {"title": "Best Item 2", "profit": 600, "price": 20000}
    ]

    # Configure mock
    mock_find_opportunities.return_value = opportunities

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"game_filters": {"current_game": "rust"}}

    # Patch formatting and keyboard functions
    with patch("src.telegram_bot.handlers.arbitrage_callback_impl.format_best_opportunities") as mock_format_results:
        with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
            # Configure additional mocks
            mock_format_results.return_value = "Best opportunities"
            mock_keyboard = MagicMock()
            mock_get_keyboard.return_value = mock_keyboard

            # Call the function being tested
            await handle_best_opportunities_impl(query, context)

            # Verify function calls
            mock_find_opportunities.assert_called_once_with(
                game="csgo",
                min_profit_percentage=5.0,
                max_items=10
            )
            mock_format_results.assert_called_once_with(opportunities, "csgo")

            # Verify messages
            assert query.edit_message_text.call_count == 2

            # Check first call - search message
            first_call = query.edit_message_text.call_args_list[0]
            assert "Поиск лучших" in first_call[1]["text"]

            # Check last call - results
            last_call = query.edit_message_text.call_args_list[1]
            assert "Best opportunities" in last_call[1]["text"]
            assert last_call[1]["reply_markup"] == mock_keyboard

@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.find_arbitrage_opportunities", create=True)
async def test_handle_best_opportunities_impl_error(mock_find_opportunities):
    """Test handle_best_opportunities_impl function when an error occurs."""
    # Configure mock to raise an exception
    mock_find_opportunities.side_effect = Exception("Find opportunities error")

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"game_filters": {"current_game": "csgo"}}

    # Call the function being tested
    await handle_best_opportunities_impl(query, context)

    # Verify messages - called twice: search message and error
    assert query.edit_message_text.call_count == 2

    # Check first call - search message
    first_call = query.edit_message_text.call_args_list[0]
    assert "Поиск лучших" in first_call[1]["text"]

    # Check last call - error message
    last_call = query.edit_message_text.call_args_list[1]
    assert "Ошибка при поиске" in last_call[1]["text"]
    assert isinstance(last_call[1]["reply_markup"], InlineKeyboardMarkup)

@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_no_user_data(mock_execute_api_request):
    """Test handle_dmarket_arbitrage_impl function when context has no user_data attribute."""
    # Create test data
    results = [{"title": "Item", "profit": 100, "price": {"USD": 1000}}]
    mock_execute_api_request.return_value = results

    # Create query and context mocks, but don't add user_data to context
    query = AsyncMock(spec=CallbackQuery)
    query.from_user.id = 12345
    context = MagicMock(spec=CallbackContext)
    delattr(context, 'user_data')  # Remove user_data attribute

    # Patch functions used inside handle_dmarket_arbitrage_impl
    with patch("src.telegram_bot.pagination.pagination_manager") as mock_pagination_manager:
        with patch("src.telegram_bot.pagination.format_paginated_results") as mock_format_results:
            with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
                # Configure additional mocks
                mock_pagination_manager.get_page.return_value = (results, 0, 1)
                mock_format_results.return_value = "Formatted results"
                mock_keyboard = MagicMock()
                mock_keyboard.inline_keyboard = [[]]
                mock_get_keyboard.return_value = mock_keyboard

                # Call the function being tested
                await handle_dmarket_arbitrage_impl(query, context, "boost")

                # Verify function adds user_data
                assert hasattr(context, 'user_data')
                assert context.user_data["last_arbitrage_mode"] == "boost"

@pytest.mark.asyncio
async def test_arbitrage_callback_impl():
    """Test the arbitrage_callback_impl function."""
    from src.telegram_bot.handlers.arbitrage_callback_impl import arbitrage_callback_impl

    # Create mock for update and context
    update = AsyncMock()
    context = MagicMock()

    # Call the function - it's just a stub so it should return None
    result = await arbitrage_callback_impl(update, context)

    # Verify the function was called without error
    assert result is None

@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_auth_error(mock_execute_api_request):
    """Test API auth error (401) handling in handle_dmarket_arbitrage_impl."""
    # Configure mock to raise an auth error
    mock_execute_api_request.side_effect = APIError("Auth failed", 401)

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    # Call the function being tested
    await handle_dmarket_arbitrage_impl(query, context, "boost")

    # Verify error message
    assert query.edit_message_text.call_count == 2
    last_call = query.edit_message_text.call_args_list[1]
    assert "Ошибка авторизации" in last_call[1]["text"]
    assert isinstance(last_call[1]["reply_markup"], InlineKeyboardMarkup)

@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_not_found_error(mock_execute_api_request):
    """Test not found error (404) handling in handle_dmarket_arbitrage_impl."""
    # Configure mock to raise a not found error
    mock_execute_api_request.side_effect = APIError("Not found", 404)

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    # Call the function being tested
    await handle_dmarket_arbitrage_impl(query, context, "boost")

    # Verify error message
    assert query.edit_message_text.call_count == 2
    last_call = query.edit_message_text.call_args_list[1]
    assert "данные не найдены" in last_call[1]["text"]
    assert isinstance(last_call[1]["reply_markup"], InlineKeyboardMarkup)

@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_server_error(mock_execute_api_request):
    """Test server error (500+) handling in handle_dmarket_arbitrage_impl."""
    # Configure mock to raise a server error
    mock_execute_api_request.side_effect = APIError("Server error", 500)

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    # Call the function being tested
    await handle_dmarket_arbitrage_impl(query, context, "boost")

    # Verify error message
    assert query.edit_message_text.call_count == 2
    last_call = query.edit_message_text.call_args_list[1]
    assert "Сервер DMarket временно недоступен" in last_call[1]["text"]
    assert isinstance(last_call[1]["reply_markup"], InlineKeyboardMarkup)

@pytest.mark.asyncio
@patch("src.dmarket.arbitrage.arbitrage_boost_async")
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_pagination(mock_execute_api_request, mock_arbitrage_boost):
    """Test pagination functionality in handle_dmarket_arbitrage_impl."""
    # Create test data - many items to trigger pagination
    results = [{"title": f"Item {i}", "profit": i*100, "price": {"USD": i*1000}} for i in range(1, 15)]

    # Configure mocks
    mock_execute_api_request.return_value = results

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    query.from_user.id = 12345
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}

    # Patch functions used inside handle_dmarket_arbitrage_impl
    with patch("src.telegram_bot.pagination.pagination_manager") as mock_pagination_manager:
        with patch("src.telegram_bot.pagination.format_paginated_results") as mock_format_results:
            with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
                # Configure additional mocks
                # Return results with pagination info (current page 0, total pages 2)
                mock_pagination_manager.get_page.return_value = (results[:10], 0, 2)
                mock_format_results.return_value = "Paginated results"
                mock_keyboard = MagicMock()
                mock_keyboard.inline_keyboard = [[]]
                mock_get_keyboard.return_value = mock_keyboard

                # Call the function being tested
                await handle_dmarket_arbitrage_impl(query, context, "boost")

                # Verify pagination functions were called
                mock_pagination_manager.add_items_for_user.assert_called_once_with(12345, results, "boost")

                # Verify keyboard with pagination buttons was created
                # The keyboard creation happens in lines 59-75
                last_call = query.edit_message_text.call_args_list[1]
                # Check the InlineKeyboardMarkup was passed
                assert isinstance(last_call[1]["reply_markup"], InlineKeyboardMarkup)

@pytest.mark.asyncio
@patch("src.dmarket.arbitrage.arbitrage_boost_async")
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_first_page(mock_execute_api_request, mock_arbitrage_boost):
    """Test pagination when on first page."""
    # Create test data - many items to trigger pagination
    results = [{"title": f"Item {i}", "profit": i*100, "price": {"USD": i*1000}} for i in range(1, 15)]

    # Configure mocks
    mock_execute_api_request.return_value = results

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    query.from_user.id = 12345
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}

    # Patch functions used inside handle_dmarket_arbitrage_impl
    with patch("src.telegram_bot.pagination.pagination_manager") as mock_pagination_manager:
        with patch("src.telegram_bot.pagination.format_paginated_results") as mock_format_results:
            with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
                # Set current_page to 0 to test the pagination when at first page
                mock_pagination_manager.get_page.return_value = (results[:5], 0, 3)
                mock_format_results.return_value = "First page results"
                mock_keyboard = MagicMock()
                mock_keyboard.inline_keyboard = [[]]
                mock_get_keyboard.return_value = mock_keyboard

                # Call the function being tested
                await handle_dmarket_arbitrage_impl(query, context, "boost")

                # Verify function calls
                mock_execute_api_request.assert_called_once()
                mock_pagination_manager.add_items_for_user.assert_called_once_with(12345, results, "boost")
                mock_pagination_manager.get_page.assert_called_once()
                mock_format_results.assert_called_once()

                # Verify messages
                assert query.edit_message_text.call_count == 2

                # Check first call - search message
                first_call = query.edit_message_text.call_args_list[0]
                assert "Поиск арбитражных возможностей" in first_call[1]["text"]

                # Check last call - results
                last_call = query.edit_message_text.call_args_list[1]
                assert "First page results" in last_call[1]["text"]

@pytest.mark.asyncio
@patch("src.dmarket.arbitrage.arbitrage_pro_async")
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_pro_mode(mock_execute_api_request, mock_arbitrage_pro):
    """Test handle_dmarket_arbitrage_impl function in pro mode."""
    # Create test data
    results = [{"title": "Item 1", "profit": 100, "price": {"USD": 1000}}]

    # Configure mocks
    mock_execute_api_request.return_value = results

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    query.from_user.id = 12345
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}

    # Patch functions used inside handle_dmarket_arbitrage_impl
    with patch("src.telegram_bot.pagination.pagination_manager") as mock_pagination_manager:
        with patch("src.telegram_bot.pagination.format_paginated_results") as mock_format_results:
            with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
                # Configure additional mocks
                mock_pagination_manager.get_page.return_value = (results, 0, 1)
                mock_format_results.return_value = "Formatted results"
                mock_keyboard = MagicMock()
                mock_keyboard.inline_keyboard = [[]]
                mock_get_keyboard.return_value = mock_keyboard

                # Call the function with pro mode
                await handle_dmarket_arbitrage_impl(query, context, "pro")

                # Verify function calls
                mock_execute_api_request.assert_called_once()

@pytest.mark.asyncio
@patch("src.dmarket.arbitrage.arbitrage_mid_async")
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_mid_mode(mock_execute_api_request, mock_arbitrage_mid):
    """Test handle_dmarket_arbitrage_impl function in mid mode."""
    # Create test data
    results = [{"title": "Item 1", "profit": 100, "price": {"USD": 1000}}]

    # Configure mocks
    mock_execute_api_request.return_value = results

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    query.from_user.id = 12345
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}

    # Patch functions used inside handle_dmarket_arbitrage_impl
    with patch("src.telegram_bot.pagination.pagination_manager") as mock_pagination_manager:
        with patch("src.telegram_bot.pagination.format_paginated_results") as mock_format_results:
            with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
                # Configure additional mocks
                mock_pagination_manager.get_page.return_value = (results, 0, 1)
                mock_format_results.return_value = "Formatted results"
                mock_keyboard = MagicMock()
                mock_keyboard.inline_keyboard = [[]]
                mock_get_keyboard.return_value = mock_keyboard

                # Call the function with mid mode
                await handle_dmarket_arbitrage_impl(query, context, "mid")

                # Verify function calls
                mock_execute_api_request.assert_called_once()

@pytest.mark.asyncio
@patch("src.telegram_bot.arbitrage_scanner.find_arbitrage_opportunities", create=True)
async def test_handle_best_opportunities_impl_custom_game(mock_find_opportunities):
    """Test handle_best_opportunities_impl with a custom game."""
    # Create test data
    opportunities = [{"title": "Custom Item", "profit": 300, "price": 5000}]

    # Configure mock
    mock_find_opportunities.return_value = opportunities

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "dota2"}  # Different game

    # Patch functions
    with patch("src.telegram_bot.handlers.arbitrage_callback_impl.format_best_opportunities") as mock_format_results:
        with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
            # Configure additional mocks
            mock_format_results.return_value = "Custom game results"
            mock_keyboard = MagicMock()
            mock_get_keyboard.return_value = mock_keyboard

            # Call the function being tested
            await handle_best_opportunities_impl(query, context)

            # Verify function calls with the custom game
            mock_find_opportunities.assert_called_once_with(
                game="dota2",  # This should cover line 136
                min_profit_percentage=5.0,
                max_items=10
            )
            mock_format_results.assert_called_once_with(opportunities, "dota2")

            # Verify messages
            assert query.edit_message_text.call_count == 2

            # Check first call - search message
            first_call = query.edit_message_text.call_args_list[0]
            assert "Поиск лучших" in first_call[1]["text"]

            # Check last call - results
            last_call = query.edit_message_text.call_args_list[1]
            assert "Custom game results" in last_call[1]["text"]
            assert last_call[1]["reply_markup"] == mock_keyboard

@pytest.mark.asyncio
@patch("src.dmarket.arbitrage.arbitrage_boost_async")
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_last_page(mock_execute_api_request, mock_arbitrage_boost):
    """Test pagination when on last page."""
    # Create test data - many items to trigger pagination
    results = [{"title": f"Item {i}", "profit": i*100, "price": {"USD": i*1000}} for i in range(1, 15)]

    # Configure mocks
    mock_execute_api_request.return_value = results

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    query.from_user.id = 12345
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}

    # Patch functions used inside handle_dmarket_arbitrage_impl
    with patch("src.telegram_bot.pagination.pagination_manager") as mock_pagination_manager:
        with patch("src.telegram_bot.pagination.format_paginated_results") as mock_format_results:
            with patch("src.telegram_bot.handlers.arbitrage_callback_impl.get_arbitrage_keyboard") as mock_get_keyboard:
                # Set current_page to be the last page (2 of 3 pages, zero-indexed)
                mock_pagination_manager.get_page.return_value = (results[10:], 2, 3)
                mock_format_results.return_value = "Last page results"
                mock_keyboard = MagicMock()
                mock_keyboard.inline_keyboard = [[]]
                mock_get_keyboard.return_value = mock_keyboard

                # Call the function being tested
                await handle_dmarket_arbitrage_impl(query, context, "boost")

                # Verify function calls
                mock_execute_api_request.assert_called_once()
                mock_pagination_manager.add_items_for_user.assert_called_once_with(12345, results, "boost")
                mock_pagination_manager.get_page.assert_called_once()
                mock_format_results.assert_called_once()

                # Verify messages
                assert query.edit_message_text.call_count == 2

                # Check first call - search message
                first_call = query.edit_message_text.call_args_list[0]
                assert "Поиск арбитражных возможностей" in first_call[1]["text"]

                # Check last call - results
                last_call = query.edit_message_text.call_args_list[1]
                assert "Last page results" in last_call[1]["text"]

@pytest.mark.asyncio
@patch("src.telegram_bot.handlers.arbitrage_callback_impl.execute_api_request")
async def test_handle_dmarket_arbitrage_impl_other_api_error(mock_execute_api_request):
    """Test handling of other API errors in handle_dmarket_arbitrage_impl."""
    # Configure mock to raise an API error with non-standard code
    mock_execute_api_request.side_effect = APIError("Custom API error", 403)

    # Create query and context mocks
    query = AsyncMock(spec=CallbackQuery)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    # Call the function being tested
    await handle_dmarket_arbitrage_impl(query, context, "boost")

    # Verify error message for custom error
    assert query.edit_message_text.call_count == 2
    last_call = query.edit_message_text.call_args_list[1]
    assert "Ошибка DMarket API" in last_call[1]["text"]
    assert "Custom API error" in last_call[1]["text"]
    assert isinstance(last_call[1]["reply_markup"], InlineKeyboardMarkup)
