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
            price_value = self._get_price_value(item)
            if price_value < filters["min_price"]:
                return False

        if "max_price" in filters:
            price_value = self._get_price_value(item)
            if price_value > filters["max_price"]:
                return False

        return True

    def _get_price_value(self, item: dict[str, Any]) -> float:
        """Extract the price value from an item.

        Args:
            item: The item to extract price from.

        Returns:
            The price value as a float.

        """
        if "price" not in item:
            return 0.0

        price = item["price"]
        if isinstance(price, dict):
            if "USD" in price:
                return float(price["USD"])
            if "amount" in price:
                # DMarket API sometimes returns price as {amount: 10000, currency: "USD"}
                # where amount is in cents
                return float(price["amount"]) / 100.0

        return float(price)

    def build_api_params(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Build API parameters based on filters.

        Args:
            filters: The filters to convert to API parameters.

        Returns:
            A dictionary of API parameters.

        """
        params: dict[str, Any] = {}

        # Common price filters
        if "min_price" in filters:
            params["minPrice"] = int(float(filters["min_price"]) * 100)  # Convert to cents
        if "max_price" in filters:
            params["maxPrice"] = int(float(filters["max_price"]) * 100)  # Convert to cents

        return params

    def get_filter_description(self, filters: dict[str, Any]) -> str:
        """Get a human-readable description of the filters.

        Args:
            filters: The filters to describe.

        Returns:
            A string describing the filters.

        """
        descriptions = []

        if "min_price" in filters:
            descriptions.append(f"Price from ${float(filters['min_price']):.2f}")
        if "max_price" in filters:
            descriptions.append(f"Price to ${float(filters['max_price']):.2f}")

        return ", ".join(descriptions)


class CS2Filter(BaseGameFilter):
    """Filter for CS2/CSGO items."""

    game_name = "csgo"
    supported_filters = BaseGameFilter.supported_filters + [
        "float_min",
        "float_max",
        "category",
        "rarity",
        "exterior",
        "stattrak",
        "souvenir",
    ]

    def apply_filters(self, item: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if CS2 item passes the filters.

        Args:
            item: The item to check.
            filters: The filters to apply.

        Returns:
            True if item passes all filters, False otherwise.

        """
        if not super().apply_filters(item, filters):
            return False

        # Float range (wear) filters
        if "float_min" in filters and "float" in item:
            if item["float"] < filters["float_min"]:
                return False
        if "float_max" in filters and "float" in item:
            if item["float"] > filters["float_max"]:
                return False

        # Category filter (e.g., Rifle, Knife, etc.)
        if "category" in filters and "category" in item:
            if item["category"] != filters["category"]:
                return False

        # Rarity filter (e.g., Covert, Classified, etc.)
        if "rarity" in filters and "rarity" in item:
            if item["rarity"] != filters["rarity"]:
                return False

        # Exterior filter (e.g., Factory New, Field-Tested, etc.)
        # This is usually part of the title
        if "exterior" in filters and "title" in item:
            if filters["exterior"] not in item["title"]:
                return False

        # StatTrak filter
        if filters.get("stattrak"):
            if "title" not in item or "StatTrak™" not in item["title"]:
                return False

        # Souvenir filter
        if filters.get("souvenir"):
            if "title" not in item or "Souvenir" not in item["title"]:
                return False

        return True

    def build_api_params(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Build CS2-specific API parameters.

        Args:
            filters: The filters to convert to API parameters.

        Returns:
            A dictionary of API parameters.

        """
        params = super().build_api_params(filters)

        # Float range parameters
        if "float_min" in filters:
            params["floatMin"] = filters["float_min"]
        if "float_max" in filters:
            params["floatMax"] = filters["float_max"]

        # Category parameter
        if "category" in filters:
            params["category"] = filters["category"]

        # Rarity parameter
        if "rarity" in filters:
            params["rarity"] = filters["rarity"]

        # Exterior parameter
        if "exterior" in filters:
            params["exterior"] = filters["exterior"]

        # StatTrak parameter
        if "stattrak" in filters:
            params["statTrak"] = "true" if filters["stattrak"] else "false"

        # Souvenir parameter
        if "souvenir" in filters:
            params["souvenir"] = "true" if filters["souvenir"] else "false"

        return params

    def get_filter_description(self, filters: dict[str, Any]) -> str:
        """Get a human-readable description of CS2 filters.

        Args:
            filters: The filters to describe.

        Returns:
            A string describing the filters.

        """
        descriptions = []
        base_description = super().get_filter_description(filters)
        if base_description:
            descriptions.append(base_description)

        if "float_min" in filters:
            descriptions.append(f"Float from {filters['float_min']}")
        if "float_max" in filters:
            descriptions.append(f"Float to {filters['float_max']}")

        if "category" in filters:
            descriptions.append(f"Category: {filters['category']}")
        if "rarity" in filters:
            descriptions.append(f"Rarity: {filters['rarity']}")
        if "exterior" in filters:
            descriptions.append(f"Exterior: {filters['exterior']}")

        if filters.get("stattrak"):
            descriptions.append("StatTrak™")
        if filters.get("souvenir"):
            descriptions.append("Souvenir")

        return ", ".join(descriptions)


class Dota2Filter(BaseGameFilter):
    """Filter for Dota 2 items."""

    game_name = "dota2"
    supported_filters = BaseGameFilter.supported_filters + [
        "hero",
        "rarity",
        "slot",
        "quality",
        "tradable",
    ]

    def apply_filters(self, item: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if Dota 2 item passes the filters.

        Args:
            item: The item to check.
            filters: The filters to apply.

        Returns:
            True if item passes all filters, False otherwise.

        """
        if not super().apply_filters(item, filters):
            return False

        # Hero filter
        if "hero" in filters and "hero" in item:
            if item["hero"] != filters["hero"]:
                return False

        # Rarity filter
        if "rarity" in filters and "rarity" in item:
            if item["rarity"] != filters["rarity"]:
                return False

        # Slot filter
        if "slot" in filters and "slot" in item:
            if item["slot"] != filters["slot"]:
                return False

        # Quality filter
        if "quality" in filters and "quality" in item:
            if item["quality"] != filters["quality"]:
                return False

        # Tradable filter
        if "tradable" in filters and "tradable" in item:
            if item["tradable"] != filters["tradable"]:
                return False

        return True

    def build_api_params(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Build Dota 2-specific API parameters.

        Args:
            filters: The filters to convert to API parameters.

        Returns:
            A dictionary of API parameters.

        """
        params = super().build_api_params(filters)

        # Hero parameter
        if "hero" in filters:
            params["hero"] = filters["hero"]

        # Rarity parameter
        if "rarity" in filters:
            params["rarity"] = filters["rarity"]

        # Slot parameter
        if "slot" in filters:
            params["slot"] = filters["slot"]

        # Quality parameter
        if "quality" in filters:
            params["quality"] = filters["quality"]

        # Tradable parameter
        if "tradable" in filters:
            params["tradable"] = "true" if filters["tradable"] else "false"

        return params

    def get_filter_description(self, filters: dict[str, Any]) -> str:
        """Get a human-readable description of Dota 2 filters.

        Args:
            filters: The filters to describe.

        Returns:
            A string describing the filters.

        """
        descriptions = []
        base_description = super().get_filter_description(filters)
        if base_description:
            descriptions.append(base_description)

        if "hero" in filters:
            descriptions.append(f"Hero: {filters['hero']}")
        if "rarity" in filters:
            descriptions.append(f"Rarity: {filters['rarity']}")
        if "slot" in filters:
            descriptions.append(f"Slot: {filters['slot']}")
        if "quality" in filters:
            descriptions.append(f"Quality: {filters['quality']}")
        if "tradable" in filters:
            tradable = "Tradable" if filters["tradable"] else "Not Tradable"
            descriptions.append(tradable)

        return ", ".join(descriptions)


class TF2Filter(BaseGameFilter):
    """Filter for Team Fortress 2 items."""

    game_name = "tf2"
    supported_filters = BaseGameFilter.supported_filters + [
        "class",
        "quality",
        "type",
        "effect",
        "killstreak",
        "australium",
    ]

    def apply_filters(self, item: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if TF2 item passes the filters.

        Args:
            item: The item to check.
            filters: The filters to apply.

        Returns:
            True if item passes all filters, False otherwise.

        """
        if not super().apply_filters(item, filters):
            return False

        # Class filter
        if "class" in filters and "class" in item:
            if item["class"] != filters["class"]:
                return False

        # Quality filter
        if "quality" in filters and "quality" in item:
            if item["quality"] != filters["quality"]:
                return False

        # Type filter
        if "type" in filters and "type" in item:
            if item["type"] != filters["type"]:
                return False

        # Effect filter (for unusual items)
        if "effect" in filters and "effect" in item:
            if item["effect"] != filters["effect"]:
                return False

        # Killstreak filter
        if "killstreak" in filters and "killstreak" in item:
            if item["killstreak"] != filters["killstreak"]:
                return False

        # Australium filter
        if "australium" in filters and "australium" in item:
            if item["australium"] != filters["australium"]:
                return False

        return True

    def build_api_params(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Build TF2-specific API parameters.

        Args:
            filters: The filters to convert to API parameters.

        Returns:
            A dictionary of API parameters.

        """
        params = super().build_api_params(filters)

        # Class parameter
        if "class" in filters:
            params["class"] = filters["class"]

        # Quality parameter
        if "quality" in filters:
            params["quality"] = filters["quality"]

        # Type parameter
        if "type" in filters:
            params["type"] = filters["type"]

        # Effect parameter
        if "effect" in filters:
            params["effect"] = filters["effect"]

        # Killstreak parameter
        if "killstreak" in filters:
            params["killstreak"] = filters["killstreak"]

        # Australium parameter
        if "australium" in filters:
            params["australium"] = "true" if filters["australium"] else "false"

        return params

    def get_filter_description(self, filters: dict[str, Any]) -> str:
        """Get a human-readable description of TF2 filters.

        Args:
            filters: The filters to describe.

        Returns:
            A string describing the filters.

        """
        descriptions = []
        base_description = super().get_filter_description(filters)
        if base_description:
            descriptions.append(base_description)

        if "class" in filters:
            descriptions.append(f"Class: {filters['class']}")
        if "quality" in filters:
            descriptions.append(f"Quality: {filters['quality']}")
        if "type" in filters:
            descriptions.append(f"Type: {filters['type']}")
        if "effect" in filters:
            descriptions.append(f"Effect: {filters['effect']}")
        if "killstreak" in filters:
            descriptions.append(f"Killstreak: {filters['killstreak']}")
        if filters.get("australium"):
            descriptions.append("Australium")

        return ", ".join(descriptions)


class RustFilter(BaseGameFilter):
    """Filter for Rust items."""

    game_name = "rust"
    supported_filters = BaseGameFilter.supported_filters + [
        "category",
        "type",
        "rarity",
    ]

    def apply_filters(self, item: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if Rust item passes the filters.

        Args:
            item: The item to check.
            filters: The filters to apply.

        Returns:
            True if item passes all filters, False otherwise.

        """
        if not super().apply_filters(item, filters):
            return False

        # Category filter
        if "category" in filters and "category" in item:
            if item["category"] != filters["category"]:
                return False

        # Type filter
        if "type" in filters and "type" in item:
            if item["type"] != filters["type"]:
                return False

        # Rarity filter
        if "rarity" in filters and "rarity" in item:
            if item["rarity"] != filters["rarity"]:
                return False

        return True

    def build_api_params(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Build Rust-specific API parameters.

        Args:
            filters: The filters to convert to API parameters.

        Returns:
            A dictionary of API parameters.

        """
        params = super().build_api_params(filters)

        # Category parameter
        if "category" in filters:
            params["category"] = filters["category"]

        # Type parameter
        if "type" in filters:
            params["type"] = filters["type"]

        # Rarity parameter
        if "rarity" in filters:
            params["rarity"] = filters["rarity"]

        return params

    def get_filter_description(self, filters: dict[str, Any]) -> str:
        """Get a human-readable description of Rust filters.

        Args:
            filters: The filters to describe.

        Returns:
            A string describing the filters.

        """
        descriptions = []
        base_description = super().get_filter_description(filters)
        if base_description:
            descriptions.append(base_description)

        if "category" in filters:
            descriptions.append(f"Category: {filters['category']}")
        if "type" in filters:
            descriptions.append(f"Type: {filters['type']}")
        if "rarity" in filters:
            descriptions.append(f"Rarity: {filters['rarity']}")

        return ", ".join(descriptions)


class FilterFactory:
    """Factory for creating game filter instances."""

    _filters = {
        "csgo": CS2Filter,
        "dota2": Dota2Filter,
        "tf2": TF2Filter,
        "rust": RustFilter,
    }

    @classmethod
    def get_filter(cls, game: str) -> BaseGameFilter:
        """Get a filter instance for a specific game.

        Args:
            game: The game identifier (case insensitive).

        Returns:
            A filter instance for the specified game.

        Raises:
            ValueError: If the game is not supported.

        """
        game_lower = game.lower()
        if game_lower not in cls._filters:
            supported_games = ", ".join(cls._filters.keys())
            raise ValueError(
                f"Game '{game}' is not supported. Supported games: {supported_games}",
            )

        return cls._filters[game_lower]()

    @classmethod
    def get_supported_games(cls) -> list[str]:
        """Get a list of supported games.

        Returns:
            A list of supported game identifiers.

        """
        return list(cls._filters.keys())


def apply_filters_to_items(
    items: list[dict[str, Any]],
    game: str,
    filters: dict[str, Any],
) -> list[dict[str, Any]]:
    """Apply filters to a list of items.

    Args:
        items: The list of items to filter.
        game: The game identifier.
        filters: The filters to apply.

    Returns:
        A filtered list of items.

    """
    game_filter = FilterFactory.get_filter(game)
    return [item for item in items if game_filter.apply_filters(item, filters)]


def build_api_params_for_game(
    game: str,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """Build API parameters for a specific game.

    Args:
        game: The game identifier.
        filters: The filters to convert to API parameters.

    Returns:
        A dictionary of API parameters.

    """
    game_filter = FilterFactory.get_filter(game)
    params = game_filter.build_api_params(filters)
    params["gameId"] = game
    return params
