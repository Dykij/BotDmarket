"""
Модуль для централизованного логирования с контекстной информацией.
Предоставляет настраиваемые логгеры для различных компонентов системы.
"""

import logging
import os
import sys
import traceback
import json
from typing import Any, Dict, Optional, Union
import functools
import inspect

# Настройка базового формата логирования
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(context)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Настройка уровней логирования
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

DEFAULT_LOG_LEVEL = LOG_LEVELS.get(os.environ.get('LOG_LEVEL', 'INFO'), logging.INFO)


class ContextLogAdapter(logging.LoggerAdapter):
    """Адаптер для добавления контекста в сообщения лога."""

    def process(self, msg, kwargs):
        """Добавляет контекст в сообщения лога."""
        if not 'context' in kwargs or not kwargs['context']:
            kwargs['context'] = self.extra.get('context', {})
        else:
            # Объединяем контексты
            kwargs['context'].update(self.extra.get('context', {}))

        # Преобразуем контекст в строку для логирования
        context_str = json.dumps(kwargs.pop('context', {}), default=str)
        return msg, kwargs


class ContextFilter(logging.Filter):
    """Фильтр для добавления контекста в записи лога."""

    def filter(self, record):
        """Добавляет контекст в запись лога."""
        if not hasattr(record, 'context'):
            record.context = '{}'
        elif isinstance(record.context, dict):
            record.context = json.dumps(record.context, default=str)
        return True


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Возвращает логгер с заданным контекстом.

    Args:
        name: Имя логгера.
        context: Словарь с контекстной информацией.

    Returns:
        Настроенный логгер.
    """
    logger = logging.getLogger(name)

    # Настраиваем обработчик логов, если его еще нет
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Устанавливаем уровень логирования
        logger.setLevel(DEFAULT_LOG_LEVEL)

        # Добавляем фильтр контекста
        context_filter = ContextFilter()
        handler.addFilter(context_filter)

    # Создаем адаптер с контекстом
    context_dict = context or {}
    adapter = ContextLogAdapter(logger, {'context': context_dict})

    return adapter


def log_exceptions(logger: Optional[logging.Logger] = None):
    """
    Декоратор для логирования исключений с контекстной информацией.

    Args:
        logger: Логгер для записи исключений. Если None, будет создан новый.

    Returns:
        Декоратор функции.
    """
    def decorator(func):
        # Получаем имя модуля и функции для создания логгера
        module_name = func.__module__
        func_name = func.__qualname__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Создаем логгер, если не передан
            nonlocal logger
            if logger is None:
                logger = get_logger(f"{module_name}.{func_name}")

            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Готовим контекстную информацию
                context = {
                    'function': func_name,
                    'args': str(args),
                    'kwargs': str(kwargs),
                    'exception_type': e.__class__.__name__,
                    'exception_args': e.args if hasattr(e, 'args') else str(e),
                    'traceback': traceback.format_exc().split('\n')
                }

                # Логируем исключение с контекстом
                logger.error(f"Необработанное исключение в {func_name}: {str(e)}",
                            extra={'context': context})

                # Повторно выбрасываем исключение
                raise

        return wrapper

    # Если декоратор вызван без аргументов
    if callable(logger):
        func, logger = logger, None
        return decorator(func)

    return decorator


# Создаем базовые логгеры для различных компонентов
bot_logger = get_logger('telegram_bot', {'component': 'bot'})
api_logger = get_logger('dmarket_api', {'component': 'api'})
arbitrage_logger = get_logger('arbitrage', {'component': 'business_logic'})


# Пример функции с логированием исключений
@log_exceptions
def example_function(a: int, b: int) -> int:
    """Пример функции с логированием исключений."""
    api_logger.info("Выполняется пример функции",
                   extra={'context': {'a': a, 'b': b}})
    return a / b  # Может вызвать деление на ноль
