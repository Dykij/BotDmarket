import unittest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestMarketAnalysisHandler(unittest.TestCase):
    """Tests for the Market Analysis Handler module."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock for update and context
        self.update = MagicMock()
        self.context = MagicMock()
        
        # Setup message mock for update
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()
        
        # Setup callback query mock
        self.update.callback_query = MagicMock()
        self.update.callback_query.data = "analysis:price_changes:csgo"
        self.update.callback_query.from_user.id = 12345
        self.update.callback_query.edit_message_text = AsyncMock()
        self.update.callback_query.answer = AsyncMock()
        
        # Setup context.user_data
        self.context.user_data = {"market_analysis": {
            "current_game": "csgo",
            "period": "24h",
            "min_price": 1.0,
            "max_price": 500.0
        }}

    @patch('src.telegram_bot.handlers.market_analysis_handler.DMarketAPI')
    @patch('src.telegram_bot.handlers.market_analysis_handler.analyze_price_changes')
    @patch('src.telegram_bot.handlers.market_analysis_handler.pagination_manager')
    async def test_market_analysis_callback_price_changes(self, mock_pagination, mock_analyze, mock_api):
        """Test market_analysis_callback with price_changes action."""
        from src.telegram_bot.handlers.market_analysis_handler import market_analysis_callback
        
        # Setup mocks
        mock_analyze.return_value = [{"market_hash_name": "Test Item", "current_price": 10.0, "old_price": 8.0, 
                                     "change_amount": 2.0, "change_percent": 25.0}]
        
        # Call the function
        await market_analysis_callback(self.update, self.context)
        
        # Verify API was initialized
        mock_api.assert_called_once()
        
        # Verify analyze_price_changes was called
        mock_analyze.assert_called_once()
        
        # Verify pagination was set
        mock_pagination.set_items.assert_called_once()
        
        # Verify edit_message_text was called
        self.update.callback_query.edit_message_text.assert_called_once()

    @patch('src.telegram_bot.handlers.market_analysis_handler.DMarketAPI')
    @patch('src.telegram_bot.handlers.market_analysis_handler.find_undervalued_items')
    @patch('src.telegram_bot.handlers.market_analysis_handler.pagination_manager')
    async def test_market_analysis_callback_undervalued(self, mock_pagination, mock_find, mock_api):
        """Test market_analysis_callback with undervalued action."""
        from src.telegram_bot.handlers.market_analysis_handler import market_analysis_callback
        
        # Change callback data
        self.update.callback_query.data = "analysis:undervalued:csgo"
        
        # Setup mocks
        mock_find.return_value = [{"title": "Test Item", "current_price": 10.0, "avg_price": 15.0, 
                                  "discount": 33.3, "trend": "stable", "volume": 100}]
        
        # Call the function
        await market_analysis_callback(self.update, self.context)
        
        # Verify API was initialized
        mock_api.assert_called_once()
        
        # Verify find_undervalued_items was called
        mock_find.assert_called_once()
        
        # Verify pagination was set
        mock_pagination.set_items.assert_called_once()
        
        # Verify edit_message_text was called
        self.update.callback_query.edit_message_text.assert_called_once()

    @patch('src.telegram_bot.handlers.market_analysis_handler.DMarketAPI')
    @patch('src.telegram_bot.handlers.market_analysis_handler.get_investment_recommendations')
    @patch('src.telegram_bot.handlers.market_analysis_handler.pagination_manager')
    async def test_market_analysis_callback_recommendations(self, mock_pagination, mock_recommend, mock_api):
        """Test market_analysis_callback with recommendations action."""
        from src.telegram_bot.handlers.market_analysis_handler import market_analysis_callback
        
        # Change callback data
        self.update.callback_query.data = "analysis:recommendations:csgo"
        
        # Setup mocks
        mock_recommend.return_value = [{"title": "Test Item", "current_price": 10.0, "discount": 15.0, 
                                      "liquidity": "high", "investment_score": 85.0, "reason": "Good investment"}]
        
        # Call the function
        await market_analysis_callback(self.update, self.context)
        
        # Verify API was initialized
        mock_api.assert_called_once()
        
        # Verify get_investment_recommendations was called
        mock_recommend.assert_called_once()
        
        # Verify pagination was set
        mock_pagination.set_items.assert_called_once()
        
        # Verify edit_message_text was called
        self.update.callback_query.edit_message_text.assert_called_once()

    @patch('src.telegram_bot.handlers.market_analysis_handler.DMarketAPI')
    async def test_market_analysis_callback_error(self, mock_api):
        """Test market_analysis_callback with an error."""
        from src.telegram_bot.handlers.market_analysis_handler import market_analysis_callback
        
        # Setup API to raise an exception
        mock_api.side_effect = Exception("Test error")
        
        # Call the function
        await market_analysis_callback(self.update, self.context)
        
        # Verify edit_message_text was called with error message
        call_args = self.update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("❌ Произошла ошибка", call_args)


if __name__ == '__main__':
    unittest.main() 