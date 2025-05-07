"""Modified version of the main Telegram bot for DMarket."""

# Fix APScheduler timezone issues
import importlib.util

if importlib.util.find_spec("tzlocal") is not None:
    import tzlocal.unix
    original_get_localzone = tzlocal.unix.get_localzone

    def patched_get_localzone():
        import pytz
        return pytz.timezone("Europe/Moscow")

    tzlocal.unix.get_localzone = patched_get_localzone

import logging
import os
import traceback

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Устанавливаем часовой пояс для APScheduler
os.environ["TZ"] = "Europe/Moscow"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start."""
    user = update.effective_user

    welcome_message = (
        "👋 Добро пожаловать! Я бот для работы с DMarket.\n\n"
        "Что я умею:\n"
        "• Поиск арбитражных ситуаций между площадками\n"
        "• Автоматический арбитраж\n"
        "• Проверка статуса API DMarket\n\n"
        "Используйте команду /help для получения списка команд."
    )

    # Создаем клавиатуру для выбора действий
    keyboard = [
        [
            InlineKeyboardButton("🔍 Поиск арбитража", callback_data="arbitrage"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            InlineKeyboardButton("❓ Помощь", callback_data="help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /help."""
    help_text = (
        "📋 Список доступных команд:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать справку\n"
        "/status - Проверить статус API DMarket\n"
        "/arbitrage - Показать меню арбитража\n"
        "/price_alerts - Управление оповещениями о ценах"
    )

    await update.message.reply_text(help_text)


async def dmarket_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверяет статус API DMarket."""
    message = await update.message.reply_text("Проверка статуса API DMarket...")

    # Проверяем наличие ключей API
    public_key = os.getenv("DMARKET_PUBLIC_KEY")
    secret_key = os.getenv("DMARKET_SECRET_KEY")

    if public_key and secret_key:
        status_text = (
            "✅ API ключи настроены!\n\n"
            "API endpoint доступен для использования."
        )
    else:
        status_text = (
            "❌ API ключи не настроены.\n\n"
            "Пожалуйста, установите DMARKET_PUBLIC_KEY и DMARKET_SECRET_KEY в .env файле."
        )

    await message.edit_text(status_text)


async def arbitrage_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /arbitrage."""
    keyboard = [
        [
            InlineKeyboardButton("🎮 Выбрать игру", callback_data="arbitrage_game_selection"),
        ],
        [
            InlineKeyboardButton("🤖 Автоматический арбитраж", callback_data="arbitrage_auto"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔍 Выберите режим арбитража:",
        reply_markup=reply_markup,
    )


async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Общий обработчик колбэков от кнопок."""
    query = update.callback_query
    await query.answer()  # Убираем часы загрузки

    callback_data = query.data

    if callback_data == "arbitrage":
        # Показываем меню арбитража
        keyboard = [
            [
                InlineKeyboardButton("🎮 Выбрать игру", callback_data="arbitrage_game_selection"),
            ],
            [
                InlineKeyboardButton("🤖 Автоматический арбитраж", callback_data="arbitrage_auto"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🔍 Выберите режим арбитража:",
            reply_markup=reply_markup,
        )

    elif callback_data.startswith("arbitrage_"):
        # Обрабатываем выбор типа арбитража
        arb_type = callback_data.replace("arbitrage_", "")

        if arb_type == "game_selection":
            # Показываем выбор игры
            keyboard = [
                [
                    InlineKeyboardButton("🎮 CS:GO", callback_data="select_game_csgo"),
                    InlineKeyboardButton("🎮 DOTA 2", callback_data="select_game_dota2"),
                ],
                [
                    InlineKeyboardButton("🎮 RUST", callback_data="select_game_rust"),
                    InlineKeyboardButton("🎮 TF2", callback_data="select_game_tf2"),
                ],
                [
                    InlineKeyboardButton("⬅️ Назад", callback_data="arbitrage"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "🎮 Выберите игру для арбитража:",
                reply_markup=reply_markup,
            )

        elif arb_type == "auto":
            # Показываем меню автоарбитража
            keyboard = [
                [
                    InlineKeyboardButton("▶️ Запустить", callback_data="auto_start:best"),
                    InlineKeyboardButton("⏹️ Остановить", callback_data="auto_stop"),
                ],
                [
                    InlineKeyboardButton("📊 Статистика", callback_data="auto_stats"),
                    InlineKeyboardButton("⬅️ Назад", callback_data="arbitrage"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "🤖 Автоматический арбитраж:",
                reply_markup=reply_markup,
            )

    elif callback_data.startswith("select_game_"):
        # Запоминаем выбранную игру
        game = callback_data.replace("select_game_", "")
        context.user_data["current_game"] = game

        # Словарь полных названий игр
        games = {
            "csgo": "CS:GO",
            "dota2": "DOTA 2",
            "rust": "RUST",
            "tf2": "Team Fortress 2",
        }

        # Показываем меню арбитража снова
        keyboard = [
            [
                InlineKeyboardButton("🎮 Выбрать игру", callback_data="arbitrage_game_selection"),
            ],
            [
                InlineKeyboardButton("🤖 Автоматический арбитраж", callback_data="arbitrage_auto"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"Выбрана игра: {games.get(game, game)}\n\n"
            "🔍 Выберите тип арбитража:",
            reply_markup=reply_markup,
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ошибки, возникающие при работе бота."""
    if update is None:
        # Если update None, значит ошибка произошла не в контексте обработки сообщения
        logger.error(f"Exception: {context.error}")
        logger.error(traceback.format_exc())
        return

    error = context.error

    # Логируем ошибку
    logger.error(f"Exception while handling an update: {error}")
    logger.error(traceback.format_exc())

    # Отправляем сообщение пользователю в зависимости от типа ошибки
    error_message = "⚠️ Произошла ошибка при выполнении команды. Попробуйте позднее."

    # Отправляем сообщение, если это возможно
    if update.effective_message:
        await update.effective_message.reply_text(error_message)


def main() -> None:
    """Основная функция для запуска бота."""
    # Загружаем переменные окружения
    load_dotenv()

    # Получаем токен бота
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        logger.error("Не задан TELEGRAM_BOT_TOKEN. Бот не может быть запущен.")
        return

    # Создаем приложение с явным отключением job_queue
    application = Application.builder().token(token).job_queue(None).build()

    # Добавляем базовые обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", dmarket_status))
    application.add_handler(CommandHandler("arbitrage", arbitrage_command))

    # Добавляем обработчики колбэков
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем бота в polling-режиме
    try:
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")


if __name__ == "__main__":
    main()
