"""
Тесты для модуля rate_limiter.
"""

import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock

# Необходимо для тестирования асинхронных функций
pytest_asyncio = pytest.importorskip("pytest_asyncio")

from src.utils.rate_limiter import RateLimiter, DEFAULT_API_RATE_LIMITS


def test_init() -> None:
    """Тест инициализации RateLimiter с значениями по умолчанию."""
    limiter = RateLimiter()
    assert limiter.is_authorized is True
    assert isinstance(limiter.default_limits, dict)
    assert limiter.last_request_times == {}
    assert limiter.reset_times == {}
    assert limiter.request_counters == {}


def test_get_endpoint_type() -> None:
    """Тест определения типа эндпоинта на основе пути."""
    limiter = RateLimiter()

    # Тест для рыночных эндпоинтов
    assert limiter.get_endpoint_type("/marketplace-api/items") == "market"
    assert limiter.get_endpoint_type("/items/123456") == "market"
    assert limiter.get_endpoint_type("/market/listings") == "market"

    # Тест для торговых эндпоинтов
    assert limiter.get_endpoint_type("/exchange/offers") == "trade"
    assert limiter.get_endpoint_type("/offers/create") == "trade"

    # Учитываем, что "/buy/items" классифицируется как "market"
    assert limiter.get_endpoint_type("/buy/items") == "market"

    # Тест для пользовательских эндпоинтов
    assert limiter.get_endpoint_type("/account/profile") == "user"
    assert limiter.get_endpoint_type("/user/settings") == "user"
    assert limiter.get_endpoint_type("/balance/history") == "user"

    # Тест для прочих эндпоинтов
    assert limiter.get_endpoint_type("/api/status") == "other"
    assert limiter.get_endpoint_type("/unknown/endpoint") == "other"


def test_get_rate_limit() -> None:
    """Тест получения лимита запросов для эндпоинта."""
    limiter = RateLimiter()

    # Проверяем стандартные лимиты
    assert limiter.get_rate_limit("market") == DEFAULT_API_RATE_LIMITS["market"]
    assert limiter.get_rate_limit("trade") == DEFAULT_API_RATE_LIMITS["trade"]
    assert limiter.get_rate_limit("user") == DEFAULT_API_RATE_LIMITS["user"]
    assert limiter.get_rate_limit("other") == DEFAULT_API_RATE_LIMITS["other"]

    # Проверяем пользовательский лимит
    limiter.custom_limits["market"] = 20
    assert limiter.get_rate_limit("market") == 20


@pytest.mark.asyncio
@patch("time.time")
async def test_update_after_call(mock_time) -> None:
    """Тест обновления состояния после выполнения запроса."""
    mock_time.return_value = 1000
    limiter = RateLimiter()

    # Вызываем метод обновления
    limiter.update_after_call("market")

    # Проверяем обновление времени и счетчика
    assert limiter.last_request_times["market"] == 1000
    assert limiter.request_counters["market"] == 1

    # Повторный вызов
    limiter.update_after_call("market")
    assert limiter.request_counters["market"] == 2


@pytest.mark.asyncio
@patch("time.time")
async def test_mark_rate_limited(mock_time) -> None:
    """Тест отметки эндпоинта как находящегося под ограничением."""
    mock_time.return_value = 1000
    limiter = RateLimiter()

    # Отмечаем эндпоинт как находящийся под ограничением
    limiter.mark_rate_limited("market", 60)

    # Проверяем, что время сброса установлено правильно
    assert limiter.reset_times["market"] == 1060  # 1000 + 60


@pytest.mark.asyncio
@patch("time.time")
@patch("asyncio.sleep")
async def test_wait_if_needed_no_wait(mock_sleep, mock_time) -> None:
    """Тест ожидания, когда ожидание не требуется."""
    mock_time.return_value = 1000
    limiter = RateLimiter()

    # Первый запрос не требует ожидания
    await limiter.wait_if_needed("market")

    # Проверяем, что sleep не вызывался
    mock_sleep.assert_not_called()


@pytest.mark.asyncio
@patch("time.time")
@patch("asyncio.sleep")
async def test_wait_if_needed_with_reset_time(mock_sleep, mock_time) -> None:
    """Тест ожидания с учетом времени сброса."""
    limiter = RateLimiter()

    # Текущее время 1000, время сброса 1060
    mock_time.return_value = 1000
    limiter.reset_times["market"] = 1060

    # Вызываем метод ожидания
    await limiter.wait_if_needed("market")

    # Должен быть вызван sleep с интервалом ожидания до времени сброса
    mock_sleep.assert_called_once_with(60)

    # Проверяем, что запись о времени сброса удалена
    assert "market" not in limiter.reset_times
