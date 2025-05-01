"""
Модуль для обработки ошибок API.
"""

import asyncio
import logging
import re
from typing import Any, Callable, Dict, Optional, TypeVar, Union
import aiohttp
from aiohttp import ClientResponse

# Настройки логирования
logger = logging.getLogger(__name__)

# Тип для обобщенного результата запроса
T = TypeVar('T')


class APIError(Exception):
    """Базовый класс для ошибок API."""

    def __init__(self, message: str, status_code: int = 0,
                 response_data: Optional[Dict[str, Any]] = None):
        """
        Инициализирует исключение API ошибки.

        Args:
            message: Сообщение об ошибке
            status_code: HTTP статус-код ответа
            response_data: Данные ответа API
        """
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Строковое представление ошибки."""
        return f"{self.message} (Статус: {self.status_code})"


class AuthenticationError(APIError):
    """Ошибка аутентификации (401)."""


class NotFoundError(APIError):
    """Ресурс не найден (404)."""


class RateLimitExceeded(APIError):
    """Превышен лимит запросов (429)."""

    def __init__(self, message: str, status_code: int = 429,
                 response_data: Optional[Dict[str, Any]] = None,
                 retry_after: int = 60):
        """
        Инициализирует исключение о превышении лимита запросов.

        Args:
            message: Сообщение об ошибке
            status_code: HTTP статус-код ответа
            response_data: Данные ответа API
            retry_after: Рекомендуемое время ожидания в секундах
        """
        super().__init__(message, status_code, response_data)
        self.retry_after = retry_after


class ServerError(APIError):
    """Серверная ошибка (5xx)."""


class BadRequestError(APIError):
    """Ошибка в запросе клиента (400)."""


async def handle_response(response: ClientResponse) -> Dict[str, Any]:
    """
    Обрабатывает HTTP-ответ и возвращает данные или вызывает соответствующее исключение.

    Args:
        response: HTTP-ответ от API

    Returns:
        Данные из ответа API

    Raises:
        APIError: Если ответ содержит ошибку
    """
    status = response.status

    # Пробуем получить данные ответа
    try:
        data = await response.json()
    except Exception as e:
        # Если не удалось преобразовать ответ в JSON
        data = {}
        logger.warning(f"Не удалось прочитать JSON из ответа: {e}")

    # Если статус успешный (2xx), возвращаем данные
    if 200 <= status < 300:
        return data

    # В зависимости от статуса вызываем соответствующее исключение
    error_message = data.get('error', 'Неизвестная ошибка API')
    # Общее сообщение об ошибке
    if isinstance(error_message, dict):
        error_message = str(error_message)

    if status == 401:
        raise AuthenticationError(
            "Ошибка авторизации в API", status, data
        )
    elif status == 404:
        raise NotFoundError(
            "Запрашиваемый ресурс не найден", status, data
        )
    elif status == 429:
        # Извлекаем Retry-After из заголовков или используем значение по умолчанию
        retry_after_header = response.headers.get('Retry-After', '')
        
        try:
            # Если значение можно преобразовать в число, считаем его секундами
            retry_after = int(retry_after_header) if retry_after_header else 60
        except ValueError:
            # Если значение не число, пробуем разобрать как HTTP-дату или используем значение по умолчанию
            retry_after = 60

        # Создаем специальное исключение с информацией о повторной попытке
        rate_limit_error = RateLimitExceeded(
            f"Превышен лимит запросов. Повторите через {retry_after} сек.",
            status,
            data,
            retry_after=retry_after
        )
        raise rate_limit_error
    elif 500 <= status < 600:
        raise ServerError(
            f"Серверная ошибка API (код {status})", status, data
        )
    elif status == 400:
        raise BadRequestError(
            f"Неверный запрос: {error_message}", status, data
        )
    else:
        # Для других ошибок используем базовый класс
        raise APIError(
            f"Ошибка API: {error_message}", status, data
        )


async def retry_request(
    request_func: Callable[..., T],
    limiter=None,
    endpoint_type: str = "other",
    max_retries: int = 3,
    **kwargs
) -> T:
    """
    Выполняет запрос с автоматическими повторными попытками и соблюдением ограничений.

    Args:
        request_func: Асинхронная функция для выполнения запроса
        limiter: Объект RateLimiter для контроля скорости запросов
        endpoint_type: Тип эндпоинта для определения лимитов
        max_retries: Максимальное количество повторных попыток
        **kwargs: Дополнительные параметры для функции запроса

    Returns:
        Результат выполнения запроса

    Raises:
        APIError: Если все попытки запроса завершились неудачно
    """
    # Ожидаем разрешения от лимитера, если он предоставлен
    if limiter:
        await limiter.wait_for_call(endpoint_type)

    attempt = 0
    last_error = None

    # Пробуем выполнить запрос несколько раз
    while attempt <= max_retries:
        try:
            # Выполняем запрос
            result = await request_func(**kwargs)
            
            # Обновляем состояние лимитера после успешного запроса
            if limiter:
                limiter.update_after_call(endpoint_type)
                
            return result
            
        except (aiohttp.ClientError, APIError) as e:
            last_error = e
            attempt += 1

            # Логируем ошибку
            if isinstance(e, aiohttp.ClientResponseError):
                error_status = getattr(e, 'status', 0)
                error_message = getattr(e, 'message', str(e))
                logger.warning(
                    f"Попытка {attempt}/{max_retries} не удалась: "
                    f"HTTP {error_status} - {error_message}"
                )
                
                # Обработка превышения лимита запросов (429)
                if error_status == 429 and limiter:
                    # Извлекаем Retry-After из заголовков
                    retry_after = 60  # Значение по умолчанию
                    
                    # Получаем заголовки, если они есть
                    headers = getattr(e, 'headers', {})
                    if headers:
                        retry_after_header = headers.get('Retry-After', '')
                        if retry_after_header:
                            try:
                                retry_after = int(retry_after_header)
                            except ValueError:
                                # Если не удалось преобразовать в число, используем значение по умолчанию
                                pass
                        
                    # Отмечаем лимит в RateLimiter
                    limiter.mark_rate_limited(endpoint_type, retry_after)
                    
                    # Если это не последняя попытка, ждем указанное время
                    if attempt <= max_retries:
                        # Ждем указанное время перед следующей попыткой
                        logger.info(f"Ожидание {retry_after} сек. из-за превышения лимита")
                        await asyncio.sleep(retry_after)
                        continue
            
            elif isinstance(e, APIError):
                logger.warning(
                    f"Попытка {attempt}/{max_retries} не удалась: "
                    f"{e.message} (код {e.status_code})"
                )
                
                # Обработка превышения лимита запросов (429)
                if e.status_code == 429 and limiter and hasattr(e, 'retry_after'):
                    # Отмечаем лимит в RateLimiter
                    retry_after = getattr(e, 'retry_after', 60)
                    limiter.mark_rate_limited(endpoint_type, retry_after)
                    
                    # Если это не последняя попытка, ждем указанное время
                    if attempt <= max_retries:
                        # Ждем указанное время перед следующей попыткой
                        logger.info(f"Ожидание {retry_after} сек. из-за превышения лимита")
                        await asyncio.sleep(retry_after)
                        continue
            else:
                logger.warning(f"Попытка {attempt}/{max_retries} не удалась: {str(e)}")
            
            # Экспоненциальная задержка между попытками (если не 429)
            if attempt <= max_retries:
                delay = min(2 ** (attempt - 1), 30)  # Максимум 30 сек.
                logger.info(f"Повтор через {delay} сек.")
                await asyncio.sleep(delay)
                
    # Если все попытки не удались, преобразуем последнюю ошибку в APIError
    if isinstance(last_error, aiohttp.ClientResponseError):
        error_status = getattr(last_error, 'status', 0)
        error_message = getattr(last_error, 'message', str(last_error))
        
        raise APIError(
            f"Ошибка после {max_retries + 1} попыток: {error_message}",
            error_status
        )
    elif isinstance(last_error, APIError):
        # Если это уже APIError, пробрасываем его дальше
        raise last_error
    else:
        # Для других типов ошибок
        raise APIError(
            f"Неизвестная ошибка после {max_retries + 1} попыток: {str(last_error)}",
            0
        )
