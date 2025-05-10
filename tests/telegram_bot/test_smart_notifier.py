"""Unit tests for the smart notifier module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from telegram import Bot, InlineKeyboardMarkup, Update

from src.telegram_bot.smart_notifier import (
    check_market_opportunities,
    check_price_alerts,
    create_alert,
    deactivate_alert,
    get_item_price,
    get_market_data_for_items,
    get_user_alerts,
    handle_notification_callback,
    load_user_preferences,
    record_notification,
    register_user,
    save_user_preferences,
    send_market_opportunity_notification,
    send_price_alert_notification,
    should_throttle_notification,
    start_notification_checker,
    update_user_preferences,
)


@pytest.fixture
def mock_bot():
    """Fixture for a mock Telegram bot."""
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return 123456789


@pytest.fixture
def sample_alert_data():
    """Sample alert data for testing."""
    return {
        "id": "test-alert-id",
        "user_id": "123456789",
        "type": "price_alert",
        "item_id": "item-123",
        "item_name": "AK-47 | Redline",
        "game": "csgo",
        "conditions": {
            "price": 10.0,
            "direction": "below",
        },
        "one_time": False,
        "created_at": datetime.now().timestamp(),
        "last_triggered": None,
        "trigger_count": 0,
        "active": True,
    }


@pytest.fixture
def sample_item_data():
    """Sample item data for testing."""
    return {
        "itemId": "item-123",
        "title": "AK-47 | Redline",
        "price": {"amount": 950},  # $9.50
        "gameId": "csgo",
        "extra": {
            "categoryPath": "Rifle",
            "rarity": "Classified",
            "exterior": "Field-Tested",
        },
    }


@pytest.fixture
def sample_opportunity_data():
    """Sample market opportunity data for testing."""
    return {
        "item_name": "AK-47 | Redline",
        "item_id": "item-123",
        "current_price": 9.50,
        "game": "csgo",
        "opportunity_score": 75,
        "opportunity_type": "buy",
        "reasons": ["Price near support level", "Recent price drop"],
        "market_analysis": {
            "trend": "down",
            "confidence": 0.8,
            "volatility": "medium",
            "patterns": [
                {"type": "bottoming", "confidence": 0.7},
            ],
            "support_level": 9.0,
            "price_change_24h": -5.0,
        },
        "timestamp": datetime.now().timestamp(),
    }


@pytest.fixture
def callback_query():
    """Sample callback query for testing."""
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    query.from_user = MagicMock(id=123456789)
    query.message = MagicMock()
    query.message.text = "Test message text"
    return query


@pytest.fixture
def mock_dmarket_api():
    """Fixture for a mock DMarketAPI."""
    api = MagicMock()
    api._request = AsyncMock()
    return api


@pytest.mark.asyncio
class TestUserManagement:
    """Tests for user management functions."""

    @patch("src.telegram_bot.smart_notifier.save_user_preferences")
    async def test_register_user(self, mock_save, sample_user_id):
        """Test registering a new user."""
        # Clear global user preferences for this test
        global _user_preferences
        _user_preferences = {}

        await register_user(sample_user_id)

        assert str(sample_user_id) in _user_preferences
        assert _user_preferences[str(sample_user_id)]["enabled"] is True
        assert _user_preferences[str(sample_user_id)]["chat_id"] == sample_user_id
        mock_save.assert_called_once()

    @patch("src.telegram_bot.smart_notifier.save_user_preferences")
    async def test_update_user_preferences(self, mock_save, sample_user_id):
        """Test updating user preferences."""
        # Register user first
        global _user_preferences
        _user_preferences = {}
        await register_user(sample_user_id)

        # Test updating preferences
        new_preferences = {
            "enabled": False,
            "frequency": "low",
            "games": {"csgo": True, "dota2": False},
        }

        await update_user_preferences(sample_user_id, new_preferences)

        assert _user_preferences[str(sample_user_id)]["enabled"] is False
        assert _user_preferences[str(sample_user_id)]["frequency"] == "low"
        assert _user_preferences[str(sample_user_id)]["games"]["csgo"] is True
        assert _user_preferences[str(sample_user_id)]["games"]["dota2"] is False
        mock_save.assert_called()


@pytest.mark.asyncio
class TestAlerts:
    """Tests for alert management functions."""

    @patch("src.telegram_bot.smart_notifier.save_user_preferences")
    @patch("uuid.uuid4")
    async def test_create_alert(self, mock_uuid, mock_save, sample_user_id):
        """Test creating a new alert."""
        # Set up mock UUID
        mock_uuid.return_value = "test-alert-id"

        # Clear global alerts for this test
        global _active_alerts
        _active_alerts = {}

        alert_id = await create_alert(
            sample_user_id,
            "price_alert",
            item_id="item-123",
            item_name="AK-47 | Redline",
            game="csgo",
            conditions={"price": 10.0, "direction": "below"},
            one_time=False,
        )

        assert alert_id == "test-alert-id"
        assert str(sample_user_id) in _active_alerts
        assert len(_active_alerts[str(sample_user_id)]) == 1
        assert _active_alerts[str(sample_user_id)][0]["type"] == "price_alert"
        assert _active_alerts[str(sample_user_id)][0]["item_id"] == "item-123"
        mock_save.assert_called_once()

    @patch("src.telegram_bot.smart_notifier.save_user_preferences")
    async def test_deactivate_alert(self, mock_save, sample_user_id, sample_alert_data):
        """Test deactivating an alert."""
        # Set up test data
        global _active_alerts
        _active_alerts = {str(sample_user_id): [sample_alert_data]}

        result = await deactivate_alert(sample_user_id, "test-alert-id")

        assert result is True
        assert _active_alerts[str(sample_user_id)][0]["active"] is False
        mock_save.assert_called_once()

        # Test deactivating non-existent alert
        result = await deactivate_alert(sample_user_id, "nonexistent-id")
        assert result is False

    async def test_get_user_alerts(self, sample_user_id, sample_alert_data):
        """Test getting a user's active alerts."""
        # Set up test data
        global _active_alerts
        _active_alerts = {str(sample_user_id): [sample_alert_data]}

        alerts = await get_user_alerts(sample_user_id)

        assert len(alerts) == 1
        assert alerts[0]["id"] == "test-alert-id"

        # Test with inactive alert
        _active_alerts[str(sample_user_id)][0]["active"] = False
        alerts = await get_user_alerts(sample_user_id)
        assert len(alerts) == 0


@pytest.mark.asyncio
class TestNotificationCheckers:
    """Tests for notification checking functions."""

    @patch("src.telegram_bot.smart_notifier.send_price_alert_notification")
    @patch("src.telegram_bot.smart_notifier.get_market_data_for_items")
    async def test_check_price_alerts(
        self,
        mock_get_market_data,
        mock_send_notification,
        mock_bot,
        mock_dmarket_api,
        sample_user_id,
        sample_alert_data,
        sample_item_data,
    ):
        """Test checking price alerts."""
        # Set up test data
        global _active_alerts, _user_preferences
        _active_alerts = {str(sample_user_id): [sample_alert_data]}
        _user_preferences = {str(sample_user_id): {"enabled": True}}

        # Mock market data
        mock_get_market_data.return_value = {"item-123": sample_item_data}

        # Test alert condition met (price below threshold)
        sample_alert_data["conditions"]["price"] = 10.0  # Alert triggers when price <= 10.0
        sample_item_data["price"]["amount"] = 950  # $9.50

        await check_price_alerts(mock_dmarket_api, mock_bot)

        mock_get_market_data.assert_called_once()
        mock_send_notification.assert_called_once()
        assert _active_alerts[str(sample_user_id)][0]["trigger_count"] == 1

        # Test one-time alert deactivation
        _active_alerts[str(sample_user_id)][0]["trigger_count"] = 0  # Reset trigger count
        _active_alerts[str(sample_user_id)][0]["one_time"] = True

        await check_price_alerts(mock_dmarket_api, mock_bot)

        assert _active_alerts[str(sample_user_id)][0]["active"] is False

    @patch("src.telegram_bot.smart_notifier.send_market_opportunity_notification")
    @patch("src.telegram_bot.smart_notifier.should_throttle_notification", return_value=False)
    @patch("src.telegram_bot.smart_notifier.analyze_market_opportunity")
    @patch("src.telegram_bot.smart_notifier.get_price_history_for_items")
    @patch("src.telegram_bot.smart_notifier.get_market_items_for_game")
    async def test_check_market_opportunities(
        self,
        mock_get_items,
        mock_get_history,
        mock_analyze,
        mock_throttle,
        mock_send,
        mock_bot,
        mock_dmarket_api,
        sample_user_id,
        sample_item_data,
        sample_opportunity_data,
    ):
        """Test checking market opportunities."""
        # Set up test data
        global _user_preferences
        _user_preferences = {
            str(sample_user_id): {
                "enabled": True,
                "notifications": {"market_opportunity": True},
                "games": {"csgo": True},
                "preferences": {"min_opportunity_score": 60, "min_price": 1.0, "max_price": 1000.0},
            },
        }

        # Mock market data
        mock_get_items.return_value = [sample_item_data]
        mock_get_history.return_value = {
            "item-123": [{"price": 10.0, "timestamp": datetime.now().timestamp()}]
        }
        mock_analyze.return_value = sample_opportunity_data

        await check_market_opportunities(mock_dmarket_api, mock_bot)

        mock_get_items.assert_called_once_with(mock_dmarket_api, "csgo")
        mock_get_history.assert_called_once()
        mock_analyze.assert_called_once()
        mock_send.assert_called_once()


@pytest.mark.asyncio
class TestNotificationUtils:
    """Tests for notification utility functions."""

    async def test_should_throttle_notification(self, sample_user_id):
        """Test notification throttling logic."""
        # Set up test data
        global _user_preferences
        _user_preferences = {
            str(sample_user_id): {
                "frequency": "normal",
                "quiet_hours": {"start": 23, "end": 8},
                "last_notification": {},
            },
        }

        # Test throttling based on timing
        notification_type = "market_opportunity"
        item_id = "item-123"

        # No previous notification, should not throttle
        result = await should_throttle_notification(sample_user_id, notification_type, item_id)
        assert result is False

        # Record a notification
        await record_notification(sample_user_id, notification_type, item_id)

        # Recent notification, should throttle
        result = await should_throttle_notification(sample_user_id, notification_type, item_id)
        assert result is True

    @patch("src.telegram_bot.smart_notifier.save_user_preferences")
    async def test_record_notification(self, mock_save, sample_user_id):
        """Test recording a notification."""
        # Set up test data
        global _user_preferences
        _user_preferences = {
            str(sample_user_id): {
                "last_notification": {},
            },
        }

        notification_type = "price_alert"
        item_id = "item-123"

        await record_notification(sample_user_id, notification_type, item_id)

        key = f"{notification_type}:{item_id}"
        assert key in _user_preferences[str(sample_user_id)]["last_notification"]
        assert isinstance(
            _user_preferences[str(sample_user_id)]["last_notification"][key], (int, float)
        )
        mock_save.assert_called_once()

    async def test_send_price_alert_notification(
        self, mock_bot, sample_user_id, sample_alert_data, sample_item_data
    ):
        """Test sending a price alert notification."""
        with patch("src.telegram_bot.smart_notifier.record_notification") as mock_record:
            user_prefs = {"preferences": {"notification_style": "detailed"}}

            await send_price_alert_notification(
                mock_bot,
                sample_user_id,
                sample_alert_data,
                sample_item_data,
                9.50,  # Current price
                user_prefs,
            )

            mock_bot.send_message.assert_called_once()
            mock_record.assert_called_once()

            # Verify message contains item name and price
            call_args = mock_bot.send_message.call_args[1]
            assert "AK-47 | Redline" in call_args["text"]
            assert "$9.50" in call_args["text"]
            assert isinstance(call_args["reply_markup"], InlineKeyboardMarkup)

    async def test_send_market_opportunity_notification(
        self, mock_bot, sample_user_id, sample_opportunity_data
    ):
        """Test sending a market opportunity notification."""
        with patch("src.telegram_bot.smart_notifier.record_notification") as mock_record:
            user_prefs = {"preferences": {"notification_style": "detailed"}}

            await send_market_opportunity_notification(
                mock_bot,
                sample_user_id,
                sample_opportunity_data,
                user_prefs,
            )

            mock_bot.send_message.assert_called_once()
            mock_record.assert_called_once()

            # Verify message contains opportunity info
            call_args = mock_bot.send_message.call_args[1]
            assert "AK-47 | Redline" in call_args["text"]
            assert "BUY Signal" in call_args["text"]
            assert "75/100" in call_args["text"]
            assert isinstance(call_args["reply_markup"], InlineKeyboardMarkup)


@pytest.mark.asyncio
class TestCallbackHandling:
    """Tests for handling notification callbacks."""

    @patch("src.telegram_bot.smart_notifier.deactivate_alert")
    async def test_handle_disable_alert_callback(self, mock_deactivate, callback_query):
        """Test handling a callback to disable an alert."""
        callback_query.data = "disable_alert:test-alert-id"
        mock_deactivate.return_value = True

        context = MagicMock()

        await handle_notification_callback(Update(0, callback_query=callback_query), context)

        callback_query.answer.assert_called_once()
        mock_deactivate.assert_called_once_with(123456789, "test-alert-id")
        callback_query.edit_message_text.assert_called_once()

    @patch("src.telegram_bot.smart_notifier.create_alert")
    @patch("src.telegram_bot.smart_notifier.get_item_by_id")
    async def test_handle_track_item_callback(
        self, mock_get_item, mock_create_alert, callback_query
    ):
        """Test handling a callback to track an item."""
        callback_query.data = "track_item:item-123:csgo"

        context = MagicMock()
        context.bot_data = {"dmarket_api": MagicMock()}

        # Mock item data
        mock_get_item.return_value = {
            "itemId": "item-123",
            "title": "AK-47 | Redline",
            "price": {"amount": 1000},  # $10.00
        }

        mock_create_alert.side_effect = ["below-alert-id", "above-alert-id"]

        await handle_notification_callback(Update(0, callback_query=callback_query), context)

        callback_query.answer.assert_called_once()
        mock_get_item.assert_called_once()
        assert (
            mock_create_alert.call_count == 2
        )  # Creates two alerts, one for price below and one for above
        callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
class TestDataFetching:
    """Tests for data fetching functions."""

    async def test_get_market_data_for_items(self, mock_dmarket_api):
        """Test getting market data for multiple items."""
        mock_dmarket_api._request.return_value = {
            "items": [
                {"itemId": "item-123", "title": "AK-47 | Redline"},
                {"itemId": "item-456", "title": "M4A4 | Asiimov"},
            ],
        }

        result = await get_market_data_for_items(
            mock_dmarket_api,
            ["item-123", "item-456"],
            "csgo",
        )

        mock_dmarket_api._request.assert_called_once()
        assert "item-123" in result
        assert "item-456" in result
        assert result["item-123"]["title"] == "AK-47 | Redline"
        assert result["item-456"]["title"] == "M4A4 | Asiimov"

    async def test_get_item_price(self):
        """Test extracting price from item data."""
        # Test with price as dict
        item_data = {"price": {"amount": 1250}}
        price = get_item_price(item_data)
        assert price == 12.50

        # Test with price as integer
        item_data = {"price": 1000}
        price = get_item_price(item_data)
        assert price == 1000.0

        # Test with missing price
        item_data = {}
        price = get_item_price(item_data)
        assert price == 0.0

    @patch("asyncio.sleep")
    async def test_start_notification_checker(self, mock_sleep, mock_dmarket_api, mock_bot):
        """Test starting the notification checker loop."""
        mock_sleep.side_effect = [None, Exception("Stop loop")]  # Run once then stop

        with patch("src.telegram_bot.smart_notifier.check_price_alerts") as mock_check_price, patch(
            "src.telegram_bot.smart_notifier.check_market_opportunities"
        ) as mock_check_market, patch(
            "src.telegram_bot.smart_notifier.load_user_preferences"
        ) as mock_load:

            try:
                await start_notification_checker(mock_dmarket_api, mock_bot, interval=1)
            except Exception:
                pass

            mock_load.assert_called_once()
            mock_check_price.assert_called_once_with(mock_dmarket_api, mock_bot)
            mock_check_market.assert_called_once_with(mock_dmarket_api, mock_bot)


class TestPreferences:
    """Tests for preference file handling."""

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"user_preferences": {"123": {"enabled": true}}, "active_alerts": {}}',
    )
    @patch("src.telegram_bot.smart_notifier.SMART_ALERTS_FILE")
    def test_load_user_preferences(self, mock_file, mock_open_func):
        """Test loading user preferences from file."""
        mock_file.exists.return_value = True

        # Clear global data
        global _user_preferences, _active_alerts
        _user_preferences = {}
        _active_alerts = {}

        load_user_preferences()

        assert "123" in _user_preferences
        assert _user_preferences["123"]["enabled"] is True
        mock_open_func.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_user_preferences(self, mock_json_dump, mock_open_func):
        """Test saving user preferences to file."""
        # Set up test data
        global _user_preferences, _active_alerts
        _user_preferences = {"123": {"enabled": True}}
        _active_alerts = {"123": [{"id": "alert1"}]}

        save_user_preferences()

        mock_open_func.assert_called_once()
        mock_json_dump.assert_called_once()
        args = mock_json_dump.call_args[0]
        assert args[0]["user_preferences"] == _user_preferences
        assert args[0]["active_alerts"] == _active_alerts
