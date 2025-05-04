"""
Пример использования новой системы логирования и обработки ошибок.
Этот модуль демонстрирует, как правильно применять разработанные механизмы
логирования с контекстом и обработки исключений.
"""

import asyncio
from typing import Dict, Any, List, Optional
from src.utils.logging_utils import get_logger, log_exceptions
from src.utils.exception_handling import (
    handle_exceptions, APIError, ValidationError, BusinessLogicError, ErrorCode
)

# Получаем логгер с контекстом компонента
logger = get_logger("examples.error_handling", {"component": "demo"})


class DemoAPIClient:
    """Пример клиента API с использованием новой системы обработки ошибок."""

    def __init__(self, api_key: str, base_url: str):
        """
        Инициализирует клиент API.

        Args:
            api_key: Ключ API для авторизации.
            base_url: Базовый URL для запросов.
        """
        self.api_key = api_key
        self.base_url = base_url
        # Логгер с контекстом клиента
        self.logger = get_logger("examples.api_client", {
            "component": "api_client",
            "base_url": base_url
        })

    @handle_exceptions(default_error_message="Ошибка при выполнении API запроса")
    async def make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполняет запрос к API.

        Args:
            endpoint: Конечная точка API.
            params: Параметры запроса.

        Returns:
            Результат запроса в виде словаря.

        Raises:
            APIError: Если произошла ошибка при выполнении запроса.
        """
        # Логируем начало запроса с контекстом
        self.logger.info(
            f"Выполняется запрос к {endpoint}",
            extra={"context": {"endpoint": endpoint, "params": params}}
        )

        # Имитируем запрос
        await asyncio.sleep(0.5)

        # Имитируем некоторые ошибки для демонстрации
        if "error" in params:
            error_type = params["error"]
            if error_type == "api":
                self.logger.warning("API вернул ошибку",
                                  extra={"context": {"status_code": 429}})
                raise APIError(
                    message="Rate limit exceeded",
                    status_code=429,
                    details={"retry_after": 30}
                )
            elif error_type == "validation":
                raise ValidationError(
                    message="Invalid parameter",
                    field="price",
                    details={"value": params.get("price"), "valid_range": [0, 1000]}
                )

        # Логируем успешное выполнение
        self.logger.info(
            f"Запрос к {endpoint} выполнен успешно",
            extra={"context": {"endpoint": endpoint}}
        )

        return {"status": "success", "data": {"items": [1, 2, 3]}}


class DemoArbitrageService:
    """Пример сервиса арбитража с использованием новой системы обработки ошибок."""

    def __init__(self, api_client: DemoAPIClient):
        """
        Инициализирует сервис арбитража.

        Args:
            api_client: Клиент API для работы с внешним API.
        """
        self.api_client = api_client
        # Логгер с контекстом сервиса
        self.logger = get_logger("examples.arbitrage", {
            "component": "arbitrage_service"
        })

    @handle_exceptions(default_error_message="Ошибка при поиске арбитража")
    async def find_arbitrage_opportunities(
        self, game: str, min_profit: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Ищет арбитражные возможности.

        Args:
            game: Игра для поиска арбитража.
            min_profit: Минимальная прибыль (в процентах).

        Returns:
            Список арбитражных возможностей.

        Raises:
            BusinessLogicError: Если произошла ошибка бизнес-логики.
            ValidationError: Если параметры некорректны.
        """
        # Проверка параметров
        if min_profit < 0:
            raise ValidationError(
                message="Минимальная прибыль не может быть отрицательной",
                field="min_profit"
            )

        # Логируем начало поиска
        self.logger.info(
            f"Начат поиск арбитража для {game}",
            extra={"context": {"game": game, "min_profit": min_profit}}
        )

        try:
            # Запрашиваем данные через API клиент
            params = {"game": game, "sort": "price", "limit": 100}
            items = await self.api_client.make_request("/items", params)

            # Логика поиска арбитража (упрощенно)
            opportunities = self._calculate_opportunities(items, min_profit)

            # Логируем результат
            self.logger.info(
                f"Найдено {len(opportunities)} арбитражных возможностей",
                extra={"context": {"game": game, "count": len(opportunities)}}
            )

            return opportunities
        except APIError as e:
            # Преобразуем ошибку API в ошибку бизнес-логики
            raise BusinessLogicError(
                message=f"Не удалось получить данные для арбитража: {e.message}",
                operation="find_arbitrage",
                details={"original_error": e.to_dict()}
            ) from e

    def _calculate_opportunities(
        self, items_data: Dict[str, Any], min_profit: float
    ) -> List[Dict[str, Any]]:
        """
        Вычисляет арбитражные возможности из данных предметов.

        Args:
            items_data: Данные предметов из API.
            min_profit: Минимальная прибыль.

        Returns:
            Список арбитражных возможностей.
        """
        # Упрощенная логика расчета арбитража
        opportunities = []
        for item in items_data.get("data", {}).get("items", []):
            # В реальном коде здесь была бы настоящая логика
            opportunities.append({
                "name": f"Item {item}",
                "profit": 10.0,
                "price": 100
            })

        return opportunities


@log_exceptions
async def demo_main():
    """Демонстрирует использование системы логирования и обработки ошибок."""
    logger.info("Запуск демонстрации системы логирования и обработки ошибок")

    # Создаем клиент API
    api_client = DemoAPIClient("demo_key", "https://api.example.com")

    # Создаем сервис арбитража
    arbitrage_service = DemoArbitrageService(api_client)

    try:
        # Демонстрируем успешный сценарий
        logger.info("Демонстрация успешного сценария")
        opportunities = await arbitrage_service.find_arbitrage_opportunities("cs", 5.0)
        logger.info(f"Найдено {len(opportunities)} арбитражных возможностей")

        # Демонстрируем обработку ошибки валидации
        logger.info("Демонстрация ошибки валидации")
        try:
            await arbitrage_service.find_arbitrage_opportunities("dota", -1.0)
        except ValidationError as e:
            logger.warning(f"Перехвачена ошибка валидации: {e.message}")

        # Демонстрируем обработку ошибки API
        logger.info("Демонстрация ошибки API")
        try:
            await api_client.make_request("/test", {"error": "api"})
        except APIError as e:
            logger.warning(f"Перехвачена ошибка API: {e.message}")

    except Exception as e:
        logger.error(f"Неожиданная ошибка в демонстрации: {e}")

    logger.info("Демонстрация завершена")


if __name__ == "__main__":
    # Настройка и запуск демонстрации
    asyncio.run(demo_main())
