"""
Test module for DMarket API client.
"""

from unittest.mock import AsyncMock

import pytest
import httpx

# Import the DMarketAPI class and RateLimiter to test
from src.dmarket.dmarket_api import DMarketAPI
from src.utils.rate_limiter import RateLimiter

# Sample test data
TEST_PUBLIC_KEY = "test_public_key"
TEST_SECRET_KEY = "test_secret_key"


@pytest.fixture
def dmarket_api():
    """Create a DMarketAPI instance for tests."""
    return DMarketAPI(
        public_key=TEST_PUBLIC_KEY,
        secret_key=TEST_SECRET_KEY,
        api_url="https://api.dmarket.com"
    )


@pytest.mark.asyncio
async def test_generate_signature(dmarket_api):  # type: ignore
    """Test signature generation."""
    # Test signature generation
    # type: ignore[attr-defined]
    headers = dmarket_api._generate_signature("GET", "/test/path", "")

    # Check that headers contain required keys
    assert "X-Api-Key" in headers
    assert "X-Request-Sign" in headers
    assert "Content-Type" in headers

    # Check header values
    assert headers["X-Api-Key"] == TEST_PUBLIC_KEY
    assert "timestampString" in headers["X-Request-Sign"]
    assert "signatureString" in headers["X-Request-Sign"]
    assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_request_method_with_mock(monkeypatch, dmarket_api):  # type: ignore
    """Test the _request method with mocked httpx client."""
    mock_response = {"balance": {"usd": 100}}
    
    # Мокаем метод wait_if_needed, чтобы избежать ошибок с rate_limiter
    async def mock_wait_if_needed(self, endpoint_type):
        return None
    
    monkeypatch.setattr(RateLimiter, 'wait_if_needed', mock_wait_if_needed)
    monkeypatch.setattr(RateLimiter, 'update_from_headers', lambda self, headers: None)
    
    # Создаем мок для клиента
    mock_client = AsyncMock()
    
    # Настраиваем мок ответа
    mock_response_obj = AsyncMock()
    mock_response_obj.status_code = 200
    mock_response_obj.headers = {}
    # Делаем метод json обычным методом, а не AsyncMock
    mock_response_obj.json = lambda: mock_response
    
    # Настраиваем метод raise_for_status для успешных запросов
    # Важно: не делаем его AsyncMock, чтобы избежать необходимости его ожидания
    mock_response_obj.raise_for_status = lambda: None
    
    # Настраиваем метод get
    mock_client.get.return_value = mock_response_obj
    
    # Заменяем метод получения клиента, чтобы он возвращал наш мок
    async def mock_get_client():
        return mock_client
    
    monkeypatch.setattr(dmarket_api, '_get_client', mock_get_client)
    
    # Вызываем тестируемый метод
    result = await dmarket_api._request("GET", "/test/path")
    
    # Проверяем результат
    assert result == mock_response
    
    # Проверяем, что метод get был вызван
    mock_client.get.assert_called_once_with(
        f"{dmarket_api.api_url}/test/path",
        headers=mock_client.get.call_args[1]['headers']
    )
