"""Объединенные тесты для модулей автоматического арбитража.

Этот модуль содержит тесты для проверки:
1. Генерации случайных предметов
2. Фильтрации предметов по режимам арбитража
3. Демонстрационного режима арбитража
4. Взаимодействия с API для арбитражных операций
5. Обработки пагинации в арбитраже
6. Форматирования результатов арбитража
7. Интеграцию с Telegram ботом
"""

import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from telegram.ext import CallbackContext

# Импортируем необходимые модули для тестирования
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from dmarket.auto_arbitrage import (
    GAMES,
    arbitrage_boost,
    arbitrage_mid,
    arbitrage_pro,
    auto_arbitrage_demo,
    generate_random_items,
    main as auto_arbitrage_main
)

try:
    from src.telegram_bot.auto_arbitrage import (
        format_results,
        handle_pagination,
        show_auto_stats_with_pagination,
        start_auto_trading,
        pagination_manager
    )
except ImportError:
    # Мокаем модуль, если он не доступен
    format_results = AsyncMock()
    handle_pagination = AsyncMock()
    show_auto_stats_with_pagination = AsyncMock()
    start_auto_trading = AsyncMock()
    pagination_manager = MagicMock()

# Фикстуры для Telegram-бота

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

# Тесты генерации случайных предметов

def test_generate_random_items():
    """Тестирует генерацию случайных предметов для тестирования арбитража."""
    # Тестируем с разными играми и количеством предметов
    items_csgo = generate_random_items("csgo", 5)
    items_dota2 = generate_random_items("dota2", 10)

    # Проверяем количество сгенерированных предметов
    assert len(items_csgo) == 5
    assert len(items_dota2) == 10

    # Проверяем структуру предметов
    for item in items_csgo:
        assert "id" in item
        assert "game" in item
        assert "price" in item
        assert "profit" in item
        assert item["game"] == "csgo"
        assert isinstance(item["price"], float)
        assert isinstance(item["profit"], float)

    for item in items_dota2:
        assert "id" in item
        assert "game" in item
        assert "price" in item
        assert "profit" in item
        assert item["game"] == "dota2"

# Тесты режимов арбитража

def test_arbitrage_boost():
    """Тестирует режим 'Разгон баланса' (низкая прибыль, быстрые сделки)."""
    # Создаем мок для функции generate_random_items
    mock_items = [
        {"id": "item_1", "game": "csgo", "price": 10.0, "profit": -5.0},
        {"id": "item_2", "game": "csgo", "price": 20.0, "profit": 2.0},
        {"id": "item_3", "game": "csgo", "price": 30.0, "profit": -2.0},
    ]

    with patch("dmarket.auto_arbitrage.generate_random_items", return_value=mock_items):
        result = arbitrage_boost("csgo")

        # Проверяем, что возвращены только предметы с отрицательной прибылью
        assert len(result) == 2
        assert all(item["profit"] < 0 for item in result)
        assert result[0]["id"] == "item_1"
        assert result[1]["id"] == "item_3"

def test_arbitrage_mid():
    """Тестирует режим 'Средний трейдер' (средняя прибыль)."""
    # Создаем мок для функции generate_random_items
    mock_items = [
        {"id": "item_1", "game": "csgo", "price": 10.0, "profit": -5.0},
        {"id": "item_2", "game": "csgo", "price": 20.0, "profit": 2.0},
        {"id": "item_3", "game": "csgo", "price": 30.0, "profit": 4.5},
        {"id": "item_4", "game": "csgo", "price": 40.0, "profit": 7.0},
    ]

    with patch("dmarket.auto_arbitrage.generate_random_items", return_value=mock_items):
        result = arbitrage_mid("csgo")

        # Проверяем, что возвращены только предметы с прибылью от 0 до 5
        assert len(result) == 2
        assert all(0 <= item["profit"] < 5 for item in result)
        assert result[0]["id"] == "item_2"
        assert result[1]["id"] == "item_3"

def test_arbitrage_pro():
    """Тестирует режим 'Trade Pro' (высокая прибыль)."""
    # Создаем мок для функции generate_random_items
    mock_items = [
        {"id": "item_1", "game": "csgo", "price": 10.0, "profit": -5.0},
        {"id": "item_2", "game": "csgo", "price": 20.0, "profit": 2.0},
        {"id": "item_3", "game": "csgo", "price": 30.0, "profit": 4.5},
        {"id": "item_4", "game": "csgo", "price": 40.0, "profit": 7.0},
        {"id": "item_5", "game": "csgo", "price": 50.0, "profit": 10.0},
    ]

    with patch("dmarket.auto_arbitrage.generate_random_items", return_value=mock_items):
        result = arbitrage_pro("csgo")

        # Проверяем, что возвращены только предметы с прибылью от 5 и выше
        assert len(result) == 2
        assert all(item["profit"] >= 5 for item in result)
        assert result[0]["id"] == "item_4"
        assert result[1]["id"] == "item_5"

# Тесты демонстрационного режима

@pytest.mark.asyncio
async def test_auto_arbitrage_demo():
    """Тестирует демонстрацию работы автоматического арбитража."""
    # Создаем моки
    mock_items_low = [
        {"id": "item_1", "game": "csgo", "price": 10.0, "profit": -2.0},
    ]
    mock_items_medium = [
        {"id": "item_2", "game": "csgo", "price": 20.0, "profit": 3.0},
    ]
    mock_items_high = [
        {"id": "item_3", "game": "csgo", "price": 30.0, "profit": 8.0},
    ]

    # Патчим функции и asyncio.sleep для ускорения теста
    with patch("dmarket.auto_arbitrage.arbitrage_boost", return_value=mock_items_low), \
         patch("dmarket.auto_arbitrage.arbitrage_mid", return_value=mock_items_medium), \
         patch("dmarket.auto_arbitrage.arbitrage_pro", return_value=mock_items_high), \
         patch("asyncio.sleep", new_callable=AsyncMock), \
         patch("builtins.print") as mock_print:
        
        # Запускаем демонстрацию с разными режимами
        await auto_arbitrage_demo(game="csgo", mode="low", iterations=1)
        await auto_arbitrage_demo(game="csgo", mode="medium", iterations=1)
        await auto_arbitrage_demo(game="csgo", mode="high", iterations=1)
        
        # Проверяем, что вызовы print были с правильными аргументами
        expected_calls = [
            call(f"Итерация арбитража для {GAMES['csgo']} в режиме low:"),
            call(f"- {mock_items_low[0]['id']}: прибыль {mock_items_low[0]['profit']:.2f}, цена {mock_items_low[0]['price']:.2f}"),
            call(f"Итерация арбитража для {GAMES['csgo']} в режиме medium:"),
            call(f"- {mock_items_medium[0]['id']}: прибыль {mock_items_medium[0]['profit']:.2f}, цена {mock_items_medium[0]['price']:.2f}"),
            call(f"Итерация арбитража для {GAMES['csgo']} в режиме high:"),
            call(f"- {mock_items_high[0]['id']}: прибыль {mock_items_high[0]['profit']:.2f}, цена {mock_items_high[0]['price']:.2f}"),
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)

# Тесты GAMES

def test_games_constants():
    """Тестирует константы GAMES."""
    assert "csgo" in GAMES
    assert "dota2" in GAMES
    assert GAMES["csgo"] == "Counter-Strike: Global Offensive"
    assert GAMES["dota2"] == "Dota 2"

# Интеграционные тесты

@pytest.mark.asyncio
async def test_main_flow():
    """Тестирует полный цикл работы модуля."""
    # Патчим asyncio.sleep для ускорения теста
    with patch("asyncio.sleep", new_callable=AsyncMock), \
         patch("builtins.print") as mock_print:
        
        # Патчим функции из модуля
        with patch("dmarket.auto_arbitrage.auto_arbitrage_demo", new_callable=AsyncMock) as mock_demo:
            # Запускаем основную функцию
            await auto_arbitrage_main()
            
            # Проверяем, что auto_arbitrage_demo был вызван для всех комбинаций игр и режимов
            assert mock_demo.call_count == 6
            mock_demo.assert_has_calls([
                call("csgo", "low"),
                call("csgo", "medium"),
                call("csgo", "high"),
                call("dota2", "low"),
                call("dota2", "medium"),
                call("dota2", "high"),
            ], any_order=False)

# Тесты интеграции с Telegram ботом (если модуль доступен)

@pytest.mark.asyncio
async def test_format_results():
    """Тест функции форматирования результатов автоарбитража."""
    if isinstance(format_results, AsyncMock):
        pytest.skip("Модуль telegram_bot.auto_arbitrage недоступен")
        
    items = [
        {
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {"amount": 1000},
            "profit": 100,
            "profit_percent": 10.0,
        },
        {
            "title": "AWP | Asiimov (Field-Tested)",
            "price": {"amount": 3000},
            "profit": 300,
            "profit_percent": 10.0,
        },
    ]

    result = await format_results(items, "mid_medium", "csgo")
    # Проверяем, что результат содержит заголовок
    assert "Результаты автоматического арбитража" in result
    # Проверяем, что результат содержит названия предметов
    assert "AK-47 | Redline" in result
    assert "AWP | Asiimov" in result
    # Проверяем, что результат содержит информацию о цене и прибыли
    assert "$10.00" in result  # Цена AK-47
    assert "$30.00" in result  # Цена AWP
    assert "$100.00" in result  # Прибыль AK-47
    assert "$300.00" in result  # Прибыль AWP
    assert "10.0%" in result  # Процент прибыли

@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.pagination_manager", create=True)
async def test_handle_pagination_next(mock_pagination_manager, mock_query, mock_context):
    """Тест обработки пагинации - следующая страница."""
    if isinstance(handle_pagination, AsyncMock):
        pytest.skip("Модуль telegram_bot.auto_arbitrage недоступен")
        
    mock_pagination_manager.next_page = MagicMock()

    # Мокаем функцию show_auto_stats_with_pagination
    with patch("src.telegram_bot.auto_arbitrage.show_auto_stats_with_pagination", new=AsyncMock()) as mock_show:
        await handle_pagination(mock_query, mock_context, "next", "mid_medium")

        # Проверяем, что был вызван метод next_page менеджера пагинации
        mock_pagination_manager.next_page.assert_called_once_with(mock_query.from_user.id)
        # Проверяем, что была вызвана функция отображения результатов
        mock_show.assert_called_once_with(mock_query, mock_context)

@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.pagination_manager", create=True)
async def test_handle_pagination_prev(mock_pagination_manager, mock_query, mock_context):
    """Тест обработки пагинации - предыдущая страница."""
    if isinstance(handle_pagination, AsyncMock):
        pytest.skip("Модуль telegram_bot.auto_arbitrage недоступен")
        
    mock_pagination_manager.prev_page = MagicMock()

    # Мокаем функцию show_auto_stats_with_pagination
    with patch("src.telegram_bot.auto_arbitrage.show_auto_stats_with_pagination", new=AsyncMock()) as mock_show:
        await handle_pagination(mock_query, mock_context, "prev", "mid_medium")

        # Проверяем, что был вызван метод prev_page менеджера пагинации
        mock_pagination_manager.prev_page.assert_called_once_with(mock_query.from_user.id)
        # Проверяем, что была вызвана функция отображения результатов
        mock_show.assert_called_once_with(mock_query, mock_context)

@pytest.mark.asyncio
@patch("src.telegram_bot.auto_arbitrage.format_results", create=True)
@patch("src.telegram_bot.auto_arbitrage.pagination_manager", create=True)
@patch("src.telegram_bot.auto_arbitrage.InlineKeyboardMarkup", create=True)
@patch("src.telegram_bot.auto_arbitrage.InlineKeyboardButton", create=True)
@patch("src.telegram_bot.auto_arbitrage.get_back_to_arbitrage_keyboard", create=True)
async def test_show_auto_stats_with_pagination_with_items(
    mock_get_keyboard,
    mock_button,
    mock_markup,
    mock_pagination_manager,
    mock_format_results,
    mock_query,
    mock_context,
):
    """Тест отображения статистики автоарбитража с пагинацией - с данными."""
    if isinstance(show_auto_stats_with_pagination, AsyncMock):
        pytest.skip("Модуль telegram_bot.auto_arbitrage недоступен")
        
    # Настройка моков
    mock_pagination_manager.get_page.return_value = (
        [{"title": "Test Item"}],
        0,  # current_page
        2,  # total_pages
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
@patch("src.telegram_bot.auto_arbitrage.scan_multiple_games", create=True)
@patch("src.telegram_bot.auto_arbitrage.check_user_balance", create=True)
@patch("src.telegram_bot.auto_arbitrage.pagination_manager", create=True)
@patch("os.environ.get", create=True)
@patch("src.telegram_bot.auto_arbitrage.DMarketAPI", create=True)
async def test_start_auto_trading_boost_low(
    mock_dmarket_api,
    mock_env_get,
    mock_pagination_manager,
    mock_check_balance,
    mock_scan_games,
    mock_query,
    mock_context,
):
    """Тест запуска автоарбитража в режиме разгона баланса (boost_low)."""
    if isinstance(start_auto_trading, AsyncMock):
        pytest.skip("Модуль telegram_bot.auto_arbitrage недоступен")
        
    # Настраиваем моки
    mock_context.bot_data = {
        "dmarket_public_key": "test_public_key",
        "dmarket_secret_key": "test_secret_key",
    }
    mock_check_balance.return_value = {"balance": 100.0}  # Достаточно средств
    mock_scan_games.return_value = []  # Пустой результат для простоты
    mock_dmarket_api.return_value = MagicMock()
    mock_pagination_manager.get_page.return_value = ([], 0, 0)

    # Мокаем импорт модулей из intramarket_arbitrage
    with patch("src.telegram_bot.auto_arbitrage.find_price_anomalies", return_value=[], create=True):
        # Вызываем функцию
        await start_auto_trading(mock_query, mock_context, "boost_low")

        # Проверяем, что все ожидаемые функции были вызваны
        mock_query.edit_message_text.assert_called()  # Должно быть несколько вызовов
        mock_check_balance.assert_called_once()
        mock_scan_games.assert_called_once()

        # Проверяем, что сканирование выполняется для всех игр
        scan_games_call = mock_scan_games.call_args
        assert "games" in scan_games_call[1]
        assert isinstance(scan_games_call[1]["games"], list)
        assert len(scan_games_call[1]["games"]) > 0  # Должен быть непустой список игр

        # Проверяем параметры для режима boost_low
        assert scan_games_call[1]["min_price"] < 50.0  # Нижний порог цены для режима boost
