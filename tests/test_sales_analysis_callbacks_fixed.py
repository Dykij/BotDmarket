import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Dict, Any, List, Optional

from src.telegram_bot.sales_analysis_callbacks import (
    handle_sales_history_callback,
    handle_liquidity_callback,
    handle_all_arbitrage_sales_callback
)


@pytest.fixture
def mock_update_and_context():
    """Создает моки для Update и CallbackContext."""
    # Создаем мок для Update
    update = MagicMock()
    query = MagicMock()
    update.callback_query = query
    query.answer = AsyncMock()

    # Важно: настраиваем edit_message_text так, чтобы сохранять аргументы вызова
    edit_message_mock = AsyncMock()
    edit_message_mock.return_value = None
    query.edit_message_text = edit_message_mock

    query.data = "sales_history:AWP | Asiimov (Field-Tested)"
    query.from_user.id = 12345

    # Создаем мок для CallbackContext
    context = MagicMock()
    context.user_data = {}

    return update, context


@pytest.fixture
def mock_sales_data() -> List[Dict[str, Any]]:
    """Создает фиктивные данные продаж для тестов."""
    return [
        {"date": "2023-01-01T12:00:00Z", "price": {"USD": 35.5}},
        {"date": "2023-01-02T13:00:00Z", "price": {"USD": 36.0}},
        {"date": "2023-01-03T14:00:00Z", "price": {"USD": 35.7}},
        {"date": "2023-01-04T15:00:00Z", "price": {"USD": 36.2}},
        {"date": "2023-01-05T16:00:00Z", "price": {"USD": 36.5}}
    ]


@pytest.mark.asyncio
@patch("src.telegram_bot.sales_analysis_callbacks.get_sales_history")
@patch("src.telegram_bot.sales_analysis_callbacks.analyze_sales_history")
async def test_handle_sales_history_callback_success(
    mock_analyze_sales, mock_get_sales, mock_update_and_context, mock_sales_data
):
    """Тест успешной обработки запроса истории продаж."""
    # Распаковка моков
    update, context = mock_update_and_context

    # Настройка для callback_data
    update.callback_query.data = "sales_history:AWP | Asiimov (Field-Tested)"

    # Создаем корректную структуру данных DMarket API
    sales_data_structure = {
        "LastSales": [
            {
                "MarketHashName": "AWP | Asiimov (Field-Tested)",
                "Sales": [
                    {"Timestamp": 1672567200, "Price": "35.50", "Currency": "USD", "OrderType": "Sale"},
                    {"Timestamp": 1672653600, "Price": "36.00", "Currency": "USD", "OrderType": "Sale"},
                    {"Timestamp": 1672740000, "Price": "35.70", "Currency": "USD", "OrderType": "Sale"},
                    {"Timestamp": 1672826400, "Price": "36.20", "Currency": "USD", "OrderType": "Sale"},
                    {"Timestamp": 1672912800, "Price": "36.50", "Currency": "USD", "OrderType": "Sale"}
                ]
            }
        ]
    }

    # Настройка моков
    mock_get_sales.return_value = sales_data_structure
    mock_analyze_sales.return_value = {
        "avg_price": 36.0,
        "min_price": 35.5,
        "max_price": 36.5,
        "volatility": 0.8,
        "trend": 0.2,
        "volume": 5
    }

    # Вызов функции
    await handle_sales_history_callback(update, context)

    # Проверки
    update.callback_query.answer.assert_called_once()
    mock_get_sales.assert_called_once()

    # Проверка содержимого сообщения (последний вызов)
    call_args = update.callback_query.edit_message_text.call_args

    # Проверяем аргументы позиционно или по ключам
    if len(call_args[0]) > 0:  # Есть позиционные аргументы
        text = call_args[0][0]
    elif "text" in call_args[1]:  # Есть именованный аргумент text
        text = call_args[1]["text"]
    else:
        pytest.fail("Не удалось найти текст сообщения в аргументах вызова edit_message_text")

    assert "AWP | Asiimov" in text
    assert "История продаж" in text


@pytest.mark.asyncio
@patch("src.telegram_bot.sales_analysis_callbacks.get_sales_history")
async def test_handle_sales_history_callback_no_data(
    mock_get_sales, mock_update_and_context
):
    """Тест обработки запроса истории продаж при отсутствии данных."""
    # Распаковка моков
    update, context = mock_update_and_context

    # Настройка для callback_data
    update.callback_query.data = "sales_history:AWP | Asiimov (Field-Tested)"

    # Настройка моков - возвращаем пустой словарь LastSales
    mock_get_sales.return_value = {"LastSales": []}

    # Вызов функции
    await handle_sales_history_callback(update, context)

    # Проверки
    update.callback_query.answer.assert_called_once()
    mock_get_sales.assert_called_once()
    assert update.callback_query.edit_message_text.call_count >= 1

    # Проверка содержимого сообщения (последний вызов)
    call_args = update.callback_query.edit_message_text.call_args

    # Проверяем аргументы позиционно или по ключам
    if len(call_args[0]) > 0:  # Есть позиционные аргументы
        text = call_args[0][0]
    elif "text" in call_args[1]:  # Есть именованный аргумент text
        text = call_args[1]["text"]
    else:
        pytest.fail("Не удалось найти текст сообщения в аргументах вызова edit_message_text")

    error_messages = ["не найдено", "не удалось найти", "нет данных", "ошибка"]
    assert any(msg in text.lower() for msg in error_messages)


@pytest.mark.asyncio
@patch("src.telegram_bot.sales_analysis_callbacks.get_sales_history")
async def test_handle_sales_history_callback_api_error(
    mock_get_sales, mock_update_and_context
):
    """Тест обработки API ошибки при запросе истории продаж."""
    # Распаковка моков
    update, context = mock_update_and_context

    # Настройка для callback_data
    update.callback_query.data = "sales_history:AWP | Asiimov (Field-Tested)"

    # Настройка моков для имитации API ошибки
    mock_get_sales.side_effect = Exception("API error")

    # Вызов функции
    await handle_sales_history_callback(update, context)

    # Проверки
    update.callback_query.answer.assert_called_once()
    mock_get_sales.assert_called_once()
    assert update.callback_query.edit_message_text.call_count >= 1

    # Проверка содержимого сообщения (последний вызов)
    call_args = update.callback_query.edit_message_text.call_args

    # Проверяем аргументы позиционно или по ключам
    if len(call_args[0]) > 0:  # Есть позиционные аргументы
        text = call_args[0][0]
    elif "text" in call_args[1]:  # Есть именованный аргумент text
        text = call_args[1]["text"]
    else:
        pytest.fail("Не удалось найти текст сообщения в аргументах вызова edit_message_text")

    assert "ошибка" in text.lower()
    assert "api error" in text.lower()
