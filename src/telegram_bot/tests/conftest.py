"""Конфигурация pytest для модуля telegram_bot.

Этот файл содержит фикстуры для тестирования модулей в директории src/telegram_bot.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_telegram_update():
    """Создает мок объекта Update из библиотеки python-telegram-bot."""
    mock_update = MagicMock()
    mock_update.effective_chat.id = 123456789
    mock_update.effective_user.id = 987654321
    mock_update.effective_user.username = "test_user"
    mock_update.effective_message.text = "/test command"
    mock_update.effective_message.message_id = 11223344

    # Callback query
    mock_callback_query = MagicMock()
    mock_callback_query.from_user.id = 987654321
    mock_callback_query.from_user.username = "test_user"
    mock_callback_query.message.chat.id = 123456789
    mock_callback_query.message.message_id = 11223344
    mock_callback_query.data = "test_callback_data"

    mock_update.callback_query = mock_callback_query

    return mock_update


@pytest.fixture
def mock_telegram_context():
    """Создает мок объекта CallbackContext из библиотеки python-telegram-bot."""
    mock_context = MagicMock()
    mock_context.bot = MagicMock()
    mock_context.bot.send_message = AsyncMock()
    mock_context.bot.edit_message_text = AsyncMock()
    mock_context.bot.edit_message_reply_markup = AsyncMock()
    mock_context.bot.answer_callback_query = AsyncMock()

    # Имитируем хранилище данных пользователя
    mock_context.user_data = {}
    mock_context.chat_data = {}
    mock_context.bot_data = {}

    return mock_context


@pytest.fixture
def mock_dmarket_api_for_telegram():
    """Создает мок DMarketAPI для использования в тестах telegram_bot."""
    with patch("src.dmarket.dmarket_api.DMarketAPI") as mock_api_class:
        mock_api = MagicMock()

        # Настраиваем базовые методы
        mock_api.get_balance = AsyncMock(
            return_value={"usd": {"amount": 10000}},
        )  # $100
        mock_api.get_market_items = AsyncMock(return_value={"objects": []})

        # Настраиваем класс для возврата подготовленного инстанса
        mock_api_class.return_value = mock_api
        mock_api_class.__aenter__.return_value = mock_api

        return mock_api


@pytest.fixture
def mock_arbitrage_functions():
    """Мокирует функции арбитража для тестов telegram_bot."""
    with (
        patch("src.dmarket.arbitrage.arbitrage_boost_async") as mock_boost,
        patch("src.dmarket.arbitrage.arbitrage_mid_async") as mock_mid,
        patch("src.dmarket.arbitrage.arbitrage_pro_async") as mock_pro,
        patch(
            "src.dmarket.arbitrage.find_arbitrage_opportunities_async",
        ) as mock_opportunities,
    ):

        # Настройка возвращаемых значений
        mock_boost.return_value = [
            {
                "name": "Test Skin 1",
                "buy": "$10.50",
                "sell": "$12.00",
                "profit": "$1.10",
                "profit_percent": "10.5",
                "fee": "7%",
            },
        ]

        mock_mid.return_value = [
            {
                "name": "Test Skin 2",
                "buy": "$25.00",
                "sell": "$32.00",
                "profit": "$6.50",
                "profit_percent": "26.0",
                "fee": "7%",
            },
        ]

        mock_pro.return_value = [
            {
                "name": "Test Skin 3",
                "buy": "$150.00",
                "sell": "$200.00",
                "profit": "$35.00",
                "profit_percent": "23.3",
                "fee": "7%",
            },
        ]

        mock_opportunities.return_value = [
            {
                "item_title": "Test Skin 4",
                "buy_price": 75.0,
                "sell_price": 100.0,
                "profit_amount": 18.0,
                "profit_percentage": 24.0,
                "market_from": "DMarket",
                "market_to": "Steam Market",
            },
        ]

        yield {
            "boost": mock_boost,
            "mid": mock_mid,
            "pro": mock_pro,
            "opportunities": mock_opportunities,
        }
