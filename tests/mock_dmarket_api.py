"""Модуль с мок-объектом DMarketAPI для тестирования.
"""

from typing import Any


class DMarketAPI:
    """Мок-класс DMarketAPI для тестирования."""

    def __init__(
        self,
        public_key: str,
        secret_key: str,
        api_url: str = "https://api.dmarket.com",
        max_retries: int = 3,
    ):
        """Инициализирует мок-объект DMarketAPI.

        Args:
            public_key: Публичный ключ DMarket API
            secret_key: Секретный ключ DMarket API
            api_url: URL API
            max_retries: Максимальное количество повторных попыток

        """
        self.public_key = public_key
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self.api_url = api_url
        self.max_retries = max_retries

    async def get_user_balance(self) -> dict[str, Any]:
        """Возвращает мок-баланс пользователя.

        Returns:
            Dict[str, Any]: Информация о балансе

        """
        return {
            "usd": {"amount": 10000},  # $100 в центах
            "has_funds": True,
            "balance": 100.0,
            "available_balance": 95.0,
            "total_balance": 105.0,
            "error": False,
        }

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
        """Возвращает мок-список предметов на рынке.

        Args:
            game: Игра
            limit: Лимит предметов
            offset: Смещение
            currency: Валюта
            price_from: Минимальная цена
            price_to: Максимальная цена
            title: Название предмета
            sort: Сортировка
            force_refresh: Принудительное обновление

        Returns:
            Dict[str, Any]: Предметы на рынке

        """
        items = [
            {
                "itemId": "item1",
                "title": "AK-47 | Redline (Field-Tested)",
                "price": {"amount": 2000, "currency": "USD"},  # $20 в центах
                "suggestedPrice": 1800,  # $18 в центах
                "game": game,
            },
            {
                "itemId": "item2",
                "title": "AWP | Asiimov (Field-Tested)",
                "price": {"amount": 7500, "currency": "USD"},  # $75 в центах
                "suggestedPrice": 7000,  # $70 в центах
                "game": game,
            },
        ]

        # Фильтрация по цене если указана
        if price_from is not None:
            price_from_cents = int(price_from * 100)
            items = [item for item in items if item["price"]["amount"] >= price_from_cents]

        if price_to is not None:
            price_to_cents = int(price_to * 100)
            items = [item for item in items if item["price"]["amount"] <= price_to_cents]

        # Фильтрация по названию если указано
        if title:
            items = [item for item in items if title.lower() in item["title"].lower()]

        # Применение лимита и смещения
        paginated_items = items[offset : offset + limit]

        return {
            "objects": paginated_items,
            "total": len(items),
            "cursor": str(offset + len(paginated_items)),
        }

    async def get_user_inventory(
        self,
        game: str = "csgo",
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Возвращает мок-инвентарь пользователя.

        Args:
            game: Игра
            limit: Лимит предметов
            offset: Смещение

        Returns:
            Dict[str, Any]: Инвентарь пользователя

        """
        items = [
            {
                "itemId": "item3",
                "title": "Glock-18 | Water Elemental (Minimal Wear)",
                "price": {"amount": 500, "currency": "USD"},  # $5 в центах
                "game": game,
            },
            {
                "itemId": "item4",
                "title": "M4A4 | Desolate Space (Field-Tested)",
                "price": {"amount": 1500, "currency": "USD"},  # $15 в центах
                "game": game,
            },
        ]

        # Применение лимита и смещения
        paginated_items = items[offset : offset + limit]

        return {
            "objects": paginated_items,
            "total": len(items),
            "cursor": str(offset + len(paginated_items)),
        }

    async def _close_client(self):
        """Закрывает клиент (заглушка)."""
