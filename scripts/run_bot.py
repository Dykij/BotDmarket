"""Основной модуль запуска Telegram бота.

Этот модуль инициализирует и запускает Telegram бота для работы с DMarket.
"""

import logging
import os

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes

# Настройка логирования
from src.utils.logging_utils import setup_logging

setup_logging()

logger = logging.getLogger(__name__)

# Загрузка переменных окружения из .env файла (если он существует)
try:
    from dotenv import load_dotenv

    load_dotenv()  # берёт переменные окружения из .env
except ImportError:
    logger.warning("python-dotenv не установлен, продолжаем без него")

# Импорт обработчиков команд и других компонентов бота
from src.telegram_bot.commands.basic_commands import register_basic_commands
from src.telegram_bot.handlers.dmarket_handlers import register_dmarket_handlers

# Токены и API ключи из переменных окружения
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DMARKET_PUBLIC_KEY = os.environ.get("DMARKET_PUBLIC_KEY", "")
DMARKET_SECRET_KEY = os.environ.get("DMARKET_SECRET_KEY", "")
DMARKET_API_URL = os.environ.get("DMARKET_API_URL", "https://api.dmarket.com")

# Проверка наличия токена Telegram бота
if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    raise ValueError(
        "TELEGRAM_BOT_TOKEN не найден в переменных окружения. "
        "Пожалуйста, добавьте его в .env файл или переменные окружения.",
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ошибки в обработчиках."""
    logger.error(f"Произошла ошибка: {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка при обработке запроса. Пожалуйста, повторите попытку позже.",
        )


def main() -> None:
    """Инициализирует и запускает бота."""
    logger.info("Запуск Telegram бота для DMarket")

    try:
        # Создание приложения Telegram бота
        app = ApplicationBuilder().token(TOKEN).build()

        # Регистрация обработчиков команд
        register_basic_commands(app)
        register_dmarket_handlers(app, DMARKET_PUBLIC_KEY, DMARKET_SECRET_KEY, DMARKET_API_URL)

        # Установка обработчика ошибок
        app.add_error_handler(error_handler)

        # Запуск бота
        logger.info("Бот запущен и ожидает сообщения")
        app.run_polling()

    except Exception as e:
        logger.critical(f"Не удалось запустить бота: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
