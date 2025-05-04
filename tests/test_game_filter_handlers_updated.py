"""
Тесты для модуля game_filter_handlers.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, InlineKeyboardMarkup

from src.telegram_bot.game_filter_handlers import (
    handle_game_filters,
    handle_filter_callback,
    handle_reset_filters,
    handle_select_game_filter_callback,
    handle_search_with_filters,
    DEFAULT_FILTERS
)


@pytest.fixture
def mock_update():
    """Создает мок объекта Update."""
    update = AsyncMock(spec=Update)
    update.effective_user.id = 12345
    update.effective_message = AsyncMock()
    update.callback_query = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Создает мок объекта CallbackContext."""
    context = MagicMock()
    context.user_data = {}
    context.bot = AsyncMock()
    return context


@pytest.mark.asyncio
@patch("src.telegram_bot.game_filter_handlers.FilterFactory")
async def test_handle_game_filters_no_game(mock_filter_factory, mock_update, mock_context):
    """Тест обработки команды фильтров без выбранной игры."""
    # Настройка мока
    mock_game_filter = MagicMock()
    mock_game_filter.get_filter_description.return_value = "Test description"
    mock_filter_factory.get_filter.return_value = mock_game_filter

    # Вызов функции
    await handle_game_filters(mock_update, mock_context)

    # Проверки
    mock_update.effective_message.reply_text.assert_called_once()
    args, kwargs = mock_update.effective_message.reply_text.call_args
    assert "фильтры" in args[0].lower()
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
@patch("src.telegram_bot.game_filter_handlers.FilterFactory")
async def test_handle_game_filters_with_game(mock_filter_factory, mock_update, mock_context):
    """Тест обработки команды фильтров с выбранной игрой."""
    # Настройка моков
    mock_context.user_data["current_game"] = "csgo"
    mock_context.user_data["game_filters"] = {"csgo": {"min_price": 10, "max_price": 100}}

    mock_game_filter = MagicMock()
    mock_game_filter.get_filter_description.return_value = "Test description"
    mock_filter_factory.get_filter.return_value = mock_game_filter

    # Вызов функции
    await handle_game_filters(mock_update, mock_context)

    # Проверки
    mock_update.effective_message.reply_text.assert_called_once()
    args, kwargs = mock_update.effective_message.reply_text.call_args
    assert "reply_markup" in kwargs
    mock_filter_factory.get_filter.assert_called_once_with("csgo")


@pytest.mark.asyncio
async def test_handle_select_game_filter_callback(mock_update, mock_context):
    """Тест функции выбора игры для фильтрации."""
    # Настройка моков
    mock_update.callback_query.data = "select_game_filter:dota2"

    # Вызов функции
    await handle_select_game_filter_callback(mock_update, mock_context)

    # Проверки
    assert mock_context.user_data.get("current_game") == "dota2"
    mock_update.callback_query.answer.assert_called_once()
    mock_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
@patch("src.telegram_bot.game_filter_handlers.apply_filters_to_items")
@patch("src.telegram_bot.game_filter_handlers.find_arbitrage_items")
async def test_handle_search_with_filters(
    mock_find_arbitrage,
    mock_apply_filters,
    mock_update,
    mock_context
):
    """Тест функции применения фильтров к поиску предметов."""
    # Настройка моков
    game = "csgo"
    test_items = [
        {"title": "Item 1", "price": {"USD": 15}},
        {"title": "Item 2", "price": {"USD": 20}}
    ]
    filtered_items = [{"title": "Item 1", "price": {"USD": 15}}]

    mock_find_arbitrage.return_value = test_items
    mock_apply_filters.return_value = filtered_items

    # Вызов функции
    await handle_search_with_filters(mock_update, mock_context, game)

    # Проверки
    mock_find_arbitrage.assert_called_once_with(game)
    mock_apply_filters.assert_called_once()

    mock_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_reset_filters(mock_update, mock_context):
    """Тест функции сброса фильтров на значения по умолчанию."""
    # Настройка моков
    game = "csgo"
    mock_context.user_data["game_filters"] = {
        "csgo": {"min_price": 50, "max_price": 200, "category": "Knife"}
    }

    # Вызов функции
    await handle_reset_filters(mock_update, mock_context, game)

    # Проверки
    assert "csgo" in mock_context.user_data["game_filters"]
    assert mock_context.user_data["game_filters"]["csgo"] == {}
    mock_update.callback_query.answer.assert_called_once()
    mock_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
@patch("src.telegram_bot.game_filter_handlers.handle_price_filter")
async def test_handle_filter_callback_price(
    mock_handle_price,
    mock_update,
    mock_context
):
    """Тест обработки колбэка для изменения цены."""
    # Настройка моков
    mock_update.callback_query.data = "filter_price:csgo"

    # Вызов функции
    await handle_filter_callback(mock_update, mock_context)

    # Проверки
    mock_handle_price.assert_called_once_with(mock_update, mock_context, "csgo")


@pytest.mark.asyncio
@patch("src.telegram_bot.game_filter_handlers.handle_float_filter")
async def test_handle_filter_callback_float(
    mock_handle_float,
    mock_update,
    mock_context
):
    """Тест обработки колбэка для изменения флоата."""
    # Настройка моков
    mock_update.callback_query.data = "filter_float:value"

    # Вызов функции
    await handle_filter_callback(mock_update, mock_context)

    # Проверки
    mock_handle_float.assert_called_once_with(mock_update, mock_context)


@pytest.mark.asyncio
@patch("src.telegram_bot.game_filter_handlers.handle_category_filter")
async def test_handle_filter_callback_category(
    mock_handle_category,
    mock_update,
    mock_context
):
    """Тест обработки колбэка для изменения категории."""
    # Настройка моков
    mock_update.callback_query.data = "filter_category:value"

    # Вызов функции
    await handle_filter_callback(mock_update, mock_context)

    # Проверки
    mock_handle_category.assert_called_once_with(mock_update, mock_context)


@pytest.mark.asyncio
@patch("src.telegram_bot.game_filter_handlers.handle_rarity_filter")
async def test_handle_filter_callback_rarity(
    mock_handle_rarity,
    mock_update,
    mock_context
):
    """Тест обработки колбэка для изменения редкости."""
    # Настройка моков
    mock_update.callback_query.data = "filter_rarity:csgo"

    # Вызов функции
    await handle_filter_callback(mock_update, mock_context)

    # Проверки
    mock_handle_rarity.assert_called_once_with(mock_update, mock_context, "csgo")


@pytest.mark.asyncio
@patch("src.telegram_bot.game_filter_handlers.handle_exterior_filter")
async def test_handle_filter_callback_exterior(
    mock_handle_exterior,
    mock_update,
    mock_context
):
    """Тест обработки колбэка для изменения экстерьера."""
    # Настройка моков
    mock_update.callback_query.data = "filter_exterior:value"

    # Вызов функции
    await handle_filter_callback(mock_update, mock_context)

    # Проверки
    mock_handle_exterior.assert_called_once_with(mock_update, mock_context)


@pytest.mark.asyncio
@patch("src.telegram_bot.game_filter_handlers.handle_reset_filters")
async def test_handle_filter_callback_reset(
    mock_handle_reset,
    mock_update,
    mock_context
):
    """Тест обработки колбэка для сброса фильтров."""
    # Настройка моков
    mock_update.callback_query.data = "filter_reset:csgo"

    # Вызов функции
    await handle_filter_callback(mock_update, mock_context)

    # Проверки
    mock_handle_reset.assert_called_once_with(mock_update, mock_context, "csgo")


@pytest.mark.asyncio
@patch("src.telegram_bot.game_filter_handlers.handle_search_with_filters")
async def test_handle_filter_callback_search(
    mock_handle_search,
    mock_update,
    mock_context
):
    """Тест обработки колбэка для поиска с фильтрами."""
    # Настройка моков
    mock_update.callback_query.data = "filter_search:csgo"

    # Вызов функции
    await handle_filter_callback(mock_update, mock_context)

    # Проверки
    mock_handle_search.assert_called_once_with(mock_update, mock_context, "csgo")


@pytest.mark.asyncio
@patch("src.telegram_bot.game_filter_handlers.handle_price_range_callback")
async def test_handle_filter_callback_price_range(
    mock_handle_price_range,
    mock_update,
    mock_context
):
    """Тест обработки колбэка для диапазона цен."""
    # Настройка моков
    mock_update.callback_query.data = "filter_price_range:value"

    # Вызов функции
    await handle_filter_callback(mock_update, mock_context)

    # Проверки
    mock_handle_price_range.assert_called_once_with(mock_update, mock_context)
