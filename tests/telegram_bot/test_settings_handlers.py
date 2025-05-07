"""Тесты для модуля settings_handlers.py.

Этот модуль содержит тесты для обработчиков настроек и локализации.
"""

import os
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from telegram import InlineKeyboardMarkup, Message, Update, User
from telegram.ext import CallbackContext

from src.telegram_bot.settings_handlers import (
    get_localized_text,
    get_user_profile,
    save_user_profiles,
    settings_callback,
    settings_command,
)


@pytest.fixture
def mock_update():
    """Создает мок объекта Update для тестирования."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 123456789

    update = MagicMock(spec=Update)
    update.effective_user = mock_user
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    update.callback_query = MagicMock()
    update.callback_query.from_user = mock_user
    update.callback_query.data = "settings"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Создает мок объекта CallbackContext для тестирования."""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}
    return context


@pytest.fixture
def mock_user_profiles():
    """Создает мок для USER_PROFILES."""
    return {
        "123456789": {
            "language": "ru",
            "api_key": "test_key",
            "api_secret": "test_secret",
            "auto_trading_enabled": False,
            "trade_settings": {
                "min_profit": 2.0,
                "max_price": 50.0,
                "max_trades": 3,
                "risk_level": "medium",
            },
            "last_activity": 1625000000,
        },
    }


@patch("src.telegram_bot.settings_handlers.USER_PROFILES", {})
def test_get_user_profile_new_user():
    """Тестирует получение профиля для нового пользователя."""
    # Получаем профиль для нового пользователя
    user_id = 999999
    profile = get_user_profile(user_id)

    # Проверяем, что был создан профиль с умолчаниями
    assert "language" in profile
    assert profile["language"] == "ru"
    assert "api_key" in profile
    assert "api_secret" in profile
    assert "auto_trading_enabled" in profile
    assert not profile["auto_trading_enabled"]
    assert "trade_settings" in profile
    assert "min_profit" in profile["trade_settings"]
    assert "max_price" in profile["trade_settings"]
    assert "max_trades" in profile["trade_settings"]
    assert "risk_level" in profile["trade_settings"]


@patch("src.telegram_bot.settings_handlers.USER_PROFILES")
def test_get_user_profile_existing_user(mock_profiles):
    """Тестирует получение профиля для существующего пользователя."""
    # Настройка мока для USER_PROFILES
    user_id = 123456789
    mock_profiles.get.return_value = {
        "language": "en",
        "api_key": "existing_key",
        "api_secret": "existing_secret",
    }
    mock_profiles.__getitem__.return_value = mock_profiles.get.return_value
    mock_profiles.__contains__.return_value = True

    # Получаем профиль для существующего пользователя
    profile = get_user_profile(user_id)

    # Проверяем, что был возвращен существующий профиль
    assert profile["language"] == "en"
    assert profile["api_key"] == "existing_key"
    assert profile["api_secret"] == "existing_secret"


@patch("src.telegram_bot.settings_handlers.USER_PROFILES")
@patch(
    "src.telegram_bot.settings_handlers.LOCALIZATIONS",
    {
        "ru": {"greeting": "Привет", "settings": "Настройки"},
        "en": {"greeting": "Hello", "settings": "Settings"},
    },
)
def test_get_localized_text(mock_profiles):
    """Тестирует получение локализованного текста."""
    # Настройка мока для USER_PROFILES
    user_id = 123456789
    mock_profiles.get.return_value = {"language": "en"}
    mock_profiles.__getitem__.return_value = mock_profiles.get.return_value
    mock_profiles.__contains__.return_value = True

    # Получаем локализованный текст
    text = get_localized_text(user_id, "greeting")

    # Проверяем, что был возвращен правильный текст
    assert text == "Hello"


@patch("src.telegram_bot.settings_handlers.USER_PROFILES")
@patch(
    "src.telegram_bot.settings_handlers.LOCALIZATIONS",
    {
        "ru": {"greeting": "Привет, {name}!", "settings": "Настройки"},
        "en": {"greeting": "Hello, {name}!", "settings": "Settings"},
    },
)
def test_get_localized_text_with_params(mock_profiles):
    """Тестирует получение локализованного текста с параметрами."""
    # Настройка мока для USER_PROFILES
    user_id = 123456789
    mock_profiles.get.return_value = {"language": "en"}
    mock_profiles.__getitem__.return_value = mock_profiles.get.return_value
    mock_profiles.__contains__.return_value = True

    # Получаем локализованный текст с параметром
    text = get_localized_text(user_id, "greeting", name="John")

    # Проверяем, что был возвращен правильный текст с подставленным параметром
    assert text == "Hello, John!"


@patch("src.telegram_bot.settings_handlers.USER_PROFILES")
@patch(
    "src.telegram_bot.settings_handlers.LOCALIZATIONS",
    {
        "ru": {"greeting": "Привет", "settings": "Настройки"},
        "en": {"hello": "Hello"},  # "greeting" отсутствует в английском
    },
)
def test_get_localized_text_missing_key(mock_profiles):
    """Тестирует получение локализованного текста при отсутствии ключа."""
    # Настройка мока для USER_PROFILES
    user_id = 123456789
    mock_profiles.get.return_value = {"language": "en"}
    mock_profiles.__getitem__.return_value = mock_profiles.get.return_value
    mock_profiles.__contains__.return_value = True

    # Получаем локализованный текст для отсутствующего ключа
    text = get_localized_text(user_id, "greeting")

    # Проверяем, что был возвращен текст из русского языка
    assert text == "Привет"


@patch("src.telegram_bot.settings_handlers.USER_PROFILES")
@patch(
    "src.telegram_bot.settings_handlers.LOCALIZATIONS",
    {
        "ru": {"greeting": "Привет", "settings": "Настройки"},
        "en": {"greeting": "Hello", "settings": "Settings"},
    },
)
def test_get_localized_text_unsupported_language(mock_profiles):
    """Тестирует получение локализованного текста при неподдерживаемом языке."""
    # Настройка мока для USER_PROFILES
    user_id = 123456789
    mock_profiles.get.return_value = {"language": "de"}  # Немецкий не поддерживается
    mock_profiles.__getitem__.return_value = mock_profiles.get.return_value
    mock_profiles.__contains__.return_value = True

    # Получаем локализованный текст с неподдерживаемым языком
    text = get_localized_text(user_id, "greeting")

    # Проверяем, что был возвращен текст из русского языка
    assert text == "Привет"


@patch(
    "src.telegram_bot.settings_handlers.USER_PROFILES",
    {"123456789": {"language": "ru"}},
)
@patch("os.path.dirname")
@patch("builtins.open", new_callable=mock_open)
@patch("json.dump")
def test_save_user_profiles(mock_json_dump, mock_file_open, mock_dirname):
    """Тестирует сохранение профилей пользователей."""
    # Настройка мока для os.path.dirname
    mock_dirname.return_value = "/test/path"

    # Вызываем тестируемую функцию
    save_user_profiles()

    # Проверяем, что был вызван open с правильным путем
    # Используем os.path.join для правильного формирования пути в разных ОС
    expected_path = os.path.join("/test/path", "user_profiles.json")
    mock_file_open.assert_called_once_with(
        expected_path,
        "w",
        encoding="utf-8",
    )

    # Проверяем, что был вызван json.dump с правильными данными
    mock_json_dump.assert_called_once()
    args, kwargs = mock_json_dump.call_args
    assert args[0] == {"123456789": {"language": "ru"}}
    assert kwargs["ensure_ascii"] is False
    assert kwargs["indent"] == 2


@pytest.mark.asyncio
@patch("src.telegram_bot.settings_handlers.get_user_profile")
@patch("src.telegram_bot.settings_handlers.get_localized_text")
@patch("src.telegram_bot.settings_handlers.get_settings_keyboard")
async def test_settings_command(
    mock_get_settings_keyboard,
    mock_get_localized_text,
    mock_get_user_profile,
    mock_update,
    mock_context,
):
    """Тестирует обработку команды /settings."""
    # Настройка моков
    mock_profile = {"auto_trading_enabled": False}
    mock_get_user_profile.return_value = mock_profile
    mock_get_localized_text.return_value = "Настройки бота"
    mock_keyboard = MagicMock(spec=InlineKeyboardMarkup)
    mock_get_settings_keyboard.return_value = mock_keyboard

    # Вызываем тестируемую функцию
    await settings_command(mock_update, mock_context)

    # Проверяем, что были вызваны правильные функции
    mock_get_user_profile.assert_called_once_with(mock_update.effective_user.id)
    mock_get_localized_text.assert_called_once_with(
        mock_update.effective_user.id,
        "settings",
    )
    mock_get_settings_keyboard.assert_called_once_with(auto_trading_enabled=False)

    # Проверяем, что был вызван reply_text с правильными аргументами
    mock_update.message.reply_text.assert_called_once_with(
        "Настройки бота",
        reply_markup=mock_keyboard,
    )


@pytest.mark.asyncio
@patch("src.telegram_bot.settings_handlers.get_user_profile")
@patch("src.telegram_bot.settings_handlers.get_localized_text")
@patch("src.telegram_bot.settings_handlers.get_settings_keyboard")
async def test_settings_callback_main_menu(
    mock_get_settings_keyboard,
    mock_get_localized_text,
    mock_get_user_profile,
    mock_update,
    mock_context,
):
    """Тестирует обработку callback с основным меню настроек."""
    # Настройка моков
    mock_profile = {"auto_trading_enabled": False}
    mock_get_user_profile.return_value = mock_profile
    mock_get_localized_text.return_value = "Настройки бота"
    mock_keyboard = MagicMock(spec=InlineKeyboardMarkup)
    mock_get_settings_keyboard.return_value = mock_keyboard

    # Настройка данных callback
    mock_update.callback_query.data = "settings"

    # Вызываем тестируемую функцию
    await settings_callback(mock_update, mock_context)

    # Проверяем, что был вызван answer
    mock_update.callback_query.answer.assert_called_once()

    # Проверяем, что были вызваны правильные функции
    mock_get_user_profile.assert_called_once_with(
        mock_update.callback_query.from_user.id,
    )
    mock_get_localized_text.assert_called_once_with(
        mock_update.callback_query.from_user.id,
        "settings",
    )
    mock_get_settings_keyboard.assert_called_once_with(auto_trading_enabled=False)

    # Проверяем, что был вызван edit_message_text с правильными аргументами
    mock_update.callback_query.edit_message_text.assert_called_once_with(
        text="Настройки бота",
        reply_markup=mock_keyboard,
    )


@pytest.mark.asyncio
@patch("src.telegram_bot.settings_handlers.get_user_profile")
@patch("src.telegram_bot.settings_handlers.get_localized_text")
@patch("src.telegram_bot.settings_handlers.get_language_keyboard")
async def test_settings_callback_language_menu(
    mock_get_language_keyboard,
    mock_get_localized_text,
    mock_get_user_profile,
    mock_update,
    mock_context,
):
    """Тестирует обработку callback с меню выбора языка."""
    # Настройка моков
    mock_profile = {"language": "ru"}
    mock_get_user_profile.return_value = mock_profile
    mock_get_localized_text.return_value = "Выберите язык (текущий: Русский)"
    mock_keyboard = MagicMock(spec=InlineKeyboardMarkup)
    mock_get_language_keyboard.return_value = mock_keyboard

    # Настройка данных callback
    mock_update.callback_query.data = "settings_language"

    # Вызываем тестируемую функцию
    await settings_callback(mock_update, mock_context)

    # Проверяем, что был вызван answer
    mock_update.callback_query.answer.assert_called_once()

    # Проверяем, что были вызваны правильные функции
    mock_get_user_profile.assert_called_once_with(
        mock_update.callback_query.from_user.id,
    )
    mock_get_localized_text.assert_called_once()
    mock_get_language_keyboard.assert_called_once_with("ru")

    # Проверяем, что был вызван edit_message_text с правильными аргументами
    mock_update.callback_query.edit_message_text.assert_called_once_with(
        text="Выберите язык (текущий: Русский)",
        reply_markup=mock_keyboard,
    )


@pytest.mark.asyncio
@patch("src.telegram_bot.settings_handlers.get_user_profile")
@patch("src.telegram_bot.settings_handlers.save_user_profiles")
@patch("src.telegram_bot.settings_handlers.get_localized_text")
@patch("src.telegram_bot.settings_handlers.get_back_to_settings_keyboard")
@patch(
    "src.telegram_bot.settings_handlers.LANGUAGES",
    {"ru": "Русский", "en": "English"},
)
async def test_settings_callback_language_set(
    mock_get_back_keyboard,
    mock_get_localized_text,
    mock_save_profiles,
    mock_get_user_profile,
    mock_update,
    mock_context,
):
    """Тестирует обработку callback с установкой языка."""
    # Настройка моков
    mock_profile = {"language": "ru"}
    mock_get_user_profile.return_value = mock_profile
    mock_get_localized_text.return_value = "Язык изменен на English"
    mock_keyboard = MagicMock(spec=InlineKeyboardMarkup)
    mock_get_back_keyboard.return_value = mock_keyboard

    # Настройка данных callback
    mock_update.callback_query.data = "language:en"

    # Вызываем тестируемую функцию
    await settings_callback(mock_update, mock_context)

    # Проверяем, что был вызван answer
    mock_update.callback_query.answer.assert_called_once()

    # Проверяем, что профиль был обновлен
    assert mock_profile["language"] == "en"

    # Проверяем, что профили были сохранены
    mock_save_profiles.assert_called_once()

    # Проверяем, что были вызваны правильные функции
    mock_get_back_keyboard.assert_called_once()

    # Проверяем, что был вызван edit_message_text с правильными аргументами
    mock_update.callback_query.edit_message_text.assert_called_once_with(
        text="Язык изменен на English",
        reply_markup=mock_keyboard,
    )


@pytest.mark.asyncio
@patch("src.telegram_bot.settings_handlers.get_user_profile")
@patch("src.telegram_bot.settings_handlers.save_user_profiles")
@patch("src.telegram_bot.settings_handlers.get_localized_text")
@patch("src.telegram_bot.settings_handlers.get_settings_keyboard")
async def test_settings_callback_toggle_trading(
    mock_get_settings_keyboard,
    mock_get_localized_text,
    mock_save_profiles,
    mock_get_user_profile,
    mock_update,
    mock_context,
):
    """Тестирует обработку callback с переключением режима автоматической торговли."""
    # Настройка моков
    mock_profile = {"auto_trading_enabled": False, "language": "ru"}
    mock_get_user_profile.return_value = mock_profile
    mock_get_localized_text.side_effect = lambda user_id, key: (
        "Настройки бота" if key == "settings" else "Авто-торговля включена"
    )
    mock_keyboard = MagicMock(spec=InlineKeyboardMarkup)
    mock_get_settings_keyboard.return_value = mock_keyboard

    # Настройка данных callback
    mock_update.callback_query.data = "settings_toggle_trading"

    # Вызываем тестируемую функцию
    await settings_callback(mock_update, mock_context)

    # Проверяем, что был вызван answer
    mock_update.callback_query.answer.assert_called_once()

    # Проверяем, что профиль был обновлен
    assert mock_profile["auto_trading_enabled"] is True

    # Проверяем, что профили были сохранены
    mock_save_profiles.assert_called_once()

    # Проверяем, что get_settings_keyboard был вызван с правильными аргументами
    mock_get_settings_keyboard.assert_called_once_with(auto_trading_enabled=True)

    # Проверяем, что был вызван edit_message_text с правильными аргументами
    mock_update.callback_query.edit_message_text.assert_called_once()

    # Исправлено: безопасный доступ к аргументам
    call_args = mock_update.callback_query.edit_message_text.call_args
    # Проверяем сначала kwargs, т.к. в них может быть text
    if call_args.kwargs and "text" in call_args.kwargs:
        message_text = call_args.kwargs["text"]
    # Если вызов был с позиционным аргументом
    elif call_args.args:
        message_text = call_args.args[0]
    else:
        message_text = ""

    assert "Настройки бота" in message_text
    assert "Авто-торговля включена" in message_text
    assert call_args.kwargs.get("reply_markup") == mock_keyboard


@pytest.mark.asyncio
@patch("src.telegram_bot.settings_handlers.get_user_profile")
@patch("src.telegram_bot.settings_handlers.get_back_to_settings_keyboard")
async def test_settings_callback_api_keys(
    mock_get_back_keyboard,
    mock_get_user_profile,
    mock_update,
    mock_context,
):
    """Тестирует обработку callback с отображением настроек API ключей."""
    # Настройка моков
    mock_profile = {
        "api_key": "abcde12345fghij67890",
        "api_secret": "secret123456",
        "language": "ru",
    }
    mock_get_user_profile.return_value = mock_profile
    mock_keyboard = MagicMock(spec=InlineKeyboardMarkup)
    mock_get_back_keyboard.return_value = mock_keyboard

    # Настройка данных callback
    mock_update.callback_query.data = "settings_api_keys"

    # Вызываем тестируемую функцию
    await settings_callback(mock_update, mock_context)

    # Проверяем, что был вызван answer
    mock_update.callback_query.answer.assert_called_once()

    # Проверяем, что были вызваны правильные функции
    mock_get_back_keyboard.assert_called_once()

    # Проверяем, что был вызван edit_message_text с правильными аргументами
    mock_update.callback_query.edit_message_text.assert_called_once()

    # Исправлено: безопасный доступ к аргументам
    call_args = mock_update.callback_query.edit_message_text.call_args
    # Проверяем сначала kwargs, т.к. в них может быть text
    if call_args.kwargs and "text" in call_args.kwargs:
        message_text = call_args.kwargs["text"]
    # Если вызов был с позиционным аргументом
    elif call_args.args:
        message_text = call_args.args[0]
    else:
        message_text = ""

    # Проверяем, что показаны маскированные ключи
    assert (
        "abcde...67890" in message_text
    )  # Показаны первые 5 и последние 5 символов ключа
    assert (
        "sec...456" in message_text
    )  # Показаны первые 3 и последние 3 символа секрета
    assert call_args.kwargs.get("reply_markup") == mock_keyboard
