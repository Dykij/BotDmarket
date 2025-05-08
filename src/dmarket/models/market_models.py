"""Модели данных для работы с DMarket API.

Этот модуль содержит классы для работы с данными DMarket API,
включая модели для предметов, цен, продаж и других сущностей.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypedDict


class MarketPrice(TypedDict):
    """Модель цены на предмет."""

    USD: str
    EUR: str | None


@dataclass
class MarketItem:
    """Модель предмета на маркете."""

    itemId: str
    title: str
    price: MarketPrice
    classId: str
    gameId: str
    inMarket: bool
    lockStatus: bool | None = None
    createdAt: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarketItem":
        """Создает объект MarketItem из словаря.

        Args:
            data: Словарь с данными предмета.

        Returns:
            Объект MarketItem.

        """
        # Преобразуем timestamp в datetime, если он есть
        created_at = data.get("createdAt")
        if created_at and isinstance(created_at, (int, float)):
            created_at = datetime.fromtimestamp(created_at / 1000)

        return cls(
            itemId=data.get("itemId", ""),
            title=data.get("title", ""),
            price=data.get("price", {"USD": "0.0"}),
            classId=data.get("classId", ""),
            gameId=data.get("gameId", ""),
            inMarket=data.get("inMarket", False),
            lockStatus=data.get("lockStatus"),
            createdAt=created_at,
        )


@dataclass
class Balance:
    """Модель баланса пользователя."""

    totalBalance: float
    blockedBalance: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Balance":
        """Создает объект Balance из словаря.

        Args:
            data: Словарь с данными баланса.

        Returns:
            Объект Balance.

        """
        return cls(
            totalBalance=float(data.get("totalBalance", 0.0)),
            blockedBalance=float(data.get("blockedBalance", 0.0)),
        )


@dataclass
class SalesHistory:
    """Модель истории продаж предмета."""

    itemId: str
    timestamp: datetime
    price: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SalesHistory":
        """Создает объект SalesHistory из словаря.

        Args:
            data: Словарь с данными истории продаж.

        Returns:
            Объект SalesHistory.

        """
        timestamp = datetime.fromtimestamp(data.get("date", 0) / 1000)
        return cls(
            itemId=data.get("itemId", ""),
            timestamp=timestamp,
            price=float(data.get("price", {}).get("USD", 0.0)),
        )
