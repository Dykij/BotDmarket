"""
Тестирование патчей для DMarket API.
"""

import unittest
import asyncio
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.dmarket.dmarket_api_patches import enhanced_get_user_balance, apply_balance_patch


class TestDMarketApiPatches(unittest.TestCase):
    """Tests for the DMarket API patches module."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_mock = MagicMock()
        self.api_mock.public_key = "test_public_key"
        self.api_mock.secret_key = "test_secret_key"
        self.api_mock._request = AsyncMock()

    async def async_test_enhanced_get_user_balance_success(self):
        """Test enhanced_get_user_balance with successful response."""
        # Mock successful response using the expected format that will work with the implementation
        self.api_mock._request.return_value = {
            "usd": {"amount": 1234}
        }
        
        result = await enhanced_get_user_balance(self.api_mock)
        
        # Check that the function correctly processed the response
        self.assertFalse(result["error"])
        self.assertEqual(result["usd"]["amount"], 1234)
        self.assertEqual(result["balance"], 12.34)  # 1234 cents = $12.34
        self.assertEqual(result["available_balance"], 12.34)
        self.assertEqual(result["total_balance"], 12.34)
        self.assertTrue(result["has_funds"])

    async def async_test_enhanced_get_user_balance_no_keys(self):
        """Test enhanced_get_user_balance with missing API keys."""
        # Set empty API keys
        api_mock = MagicMock()
        api_mock.public_key = ""
        api_mock.secret_key = ""
        
        result = await enhanced_get_user_balance(api_mock)
        
        # Check that the function correctly handles missing keys
        self.assertTrue(result["error"])
        self.assertEqual(result["error_message"], "API ключи не настроены")
        self.assertEqual(result["balance"], 0.0)

    async def async_test_enhanced_get_user_balance_api_error(self):
        """Test enhanced_get_user_balance with API error."""
        # Create a fresh mock instance to avoid state from other tests
        api_mock = MagicMock()
        api_mock.public_key = "test_public_key"
        api_mock.secret_key = "test_secret_key"
        api_mock._request = AsyncMock()
        
        # Mock error response
        api_mock._request.return_value = {
            "error": "Some error",
            "code": "Unauthorized",
            "status_code": 401
        }
        
        result = await enhanced_get_user_balance(api_mock)
        
        # Check that the function correctly handles API error
        self.assertTrue(result["error"])
        self.assertEqual(result["error_message"], "Ошибка авторизации: неверные ключи API")
        self.assertEqual(result["balance"], 0.0)

    async def async_test_enhanced_get_user_balance_exception(self):
        """Test enhanced_get_user_balance with exception."""
        # Create a fresh mock instance
        api_mock = MagicMock()
        api_mock.public_key = "test_public_key"
        api_mock.secret_key = "test_secret_key"
        api_mock._request = AsyncMock()
        
        # Mock exception
        api_mock._request.side_effect = Exception("Test exception")
        
        result = await enhanced_get_user_balance(api_mock)
        
        # Check that the function correctly handles exception
        self.assertTrue(result["error"])
        self.assertEqual(result["error_message"], "Test exception")
        self.assertEqual(result["balance"], 0.0)

    def test_apply_balance_patch(self):
        """Test apply_balance_patch function."""
        with patch('src.dmarket.dmarket_api.DMarketAPI') as mock_api_class:
            result = apply_balance_patch()
            self.assertTrue(result)
            # Check that get_user_balance was patched
            self.assertEqual(mock_api_class.get_user_balance, enhanced_get_user_balance)

    def test_enhanced_get_user_balance(self):
        """Runner for async tests of enhanced_get_user_balance."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_test_enhanced_get_user_balance_success())
        loop.run_until_complete(self.async_test_enhanced_get_user_balance_no_keys())
        loop.run_until_complete(self.async_test_enhanced_get_user_balance_api_error())
        loop.run_until_complete(self.async_test_enhanced_get_user_balance_exception())


if __name__ == '__main__':
    unittest.main()
