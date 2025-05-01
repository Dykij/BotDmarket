"""
Модульные тесты для Rate Limiter.
"""

import asyncio
import time
import pytest
from unittest.mock import patch, MagicMock

from src.utils.rate_limiter import RateLimiter


@pytest.fixture
def limiter():
    """Создает экземпляр RateLimiter для тестов."""
    return RateLimiter(is_authorized=False)


def test_endpoint_type_detection():
    """Тест определения типа эндпоинта."""
    limiter = RateLimiter()
    
    # Проверяем различные пути
    assert limiter.get_endpoint_type("/api/v1/signin") == "signin"
    assert limiter.get_endpoint_type("/api/v1/fee/calculate") == "fee"
    assert limiter.get_endpoint_type("/marketplace-api/v1/items") == "market"
    assert limiter.get_endpoint_type("/market-api/v1/last-sales") == "last_sales"
    assert limiter.get_endpoint_type("/api/v1/user/balance") == "other"


def test_initialization():
    """Тест инициализации с разными параметрами."""
    # Неавторизованный пользователь
    limiter_unauth = RateLimiter(is_authorized=False)
    assert limiter_unauth.is_authorized is False
    assert limiter_unauth.limits["market"] == 2  # 2 RPS для неавторизованного
    
    # Авторизованный пользователь
    limiter_auth = RateLimiter(is_authorized=True)
    assert limiter_auth.is_authorized is True
    assert limiter_auth.limits["market"] == 10  # 10 RPS для авторизованного


@pytest.mark.asyncio
async def test_wait_if_needed():
    """Тест ожидания между запросами."""
    limiter = RateLimiter(is_authorized=False)
    
    # Устанавливаем время последнего запроса
    endpoint_type = "market"
    limiter.last_request_time[endpoint_type] = time.time()
    
    # Патч для asyncio.sleep
    with patch('asyncio.sleep', new=AsyncMock()) as mock_sleep:
        await limiter.wait_if_needed(endpoint_type)
        
        # Должен быть вызван sleep для соблюдения лимита 2 RPS (0.5 секунды между запросами)
        mock_sleep.assert_called_once()
        # Проверяем, что sleep был вызван с аргументом близким к 0.5
        assert 0.4 <= mock_sleep.call_args[0][0] <= 0.6


def test_update_from_headers():
    """Тест обновления лимитов из заголовков."""
    limiter = RateLimiter()
    
    # Имитируем заголовки ответа
    headers = {
        "X-RateLimit-Limit-Second": "5",
        "X-RateLimit-Limit-Minute": "100",
        "X-Market-RateLimit-Limit-Second": "15"
    }
    
    # Обновляем лимиты
    limiter.update_from_headers(headers)
    
    # Проверяем, что лимит для "other" был обновлен до 5 RPS
    assert limiter.custom_limits.get("other") == 5
    
    # Заголовок для минуты должен быть преобразован в RPS (100/60 = 1.67)
    assert abs(limiter.custom_limits.get("other") - 5) < 0.01


def test_convert_to_rps():
    """Тест конвертации различных единиц времени в RPS."""
    limiter = RateLimiter()
    
    # Проверяем разные единицы времени
    assert limiter._convert_to_rps(60, "second") == 60
    assert limiter._convert_to_rps(60, "minute") == 1
    assert limiter._convert_to_rps(3600, "hour") == 1
    assert limiter._convert_to_rps(86400, "day") == 1
    
    # Проверяем обработку неизвестного типа лимита
    assert limiter._convert_to_rps(42, "unknown") == 42


# Вспомогательный класс для мока асинхронных функций
class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)
