"""
Модуль для управления лимитами запросов к API.
"""

import asyncio
import logging
import time
import math
from typing import Dict, Optional, Any, Tuple

# Настройка логирования
logger = logging.getLogger(__name__)

# Ограничения запросов для различных типов эндпоинтов DMarket API
# Значения в запросах в секунду (rps)
DMARKET_API_RATE_LIMITS = {
    "market": 2,      # Рыночные запросы (2 запроса в секунду)
    "trade": 1,       # Торговые операции (1 запрос в секунду)
    "user": 5,        # Запросы пользовательских данных
    "balance": 10,    # Запросы баланса
    "other": 5,       # Прочие запросы
}

# Базовая задержка для экспоненциального отступа при ошибках 429
BASE_RETRY_DELAY = 1.0  # 1 секунда


class RateLimiter:
    """
    Класс для контроля скорости запросов к API DMarket.

    Позволяет:
    - Ограничивать скорость запросов к разным эндпоинтам
    - Ожидать до освобождения слота для запроса
    - Обрабатывать ситуации превышения лимита запросов от API
    - Реализовывать экспоненциальную задержку для обработки ошибок 429
    """

    def __init__(self, is_authorized: bool = True):
        """
        Инициализирует контроллер лимитов запросов.

        Args:
            is_authorized: Является ли клиент авторизованным
                (влияет на доступные лимиты запросов)
        """
        self.is_authorized = is_authorized
        
        # Лимиты запросов для разных типов эндпоинтов
        self.rate_limits = DMARKET_API_RATE_LIMITS.copy()
        
        # Пользовательские лимиты запросов
        self.custom_limits = {}
        
        # Временные точки последних запросов для разных типов эндпоинтов
        self.last_request_times: Dict[str, float] = {}
        
        # Временные метки сброса лимитов для каждого эндпоинта
        self.reset_times: Dict[str, float] = {}
        
        # Счетчики оставшихся запросов для каждого эндпоинта
        self.remaining_requests: Dict[str, int] = {}
        
        # Счетчики попыток для экспоненциальной задержки
        self.retry_attempts: Dict[str, int] = {}
        
        logger.info(f"Инициализирован контроллер лимитов запросов API (авторизован: {is_authorized})")
        
    def get_endpoint_type(self, path: str) -> str:
        """
        Определяет тип эндпоинта по его пути для DMarket API.
        
        Args:
            path: Путь эндпоинта API

        Returns:
            Тип эндпоинта ("market", "trade", "user", "balance", "other")
        """
        path = path.lower()
        
        # DMarket маркет эндпоинты
        market_keywords = [
            "/exchange/v1/market/", 
            "/market/items", 
            "/market/aggregated-prices",
            "/market/best-offers",
            "/market/search"
        ]
        if any(keyword in path for keyword in market_keywords):
            return "market"
            
        # DMarket торговые эндпоинты
        trade_keywords = [
            "/exchange/v1/market/buy", 
            "/exchange/v1/market/create-offer", 
            "/exchange/v1/user/offers/edit",
            "/exchange/v1/user/offers/delete"
        ]
        if any(keyword in path for keyword in trade_keywords):
            return "trade"
            
        # DMarket баланс и аккаунт
        balance_keywords = [
            "/api/v1/account/balance", 
            "/account/v1/balance"
        ]
        if any(keyword in path for keyword in balance_keywords):
            return "balance"
            
        # DMarket пользовательские эндпоинты
        user_keywords = [
            "/exchange/v1/user/inventory", 
            "/api/v1/account/details",
            "/exchange/v1/user/offers", 
            "/exchange/v1/user/targets"
        ]
        if any(keyword in path for keyword in user_keywords):
            return "user"
            
        return "other"
            
    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """
        Обновляет лимиты запросов на основе заголовков ответа DMarket API.
        
        Args:
            headers: Заголовки HTTP-ответа
        """
        # Заголовки для анализа: X-RateLimit-Remaining, X-RateLimit-Reset, X-RateLimit-Limit
        remaining_header = 'X-RateLimit-Remaining'
        reset_header = 'X-RateLimit-Reset'
        limit_header = 'X-RateLimit-Limit'
        
        # Получаем тип эндпоинта из заголовков или используем "other" по умолчанию
        endpoint_type = "other"
        if "X-RateLimit-Scope" in headers:
            scope = headers["X-RateLimit-Scope"].lower()
            if "market" in scope:
                endpoint_type = "market"
            elif "trade" in scope:
                endpoint_type = "trade"
            elif "user" in scope:
                endpoint_type = "user"
            elif "balance" in scope:
                endpoint_type = "balance"
        
        # Обновляем информацию о лимитах на основе заголовков
        if remaining_header in headers:
            try:
                remaining = int(headers[remaining_header])
                self.remaining_requests[endpoint_type] = remaining
                
                # Если в ответе есть заголовок с лимитом, обновляем его
                if limit_header in headers:
                    try:
                        limit = int(headers[limit_header])
                        # Устанавливаем лимит только если он отличается от текущего
                        if limit != self.rate_limits.get(endpoint_type):
                            self.rate_limits[endpoint_type] = limit
                            logger.info(f"Обновлен лимит для {endpoint_type}: {limit} запросов")
                    except (ValueError, KeyError):
                        pass
                
                # Если оставшееся количество запросов мало, логируем предупреждение
                if remaining <= 2:
                    logger.warning(
                        f"Почти исчерпан лимит запросов для {endpoint_type}: осталось {remaining}"
                    )
                
                # Если достигли лимита запросов (remaining <= 0), 
                # устанавливаем время сброса из заголовка Reset
                if remaining <= 0 and reset_header in headers:
                    try:
                        reset_time = float(headers[reset_header])
                        self.reset_times[endpoint_type] = reset_time
                        
                        # Вычисляем время ожидания до сброса
                        wait_time = max(0, reset_time - time.time())
                        logger.warning(
                            f"Достигнут лимит запросов для {endpoint_type}. "
                            f"Сброс через {wait_time:.2f} сек"
                        )
                    except (ValueError, KeyError):
                        pass
            except (ValueError, KeyError):
                pass

    async def wait_if_needed(self, endpoint_type: str = "other") -> None:
        """
        Ожидает, если необходимо, перед выполнением запроса указанного типа.
        
        Args:
            endpoint_type: Тип эндпоинта
        """
        # Проверяем, не находится ли эндпоинт под ограничением
        if endpoint_type in self.reset_times:
            reset_time = self.reset_times[endpoint_type]
            current_time = time.time()
            
            # Если время сброса еще не наступило
            if reset_time > current_time:
                wait_time = reset_time - current_time
                logger.info(f"Ожидание сброса лимита для {endpoint_type}: {wait_time:.2f} сек")
                await asyncio.sleep(wait_time)
                
                # После ожидания удаляем запись о временном ограничении
                del self.reset_times[endpoint_type]
                self.remaining_requests[endpoint_type] = self.rate_limits.get(endpoint_type, 5)
        
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
        
        # Обновляем время последнего запроса
        self.last_request_times[endpoint_type] = time.time()
    
    async def handle_429(self, endpoint_type: str, retry_after: Optional[int] = None) -> Tuple[float, int]:
        """
        Обрабатывает ошибку 429 (Too Many Requests) с экспоненциальной задержкой.
        
        Args:
            endpoint_type: Тип эндпоинта
            retry_after: Рекомендуемое время ожидания из заголовка Retry-After

        Returns:
            Tuple[float, int]: (время ожидания в секундах, новое количество попыток)
        """
        # Увеличиваем счетчик попыток для данного эндпоинта
        current_attempts = self.retry_attempts.get(endpoint_type, 0) + 1
        self.retry_attempts[endpoint_type] = current_attempts
        
        # Если есть заголовок Retry-After, используем его значение
        if retry_after is not None and retry_after > 0:
            wait_time = retry_after
        else:
            # Иначе используем экспоненциальную задержку с небольшим случайным компонентом
            # Base * 2^(attempts - 1) + random jitter
            base_wait = BASE_RETRY_DELAY * (2 ** (current_attempts - 1))
            jitter = 0.1 * base_wait * (0.5 - (time.time() % 1.0))  # 10% случайное отклонение
            wait_time = base_wait + jitter
            
            # Ограничиваем максимальное время ожидания 30 секундами
            wait_time = min(wait_time, 30.0)
        
        # Устанавливаем время сброса лимита
        self.reset_times[endpoint_type] = time.time() + wait_time
        
        logger.warning(
            f"Превышен лимит запросов для {endpoint_type} (попытка {current_attempts}). "
            f"Ожидание {wait_time:.2f} сек перед следующей попыткой."
        )
        
        # Выполняем ожидание
        await asyncio.sleep(wait_time)
        
        return wait_time, current_attempts
    
    def reset_retry_attempts(self, endpoint_type: str) -> None:
        """
        Сбрасывает счетчик попыток для эндпоинта после успешного запроса.
        
        Args:
            endpoint_type: Тип эндпоинта
        """
        if endpoint_type in self.retry_attempts:
            del self.retry_attempts[endpoint_type]
    
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
        if endpoint_type in self.rate_limits:
            # Для неавторизованных пользователей снижаем лимиты
            if not self.is_authorized and endpoint_type in ["market", "trade"]:
                return self.rate_limits[endpoint_type] / 2  # 50% от авторизованного лимита
            return self.rate_limits[endpoint_type]
        
        # Если тип эндпоинта неизвестен, используем лимит для "other"
        return self.rate_limits.get("other", 5)
    
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
        Возвращает количество оставшихся запросов в текущем окне.

        Args:
            endpoint_type: Тип эндпоинта

        Returns:
            Количество оставшихся запросов
        """
        # Если эндпоинт находится под ограничением
        if endpoint_type in self.reset_times and time.time() < self.reset_times[endpoint_type]:
            return 0
        
        # Возвращаем оставшееся количество запросов (или максимальное значение, если неизвестно)
        return self.remaining_requests.get(
            endpoint_type, 
            int(self.get_rate_limit(endpoint_type) * 60)  # Примерная оценка на 1 минуту
        )
