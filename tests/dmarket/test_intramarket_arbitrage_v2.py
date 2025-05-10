"""Unit tests for the intramarket arbitrage module."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dmarket.intramarket_arbitrage import (
    find_mispriced_rare_items,
    find_price_anomalies,
    find_trending_items,
    scan_for_intramarket_opportunities,
)


@pytest.fixture
def sample_market_items():
    """Sample market items for testing."""
    return {
        "items": [
            {
                "itemId": "item1",
                "title": "AK-47 | Redline (Field-Tested)",
                "price": {"amount": 1000},  # $10.00
                "extra": {
                    "categoryPath": "Rifle",
                    "rarity": "Classified",
                    "exterior": "Field-Tested",
                },
            },
            {
                "itemId": "item2",
                "title": "AK-47 | Redline (Field-Tested)",
                "price": {"amount": 1500},  # $15.00
                "extra": {
                    "categoryPath": "Rifle",
                    "rarity": "Classified",
                    "exterior": "Field-Tested",
                },
            },
            {
                "itemId": "item3",
                "title": "AWP | Asiimov (Battle-Scarred)",
                "price": {"amount": 2500},  # $25.00
                "extra": {
                    "categoryPath": "Sniper Rifle",
                    "rarity": "Covert",
                    "exterior": "Battle-Scarred",
                },
            },
            {
                "itemId": "item4",
                "title": "AWP | Asiimov (Battle-Scarred)",
                "price": {"amount": 2700},  # $27.00
                "extra": {
                    "categoryPath": "Sniper Rifle",
                    "rarity": "Covert",
                    "exterior": "Battle-Scarred",
                },
            },
        ],
    }


@pytest.fixture
def sample_sales_history():
    """Sample sales history data for testing."""
    return {
        "items": [
            {
                "title": "AK-47 | Redline (Field-Tested)",
                "price": {"amount": 1200},  # $12.00
                "soldAt": (datetime.now() - timedelta(hours=5)).isoformat(),
            },
            {
                "title": "AK-47 | Redline (Field-Tested)",
                "price": {"amount": 1100},  # $11.00
                "soldAt": (datetime.now() - timedelta(hours=10)).isoformat(),
            },
            {
                "title": "AWP | Asiimov (Battle-Scarred)",
                "price": {"amount": 2600},  # $26.00
                "soldAt": (datetime.now() - timedelta(hours=3)).isoformat(),
            },
            {
                "title": "AWP | Asiimov (Battle-Scarred)",
                "price": {"amount": 2400},  # $24.00
                "soldAt": (datetime.now() - timedelta(hours=8)).isoformat(),
            },
        ],
    }


@pytest.fixture
def mock_dmarket_api():
    """Fixture for mocking DMarketAPI."""
    api = MagicMock()
    api.get_market_items = AsyncMock()
    api.get_sales_history = AsyncMock()
    api._request = AsyncMock()
    api._close_client = AsyncMock()
    return api


@pytest.mark.asyncio
class TestPriceAnomalies:
    """Tests for price anomalies detection functionality."""

    async def test_find_price_anomalies(self, mock_dmarket_api, sample_market_items):
        """Test finding price anomalies between similar items."""
        # Set up mock API responses
        mock_dmarket_api.get_market_items.return_value = sample_market_items

        # Call the function
        results = await find_price_anomalies(
            game="csgo",
            similarity_threshold=0.9,
            price_diff_percent=10.0,
            max_results=10,
            min_price=1.0,
            max_price=100.0,
            dmarket_api=mock_dmarket_api,
        )

        # Verify results
        assert isinstance(results, list)
        assert len(results) > 0

        # Check that anomalies were detected for similar items with price differences
        assert any(
            r["item_to_buy"]["itemId"] == "item1" and r["item_to_sell"]["itemId"] == "item2"
            for r in results
        )

        # Verify that price difference and profit calculations are correct
        for anomaly in results:
            if (
                anomaly["item_to_buy"]["itemId"] == "item1"
                and anomaly["item_to_sell"]["itemId"] == "item2"
            ):
                assert anomaly["buy_price"] == 10.0
                assert anomaly["sell_price"] == 15.0
                assert anomaly["price_difference"] == 5.0
                assert anomaly["profit_percentage"] == 50.0  # (15 - 10) / 10 * 100

                # Verify fee calculation (7% fee)
                expected_profit = 15.0 * 0.93 - 10.0  # Sell price after fees minus buy price
                assert round(anomaly["profit_after_fee"], 2) == round(expected_profit, 2)

        # Verify the API was called correctly
        mock_dmarket_api.get_market_items.assert_called_once()
        call_args = mock_dmarket_api.get_market_items.call_args[1]
        assert call_args["game"] == "csgo"
        assert call_args["limit"] == 200
        assert call_args["price_from"] == 1.0
        assert call_args["price_to"] == 100.0

    async def test_find_price_anomalies_empty_results(self, mock_dmarket_api):
        """Test handling of empty results."""
        # Set up mock API to return empty results
        mock_dmarket_api.get_market_items.return_value = {"items": []}

        # Call the function
        results = await find_price_anomalies(
            game="csgo",
            dmarket_api=mock_dmarket_api,
        )

        # Verify empty results handling
        assert isinstance(results, list)
        assert len(results) == 0

        # Verify the API was called
        mock_dmarket_api.get_market_items.assert_called_once()

    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_find_price_anomalies_error_handling(self, mock_sleep, mock_dmarket_api):
        """Test error handling in find_price_anomalies."""
        # Set up mock API to raise an exception
        mock_dmarket_api.get_market_items.side_effect = Exception("API Error")

        # Call the function
        results = await find_price_anomalies(
            game="csgo",
            dmarket_api=mock_dmarket_api,
        )

        # Verify error handling
        assert isinstance(results, list)
        assert len(results) == 0

        # Verify API connection is closed even on error
        mock_dmarket_api._close_client.assert_called_once()


@pytest.mark.asyncio
class TestTrendingItems:
    """Tests for trending items detection functionality."""

    async def test_find_trending_items(
        self, mock_dmarket_api, sample_market_items, sample_sales_history
    ):
        """Test finding trending items based on sales history."""
        # Set up mock API responses
        mock_dmarket_api.get_market_items.return_value = sample_market_items
        mock_dmarket_api.get_sales_history.return_value = sample_sales_history

        # Call the function
        results = await find_trending_items(
            game="csgo",
            min_price=5.0,
            max_price=50.0,
            max_results=10,
            dmarket_api=mock_dmarket_api,
        )

        # Verify results
        assert isinstance(results, list)

        # Verify the API calls
        mock_dmarket_api.get_market_items.assert_called_once()
        mock_dmarket_api.get_sales_history.assert_called_once()

        # Check call arguments
        market_call_args = mock_dmarket_api.get_market_items.call_args[1]
        assert market_call_args["game"] == "csgo"
        assert market_call_args["price_from"] == 5.0
        assert market_call_args["price_to"] == 50.0

        history_call_args = mock_dmarket_api.get_sales_history.call_args[1]
        assert history_call_args["game"] == "csgo"
        assert history_call_args["days"] == 3

    async def test_find_trending_items_empty_results(self, mock_dmarket_api):
        """Test handling of empty results."""
        # Set up mock API to return empty results
        mock_dmarket_api.get_market_items.return_value = {"items": []}
        mock_dmarket_api.get_sales_history.return_value = {"items": []}

        # Call the function
        results = await find_trending_items(
            game="csgo",
            dmarket_api=mock_dmarket_api,
        )

        # Verify empty results handling
        assert isinstance(results, list)
        assert len(results) == 0


@pytest.mark.asyncio
class TestMispricedRareItems:
    """Tests for mispriced rare items detection functionality."""

    async def test_find_mispriced_rare_items(self, mock_dmarket_api, sample_market_items):
        """Test finding mispriced rare items."""
        # Extend sample items with rare attributes
        rare_items = {"items": sample_market_items["items"].copy()}
        rare_items["items"].append(
            {
                "itemId": "rare1",
                "title": "★ Karambit | Fade (Factory New)",
                "price": {"amount": 80000},  # $800.00
                "extra": {
                    "categoryPath": "Knife",
                    "rarity": "Covert",
                    "exterior": "Factory New",
                    "float": "0.009",
                },
            }
        )
        rare_items["items"].append(
            {
                "itemId": "rare2",
                "title": "★ Karambit | Fade (Factory New)",
                "price": {"amount": 60000},  # $600.00 (underpriced)
                "suggestedPrice": {"amount": 75000},  # $750.00
                "extra": {
                    "categoryPath": "Knife",
                    "rarity": "Covert",
                    "exterior": "Factory New",
                    "float": "0.011",
                },
            }
        )

        # Set up mock API responses
        mock_dmarket_api.get_market_items.return_value = rare_items

        # Call the function
        results = await find_mispriced_rare_items(
            game="csgo",
            min_price=100.0,
            max_price=1000.0,
            max_results=5,
            dmarket_api=mock_dmarket_api,
        )

        # Verify results
        assert isinstance(results, list)

        # Check if rare items are detected
        assert any(r["item"]["itemId"] == "rare2" for r in results)

        # Verify the API call
        mock_dmarket_api.get_market_items.assert_called_once()
        call_args = mock_dmarket_api.get_market_items.call_args[1]
        assert call_args["game"] == "csgo"
        assert call_args["limit"] == 500

    async def test_find_mispriced_rare_items_empty_results(self, mock_dmarket_api):
        """Test handling of empty results."""
        # Set up mock API to return empty results
        mock_dmarket_api.get_market_items.return_value = {"items": []}

        # Call the function
        results = await find_mispriced_rare_items(
            game="csgo",
            dmarket_api=mock_dmarket_api,
        )

        # Verify empty results handling
        assert isinstance(results, list)
        assert len(results) == 0


@pytest.mark.asyncio
class TestComprehensiveScan:
    """Tests for comprehensive scanning functionality."""

    @patch("src.dmarket.intramarket_arbitrage.find_price_anomalies")
    @patch("src.dmarket.intramarket_arbitrage.find_trending_items")
    @patch("src.dmarket.intramarket_arbitrage.find_mispriced_rare_items")
    async def test_scan_for_intramarket_opportunities(
        self,
        mock_rare,
        mock_trending,
        mock_anomalies,
        mock_dmarket_api,
    ):
        """Test comprehensive scanning for all opportunity types."""
        # Set up mock returns for individual functions
        mock_anomalies.return_value = [{"type": "anomaly", "item": "item1"}]
        mock_trending.return_value = [{"type": "trending", "item": "item2"}]
        mock_rare.return_value = [{"type": "rare", "item": "item3"}]

        # Call the function
        results = await scan_for_intramarket_opportunities(
            games=["csgo", "dota2"],
            max_results_per_game=5,
            min_price=10.0,
            max_price=500.0,
            include_anomalies=True,
            include_trending=True,
            include_rare=True,
            dmarket_api=mock_dmarket_api,
        )

        # Verify results structure
        assert isinstance(results, dict)
        assert "csgo" in results
        assert "dota2" in results

        # Check that all opportunity types are included
        assert "price_anomalies" in results["csgo"]
        assert "trending_items" in results["csgo"]
        assert "rare_mispriced" in results["csgo"]

        # Verify individual scan functions were called
        assert mock_anomalies.call_count == 2  # Once for each game
        assert mock_trending.call_count == 2
        assert mock_rare.call_count == 2

        # Verify call parameters
        anomalies_call_args = mock_anomalies.call_args_list[0][1]
        assert anomalies_call_args["game"] == "csgo"
        assert anomalies_call_args["max_results"] == 5
        assert anomalies_call_args["min_price"] == 10.0
        assert anomalies_call_args["max_price"] == 500.0
        assert anomalies_call_args["dmarket_api"] == mock_dmarket_api

    @patch("src.dmarket.intramarket_arbitrage.find_price_anomalies")
    @patch("src.dmarket.intramarket_arbitrage.find_trending_items")
    @patch("src.dmarket.intramarket_arbitrage.find_mispriced_rare_items")
    async def test_scan_selective_opportunity_types(
        self,
        mock_rare,
        mock_trending,
        mock_anomalies,
        mock_dmarket_api,
    ):
        """Test scanning with selective opportunity types."""
        # Set up mock returns
        mock_anomalies.return_value = [{"type": "anomaly", "item": "item1"}]
        mock_trending.return_value = [{"type": "trending", "item": "item2"}]
        mock_rare.return_value = [{"type": "rare", "item": "item3"}]

        # Call the function with only some opportunity types
        results = await scan_for_intramarket_opportunities(
            games=["csgo"],
            include_anomalies=True,
            include_trending=False,
            include_rare=True,
            dmarket_api=mock_dmarket_api,
        )

        # Verify only requested opportunity types are included
        assert "price_anomalies" in results["csgo"]
        assert "rare_mispriced" in results["csgo"]
        assert "trending_items" in results["csgo"]  # Should still exist but be empty

        # Verify only requested scan functions were called
        assert mock_anomalies.call_count == 1
        assert mock_rare.call_count == 1
        assert mock_trending.call_count == 0

    @patch("src.dmarket.intramarket_arbitrage.find_price_anomalies")
    async def test_scan_error_handling(self, mock_anomalies, mock_dmarket_api):
        """Test error handling during scan."""
        # Set up mock to raise an exception
        mock_anomalies.side_effect = Exception("Test error")

        # Call the function
        results = await scan_for_intramarket_opportunities(
            games=["csgo"],
            include_anomalies=True,
            include_trending=False,
            include_rare=False,
            dmarket_api=mock_dmarket_api,
        )

        # Verify error handling
        assert "csgo" in results
        assert "price_anomalies" in results["csgo"]
        assert results["csgo"]["price_anomalies"] == []  # Empty results on error

        # Verify API connection is closed
        mock_dmarket_api._close_client.assert_called_once()
