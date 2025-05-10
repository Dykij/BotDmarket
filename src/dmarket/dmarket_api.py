"""DMarket API client module for interacting with DMarket API.

This module provides an asynchronous client for DMarket API, including:
- Signature generation for authenticated requests
- Rate limiting and retry logic
- Methods for market operations (get items, buy, sell, inventory, balance)
- Error handling and logging
- Caching of frequently used requests
- Support for all documented DMarket API endpoints

Example usage:

    # Импортируем класс DMarketAPI
    from src.dmarket.dmarket_api import DMarketAPI
    
    # Создаем экземпляр API клиента
    api = DMarketAPI(public_key, secret_key)
    
    # Используем методы API
    items = await api.get_market_items(game="csgo")
    balance = await api.get_balance()  # Рекомендуемый метод получения баланса

Documentation: https://docs.dmarket.com/v1/swagger.html
"""
import asyncio
import hashlib
import hmac
import json
import logging
import time
import traceback
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx
import requests

from src.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# TTL для кэша в секундах
CACHE_TTL = {
    "short": 30,  # 30 секунд для часто меняющихся данных
    "medium": 300,  # 5 минут для умеренно стабильных данных
    "long": 1800,  # 30 минут для стабильных данных
}

# Кэш для хранения результатов запросов
api_cache = {}


class DMarketAPI:
    """Асинхронный клиент для работы с DMarket API.

    Основные возможности:
    - Генерация подписей для приватных запросов
    - Асинхронные методы для работы с маркетом, инвентарём, балансом
    - Встроенный rate limiting и автоматические повторы при ошибках
    - Логирование и обработка ошибок
    - Кэширование часто используемых запросов
    - Поддержка всех документированных эндпоинтов DMarket API

    Пример:
        api = DMarketAPI(public_key, secret_key)
        items = await api.get_market_items(game="csgo")
    """

    # БАЗОВЫЕ ЭНДПОИНТЫ (согласно документации)
    BASE_URL = "https://api.dmarket.com"
    
    # Баланс и аккаунт
    ENDPOINT_BALANCE = "/account/v1/balance"  # Основной эндпоинт баланса
    ENDPOINT_BALANCE_LEGACY = "/api/v1/account/balance"  # Альтернативный эндпоинт
    ENDPOINT_ACCOUNT_DETAILS = "/api/v1/account/details"  # Детали аккаунта
    ENDPOINT_ACCOUNT_OFFERS = "/api/v1/account/offers"  # Активные торговые предложения

    # Маркет
    ENDPOINT_MARKET_ITEMS = "/exchange/v1/market/items"  # Поиск предметов на маркете
    ENDPOINT_MARKET_PRICE_AGGREGATED = "/exchange/v1/market/aggregated-prices"  # Агрегированные цены
    ENDPOINT_MARKET_META = "/exchange/v1/market/meta"  # Метаданные маркета

    # Пользователь
    ENDPOINT_USER_INVENTORY = "/exchange/v1/user/inventory"  # Инвентарь пользователя
    ENDPOINT_USER_OFFERS = "/exchange/v1/user/offers"  # Предложения пользователя
    ENDPOINT_USER_TARGETS = "/exchange/v1/target-lists"  # Целевые предложения пользователя

    # Операции
    ENDPOINT_PURCHASE = "/exchange/v1/market/items/buy"  # Покупка предмета
    ENDPOINT_SELL = "/exchange/v1/user/inventory/sell"  # Выставить на продажу
    ENDPOINT_OFFER_EDIT = "/exchange/v1/user/offers/edit"  # Редактирование предложения
    ENDPOINT_OFFER_DELETE = "/exchange/v1/user/offers/delete"  # Удаление предложения

    # Статистика и аналитика
    ENDPOINT_SALES_HISTORY = "/account/v1/sales-history"  # История продаж
    ENDPOINT_ITEM_PRICE_HISTORY = "/exchange/v1/market/price-history"  # История цен предмета

    # Новые эндпоинты 2024
    ENDPOINT_MARKET_BEST_OFFERS = "/exchange/v1/market/best-offers"  # Лучшие предложения на маркете
    ENDPOINT_MARKET_SEARCH = "/exchange/v1/market/search"  # Расширенный поиск

    # Известные коды ошибок DMarket API и рекомендации по их обработке
    ERROR_CODES = {
        400: "Неверный запрос или параметры",
        401: "Неверная аутентификация",
        403: "Доступ запрещен",
        404: "Ресурс не найден",
        429: "Слишком много запросов (rate limit)",
        500: "Внутренняя ошибка сервера",
        502: "Bad Gateway",
        503: "Сервис недоступен",
        504: "Gateway Timeout"
    }

    def __init__(
        self,
        public_key: str,
        secret_key: str,
        api_url: str = "https://api.dmarket.com",
        max_retries: int = 3,
        connection_timeout: float = 30.0,
        pool_limits: httpx.Limits = None,
        retry_codes: list[int] = None,
        enable_cache: bool = True,
    ):
        """Initialize DMarket API client.

        Args:
            public_key: DMarket API public key
            secret_key: DMarket API secret key
            api_url: API URL (default is https://api.dmarket.com)
            max_retries: Maximum number of retries for failed requests
            connection_timeout: Connection timeout in seconds
            pool_limits: Connection pool limits
            retry_codes: HTTP status codes to retry on
            enable_cache: Enable caching of frequent requests

        """
        self.public_key = public_key
        self.secret_key = secret_key.encode("utf-8") if secret_key else b""
        self.api_url = api_url
        self.max_retries = max_retries
        self.connection_timeout = connection_timeout
        self.enable_cache = enable_cache

        # Default retry codes: server errors and too many requests
        self.retry_codes = retry_codes or [429, 500, 502, 503, 504]

        # Connection pool settings
        self.pool_limits = pool_limits or httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
        )

        # HTTP client
        self._client = None

        # Initialize RateLimiter with authorization check
        self.rate_limiter = RateLimiter(
            is_authorized=bool(public_key and secret_key),
        )
        logger.info(
            f"Initialized DMarketAPI client "
            f"(authorized: {'yes' if public_key and secret_key else 'no'}, cache: {'enabled' if enable_cache else 'disabled'})",
        )

    async def __aenter__(self):
        """Context manager to use the client with async with."""
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close client when exiting context manager."""
        await self._close_client()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.connection_timeout,
                limits=self.pool_limits,
            )
        return self._client

    async def _close_client(self):
        """Close HTTP client if it exists."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _generate_signature(
        self,
        method: str,
        path: str,
        body: str = "",
    ) -> dict[str, str]:
        """Генерирует подпись для приватных запросов DMarket API согласно документации.

        Args:
            method: HTTP-метод ("GET", "POST" и т.д.)
            path: Путь запроса (например, "/exchange/v1/target/create")
            body: Тело запроса (строка JSON)

        Returns:
            dict: Заголовки с подписью и ключом API

        """
        if not self.public_key or not self.secret_key:
            return {"Content-Type": "application/json"}

        # Generate signature string
        timestamp = str(int(time.time()))
        string_to_sign = timestamp + method + path

        if body:
            string_to_sign += body

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.secret_key,
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Return headers with signature
        return {
            "X-Api-Key": self.public_key,
            "X-Request-Sign": signature,
            "X-Sign-Date": timestamp,
            "Content-Type": "application/json",
        }

    def _get_cache_key(
        self, method: str, path: str, params: dict[str, Any] = None, data: dict[str, Any] = None
    ) -> str:
        """Создает уникальный ключ для кэша на основе запроса.

        Args:
            method: HTTP-метод
            path: Путь запроса
            params: GET-параметры
            data: POST-данные

        Returns:
            str: Ключ кэша

        """
        key_parts = [method, path]

        if params:
            # Сортируем параметры для консистентного ключа
            sorted_params = sorted((str(k), str(v)) for k, v in params.items())
            key_parts.append(str(sorted_params))

        if data:
            # Для POST-данных используем хеш от JSON
            try:
                data_str = json.dumps(data, sort_keys=True)
                key_parts.append(hashlib.md5(data_str.encode()).hexdigest())
            except (TypeError, ValueError):
                key_parts.append(str(data))

        return hashlib.md5("|".join(key_parts).encode()).hexdigest()

    def _is_cacheable(self, method: str, path: str) -> tuple[bool, str]:
        """Определяет, можно ли кэшировать данный запрос и на какой период.

        Args:
            method: HTTP-метод
            path: Путь запроса

        Returns:
            Tuple[bool, str]: (можно_кэшировать, тип_ttl)

        """
        # GET-запросы можно кэшировать
        if method.upper() != "GET":
            return (False, "")

        # Определяем TTL на основе эндпоинта
        if any(
            endpoint in path
            for endpoint in [
                self.ENDPOINT_MARKET_META,
                self.ENDPOINT_MARKET_PRICE_AGGREGATED,
                "/meta",
                "/aggregated",
            ]
        ):
            return (True, "medium")  # Стабильные данные

        if any(
            endpoint in path
            for endpoint in [
                self.ENDPOINT_MARKET_ITEMS,
                self.ENDPOINT_USER_INVENTORY,
                self.ENDPOINT_MARKET_BEST_OFFERS,
                self.ENDPOINT_SALES_HISTORY,
                "/market/",
                "/items",
                "/inventory",
            ]
        ):
            return (True, "short")  # Часто меняющиеся данные

        if any(
            endpoint in path
            for endpoint in [
                self.ENDPOINT_BALANCE,
                self.ENDPOINT_BALANCE_LEGACY,
                self.ENDPOINT_ACCOUNT_DETAILS,
                "/balance",
                "/account/",
            ]
        ):
            return (True, "short")  # Финансовые данные - короткий кэш

        if any(
            endpoint in path
            for endpoint in [
                self.ENDPOINT_ITEM_PRICE_HISTORY,
                "/history",
                "/statistics",
            ]
        ):
            return (True, "long")  # Исторические данные - долгий кэш

        # По умолчанию - не кэшируем
        return (False, "")

    def _get_from_cache(self, cache_key: str) -> dict[str, Any] | None:
        """Получает данные из кэша, если они есть и не устарели.

        Args:
            cache_key: Ключ кэша

        Returns:
            Optional[Dict[str, Any]]: Данные из кэша или None

        """
        if not self.enable_cache:
            return None

        cache_entry = api_cache.get(cache_key)
        if not cache_entry:
            return None

        data, expire_time = cache_entry
        if time.time() < expire_time:
            logger.debug(f"Cache hit for key {cache_key[:8]}...")
            return data

        # Удаляем устаревшие данные
        logger.debug(f"Cache expired for key {cache_key[:8]}...")
        api_cache.pop(cache_key, None)
        return None

    def _save_to_cache(self, cache_key: str, data: dict[str, Any], ttl_type: str) -> None:
        """Сохраняет данные в кэш.

        Args:
            cache_key: Ключ кэша
            data: Данные для сохранения
            ttl_type: Тип TTL ('short', 'medium', 'long')

        """
        if not self.enable_cache:
            return

        ttl = CACHE_TTL.get(ttl_type, CACHE_TTL["short"])
        expire_time = time.time() + ttl
        api_cache[cache_key] = (data, expire_time)

        # Очистка кэша, если он слишком большой (более 500 записей)
        if len(api_cache) > 500:
            # Удаляем 20% старых записей
            current_time = time.time()
            keys_to_remove = sorted(
                api_cache.keys(),
                key=lambda k: api_cache[k][1],  # Сортировка по времени истечения
            )[:100]

            for key in keys_to_remove:
                api_cache.pop(key, None)

            logger.debug(f"Cache cleanup: removed {len(keys_to_remove)} old entries")

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] = None,
        data: dict[str, Any] = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Выполняет запрос к DMarket API с обработкой ошибок, повторными попытками и кешированием.

        Args:
            method: HTTP метод (GET, POST и т.д.)
            path: Путь API без базового URL
            params: Параметры запроса (для GET)
            data: Данные для запроса (для POST/PUT)
            force_refresh: Принудительно обновить кэш (если включен)

        Returns:
            Ответ API в виде словаря

        Raises:
            Exception: При ошибке запроса после всех повторных попыток
        """
        # Создаем клиента, если его нет
        client = await self._get_client()

        # Параметры по умолчанию
        if params is None:
            params = {}
        
        if data is None:
            data = {}

        # Полный URL запроса
        url = f"{self.api_url}{path}"

        # Определяем возможность кэширования и тип TTL заранее
        is_cacheable, ttl_type = self._is_cacheable(method, path)
        cache_key = ""

        # Проверяем кэш для GET запросов
        body_json = ""
        if method.upper() == "GET" and self.enable_cache and not force_refresh:
            cache_key = self._get_cache_key(method, path, params, data)

            # Пробуем получить из кэша
            if is_cacheable:
                cached_data = self._get_from_cache(cache_key)
                if cached_data is not None:
                    logger.debug(f"Использую кэшированные данные для {path}")
                    return cached_data

        # Формируем тело запроса для POST/PUT/PATCH
        if data and method.upper() in ("POST", "PUT", "PATCH"):
            body_json = json.dumps(data)

        # Генерируем заголовки с подписью
        headers = self._generate_signature(method.upper(), path, body_json)

        # Используем rate limiter чтобы не превысить лимиты API
        await self.rate_limiter.wait_if_needed("market" if "market" in path else "account")

        # Переменные для повторных попыток
        retries = 0
        last_error = None
        retry_delay = 1.0  # начальная задержка в секундах

        # Основной цикл запросов с повторами при ошибках
        while retries <= self.max_retries:
            try:
                # Выполняем запрос с нужным методом
                if method.upper() == "GET":
                    response = await client.get(url, params=params, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, headers=headers)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=data, headers=headers)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Неподдерживаемый HTTP метод: {method}")

                # Проверяем статус ответа
                response.raise_for_status()

                # Парсим JSON ответа
                try:
                    result = response.json()
                except Exception:
                    # Если не получается распарсить JSON, возвращаем текст
                    result = {"text": response.text, "status_code": response.status_code}

                # Сохраняем в кэш если нужно
                if method.upper() == "GET" and self.enable_cache and is_cacheable:
                    self._save_to_cache(cache_key, result, ttl_type)

                return result

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                response_text = e.response.text
                
                # Подробное логирование ошибки
                logger.warning(
                    f"HTTP ошибка {status_code} при запросе {method} {path}: {response_text}"
                )

                # Получаем описание ошибки из словаря кодов ошибок
                error_description = self.ERROR_CODES.get(status_code, "Неизвестная ошибка")
                logger.warning(f"Описание ошибки: {error_description}")

                # Проверяем, нужно ли повторить запрос
                if status_code in self.retry_codes:
                    retries += 1
                    
                    # При ошибке 429 (Too Many Requests) используем экспоненциальную задержку
                    if status_code == 429:
                        retry_after = None
                        try:
                            # Пробуем получить значение Retry-After из заголовков
                            retry_after = int(e.response.headers.get("Retry-After", "0"))
                        except (ValueError, TypeError):
                            retry_after = None
                        
                        # Если нет Retry-After или он некорректный, используем экспоненциальную задержку
                        if not retry_after or retry_after <= 0:
                            retry_delay = min(retry_delay * 2, 30)  # максимальная задержка 30 секунд
                        else:
                            retry_delay = retry_after
                        
                        logger.info(f"Rate limit превышен. Повторная попытка через {retry_delay} сек.")
                    else:
                        # Для других ошибок используем фиксированную задержку с небольшим случайным компонентом
                        retry_delay = 1.0 + retries * 0.5
                    
                    if retries <= self.max_retries:
                        logger.info(f"Повторная попытка {retries}/{self.max_retries} через {retry_delay} сек...")
                        await asyncio.sleep(retry_delay)
                        continue
                
                # Если это не ретраибл ошибка или исчерпаны попытки
                try:
                    error_json = e.response.json()
                    error_message = error_json.get("message", str(e))
                    error_code = error_json.get("code", status_code)
                except Exception:
                    error_message = response_text
                    error_code = status_code
                
                error_data = {
                    "error": True,
                    "code": error_code,
                    "message": error_message,
                    "status": status_code,
                    "description": error_description
                }
                
                # Для некоторых ошибок возвращаем структурированный ответ вместо исключения
                if status_code in [400, 404]:
                    return error_data
                
                last_error = Exception(f"DMarket API error: {error_message} (code: {error_code}, description: {error_description})")
                break

            except (httpx.ConnectError, httpx.ReadError, httpx.WriteError) as e:
                # Сетевые ошибки
                logger.warning(f"Сетевая ошибка при запросе {method} {path}: {e!s}")
                retries += 1
                retry_delay = min(retry_delay * 1.5, 10)  # максимальная задержка 10 секунд
                
                if retries <= self.max_retries:
                    logger.info(f"Повторная попытка {retries}/{self.max_retries} через {retry_delay} сек...")
                    await asyncio.sleep(retry_delay)
                    continue
                
                last_error = e
                break

            except Exception as e:
                # Другие ошибки
                logger.error(f"Непредвиденная ошибка при запросе {method} {path}: {e!s}")
                logger.error(traceback.format_exc())
                last_error = e
                break

        # Если были исчерпаны все попытки
        if last_error:
            error_message = str(last_error)
            return {
                "error": True,
                "message": error_message,
                "code": "REQUEST_FAILED",
            }
        
        # Эта часть кода никогда не должна выполняться, но для безопасности
        return {
            "error": True,
            "message": "Unknown error occurred during API request",
            "code": "UNKNOWN_ERROR",
        }

    async def clear_cache(self) -> None:
        """Очищает весь кэш API."""
        global api_cache
        api_cache = {}
        logger.info("API cache cleared")

    async def clear_cache_for_endpoint(self, endpoint_path: str) -> None:
        """Очищает кэш для конкретного эндпоинта.

        Args:
            endpoint_path: Путь эндпоинта

        """
        global api_cache
        keys_to_remove = []

        for key in api_cache:
            if endpoint_path in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            api_cache.pop(key, None)

        logger.info(f"Cleared {len(keys_to_remove)} cache entries for endpoint {endpoint_path}")

    # Оставляем для обратной совместимости
    async def get_balance(self) -> dict[str, Any]:
        """Улучшенная версия метода получения баланса пользователя DMarket.
        Комбинирует все доступные методы для максимальной совместимости.

        Returns:
            Информация о балансе в формате:
            {
                "usd": {"amount": value_in_cents},
                "has_funds": True/False,
                "balance": value_in_dollars,
                "available_balance": value_in_dollars,
                "total_balance": value_in_dollars,
                "error": True/False,
                "error_message": "Сообщение об ошибке (если есть)"
            }

        """
        logger.debug("Запрос баланса пользователя DMarket через универсальный метод")

        # Проверяем наличие API ключей
        if not self.public_key or not self.secret_key:
            logger.error("Ошибка: API ключи не настроены (пустые значения)")
            return {
                "usd": {"amount": 0},
                "has_funds": False,
                "balance": 0.0,
                "available_balance": 0.0,
                "total_balance": 0.0,
                "error": True,
                "error_message": "API ключи не настроены",
            }

        try:
            # 2024 обновление: сначала пробуем прямой REST API запрос через requests
            # Этот подход может быть более надежен для некоторых эндпоинтов
            try:
                direct_response = await self.direct_balance_request()
                if direct_response and direct_response.get("success", False):
                    logger.info("Успешно получили баланс через прямой REST API запрос")

                    # Извлекаем данные из успешного ответа
                    balance_data = direct_response.get("data", {})
                    usd_amount = balance_data.get("balance", 0) * 100  # конвертируем в центы
                    usd_available = (
                        balance_data.get("available", balance_data.get("balance", 0)) * 100
                    )
                    usd_total = balance_data.get("total", balance_data.get("balance", 0)) * 100

                    # Определяем результат
                    min_required_balance = 1.0  # Минимальный требуемый баланс
                    has_funds = usd_available >= min_required_balance * 100

                    result = {
                        "usd": {"amount": usd_amount},
                        "has_funds": has_funds,
                        "balance": usd_amount / 100,
                        "available_balance": usd_available / 100,
                        "total_balance": usd_total / 100,
                        "error": False,
                        "additional_info": {
                            "method": "direct_request",
                            "raw_response": balance_data,
                        },
                    }

                    logger.info(f"Итоговый баланс (прямой запрос): ${result['balance']:.2f} USD")
                    return result
                # Если прямой запрос не сработал, логируем ошибку и продолжаем с другими методами
                error_message = direct_response.get("error", "Неизвестная ошибка")
                logger.warning(f"Прямой REST API запрос не удался: {error_message}")
            except Exception as e:
                logger.warning(f"Ошибка при прямом REST API запросе: {e!s}")

            # Если прямой запрос не удался, пробуем через внутренний API клиент
            # Пробуем все известные эндпоинты для получения баланса
            endpoints = [
                self.ENDPOINT_BALANCE,  # Актуальный эндпоинт согласно документации
                "/api/v1/account/wallet/balance",  # Альтернативный возможный эндпоинт
                "/exchange/v1/user/balance",  # Возможный эндпоинт биржи
                self.ENDPOINT_BALANCE_LEGACY,  # Старый эндпоинт (для обратной совместимости)
            ]

            response = None
            last_error = None
            successful_endpoint = None

            # Перебираем все эндпоинты, пока не получим корректный ответ
            for endpoint in endpoints:
                try:
                    logger.info(f"Пробуем получить баланс через эндпоинт {endpoint}")
                    response = await self._request(
                        "GET",
                        endpoint,
                    )

                    if (
                        response
                        and isinstance(response, dict)
                        and not ("error" in response or "code" in response)
                    ):
                        logger.info(f"Успешно получили баланс через {endpoint}")
                        successful_endpoint = endpoint
                        break

                except Exception as e:
                    last_error = e
                    logger.warning(f"Ошибка при запросе {endpoint}: {e!s}")
                    continue

            # Если не получили ответ ни от одного эндпоинта
            if not response:
                error_message = (
                    str(last_error)
                    if last_error
                    else "Не удалось получить баланс ни с одного эндпоинта"
                )
                logger.error(f"Критическая ошибка при запросе баланса: {error_message}")
                return {
                    "usd": {"amount": 0},
                    "has_funds": False,
                    "balance": 0.0,
                    "available_balance": 0.0,
                    "total_balance": 0.0,
                    "error": True,
                    "error_message": error_message,
                }

            # Проверяем на ошибки API
            if isinstance(response, dict) and ("error" in response or "code" in response):
                error_code = response.get("code", "unknown")
                error_message = response.get("message", response.get("error", "Неизвестная ошибка"))
                status_code = response.get("status_code", None)

                logger.error(
                    f"Ошибка DMarket API при получении баланса: {error_code} - {error_message} (HTTP {status_code if status_code else 'неизвестный код'})"
                )

                # Если ошибка авторизации (401 Unauthorized)
                if error_code == "Unauthorized" or status_code == 401:
                    logger.error(
                        "Проблема с API ключами. Пожалуйста, проверьте правильность и актуальность ключей DMarket API"
                    )
                    return {
                        "usd": {"amount": 0},
                        "has_funds": False,
                        "balance": 0.0,
                        "available_balance": 0.0,
                        "total_balance": 0.0,
                        "error": True,
                        "error_message": "Ошибка авторизации: неверные ключи API",
                    }

                return {
                    "usd": {"amount": 0},
                    "has_funds": False,
                    "balance": 0.0,
                    "available_balance": 0.0,
                    "total_balance": 0.0,
                    "error": True,
                    "error_message": error_message,
                }

            # Обработка успешного ответа
            usd_amount = 0  # общий баланс в центах
            usd_available = 0  # доступный баланс в центах
            usd_total = 0  # полный баланс в центах
            additional_info = {
                "endpoint": successful_endpoint
            }  # дополнительная информация о балансе

            if response and isinstance(response, dict):
                logger.info(f"Анализ ответа баланса от {successful_endpoint}: {response}")

                # Формат 0: Новый формат (2024) с usdWallet в funds
                if "funds" in response:
                    try:
                        funds = response["funds"]
                        if isinstance(funds, dict) and "usdWallet" in funds:
                            wallet = funds["usdWallet"]
                            if "balance" in wallet:
                                usd_amount = (
                                    float(wallet["balance"]) * 100
                                )  # обычно в долларах, конвертируем в центы
                            if "availableBalance" in wallet:
                                usd_available = float(wallet["availableBalance"]) * 100
                            if "totalBalance" in wallet:
                                usd_total = float(wallet["totalBalance"]) * 100

                            logger.info(f"Баланс из funds.usdWallet: {usd_amount/100:.2f} USD")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Ошибка при обработке поля funds.usdWallet: {e}")

                # Новый формат по документации: balance/available/usd/dmc
                elif "balance" in response and isinstance(response["balance"], (int, float, str)):
                    try:
                        usd_amount = (
                            float(response["balance"]) * 100
                        )  # в долларах, конвертируем в центы
                        # Если есть поле available, используем его для доступного баланса
                        if "available" in response:
                            usd_available = float(response["available"]) * 100
                        else:
                            usd_available = usd_amount

                        # Если есть поле total, используем его для общего баланса
                        if "total" in response:
                            usd_total = float(response["total"]) * 100
                        else:
                            usd_total = usd_amount

                        logger.info(f"Баланс из нового формата: {usd_amount/100:.2f} USD")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Ошибка при обработке баланса нового формата: {e}")

                # Формат 1: DMarket API 2023+ с usdAvailableToWithdraw и usd
                elif "usdAvailableToWithdraw" in response:
                    try:
                        usd_value = response["usdAvailableToWithdraw"]
                        if isinstance(usd_value, str):
                            # Строка может быть в формате "5.00" или "$5.00"
                            usd_available = float(usd_value.replace("$", "").strip()) * 100
                        else:
                            usd_available = float(usd_value) * 100

                        # Также проверяем общий баланс (если есть)
                        if "usd" in response:
                            usd_value = response["usd"]
                            if isinstance(usd_value, str):
                                usd_total = float(usd_value.replace("$", "").strip()) * 100
                            else:
                                usd_total = float(usd_value) * 100
                        else:
                            usd_total = usd_available

                        # Используем доступный баланс как основной
                        usd_amount = usd_available
                        logger.info(f"Баланс из usdAvailableToWithdraw: {usd_amount/100:.2f} USD")

                    except (ValueError, TypeError) as e:
                        logger.error(f"Ошибка при обработке поля usdAvailableToWithdraw: {e}")
                        # Продолжаем проверку других форматов

                # Формат 2: Старый формат DMarket API с полем usd.amount в центах
                elif "usd" in response:
                    try:
                        if isinstance(response["usd"], dict) and "amount" in response["usd"]:
                            # Формат {"usd": {"amount": 1234}}
                            usd_amount = float(response["usd"]["amount"])
                            usd_available = usd_amount
                            usd_total = usd_amount
                            logger.info(f"Баланс из usd.amount: {usd_amount/100:.2f} USD")
                        elif isinstance(response["usd"], (int, float)):
                            # Формат {"usd": 1234}
                            usd_amount = float(response["usd"])
                            usd_available = usd_amount
                            usd_total = usd_amount
                            logger.info(
                                f"Баланс из usd (прямое значение): {usd_amount/100:.2f} USD"
                            )
                        elif isinstance(response["usd"], str):
                            # Формат {"usd": "$12.34"}
                            usd_amount = float(response["usd"].replace("$", "").strip()) * 100
                            usd_available = usd_amount
                            usd_total = usd_amount
                            logger.info(
                                f"Баланс из usd (строковое значение): {usd_amount/100:.2f} USD"
                            )
                    except (ValueError, TypeError) as e:
                        logger.error(f"Ошибка при обработке поля usd: {e}")

                # Формат 3: Формат с totalBalance как списком валют
                elif "totalBalance" in response and isinstance(response["totalBalance"], list):
                    for currency in response["totalBalance"]:
                        if isinstance(currency, dict) and currency.get("currency") == "USD":
                            usd_amount = float(currency.get("amount", 0))
                            usd_total = usd_amount
                            # Если есть доступный баланс
                            if "availableAmount" in currency:
                                usd_available = float(currency.get("availableAmount", 0))
                            else:
                                usd_available = usd_amount

                            logger.info(f"Баланс из totalBalance: {usd_amount/100:.2f} USD")
                            break

                # Формат 4: Формат с balance как объектом с валютами
                elif "balance" in response and isinstance(response["balance"], dict):
                    if "usd" in response["balance"]:
                        usd_value = response["balance"]["usd"]
                        if isinstance(usd_value, (int, float)):
                            usd_amount = float(usd_value)
                        elif isinstance(usd_value, str):
                            usd_amount = float(usd_value.replace("$", "").strip()) * 100
                        elif isinstance(usd_value, dict) and "amount" in usd_value:
                            usd_amount = float(usd_value["amount"])

                        usd_available = usd_amount
                        usd_total = usd_amount
                        logger.info(f"Баланс из balance.usd: {usd_amount/100:.2f} USD")

                # Собираем дополнительную информацию для анализа
                for field in ["dmc", "dmcAvailableToWithdraw", "userData"]:
                    if field in response:
                        additional_info[field] = response[field]

                # Если не смогли найти баланс в известных форматах
                if usd_amount == 0 and usd_available == 0 and usd_total == 0:
                    logger.warning(
                        f"Не удалось разобрать данные о балансе из известных форматов: {response}"
                    )
                    # В качестве отладки сохраняем весь ответ API
                    additional_info["raw_response"] = response

            # Определяем результат
            min_required_balance = 1.0  # Минимальный требуемый баланс
            has_funds = (
                usd_available >= min_required_balance * 100
            )  # Проверяем, достаточно ли доступных средств

            # Если доступный баланс не определен, но есть общий баланс
            if usd_available == 0 and usd_amount > 0:
                usd_available = usd_amount

            # Если полный баланс не определен, используем максимум из доступного и общего
            if usd_total == 0:
                usd_total = max(usd_amount, usd_available)

            # Формируем результат
            result = {
                "usd": {"amount": usd_amount},
                "has_funds": has_funds,
                "balance": usd_amount / 100,  # Общий баланс в долларах
                "available_balance": usd_available / 100,  # Доступный баланс в долларах
                "total_balance": usd_total / 100,  # Полный баланс в долларах
                "error": False,
                "additional_info": additional_info,  # Сохраняем дополнительную информацию для отладки
            }

            logger.info(
                f"Итоговый баланс: ${result['balance']:.2f} USD (доступно: ${result['available_balance']:.2f}, всего: ${result['total_balance']:.2f})"
            )
            return result

        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении баланса: {e!s}")
            logger.error(f"Стек вызовов: {traceback.format_exc()}")
            return {
                "usd": {"amount": 0},
                "has_funds": False,
                "balance": 0.0,
                "available_balance": 0.0,
                "total_balance": 0.0,
                "error": True,
                "error_message": str(e),
            }

    async def get_user_balance(self) -> dict[str, Any]:
        """Получение баланса пользователя (устаревший метод).
        
        Этот метод оставлен для обратной совместимости.
        Рекомендуется использовать get_balance() вместо него.
        
        Returns:
            dict: Информация о балансе пользователя в том же формате, что и get_balance()
        """
        logger.warning(
            "Метод get_user_balance() устарел и может быть удален в будущих версиях. "
            "Пожалуйста, используйте get_balance() вместо него."
        )
        return await self.get_balance()

    async def get_market_items(
        self,
        game: str = "csgo",
        limit: int = 100,
        offset: int = 0,
        currency: str = "USD",
        price_from: float | None = None,
        price_to: float | None = None,
        title: str | None = None,
        sort: str = "price",
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Get items from the marketplace.

        Args:
            game: Game name (csgo, dota2, tf2, rust etc)
            limit: Number of items to retrieve
            offset: Offset for pagination
            currency: Price currency (USD, EUR etc)
            price_from: Minimum price filter
            price_to: Maximum price filter
            title: Filter by item title
            sort: Sort options (price, price_desc, date, popularity)
            force_refresh: Force refresh cache

        Returns:
            Items as dict

        """
        # Build query parameters according to docs
        params = {
            "gameId": game,
            "limit": limit,
            "offset": offset,
            "currency": currency,
        }

        if price_from is not None:
            params["priceFrom"] = str(int(price_from * 100))  # Price in cents

        if price_to is not None:
            params["priceTo"] = str(int(price_to * 100))  # Price in cents

        if title:
            params["title"] = title

        if sort:
            params["orderBy"] = sort

        # Use correct endpoint from DMarket API docs
        return await self._request(
            "GET",
            self.ENDPOINT_MARKET_ITEMS,
            params=params,
            force_refresh=force_refresh,
        )

    async def get_all_market_items(
        self,
        game: str = "csgo",
        max_items: int = 1000,
        currency: str = "USD",
        price_from: float | None = None,
        price_to: float | None = None,
        title: str | None = None,
        sort: str = "price",
    ) -> list[dict[str, Any]]:
        """Get all items from the marketplace using pagination.

        Args:
            game: Game name (csgo, dota2, tf2, rust etc)
            max_items: Maximum number of items to retrieve
            currency: Price currency (USD, EUR etc)
            price_from: Minimum price filter
            price_to: Maximum price filter
            title: Filter by item title
            sort: Sort options (price, price_desc, date, popularity)

        Returns:
            List of all items as dict

        """
        all_items = []
        limit = 100  # Maximum limit per request
        offset = 0
        total_fetched = 0

        while total_fetched < max_items:
            response = await self.get_market_items(
                game=game,
                limit=limit,
                offset=offset,
                currency=currency,
                price_from=price_from,
                price_to=price_to,
                title=title,
                sort=sort,
            )

            items = response.get("items", [])
            if not items:
                break

            all_items.extend(items)
            total_fetched += len(items)
            offset += limit

            # If we received less than limit items, there are no more items
            if len(items) < limit:
                break

        return all_items[:max_items]

    async def buy_item(
        self,
        item_id: str,
        price: float,
        game: str = "csgo",
    ) -> dict[str, Any]:
        """Покупает предмет с указанным ID и ценой.

        Args:
            item_id: ID предмета для покупки
            price: Цена в USD (будет конвертирована в центы)
            game: Код игры (csgo, dota2, tf2, rust)

        Returns:
            Результат операции покупки

        """
        # Конвертируем цену из USD в центы
        price_cents = int(price * 100)

        # Формируем данные запроса согласно документации API
        data = {
            "itemId": item_id,
            "price": {
                "amount": price_cents,
                "currency": "USD"
            },
            "gameType": game
        }

        # Выполняем запрос на покупку
        result = await self._request(
            "POST", 
            self.ENDPOINT_PURCHASE,
            data=data
        )

        # Очищаем кэш для инвентаря, т.к. он изменился
        await self.clear_cache_for_endpoint(self.ENDPOINT_USER_INVENTORY)
        
        # Очищаем кэш для баланса, т.к. он также изменился
        await self.clear_cache_for_endpoint(self.ENDPOINT_BALANCE)
        await self.clear_cache_for_endpoint(self.ENDPOINT_BALANCE_LEGACY)

        return result

    async def sell_item(
        self,
        item_id: str,
        price: float,
        game: str = "csgo",
    ) -> dict[str, Any]:
        """Выставляет предмет на продажу.

        Args:
            item_id: ID предмета для продажи
            price: Цена в USD (будет конвертирована в центы)
            game: Код игры (csgo, dota2, tf2, rust)

        Returns:
            Результат операции продажи

        """
        # Конвертируем цену из USD в центы
        price_cents = int(price * 100)

        # Формируем данные запроса согласно документации API
        data = {
            "itemId": item_id,
            "price": {
                "amount": price_cents,
                "currency": "USD"
            }
        }

        # Выполняем запрос на продажу
        result = await self._request(
            "POST", 
            self.ENDPOINT_SELL,
            data=data
        )

        # Очищаем кэш для инвентаря и списка предложений, т.к. они изменились
        await self.clear_cache_for_endpoint(self.ENDPOINT_USER_INVENTORY)
        await self.clear_cache_for_endpoint(self.ENDPOINT_USER_OFFERS)

        return result

    async def get_user_inventory(
        self,
        game: str = "csgo",
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get user inventory items.

        Args:
            game: Game name (csgo, dota2, tf2, rust etc)
            limit: Number of items to retrieve
            offset: Offset for pagination

        Returns:
            User inventory items as dict

        """
        params = {
            "gameId": game,
            "limit": limit,
            "offset": offset,
        }
        return await self._request(
            "GET",
            self.ENDPOINT_USER_INVENTORY,
            params=params,
        )

    async def get_suggested_price(
        self,
        item_name: str,
        game: str = "csgo",
    ) -> float | None:
        """Get suggested price for an item.

        Args:
            item_name: Item name
            game: Game name

        Returns:
            Suggested price as float or None if not found

        """
        # Find the item
        response = await self.get_market_items(
            game=game,
            title=item_name,
            limit=1,
        )

        items = response.get("items", [])
        if not items:
            return None

        item = items[0]
        suggested_price = item.get("suggestedPrice")

        if suggested_price:
            try:
                # Convert from cents to dollars
                return float(suggested_price) / 100
            except (ValueError, TypeError):
                try:
                    # Sometimes the API returns an object with amount and currency
                    amount = suggested_price.get("amount", 0)
                    return float(amount) / 100
                except (AttributeError, ValueError, TypeError):
                    return None

        return None

    # Новые методы для работы с DMarket API

    async def get_account_details(self) -> dict[str, Any]:
        """Получает детали аккаунта пользователя.

        Returns:
            Dict[str, Any]: Информация об аккаунте

        """
        return await self._request(
            "GET",
            self.ENDPOINT_ACCOUNT_DETAILS,
        )

    async def get_market_best_offers(
        self,
        game: str = "csgo",
        title: str | None = None,
        limit: int = 50,
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Получает лучшие предложения на маркете.

        Args:
            game: Идентификатор игры
            title: Название предмета (опционально)
            limit: Лимит результатов
            currency: Валюта цен

        Returns:
            Dict[str, Any]: Лучшие предложения

        """
        params = {
            "gameId": game,
            "limit": limit,
            "currency": currency,
        }

        if title:
            params["title"] = title

        return await self._request(
            "GET",
            self.ENDPOINT_MARKET_BEST_OFFERS,
            params=params,
        )

    async def get_market_aggregated_prices(
        self,
        game: str = "csgo",
        title: str | None = None,
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Получает агрегированные цены на предметы.

        Args:
            game: Идентификатор игры
            title: Название предмета (опционально)
            currency: Валюта цен

        Returns:
            Dict[str, Any]: Агрегированные цены

        """
        params = {
            "gameId": game,
            "currency": currency,
        }

        if title:
            params["title"] = title

        return await self._request(
            "GET",
            self.ENDPOINT_MARKET_PRICE_AGGREGATED,
            params=params,
        )

    async def get_sales_history(
        self,
        game: str,
        title: str,
        days: int = 7,
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Получает историю продаж предмета.

        Args:
            game: Идентификатор игры
            title: Название предмета
            days: Количество дней истории
            currency: Валюта цен

        Returns:
            Dict[str, Any]: История продаж

        """
        params = {
            "gameId": game,
            "title": title,
            "days": days,
            "currency": currency,
        }

        return await self._request(
            "GET",
            self.ENDPOINT_SALES_HISTORY,
            params=params,
        )

    async def get_item_price_history(
        self,
        game: str,
        title: str,
        period: str = "last_month",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Получает историю цен предмета.

        Args:
            game: Идентификатор игры
            title: Название предмета
            period: Период ("last_day", "last_week", "last_month", "last_year")
            currency: Валюта цен

        Returns:
            Dict[str, Any]: История цен

        """
        params = {
            "gameId": game,
            "title": title,
            "period": period,
            "currency": currency,
        }

        return await self._request(
            "GET",
            self.ENDPOINT_ITEM_PRICE_HISTORY,
            params=params,
        )

    async def get_market_meta(
        self,
        game: str = "csgo",
    ) -> dict[str, Any]:
        """Получает метаданные маркета для указанной игры.

        Args:
            game: Идентификатор игры

        Returns:
            Dict[str, Any]: Метаданные маркета

        """
        params = {
            "gameId": game,
        }

        return await self._request(
            "GET",
            self.ENDPOINT_MARKET_META,
            params=params,
        )

    async def edit_offer(
        self,
        offer_id: str,
        price: float,
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Редактирует существующее предложение.

        Args:
            offer_id: ID предложения
            price: Новая цена
            currency: Валюта цены

        Returns:
            Dict[str, Any]: Результат редактирования

        """
        data = {
            "offerId": offer_id,
            "price": {
                "amount": int(price * 100),  # В центах
                "currency": currency,
            },
        }

        return await self._request(
            "POST",
            self.ENDPOINT_OFFER_EDIT,
            data=data,
        )

    async def delete_offer(
        self,
        offer_id: str,
    ) -> dict[str, Any]:
        """Удаляет предложение.

        Args:
            offer_id: ID предложения

        Returns:
            Dict[str, Any]: Результат удаления

        """
        data = {
            "offers": [offer_id],
        }

        return await self._request(
            "DELETE",
            self.ENDPOINT_OFFER_DELETE,
            data=data,
        )

    async def get_active_offers(
        self,
        game: str = "csgo",
        limit: int = 50,
        offset: int = 0,
        status: str = "active",
    ) -> dict[str, Any]:
        """Получает активные предложения пользователя.

        Args:
            game: Идентификатор игры
            limit: Лимит результатов
            offset: Смещение для пагинации
            status: Статус предложений ("active", "completed", "canceled")

        Returns:
            Dict[str, Any]: Активные предложения

        """
        params = {
            "gameId": game,
            "limit": limit,
            "offset": offset,
            "status": status,
        }

        return await self._request(
            "GET",
            self.ENDPOINT_ACCOUNT_OFFERS,
            params=params,
        )

    async def direct_balance_request(self) -> dict[str, Any]:
        """Выполняет прямой запрос баланса через REST API.
        
        Этот метод используется как альтернативный способ получения баланса
        в случае проблем с основным методом.
        
        Returns:
            dict: Результат запроса баланса или словарь с ошибкой
        """
        try:
            # Актуальный эндпоинт баланса (2024) согласно документации DMarket
            endpoint = self.ENDPOINT_BALANCE
            base_url = self.api_url
            full_url = f"{base_url}{endpoint}"

            # Формируем timestamp для запроса
            timestamp = str(int(datetime.now().timestamp()))
            string_to_sign = f"GET{endpoint}{timestamp}"

            # Создаем HMAC подпись
            signature = hmac.new(
                self.secret_key,
                string_to_sign.encode(),
                hashlib.sha256,
            ).hexdigest()

            # Формируем заголовки запроса согласно последней документации DMarket
            headers = {
                "X-Api-Key": self.public_key,
                "X-Sign-Date": timestamp,
                "X-Request-Sign": f"dmar ed25519 {signature}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            logger.debug(f"Выполняем прямой запрос к {endpoint}")

            # Выполняем запрос
            response = requests.get(full_url, headers=headers, timeout=10)

            # Если запрос успешен (HTTP 200)
            if response.status_code == 200:
                try:
                    # Парсим JSON ответ
                    response_data = response.json()

                    # Проверяем структуру ответа согласно документации DMarket
                    if response_data:
                        logger.info(f"Успешный прямой запрос к {endpoint}")

                        # Извлекаем значения баланса из ответа
                        balance = response_data.get("balance", 0)
                        available = response_data.get("available", balance)
                        total = response_data.get("total", balance)

                        return {
                            "success": True,
                            "data": {
                                "balance": float(balance),
                                "available": float(available),
                                "total": float(total),
                            },
                        }
                except json.JSONDecodeError:
                    logger.warning(f"Ошибка декодирования JSON при прямом запросе: {response.text}")

            # Если статус 401, значит проблема с авторизацией
            if response.status_code == 401:
                logger.error("Ошибка авторизации (401) при прямом запросе баланса")
                return {
                    "success": False,
                    "status_code": 401,
                    "error": "Ошибка авторизации: неверные ключи API",
                }

            # Для всех остальных ошибок
            logger.warning(
                f"Ошибка при прямом запросе: HTTP {response.status_code} - {response.text}"
            )
            return {
                "success": False,
                "status_code": response.status_code,
                "error": f"Ошибка HTTP {response.status_code}: {response.text}",
            }

        except Exception as e:
            logger.error(f"Исключение при прямом запросе баланса: {e!s}")
            return {
                "success": False,
                "error": str(e),
            }
