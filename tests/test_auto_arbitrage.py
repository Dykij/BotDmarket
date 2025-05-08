"""
Модульные тесты для модуля автоматического арбитража.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from src.telegram_bot.auto_arbitrage import (
    format_results, 
    show_auto_stats_with_pagination, 
    handle_pagination,
    start_auto_trading,
    stop_auto_trading
)


@pytest.fixture
def mock_query():
    """Создает мок объекта callback query."""
    query = MagicMock()
    query.from_user = MagicMock()
    query.from_user.id = 12345
    query.edit_message_text = AsyncMock()
    return query


@pytest.fixture
def mock_context():
    """Создает мок объекта контекста."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {"current_game": "csgo"}
    return context


@pytest.mark.asyncio
async def test_format_results():
    """Тест функции форматирования результатов автоарбитража."""
    items = [
        {
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {"amount": 1000},
            "profit": 100,
            "profit_percent": 10.0
        },
        {
            "title": "AWP | Asiimov (Field-Tested)",
            "price": {"amount": 3000},
            "profit": 300,
            "profit_percent": 10.0
        }
    ]
    
    result = await format_results(items, "mid_medium", "csgo")
    # Проверяем, что результат содержит заголовок
    assert "🤖 Результаты автоматического арбитража" in result
    # Проверяем, что результат содержит названия предметов
    assert "AK-47 | Redline" in result
    assert "AWP | Asiimov" in result
    # Проверяем, что результат содержит информацию о цене и прибыли
    assert "$10.00" in result  # Цена AK-47
    assert "$30.00" in result  # Цена AWP
    # В новой версии функции прибыль отображается в формате $100.00 вместо $1.00
    assert "$100.00" in result  # Прибыль AK-47
    assert "$300.00" in result  # Прибыль AWP
    assert "10.0%" in result   # Процент прибыли


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
async def test_handle_pagination_next(mock_pagination_manager, mock_query, mock_context):
    """Тест обработки пагинации - следующая страница."""
    mock_pagination_manager.next_page = MagicMock()
    
    # Мокаем функцию show_auto_stats_with_pagination
    with patch("src.telegram_bot.auto_arbitrage.show_auto_stats_with_pagination", new=AsyncMock()) as mock_show:
        await handle_pagination(mock_query, mock_context, "next", "mid_medium")
        
        # Проверяем, что был вызван метод next_page менеджера пагинации
        mock_pagination_manager.next_page.assert_called_once_with(mock_query.from_user.id)
        # Проверяем, что была вызвана функция отображения результатов
        mock_show.assert_called_once_with(mock_query, mock_context)


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
async def test_handle_pagination_prev(mock_pagination_manager, mock_query, mock_context):
    """Тест обработки пагинации - предыдущая страница."""
    mock_pagination_manager.prev_page = MagicMock()
    
    # Мокаем функцию show_auto_stats_with_pagination
    with patch("src.telegram_bot.auto_arbitrage.show_auto_stats_with_pagination", new=AsyncMock()) as mock_show:
        await handle_pagination(mock_query, mock_context, "prev", "mid_medium")
        
        # Проверяем, что был вызван метод prev_page менеджера пагинации
        mock_pagination_manager.prev_page.assert_called_once_with(mock_query.from_user.id)
        # Проверяем, что была вызвана функция отображения результатов
        mock_show.assert_called_once_with(mock_query, mock_context)


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.format_results")
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
@patch("src.telegram_bot.auto_arbitrage.InlineKeyboardMarkup")
@patch("src.telegram_bot.auto_arbitrage.InlineKeyboardButton")
@patch("src.telegram_bot.auto_arbitrage.get_back_to_arbitrage_keyboard")
async def test_show_auto_stats_with_pagination_with_items(
    mock_get_keyboard, 
    mock_button, 
    mock_markup,
    mock_pagination_manager, 
    mock_format_results, 
    mock_query, 
    mock_context
):
    """Тест отображения статистики автоарбитража с пагинацией - с данными."""
    # Настройка моков
    mock_pagination_manager.get_page.return_value = (
        [{"title": "Test Item"}], 
        0,  # current_page
        2   # total_pages
    )
    
    mock_pagination_manager.get_mode.return_value = "mid_medium"
    mock_format_results.return_value = "Форматированный текст"
    mock_markup.return_value = "keyboard_markup"
    mock_get_keyboard.return_value = "back_keyboard"
    
    # Вызов тестируемой функции
    await show_auto_stats_with_pagination(mock_query, mock_context)
    
    # Проверки
    mock_pagination_manager.get_page.assert_called_once_with(mock_query.from_user.id)
    mock_format_results.assert_called_once()
    mock_query.edit_message_text.assert_called_once()
    
    # Проверяем наличие параметров в вызове edit_message_text
    call_kwargs = mock_query.edit_message_text.call_args[1]
    assert "text" in call_kwargs
    assert "reply_markup" in call_kwargs


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.format_results")
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
@patch("src.telegram_bot.auto_arbitrage.get_back_to_arbitrage_keyboard")
async def test_show_auto_stats_with_pagination_no_items(
    mock_get_keyboard, 
    mock_pagination_manager, 
    mock_format_results, 
    mock_query, 
    mock_context
):
    """Тест отображения статистики автоарбитража с пагинацией - без данных."""
    # Настройка моков
    mock_pagination_manager.get_page.return_value = (
        [],   # пустой список предметов
        0,    # current_page
        0     # total_pages
    )
    
    mock_pagination_manager.get_mode.return_value = "mid_medium"
    mock_get_keyboard.return_value = "back_keyboard"
    
    # Вызов тестируемой функции
    await show_auto_stats_with_pagination(mock_query, mock_context)
    
    # Проверки
    mock_pagination_manager.get_page.assert_called_once_with(mock_query.from_user.id)
    mock_format_results.assert_not_called()  # Не должно быть вызова, т.к. нет предметов
    
    # Проверяем параметры вызова edit_message_text
    mock_query.edit_message_text.assert_called_once()
    call_kwargs = mock_query.edit_message_text.call_args[1]
    assert "ℹ️ Нет данных об автоматическом арбитраже" in call_kwargs["text"]
    assert call_kwargs["reply_markup"] == "back_keyboard"


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.scan_multiple_games")
@patch("src.telegram_bot.auto_arbitrage.check_user_balance")
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
@patch("os.environ.get")
@patch("src.telegram_bot.auto_arbitrage.DMarketAPI")
async def test_start_auto_trading_boost_low(
    mock_dmarket_api,
    mock_env_get,
    mock_pagination_manager,
    mock_check_balance,
    mock_scan_games,
    mock_query,
    mock_context
):
    """Тест запуска автоарбитража в режиме разгона баланса (boost_low)."""
    # Настраиваем моки
    mock_context.bot_data = {
        'dmarket_public_key': 'test_public_key',
        'dmarket_secret_key': 'test_secret_key'
    }
    mock_check_balance.return_value = {'balance': 100.0}  # Достаточно средств
    mock_scan_games.return_value = []  # Пустой результат для простоты
    mock_dmarket_api.return_value = MagicMock()
    mock_pagination_manager.get_page.return_value = ([], 0, 0)
    
    # Мокаем импорт модулей из intramarket_arbitrage, используя create=True для создания мока
    with patch("src.telegram_bot.auto_arbitrage.find_price_anomalies", return_value=[], create=True):
        # Вызываем функцию
        await start_auto_trading(mock_query, mock_context, "boost_low")
        
        # Проверяем, что все ожидаемые функции были вызваны
        mock_query.edit_message_text.assert_called()  # Должно быть несколько вызовов
        mock_check_balance.assert_called_once()
        mock_scan_games.assert_called_once()
        
        # Проверяем, что сканирование выполняется для всех игр
        scan_games_call = mock_scan_games.call_args
        assert 'games' in scan_games_call[1]
        assert isinstance(scan_games_call[1]['games'], list)
        assert len(scan_games_call[1]['games']) > 0  # Должен быть непустой список игр
        
        # Проверяем параметры для режима boost_low
        assert scan_games_call[1]['min_price'] < 50.0  # Нижний порог цены для режима boost
        assert scan_games_call[1]['min_profit_percent'] <= 10.0  # Небольшой порог прибыли для быстрого оборота


@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.scan_multiple_games")
@patch("src.telegram_bot.auto_arbitrage.check_user_balance")
@patch("src.telegram_bot.auto_arbitrage.pagination_manager")
@patch("os.environ.get")
@patch("src.telegram_bot.auto_arbitrage.DMarketAPI")
async def test_start_auto_trading_mid_medium(
    mock_dmarket_api,
    mock_env_get,
    mock_pagination_manager,
    mock_check_balance,
    mock_scan_games,
    mock_query,
    mock_context
):
    """Тест запуска автоарбитража в режиме среднего трейдера (mid_medium)."""
    # Настраиваем моки
    mock_context.bot_data = {
        'dmarket_public_key': 'test_public_key',
        'dmarket_secret_key': 'test_secret_key'
    }
    mock_check_balance.return_value = {'balance': 200.0}  # Достаточно средств
    mock_scan_games.return_value = []  # Пустой результат для простоты
    mock_dmarket_api.return_value = MagicMock()
    mock_pagination_manager.get_page.return_value = ([], 0, 0)
    
    # Мокаем импорт модулей из intramarket_arbitrage, используя create=True для создания мока
    with patch("src.telegram_bot.auto_arbitrage.find_price_anomalies", return_value=[], create=True) as mock_find_anomalies, \
         patch("src.telegram_bot.auto_arbitrage.find_trending_items", return_value=[], create=True) as mock_find_trending:
        
        # Вызываем функцию
        await start_auto_trading(mock_query, mock_context, "mid_medium")
        
        # Проверяем, что все ожидаемые функции были вызваны
        mock_query.edit_message_text.assert_called()  # Должно быть несколько вызовов
        mock_check_balance.assert_called_once()
        mock_scan_games.assert_called_once()
        
        # Проверяем параметры для режима mid_medium
        scan_games_call = mock_scan_games.call_args
        assert scan_games_call[1]['min_price'] >= 10.0  # Средний порог цены
        assert scan_games_call[1]['min_profit_percent'] >= 10.0  # Средний порог прибыли
