"""Module for filtering game items on DMarket by game-specific attributes.

This module provides a collection of filter classes for different games,
allowing for detailed filtering of game items based on their attributes.
Supported games include CS2/CSGO, Dota 2, Team Fortress 2, and Rust.
"""

from typing import Any


class BaseGameFilter:
    """Base class for game filters."""

    game_name = "base"
    # Common filters for all games
    supported_filters = ["min_price", "max_price"]

    def apply_filters(self, item: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if item passes the filters.

        Args:
            item: The item to check.
            filters: The filters to apply.

        Returns:
            True if item passes all filters, False otherwise.

        """
        # Price filters
        if "min_price" in filters:
            price = float(item.get("price", {}).get("USD", 0))
            if price < filters["min_price"]:
                return False

        if "max_price" in filters:
            price = float(item.get("price", {}).get("USD", 0))
            if price > filters["max_price"]:
                return False

        return True


# Остальная часть кода скопирована из оригинального файла
