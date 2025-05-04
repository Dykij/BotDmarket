"""
Модуль для интеграции единого подхода к обработке исключений.
Предоставляет базовые классы исключений и декораторы для их обработки.
"""

from typing import Any, Callable, Dict, Optional, Type, Union, TypeVar, cast
import functools
import logging
import traceback
import inspect
from enum import Enum

from src.utils.logging_utils import get_logger

# Определение универсального типа для декораторов
F = TypeVar('F', bound=Callable[..., Any])

# Общие коды ошибок
class ErrorCode(Enum):
    """Перечисление кодов ошибок для унификации обработки."""
    UNKNOWN_ERROR = 1000
    API_ERROR = 2000
    VALIDATION_ERROR = 3000
    AUTH_ERROR = 4000
    RATE_LIMIT_ERROR = 5000
    NETWORK_ERROR = 6000
    DATABASE_ERROR = 7000
    BUSINESS_LOGIC_ERROR = 8000


class BaseAppException(Exception):
    """
    Базовый класс для всех исключений приложения.

    Attributes:
        code: Код ошибки из перечисления ErrorCode.
        message: Сообщение об ошибке.
        details: Дополнительные детали ошибки.
    """

    def __init__(
        self,
        message: str,
        code: Union[ErrorCode, int] = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Инициализирует исключение.

        Args:
            message: Сообщение об ошибке.
            code: Код ошибки.
            details: Дополнительная информация об ошибке.
        """
        self.code = code if isinstance(code, int) else code.value
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует исключение в словарь для логирования или API-ответа."""
        result = {
            'code': self.code,
            'message': self.message,
        }

        if self.details:
            result['details'] = self.details

        return result

    def __str__(self) -> str:
        """Строковое представление исключения."""
        details_str = f", details: {self.details}" if self.details else ""
        return f"{self.__class__.__name__}(code={self.code}, message='{self.message}'{details_str})"


class APIError(BaseAppException):
    """Исключение, связанное с внешними API."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: Union[ErrorCode, int] = ErrorCode.API_ERROR,
        details: Optional[Dict[str, Any]] = None,
        response_body: Optional[str] = None
    ):
        """
        Инициализирует исключение API.

        Args:
            message: Сообщение об ошибке.
            status_code: HTTP статус-код ответа.
            code: Внутренний код ошибки.
            details: Дополнительная информация.
            response_body: Тело ответа от API.
        """
        details = details or {}
        details['status_code'] = status_code
        if response_body:
            details['response_body'] = response_body
        super().__init__(message, code, details)
        self.status_code = status_code


class ValidationError(BaseAppException):
    """Исключение при ошибках валидации данных."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        code: Union[ErrorCode, int] = ErrorCode.VALIDATION_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Инициализирует исключение валидации.

        Args:
            message: Сообщение об ошибке.
            field: Поле, вызвавшее ошибку валидации.
            code: Код ошибки.
            details: Дополнительная информация.
        """
        details = details or {}
        if field:
            details['field'] = field
        super().__init__(message, code, details)


class BusinessLogicError(BaseAppException):
    """Исключение при ошибках бизнес-логики."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        code: Union[ErrorCode, int] = ErrorCode.BUSINESS_LOGIC_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Инициализирует исключение бизнес-логики.

        Args:
            message: Сообщение об ошибке.
            operation: Операция, вызвавшая ошибку.
            code: Код ошибки.
            details: Дополнительная информация.
        """
        details = details or {}
        if operation:
            details['operation'] = operation
        super().__init__(message, code, details)


def handle_exceptions(
    logger: Optional[logging.Logger] = None,
    default_error_message: str = "Произошла ошибка",
    reraise: bool = True
) -> Callable[[F], F]:
    """
    Декоратор для обработки исключений с логированием.

    Args:
        logger: Логгер для записи ошибок.
        default_error_message: Сообщение по умолчанию при ошибке.
        reraise: Если True, исключение будет выброшено повторно.

    Returns:
        Декорированная функция.
    """
    def decorator(func: F) -> F:
        # Создаем логгер на основе имени функции, если не передан
        nonlocal logger
        if logger is None:
            logger = get_logger(f"{func.__module__}.{func.__qualname__}")

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except BaseAppException as e:
                # Логируем исключение приложения
                logger.error(
                    f"{default_error_message}: {str(e)}",
                    extra={'context': e.to_dict()}
                )
                if reraise:
                    raise
            except Exception as e:
                # Логируем неожиданное исключение
                error_details = {
                    'exception_type': e.__class__.__name__,
                    'traceback': traceback.format_exc().split('\n')
                }
                logger.error(
                    f"Необработанное исключение в {func.__qualname__}: {str(e)}",
                    extra={'context': error_details}
                )
                if reraise:
                    raise

        return cast(F, wrapper)

    return decorator
