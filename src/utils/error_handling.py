"""
Модуль для централизованной обработки ошибок и логирования в боте DMarket.

Основные функции:
- Форматирование сообщений об ошибках для пользователя
- Централизованное логирование с контекстом
- Категоризация ошибок для принятия решений
"""

import logging
import sys
import traceback
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List, Union

# Настраиваем базовое логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Получаем корневой логгер
logger = logging.getLogger("dmarket_bot")

# Добавляем обработчик для сохранения ошибок в файл
file_handler = logging.FileHandler("dmarket_bot_errors.log")
file_handler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Категории ошибок для принятия решений
ERROR_CATEGORIES = {
    "API_ERROR": {
        "max_retries": 3,
        "retry_delay": 5,  # секунды
        "critical": False,
    },
    "NETWORK_ERROR": {
        "max_retries": 5,
        "retry_delay": 10,
        "critical": False,
    },
    "AUTH_ERROR": {
        "max_retries": 1,
        "retry_delay": 0,
        "critical": True,
    },
    "BALANCE_ERROR": {
        "max_retries": 0,
        "retry_delay": 0,
        "critical": True,
    },
    "DATA_ERROR": {
        "max_retries": 2,
        "retry_delay": 3,
        "critical": False,
    },
    "INTERNAL_ERROR": {
        "max_retries": 0,
        "retry_delay": 0,
        "critical": True,
    }
}

# Хранилище ошибок для аналитики
error_storage = []


def categorize_error(error: Exception) -> str:
    """
    Определяет категорию ошибки на основе типа исключения и сообщения.
    
    Args:
        error: Исключение для категоризации
        
    Returns:
        Строка с категорией ошибки
    """
    error_type = type(error).__name__
    error_msg = str(error).lower()
    
    # Определяем категорию по типу и содержимому ошибки
    if "connection" in error_msg or "timeout" in error_msg or "socket" in error_msg:
        return "NETWORK_ERROR"
    
    if "api" in error_msg or "request" in error_msg or "response" in error_msg:
        return "API_ERROR"
    
    if "auth" in error_msg or "token" in error_msg or "key" in error_msg or "unauthorized" in error_msg:
        return "AUTH_ERROR"
    
    if "balance" in error_msg or "insufficient" in error_msg or "funds" in error_msg:
        return "BALANCE_ERROR"
    
    if "json" in error_msg or "parse" in error_msg or "data" in error_msg:
        return "DATA_ERROR"
    
    # По умолчанию считаем ошибку внутренней
    return "INTERNAL_ERROR"


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    operation: Optional[str] = None
) -> Dict[str, Any]:
    """
    Логирует ошибку с дополнительным контекстом.
    
    Args:
        error: Исключение для логирования
        context: Дополнительный контекст ошибки
        user_id: ID пользователя, у которого произошла ошибка
        operation: Операция, при которой произошла ошибка
        
    Returns:
        Словарь с информацией об ошибке
    """
    # Получаем трассировку стека
    stack_trace = traceback.format_exception(type(error), error, error.__traceback__)
    
    # Определяем категорию ошибки
    category = categorize_error(error)
    
    # Формируем данные ошибки
    error_data = {
        "timestamp": datetime.now().isoformat(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "category": category,
        "user_id": user_id,
        "operation": operation,
        "context": context or {},
        "stack_trace": stack_trace
    }
    
    # Логируем ошибку
    logger.error(
        f"Error [{category}]: {error_data['error_type']}: {error_data['error_message']}",
        extra={
            "user_id": user_id,
            "operation": operation,
            "error_data": error_data
        }
    )
    
    # Добавляем ошибку в хранилище для аналитики
    global error_storage
    error_storage.append(error_data)
    
    # Ограничиваем размер хранилища
    if len(error_storage) > 100:
        error_storage = error_storage[-100:]
    
    # Сохраняем ошибки в JSON файл
    try:
        with open("error_analytics.json", "w", encoding="utf-8") as f:
            json.dump(error_storage, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save error analytics: {e}")
    
    return error_data


def format_error_for_user(
    error: Union[Exception, str],
    with_details: bool = False,
    lang: str = "ru"
) -> str:
    """
    Форматирует сообщение об ошибке для пользователя.
    
    Args:
        error: Исключение или строка с сообщением об ошибке
        with_details: Включать ли детали ошибки
        lang: Язык сообщения
        
    Returns:
        Отформатированное сообщение об ошибке
    """
    # Определяем базовый текст ошибки
    if isinstance(error, Exception):
        error_message = str(error)
        error_type = type(error).__name__
        category = categorize_error(error)
    else:
        error_message = str(error)
        error_type = "Error"
        category = "INTERNAL_ERROR"
    
    # Формируем базовое сообщение в зависимости от языка и категории
    if lang == "ru":
        base_messages = {
            "API_ERROR": "Ошибка API DMarket",
            "NETWORK_ERROR": "Ошибка сети",
            "AUTH_ERROR": "Ошибка авторизации",
            "BALANCE_ERROR": "Недостаточно средств",
            "DATA_ERROR": "Ошибка данных",
            "INTERNAL_ERROR": "Внутренняя ошибка бота"
        }
    else:  # По умолчанию используем английский
        base_messages = {
            "API_ERROR": "DMarket API error",
            "NETWORK_ERROR": "Network error",
            "AUTH_ERROR": "Authorization error",
            "BALANCE_ERROR": "Insufficient funds",
            "DATA_ERROR": "Data error",
            "INTERNAL_ERROR": "Internal bot error"
        }
    
    # Получаем базовое сообщение для категории или используем общее
    base_message = base_messages.get(category, "Error")
    
    # Если нужно показать детали, добавляем их
    if with_details:
        if lang == "ru":
            return f"❌ {base_message}: {error_message}\n\nТип: {error_type}"
        else:
            return f"❌ {base_message}: {error_message}\n\nType: {error_type}"
    else:
        if lang == "ru":
            return f"❌ {base_message}. Пожалуйста, попробуйте позже или обратитесь к администратору."
        else:
            return f"❌ {base_message}. Please try again later or contact the administrator."


def should_retry(error_data: Dict[str, Any], current_attempt: int) -> Tuple[bool, int]:
    """
    Определяет, нужно ли повторить операцию после ошибки.
    
    Args:
        error_data: Данные об ошибке
        current_attempt: Номер текущей попытки
        
    Returns:
        (retry_needed, retry_delay) - нужно ли повторять и задержка перед повторением
    """
    category = error_data["category"]
    category_info = ERROR_CATEGORIES.get(category, {
        "max_retries": 0,
        "retry_delay": 0,
        "critical": True
    })
    
    # Определяем, нужно ли повторять
    retry_needed = current_attempt <= category_info["max_retries"]
    
    # Получаем задержку перед повторением
    retry_delay = category_info["retry_delay"]
    
    return retry_needed, retry_delay


def get_error_analytics() -> Dict[str, Any]:
    """
    Возвращает аналитику по ошибкам.
    
    Returns:
        Словарь с аналитическими данными по ошибкам
    """
    # Собираем статистику по категориям ошибок
    category_stats = {}
    for error in error_storage:
        category = error["category"]
        if category not in category_stats:
            category_stats[category] = 0
        category_stats[category] += 1
    
    # Собираем статистику по пользователям
    user_stats = {}
    for error in error_storage:
        user_id = error.get("user_id")
        if not user_id:
            continue
            
        user_id_str = str(user_id)
        if user_id_str not in user_stats:
            user_stats[user_id_str] = 0
        user_stats[user_id_str] += 1
    
    # Собираем статистику по операциям
    operation_stats = {}
    for error in error_storage:
        operation = error.get("operation")
        if not operation:
            continue
            
        if operation not in operation_stats:
            operation_stats[operation] = 0
        operation_stats[operation] += 1
    
    # Возвращаем аналитические данные
    return {
        "total_errors": len(error_storage),
        "category_stats": category_stats,
        "user_stats": user_stats,
        "operation_stats": operation_stats,
        "recent_errors": error_storage[-10:]  # Последние 10 ошибок
    }


def clear_error_storage() -> None:
    """Очищает хранилище ошибок."""
    global error_storage
    error_storage = []


# Примеры использования:
# try:
#     # Код, который может вызвать ошибку
#     raise ValueError("This is a test error")
# except Exception as e:
#     error_data = log_error(
#         error=e,
#         context={"test": True},
#         user_id=123456,
#         operation="test_operation"
#     )
#     
#     user_message = format_error_for_user(e, with_details=True)
#     print(user_message)
#     
#     retry, delay = should_retry(error_data, current_attempt=1)
#     if retry:
#         print(f"Retrying after {delay} seconds...")
