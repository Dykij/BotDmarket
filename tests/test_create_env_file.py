import io
import os
import sys
import unittest
from unittest.mock import mock_open, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestCreateEnvFile(unittest.TestCase):
    """Tests for the create_env_file.py utility."""

    def setUp(self):
        """Set up test fixtures."""
        # Test environment variables
        self.test_env_vars = {
            "TELEGRAM_BOT_TOKEN": "1234567890:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPабвг",
            "DMARKET_PUBLIC_KEY": "testpublickey123",
            "DMARKET_SECRET_KEY": "testsecretkey456",
            "DMARKET_API_URL": "https://api.dmarket.com",
            "LOG_LEVEL": "INFO",
        }

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_read_existing_env(self, mock_exists, mock_file):
        """Test read_existing_env function."""
        import create_env_file

        # Mock file exists
        mock_exists.return_value = True

        # Mock file content
        mock_file.return_value.read.return_value = """
        # Comment line
        TELEGRAM_BOT_TOKEN=1234567890:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQ
        DMARKET_PUBLIC_KEY=publickey123
        DMARKET_SECRET_KEY=secretkey456
        DMARKET_API_URL=https://api.dmarket.com
        LOG_LEVEL=INFO
        """

        # Call the function
        result = create_env_file.read_existing_env()

        # Check result
        self.assertEqual(
            result["TELEGRAM_BOT_TOKEN"], "1234567890:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQ"
        )
        self.assertEqual(result["DMARKET_PUBLIC_KEY"], "publickey123")
        self.assertEqual(result["DMARKET_SECRET_KEY"], "secretkey456")
        self.assertEqual(result["DMARKET_API_URL"], "https://api.dmarket.com")
        self.assertEqual(result["LOG_LEVEL"], "INFO")

    def test_validate_input_valid(self):
        """Test validate_input function with valid inputs."""
        import create_env_file

        # Test required field with valid value
        var_info = {
            "name": "TELEGRAM_BOT_TOKEN",
            "required": True,
            "pattern": r"^\d+:[A-Za-z0-9_-]+$",
        }
        is_valid, _ = create_env_file.validate_input(
            "1234567890:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQ", var_info
        )
        self.assertTrue(is_valid)

        # Test optional field with valid value
        var_info = {
            "name": "LOG_LEVEL",
            "required": False,
            "pattern": r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        }
        is_valid, _ = create_env_file.validate_input("INFO", var_info)
        self.assertTrue(is_valid)

        # Test optional field with empty value
        is_valid, _ = create_env_file.validate_input("", var_info)
        self.assertTrue(is_valid)

    def test_validate_input_invalid(self):
        """Test validate_input function with invalid inputs."""
        import create_env_file

        # Test required field with empty value
        var_info = {
            "name": "TELEGRAM_BOT_TOKEN",
            "required": True,
            "pattern": r"^\d+:[A-Za-z0-9_-]+$",
            "error_message": "Токен должен иметь формат '123456789:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPабвг'",
        }
        is_valid, error_message = create_env_file.validate_input("", var_info)
        self.assertFalse(is_valid)
        self.assertEqual(error_message, "Это поле обязательно для заполнения")

        # Test field with invalid format
        is_valid, error_message = create_env_file.validate_input("invalid-token", var_info)
        self.assertFalse(is_valid)
        self.assertEqual(
            error_message,
            "Токен должен иметь формат '123456789:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPабвг'",
        )

    @patch("builtins.open", new_callable=mock_open)
    def test_save_env_file(self, mock_file):
        """Test save_env_file function."""
        import create_env_file

        # Call the function
        create_env_file.save_env_file(self.test_env_vars)

        # Check file was opened for writing
        mock_file.assert_called_once()

        # Check each variable was written
        handle = mock_file()
        for var_name, var_value in self.test_env_vars.items():
            handle.write.assert_any_call(f"{var_name}={var_value}\n\n")

    @patch("requests.get")
    def test_verify_api_keys_success(self, mock_get):
        """Test verify_api_keys function with successful response."""
        import create_env_file

        # Mock successful response
        mock_response = mock_get.return_value
        mock_response.status_code = 200

        # Call the function
        result = create_env_file.verify_api_keys("testpublickey", "testsecretkey")

        # Check result
        self.assertTrue(result)

        # Verify request was made with correct params
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "https://api.dmarket.com/account/v1/balance")
        self.assertIn("X-Api-Key", kwargs["headers"])
        self.assertEqual(kwargs["headers"]["X-Api-Key"], "testpublickey")

    @patch("requests.get")
    def test_verify_api_keys_unauthorized(self, mock_get):
        """Test verify_api_keys function with unauthorized response."""
        import create_env_file

        # Mock unauthorized response
        mock_response = mock_get.return_value
        mock_response.status_code = 401

        # Call the function with stdout captured to suppress print statements
        with patch("sys.stdout", new=io.StringIO()):
            result = create_env_file.verify_api_keys("testpublickey", "testsecretkey")

        # Check result
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
