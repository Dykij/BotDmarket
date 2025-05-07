"""Тесты для модуля game_filters.py.

Этот модуль тестирует функциональность src.dmarket.game_filters.
"""

import pytest

from src.dmarket.game_filters import (
    BaseGameFilter,
    CS2Filter,
    Dota2Filter,
    FilterFactory,
    RustFilter,
    apply_filters_to_items,
)


@pytest.fixture
def mock_csgo_filters():
    """Возвращает мок для фильтров CS:GO."""
    return {
        "title": "Counter-Strike: Global Offensive",
        "slug": "csgo",
        "filters": {
            "Rarities": [
                {"name": "Covert", "slug": "covert", "color": "#eb4b4b"},
                {"name": "Classified", "slug": "classified", "color": "#d32ce6"},
                {"name": "Restricted", "slug": "restricted", "color": "#8847ff"},
                {"name": "Mil-Spec", "slug": "milspec", "color": "#4b69ff"},
            ],
            "Exteriors": [
                {"name": "Factory New", "slug": "fn"},
                {"name": "Minimal Wear", "slug": "mw"},
                {"name": "Field-Tested", "slug": "ft"},
                {"name": "Well-Worn", "slug": "ww"},
                {"name": "Battle-Scarred", "slug": "bs"},
            ],
            "Categories": [
                {"name": "Knife", "slug": "knife"},
                {"name": "Rifle", "slug": "rifle"},
                {"name": "Pistol", "slug": "pistol"},
                {"name": "SMG", "slug": "smg"},
            ],
        },
    }


def test_get_csgo_filters():
    """Тестирует получение фильтров для CS:GO."""
    # Test that we can get a CS2Filter
    filter_obj = FilterFactory.get_filter("csgo")
    assert isinstance(filter_obj, CS2Filter)
    assert filter_obj.game_name == "csgo"


def test_cs2_filter_rarity():
    """Тестирует фильтрацию по редкости в CS2Filter."""
    filter_obj = CS2Filter()

    # Create test items
    classified_item = {
        "title": "AK-47 | Redline",
        "extra": {"rarity": {"name": "Classified"}},
    }

    covert_item = {
        "title": "AWP | Asiimov",
        "extra": {"rarity": {"name": "Covert"}},
    }

    # Check filter matching
    assert filter_obj.apply_filters(classified_item, {"rarity": "Classified"})
    assert not filter_obj.apply_filters(classified_item, {"rarity": "Covert"})
    assert filter_obj.apply_filters(covert_item, {"rarity": "Covert"})


def test_cs2_filter_exterior():
    """Тестирует фильтрацию по внешнему виду в CS2Filter."""
    filter_obj = CS2Filter()

    # Create test items
    ft_item = {
        "title": "AK-47 | Redline",
        "description": "Field-Tested",
        "extra": {"exterior": {"name": "Field-Tested"}},
    }

    fn_item = {
        "title": "AWP | Asiimov",
        "description": "Factory New",
        "extra": {"exterior": {"name": "Factory New"}},
    }

    # Check filter matching
    assert filter_obj.apply_filters(ft_item, {"exterior": "Field-Tested"})
    assert not filter_obj.apply_filters(ft_item, {"exterior": "Factory New"})
    assert filter_obj.apply_filters(fn_item, {"exterior": "Factory New"})


def test_cs2_filter_category():
    """Тестирует фильтрацию по категории в CS2Filter."""
    filter_obj = CS2Filter()

    # Create test items
    rifle_item = {
        "title": "AK-47 | Redline",
        "extra": {"category": {"name": "Rifle"}},
    }

    knife_item = {
        "title": "Karambit | Fade",
        "extra": {"category": {"name": "Knife"}},
    }

    # Check filter matching
    assert filter_obj.apply_filters(rifle_item, {"category": "Rifle"})
    assert not filter_obj.apply_filters(rifle_item, {"category": "Knife"})
    assert filter_obj.apply_filters(knife_item, {"category": "Knife"})


def test_price_filter():
    """Тестирует фильтрацию по цене."""
    filter_obj = BaseGameFilter()

    # Create test items with different prices
    cheap_item = {"price": {"USD": 10}}
    medium_item = {"price": {"USD": 50}}
    expensive_item = {"price": {"USD": 100}}

    # Test min_price filter
    assert filter_obj.apply_filters(cheap_item, {"min_price": 5})
    assert not filter_obj.apply_filters(cheap_item, {"min_price": 20})

    # Test max_price filter
    assert filter_obj.apply_filters(medium_item, {"max_price": 60})
    assert not filter_obj.apply_filters(expensive_item, {"max_price": 80})

    # Test combined price filter
    assert filter_obj.apply_filters(medium_item, {"min_price": 30, "max_price": 70})
    assert not filter_obj.apply_filters(cheap_item, {"min_price": 30, "max_price": 70})
    assert not filter_obj.apply_filters(
        expensive_item, {"min_price": 30, "max_price": 70}
    )


def test_complete_cs2_filter():
    """Тестирует получение полного фильтра для CS2."""
    filter_obj = CS2Filter()

    # Create a test item that matches all filters
    item = {
        "title": "AK-47 | Redline",
        "description": "Field-Tested",
        "price": {"USD": 50},
        "extra": {
            "category": {"name": "Rifle"},
            "rarity": {"name": "Classified"},
            "exterior": {"name": "Field-Tested"},
            "stattrak": False,
            "souvenir": False,
        },
    }

    # Test with all filters matching
    filters = {
        "min_price": 40,
        "max_price": 60,
        "category": "Rifle",
        "rarity": "Classified",
        "exterior": "Field-Tested",
        "stattrak": False,
        "souvenir": False,
    }

    assert filter_obj.apply_filters(item, filters)

    # Test with one non-matching filter
    non_matching = filters.copy()
    non_matching["rarity"] = "Covert"
    assert not filter_obj.apply_filters(item, non_matching)


def test_valid_filter_factory():
    """Тестирует получение валидного фильтра через FilterFactory."""
    # Check that we get the right filter for each game
    assert isinstance(FilterFactory.get_filter("csgo"), CS2Filter)
    assert isinstance(FilterFactory.get_filter("dota2"), Dota2Filter)
    assert isinstance(FilterFactory.get_filter("rust"), RustFilter)

    # Check that we get an error for invalid game
    try:
        FilterFactory.get_filter("invalid_game")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_parse_filters():
    """Тестирует парсинг фильтров."""
    # Create sample items
    items = [
        {
            "title": "AK-47 | Redline",
            "price": {"USD": 50},
            "extra": {"category": {"name": "Rifle"}},
        },
        {
            "title": "USP-S | Kill Confirmed",
            "price": {"USD": 80},
            "extra": {"category": {"name": "Pistol"}},
        },
        {
            "title": "Karambit | Fade",
            "price": {"USD": 500},
            "extra": {"category": {"name": "Knife"}},
        },
    ]

    # Filter by category
    filtered = apply_filters_to_items(items, "csgo", {"category": "Rifle"})
    assert len(filtered) == 1
    assert filtered[0]["title"] == "AK-47 | Redline"

    # Filter by price range
    filtered = apply_filters_to_items(
        items, "csgo", {"min_price": 70, "max_price": 100}
    )
    assert len(filtered) == 1
    assert filtered[0]["title"] == "USP-S | Kill Confirmed"

    # Combined filter
    filtered = apply_filters_to_items(
        items, "csgo", {"min_price": 40, "category": "Rifle"}
    )
    assert len(filtered) == 1
    assert filtered[0]["title"] == "AK-47 | Redline"

    # Filter with no matches
    filtered = apply_filters_to_items(items, "csgo", {"min_price": 1000})
    assert len(filtered) == 0
