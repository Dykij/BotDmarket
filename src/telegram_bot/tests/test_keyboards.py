"""Тесты для модуля keyboards.py.

Этот модуль тестирует функциональность создания клавиатур для Telegram-бота.
"""

from telegram import InlineKeyboardMarkup

from src.telegram_bot.keyboards import (
    get_arbitrage_keyboard,
    get_auto_arbitrage_keyboard,
    get_back_to_arbitrage_keyboard,
    get_back_to_settings_keyboard,
    get_game_selection_keyboard,
    get_language_keyboard,
    get_risk_profile_keyboard,
    get_settings_keyboard,
)


def test_get_arbitrage_keyboard():
    """Тестирует создание клавиатуры арбитража."""
    keyboard = get_arbitrage_keyboard()

    # Проверяем, что клавиатура создана
    assert isinstance(keyboard, InlineKeyboardMarkup)

    # Проверяем количество строк
    assert len(keyboard.inline_keyboard) == 5

    # Проверяем наличие кнопок
    buttons_text = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "🚀 Разгон баланса" in buttons_text
    assert "💼 Средний трейдер" in buttons_text
    assert "💰 Trade Pro" in buttons_text
    assert "🌟 Лучшие возможности" in buttons_text
    assert "🤖 Авто-арбитраж" in buttons_text
    assert "🎮 Выбрать игру" in buttons_text
    assert "⬅️ Назад в меню" in buttons_text

    # Проверяем callback_data
    for row in keyboard.inline_keyboard:
        for button in row:
            if button.text == "🚀 Разгон баланса":
                assert button.callback_data == "arbitrage_boost"
            elif button.text == "💼 Средний трейдер":
                assert button.callback_data == "arbitrage_mid"
            elif button.text == "💰 Trade Pro":
                assert button.callback_data == "arbitrage_pro"
            elif button.text == "🤖 Авто-арбитраж":
                assert button.callback_data == "auto_arbitrage"
            elif button.text == "🎮 Выбрать игру":
                assert button.callback_data == "select_game"
            elif button.text == "⬅️ Назад в меню":
                assert button.callback_data == "back_to_menu"


def test_get_game_selection_keyboard():
    """Тестирует создание клавиатуры выбора игры."""
    keyboard = get_game_selection_keyboard()

    # Проверяем, что клавиатура создана
    assert isinstance(keyboard, InlineKeyboardMarkup)

    # Проверяем наличие кнопок для всех поддерживаемых игр
    buttons_text = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "CS2" in buttons_text or "CS:GO" in buttons_text
    assert "Dota 2" in buttons_text
    assert "Team Fortress 2" in buttons_text
    assert "Rust" in buttons_text
    assert "⬅️ Назад" in buttons_text

    # Проверяем callback_data
    for row in keyboard.inline_keyboard:
        for button in row:
            if "CS" in button.text:  # CS:GO или CS2
                assert button.callback_data == "game:csgo"
            elif button.text == "Dota 2":
                assert button.callback_data == "game:dota2"
            elif button.text == "Team Fortress 2":
                assert button.callback_data == "game:tf2"
            elif button.text == "Rust":
                assert button.callback_data == "game:rust"
            elif button.text == "⬅️ Назад":
                assert button.callback_data == "arbitrage"


def test_get_auto_arbitrage_keyboard():
    """Тестирует создание клавиатуры автоматического арбитража."""
    keyboard = get_auto_arbitrage_keyboard()

    # Проверяем, что клавиатура создана
    assert isinstance(keyboard, InlineKeyboardMarkup)

    # Проверяем количество строк
    assert len(keyboard.inline_keyboard) == 5

    # Проверяем наличие кнопок
    buttons_text = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "💰 Мин. прибыль" in buttons_text
    assert "💰💰 Средняя прибыль" in buttons_text
    assert "💰💰💰 Высокая прибыль" in buttons_text
    assert "📊 Статистика" in buttons_text
    assert "⬅️ Назад" in buttons_text

    # Проверяем callback_data
    for row in keyboard.inline_keyboard:
        for button in row:
            if button.text == "💰 Мин. прибыль":
                assert button.callback_data == "auto_start:auto_low"
            elif button.text == "💰💰 Средняя прибыль":
                assert button.callback_data == "auto_start:auto_medium"
            elif button.text == "💰💰💰 Высокая прибыль":
                assert button.callback_data == "auto_start:auto_high"
            elif button.text == "📊 Статистика":
                assert button.callback_data == "auto_stats"
            elif button.text == "⬅️ Назад":
                assert button.callback_data == "arbitrage"


def test_get_back_to_arbitrage_keyboard():
    """Тестирует создание клавиатуры с кнопкой возврата к меню арбитража."""
    keyboard = get_back_to_arbitrage_keyboard()

    # Проверяем, что клавиатура создана
    assert isinstance(keyboard, InlineKeyboardMarkup)

    # Проверяем количество строк
    assert len(keyboard.inline_keyboard) == 1

    # Проверяем наличие кнопки
    assert keyboard.inline_keyboard[0][0].text == "⬅️ Назад к меню арбитража"
    assert keyboard.inline_keyboard[0][0].callback_data == "arbitrage"


def test_get_settings_keyboard():
    """Тестирует создание клавиатуры настроек."""
    # Проверка с выключенным авто-арбитражем
    keyboard_off = get_settings_keyboard(auto_trading_enabled=False)

    # Проверяем, что клавиатура создана
    assert isinstance(keyboard_off, InlineKeyboardMarkup)

    # Проверяем количество строк
    assert len(keyboard_off.inline_keyboard) == 5

    # Проверяем наличие кнопок
    buttons_text = [button.text for row in keyboard_off.inline_keyboard for button in row]
    assert "🔑 API ключи" in buttons_text
    assert "🌐 Язык" in buttons_text
    assert "🤖 Авто-торговля: ❌ Выкл." in buttons_text
    assert "💰 Лимиты торговли" in buttons_text
    assert "⬅️ Назад в главное меню" in buttons_text

    # Проверка с включенным авто-арбитражем
    keyboard_on = get_settings_keyboard(auto_trading_enabled=True)
    buttons_text = [button.text for row in keyboard_on.inline_keyboard for button in row]
    assert "🤖 Авто-торговля: ✅ Вкл." in buttons_text


def test_get_language_keyboard():
    """Тестирует создание клавиатуры выбора языка."""
    # Проверка с текущим языком - русский
    keyboard_ru = get_language_keyboard(current_language="ru")

    # Проверяем, что клавиатура создана
    assert isinstance(keyboard_ru, InlineKeyboardMarkup)

    # Проверяем наличие кнопок для всех языков
    buttons_text = [button.text for row in keyboard_ru.inline_keyboard for button in row]
    assert "🇷🇺 Русский ✅" in buttons_text  # Отмечен текущий язык
    assert "🇬🇧 English" in buttons_text
    assert "🇪🇸 Español" in buttons_text
    assert "🇩🇪 Deutsch" in buttons_text
    assert "⬅️ Назад к настройкам" in buttons_text

    # Проверка с текущим языком - английский
    keyboard_en = get_language_keyboard(current_language="en")
    buttons_text = [button.text for row in keyboard_en.inline_keyboard for button in row]
    assert "🇷🇺 Русский" in buttons_text
    assert "🇬🇧 English ✅" in buttons_text  # Отмечен текущий язык


def test_get_risk_profile_keyboard():
    """Тестирует создание клавиатуры выбора профиля риска."""
    # Проверка с текущим профилем - средний
    keyboard_medium = get_risk_profile_keyboard(current_profile="medium")

    # Проверяем, что клавиатура создана
    assert isinstance(keyboard_medium, InlineKeyboardMarkup)

    # Проверяем количество строк (3 профиля + кнопка назад)
    assert len(keyboard_medium.inline_keyboard) == 4

    # Проверяем наличие кнопок
    buttons_text = [button.text for row in keyboard_medium.inline_keyboard for button in row]
    assert "🟢 Низкий риск" in buttons_text
    assert "🟡 Средний риск ✅" in buttons_text  # Отмечен текущий профиль
    assert "🔴 Высокий риск" in buttons_text
    assert "⬅️ Назад к настройкам торговли" in buttons_text

    # Проверка с текущим профилем - высокий
    keyboard_high = get_risk_profile_keyboard(current_profile="high")
    buttons_text = [button.text for row in keyboard_high.inline_keyboard for button in row]
    assert "🟢 Низкий риск" in buttons_text
    assert "🟡 Средний риск" in buttons_text
    assert "🔴 Высокий риск ✅" in buttons_text  # Отмечен текущий профиль


def test_get_back_to_settings_keyboard():
    """Тестирует создание клавиатуры с кнопкой возврата к настройкам."""
    keyboard = get_back_to_settings_keyboard()

    # Проверяем, что клавиатура создана
    assert isinstance(keyboard, InlineKeyboardMarkup)

    # Проверяем количество строк
    assert len(keyboard.inline_keyboard) == 1

    # Проверяем наличие кнопки
    assert keyboard.inline_keyboard[0][0].text == "⬅️ Назад к настройкам"
    assert keyboard.inline_keyboard[0][0].callback_data == "settings"
