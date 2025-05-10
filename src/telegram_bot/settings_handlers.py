"""Обработчики для настроек и локализации в Telegram-боте DMarket.
"""

import logging
import os
from typing import Any

from telegram import Update
from telegram.ext import CallbackContext

from src.telegram_bot.keyboards import (
    get_back_to_settings_keyboard,
    get_language_keyboard,
    get_risk_profile_keyboard,
    get_settings_keyboard,
)
from src.telegram_bot.localization import LANGUAGES, LOCALIZATIONS

# Настраиваем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# Глобальный словарь для хранения пользовательских профилей
try:
    from src.telegram_bot.bot_v2 import USER_PROFILES, get_user_profile
except ImportError:
    # Временные заглушки на случай, если основной модуль еще не обновлен
    USER_PROFILES = {}

    def get_user_profile(user_id: int) -> dict[str, Any]:
        """Получает профиль пользователя или создает новый.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            Словарь с данными профиля

        """
        user_id_str = str(user_id)

        if user_id_str not in USER_PROFILES:
            import time

            USER_PROFILES[user_id_str] = {
                "language": "ru",
                "api_key": "",
                "api_secret": "",
                "auto_trading_enabled": False,
                "trade_settings": {
                    "min_profit": 2.0,
                    "max_price": 50.0,
                    "max_trades": 3,
                    "risk_level": "medium",
                },
                "last_activity": time.time(),
            }

        return USER_PROFILES[user_id_str]


def get_localized_text(user_id: int, key: str, **kwargs) -> str:
    """Получает локализованный текст для пользователя.

    Args:
        user_id: ID пользователя Telegram
        key: Ключ локализации
        **kwargs: Дополнительные параметры для форматирования строки

    Returns:
        Локализованный текст

    """
    profile = get_user_profile(user_id)
    lang = profile["language"]

    # Если язык не поддерживается, используем русский
    if lang not in LOCALIZATIONS:
        lang = "ru"

    # Если ключ не найден, ищем в русской локализации
    if key not in LOCALIZATIONS[lang]:
        if key in LOCALIZATIONS["ru"]:
            text = LOCALIZATIONS["ru"][key]
        else:
            text = f"[Missing: {key}]"
    else:
        text = LOCALIZATIONS[lang][key]

    # Форматируем строку с переданными параметрами
    if kwargs:
        text = text.format(**kwargs)

    return text


def save_user_profiles():
    """Сохраняет профили пользователей в файл"""
    try:
        import json

        user_profiles_file = os.path.join(
            os.path.dirname(__file__),
            "user_profiles.json",
        )

        with open(user_profiles_file, "w", encoding="utf-8") as f:
            json.dump(USER_PROFILES, f, ensure_ascii=False, indent=2)
        logger.info(f"Сохранено {len(USER_PROFILES)} пользовательских профилей")
    except Exception as e:
        logger.error(f"Ошибка при сохранении профилей: {e!s}")


async def settings_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /settings."""
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)

    # Получаем локализованный текст для настроек
    settings_text = get_localized_text(user_id, "settings")

    # Создаем клавиатуру настроек
    keyboard = get_settings_keyboard(
        auto_trading_enabled=profile.get("auto_trading_enabled", False),
    )

    # Отправляем сообщение с настройками
    await update.message.reply_text(settings_text, reply_markup=keyboard)


async def settings_callback(update: Update, context: CallbackContext) -> None:
    """Обработчик callback-запросов для настроек."""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    # Отвечаем на query, чтобы убрать часы ожидания
    await query.answer()

    if data == "settings":
        # Показываем основное меню настроек
        profile = get_user_profile(user_id)
        settings_text = get_localized_text(user_id, "settings")
        keyboard = get_settings_keyboard(
            auto_trading_enabled=profile.get("auto_trading_enabled", False),
        )
        await query.edit_message_text(
            text=settings_text,
            reply_markup=keyboard,
        )

    elif data == "settings_language":
        # Показываем меню выбора языка
        profile = get_user_profile(user_id)
        current_language = profile.get("language", "ru")
        lang_display_name = LANGUAGES.get(current_language, current_language)

        language_text = get_localized_text(
            user_id,
            "language",
            lang=lang_display_name,
        )
        keyboard = get_language_keyboard(current_language)

        await query.edit_message_text(
            text=language_text,
            reply_markup=keyboard,
        )

    elif data.startswith("language:"):
        # Устанавливаем выбранный язык
        lang_code = data.split(":")[1]
        if lang_code in LANGUAGES:
            profile = get_user_profile(user_id)
            profile["language"] = lang_code
            save_user_profiles()

            # Получаем название языка для отображения
            lang_display = LANGUAGES.get(lang_code, lang_code)

            # Отправляем подтверждение на новом языке
            confirmation_text = get_localized_text(
                user_id,
                "language_set",
                lang=lang_display,
            )

            keyboard = get_back_to_settings_keyboard()
            await query.edit_message_text(
                text=confirmation_text,
                reply_markup=keyboard,
            )
        else:
            # Если выбран неподдерживаемый язык
            error_text = f"⚠️ Язык {lang_code} не поддерживается."
            keyboard = get_language_keyboard("ru")
            await query.edit_message_text(
                text=error_text,
                reply_markup=keyboard,
            )

    elif data == "settings_api_keys":
        # Показываем настройки API ключей
        profile = get_user_profile(user_id)
        api_key = profile.get("api_key", "")
        api_secret = profile.get("api_secret", "")

        # Скрываем часть ключей для безопасности
        if api_key:
            api_key_display = api_key[:5] + "..." + api_key[-5:]
        else:
            api_key_display = "Не установлен"

        if api_secret:
            api_secret_display = api_secret[:3] + "..." + api_secret[-3:]
        else:
            api_secret_display = "Не установлен"

        api_text = (
            f"🔑 Настройки API DMarket\n\n"
            f"Публичный ключ: {api_key_display}\n"
            f"Секретный ключ: {api_secret_display}\n\n"
            f"Для изменения ключей используйте команду /setup"
        )

        keyboard = get_back_to_settings_keyboard()
        await query.edit_message_text(
            text=api_text,
            reply_markup=keyboard,
        )

    elif data == "settings_toggle_trading":
        # Переключаем режим автоматической торговли
        profile = get_user_profile(user_id)
        current_state = profile.get("auto_trading_enabled", False)

        # Инвертируем состояние
        profile["auto_trading_enabled"] = not current_state
        save_user_profiles()

        # Отправляем обновленное меню настроек
        settings_text = get_localized_text(user_id, "settings")
        keyboard = get_settings_keyboard(
            auto_trading_enabled=profile["auto_trading_enabled"],
        )

        # Добавляем уведомление о текущем состоянии
        if profile["auto_trading_enabled"]:
            status_text = get_localized_text(user_id, "auto_trading_on")
        else:
            status_text = get_localized_text(user_id, "auto_trading_off")

        await query.edit_message_text(
            text=f"{settings_text}\n\n{status_text}",
            reply_markup=keyboard,
        )

    elif data == "settings_limits":
        # Показываем настройки лимитов торговли
        profile = get_user_profile(user_id)
        trade_settings = profile.get("trade_settings", {})

        min_profit = trade_settings.get("min_profit", 2.0)
        max_price = trade_settings.get("max_price", 50.0)
        max_trades = trade_settings.get("max_trades", 3)
        risk_level = trade_settings.get("risk_level", "medium")

        limits_text = (
            f"💰 Настройки лимитов торговли\n\n"
            f"Минимальная прибыль: ${min_profit:.2f}\n"
            f"Максимальная цена покупки: ${max_price:.2f}\n"
            f"Максимум сделок: {max_trades}\n"
            f"Уровень риска: {risk_level}\n\n"
            f"Выберите профиль риска:"
        )

        keyboard = get_risk_profile_keyboard(risk_level)
        await query.edit_message_text(
            text=limits_text,
            reply_markup=keyboard,
        )

    elif data.startswith("risk:"):
        # Устанавливаем выбранный профиль риска
        risk_profile = data.split(":")[1]
        profile = get_user_profile(user_id)

        # Обновляем настройки в зависимости от выбранного профиля риска
        if "trade_settings" not in profile:
            profile["trade_settings"] = {}

        profile["trade_settings"]["risk_level"] = risk_profile

        # Устанавливаем параметры в зависимости от профиля риска
        if risk_profile == "low":
            profile["trade_settings"].update(
                {
                    "min_profit": 1.0,
                    "max_price": 30.0,
                    "max_trades": 2,
                }
            )
        elif risk_profile == "medium":
            profile["trade_settings"].update(
                {
                    "min_profit": 2.0,
                    "max_price": 50.0,
                    "max_trades": 5,
                }
            )
        elif risk_profile == "high":
            profile["trade_settings"].update(
                {
                    "min_profit": 5.0,
                    "max_price": 100.0,
                    "max_trades": 10,
                }
            )

        # Сохраняем изменения
        save_user_profiles()

        # Отправляем обновленные настройки лимитов
        trade_settings = profile["trade_settings"]
        limits_text = (
            f"✅ Профиль риска установлен: {risk_profile}\n\n"
            f"💰 Настройки лимитов торговли:\n\n"
            f"Минимальная прибыль: ${trade_settings['min_profit']:.2f}\n"
            f"Максимальная цена покупки: ${trade_settings['max_price']:.2f}\n"
            f"Максимум сделок: {trade_settings['max_trades']}\n\n"
            f"Настройки сохранены."
        )

        keyboard = get_back_to_settings_keyboard()
        await query.edit_message_text(
            text=limits_text,
            reply_markup=keyboard,
        )

    elif data == "back_to_menu":
        # Возвращаемся в главное меню
        from src.telegram_bot.keyboards import get_arbitrage_keyboard

        keyboard = get_arbitrage_keyboard()
        welcome_text = get_localized_text(
            user_id,
            "welcome",
            user=query.from_user.mention_html(),
        )

        await query.edit_message_text(
            text=welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )


async def setup_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /setup для настройки API ключей.
    Запускает диалог настройки API ключей.
    """
    user_id = update.effective_user.id

    # Отправляем запрос на ввод публичного ключа
    api_key_prompt = get_localized_text(user_id, "api_key_prompt")

    # Устанавливаем следующее состояние - ожидание ввода API ключа
    if hasattr(context, "user_data"):
        context.user_data["setup_state"] = "waiting_api_key"

    # Отправляем приветственное сообщение
    await update.message.reply_text(
        f"🔑 Настройка API ключей DMarket\n\n{api_key_prompt}",
    )


async def handle_setup_input(update: Update, context: CallbackContext) -> None:
    """Обработчик ввода текста во время настройки API ключей."""
    user_id = update.effective_user.id
    text = update.message.text

    # Проверяем текущее состояние настройки
    if not hasattr(context, "user_data") or "setup_state" not in context.user_data:
        # Если нет активной настройки, игнорируем сообщение
        return

    setup_state = context.user_data["setup_state"]

    if setup_state == "waiting_api_key":
        # Сохраняем введенный API ключ
        profile = get_user_profile(user_id)
        profile["api_key"] = text
        save_user_profiles()

        # Запрашиваем секретный ключ
        api_secret_prompt = get_localized_text(user_id, "api_secret_prompt")
        context.user_data["setup_state"] = "waiting_api_secret"

        await update.message.reply_text(api_secret_prompt)

    elif setup_state == "waiting_api_secret":
        # Сохраняем введенный секретный ключ
        profile = get_user_profile(user_id)
        profile["api_secret"] = text
        save_user_profiles()

        # Завершаем настройку
        api_keys_set = get_localized_text(user_id, "api_keys_set")
        context.user_data.pop("setup_state", None)

        # Отправляем подтверждение
        await update.message.reply_text(api_keys_set)


# Функции для интеграции в основной модуль bot_v2.py
def register_localization_handlers(application):
    """Регистрирует обработчики для локализации и настроек в приложении.

    Args:
        application: Экземпляр Application из python-telegram-bot

    """
    from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("setup", setup_command))

    # Добавляем обработчики callback-запросов
    application.add_handler(CallbackQueryHandler(settings_callback, pattern="^settings"))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern="^language:"))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern="^risk:"))

    # Добавляем обработчик текстовых сообщений для настройки API ключей
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_setup_input),
    )
