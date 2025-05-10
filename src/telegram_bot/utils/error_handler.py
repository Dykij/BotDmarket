"""Модуль обработки ошибок для Telegram бота.

Содержит функции для централизованной обработки ошибок,
логирования исключений и отправки уведомлений пользователям
при возникновении проблем.
"""

import html
import json
import logging
import os
import traceback
from typing import Optional, Callable, Awaitable, Any, Dict, Union, Tuple

from telegram import Update, Bot, Message
from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes
from telegram.error import (
    TelegramError,
    Forbidden,
    BadRequest,
    NetworkError,
    TimedOut,
    RetryAfter,
)

logger = logging.getLogger(__name__)

# ID администраторов (пользователи, получающие уведомления об ошибках)
ADMIN_IDS = []

# Форматы сообщений об ошибках
ERROR_MESSAGE_HTML = """
<b>❌ Произошла ошибка</b>

К сожалению, при выполнении операции произошла ошибка.
Администраторы уведомлены и уже работают над её устранением.

<i>Вы можете попробовать выполнить операцию позднее или обратиться к /help для получения справки.</i>
"""

ERROR_MESSAGE_ADMIN_HTML = """
<b>⚠️ Ошибка в боте</b>

<b>Пользователь:</b> {user_id} (@{username})
<b>Чат:</b> {chat_id}
<b>Сообщение:</b> <code>{message}</code>
<b>Ошибка:</b> <code>{error}</code>

<b>Трассировка:</b>
<pre>{traceback}</pre>
"""

# Хелперы для обработки различных типов ошибок

async def handle_network_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает сетевые ошибки при взаимодействии с Telegram API.
    
    Args:
        update: Объект обновления
        context: Контекст бота с информацией об ошибке
    """
    error = context.error
    # При сетевой ошибке предлагаем пользователю попробовать позже
    message = "Произошла сетевая ошибка. Пожалуйста, попробуйте позже."
    
    if isinstance(error, RetryAfter):
        # При превышении лимита запросов указываем время ожидания
        retry_after = error.retry_after
        message = f"Превышен лимит запросов к Telegram API. Пожалуйста, подождите {retry_after} секунд."
        logger.warning(f"Превышен лимит запросов: {error}. Ожидание {retry_after} секунд.")
        
        # Планируем повторную попытку через указанное время
        if hasattr(context, 'job_queue') and context.job_queue:
            context.job_queue.run_once(
                lambda _: retry_last_action(context),
                retry_after,
                context={'original_update': update}
            )
    
    elif isinstance(error, TimedOut):
        message = "Истекло время ожидания ответа от Telegram. Пожалуйста, попробуйте позже."
        logger.warning(f"Тайм-аут соединения: {error}")
        
        # Можно запланировать автоматическую повторную попытку
        if hasattr(context, 'job_queue') and context.job_queue:
            context.job_queue.run_once(
                lambda _: retry_last_action(context),
                5.0,  # Пробуем через 5 секунд
                context={'original_update': update}
            )
    
    elif isinstance(error, NetworkError):
        logger.error(f"Сетевая ошибка: {error}")
        
    # Отправляем сообщение пользователю, если возможно
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {e}")

async def retry_last_action(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Пытается повторить последнее действие после задержки.
    
    Args:
        context: Контекст с информацией о первоначальном обновлении
    """
    job = context.job
    if job and hasattr(job, 'context') and 'original_update' in job.context:
        original_update = job.context['original_update']
        # Здесь можно реализовать логику повторной обработки запроса
        logger.info(f"Повторная попытка обработки запроса после ошибки")
        # Фактическая реализация повторной обработки запроса зависит от структуры бота

async def handle_forbidden_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ошибки доступа (403 Forbidden).
    
    Args:
        update: Объект обновления
        context: Контекст бота с информацией об ошибке
    """
    error = context.error
    logger.warning(f"Ошибка доступа: {error}")
    
    # Анализируем сообщение об ошибке для более точной диагностики
    error_message = str(error)
    user_message = "У бота нет необходимых прав для выполнения этой операции."
    
    if "bot was blocked by the user" in error_message:
        user_message = "Пользователь заблокировал бота. Диалог невозможен."
        # Возможно, стоит отметить пользователя как неактивного в базе данных
    elif "bot was kicked from the group" in error_message:
        user_message = "Бот был удален из группы."
    elif "not enough rights to send" in error_message:
        user_message = "У бота недостаточно прав для отправки сообщений в этот чат."
    
    # Отправляем сообщение пользователю, если возможно
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=user_message
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {e}")

async def handle_bad_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ошибки некорректного запроса (400 Bad Request).
    
    Args:
        update: Объект обновления
        context: Контекст бота с информацией об ошибке
    """
    error = context.error
    logger.warning(f"Некорректный запрос: {error}")
    
    # Проверяем наличие специфических ошибок
    error_message = str(error)
    user_message = "Произошла ошибка при обработке запроса."
    
    # Разбор типичных ошибок Bad Request и формирование понятных сообщений
    if "message is not modified" in error_message:
        # Игнорируем ошибку неизмененного сообщения
        return
    elif "message to edit not found" in error_message:
        user_message = "Сообщение, которое бот пытался изменить, не найдено."
    elif "query is too old" in error_message:
        user_message = "Запрос устарел. Пожалуйста, повторите команду."
    elif "have no rights to send a message" in error_message:
        user_message = "У бота нет прав отправлять сообщения в этот чат."
    elif "can't parse entities" in error_message:
        # Ошибка форматирования (HTML/Markdown)
        logger.error(f"Ошибка форматирования сообщения: {error_message}")
        user_message = "Произошла ошибка при форматировании сообщения."
    elif "wrong file identifier" in error_message:
        # Неверный идентификатор файла
        logger.error(f"Неверный идентификатор файла: {error_message}")
        user_message = "Произошла ошибка при работе с файлом."
    
    # Отправляем сообщение пользователю, если возможно
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=user_message
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {e}")

async def handle_dmarket_api_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ошибки при работе с DMarket API.
    
    Args:
        update: Объект обновления
        context: Контекст бота с информацией об ошибке
    """
    error = context.error
    dmarket_error = getattr(context, 'dmarket_error', None)
    error_code = getattr(dmarket_error, 'code', None)
    
    # Формируем сообщение для пользователя
    if error_code == 401:
        user_message = "Ошибка авторизации в DMarket API. Пожалуйста, проверьте ваши API ключи."
        logger.error("Ошибка авторизации DMarket API: неверные ключи")
    elif error_code == 429:
        user_message = "Превышен лимит запросов к DMarket API. Пожалуйста, попробуйте позже."
        logger.warning(f"Превышен лимит запросов к DMarket API: {dmarket_error}")
    elif error_code in (500, 502, 503, 504):
        user_message = "Сервис DMarket временно недоступен. Пожалуйста, попробуйте позже."
        logger.error(f"Ошибка сервера DMarket: {dmarket_error}")
    else:
        user_message = "Произошла ошибка при взаимодействии с DMarket. Пожалуйста, попробуйте позже."
        logger.error(f"Ошибка DMarket API: {error}, {dmarket_error}")
    
    # Отправляем сообщение пользователю
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=user_message,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {e}")

# Основной обработчик ошибок

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок для Telegram бота.
    
    Обрабатывает все типы ошибок, логирует их, отправляет сообщения 
    пользователю и администраторам.
    
    Args:
        update: Объект обновления (может быть None)
        context: Контекст бота с информацией об ошибке
    """
    # Получаем информацию об ошибке
    error = context.error
    
    # Логируем трассировку ошибки
    tb_list = traceback.format_exception(None, error, error.__traceback__)
    tb_string = "".join(tb_list)
    
    # Подробное логирование
    update_str = update.to_dict() if update else "Нет данных update"
    logger.error(
        f"Исключение при обработке обновления {update_str}:\n{tb_string}"
    )
    
    # Обработка различных типов ошибок
    if isinstance(error, NetworkError):
        return await handle_network_error(update, context)
    elif isinstance(error, Forbidden):
        return await handle_forbidden_error(update, context)
    elif isinstance(error, BadRequest):
        return await handle_bad_request(update, context)
    
    # Проверка на ошибки DMarket API
    if hasattr(context, 'dmarket_error'):
        return await handle_dmarket_api_error(update, context)
    
    # Получаем информацию о пользователе и чате
    user_id = None
    chat_id = None
    username = "Неизвестно"
    message_text = "Неизвестно"
    
    if update:
        if update.effective_user:
            user_id = update.effective_user.id
            username = update.effective_user.username or "Неизвестно"
        
        if update.effective_chat:
            chat_id = update.effective_chat.id
        
        if update.effective_message:
            message_text = update.effective_message.text or "Неизвестно"
    
    # Отправляем сообщение об ошибке пользователю
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=ERROR_MESSAGE_HTML,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {e}")
    
    # Отправляем уведомление администраторам
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=ERROR_MESSAGE_ADMIN_HTML.format(
                    user_id=user_id,
                    username=html.escape(str(username)),
                    chat_id=chat_id,
                    message=html.escape(str(message_text)),
                    error=html.escape(str(error)),
                    traceback=html.escape(tb_string[:3000])  # Ограничиваем длину трассировки
                ),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {e}")

# Функция для регистрации обработчика ошибок в приложении

def setup_error_handler(application: Application, admin_ids: list[int] = None) -> None:
    """Устанавливает обработчик ошибок для приложения Telegram бота.
    
    Args:
        application: Экземпляр приложения Telegram бота
        admin_ids: Список ID администраторов для уведомлений об ошибках
    """
    global ADMIN_IDS
    
    # Инициализируем список администраторов из переменной окружения, если не задан явно
    if not admin_ids:
        admin_ids = configure_admin_ids()
    
    # Обновляем список администраторов
    if admin_ids:
        ADMIN_IDS = admin_ids
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info(f"Обработчик ошибок установлен. Администраторы: {ADMIN_IDS}")

# Функция для обертывания обработчиков команд с отлавливанием исключений

def exception_guard(func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]) -> Callable:
    """Декоратор для защиты обработчиков команд от необработанных исключений.
    
    Оборачивает функцию-обработчик в try-except и логирует все исключения.
    
    Args:
        func: Функция-обработчик команды
        
    Returns:
        Обернутая функция-обработчик
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        try:
            return await func(update, context)
        except Exception as e:
            logger.error(f"Необработанное исключение в обработчике {func.__name__}: {e}")
            logger.error(traceback.format_exc())
            # Передаем ошибку глобальному обработчику
            context.error = e
            await error_handler(update, context)
            return None
    
    return wrapper

# Вспомогательные функции для отправки сообщений с обработкой ошибок

async def send_message_safe(
    bot: Bot, 
    chat_id: Union[int, str], 
    text: str, 
    **kwargs
) -> Optional[Message]:
    """Безопасно отправляет сообщение с обработкой исключений.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата для отправки
        text: Текст сообщения
        **kwargs: Дополнительные аргументы для send_message
        
    Returns:
        Optional[Message]: Отправленное сообщение или None в случае ошибки
    """
    try:
        return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
    except Forbidden:
        logger.warning(f"У бота нет прав отправлять сообщения в чат {chat_id}")
    except BadRequest as e:
        logger.warning(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
    except NetworkError as e:
        logger.error(f"Сетевая ошибка при отправке сообщения: {e}")
    except TelegramError as e:
        logger.error(f"Ошибка Telegram при отправке сообщения: {e}")
    
    return None

# Конфигурирование администраторов из ENV переменных

def configure_admin_ids(admin_ids_str: Optional[str] = None) -> list[int]:
    """Настраивает список ID администраторов из строки или переменной окружения.
    
    Args:
        admin_ids_str: Строка с ID администраторов через запятую или None
        
    Returns:
        list[int]: Список ID администраторов
    """
    # Используем аргумент или переменную окружения
    ids_str = admin_ids_str or os.environ.get("TELEGRAM_ADMIN_IDS", "")
    
    # Разбираем строку в список ID
    admin_ids = []
    if ids_str:
        try:
            for id_str in ids_str.split(","):
                id_str = id_str.strip()
                if id_str:
                    admin_ids.append(int(id_str))
        except ValueError as e:
            logger.error(f"Ошибка при разборе ID администраторов: {e}")
    
    return admin_ids 