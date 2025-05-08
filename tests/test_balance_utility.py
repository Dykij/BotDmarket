import unittest
import sys
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestBalanceUtility(unittest.TestCase):
    """Tests for the test_balance.py utility."""

    def setUp(self):
        """Set up test fixtures."""
        # Test API keys
        self.test_api_keys = {
            "public_key": "testpublickey123",
            "secret_key": "testsecretkey456",
            "api_url": "https://api.dmarket.com"
        }

    @patch('os.environ')
    @patch('builtins.input')
    def test_get_api_keys_from_env(self, mock_input, mock_environ):
        """Test get_api_keys function when keys are in environment."""
        import test_balance
        
        # Mock environment variables
        mock_environ.get.side_effect = lambda key, default: {
            "DMARKET_PUBLIC_KEY": "testpublickey123",
            "DMARKET_SECRET_KEY": "testsecretkey456",
            "DMARKET_API_URL": "https://api.dmarket.com"
        }.get(key, default)
        
        # Call the function
        result = test_balance.get_api_keys()
        
        # Check result
        self.assertEqual(result["public_key"], "testpublickey123")
        self.assertEqual(result["secret_key"], "testsecretkey456")
        self.assertEqual(result["api_url"], "https://api.dmarket.com")
        
        # Verify input was not called
        mock_input.assert_not_called()

    @patch('os.environ')
    @patch('builtins.input')
    def test_get_api_keys_from_input(self, mock_input, mock_environ):
        """Test get_api_keys function when keys are from user input."""
        import test_balance
        
        # Mock environment variables (empty)
        mock_environ.get.return_value = ""
        
        # Mock user input
        mock_input.side_effect = ["inputpublickey", "inputsecretkey"]
        
        # Call the function
        result = test_balance.get_api_keys()
        
        # Check result
        self.assertEqual(result["public_key"], "inputpublickey")
        self.assertEqual(result["secret_key"], "inputsecretkey")
        self.assertEqual(result["api_url"], "https://api.dmarket.com")
        
        # Verify input was called
        self.assertEqual(mock_input.call_count, 2)

    async def async_test_dmarket_api_success(self):
        """Test test_dmarket_api function with successful response."""
        import test_balance
        
        # Mock DMarketAPI
        with patch('src.dmarket.dmarket_api.DMarketAPI') as mock_api_class:
            # Setup mock response
            mock_api_instance = mock_api_class.return_value
            mock_api_instance._request = AsyncMock()
            mock_api_instance._request.return_value = {"balance": 123.45}
            
            # Call the function
            result = await test_balance.test_dmarket_api(self.test_api_keys, "/test/endpoint")
            
            # Check result
            self.assertTrue(result["success"])
            self.assertEqual(result["response"], {"balance": 123.45})
            self.assertEqual(result["endpoint"], "/test/endpoint")
            
            # Verify API was initialized with correct params
            mock_api_class.assert_called_once_with(
                public_key=self.test_api_keys["public_key"],
                secret_key=self.test_api_keys["secret_key"],
                api_url=self.test_api_keys["api_url"],
                max_retries=2
            )
            
            # Verify request was made
            mock_api_instance._request.assert_called_once_with(
                method="GET",
                endpoint="/test/endpoint",
                params={}
            )

    async def async_test_dmarket_api_error(self):
        """Test test_dmarket_api function with error response."""
        import test_balance
        
        # Mock DMarketAPI
        with patch('src.dmarket.dmarket_api.DMarketAPI') as mock_api_class:
            # Setup mock to raise exception
            mock_api_instance = mock_api_class.return_value
            mock_api_instance._request = AsyncMock()
            mock_api_instance._request.side_effect = Exception("Test error")
            
            # Call the function
            result = await test_balance.test_dmarket_api(self.test_api_keys, "/test/endpoint")
            
            # Check result
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "Test error")
            self.assertEqual(result["endpoint"], "/test/endpoint")

    async def async_test_patched_get_balance_success(self):
        """Test test_patched_get_balance function with successful response."""
        import test_balance
        
        # Mock apply_balance_patch
        with patch('src.dmarket.dmarket_api_patches.apply_balance_patch') as mock_apply_patch:
            # Mock DMarketAPI
            with patch('src.dmarket.dmarket_api.DMarketAPI') as mock_api_class:
                # Setup mock response
                mock_api_instance = mock_api_class.return_value
                # Mock the patched method
                mock_api_instance.get_user_balance = AsyncMock()
                mock_api_instance.get_user_balance.return_value = {
                    "balance": 100.0,
                    "available_balance": 90.0,
                    "total_balance": 110.0,
                    "has_funds": True,
                    "error": False
                }
                
                # Call the function
                result = await test_balance.test_patched_get_balance(self.test_api_keys)
                
                # Check result
                self.assertTrue(result["success"])
                self.assertEqual(result["balance"]["balance"], 100.0)
                self.assertEqual(result["balance"]["available_balance"], 90.0)
                self.assertEqual(result["balance"]["total_balance"], 110.0)
                self.assertTrue(result["balance"]["has_funds"])
                
                # Verify patch was applied
                mock_apply_patch.assert_called_once()
                
                # Verify API was initialized with correct params
                mock_api_class.assert_called_once()
                
                # Verify get_user_balance was called
                mock_api_instance.get_user_balance.assert_called_once()

    def test_test_dmarket_api(self):
        """Runner for async test_dmarket_api tests."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_test_dmarket_api_success())
        loop.run_until_complete(self.async_test_dmarket_api_error())

    def test_test_patched_get_balance(self):
        """Runner for async test_patched_get_balance tests."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_test_patched_get_balance_success())


if __name__ == '__main__':
    unittest.main() 