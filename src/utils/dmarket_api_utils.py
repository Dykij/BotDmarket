"""Утилиты для работы с DMarket API.
"""

import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from src.utils.api_error_handling import APIError, retry_request
from src.utils.rate_limiter import RateLimiter

# Тип для обобщенного результата запроса
T = TypeVar("T")

# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальный экземпляр RateLimiter
default_rate_limiter = RateLimiter(is_authorized=True)


async def execute_api_request(
    request_func: Callable[..., Coroutine[Any, Any, T]],
    endpoint_type: str = "other",
    max_retries: int = 3,
    is_authenticated: bool = True,
    **kwargs,
) -> T:
    """Выполняет запрос к API с контролем лимитов и обработкой ошибок.

    Args:
        request_func: Асинхронная функция для выполнения запроса
        endpoint_type: Тип эндпоинта для определения лимитов
        max_retries: Максимальное количество повторных попыток
        is_authenticated: Требуется ли аутентификация для запроса
        **kwargs: Дополнительные параметры для функции запроса

    Returns:
        Результат выполнения запроса

    Raises:
        APIError: Если все попытки запроса завершились неудачно

    """
    # Используем глобальный лимитер
    global default_rate_limiter

    # Если запрос является аутентифицированным, а лимитер не настроен соответствующим образом
    if is_authenticated != default_rate_limiter.is_authorized:
        # Создаем новый экземпляр лимитера с правильной настройкой
        default_rate_limiter = RateLimiter(is_authorized=is_authenticated)

    try:
        # Выполняем запрос с учетом ограничений и автоматическими повторными попытками
        result = await retry_request(
            request_func=request_func,
            limiter=default_rate_limiter,
            endpoint_type=endpoint_type,
            max_retries=max_retries,
            **kwargs,
        )

        return result

    except APIError as e:
        # Добавляем контекст в логи
        logger.error(f"Ошибка API при выполнении запроса {endpoint_type}: {e}")

        # Пробрасываем исключение дальше
        raise
