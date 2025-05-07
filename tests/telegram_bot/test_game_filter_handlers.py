"""Тесты для модуля game_filter_handlers.py.

Этот модуль содержит тесты для функций обработки фильтров игр для Telegram-бота.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Message, Update
from telegram.ext import CallbackContext

from src.telegram_bot.game_filter_handlers import (
    GAMES_MAPPING,
    handle_back_to_filters_callback,
    handle_change_game_filter,
    handle_filter_callback,
    handle_float_filter,
    handle_game_filters,
    handle_price_filter,
    handle_reset_filters,
    handle_search_with_filters,
    handle_select_game_filter_callback,
)


@pytest.fixture
def mock_update():
    """Создает мок объекта Update для тестирования."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.edit_message_reply_markup = AsyncMock()
    update.callback_query.data = "filter:price:csgo"
    return update


@pytest.fixture
def mock_context():
    """Создает мок объекта CallbackContext для тестирования."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo", "game_filters": {}}
    return context


@pytest.mark.asyncio
async def test_handle_game_filters_csgo(mock_update, mock_context):
    """Тестирует обработку команды /filters для CS2."""
    # Настраиваем конкретную игру
    mock_context.user_data["current_game"] = "csgo"

    # Создаем мок для FilterFactory.get_filter
    mock_filter = MagicMock()
    mock_filter.get_filter_description.return_value = (
        "Цена: $1.00 - $500.00\nFloat: 0.0 - 1.0"
    )

    with patch(
        "src.telegram_bot.game_filter_handlers.FilterFactory.get_filter",
        return_value=mock_filter,
    ):
        # Вызываем тестируемую функцию
        await handle_game_filters(mock_update, mock_context)

        # Проверяем, что функция отправила сообщение
        mock_update.message.reply_text.assert_called_once()

        # Проверяем содержимое сообщения
        args, kwargs = mock_update.message.reply_text.call_args
        message_text = args[0]
        assert "Настройка фильтров для игры" in message_text
        assert "CS2" in message_text  # Правильное имя игры

        # Проверяем, что клавиатура содержит нужные кнопки
        keyboard = kwargs["reply_markup"].inline_keyboard
        # Проверяем наличие кнопок, специфичных для CS2
        assert any(
            button.text == "🔍 Float" and "filter:float:csgo" in button.callback_data
            for row in keyboard
            for button in row
        )
        assert any(
            button.text == "🔶 Внешний вид"
            and "filter:exterior:csgo" in button.callback_data
            for row in keyboard
            for button in row
        )


@pytest.mark.asyncio
async def test_handle_game_filters_dota2(mock_update, mock_context):
    """Тестирует обработку команды /filters для Dota 2."""
    # Настраиваем конкретную игру
    mock_context.user_data["current_game"] = "dota2"

    # Создаем мок для FilterFactory.get_filter
    mock_filter = MagicMock()
    mock_filter.get_filter_description.return_value = (
        "Цена: $1.00 - $500.00\nГерои: Любые"
    )

    with patch(
        "src.telegram_bot.game_filter_handlers.FilterFactory.get_filter",
        return_value=mock_filter,
    ):
        # Вызываем тестируемую функцию
        await handle_game_filters(mock_update, mock_context)

        # Проверяем содержимое сообщения
        args, kwargs = mock_update.message.reply_text.call_args
        message_text = args[0]
        assert "Dota 2" in message_text  # Правильное имя игры

        # Проверяем, что клавиатура содержит нужные кнопки для Dota 2
        keyboard = kwargs["reply_markup"].inline_keyboard
        assert any(
            button.text == "🦸‍♂️ Герой" and "filter:hero:dota2" in button.callback_data
            for row in keyboard
            for button in row
        )


@pytest.mark.asyncio
async def test_handle_filter_callback_price(mock_update, mock_context):
    """Тестирует обработку callback для настройки цены."""
    # Настраиваем данные callback
    mock_update.callback_query.data = "filter:price:csgo"

    # Мокируем функцию handle_price_filter
    with patch(
        "src.telegram_bot.game_filter_handlers.handle_price_filter"
    ) as mock_price_filter:
        mock_price_filter.return_value = None

        # Вызываем тестируемую функцию
        await handle_filter_callback(mock_update, mock_context)

        # Проверяем, что нужная функция была вызвана с правильными параметрами
        mock_price_filter.assert_called_once_with(mock_update, mock_context, "csgo")


@pytest.mark.asyncio
async def test_handle_filter_callback_float(mock_update, mock_context):
    """Тестирует обработку callback для настройки float."""
    # Настраиваем данные callback
    mock_update.callback_query.data = "filter:float:csgo"

    # Мокируем функцию handle_float_filter
    with patch(
        "src.telegram_bot.game_filter_handlers.handle_float_filter"
    ) as mock_float_filter:
        mock_float_filter.return_value = None

        # Вызываем тестируемую функцию
        await handle_filter_callback(mock_update, mock_context)

        # Проверяем, что нужная функция была вызвана с правильными параметрами
        mock_float_filter.assert_called_once_with(mock_update, mock_context)


@pytest.mark.asyncio
async def test_handle_filter_callback_reset(mock_update, mock_context):
    """Тестирует обработку callback для сброса фильтров."""
    # Настраиваем данные callback
    mock_update.callback_query.data = "filter:reset:csgo"

    # Мокируем функцию handle_reset_filters
    with patch(
        "src.telegram_bot.game_filter_handlers.handle_reset_filters"
    ) as mock_reset:
        mock_reset.return_value = None

        # Вызываем тестируемую функцию
        await handle_filter_callback(mock_update, mock_context)

        # Проверяем, что нужная функция была вызвана с правильными параметрами
        mock_reset.assert_called_once_with(mock_update, mock_context, "csgo")


@pytest.mark.asyncio
async def test_handle_filter_callback_search(mock_update, mock_context):
    """Тестирует обработку callback для поиска с фильтрами."""
    # Настраиваем данные callback
    mock_update.callback_query.data = "filter:search:csgo"

    # Мокируем функцию handle_search_with_filters
    with patch(
        "src.telegram_bot.game_filter_handlers.handle_search_with_filters"
    ) as mock_search:
        mock_search.return_value = None

        # Вызываем тестируемую функцию
        await handle_filter_callback(mock_update, mock_context)

        # Проверяем, что нужная функция была вызвана с правильными параметрами
        mock_search.assert_called_once_with(mock_update, mock_context, "csgo")


@pytest.mark.asyncio
async def test_handle_filter_callback_change_game(mock_update, mock_context):
    """Тестирует обработку callback для смены игры."""
    # Настраиваем данные callback
    mock_update.callback_query.data = "filter:change_game"

    # Мокируем функцию handle_change_game_filter
    with patch(
        "src.telegram_bot.game_filter_handlers.handle_change_game_filter"
    ) as mock_change:
        mock_change.return_value = None

        # Вызываем тестируемую функцию
        await handle_filter_callback(mock_update, mock_context)

        # Проверяем, что нужная функция была вызвана
        mock_change.assert_called_once_with(mock_update, mock_context)


@pytest.mark.asyncio
async def test_handle_price_filter(mock_update, mock_context):
    """Тестирует настройку фильтра цены."""
    # Вызываем тестируемую функцию
    await handle_price_filter(mock_update, mock_context, "csgo")

    # Проверяем, что был вызван метод edit_message_text
    mock_update.callback_query.edit_message_text.assert_called_once()

    # Проверяем содержимое сообщения
    args, kwargs = mock_update.callback_query.edit_message_text.call_args
    message_text = args[0]
    assert "настройки цены" in message_text.lower()

    # Проверяем, что в клавиатуре есть правильные диапазоны цен
    keyboard = kwargs["reply_markup"].inline_keyboard
    assert any("$1-$50" in button.text for row in keyboard for button in row)


@pytest.mark.asyncio
async def test_handle_float_filter(mock_update, mock_context):
    """Тестирует настройку фильтра float."""
    # Вызываем тестируемую функцию
    await handle_float_filter(mock_update, mock_context)

    # Проверяем, что был вызван метод edit_message_text
    mock_update.callback_query.edit_message_text.assert_called_once()

    # Проверяем содержимое сообщения
    args, kwargs = mock_update.callback_query.edit_message_text.call_args
    message_text = args[0]
    assert "float" in message_text.lower()

    # Проверяем, что в клавиатуре есть правильные диапазоны float
    keyboard = kwargs["reply_markup"].inline_keyboard
    assert any(
        "0.00-0.07" in button.text for row in keyboard for button in row  # Factory New
    )


@pytest.mark.asyncio
async def test_handle_reset_filters(mock_update, mock_context):
    """Тестирует сброс фильтров."""
    # Настройка начальных фильтров
    mock_context.user_data["game_filters"] = {
        "csgo": {
            "min_price": 10.0,
            "max_price": 100.0,
            "float_min": 0.1,
            "float_max": 0.5,
        },
    }

    # Вызываем тестируемую функцию
    await handle_reset_filters(mock_update, mock_context, "csgo")

    # Проверяем, что фильтры были сброшены
    assert "csgo" not in mock_context.user_data["game_filters"]

    # Проверяем, что был вызван метод edit_message_text
    mock_update.callback_query.edit_message_text.assert_called_once()

    # Проверяем содержимое сообщения
    args, kwargs = mock_update.callback_query.edit_message_text.call_args
    message_text = args[0]
    assert "сброшены" in message_text.lower()


@pytest.mark.asyncio
async def test_handle_change_game_filter(mock_update, mock_context):
    """Тестирует смену игры для фильтров."""
    # Вызываем тестируемую функцию
    await handle_change_game_filter(mock_update, mock_context)

    # Проверяем, что был вызван метод edit_message_text
    mock_update.callback_query.edit_message_text.assert_called_once()

    # Проверяем содержимое сообщения
    args, kwargs = mock_update.callback_query.edit_message_text.call_args
    message_text = args[0]
    assert "выберите игру" in message_text.lower()

    # Проверяем, что в клавиатуре есть все игры
    keyboard = kwargs["reply_markup"].inline_keyboard
    games = ["csgo", "dota2", "tf2", "rust"]

    for game in games:
        game_display = GAMES_MAPPING.get(game, game)
        assert any(game_display in button.text for row in keyboard for button in row)


@pytest.mark.asyncio
@patch("src.telegram_bot.game_filter_handlers.execute_api_request")
async def test_handle_search_with_filters(mock_execute_api, mock_update, mock_context):
    """Тестирует поиск предметов с фильтрами."""
    # Настройка фильтров
    mock_context.user_data["game_filters"] = {
        "csgo": {"min_price": 10.0, "max_price": 100.0},
    }

    # Настройка возвращаемых данных от API
    mock_items = [
        {"market_hash_name": "AWP | Asiimov", "price": {"USD": 50.0}},
        {"market_hash_name": "AK-47 | Redline", "price": {"USD": 30.0}},
    ]
    mock_execute_api.return_value = mock_items

    # Вызываем тестируемую функцию
    await handle_search_with_filters(mock_update, mock_context, "csgo")

    # Проверяем, что метод edit_message_text был вызван
    assert mock_update.callback_query.edit_message_text.call_count >= 2

    # Проверяем содержимое сообщения
    final_call = mock_update.callback_query.edit_message_text.call_args_list[-1]
    args, kwargs = final_call
    message_text = args[0]

    # В сообщении должны быть найденные предметы
    assert (
        "найдено 2 предмет" in message_text.lower()
        or "найдено: 2" in message_text.lower()
    )


@pytest.mark.asyncio
async def test_handle_select_game_filter_callback(mock_update, mock_context):
    """Тестирует callback для выбора игры."""
    # Настройка данных callback
    mock_update.callback_query.data = "select_game:dota2"

    # Вызываем тестируемую функцию
    await handle_select_game_filter_callback(mock_update, mock_context)

    # Проверяем, что игра была изменена в контексте
    assert mock_context.user_data["current_game"] == "dota2"

    # Проверяем вызов функции handle_game_filters
    # (в данном случае через edit_message_text)
    mock_update.callback_query.edit_message_text.assert_called_once()

    # Проверяем содержимое сообщения
    args, kwargs = mock_update.callback_query.edit_message_text.call_args
    message_text = args[0]
    assert "dota 2" in message_text.lower()


@pytest.mark.asyncio
async def test_handle_back_to_filters_callback(mock_update, mock_context):
    """Тестирует callback для возврата к меню фильтров."""
    # Настройка мока для handle_game_filters
    with patch(
        "src.telegram_bot.game_filter_handlers.handle_game_filters"
    ) as mock_game_filters:
        mock_game_filters.return_value = None

        # Вызываем тестируемую функцию
        await handle_back_to_filters_callback(mock_update, mock_context)

        # Проверяем, что был вызван handle_game_filters
        mock_game_filters.assert_called_once()

        # Проверяем, что был вызван answer
        mock_update.callback_query.answer.assert_called_once()

        # Убедимся, что метод delete_message был вызван
        mock_update.callback_query.message.delete.assert_called_once()
