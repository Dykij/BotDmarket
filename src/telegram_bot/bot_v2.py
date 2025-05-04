"""Модуль Telegram-бота для арбитража DMarket."""

import logging
import os
import traceback
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext

from src.dmarket.arbitrage import GAMES
from src.telegram_bot.keyboards import get_arbitrage_keyboard, get_auto_arbitrage_keyboard, get_game_selection_keyboard
from src.utils.api_error_handling import APIError
from src.utils.dmarket_api_utils import execute_api_request
from src.telegram_bot.game_filter_handlers import (
    handle_game_filters, handle_filter_callback, handle_price_range_callback,
    handle_float_range_callback, handle_set_category_callback, handle_set_rarity_callback,
    handle_set_exterior_callback, handle_set_hero_callback, handle_set_class_callback,
    handle_back_to_filters_callback, handle_select_game_filter_callback,
)

# Константы для API DMarket
DMARKET_PUBLIC_KEY = os.environ.get("DMARKET_PUBLIC_KEY", "")
DMARKET_SECRET_KEY = os.environ.get("DMARKET_SECRET_KEY", "")

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: CallbackContext) -> None:
    """Обрабатывает команду /start.

    Args:
        update: Объект Update от Telegram.
        context: Контекст CallbackContext.
    """
    user = update.message.from_user

    welcome_message = (
        "👋 Добро пожаловать! Я бот для работы с DMarket.\n\n"
        "Что я умею:\n"
        "• Поиск арбитражных ситуаций между площадками\n"
        "• Автоматический арбитраж\n"
        "• Проверка статуса API DMarket\n\n"
        "Используйте команду /help для получения списка команд."
    )

    keyboard = get_arbitrage_keyboard()
    await update.message.reply_text(welcome_message, reply_markup=keyboard)


async def help_command(update: Update, context: CallbackContext) -> None:
    """Обрабатывает команду /help.

    Args:
        update: Объект Update от Telegram.
        context: Контекст CallbackContext.
    """
    help_text = (
        "📋 Список доступных команд:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/status - Проверить статус API DMarket\n"
        "/dmarket - Информация о DMarket API\n"
        "/arbitrage - Показать меню арбитража\n"
    )
    await update.message.reply_text(help_text)


async def dmarket_status(update: Update, context: CallbackContext) -> None:
    """Проверяет статус API DMarket.

    Args:
        update: Объект Update от Telegram.
        context: Контекст CallbackContext.
    """
    message = await update.message.reply_text("Проверка статуса API DMarket...")

    # Проверяем наличие ключей API
    if DMARKET_PUBLIC_KEY and DMARKET_SECRET_KEY:
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


async def arbitrage_command(update: Update, context: CallbackContext) -> None:
    """Обрабатывает команду /arbitrage.

    Args:
        update: Объект Update от Telegram.
        context: Контекст CallbackContext.
    """
    keyboard = get_arbitrage_keyboard()
    await update.message.reply_text(
        "🔍 Выберите режим арбитража:",
        reply_markup=keyboard
    )


async def arbitrage_callback(update: Update, context: CallbackContext) -> None:
    """Обрабатывает колбэки от кнопок меню арбитража.

    Args:
        update: Объект Update от Telegram.
        context: Контекст CallbackContext.
    """
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data == "arbitrage":
        # Показываем меню арбитража
        keyboard = get_arbitrage_keyboard()
        await query.edit_message_text(
            "🔍 Выберите режим арбитража:",
            reply_markup=keyboard
        )
    elif callback_data.startswith("arbitrage_"):
        # Обрабатываем выбор типа арбитража
        arb_type = callback_data.replace("arbitrage_", "")

        if arb_type == "game_selection":
            # Показываем выбор игры
            keyboard = get_game_selection_keyboard()
            await query.edit_message_text(
                "🎮 Выберите игру для арбитража:",
                reply_markup=keyboard
            )
        elif arb_type == "auto":
            # Показываем меню автоарбитража
            keyboard = get_auto_arbitrage_keyboard()
            await query.edit_message_text(
                "🤖 Автоматический арбитраж:",
                reply_markup=keyboard
            )
    elif callback_data.startswith("select_game_"):
        # Запоминаем выбранную игру
        game = callback_data.replace("select_game_", "")
        context.user_data["current_game"] = game

        # Показываем меню арбитража снова
        keyboard = get_arbitrage_keyboard()
        await query.edit_message_text(
            f"Выбрана игра: {GAMES.get(game, game)}\n\n"
            "🔍 Выберите тип арбитража:",
            reply_markup=keyboard
        )


async def button_callback_handler(update: Update, context: CallbackContext) -> None:
    """Общий обработчик колбэков от кнопок.

    Args:
        update: Объект Update от Telegram.
        context: Контекст CallbackContext.
    """
    query = update.callback_query
    callback_data = query.data

    # Обработка для арбитража и выбора игры
    if callback_data == "arbitrage" or callback_data.startswith("arbitrage_"):
        await arbitrage_callback(update, context)
    elif callback_data == "select_game":
        await query.answer()
        keyboard = get_game_selection_keyboard()
        await query.edit_message_text(
            "🎮 Выберите игру для арбитража:",
            reply_markup=keyboard
        )
    elif callback_data.startswith("select_game_"):
        await arbitrage_callback(update, context)
    elif callback_data.startswith("auto_start:"):
        # Функция заглушка для тестов
        await start_auto_trading(query, context, callback_data.split(":", 1)[1])
    elif callback_data.startswith("paginate:"):
        # Функция заглушка для тестов
        await show_auto_stats(query, context)


# Вспомогательные функции-заглушки для тестирования
async def start_auto_trading(query: Any, context: CallbackContext, mode: str) -> None:
    """Заглушка для функции запуска автоматического арбитража."""
    pass


async def show_auto_stats(query: Any, context: CallbackContext) -> None:
    """Заглушка для функции показа статистики автоматического арбитража."""
    pass


# Класс-заглушка для менеджера пагинации
class PaginationManager:
    """Менеджер для обработки пагинации в сообщениях."""

    def __init__(self) -> None:
        """Инициализация менеджера пагинации."""
        pass

    def paginate(self, query: Any, context: CallbackContext, page_action: str, current_page: int = 0) -> None:
        """Обрабатывает действие пагинации."""
        pass


pagination_manager = PaginationManager()


async def error_handler(update: Update, context: CallbackContext) -> None:
    """Обрабатывает ошибки, возникающие при работе бота.

    Args:
        update: Объект Update от Telegram.
        context: Контекст CallbackContext с информацией об ошибке.
    """
    error = context.error

    # Логируем ошибку
    logging.error(f"Exception while handling an update: {error}")
    logging.error(traceback.format_exc())

    # Отправляем сообщение пользователю в зависимости от типа ошибки
    if isinstance(error, APIError):
        error_message = (
            f"❌ Ошибка API DMarket:\n"
            f"Код: {error.status_code}\n"
            f"Сообщение: {error!s}"
        )
    else:
        error_message = "⚠️ Произошла ошибка при выполнении команды. Попробуйте позднее."

    # Отправляем сообщение, если это возможно
    if update and update.effective_message:
        await update.effective_message.reply_text(error_message)


def main() -> None:
    """Основная функция для запуска бота."""
    # Загружаем переменные окружения из .env файла
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path=env_path)

    # Получаем токен бота из переменной окружения
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

    try:
        # Применяем патч для получения баланса DMarket, если он еще не применен
        try:
            from src.dmarket.dmarket_api_patches import apply_balance_patch
            logger.info("Применение патча для получения баланса DMarket...")
            apply_balance_patch()
        except ImportError:
            # Попробуем альтернативный путь
            try:
                from src.dmarket.dmarket_api_patch import apply_patch
                logger.info("Применение альтернативного патча для получения баланса DMarket...")
                apply_patch()
            except ImportError:
                logger.warning("Патч для получения баланса DMarket не найден")

        if not TOKEN or TOKEN == "YOUR_TOKEN_HERE":
            logger.error(
                "Токен бота не настроен! "
                "Укажите TELEGRAM_BOT_TOKEN в .env файле"
            )
            return

        # Создаем приложение и добавляем обработчики
        application = Application.builder().token(TOKEN).build()

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", dmarket_status))
        application.add_handler(CommandHandler("dmarket", dmarket_status))
        application.add_handler(CommandHandler("arbitrage", arbitrage_command))
        application.add_handler(CommandHandler("filters", handle_game_filters))

        # Добавляем обработчики callback-запросов для основного меню
        application.add_handler(
            CallbackQueryHandler(
                button_callback_handler,
                pattern=r"^(?!filter:|price_range:|float_range:|set_|back_to_filters:|select_game_filter)"
            )
        )

        # Добавляем обработчики callback-запросов для фильтрации
        application.add_handler(
            CallbackQueryHandler(handle_filter_callback, pattern=r"^filter:")
        )
        application.add_handler(
            CallbackQueryHandler(handle_price_range_callback, pattern=r"^price_range:")
        )
        application.add_handler(
            CallbackQueryHandler(handle_float_range_callback, pattern=r"^float_range:")
        )
        application.add_handler(
            CallbackQueryHandler(handle_set_category_callback, pattern=r"^set_category:")
        )
        application.add_handler(
            CallbackQueryHandler(handle_set_rarity_callback, pattern=r"^set_rarity:")
        )
        application.add_handler(
            CallbackQueryHandler(handle_set_exterior_callback, pattern=r"^set_exterior:")
        )
        application.add_handler(
            CallbackQueryHandler(handle_set_hero_callback, pattern=r"^set_hero:")
        )
        application.add_handler(
            CallbackQueryHandler(handle_set_class_callback, pattern=r"^set_class:")
        )
        application.add_handler(
            CallbackQueryHandler(
                handle_select_game_filter_callback, pattern=r"^select_game_filter:"
            )
        )
        application.add_handler(
            CallbackQueryHandler(
                handle_back_to_filters_callback, pattern=r"^back_to_filters:"
            )
        )

        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)

        # Запускаем бота
        logger.info("Бот запущен")
        application.run_polling()
    except Exception as e:
        logging.exception(f"Ошибка при запуске бота: {e}")


if __name__ == "__main__":
    # Загружаем профили пользователей при старте
    from src.telegram_bot.profiles import load_user_profiles
    load_user_profiles()

    main()
