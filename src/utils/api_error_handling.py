"""
Модуль для обработки ошибок API.
"""

import asyncio
import logging
import re
import time
from typing import Any, Callable, Dict, Optional, TypeVar, Union, List, Tuple
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
    
    @property
    def error_code(self) -> str:
        """Код ошибки из ответа API."""
        if isinstance(self.response_data, dict):
            # DMarket API возвращает код ошибки в разных форматах
            return str(self.response_data.get('code', 
                self.response_data.get('error_code',
                    self.response_data.get('error', ''))))
        return ''
    
    @property
    def human_readable(self) -> str:
        """Человекочитаемое сообщение об ошибке."""
        return f"Ошибка API (код {self.status_code}): {self.message}"


class AuthenticationError(APIError):
    """Ошибка аутентификации (401)."""
    
    @property
    def human_readable(self) -> str:
        """Человекочитаемое сообщение об ошибке."""
        return (f"Ошибка аутентификации: проверьте ваши API ключи или токен.\n"
                f"Детали: {self.message}")


class ForbiddenError(APIError):
    """Доступ запрещен (403)."""
    
    @property
    def human_readable(self) -> str:
        """Человекочитаемое сообщение об ошибке."""
        return (f"Доступ запрещен: у вас нет прав для выполнения этого действия.\n"
                f"Детали: {self.message}")


class NotFoundError(APIError):
    """Ресурс не найден (404)."""
    
    @property
    def human_readable(self) -> str:
        """Человекочитаемое сообщение об ошибке."""
        return (f"Ресурс не найден: запрашиваемые данные не существуют.\n"
                f"Детали: {self.message}")


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
    
    @property
    def human_readable(self) -> str:
        """Человекочитаемое сообщение об ошибке."""
        return (f"Превышен лимит запросов: пожалуйста, подождите {self.retry_after} секунд.\n"
                f"Детали: {self.message}")


class ServerError(APIError):
    """Серверная ошибка (5xx)."""
    
    @property
    def human_readable(self) -> str:
        """Человекочитаемое сообщение об ошибке."""
        return (f"Ошибка сервера: произошла внутренняя ошибка на сервере.\n"
                f"Код: {self.status_code}\n"
                f"Детали: {self.message}")


class BadRequestError(APIError):
    """Ошибка в запросе клиента (400)."""
    
    @property
    def human_readable(self) -> str:
        """Человекочитаемое сообщение об ошибке."""
        return (f"Неверный запрос: проверьте параметры вашего запроса.\n"
                f"Детали: {self.message}")


class DMarketSpecificError(APIError):
    """Ошибки, специфичные для DMarket API."""
    
    def __init__(self, message: str, status_code: int = 0,
                 response_data: Optional[Dict[str, Any]] = None,
                 error_code: str = ''):
        """
        Инициализирует исключение для ошибок, специфичных для DMarket API.

        Args:
            message: Сообщение об ошибке
            status_code: HTTP статус-код ответа
            response_data: Данные ответа API
            error_code: Код ошибки DMarket API
        """
        super().__init__(message, status_code, response_data)
        self._error_code = error_code
    
    @property
    def error_code(self) -> str:
        """Код ошибки из ответа API."""
        if self._error_code:
            return self._error_code
        return super().error_code
    
    @property
    def human_readable(self) -> str:
        """Человекочитаемое сообщение об ошибке."""
        code_msg = f" (код {self.error_code})" if self.error_code else ""
        return f"Ошибка DMarket API{code_msg}: {self.message}"


class InsufficientFundsError(DMarketSpecificError):
    """Недостаточно средств для выполнения операции."""
    
    @property
    def human_readable(self) -> str:
        """Человекочитаемое сообщение об ошибке."""
        return "Недостаточно средств на балансе для выполнения операции."


class ItemNotAvailableError(DMarketSpecificError):
    """Предмет недоступен для покупки/продажи."""
    
    @property
    def human_readable(self) -> str:
        """Человекочитаемое сообщение об ошибке."""
        return "Предмет более недоступен для покупки или продажи."


class TemporaryUnavailableError(DMarketSpecificError):
    """API временно недоступно."""
    
    @property
    def human_readable(self) -> str:
        """Человекочитаемое сообщение об ошибке."""
        return "API DMarket временно недоступно. Пожалуйста, попробуйте позже."


# Словарь для маппинга кодов ошибок DMarket на классы исключений
DMARKET_ERROR_MAPPING = {
    'InsuficientAmount': InsufficientFundsError,
    'NotEnoughMoney': InsufficientFundsError,
    'ItemNotFound': ItemNotAvailableError,
    'WalletNotFound': DMarketSpecificError,
    'OfferNotFound': ItemNotAvailableError,
    'TemporaryUnavailable': TemporaryUnavailableError,
    'ServiceUnavailable': TemporaryUnavailableError,
}


async def handle_api_error(error: APIError) -> str:
    """
    Обрабатывает ошибку API и возвращает человекочитаемое сообщение.
    
    Args:
        error: Объект исключения APIError
        
    Returns:
        Человекочитаемое сообщение об ошибке
    """
    # Если это ошибка превышения лимита запросов, добавляем информацию о времени ожидания
    if isinstance(error, RateLimitExceeded):
        return (
            f"⚠️ Превышен лимит запросов к API.\n"
            f"Пожалуйста, подождите {error.retry_after} секунд перед повторной попыткой."
        )
    
    # Если это ошибка авторизации, предлагаем проверить ключи API
    elif isinstance(error, AuthenticationError):
        return (
            "🔑 Ошибка авторизации в API.\n"
            "Пожалуйста, проверьте правильность ваших API ключей."
        )
    
    # Если это ошибка запрета доступа
    elif isinstance(error, ForbiddenError):
        return (
            "🚫 Доступ запрещен.\n"
            "У вас нет прав для выполнения этого действия."
        )
    
    # Если это ошибка "не найдено"
    elif isinstance(error, NotFoundError):
        return (
            "🔍 Запрашиваемые данные не найдены.\n"
            "Возможно, ресурс был удален или перемещен."
        )
    
    # Если это ошибка сервера
    elif isinstance(error, ServerError):
        return (
            "⚙️ Внутренняя ошибка сервера API.\n"
            f"Код ошибки: {error.status_code}\n"
            "Пожалуйста, попробуйте позже."
        )
    
    # Специфичные ошибки DMarket
    elif isinstance(error, InsufficientFundsError):
        return (
            "💰 Недостаточно средств на балансе.\n"
            "Пожалуйста, пополните счет для продолжения операции."
        )
    
    elif isinstance(error, ItemNotAvailableError):
        return (
            "🛒 Предмет недоступен.\n"
            "Возможно, он был уже куплен или снят с продажи."
        )
    
    # Для всех остальных ошибок
    return (
        f"❌ Ошибка API (код {error.status_code}):\n"
        f"{error.message}"
    )


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
        try:
            # Пробуем прочитать сырой текст
            text = await response.text()
            data = {"raw_text": text}
        except Exception:
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

    # Получаем код ошибки DMarket, если есть
    dmarket_error_code = ''
    if isinstance(data, dict):
        dmarket_error_code = data.get('code', data.get('error_code', ''))

    # Проверяем, есть ли специальный класс для этого кода ошибки
    error_class = None
    if dmarket_error_code and dmarket_error_code in DMARKET_ERROR_MAPPING:
        error_class = DMARKET_ERROR_MAPPING[dmarket_error_code]

    if status == 401:
        raise AuthenticationError(
            "Ошибка авторизации в API", status, data
        )
    elif status == 403:
        raise ForbiddenError(
            "Доступ запрещен", status, data
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
        # Если есть специальный класс для этой ошибки DMarket
        if error_class:
            raise error_class(
                f"Ошибка DMarket: {error_message}", status, data, dmarket_error_code
            )
        else:
            raise BadRequestError(
                f"Неверный запрос: {error_message}", status, data
            )
    else:
        # Если есть специальный класс для этой ошибки DMarket
        if error_class:
            raise error_class(
                f"Ошибка DMarket: {error_message}", status, data, dmarket_error_code
            )
        else:
            # Для других ошибок используем базовый класс
            raise APIError(
                f"Ошибка API: {error_message}", status, data
            )


class RetryStrategy:
    """Класс, определяющий стратегию повторных попыток."""
    
    def __init__(self, 
                 max_retries: int = 3, 
                 initial_delay: float = 1.0,
                 max_delay: float = 30.0,
                 backoff_factor: float = 2.0,
                 status_codes_to_retry: Optional[List[int]] = None):
        """
        Инициализирует стратегию повторных попыток.
        
        Args:
            max_retries: Максимальное количество повторных попыток
            initial_delay: Начальная задержка в секундах
            max_delay: Максимальная задержка в секундах
            backoff_factor: Множитель для увеличения задержки
            status_codes_to_retry: Список HTTP статус-кодов, при которых нужно повторять запрос
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.status_codes_to_retry = status_codes_to_retry or [429, 500, 502, 503, 504]
    
    def should_retry(self, attempt: int, status_code: int) -> bool:
        """
        Определяет, нужно ли делать повторную попытку.
        
        Args:
            attempt: Номер текущей попытки (начиная с 1)
            status_code: HTTP статус-код ответа
            
        Returns:
            True, если нужно делать повторную попытку
        """
        return (attempt <= self.max_retries) and (status_code in self.status_codes_to_retry)
    
    def get_delay(self, attempt: int, retry_after: Optional[int] = None) -> float:
        """
        Возвращает задержку перед следующей попыткой.
        
        Args:
            attempt: Номер текущей попытки (начиная с 1)
            retry_after: Рекомендуемое время ожидания из заголовка Retry-After
            
        Returns:
            Задержка в секундах
        """
        if retry_after is not None:
            return float(retry_after)
        
        delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)


async def retry_request(
    request_func: Callable[..., T],
    limiter=None,
    endpoint_type: str = "other",
    retry_strategy: Optional[RetryStrategy] = None,
    **kwargs
) -> T:
    """
    Выполняет запрос с автоматическими повторными попытками и соблюдением ограничений.

    Args:
        request_func: Асинхронная функция для выполнения запроса
        limiter: Объект RateLimiter для контроля скорости запросов
        endpoint_type: Тип эндпоинта для определения лимитов
        retry_strategy: Стратегия повторных попыток
        **kwargs: Дополнительные параметры для функции запроса

    Returns:
        Результат выполнения запроса

    Raises:
        APIError: Если все попытки запроса завершились неудачно
    """
    # Если стратегия не указана, используем стратегию по умолчанию
    if retry_strategy is None:
        retry_strategy = RetryStrategy()
    
    # Ожидаем разрешения от лимитера, если он предоставлен
    if limiter:
        await limiter.wait_for_call(endpoint_type)

    attempt = 0
    last_error = None
    start_time = time.time()

    # Пробуем выполнить запрос несколько раз
    while attempt <= retry_strategy.max_retries:
        try:
            # Выполняем запрос
            result = await request_func(**kwargs)
            
            # Обновляем состояние лимитера после успешного запроса
            if limiter:
                limiter.update_after_call(endpoint_type)
            
            # Если запрос был повторным, логируем успех
            if attempt > 0:
                logger.info(f"Успешный запрос после {attempt} повторных попыток")
                
            return result
            
        except (aiohttp.ClientError, APIError) as e:
            last_error = e
            attempt += 1
            
            # Извлекаем статус-код и определяем, нужно ли делать повторную попытку
            status_code = 0
            retry_after = None
            
            if isinstance(e, aiohttp.ClientResponseError):
                status_code = getattr(e, 'status', 0)
                # Пытаемся извлечь Retry-After из заголовков
                headers = getattr(e, 'headers', {})
                if headers and 'Retry-After' in headers:
                    try:
                        retry_after = int(headers['Retry-After'])
                    except (ValueError, TypeError):
                        retry_after = None
            elif isinstance(e, APIError):
                status_code = e.status_code
                # Если это RateLimitExceeded, у него есть retry_after
                if isinstance(e, RateLimitExceeded):
                    retry_after = e.retry_after

            # Логируем информацию об ошибке
            error_message = str(e)
            logger.warning(
                f"Попытка {attempt}/{retry_strategy.max_retries + 1} не удалась: "
                f"Статус {status_code} - {error_message}"
            )
            
            # Проверяем, нужно ли делать повторную попытку
            if not retry_strategy.should_retry(attempt, status_code):
                logger.info(f"Прекращаем повторные попытки после {attempt} неудачных попыток")
                break
            
            # Обновляем лимитер, если это ошибка превышения лимита
            if status_code == 429 and limiter:
                limiter.mark_rate_limited(endpoint_type, retry_after or 60)
            
            # Определяем задержку перед следующей попыткой
            delay = retry_strategy.get_delay(attempt, retry_after)
            
            # Логируем информацию о повторной попытке
            logger.info(f"Повторная попытка через {delay:.1f} сек.")
            
            # Ждем перед следующей попыткой
            await asyncio.sleep(delay)
            
    # Общее время выполнения запроса со всеми повторными попытками
    total_time = time.time() - start_time
    logger.info(f"Общее время выполнения запроса: {total_time:.2f} сек.")
            
    # Если все попытки не удались, преобразуем последнюю ошибку в APIError
    if isinstance(last_error, aiohttp.ClientResponseError):
        error_status = getattr(last_error, 'status', 0)
        error_message = getattr(last_error, 'message', str(last_error))
        
        raise APIError(
            f"Ошибка после {attempt} попыток: {error_message}",
            error_status
        )
    elif isinstance(last_error, APIError):
        # Если это уже APIError, пробрасываем его дальше
        raise last_error
    else:
        # Для других типов ошибок
        raise APIError(
            f"Неизвестная ошибка после {attempt} попыток: {str(last_error)}",
            0
        )


# Специализированная обработка ошибок DMarket API
def classify_dmarket_error(status_code: int, response_data: Dict[str, Any]) -> APIError:
    """
    Классифицирует ошибки DMarket API и возвращает соответствующее исключение.
    
    Args:
        status_code: HTTP статус-код ответа
        response_data: Данные ответа API
        
    Returns:
        Соответствующее исключение APIError
    """
    error_message = response_data.get('error', 'Неизвестная ошибка DMarket API')
    if isinstance(error_message, dict):
        error_message = str(error_message)
    
    # Получаем код ошибки DMarket
    dmarket_error_code = response_data.get('code', response_data.get('error_code', ''))
    
    # Обработка специфичных ошибок DMarket по коду
    if dmarket_error_code in DMARKET_ERROR_MAPPING:
        error_class = DMARKET_ERROR_MAPPING[dmarket_error_code]
        return error_class(
            f"Ошибка DMarket: {error_message}", 
            status_code, 
            response_data,
            dmarket_error_code
        )
    
    # Обработка по HTTP статус-коду
    if status_code == 401:
        return AuthenticationError(
            "Ошибка авторизации в DMarket API", status_code, response_data
        )
    elif status_code == 403:
        return ForbiddenError(
            "Доступ запрещен DMarket API", status_code, response_data
        )
    elif status_code == 404:
        return NotFoundError(
            "Ресурс не найден в DMarket API", status_code, response_data
        )
    elif status_code == 429:
        retry_after = response_data.get('retry_after', 60)
        return RateLimitExceeded(
            f"Превышен лимит запросов к DMarket API. Повторите через {retry_after} сек.",
            status_code,
            response_data,
            retry_after=retry_after
        )
    elif 500 <= status_code < 600:
        return ServerError(
            f"Серверная ошибка DMarket API (код {status_code})", status_code, response_data
        )
    elif status_code == 400:
        return BadRequestError(
            f"Неверный запрос к DMarket API: {error_message}", status_code, response_data
        )
    else:
        # Для неизвестных ошибок используем базовый класс
        return DMarketSpecificError(
            f"Неизвестная ошибка DMarket API: {error_message}", 
            status_code, 
            response_data,
            dmarket_error_code
        )
