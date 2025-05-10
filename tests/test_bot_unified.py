"""Объединенные тесты для Telegram-бота DMarket.

Этот модуль содержит тесты для проверки:
1. Основной функциональности бота
2. Обработки команд
3. Форматирования сообщений
4. Пагинации
5. Обработки ошибок API
6. Интеграции с DMarket API
"""

import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes, ExtBot, CommandHandler, CallbackContext
from telegram.error import NetworkError

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Импортируем модули бота для тестирования
from telegram_bot.bot_v2 import (
    balance_command,
    market_command,
    help_command,
    start_command,
    arbitrage_command,
    settings_command,
    format_balance_message,
    format_market_item,
    handle_error,
    setup_command_handlers,
    setup_error_handlers,
    main,
    create_application,
    message_handler
)

# Фикстуры для тестирования

@pytest.fixture
def mock_update():
    """Создает мок объекта Update для Telegram."""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.chat = update.effective_chat
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 12345
    update.message.from_user.first_name = "Test User"
    update.message.from_user.username = "testuser"
    update.message.text = "/start"
    update.message.reply_text = AsyncMock()
    update.message.reply_html = AsyncMock()
    update.message.reply_markdown = AsyncMock()
    update.callback_query = None
    return update

@pytest.fixture
def mock_context():
    """Создает мок объекта Context для Telegram."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock(spec=ExtBot)
    context.bot.send_message = AsyncMock()
    context.user_data = {}
    return context

@pytest.fixture
def mock_callback_query(mock_update):
    """Создает мок объекта CallbackQuery для Telegram."""
    callback_query = MagicMock(spec=CallbackQuery)
    callback_query.message = mock_update.message
    callback_query.data = "test_data"
    callback_query.from_user = mock_update.message.from_user
    callback_query.answer = AsyncMock()
    callback_query.edit_message_text = AsyncMock()
    mock_update.callback_query = callback_query
    return callback_query

@pytest.fixture
def mock_application():
    """Создает мок объекта Application для Telegram."""
    app = MagicMock(spec=Application)
    app.add_handler = MagicMock()
    app.add_error_handler = MagicMock()
    return app

# Тесты основных команд

@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Тестирует команду /start."""
    await start_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    args = mock_update.message.reply_text.call_args[0][0]
    assert "Добро пожаловать" in args or "Welcome" in args

@pytest.mark.asyncio
async def test_help_command(mock_update, mock_context):
    """Тестирует команду /help."""
    await help_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    args = mock_update.message.reply_text.call_args[0][0]
    assert "команды" in args or "commands" in args or "help" in args

@pytest.mark.asyncio
async def test_balance_command_without_api_keys(mock_update, mock_context):
    """Тестирует команду /balance когда API ключи не настроены."""
    with patch.dict("os.environ", {"DMARKET_PUBLIC_KEY": "", "DMARKET_SECRET_KEY": ""}):
        await balance_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0][0]
        assert "ключи API не настроены" in args or "API keys are not configured" in args

@pytest.mark.asyncio
async def test_market_command(mock_update, mock_context):
    """Тестирует команду /market."""
    # Патчим функцию создания клавиатуры
    with patch("telegram_bot.bot_v2.create_game_selection_keyboard", return_value=MagicMock()):
        await market_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        # Проверяем, что пользовательские данные обновлены
        assert "search_state" in mock_context.user_data
        assert mock_context.user_data["search_state"] == "awaiting_game"

@pytest.mark.asyncio
async def test_arbitrage_command(mock_update, mock_context):
    """Тестирует команду /arbitrage."""
    # Патчим функцию создания клавиатуры
    with patch("telegram_bot.bot_v2.create_arbitrage_keyboard", return_value=MagicMock()):
        await arbitrage_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0][0]
        assert "арбитраж" in args.lower() or "arbitrage" in args.lower()

@pytest.mark.asyncio
async def test_settings_command(mock_update, mock_context):
    """Тестирует команду /settings."""
    # Патчим функцию создания клавиатуры
    with patch("telegram_bot.bot_v2.create_settings_keyboard", return_value=MagicMock()):
        await settings_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0][0]
        assert "настройки" in args.lower() or "settings" in args.lower()

# Тесты для обработки сообщений

@pytest.mark.asyncio
async def test_message_handler_no_state(mock_update, mock_context):
    """Тестирует обработку сообщений без установленного состояния."""
    # Устанавливаем текст сообщения
    mock_update.message.text = "Тестовое сообщение"
    
    # Патчим функцию создания клавиатуры
    with patch("telegram_bot.bot_v2.create_main_keyboard", return_value=MagicMock()):
        await message_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0][0]
        assert "команды" in args.lower() or "commands" in args.lower()

@pytest.mark.asyncio
async def test_message_handler_awaiting_game(mock_update, mock_context):
    """Тестирует обработку сообщений в состоянии ожидания выбора игры."""
    # Устанавливаем текст сообщения и состояние
    mock_update.message.text = "csgo"
    mock_context.user_data["search_state"] = "awaiting_game"
    
    # Патчим функцию проверки игры
    with patch("telegram_bot.bot_v2.SUPPORTED_GAMES", ["csgo", "dota2"]):
        with patch("telegram_bot.bot_v2.ReplyKeyboardRemove", return_value=MagicMock()):
            await message_handler(mock_update, mock_context)
            mock_update.message.reply_text.assert_called_once()
            
            # Проверяем, что состояние изменилось
            assert mock_context.user_data["search_state"] == "awaiting_query"
            assert mock_context.user_data["selected_game"] == "csgo"

# Тесты для обработки ошибок

@pytest.mark.asyncio
async def test_handle_error_general(mock_update, mock_context):
    """Тестирует обработку общих ошибок."""
    error = Exception("Test error")
    mock_context.error = error
    await handle_error(mock_update, mock_context)
    mock_context.bot.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_handle_error_network(mock_update, mock_context):
    """Тестирует обработку сетевых ошибок."""
    error = NetworkError("Network error")
    mock_context.error = error
    
    # Создаем класс ApiError для патча
    class ApiError(Exception):
        def __init__(self, message):
            self.message = message
    
    # Патчим проверку типа ошибки
    with patch("telegram_bot.bot_v2.NetworkError", NetworkError), \
         patch("telegram_bot.bot_v2.ApiError", ApiError):
        await handle_error(mock_update, mock_context)
        mock_context.bot.send_message.assert_called_once()
        args = mock_context.bot.send_message.call_args[1]
        assert "сетевая ошибка" in args["text"].lower() or "network error" in args["text"].lower()

# Тесты для форматирования сообщений

def test_format_balance_message():
    """Тестирует форматирование сообщения о балансе."""
    balance_data = {
        "usd": {"amount": 10000},  # 100 USD в центах
        "has_funds": True,
        "available_balance": 100.0,
    }
    message = format_balance_message(balance_data)
    assert "$100.00" in message or "100.00 USD" in message
    assert "доступно" in message.lower() or "available" in message.lower()

def test_format_market_item():
    """Тестирует форматирование информации о предмете маркета."""
    item = {
        "title": "AK-47 | Redline",
        "price": {"USD": 1500},  # 15 USD в центах
        "categoryPath": "Rifle",
        "extra": {"wear": "Field-Tested"},
        "itemId": "item123456",
    }
    
    message = format_market_item(item)
    assert item["title"] in message
    assert "$15.00" in message
    assert item["categoryPath"] in message
    assert item["extra"]["wear"] in message
    assert item["itemId"] in message

# Тесты для настройки обработчиков

def test_setup_command_handlers(mock_application):
    """Тестирует настройку обработчиков команд."""
    setup_command_handlers(mock_application)
    assert mock_application.add_handler.call_count >= 3  # Минимум 3 обработчика (start, help, balance)

def test_setup_error_handlers(mock_application):
    """Тестирует настройку обработчиков ошибок."""
    setup_error_handlers(mock_application)
    mock_application.add_error_handler.assert_called_once()

# Тесты для интеграции с DMarket API

@pytest.mark.asyncio
async def test_balance_command_with_mock_api(mock_update, mock_context):
    """Тестирует команду /balance с моком API."""
    mock_api = AsyncMock()
    mock_api.get_user_balance.return_value = {
        "usd": {"amount": 10000},  # 100 USD в центах
        "has_funds": True,
        "available_balance": 100.0,
    }

    with patch("src.dmarket.dmarket_api.DMarketAPI", return_value=mock_api):
        with patch.dict("os.environ", {"DMARKET_PUBLIC_KEY": "test", "DMARKET_SECRET_KEY": "test"}):
            await balance_command(mock_update, mock_context)
            mock_update.message.reply_text.assert_called_once()
            args = mock_update.message.reply_text.call_args[0][0]
            assert "$100.00" in args or "100.00 USD" in args

# Тесты для создания и запуска приложения

@pytest.mark.asyncio
async def test_create_application():
    """Тестирует создание приложения бота."""
    with patch("os.getenv", return_value="test_token"), \
         patch("telegram.ext.Application.builder") as mock_builder, \
         patch("telegram_bot.bot_v2.setup_command_handlers"), \
         patch("telegram_bot.bot_v2.setup_error_handlers"):
        
        mock_app = MagicMock()
        mock_builder.return_value.token.return_value.build.return_value = mock_app
        
        app = create_application()
        assert app == mock_app

@pytest.mark.asyncio
async def test_main_function():
    """Тестирует основную функцию запуска бота."""
    mock_app = MagicMock()
    mock_app.run_polling = AsyncMock()
    
    with patch("telegram_bot.bot_v2.create_application", return_value=mock_app):
        await main()
        mock_app.run_polling.assert_called_once()
