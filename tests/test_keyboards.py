"""
Тесты для модуля keyboards, проверяющие создание различных клавиатур для Telegram-бота.
"""

import pytest
from unittest.mock import patch

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.telegram_bot.keyboards import (
    get_arbitrage_keyboard,
    get_game_selection_keyboard,
    get_auto_arbitrage_keyboard,
    get_back_to_arbitrage_keyboard
)


def test_get_arbitrage_keyboard():
    """Проверяет создание клавиатуры для выбора режима арбитража."""
    keyboard = get_arbitrage_keyboard()
    
    # Проверяем, что возвращается правильный тип
    assert isinstance(keyboard, InlineKeyboardMarkup)
    
    # Проверяем количество строк в клавиатуре
    assert len(keyboard.inline_keyboard) == 5
    
    # Проверяем первую строку клавиатуры (кнопки разгона и среднего трейдера)
    first_row = keyboard.inline_keyboard[0]
    assert len(first_row) == 2
    assert first_row[0].text == "🚀 Разгон баланса"
    assert first_row[0].callback_data == "arbitrage_boost"
    assert first_row[1].text == "💼 Средний трейдер"
    assert first_row[1].callback_data == "arbitrage_mid"
    
    # Проверяем последнюю кнопку (возврат в меню)
    last_row = keyboard.inline_keyboard[-1]
    assert len(last_row) == 1
    assert "Назад в меню" in last_row[0].text
    assert last_row[0].callback_data == "back_to_menu"


def test_get_game_selection_keyboard():
    """Проверяет создание клавиатуры для выбора игры."""
    # Моделируем словарь игр для тестирования
    mock_games = {
        "csgo": "CS:GO",
        "dota2": "Dota 2",
        "rust": "Rust",
        "tf2": "Team Fortress 2"
    }
    
    with patch('src.telegram_bot.keyboards.GAMES', mock_games):
        keyboard = get_game_selection_keyboard()
    
    # Проверяем, что возвращается правильный тип
    assert isinstance(keyboard, InlineKeyboardMarkup)
    
    # Проверяем количество строк в клавиатуре (2 строки с играми + 1 строка с кнопкой назад)
    assert len(keyboard.inline_keyboard) == 3
    
    # Проверяем, что все игры присутствуют
    all_buttons = [button for row in keyboard.inline_keyboard for button in row]
    
    # Исключая кнопку "Назад"
    game_buttons = [button for button in all_buttons if button.callback_data != "arbitrage"]
    assert len(game_buttons) == 4
    
    # Проверяем тексты кнопок и callback_data
    game_texts = [button.text for button in game_buttons]
    game_callbacks = [button.callback_data for button in game_buttons]
    
    assert "CS:GO" in game_texts
    assert "Dota 2" in game_texts
    assert "Rust" in game_texts
    assert "Team Fortress 2" in game_texts
    
    assert "game:csgo" in game_callbacks
    assert "game:dota2" in game_callbacks
    assert "game:rust" in game_callbacks
    assert "game:tf2" in game_callbacks
    
    # Проверяем кнопку "Назад"
    back_button = [button for button in all_buttons if button.callback_data == "arbitrage"][0]
    assert "Назад" in back_button.text


def test_get_auto_arbitrage_keyboard():
    """Проверяет создание клавиатуры для автоматического арбитража."""
    keyboard = get_auto_arbitrage_keyboard()
    
    # Проверяем, что возвращается правильный тип
    assert isinstance(keyboard, InlineKeyboardMarkup)
    
    # Проверяем количество строк в клавиатуре
    assert len(keyboard.inline_keyboard) == 5
    
    # Проверяем наличие всех режимов
    all_buttons = [button for row in keyboard.inline_keyboard for button in row]
    callback_data = [button.callback_data for button in all_buttons]
    
    assert "auto_start:auto_low" in callback_data
    assert "auto_start:auto_medium" in callback_data
    assert "auto_start:auto_high" in callback_data
    assert "auto_stats" in callback_data
    assert "arbitrage" in callback_data


def test_get_back_to_arbitrage_keyboard():
    """Проверяет создание клавиатуры с кнопкой возврата."""
    keyboard = get_back_to_arbitrage_keyboard()
    
    # Проверяем, что возвращается правильный тип
    assert isinstance(keyboard, InlineKeyboardMarkup)
    
    # Проверяем одну строку с одной кнопкой
    assert len(keyboard.inline_keyboard) == 1
    assert len(keyboard.inline_keyboard[0]) == 1
    
    # Проверяем кнопку
    button = keyboard.inline_keyboard[0][0]
    assert "Назад к меню арбитража" in button.text
    assert button.callback_data == "arbitrage"
