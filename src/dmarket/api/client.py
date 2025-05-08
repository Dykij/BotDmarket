"""Клиент API для работы с DMarket.

Этот модуль предоставляет класс для взаимодействия с API DMarket,
включая методы для получения предметов, баланса, истории продаж и т.д.
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import requests

from ..models.market_models import Balance, MarketItem, SalesHistory

logger = logging.getLogger(__name__)


class DMarketAPI:
    """Клиент API для работы с DMarket."""

    def __init__(
        self,
        public_key: str,
        secret_key: str,
        api_url: str = "https://api.dmarket.com",
        rate_limit: int = 10,
    ) -> None:
        """Инициализирует клиент API для DMarket.

        Args:
            public_key: Публичный ключ для доступа к API.
            secret_key: Секретный ключ для доступа к API.
            api_url: URL API DMarket.
            rate_limit: Ограничение на количество запросов в секунду.

        """
        self.public_key = public_key
        self.secret_key = secret_key.encode("utf-8")
        self.api_url = api_url
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self._balance_cache = None
        self._balance_cache_time = 0
        self._balance_cache_expiry = 60  # 60 секунд

    def _apply_rate_limiting(self) -> None:
        """Применяет ограничение скорости запросов.

        Гарантирует, что запросы не отправляются слишком часто,
        чтобы избежать ограничений со стороны API.
        """
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        if elapsed < 1 / self.rate_limit:
            sleep_time = (1 / self.rate_limit) - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _sign_request(self, method: str, path: str, body: str = "") -> dict[str, str]:
        """Подписывает запрос к API.

        Args:
            method: Метод запроса (GET, POST и т.д.).
            path: Путь запроса.
            body: Тело запроса (для POST-запросов).

        Returns:
            Словарь с заголовками для запроса.

        """
        timestamp = str(int(time.time()))
        string_to_sign = f"{method.upper()}{path}{timestamp}{body}"
        signature = hmac.new(
            self.secret_key,
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return {
            "X-Api-Key": self.public_key,
            "X-Request-Sign": signature,
            "X-Sign-Date": timestamp,
            "Content-Type": "application/json",
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        skip_rate_limiting: bool = False,
    ) -> dict[str, Any]:
        """Выполняет запрос к API.

        Args:
            method: Метод запроса (GET, POST и т.д.).
            endpoint: Конечная точка API.
            params: Параметры запроса для GET-запросов.
            data: Данные для POST-запросов.
            skip_rate_limiting: Если True, пропускает ограничение скорости запросов.

        Returns:
            Ответ API в виде словаря.

        Raises:
            requests.exceptions.HTTPError: Если запрос вернул ошибку.

        """
        if not skip_rate_limiting:
            self._apply_rate_limiting()

        url = f"{self.api_url}{endpoint}"
        body = json.dumps(data) if data else ""
        headers = self._sign_request(method, endpoint, body)

        logger.debug(f"Making {method} request to {url}")

        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                json=data,
            )
            response.raise_for_status()

            logger.debug(f"Response status code: {response.status_code}")

            if response.content:
                return response.json()
            return {}

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            if response.content:
                error_info = response.json()
                logger.error(f"Error details: {error_info}")
            raise

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def get_balance(self, force_refresh: bool = False) -> Balance:
        """Получает баланс пользователя.

        Args:
            force_refresh: Если True, игнорирует кэшированный баланс и запрашивает новый.

        Returns:
            Объект Balance с информацией о балансе.

        """
        current_time = time.time()

        # Проверяем, нужно ли использовать кэшированный баланс
        if (
            not force_refresh
            and self._balance_cache
            and (current_time - self._balance_cache_time) < self._balance_cache_expiry
        ):
            logger.debug("Using cached balance")
            return self._balance_cache

        response = self._make_request("GET", "/account/v1/balance")

        if "usd" in response:
            balance_data = {
                "totalBalance": response["usd"].get("value", 0),
                "blockedBalance": response["usd"].get("blockedValue", 0),
            }

            balance = Balance.from_dict(balance_data)

            # Обновляем кэш
            self._balance_cache = balance
            self._balance_cache_time = current_time

            return balance

        logger.warning("Balance response does not contain 'usd' field")
        return Balance(totalBalance=0.0, blockedBalance=0.0)

    def get_items(
        self,
        game: str = "csgo",
        limit: int = 100,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> list[MarketItem]:
        """Получает список предметов с маркетплейса.

        Args:
            game: ID игры (csgo, dota2 и т.д.).
            limit: Максимальное количество предметов.
            offset: Смещение для пагинации.
            filters: Словарь с фильтрами.

        Returns:
            Список объектов MarketItem.

        """
        params = {
            "gameId": game,
            "limit": limit,
            "offset": offset,
        }

        if filters:
            # Преобразуем фильтры в формат, понятный API
            for key, value in filters.items():
                params[key] = value

        response = self._make_request("GET", "/marketplace-api/v1/items", params=params)

        items = []
        if "objects" in response:
            for item_data in response["objects"]:
                items.append(MarketItem.from_dict(item_data))

        return items

    def get_sales_history(
        self,
        item_id: str,
        limit: int = 100,
    ) -> list[SalesHistory]:
        """Получает историю продаж предмета.

        Args:
            item_id: ID предмета.
            limit: Максимальное количество записей.

        Returns:
            Список объектов SalesHistory.

        """
        params = {
            "itemId": item_id,
            "limit": limit,
        }

        response = self._make_request("GET", "/marketplace-api/v1/item-history", params=params)

        sales = []
        if "history" in response:
            for sale_data in response["history"]:
                sales.append(SalesHistory.from_dict(sale_data))

        return sales
