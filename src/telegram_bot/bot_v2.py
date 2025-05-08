"""
Telegram Bot для работы с DMarket API.

Этот модуль реализует точку входа для Telegram-бота с функциями:
- Поиск арбитражных возможностей 
- Автоматический арбитраж
- Проверка баланса DMarket API
- Работа с фильтрами предметов
- WebApp интеграция для прямого доступа к DMarket
- Улучшенная обработка ошибок API

Бот разделен на модули по функциональности.
Документация Telegram Bot API: https://core.telegram.org/bots/api
"""

import asyncio
import logging
import os
import sys
import traceback
import time
from pathlib import Path

# Добавляем корневой каталог проекта в путь поиска модулей
project_root = str(Path(__file__).parent.parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Импортируем обработчики команд
from src.telegram_bot.handlers.commands import (
    start_command,
    help_command,
    webapp_command,
    markets_command,
    dmarket_status_command,
    arbitrage_command,
    handle_text_buttons
)

# Импортируем необходимые функции инициализации
from telegram import BotCommand, BotCommandScopeDefault
from src.telegram_bot.handlers.market_alerts_handler import initialize_alerts_manager

# Импортируем обработчики обратных вызовов (callbacks)
from src.telegram_bot.handlers.callbacks import button_callback_handler

# Импортируем обработчики для фильтров
from src.telegram_bot.game_filter_handlers import (
    handle_filter_callback,
    handle_float_range_callback,
    handle_game_filters,
    handle_price_range_callback,
    handle_set_category_callback,
    handle_set_class_callback,
    handle_set_exterior_callback,
    handle_set_hero_callback,
    handle_set_rarity_callback,
    handle_select_game_filter_callback,
    handle_back_to_filters_callback
)

# Импортируем обработчики для арбитража
from src.telegram_bot.auto_arbitrage import check_balance_command

# Импортируем обработчики для ошибок
from src.telegram_bot.handlers.error_handlers import error_handler

# Импортируем обработчики для внутрирыночного арбитража
from src.telegram_bot.handlers.intramarket_arbitrage_handler import handlers as intramarket_handlers

# Импортируем обработчики для анализа рынка
from src.telegram_bot.handlers.market_analysis_handler import register_market_analysis_handlers

# Импортируем обработчики для уведомлений о рынке
from src.telegram_bot.handlers.market_alerts_handler import register_alerts_handlers

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def set_bot_commands(application: Application) -> None:
    """
    Устанавливает команды бота для отображения в меню команд Telegram.
    
    Args:
        application: Экземпляр приложения Telegram
    """
    commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("help", "Показать справку"),
        BotCommand("status", "Проверить статус API DMarket"),
        BotCommand("arbitrage", "Показать меню арбитража"),
        BotCommand("filters", "Управление фильтрами предметов"),
        BotCommand("balance", "Проверить баланс DMarket"),
        BotCommand("market_analysis", "Анализ тенденций рынка"),
        BotCommand("alerts", "Управление уведомлениями"),
        BotCommand("webapp", "Открыть DMarket в WebApp"),
        BotCommand("markets", "Сравнение рынков"),
    ]
    
    await application.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    logger.info("Команды бота успешно установлены")

async def initialize_application(application: Application) -> None:
    """
    Инициализирует приложение бота.
    
    Args:
        application: Экземпляр приложения Telegram
    """
    # Устанавливаем команды бота
    await set_bot_commands(application)
    
    # Настраиваем бота для правильного отображения клавиатуры
    try:
        # Скрываем кнопку меню или настраиваем ее минимально
        from telegram.bot import BotCommand, BotCommandScopeDefault
        from telegram.menubutton import MenuButtonCommands
        
        # Устанавливаем меню команд с минимальной видимостью, чтобы наша клавиатура была заметнее
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        
        # Устанавливаем параметры по умолчанию для отправки сообщений
        application.bot.defaults.disable_web_page_preview = True
        application.bot.defaults.disable_notification = False
        
        logger.info("Настройки отображения бота успешно применены")
    except Exception as e:
        logger.error(f"Ошибка при настройке отображения бота: {e}")
    
    # Инициализируем менеджер уведомлений
    await initialize_alerts_manager(application)
    
    logger.info("Инициализация бота завершена")

async def main() -> None:
    """Основная функция для запуска бота."""
    # Загружаем переменные окружения из .env файла
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(dotenv_path=str(env_path))

    # Получаем токен бота из переменной окружения
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

    # Получаем и проверяем ключи DMarket API
    dmarket_public_key = os.environ.get("DMARKET_PUBLIC_KEY", "")
    dmarket_secret_key = os.environ.get("DMARKET_SECRET_KEY", "")
    
    # Проверка наличия ключей API
    if not dmarket_public_key or not dmarket_secret_key:
        logger.error("Ключи DMarket API не настроены! Укажите DMARKET_PUBLIC_KEY и DMARKET_SECRET_KEY в .env файле.")
        print("Ошибка: ключи DMarket API не настроены! Укажите DMARKET_PUBLIC_KEY и DMARKET_SECRET_KEY в .env файле.")
        return

    # Проверка наличия токена бота
    if not TOKEN or TOKEN == "YOUR_TOKEN_HERE":
        logger.error(
            "Токен бота не настроен! "
            "Укажите TELEGRAM_BOT_TOKEN в .env файле"
        )
        return

    try:
        # Проверяем, не запущен ли уже бот (Windows-совместимый метод)
        lock_file_path = Path(__file__).parent.parent.parent / "bot.lock"
        
        try:
            # Открываем файл-блокировку
            if lock_file_path.exists():
                # Пытаемся прочитать PID из файла
                with open(lock_file_path, 'r') as f:
                    old_pid = int(f.read().strip())
                    
                    # Проверяем, запущен ли процесс с таким PID
                    import psutil
                    if psutil.pid_exists(old_pid):
                        logger.error(f"Обнаружен уже запущенный экземпляр бота с PID {old_pid}! Завершаем работу.")
                        return
                    else:
                        logger.warning(f"Обнаружен недействительный файл блокировки с PID {old_pid}. Перезаписываем.")
            
            # Создаем новый файл блокировки
            with open(lock_file_path, 'w') as f:
                f.write(str(os.getpid()))
            
            logger.info(f"Запущен экземпляр бота с PID {os.getpid()}")
            
            # Регистрируем обработчик для удаления файла блокировки при завершении
            import atexit
            def remove_lock_file():
                try:
                    if lock_file_path.exists():
                        lock_file_path.unlink()
                except Exception as e:
                    logger.error(f"Ошибка при удалении файла блокировки: {e}")
            
            atexit.register(remove_lock_file)
            
        except Exception as e:
            logger.error(f"Ошибка при работе с файлом-блокировкой: {e}")
            return

        # Создаем приложение с оптимизированными настройками persistence для сохранения состояния
        application = (
            Application.builder()
            .token(TOKEN)
            .concurrent_updates(True)  # Включаем параллельную обработку обновлений
            .build()
        )

        # Проверка подключения к DMarket API будет выполнена при первом запросе
        logger.info(f"Настройка DMarket API с ключами: публичный: {dmarket_public_key[:5]}..., секретный: указан")

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", dmarket_status_command))
        application.add_handler(CommandHandler("dmarket", dmarket_status_command))
        application.add_handler(CommandHandler("arbitrage", arbitrage_command))
        application.add_handler(CommandHandler("filters", handle_game_filters))
        application.add_handler(CommandHandler("balance", lambda update, context: check_balance_command(update.message, context)))
        application.add_handler(CommandHandler("webapp", webapp_command))
        application.add_handler(CommandHandler("markets", markets_command))

        # Добавляем обработчик для текстовых сообщений от клавиатуры
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))

        # Добавляем обработчики callback-запросов для основного меню
        application.add_handler(
            CallbackQueryHandler(
                button_callback_handler,
                pattern=r"^(?!(filter:|price_range:|float_range:|set_|back_to_filters:|select_game_filter))"
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
        
        # Добавляем обработчики для внутрирыночного арбитража
        for handler in intramarket_handlers:
            application.add_handler(handler)
            
        # Добавляем обработчики для анализа рынка
        register_market_analysis_handlers(application)

        # Добавляем обработчики для уведомлений о рынке
        register_alerts_handlers(application)

        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)

        # Выполняем инициализацию отдельно до запуска
        await initialize_application(application)

        # Запускаем бота
        logger.info("Бот запущен и готов к работе")
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
        
        # Добавим бесконечный цикл, чтобы бот не останавливался
        try:
            # Ожидаем сигнала завершения бесконечно
            while True:
                await asyncio.sleep(3600)  # Проверяем каждый час
        except (KeyboardInterrupt, SystemExit):
            # Обрабатываем завершение бота
            logger.info("Получен сигнал для завершения работы бота")
        finally:
        # Ожидаем завершения работы
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
    except Exception as e:
        logger.exception(f"Критическая ошибка при запуске бота: {e}")


if __name__ == "__main__":
    # Запускаем бота через asyncio.run()
    asyncio.run(main())
