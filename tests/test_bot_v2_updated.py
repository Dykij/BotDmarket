"""
Обновленные тесты для Telegram бота версии 2.
Учитывает асинхронную структуру и рефакторинг.
"""

import asyncio
import pytest
import os
from os import environ  # Explicit import to help with linting
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, ANY as mock_ANY
from unittest import mock

from telegram import Update, Message, User, CallbackQuery, InlineKeyboardMarkup, Chat
from telegram.ext import CallbackContext, Application
from telegram.constants import ParseMode

# Используем локальный мок вместо реального класса DMarketAPI
from tests.mock_dmarket_api import DMarketAPI
# Используем мок для модуля auto_arbitrage_scanner
import tests.mock_auto_arbitrage_scanner
# Используем мок для модуля intramarket_arbitrage
import tests.mock_intramarket_arbitrage

# Типизируем os.environ для устранения ошибки линтера
os_environ = environ  # type: dict[str, str]

# Создаем моки, которые будут сбрасываться перед каждым тестом
mock_intramarket_arbitrage_handler = MagicMock()
mock_intramarket_arbitrage_handler.handlers = []
mock_intramarket_arbitrage_handler.register_handlers = MagicMock()

# Создаем уникальные патчи для каждого теста
@pytest.fixture(autouse=True)
def setup_mocks():
    """Автоматически настраивает моки перед каждым тестом."""
    # Патчим импорты, чтобы избежать ошибки в исходном файле
    with patch.dict(sys.modules, {
        'src.dmarket.dmarket_api': MagicMock(),
        'src.telegram_bot.auto_arbitrage_scanner': tests.mock_auto_arbitrage_scanner,
        'src.dmarket.intramarket_arbitrage': tests.mock_intramarket_arbitrage,
        'src.dmarket.sales_history': MagicMock(),
        'src.telegram_bot.handlers.intramarket_arbitrage_handler': mock_intramarket_arbitrage_handler,
        'src.dmarket.arbitrage': MagicMock(),
        'src.utils.api_error_handling': MagicMock(),
    }):
        # Настраиваем необходимые моки
        sys.modules['src.dmarket.dmarket_api'].DMarketAPI = DMarketAPI
        sys.modules['src.dmarket.sales_history'].get_sales_history_for_game = tests.mock_intramarket_arbitrage.get_sales_history_for_game
        
        # Для других импортов из модуля dmarket создаем заглушки
        sys.modules['src.dmarket.arbitrage'].GAMES = {
            "csgo": "CS2",
            "dota2": "Dota 2",
            "rust": "Rust",
            "tf2": "Team Fortress 2"
        }
        
        # Патчим APIError
        class MockAPIError(Exception):
            """Mock API Error class для тестов."""
            def __init__(self, message, status_code=None):
                self.message = message
                self.status_code = status_code
                super().__init__(message)
                
        # Добавляем заглушку для api_error_handling
        sys.modules['src.utils.api_error_handling'].APIError = MockAPIError
        sys.modules['src.utils.api_error_handling'].handle_api_error = AsyncMock(return_value="Обработанная ошибка API")
        
        # Сброс моков перед каждым тестом
        mock_intramarket_arbitrage_handler.register_handlers.reset_mock()
        
        yield

# Теперь импортируем нужные функции из файла бота
from src.telegram_bot.bot_v2 import (
    start_command, help_command, dmarket_status_command, 
    button_callback_handler, arbitrage_command, 
    initialize_application, setup_api_client
)


@pytest.fixture
def mock_update():
    """Создает макет объекта Update для текстовых команд."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    update.effective_chat = MagicMock()
    update.effective_chat.send_action = AsyncMock()
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 12345
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.id = 12345

    # Эти атрибуты нужны только для callback_queries
    update.callback_query = None

    return update


@pytest.fixture
def mock_callback_query():
    """Создает макет объекта Update с CallbackQuery для кнопок."""
    update = MagicMock(spec=Update)
    update.message = None
    update.effective_chat = MagicMock()
    update.effective_chat.send_action = AsyncMock()

    query = MagicMock(spec=CallbackQuery)
    query.data = "test_callback"
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 12345
    query.message = MagicMock(spec=Message)
    query.message.chat = MagicMock(spec=Chat)
    query.message.chat_id = 12345
    query.message.chat.send_action = AsyncMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()

    update.callback_query = query

    return update


@pytest.fixture
def mock_context():
    """Создает макет объекта Context."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}
    context.bot_data = {
        'dmarket_public_key': 'test_public_key',
        'dmarket_secret_key': 'test_secret_key'
    }
    return context


@pytest.fixture
def mock_application():
    """Создает макет объекта Application."""
    app = MagicMock(spec=Application)
    app.bot = MagicMock()
    app.bot.set_my_commands = AsyncMock()
    app.initialize = AsyncMock()
    app.start = AsyncMock()
    app.updater = MagicMock()
    app.updater.start_polling = AsyncMock()
    app.updater.stop = AsyncMock()
    app.stop = AsyncMock()
    app.shutdown = AsyncMock()
    return app


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Тестирование команды /start."""
    with patch('src.telegram_bot.bot_v2.ParseMode', ParseMode):
        await start_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args
        assert "Привет" in args[0]
        assert "DMarket API" in args[0]
        assert kwargs.get("parse_mode") == ParseMode.HTML


@pytest.mark.asyncio
async def test_help_command(mock_update, mock_context):
    """Тестирование команды /help."""
    with patch('src.telegram_bot.bot_v2.ParseMode', ParseMode):
        await help_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args
        assert "Доступные команды" in args[0]
        assert "/start" in args[0]
        assert "/arbitrage" in args[0]
        assert kwargs.get("parse_mode") == ParseMode.HTML


@pytest.mark.asyncio
async def test_dmarket_status_command(mock_update, mock_context):
    """Тестирование команды /status для проверки статуса API."""
    with patch('src.telegram_bot.bot_v2.ParseMode', ParseMode):
        await dmarket_status_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args
        assert "Проверка статуса DMarket API" in args[0]
        assert kwargs.get("parse_mode") == ParseMode.HTML


@pytest.mark.asyncio
async def test_arbitrage_command(mock_update, mock_context):
    """Тестирование команды /arbitrage."""
    with patch('src.telegram_bot.bot_v2.get_modern_arbitrage_keyboard') as mock_get_keyboard, \
         patch('src.telegram_bot.bot_v2.ParseMode', ParseMode), \
         patch('src.telegram_bot.bot_v2.ChatAction'):
        
        mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)
        await arbitrage_command(mock_update, mock_context)
        
        mock_update.effective_chat.send_action.assert_called_once()
        mock_update.message.reply_text.assert_called_once()
        mock_get_keyboard.assert_called_once()
        
        args, kwargs = mock_update.message.reply_text.call_args
        assert "Выберите режим арбитража" in args[0]
        assert kwargs.get("parse_mode") == ParseMode.HTML


@pytest.mark.asyncio
async def test_callback_arbitrage(mock_callback_query, mock_context):
    """Тестирование обработки колбэка 'arbitrage'."""
    mock_callback_query.callback_query.data = "arbitrage"
    
    with patch("src.telegram_bot.bot_v2.arbitrage_callback_impl") as mock_arbitrage_callback:
        await button_callback_handler(mock_callback_query, mock_context)
        
        mock_callback_query.callback_query.answer.assert_called_once()
        mock_arbitrage_callback.assert_called_once_with(mock_callback_query, mock_context)


@pytest.mark.asyncio
async def test_callback_auto_arbitrage(mock_callback_query, mock_context):
    """Тестирование обработки колбэка 'auto_arbitrage'."""
    mock_callback_query.callback_query.data = "auto_arbitrage"
    
    with patch('src.telegram_bot.bot_v2.get_auto_arbitrage_keyboard') as mock_get_keyboard, \
         patch('src.telegram_bot.bot_v2.ParseMode', ParseMode):
        
        mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)
        await button_callback_handler(mock_callback_query, mock_context)
        
        mock_callback_query.callback_query.answer.assert_called_once()
        mock_callback_query.callback_query.edit_message_text.assert_called_once()
        mock_get_keyboard.assert_called_once()
        
        args, kwargs = mock_callback_query.callback_query.edit_message_text.call_args
        assert "Выберите режим автоматического арбитража" in args[0]
        assert kwargs.get("parse_mode") == ParseMode.HTML


@pytest.mark.asyncio
async def test_callback_dmarket_arbitrage(mock_callback_query, mock_context):
    """Тестирование обработки колбэка 'dmarket_arbitrage'."""
    mock_callback_query.callback_query.data = "dmarket_arbitrage"
    
    with patch("src.telegram_bot.bot_v2.handle_dmarket_arbitrage_impl") as mock_handler:
        await button_callback_handler(mock_callback_query, mock_context)
        
        mock_callback_query.callback_query.answer.assert_called_once()
        mock_handler.assert_called_once_with(mock_callback_query, mock_context, mode="normal")


@pytest.mark.asyncio
async def test_callback_best_opportunities(mock_callback_query, mock_context):
    """Тестирование обработки колбэка 'best_opportunities'."""
    mock_callback_query.callback_query.data = "best_opportunities"
    
    with patch("src.telegram_bot.bot_v2.handle_best_opportunities_impl") as mock_handler:
        await button_callback_handler(mock_callback_query, mock_context)
        
        mock_callback_query.callback_query.answer.assert_called_once()
        mock_handler.assert_called_once_with(mock_callback_query, mock_context)


@pytest.mark.asyncio
async def test_callback_game_selection(mock_callback_query, mock_context):
    """Тестирование обработки колбэка 'game_selection'."""
    mock_callback_query.callback_query.data = "game_selection"
    
    with patch("src.telegram_bot.bot_v2.handle_game_selection_impl") as mock_handler:
        await button_callback_handler(mock_callback_query, mock_context)
        
        mock_callback_query.callback_query.answer.assert_called_once()
        mock_handler.assert_called_once_with(mock_callback_query, mock_context)


@pytest.mark.asyncio
async def test_callback_game_selected(mock_callback_query, mock_context):
    """Тестирование обработки колбэка 'game_selected:X'."""
    mock_callback_query.callback_query.data = "game_selected:csgo"
    
    with patch("src.telegram_bot.bot_v2.handle_game_selected_impl") as mock_handler:
        await button_callback_handler(mock_callback_query, mock_context)
        
        mock_callback_query.callback_query.answer.assert_called_once()
        mock_handler.assert_called_once_with(mock_callback_query, mock_context, game="csgo")


@pytest.mark.asyncio
async def test_callback_auto_start(mock_callback_query, mock_context):
    """Тестирование обработки колбэка 'auto_start:X'."""
    mock_callback_query.callback_query.data = "auto_start:boost_low"
    
    with patch("src.telegram_bot.bot_v2.start_auto_trading") as mock_handler:
        await button_callback_handler(mock_callback_query, mock_context)
        
        mock_callback_query.callback_query.answer.assert_called_once()
        mock_handler.assert_called_once_with(mock_callback_query.callback_query, mock_context, "boost_low")


@pytest.mark.asyncio
async def test_callback_paginate(mock_callback_query, mock_context):
    """Тестирование обработки колбэка 'paginate:X:Y'."""
    mock_callback_query.callback_query.data = "paginate:next:boost_low"
    
    with patch("src.telegram_bot.bot_v2.handle_pagination") as mock_handler:
        await button_callback_handler(mock_callback_query, mock_context)
        
        mock_callback_query.callback_query.answer.assert_called_once()
        mock_handler.assert_called_once_with(mock_callback_query.callback_query, mock_context, "next", "boost_low")


@pytest.mark.asyncio
async def test_setup_api_client():
    """Тестирование настройки API клиента DMarket."""
    with patch.dict('os.environ', {"DMARKET_PUBLIC_KEY": "test_key", "DMARKET_SECRET_KEY": "test_secret"}), \
         patch('src.telegram_bot.bot_v2.DMarketAPI', DMarketAPI):
        api_client = setup_api_client()
        
        assert api_client is not None
        assert api_client.public_key == "test_key"
        assert api_client.api_url == "https://api.dmarket.com"


@pytest.mark.asyncio
async def test_setup_api_client_no_keys():
    """Тестирование настройки API клиента DMarket без ключей."""
    with patch.dict('os.environ', {"DMARKET_PUBLIC_KEY": "", "DMARKET_SECRET_KEY": ""}):
        api_client = setup_api_client()
        
        assert api_client is None


@pytest.mark.asyncio
async def test_initialize_application(mock_application):
    """Тестирование инициализации приложения."""
    with patch("src.telegram_bot.bot_v2.set_bot_commands") as mock_set_commands, \
         patch("src.telegram_bot.bot_v2.initialize_alerts_manager") as mock_init_alerts:
        
        await initialize_application(mock_application)
        
        mock_set_commands.assert_called_once_with(mock_application)
        mock_init_alerts.assert_called_once_with(mock_application) 