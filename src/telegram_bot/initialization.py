"""Модуль инициализации и настройки Telegram бота.

Содержит функции для создания и настройки экземпляра Telegram бота,
регистрации обработчиков команд и сообщений, конфигурации системы логирования.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Optional, Callable, List, Dict, Any, Set

from telegram.ext import Application, ApplicationBuilder
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

from src.telegram_bot.user_profiles import profile_manager
from src.telegram_bot.utils.error_handler import (
    setup_error_handler, 
    configure_admin_ids,
    register_global_exception_handlers
)
from src.telegram_bot.utils.api_client import create_api_client_from_env
from src.telegram_bot.keyboards import create_main_keyboard

logger = logging.getLogger(__name__)

def setup_logging(
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
    formatter: Optional[logging.Formatter] = None,
    error_log_file: Optional[str] = None,
) -> None:
    """Настраивает систему логирования для Telegram бота.

    Args:
        log_level: Уровень логирования (по умолчанию INFO)
        log_file: Путь к файлу логов (если None, логи выводятся в консоль)
        formatter: Форматтер для логов (если None, используется стандартный формат)
        error_log_file: Отдельный файл для ошибок (ERROR и выше)
    """
    # Корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Очищаем существующие обработчики
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Форматтер по умолчанию
    if formatter is None:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    
    # Настройка вывода в файл, если указан
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Настройка отдельного файла для ошибок
    if error_log_file:
        error_handler = logging.FileHandler(error_log_file, encoding="utf-8")
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
    
    # Настройка вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Устанавливаем уровень логирования для библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    
    logger.info("Логирование настроено")

async def initialize_bot(token: str, setup_persistence: bool = True) -> Application:
    """Инициализирует экземпляр Telegram бота с указанным токеном.

    Args:
        token: Токен Telegram бота
        setup_persistence: Включить ли сохранение состояния бота

    Returns:
        Application: Настроенный экземпляр приложения бота
    """
    # Проверка токена
    if not token:
        raise ValueError("Не указан токен Telegram бота")
    
    # Создание приложения с оптимальными настройками
    builder = (
        ApplicationBuilder()
        .token(token)
        .concurrent_updates(True)  # Включаем параллельную обработку обновлений
        .rate_limiter(group_size=20, max_retries=3)  # Настройка rate limiter
        .connection_pool_size(8)  # Размер пула соединений
    )
    
    # Добавляем сохранение состояния, если необходимо
    if setup_persistence:
        from telegram.ext import PicklePersistence
        persistence = PicklePersistence(filepath="data/bot_persistence.pickle")
        builder = builder.persistence(persistence)
        
    application = builder.build()
    
    # Настройка обработчика ошибок с администраторами из профилей пользователей
    admin_ids = list(profile_manager.get_admin_ids())
    
    # Если в профилях нет админов, получаем их из переменных окружения
    if not admin_ids:
        admin_ids = configure_admin_ids()
        
    # Регистрируем обработчик ошибок
    setup_error_handler(application, admin_ids)
    
    # Регистрируем глобальные обработчики исключений
    register_global_exception_handlers()
    
    # Настраиваем обработчики сигналов для корректного завершения
    setup_signal_handlers(application)
    
    logger.info(f"Бот инициализирован, ID администраторов: {admin_ids}")
    
    return application

def setup_signal_handlers(application: Application) -> None:
    """Настраивает обработчики сигналов для корректного завершения бота.
    
    Args:
        application: Экземпляр приложения бота
    """
    # Обработчик сигнала завершения
    async def signal_handler():
        logger.info("Получен сигнал завершения, закрываем бота...")
        await application.stop()
        await application.shutdown()
        
    # Регистрируем обработчики для разных сигналов
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
        asyncio.get_event_loop().add_signal_handler(
            sig, lambda: asyncio.create_task(signal_handler())
        )
    
    logger.debug("Обработчики сигналов настроены")

def register_handlers(
    application: Application,
    command_handlers: Dict[str, Callable] = None,
    message_handlers: List[tuple[filters.BaseFilter, Callable]] = None,
    callback_handlers: List[tuple[str, Callable]] = None,
    conversation_handlers: List[ConversationHandler] = None,
) -> None:
    """Регистрирует обработчики команд и сообщений для бота.

    Args:
        application: Экземпляр приложения бота
        command_handlers: Словарь с командами и их обработчиками
        message_handlers: Список кортежей (фильтр, обработчик) для сообщений
        callback_handlers: Список кортежей (паттерн, обработчик) для callback query
        conversation_handlers: Список обработчиков диалогов
    """
    # Регистрируем обработчики диалогов (в первую очередь, т.к. они имеют высший приоритет)
    if conversation_handlers:
        for handler in conversation_handlers:
            application.add_handler(handler)
        logger.info(f"Зарегистрировано {len(conversation_handlers)} обработчиков диалогов")
    
    # Регистрируем обработчики команд
    if command_handlers:
        for command, handler_func in command_handlers.items():
            application.add_handler(CommandHandler(command, handler_func))
        logger.info(f"Зарегистрировано {len(command_handlers)} обработчиков команд")
    
    # Регистрируем обработчики callback query
    if callback_handlers:
        for pattern, handler_func in callback_handlers:
            application.add_handler(CallbackQueryHandler(handler_func, pattern=pattern))
        logger.info(f"Зарегистрировано {len(callback_handlers)} обработчиков callback query")
    
    # Регистрируем обработчики сообщений
    if message_handlers:
        for message_filter, handler_func in message_handlers:
            application.add_handler(MessageHandler(message_filter, handler_func))
        logger.info(f"Зарегистрировано {len(message_handlers)} обработчиков сообщений")

async def initialize_services(application: Application) -> None:
    """Инициализирует сервисы, необходимые для работы бота.
    
    Args:
        application: Экземпляр приложения бота
    """
    # Создаем API клиент и добавляем его в контекст бота
    try:
        dmarket_api = create_api_client_from_env()
        application.bot_data["dmarket_api"] = dmarket_api
        logger.info("API клиент DMarket успешно инициализирован")
    except Exception as e:
        logger.warning(f"Не удалось инициализировать API клиент DMarket: {e}")
    
    # Подготавливаем другие сервисы и данные
    # ...
    
    logger.info("Сервисы инициализированы")

async def start_bot(application: Application) -> None:
    """Запускает Telegram бота.

    Args:
        application: Экземпляр приложения бота
    """
    logger.info("Запуск бота...")
    
    # Инициализируем сервисы
    await initialize_services(application)
    
    # Инициализация и запуск бота
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=application.builder.get_updates_allowed_updates())
    
    logger.info("Бот успешно запущен")
    
    try:
        # Бесконечный цикл для работы бота
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановка бота...")
    finally:
        # Сохраняем данные пользователей перед выходом
        profile_manager.save_profiles(force=True)
        
        await application.stop()
        await application.shutdown()
        logger.info("Бот остановлен")

def get_bot_token() -> str:
    """Получает токен Telegram бота из переменной окружения.

    Returns:
        str: Токен Telegram бота
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Не найден токен Telegram бота в переменных окружения (TELEGRAM_BOT_TOKEN)")
        raise ValueError("Не указан токен Telegram бота")
    return token

async def setup_and_run_bot(
    token: Optional[str] = None,
    command_handlers: Dict[str, Callable] = None,
    message_handlers: List[tuple[filters.BaseFilter, Callable]] = None,
    callback_handlers: List[tuple[str, Callable]] = None,
    conversation_handlers: List[ConversationHandler] = None,
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
    error_log_file: Optional[str] = "logs/bot_errors.log",
    setup_persistence: bool = True,
) -> None:
    """Полная настройка и запуск Telegram бота.

    Args:
        token: Токен Telegram бота (если None, берется из переменных окружения)
        command_handlers: Словарь с командами и их обработчиками
        message_handlers: Список кортежей (фильтр, обработчик) для сообщений
        callback_handlers: Список кортежей (паттерн, обработчик) для callback query
        conversation_handlers: Список обработчиков диалогов
        log_level: Уровень логирования
        log_file: Путь к файлу логов
        error_log_file: Путь к файлу логов ошибок
        setup_persistence: Включить ли сохранение состояния бота
    """
    # Создаем каталог для логов, если его нет
    if log_file or error_log_file:
        os.makedirs("logs", exist_ok=True)
    
    # Настройка логирования
    setup_logging(
        log_level=log_level, 
        log_file=log_file, 
        error_log_file=error_log_file
    )
    
    # Получение токена
    bot_token = token or get_bot_token()
    
    try:
        # Инициализация бота
        application = await initialize_bot(bot_token, setup_persistence)
        
        # Регистрация обработчиков
        register_handlers(
            application,
            command_handlers=command_handlers,
            message_handlers=message_handlers,
            callback_handlers=callback_handlers,
            conversation_handlers=conversation_handlers,
        )
        
        # Запуск бота
        await start_bot(application)
        
    except Exception as e:
        logger.exception(f"Критическая ошибка при запуске бота: {e}")
        sys.exit(1)
