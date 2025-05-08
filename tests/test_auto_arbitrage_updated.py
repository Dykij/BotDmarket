"""
Обновленные тесты для модуля auto_arbitrage.
Учитывает рефакторинг и работу с окружением.
"""

import asyncio
import pytest
import os
from os import environ  # Explicit import to help with linting
import sys
from unittest.mock import AsyncMock, MagicMock, patch, ANY as mock_ANY
from unittest import mock

from telegram import CallbackQuery, InlineKeyboardMarkup, Message
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

# Используем локальный мок вместо реального класса DMarketAPI
from tests.mock_dmarket_api import DMarketAPI
# Используем мок для модуля auto_arbitrage_scanner
import tests.mock_auto_arbitrage_scanner

# Типизируем os.environ для устранения ошибки линтера
os_environ = environ  # type: dict[str, str]

# Создаем уникальные моки для всего тестового файла, чтобы избежать конфликтов
mock_pagination_manager = MagicMock()
mock_pagination_manager.get_page = MagicMock(return_value=([], 0, 0))
mock_pagination_manager.get_mode = MagicMock(return_value="boost_low")
mock_pagination_manager.next_page = AsyncMock()
mock_pagination_manager.prev_page = AsyncMock()
mock_pagination_manager.add_items_for_user = MagicMock()

# Патчим клавиатуры
mock_keyboards = MagicMock()
mock_keyboards.get_back_to_arbitrage_keyboard = MagicMock(return_value=MagicMock(spec=InlineKeyboardMarkup))
mock_keyboards.get_modern_arbitrage_keyboard = MagicMock(return_value=MagicMock(spec=InlineKeyboardMarkup))
mock_keyboards.get_auto_arbitrage_keyboard = MagicMock(return_value=MagicMock(spec=InlineKeyboardMarkup))

# Патчим APIError
class MockAPIError(Exception):
    """Mock API Error class для тестов."""
    def __init__(self, message, status_code=None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

# Создаем уникальные патчи для каждого теста
@pytest.fixture(autouse=True)
def setup_mocks():
    """Автоматически настраивает моки перед каждым тестом."""
    # Патчим импорты, чтобы избежать ошибки в исходном файле
    with patch.dict(sys.modules, {
        'src.dmarket.dmarket_api': MagicMock(),
        'src.telegram_bot.auto_arbitrage_scanner': tests.mock_auto_arbitrage_scanner,
        'src.dmarket.arbitrage': MagicMock(),
        'src.telegram_bot.pagination': MagicMock(),
        'src.telegram_bot.keyboards': MagicMock(),
        'src.utils.api_error_handling': MagicMock(),
    }):
        # Настраиваем необходимые моки
        sys.modules['src.dmarket.dmarket_api'].DMarketAPI = DMarketAPI
        sys.modules['src.dmarket.arbitrage'].GAMES = {
            "csgo": "CS2",
            "dota2": "Dota 2",
            "rust": "Rust",
            "tf2": "Team Fortress 2"
        }
        sys.modules['src.dmarket.arbitrage'].ArbitrageTrader = MagicMock()
        
        # Настраиваем pagination_manager
        sys.modules['src.telegram_bot.pagination'].pagination_manager = mock_pagination_manager
        
        # Настраиваем клавиатуры
        sys.modules['src.telegram_bot.keyboards'].get_back_to_arbitrage_keyboard = mock_keyboards.get_back_to_arbitrage_keyboard
        sys.modules['src.telegram_bot.keyboards'].get_modern_arbitrage_keyboard = mock_keyboards.get_modern_arbitrage_keyboard
        sys.modules['src.telegram_bot.keyboards'].get_auto_arbitrage_keyboard = mock_keyboards.get_auto_arbitrage_keyboard
        
        # Настраиваем обработку ошибок API
        sys.modules['src.utils.api_error_handling'].APIError = MockAPIError
        sys.modules['src.utils.api_error_handling'].handle_api_error = AsyncMock(return_value="Обработанная ошибка API")
        sys.modules['src.utils.api_error_handling'].RetryStrategy = MagicMock()
        
        # Сброс моков перед каждым тестом для избежания конфликтов
        mock_pagination_manager.get_page.reset_mock()
        mock_pagination_manager.get_mode.reset_mock() 
        mock_pagination_manager.next_page.reset_mock()
        mock_pagination_manager.prev_page.reset_mock()
        mock_pagination_manager.add_items_for_user.reset_mock()
        
        yield

# Теперь импортируем нужные функции
from src.telegram_bot.auto_arbitrage import (
    create_dmarket_api_client,
    format_results,
    handle_pagination,
    show_auto_stats_with_pagination,
    start_auto_trading,
    check_balance_command,
    ARBITRAGE_MODES
)


@pytest.fixture
def mock_callback_query():
    """Создает мок объекта CallbackQuery."""
    query = MagicMock(spec=CallbackQuery)
    query.data = "test_callback"
    query.from_user = MagicMock()
    query.from_user.id = 12345
    query.message = MagicMock(spec=Message)
    query.message.chat_id = 12345
    query.answer = AsyncMock()
    # Изменяем мок для правильной структуры возвращаемого значения
    query.edit_message_text = AsyncMock()
    query.edit_message_text.return_value = MagicMock()
    query.edit_message_text.call_args = (("Тестовый текст",), {"parse_mode": "HTML"})
    query.edit_message_reply_markup = AsyncMock()
    return query


@pytest.fixture
def mock_context():
    """Создает мок объекта Context."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}
    context.bot_data = {
        'dmarket_public_key': 'test_public_key',
        'dmarket_secret_key': 'test_secret_key'
    }
    return context


@pytest.fixture
def mock_message():
    """Создает мок объекта Message."""
    message = MagicMock(spec=Message)
    message.chat_id = 12345
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()
    # Добавляем атрибут message для теста check_balance_command
    message.message = message
    return message


@pytest.fixture
def sample_items():
    """Возвращает примерные данные предметов для тестирования."""
    return [
        {
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {"amount": 2000},  # $20 в центах
            "profit": 400,  # $4 в центах
            "profit_percent": 20.0,
            "game": "csgo",
            "liquidity": "high"
        },
        {
            "title": "AWP | Asiimov (Field-Tested)",
            "price": {"amount": 7500},  # $75 в центах
            "profit": 1125,  # $11.25 в центах
            "profit_percent": 15.0,
            "game": "csgo",
            "liquidity": "medium"
        },
        {
            "title": "Гровая шапка",
            "price": "$50.00",  # Строковое представление
            "profit": "$7.50",  # Строковое представление
            "profit_percent": 15.0,
            "game": "rust",
            "liquidity": "low"
        }
    ]


@pytest.mark.asyncio
async def test_format_results_with_dict_prices(sample_items):
    """Тест форматирования результатов с ценами в виде словаря."""
    mode = "boost_low"
    
    with patch('src.telegram_bot.auto_arbitrage.GAMES', sys.modules['src.dmarket.arbitrage'].GAMES):
        formatted_text = await format_results([sample_items[0]], mode)
        
        assert "AK-47 | Redline" in formatted_text
        assert "$20.00" in formatted_text
        assert "$4.00" in formatted_text
        assert "20.0%" in formatted_text
        assert "CS2" in formatted_text  # Game name
        assert "высокая" in formatted_text  # Liquidity


@pytest.mark.asyncio
async def test_format_results_with_string_prices(sample_items):
    """Тест форматирования результатов с ценами в виде строки."""
    mode = "mid_medium"
    
    with patch('src.telegram_bot.auto_arbitrage.GAMES', sys.modules['src.dmarket.arbitrage'].GAMES):
        formatted_text = await format_results([sample_items[2]], mode)
        
        assert "Гровая шапка" in formatted_text
        assert "$50.00" in formatted_text
        assert "$7.50" in formatted_text
        assert "15.0%" in formatted_text
        assert "Rust" in formatted_text  # Game name
        assert "низкая" in formatted_text  # Liquidity


@pytest.mark.asyncio
async def test_format_results_no_items():
    """Тест форматирования пустого списка предметов."""
    mode = "boost_low"
    
    with patch('src.telegram_bot.auto_arbitrage.ARBITRAGE_MODES', ARBITRAGE_MODES):
        formatted_text = await format_results([], mode)
        
        assert "Нет данных" in formatted_text
        # Проверяем наличие описания режима, а не сырого ключа
        assert "разгон баланса" in formatted_text.lower()


@pytest.mark.asyncio
async def test_show_auto_stats_with_pagination_has_items(
    mock_callback_query, mock_context, sample_items
):
    """Тест отображения статистики автоматического арбитража с предметами."""
    # Настраиваем моки локально для этого теста
    with patch('src.telegram_bot.pagination.pagination_manager.get_page') as mock_get_page, \
         patch('src.telegram_bot.pagination.pagination_manager.get_mode') as mock_get_mode, \
         patch('src.telegram_bot.auto_arbitrage.format_results') as mock_format_results, \
         patch('src.telegram_bot.auto_arbitrage.get_back_to_arbitrage_keyboard') as mock_get_keyboard, \
         patch('src.telegram_bot.auto_arbitrage.ParseMode', ParseMode):
        
        # Настраиваем моки
        mock_get_page.return_value = (sample_items, 0, 2)  # items, current_page, total_pages
        mock_get_mode.return_value = "boost_low"
        mock_format_results.return_value = "Отформатированный текст с предметами"
        mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)
        
        # Вызываем тестируемую функцию
        await show_auto_stats_with_pagination(mock_callback_query, mock_context)
        
        # Проверяем вызовы
        mock_get_page.assert_called_once_with(mock_callback_query.from_user.id)
        mock_get_mode.assert_called_once_with(mock_callback_query.from_user.id)
        mock_format_results.assert_called_once_with(sample_items, "boost_low", mock_context.user_data.get("current_game", "csgo"))
        mock_callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_show_auto_stats_with_pagination_no_items(
    mock_callback_query, mock_context
):
    """Тест отображения статистики автоматического арбитража без предметов."""
    # Настраиваем моки локально для этого теста
    with patch('src.telegram_bot.pagination.pagination_manager.get_page') as mock_get_page, \
         patch('src.telegram_bot.auto_arbitrage.get_back_to_arbitrage_keyboard') as mock_get_keyboard, \
         patch('src.telegram_bot.auto_arbitrage.ParseMode', ParseMode):
        
        # Настраиваем моки
        mock_get_page.return_value = ([], 0, 0)  # no items
        mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)
        
        # Вызываем тестируемую функцию
        await show_auto_stats_with_pagination(mock_callback_query, mock_context)
        
        # Проверяем вызовы
        mock_get_page.assert_called_once_with(mock_callback_query.from_user.id)
        mock_callback_query.edit_message_text.assert_called_once()
        
        # Проверяем содержимое сообщения без указания конкретных имен параметров
        args, kwargs = mock_callback_query.edit_message_text.call_args
        assert "Нет данных" in (args[0] if args else kwargs.get('text', ''))


@pytest.mark.asyncio
async def test_handle_pagination_next(
    mock_callback_query, mock_context
):
    """Тест пагинации вперед."""
    # Настраиваем моки локально для этого теста
    with patch('src.telegram_bot.pagination.pagination_manager.next_page') as mock_next_page, \
         patch('src.telegram_bot.auto_arbitrage.show_auto_stats_with_pagination') as mock_show_stats:
            
        # Вызываем тестируемую функцию
        await handle_pagination(mock_callback_query, mock_context, "next", "boost_low")
        
        # Проверяем вызовы
        mock_next_page.assert_called_once_with(mock_callback_query.from_user.id)
        mock_show_stats.assert_called_once_with(mock_callback_query, mock_context)


@pytest.mark.asyncio
async def test_handle_pagination_prev(
    mock_callback_query, mock_context
):
    """Тест пагинации назад."""
    # Настраиваем моки локально для этого теста
    with patch('src.telegram_bot.pagination.pagination_manager.prev_page') as mock_prev_page, \
         patch('src.telegram_bot.auto_arbitrage.show_auto_stats_with_pagination') as mock_show_stats:
            
        # Вызываем тестируемую функцию
        await handle_pagination(mock_callback_query, mock_context, "prev", "boost_low")
        
        # Проверяем вызовы
        mock_prev_page.assert_called_once_with(mock_callback_query.from_user.id)
        mock_show_stats.assert_called_once_with(mock_callback_query, mock_context)


@pytest.mark.asyncio
@patch.dict('os.environ', {"DMARKET_PUBLIC_KEY": "test_key", "DMARKET_SECRET_KEY": "test_secret", "DMARKET_API_URL": "https://test-api.com"})
async def test_create_dmarket_api_client_from_env(mock_context):
    """Тест создания клиента DMarket API из переменных окружения."""
    # Очищаем переменные в контексте
    mock_context.bot_data = {}
    
    # Вызываем тестируемую функцию
    client = await create_dmarket_api_client(mock_context)
    
    # Проверяем результат
    assert client is not None
    assert client.public_key == "test_key"
    assert client.secret_key == b"test_secret"
    assert client.api_url == "https://test-api.com"


@pytest.mark.asyncio
@patch.dict('os.environ', {})  # Пустые переменные окружения
async def test_create_dmarket_api_client_from_context(mock_context):
    """Тест создания клиента DMarket API из контекста."""
    # Устанавливаем переменные в контексте
    mock_context.bot_data = {
        'dmarket_public_key': 'context_key',
        'dmarket_secret_key': 'context_secret'
    }
    
    # Патчим создание клиента
    with patch('src.telegram_bot.auto_arbitrage.DMarketAPI', DMarketAPI):
        # Вызываем тестируемую функцию
        client = await create_dmarket_api_client(mock_context)
        
        # Проверяем результат
        assert client is not None
        assert client.public_key == "context_key"
        assert client.secret_key == b"context_secret"
        assert client.api_url == "https://api.dmarket.com"  # Значение по умолчанию


@pytest.mark.asyncio
@patch.dict('os.environ', {})  # Пустые переменные окружения
async def test_create_dmarket_api_client_no_keys(mock_context):
    """Тест создания клиента DMarket API без ключей."""
    # Очищаем переменные в контексте
    mock_context.bot_data = {}
    
    # Используем правильный патч для интерцепта создания клиента
    with patch('src.telegram_bot.auto_arbitrage.DMarketAPI', side_effect=Exception("No API keys")):
        # Вызываем тестируемую функцию
        client = await create_dmarket_api_client(mock_context)
        
        # Проверяем результат
        assert client is None


@pytest.mark.asyncio
async def test_start_auto_trading_balance_check(
    mock_callback_query, mock_context, sample_items
):
    """Тест запуска автоматического арбитража с проверкой баланса."""
    # Настраиваем моки локально для этого теста
    with patch('src.telegram_bot.auto_arbitrage.create_dmarket_api_client') as mock_create_client, \
         patch('src.telegram_bot.auto_arbitrage.check_user_balance') as mock_check_balance, \
         patch('src.telegram_bot.auto_arbitrage.pagination_manager.add_items_for_user') as mock_add_items, \
         patch('src.telegram_bot.auto_arbitrage.pagination_manager.get_page') as mock_get_page, \
         patch('src.telegram_bot.auto_arbitrage.format_results') as mock_format_results, \
         patch('src.telegram_bot.auto_arbitrage.get_auto_arbitrage_keyboard') as mock_get_keyboard, \
         patch('src.telegram_bot.auto_arbitrage.scan_multiple_games', tests.mock_auto_arbitrage_scanner.scan_multiple_games), \
         patch('src.telegram_bot.auto_arbitrage.ParseMode', ParseMode):
        
        # Настраиваем моки
        api_client = MagicMock(spec=DMarketAPI)
        mock_create_client.return_value = api_client
        
        # Настраиваем мок проверки баланса
        mock_check_balance.return_value = {"balance": 50.0, "has_funds": True}
        
        # Устанавливаем режим
        mode = "boost_low"
        
        # Подготавливаем дополнительные моки для успешного выполнения
        mock_add_items.return_value = None
        mock_get_page.return_value = (sample_items, 0, 1)
        mock_format_results.return_value = "Отформатированный текст"
        mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)
        
        # Вызываем тестируемую функцию
        await start_auto_trading(mock_callback_query, mock_context, mode)
        
        # Проверяем, что клиент создан
        mock_create_client.assert_called_once_with(mock_context)
        
        # Проверяем, что баланс проверен
        mock_check_balance.assert_called_once_with(api_client)
        
        # Проверяем обновление текста сообщения
        mock_callback_query.edit_message_text.assert_called()  # Вызывается несколько раз


@pytest.mark.asyncio
async def test_start_auto_trading_insufficient_balance(
    mock_callback_query, mock_context
):
    """Тест запуска автоматического арбитража с недостаточным балансом."""
    # Настраиваем моки локально для этого теста
    with patch('src.telegram_bot.auto_arbitrage.create_dmarket_api_client') as mock_create_client, \
         patch('src.telegram_bot.auto_arbitrage.check_user_balance') as mock_check_balance, \
         patch('src.telegram_bot.auto_arbitrage.get_back_to_arbitrage_keyboard') as mock_get_keyboard, \
         patch('src.telegram_bot.auto_arbitrage.ARBITRAGE_MODES', ARBITRAGE_MODES), \
         patch('src.telegram_bot.auto_arbitrage.ParseMode', ParseMode):
        
        # Настраиваем моки
        api_client = MagicMock(spec=DMarketAPI)
        mock_create_client.return_value = api_client
        
        # Настраиваем мок проверки баланса с недостаточным балансом
        mock_check_balance.return_value = {"balance": 0.5, "has_funds": False}
        
        # Настраиваем клавиатуру
        mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)
        
        # Устанавливаем режим с минимальной ценой 1.0
        mode = "boost_low"
        
        # Вызываем тестируемую функцию
        await start_auto_trading(mock_callback_query, mock_context, mode)
        
        # Проверяем, что клиент создан
        mock_create_client.assert_called_once_with(mock_context)
        
        # Проверяем, что баланс проверен
        mock_check_balance.assert_called_once_with(api_client)
        
        # Проверяем обновление текста сообщения
        mock_callback_query.edit_message_text.assert_called()
        mock_callback_query.edit_message_text.assert_called_with(
            text=mock_ANY,
            parse_mode=ParseMode.HTML,
            reply_markup=mock_ANY
        )
        text = mock_callback_query.edit_message_text.call_args.kwargs['text']
        assert "Недостаточно средств" in text


@pytest.mark.asyncio
async def test_start_auto_trading_no_client(
    mock_callback_query, mock_context
):
    """Тест запуска автоматического арбитража без клиента API."""
    # Настраиваем моки локально для этого теста
    with patch('src.telegram_bot.auto_arbitrage.create_dmarket_api_client') as mock_create_client, \
         patch('src.telegram_bot.auto_arbitrage.get_back_to_arbitrage_keyboard') as mock_get_keyboard, \
         patch('src.telegram_bot.auto_arbitrage.ParseMode', ParseMode):
        
        # Настраиваем мок для отсутствия клиента
        mock_create_client.return_value = None
        
        # Настраиваем клавиатуру
        mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)
        
        # Устанавливаем режим
        mode = "boost_low"
        
        # Вызываем тестируемую функцию
        await start_auto_trading(mock_callback_query, mock_context, mode)
        
        # Проверяем, что клиент создан
        mock_create_client.assert_called_once_with(mock_context)
        
        # Проверяем обновление текста сообщения
        mock_callback_query.edit_message_text.assert_called()
        mock_callback_query.edit_message_text.assert_called_with(
            text=mock_ANY,
            parse_mode=ParseMode.HTML,
            reply_markup=mock_ANY
        )
        text = mock_callback_query.edit_message_text.call_args.kwargs['text']
        assert "Не удалось создать API-клиент" in text


@pytest.mark.asyncio
async def test_start_auto_trading_api_error(
    mock_callback_query, mock_context
):
    """Тест запуска автоматического арбитража с ошибкой API."""
    # Настраиваем моки локально для этого теста
    with patch('src.telegram_bot.auto_arbitrage.create_dmarket_api_client') as mock_create_client, \
         patch('src.telegram_bot.auto_arbitrage.check_user_balance') as mock_check_balance, \
         patch('src.telegram_bot.auto_arbitrage.handle_api_error') as mock_handle_error, \
         patch('src.telegram_bot.auto_arbitrage.get_back_to_arbitrage_keyboard') as mock_get_keyboard, \
         patch('src.telegram_bot.auto_arbitrage.ParseMode', ParseMode):
        
        # Настраиваем моки
        api_client = MagicMock(spec=DMarketAPI)
        mock_create_client.return_value = api_client
        
        # Настраиваем мок проверки баланса с возникновением ошибки
        api_error = MockAPIError("Test error", 400)
        mock_check_balance.side_effect = api_error
        
        # Настраиваем обработчик ошибки
        mock_handle_error.return_value = "Обработанная ошибка API"
        
        # Настраиваем клавиатуру
        mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)
        
        # Устанавливаем режим
        mode = "boost_low"
        
        # Вызываем тестируемую функцию
        await start_auto_trading(mock_callback_query, mock_context, mode)
        
        # Проверяем, что клиент создан
        mock_create_client.assert_called_once_with(mock_context)
        
        # Проверяем, что обработчик ошибки вызван
        mock_handle_error.assert_called_once_with(api_error)
        
        # Проверяем обновление текста сообщения
        mock_callback_query.edit_message_text.assert_called()
        mock_callback_query.edit_message_text.assert_called_with(
            text=mock_ANY,
            parse_mode=ParseMode.HTML,
            reply_markup=mock_ANY
        )
        text = mock_callback_query.edit_message_text.call_args.kwargs['text']
        assert "Ошибка при проверке баланса" in text


@pytest.mark.asyncio
async def test_check_balance_command(
    mock_message, mock_context
):
    """Тест команды проверки баланса."""
    # Настраиваем моки локально для этого теста
    with patch('src.telegram_bot.auto_arbitrage.create_dmarket_api_client') as mock_create_client, \
         patch('src.telegram_bot.auto_arbitrage.get_back_to_arbitrage_keyboard') as mock_get_keyboard, \
         patch('src.telegram_bot.auto_arbitrage.ParseMode', ParseMode), \
         patch('src.telegram_bot.auto_arbitrage.check_user_balance', return_value={
             "balance": 100.0,
             "has_funds": True,
             "available_balance": 95.0,
             "total_balance": 105.0
         }), \
         patch.object(DMarketAPI, 'get_user_balance', return_value={
             "usd": {"amount": 10000},  # $100 в центах
             "has_funds": True,
             "balance": 100.0,
             "available_balance": 95.0,
             "total_balance": 105.0,
         }):
        
        # Настраиваем моки
        api_client = MagicMock(spec=DMarketAPI)
        mock_create_client.return_value = api_client
        
        # Настраиваем клавиатуру
        mock_get_keyboard.return_value = MagicMock(spec=InlineKeyboardMarkup)
        
        # Вызываем тестируемую функцию
        await check_balance_command(mock_message, mock_context)
        
        # Проверяем, что сообщение было отправлено
        mock_message.reply_text.assert_called()
        
        # Проверяем содержимое сообщения без указания конкретных имен параметров
        args, kwargs = mock_message.reply_text.call_args
        assert "Проверка баланса" in (args[0] if args else kwargs.get('text', '')) 