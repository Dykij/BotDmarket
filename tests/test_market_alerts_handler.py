import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestMarketAlertsHandler(unittest.TestCase):
    """Tests for the Market Alerts Handler module."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock for update and context
        self.update = MagicMock()
        self.context = MagicMock()

        # Setup message mock for update
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()
        self.update.effective_user = MagicMock()
        self.update.effective_user.id = 12345

        # Setup callback query mock
        self.update.callback_query = MagicMock()
        self.update.callback_query.data = "alerts:toggle:price_changes"
        self.update.callback_query.from_user.id = 12345
        self.update.callback_query.edit_message_text = AsyncMock()
        self.update.callback_query.answer = AsyncMock()

    @patch("src.telegram_bot.handlers.market_alerts_handler.get_alerts_manager")
    @patch("src.telegram_bot.handlers.market_alerts_handler.get_user_alerts")
    async def test_alerts_command(self, mock_get_user_alerts, mock_get_alerts_manager):
        """Test alerts_command function."""
        from src.telegram_bot.handlers.market_alerts_handler import alerts_command

        # Setup mocks
        mock_alerts_manager = MagicMock()
        mock_alerts_manager.get_user_subscriptions.return_value = ["price_changes", "trending"]
        mock_get_alerts_manager.return_value = mock_alerts_manager

        # Mock user alerts
        mock_get_user_alerts.return_value = [
            {"id": "123", "type": "price_drop", "title": "Test Item", "threshold": 10.0},
        ]

        # Call the function
        await alerts_command(self.update, self.context)

        # Verify alerts manager was called
        mock_get_alerts_manager.assert_called_once()
        mock_alerts_manager.get_user_subscriptions.assert_called_once_with(12345)

        # Verify user alerts were fetched
        mock_get_user_alerts.assert_called_once_with(12345)

        # Verify reply_text was called
        self.update.message.reply_text.assert_called_once()

        # Check message content
        call_args = self.update.message.reply_text.call_args[0][0]
        self.assertIn("Управление уведомлениями", call_args)
        self.assertIn("Вы подписаны на следующие типы уведомлений", call_args)

    @patch("src.telegram_bot.handlers.market_alerts_handler.get_alerts_manager")
    async def test_alerts_callback_toggle(self, mock_get_alerts_manager):
        """Test alerts_callback with toggle action."""
        from src.telegram_bot.handlers.market_alerts_handler import alerts_callback

        # Setup mocks
        mock_alerts_manager = MagicMock()
        mock_alerts_manager.get_user_subscriptions.return_value = []
        mock_alerts_manager.subscribe.return_value = True
        mock_get_alerts_manager.return_value = mock_alerts_manager

        # Call the function
        await alerts_callback(self.update, self.context)

        # Verify alerts manager was called
        mock_get_alerts_manager.assert_called_once()
        mock_alerts_manager.subscribe.assert_called_once_with(12345, "price_changes")

        # Verify answer was called
        self.update.callback_query.answer.assert_called_once()

        # Verify edit_message_text was called (update_alerts_keyboard)
        self.update.callback_query.edit_message_text.assert_called_once()

    @patch("src.telegram_bot.handlers.market_alerts_handler.get_alerts_manager")
    @patch("src.telegram_bot.handlers.market_alerts_handler.get_user_alerts")
    async def test_show_user_alerts_list(self, mock_get_user_alerts, mock_get_alerts_manager):
        """Test show_user_alerts_list function."""
        from src.telegram_bot.handlers.market_alerts_handler import show_user_alerts_list

        # Mock user alerts
        mock_get_user_alerts.return_value = [
            {"id": "123", "type": "price_drop", "title": "Test Item", "threshold": 10.0},
            {"id": "456", "type": "price_rise", "title": "Another Item", "threshold": 20.0},
        ]

        # Call the function
        await show_user_alerts_list(self.update.callback_query, 12345)

        # Verify user alerts were fetched
        mock_get_user_alerts.assert_called_once_with(12345)

        # Verify edit_message_text was called
        self.update.callback_query.edit_message_text.assert_called_once()

        # Check message content
        call_args = self.update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("Мои оповещения (2)", call_args)
        self.assertIn("Test Item", call_args)
        self.assertIn("Another Item", call_args)

    @patch("src.telegram_bot.handlers.market_alerts_handler.remove_price_alert")
    async def test_alerts_callback_remove_alert(self, mock_remove_price_alert):
        """Test alerts_callback with remove_alert action."""
        from src.telegram_bot.handlers.market_alerts_handler import alerts_callback

        # Setup callback data
        self.update.callback_query.data = "alerts:remove_alert:123"

        # Mock remove_price_alert
        mock_remove_price_alert.return_value = True

        # Need to patch other functions that will be called
        with patch(
            "src.telegram_bot.handlers.market_alerts_handler.get_alerts_manager"
        ) as mock_get_alerts_manager:
            with patch(
                "src.telegram_bot.handlers.market_alerts_handler.show_user_alerts_list"
            ) as mock_show_user_alerts_list:
                # Call the function
                await alerts_callback(self.update, self.context)

                # Verify remove_price_alert was called
                mock_remove_price_alert.assert_called_once_with(12345, "123")

                # Verify answer was called with success message
                self.update.callback_query.answer.assert_called_once_with("Оповещение удалено")

                # Verify show_user_alerts_list was called
                mock_show_user_alerts_list.assert_called_once()


if __name__ == "__main__":
    unittest.main()
