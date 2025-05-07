"""Тесты для модуля sales_analysis_handlers.py.

Этот модуль содержит тесты для обработчиков командных запросов для анализа продаж.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Message, Update
from telegram.ext import CallbackContext

from src.telegram_bot.sales_analysis_handlers import (
    get_liquidity_emoji,
    get_trend_emoji,
    handle_arbitrage_with_sales,
    handle_liquidity_analysis,
    handle_sales_analysis,
    handle_sales_volume_stats,
)


@pytest.fixture
def mock_update():
    """Создает мок объекта Update для тестирования."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.text = "/sales_analysis AWP | Asiimov (Field-Tested)"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Создает мок объекта CallbackContext для тестирования."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}
    return context


@pytest.mark.asyncio
@patch("src.telegram_bot.sales_analysis_handlers.execute_api_request")
async def test_handle_sales_analysis_success(
    mock_execute_api,
    mock_update,
    mock_context,
):
    """Тестирует успешную обработку запроса анализа продаж."""
    # Настройка мока для reply_text (для получения сообщения, которое потом редактируется)
    reply_message = MagicMock()
    reply_message.edit_text = AsyncMock()
    mock_update.message.reply_text.return_value = reply_message

    # Настройка мока для execute_api_request
    mock_analysis_data = {
        "has_data": True,
        "avg_price": 100.0,
        "max_price": 120.0,
        "min_price": 90.0,
        "price_trend": "up",
        "sales_volume": 73,
        "sales_per_day": 5.2,
        "period_days": 14,
        "recent_sales": [
            {"date": "2023-01-01", "price": 95.0, "currency": "USD"},
            {"date": "2023-01-02", "price": 98.0, "currency": "USD"},
        ],
    }
    mock_execute_api.return_value = mock_analysis_data

    # Вызываем тестируемую функцию
    await handle_sales_analysis(mock_update, mock_context)

    # Проверяем, что reply_text был вызван
    mock_update.message.reply_text.assert_called_once()

    # Проверяем, что edit_text был вызван
    reply_message.edit_text.assert_called_once()

    # Проверяем содержимое сообщения безопасным методом
    call_args = reply_message.edit_text.call_args
    if call_args.kwargs and "text" in call_args.kwargs:
        message_text = call_args.kwargs["text"]
    elif call_args.args:
        message_text = call_args.args[0]
    else:
        message_text = ""

    # Проверяем, что в тексте содержится нужная информация
    assert "Анализ продаж" in message_text
    assert "AWP | Asiimov (Field-Tested)" in message_text
    assert "Средняя цена: $100.00" in message_text
    assert "Максимальная цена: $120.00" in message_text
    assert "Минимальная цена: $90.00" in message_text
    assert "Продаж в день: 5.20" in message_text

    # Проверяем наличие информации о последних продажах
    assert "Последние продажи" in message_text
    assert "2023-01-01" in message_text
    assert "$95.00" in message_text


@pytest.mark.asyncio
@patch("src.telegram_bot.sales_analysis_handlers.execute_api_request")
async def test_handle_sales_analysis_no_data(
    mock_execute_api,
    mock_update,
    mock_context,
):
    """Тестирует обработку запроса, когда данные о продажах отсутствуют."""
    # Настройка мока для reply_text
    reply_message = MagicMock()
    reply_message.edit_text = AsyncMock()
    mock_update.message.reply_text.return_value = reply_message

    # Настройка мока для execute_api_request
    mock_analysis_data = {
        "has_data": False,
    }
    mock_execute_api.return_value = mock_analysis_data

    # Вызываем тестируемую функцию
    await handle_sales_analysis(mock_update, mock_context)

    # Проверяем содержимое сообщения безопасным методом
    call_args = reply_message.edit_text.call_args
    if call_args.kwargs and "text" in call_args.kwargs:
        message_text = call_args.kwargs["text"]
    elif call_args.args:
        message_text = call_args.args[0]
    else:
        message_text = ""

    assert "Не удалось найти данные о продажах" in message_text


@pytest.mark.asyncio
@patch("src.telegram_bot.sales_analysis_handlers.execute_api_request")
async def test_handle_sales_analysis_api_error(
    mock_execute_api,
    mock_update,
    mock_context,
):
    """Тестирует обработку ошибки API при запросе анализа продаж."""
    # Настройка мока для reply_text
    reply_message = MagicMock()
    reply_message.edit_text = AsyncMock()
    mock_update.message.reply_text.return_value = reply_message

    # Настройка мока для execute_api_request
    from src.utils.api_error_handling import APIError

    mock_execute_api.side_effect = APIError("Ошибка API", status_code=500)

    # Вызываем тестируемую функцию
    await handle_sales_analysis(mock_update, mock_context)

    # Проверяем содержимое сообщения безопасным методом
    call_args = reply_message.edit_text.call_args
    if call_args.kwargs and "text" in call_args.kwargs:
        message_text = call_args.kwargs["text"]
    elif call_args.args:
        message_text = call_args.args[0]
    else:
        message_text = ""

    assert "Ошибка при получении данных о продажах" in message_text


@pytest.mark.asyncio
@patch("src.telegram_bot.sales_analysis_handlers.execute_api_request")
async def test_handle_sales_analysis_missing_item_name(
    mock_execute_api,
    mock_update,
    mock_context,
):
    """Тестирует обработку запроса без указания названия предмета."""
    # Изменяем текст запроса без названия предмета
    mock_update.message.text = "/sales_analysis"

    # Вызываем тестируемую функцию
    await handle_sales_analysis(mock_update, mock_context)

    # Проверяем, что был вызван reply_text с сообщением об ошибке
    args, kwargs = mock_update.message.reply_text.call_args
    message_text = args[0]
    assert "Необходимо указать название предмета" in message_text


@pytest.mark.asyncio
@patch("src.telegram_bot.sales_analysis_handlers.execute_api_request")
async def test_handle_arbitrage_with_sales(mock_execute_api, mock_update, mock_context):
    """Тестирует обработку запроса на поиск арбитражных возможностей с учетом продаж."""
    # Настройка мока для reply_text
    reply_message = MagicMock()
    reply_message.edit_text = AsyncMock()
    mock_update.message.reply_text.return_value = reply_message

    # Настройка мока для execute_api_request
    mock_results = {
        "opportunities": [
            {
                "market_hash_name": "AWP | Asiimov (Field-Tested)",
                "profit": 5.0,
                "profit_percent": 10.0,
                "buy_price": 50.0,
                "sell_price": 55.0,
                "sales_analysis": {
                    "price_trend": "up",
                    "sales_per_day": 5.0,
                },
            },
            {
                "market_hash_name": "AK-47 | Redline (Field-Tested)",
                "profit": 3.0,
                "profit_percent": 15.0,
                "buy_price": 20.0,
                "sell_price": 23.0,
                "sales_analysis": {
                    "price_trend": "stable",
                    "sales_per_day": 8.0,
                },
            },
        ],
        "filters": {
            "time_period_days": 7,
        },
    }
    mock_execute_api.return_value = mock_results

    # Вызываем тестируемую функцию
    await handle_arbitrage_with_sales(mock_update, mock_context)

    # Проверяем, что reply_text был вызван
    mock_update.message.reply_text.assert_called_once()

    # Проверяем, что edit_text был вызван
    reply_message.edit_text.assert_called_once()

    # Проверяем содержимое сообщения безопасным методом
    call_args = reply_message.edit_text.call_args
    if call_args.kwargs and "text" in call_args.kwargs:
        message_text = call_args.kwargs["text"]
    elif call_args.args:
        message_text = call_args.args[0]
    else:
        message_text = ""

    # Проверяем, что в тексте содержится нужная информация
    assert "Арбитражные возможности" in message_text
    assert "CS2" in message_text or "CSGO" in message_text.upper()  # Название игры
    assert "AWP | Asiimov (Field-Tested)" in message_text
    assert "AK-47 | Redline (Field-Tested)" in message_text
    assert "Прибыль: $5.00" in message_text
    assert "Прибыль: $3.00" in message_text

    # Проверяем, что есть информация о клавиатуре
    keyboard = call_args.kwargs.get("reply_markup")
    assert keyboard is not None


@pytest.mark.asyncio
@patch("src.telegram_bot.sales_analysis_handlers.execute_api_request")
async def test_handle_arbitrage_with_sales_no_opportunities(
    mock_execute_api,
    mock_update,
    mock_context,
):
    """Тестирует обработку запроса арбитража, когда возможности отсутствуют."""
    # Настройка мока для reply_text
    reply_message = MagicMock()
    reply_message.edit_text = AsyncMock()
    mock_update.message.reply_text.return_value = reply_message

    # Настройка мока для execute_api_request
    mock_results = {
        "opportunities": [],
        "filters": {
            "time_period_days": 7,
        },
    }
    mock_execute_api.return_value = mock_results

    # Вызываем тестируемую функцию
    await handle_arbitrage_with_sales(mock_update, mock_context)

    # Проверяем содержимое сообщения безопасным методом
    call_args = reply_message.edit_text.call_args
    if call_args.kwargs and "text" in call_args.kwargs:
        message_text = call_args.kwargs["text"]
    elif call_args.args:
        message_text = call_args.args[0]
    else:
        message_text = ""

    assert "Не найдено арбитражных возможностей" in message_text


@pytest.mark.asyncio
@patch("src.telegram_bot.sales_analysis_handlers.execute_api_request")
async def test_handle_liquidity_analysis(mock_execute_api, mock_update, mock_context):
    """Тестирует обработку запроса на анализ ликвидности предмета."""
    # Настройка текста команды
    mock_update.message.text = "/liquidity AWP | Asiimov (Field-Tested)"

    # Настройка мока для reply_text
    reply_message = MagicMock()
    reply_message.edit_text = AsyncMock()
    mock_update.message.reply_text.return_value = reply_message

    # Настройка мока для execute_api_request
    mock_analysis_data = {
        "liquidity_category": "Высокая",
        "liquidity_score": 6,
        "sales_analysis": {
            "has_data": True,
            "price_trend": "up",
            "sales_per_day": 5.2,
            "sales_volume": 73,
            "avg_price": 100.0,
        },
        "market_data": {
            "offers_count": 50,
            "lowest_price": 95.0,
            "highest_price": 120.0,
        },
    }
    mock_execute_api.return_value = mock_analysis_data

    # Вызываем тестируемую функцию
    await handle_liquidity_analysis(mock_update, mock_context)

    # Проверяем, что reply_text был вызван
    mock_update.message.reply_text.assert_called_once()

    # Проверяем, что edit_text был вызван
    reply_message.edit_text.assert_called_once()

    # Проверяем содержимое сообщения безопасным методом
    call_args = reply_message.edit_text.call_args
    if call_args.kwargs and "text" in call_args.kwargs:
        message_text = call_args.kwargs["text"]
    elif call_args.args:
        message_text = call_args.args[0]
    else:
        message_text = ""

    # Проверяем, что в тексте содержится нужная информация
    assert "Анализ ликвидности" in message_text
    assert "AWP | Asiimov (Field-Tested)" in message_text
    assert "Категория: Высокая" in message_text
    assert "Оценка: 6/7" in message_text
    assert "Продаж в день: 5.20" in message_text


@pytest.mark.asyncio
@patch("src.telegram_bot.sales_analysis_handlers.execute_api_request")
async def test_handle_sales_volume_stats(mock_execute_api, mock_update, mock_context):
    """Тестирует обработку запроса на статистику объемов продаж."""
    # Настройка мока для reply_text
    reply_message = MagicMock()
    reply_message.edit_text = AsyncMock()
    mock_update.message.reply_text.return_value = reply_message

    # Настройка мока для execute_api_request
    mock_stats = {
        "items": [
            {
                "item_name": "AWP | Asiimov (Field-Tested)",
                "sales_per_day": 10.5,
                "avg_price": 50.0,
                "price_trend": "up",
            },
            {
                "item_name": "AK-47 | Redline (Field-Tested)",
                "sales_per_day": 15.2,
                "avg_price": 25.0,
                "price_trend": "stable",
            },
        ],
        "count": 2,
        "summary": {
            "up_trend_count": 1,
            "down_trend_count": 0,
            "stable_trend_count": 1,
        },
    }
    mock_execute_api.return_value = mock_stats

    # Вызываем тестируемую функцию
    await handle_sales_volume_stats(mock_update, mock_context)

    # Проверяем, что reply_text был вызван
    mock_update.message.reply_text.assert_called_once()

    # Проверяем, что edit_text был вызван
    reply_message.edit_text.assert_called_once()

    # Проверяем содержимое сообщения безопасным методом
    call_args = reply_message.edit_text.call_args
    if call_args.kwargs and "text" in call_args.kwargs:
        message_text = call_args.kwargs["text"]
    elif call_args.args:
        message_text = call_args.args[0]
    else:
        message_text = ""

    # Проверяем, что в тексте содержится нужная информация
    assert "Статистика объема продаж" in message_text
    assert "CS2" in message_text or "CSGO" in message_text.upper()  # Название игры
    assert "AWP | Asiimov (Field-Tested)" in message_text
    assert "AK-47 | Redline (Field-Tested)" in message_text
    assert "продаж в день" in message_text.lower()
    assert "10.50" in message_text
    assert "15.20" in message_text


def test_get_trend_emoji():
    """Тестирует функцию получения эмодзи для тренда цены."""
    # Тестируем различные варианты трендов на основе реальных возвращаемых значений
    assert get_trend_emoji("up") == "⬆️ Растет"
    assert get_trend_emoji("down") == "⬇️ Падает"
    assert get_trend_emoji("stable") == "➡️ Стабилен"
    # Тест для неизвестного тренда должен возвращать emoji для stable
    assert get_trend_emoji("unknown") == "➡️ Стабилен"


def test_get_liquidity_emoji():
    """Тестирует функцию получения эмодзи для категории ликвидности."""
    # Тестируем различные категории ликвидности на основе реальной реализации
    assert get_liquidity_emoji("Очень высокая") == "💧💧💧💧"
    assert get_liquidity_emoji("Высокая") == "💧💧💧"
    assert get_liquidity_emoji("Средняя") == "💧💧"
    assert get_liquidity_emoji("Низкая") == "💧"
    # Тест для неизвестной категории должен возвращать один каплю
    assert get_liquidity_emoji("Неизвестная категория") == "💧"
