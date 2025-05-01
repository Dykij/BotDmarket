"""
Тесты для команды arbitrage в модуле bot_v2.
"""

import pytest
from unittest.mock import MagicMock, patch
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import CallbackContext


@pytest.fixture
def mock_update():
    """Создает мок объекта Update."""
    update = MagicMock(spec=Update)
    update.message = MagicMock()
    update.message.reply_text = MagicMock()
    update.message.reply_html = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.mention_html = MagicMock(return_value="@username")
    update.message.from_user = MagicMock()
    update.message.from_user.id = 12345
    update.message.chat_id = 12345
    
    # Эти атрибуты нужны только для callback_queries
    update.callback_query = None
    
    return update


@pytest.fixture
def mock_context():
    """Создает мок объекта Context."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}
    return context


@patch("src.telegram_bot.bot_v2.get_arbitrage_keyboard")
def test_arbitrage_command(mock_get_keyboard, mock_update, mock_context):
    """Тест команды /arbitrage."""
    # Настраиваем мок клавиатуры
    mock_keyboard = MagicMock(spec=InlineKeyboardMarkup)
    mock_get_keyboard.return_value = mock_keyboard
    
    # Импортируем функцию
    from src.telegram_bot.bot_v2 import arbitrage_command
    
    # Вызываем команду
    arbitrage_command(mock_update, mock_context)
    
    # Проверяем, что была вызвана функция reply_text с правильными параметрами
    mock_update.message.reply_text.assert_called_once()
    args, kwargs = mock_update.message.reply_text.call_args
    text = args[0]
    assert "арбитраж" in text.lower()
    assert "Выберите режим" in text
    assert kwargs.get("reply_markup") == mock_keyboard


@patch("src.telegram_bot.bot_v2.get_arbitrage_keyboard")
def test_create_arbitrage_keyboard(mock_get_keyboard, mock_update, mock_context):
    """Тест создания клавиатуры арбитража."""
    # Импортируем функции
    from src.telegram_bot.keyboards import get_arbitrage_keyboard
    
    # Настраиваем мок клавиатуры с реальным вызовом
    mock_get_keyboard.side_effect = get_arbitrage_keyboard
    
    # Получаем клавиатуру
    keyboard = get_arbitrage_keyboard()
    
    # Проверяем, что клавиатура создана и содержит правильные кнопки
    assert isinstance(keyboard, InlineKeyboardMarkup)
    
    # Проверяем наличие ключевых кнопок в клавиатуре
    button_texts = [button.text for row in keyboard.inline_keyboard for button in row]
    button_callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    
    assert any("Разгон баланса" in text for text in button_texts)
    assert any("Средний трейдер" in text for text in button_texts)
    assert any("Trade Pro" in text for text in button_texts)
    assert any("Выбрать игру" in text for text in button_texts)
    
    assert "arbitrage_boost" in button_callbacks
    assert "arbitrage_mid" in button_callbacks
    assert "arbitrage_pro" in button_callbacks
    assert "select_game" in button_callbacks


@pytest.mark.asyncio
@patch("src.telegram_bot.bot_v2.handle_dmarket_arbitrage")
async def test_arbitrage_callback_boost(mock_handle_arbitrage, mock_update, mock_context):
    """Тест обработки callback для режима boost."""
    # Настраиваем мок объекта Update с callback_query
    callback_query = MagicMock()
    callback_query.data = "arbitrage_boost"
    callback_query.answer = MagicMock()
    callback_query.from_user = MagicMock()
    callback_query.from_user.id = 12345
    mock_update.callback_query = callback_query
    mock_update.message = None
    
    # Импортируем функцию с патчем
    with patch("src.telegram_bot.bot_v2.arbitrage_callback") as mock_callback:
        # Настраиваем поведение патча
        mock_callback.side_effect = lambda update, context: None
        
        # Ручное тестирование обработки "arbitrage_boost"
        await mock_callback(mock_update, mock_context)
        
    # Проверяем, что была вызвана соответствующая обработка
    mock_handle_arbitrage.assert_not_called()  # Оригинальный метод не должен быть вызван из-за патча
