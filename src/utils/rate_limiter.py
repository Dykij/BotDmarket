"""
Модуль для управления лимитами запросов к API.
"""

import asyncio
import logging
import time
from typing import Dict, Optional

# Настройка логирования
logger = logging.getLogger(__name__)

# Значения ограничений запросов для различных типов эндпоинтов
# Значения в запросах в секунду (rps)
DEFAULT_API_RATE_LIMITS = {
    # Стандартные ограничения для разных типов эндпоинтов
    "market": 10,     # Рыночные запросы (получение предметов и т.д.)
    "trade": 5,       # Торговые операции (покупка/продажа)
    "user": 3,        # Запросы пользовательских данных
    "other": 15,      # Прочие запросы
}


class RateLimiter:
    """
    Класс для контроля скорости запросов к API.

    Позволяет:
    - Ограничивать скорость запросов к разным эндпоинтам
    - Ожидать до освобождения слота для запроса
    - Обрабатывать ситуации превышения лимита запросов от API
    """

    def __init__(self, is_authorized: bool = True):
        """
        Инициализирует контроллер лимитов запросов.

        Args:
            is_authorized: Является ли клиент авторизованным
                (влияет на доступные лимиты запросов)
        """
        self.is_authorized = is_authorized
        
        # Стандартные лимиты запросов для разных типов эндпоинтов
        self.default_limits = DEFAULT_API_RATE_LIMITS.copy()
        
        # Пользовательские лимиты запросов
        self.custom_limits = {}
        
        # Временные точки последних запросов для разных типов эндпоинтов
        self.last_request_times: Dict[str, float] = {}
        
        # Временные метки сброса лимитов
        self.reset_times: Dict[str, float] = {}
        
        # Счетчики запросов
        self.request_counters: Dict[str, int] = {}
        
        logger.info("Инициализирован контроллер лимитов запросов API")
        
    def get_endpoint_type(self, path: str) -> str:
        """
        Определяет тип эндпоинта по его пути.
        
        Args:
            path: Путь эндпоинта API

        Returns:
            Тип эндпоинта ("market", "trade", "user", "other")
        """
        path = path.lower()
        
        market_keywords = ["/marketplace-api/", "/items", "/market"]
        if any(keyword in path for keyword in market_keywords):
            return "market"
            
        trade_keywords = ["/exchange/", "/offers", "/targets", "/buy", "/sell"]
        if any(keyword in path for keyword in trade_keywords):
            return "trade"
            
        user_keywords = ["/account/", "/user", "/balance"]
        if any(keyword in path for keyword in user_keywords):
            return "user"
            
        return "other"
            
    def _get_endpoint_from_header(self, headers: Dict[str, str]) -> str:
        """
        Определяет тип эндпоинта на основе заголовков.
        
        Args:
            headers: HTTP заголовки
            
        Returns:
            Тип эндпоинта
        """
        # В реальности здесь может быть логика извлечения типа эндпоинта из заголовков
        # Например, из специальных заголовков X-RateLimit-Scope или X-RateLimit-Endpoint
        
        # Для примера вернем "other" как запасной вариант
        return "other"
            
    async def wait_if_needed(self, endpoint_type: str = "other") -> None:
        """
        Ожидает, если необходимо, перед выполнением запроса указанного типа.
        
        Args:
            endpoint_type: Тип эндпоинта
        """
        await self.wait_for_call(endpoint_type)
        
        # Обновляем время последнего запроса
        self.last_request_times[endpoint_type] = time.time()
        
        # Увеличиваем счетчик запросов
        if endpoint_type in self.request_counters:
            self.request_counters[endpoint_type] += 1
        else:
            self.request_counters[endpoint_type] = 1
            
    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """
        Обновляет лимиты запросов на основе заголовков ответа.
        
        Args:
            headers: Заголовки HTTP-ответа
        """
        # Пример заголовков с лимитами: X-RateLimit-Limit, X-RateLimit-Remaining,
        # X-RateLimit-Reset
        remaining_header = 'X-RateLimit-Remaining'
        reset_header = 'X-RateLimit-Reset'
        
        if remaining_header in headers and reset_header in headers:
            try:
                remaining = int(headers[remaining_header])
                reset_time = float(headers[reset_header])
                
                # Если достигли лимита запросов
                if remaining <= 0:
                    endpoint_type = self._get_endpoint_from_header(headers)
                    self.reset_times[endpoint_type] = reset_time
                    logger.warning(
                        f"Достигнут лимит запросов для {endpoint_type}. "
                        f"Сброс через {reset_time - time.time():.2f} сек"
                    )
            except (ValueError, KeyError):
                pass

    async def wait_for_call(self, endpoint_type: str = "other") -> None:
        """
        Ожидает, пока можно будет выполнить запрос указанного типа.

        Args:
            endpoint_type: Тип эндпоинта ("market", "trade", "user", "other")
        """
        # Если эндпоинт находится в состоянии ограничения
        if endpoint_type in self.reset_times:
            reset_time = self.reset_times[endpoint_type]
            current_time = time.time()
            
            # Проверяем, не истек ли уже таймаут
            if reset_time > current_time:
                wait_time = reset_time - current_time
                logger.info(f"Ожидание сброса лимита для {endpoint_type}: {wait_time:.2f} сек")
                await asyncio.sleep(wait_time)
                
                # После ожидания удаляем запись о таймауте
                del self.reset_times[endpoint_type]
                self.request_counters[endpoint_type] = 0
        
        # Получаем лимит запросов в секунду
        rate_limit = self.get_rate_limit(endpoint_type)
        
        # Если лимит не указан или равен бесконечности, нет необходимости ждать
        if rate_limit <= 0:
            return
        
        # Минимальный интервал между запросами в секундах
        min_interval = 1.0 / rate_limit
        
        # Время последнего запроса этого типа
        last_time = self.last_request_times.get(endpoint_type, 0)
        current_time = time.time()
        
        # Если с момента последнего запроса прошло меньше минимального интервала
        if current_time - last_time < min_interval:
            # Вычисляем необходимое время ожидания
            wait_time = min_interval - (current_time - last_time)
            
            # Если время ожидания значительное, логируем его
            if wait_time > 0.1:
                logger.debug(f"Соблюдение лимита {endpoint_type}: ожидание {wait_time:.3f} сек")
            
            # Ожидаем необходимое время
            await asyncio.sleep(wait_time)
    
    def update_after_call(self, endpoint_type: str = "other") -> None:
        """
        Обновляет состояние после выполнения запроса.

        Args:
            endpoint_type: Тип эндпоинта ("market", "trade", "user", "other")
        """
        # Обновляем время последнего запроса
        self.last_request_times[endpoint_type] = time.time()
        
        # Увеличиваем счетчик запросов
        self.request_counters[endpoint_type] = self.request_counters.get(endpoint_type, 0) + 1
    
    def mark_rate_limited(self, endpoint_type: str = "other", retry_after: int = 60) -> None:
        """
        Отмечает эндпоинт как находящийся под ограничением лимита запросов.

        Args:
            endpoint_type: Тип эндпоинта ("market", "trade", "user", "other")
            retry_after: Время в секундах до возможности повторить запрос
        """
        # Устанавливаем время сброса лимита
        self.reset_times[endpoint_type] = time.time() + retry_after
        
        logger.warning(
            f"Превышен лимит запросов для {endpoint_type}. "
            f"Следующий запрос возможен через {retry_after} сек."
        )
    
    def get_rate_limit(self, endpoint_type: str = "other") -> float:
        """
        Возвращает текущий лимит запросов в секунду для указанного типа эндпоинта.

        Args:
            endpoint_type: Тип эндпоинта

        Returns:
            Лимит запросов в секунду (rps)
        """
        # Проверяем пользовательские лимиты
        if endpoint_type in self.custom_limits:
            return self.custom_limits[endpoint_type]
        
        # Проверяем стандартные лимиты
        if endpoint_type in self.default_limits:
            return self.default_limits[endpoint_type]
        
        # Если тип эндпоинта неизвестен, используем лимит для "other"
        return self.default_limits.get("other", 15)
    
    def set_custom_limit(self, endpoint_type: str, limit: float) -> None:
        """
        Устанавливает пользовательский лимит запросов для указанного типа эндпоинта.

        Args:
            endpoint_type: Тип эндпоинта
            limit: Лимит запросов в секунду (rps)
        """
        self.custom_limits[endpoint_type] = limit
        logger.info(f"Установлен пользовательский лимит для {endpoint_type}: {limit} rps")
    
    def get_remaining_requests(self, endpoint_type: str = "other") -> int:
        """
        Возвращает примерное количество оставшихся запросов в текущем окне.

        Args:
            endpoint_type: Тип эндпоинта

        Returns:
            Оценочное количество оставшихся запросов
        """
        # Если эндпоинт находится под ограничением
        if endpoint_type in self.reset_times:
            return 0
        
        # Возвращаем оценочное количество
        return 1000  # Заглушка, в реальности нужно использовать данные из заголовков API
