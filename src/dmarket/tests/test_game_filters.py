"""Тесты для модуля game_filters.py.

Этот модуль тестирует функциональность фильтров игр.
"""

import pytest

from src.dmarket.game_filters import (
    BaseGameFilter,
    CS2Filter,
    Dota2Filter,
    FilterFactory,
    RustFilter,
    TF2Filter,
    apply_filters_to_items,
    build_api_params_for_game,
)


def test_base_game_filter():
    """Тестирует базовый класс фильтров."""
    base_filter = BaseGameFilter()

    # Проверка поддерживаемых фильтров
    assert "min_price" in base_filter.supported_filters
    assert "max_price" in base_filter.supported_filters

    # Проверка применения фильтров
    item = {"price": {"amount": 1500}}  # $15.00

    # Проверка прохождения фильтров
    assert base_filter.apply_filters(item, {"min_price": 10.0})
    assert base_filter.apply_filters(item, {"max_price": 20.0})
    assert base_filter.apply_filters(item, {"min_price": 10.0, "max_price": 20.0})

    # Проверка непрохождения фильтров
    assert not base_filter.apply_filters(item, {"min_price": 20.0})
    assert not base_filter.apply_filters(item, {"max_price": 10.0})

    # Проверка построения параметров API
    params = base_filter.build_api_params({"min_price": 10.5, "max_price": 100.0})
    assert params["minPrice"] == 1050  # Цена в центах
    assert params["maxPrice"] == 10000  # Цена в центах

    # Проверка получения описания фильтров
    desc = base_filter.get_filter_description({"min_price": 10.5, "max_price": 100.0})
    assert "Price from $10.50" in desc
    assert "Price to $100.00" in desc


def test_cs2_filter():
    """Тестирует фильтр для CS2/CSGO."""
    cs2_filter = CS2Filter()

    # Проверка поддерживаемых фильтров
    assert "float_min" in cs2_filter.supported_filters
    assert "float_max" in cs2_filter.supported_filters
    assert "category" in cs2_filter.supported_filters
    assert "rarity" in cs2_filter.supported_filters
    assert "exterior" in cs2_filter.supported_filters
    assert "stattrak" in cs2_filter.supported_filters
    assert "souvenir" in cs2_filter.supported_filters

    # Создаем тестовый предмет
    item = {
        "price": {"amount": 1500},  # $15.00
        "title": "AK-47 | Redline (Field-Tested)",
        "extra": {
            "floatValue": 0.25,
            "category": "Rifle",
            "rarity": "Classified",
            "exterior": "ft",
            "stattrak": False,
            "souvenir": False,
        },
    }

    # Проверка прохождения фильтров
    assert cs2_filter.apply_filters(item, {"category": "Rifle"})
    assert cs2_filter.apply_filters(item, {"rarity": "Classified"})
    assert cs2_filter.apply_filters(item, {"exterior": "Field-Tested"})
    assert cs2_filter.apply_filters(item, {"float_min": 0.2, "float_max": 0.3})

    # Проверка непрохождения фильтров
    assert not cs2_filter.apply_filters(item, {"category": "Knife"})
    assert not cs2_filter.apply_filters(item, {"rarity": "Covert"})
    assert not cs2_filter.apply_filters(item, {"exterior": "Factory New"})
    assert not cs2_filter.apply_filters(item, {"float_min": 0.3, "float_max": 0.4})
    assert not cs2_filter.apply_filters(item, {"stattrak": True})

    # Проверка построения параметров API
    params = cs2_filter.build_api_params(
        {
            "min_price": 10.5,
            "max_price": 100.0,
            "float_min": 0.15,
            "float_max": 0.37,
            "category": "Rifle",
            "rarity": "Classified",
            "exterior": "Field-Tested",
            "stattrak": True,
            "souvenir": False,
        },
    )

    assert params["minPrice"] == 1050
    assert params["maxPrice"] == 10000
    assert params["floatMin"] == 0.15
    assert params["floatMax"] == 0.37
    assert params["category"] == "Rifle"
    assert params["rarity"] == "Classified"
    assert params["exterior"] == "Field-Tested"
    assert params["statTrak"] == "true"
    assert params["souvenir"] == "false"

    # Проверка получения описания фильтров
    desc = cs2_filter.get_filter_description(
        {
            "min_price": 10.5,
            "max_price": 100.0,
            "category": "Rifle",
            "exterior": "Field-Tested",
        },
    )

    assert "Price from $10.50" in desc
    assert "Price to $100.00" in desc
    assert "Category: Rifle" in desc
    assert "Exterior: Field-Tested" in desc


def test_dota2_filter():
    """Тестирует фильтр для Dota 2."""
    dota2_filter = Dota2Filter()

    # Проверка поддерживаемых фильтров
    assert "hero" in dota2_filter.supported_filters
    assert "rarity" in dota2_filter.supported_filters
    assert "slot" in dota2_filter.supported_filters
    assert "quality" in dota2_filter.supported_filters
    assert "tradable" in dota2_filter.supported_filters

    # Создаем тестовый предмет
    item = {
        "price": {"amount": 1500},  # $15.00
        "hero": "Pudge",
        "rarity": "Immortal",
        "slot": "Weapon",
        "quality": "Standard",
        "tradable": True,
    }

    # Проверка прохождения фильтров
    assert dota2_filter.apply_filters(item, {"hero": "Pudge"})
    assert dota2_filter.apply_filters(item, {"rarity": "Immortal"})
    assert dota2_filter.apply_filters(item, {"slot": "Weapon"})
    assert dota2_filter.apply_filters(item, {"quality": "Standard"})
    assert dota2_filter.apply_filters(item, {"tradable": True})

    # Проверка непрохождения фильтров
    assert not dota2_filter.apply_filters(item, {"hero": "Axe"})
    assert not dota2_filter.apply_filters(item, {"rarity": "Legendary"})
    assert not dota2_filter.apply_filters(item, {"slot": "Head"})
    assert not dota2_filter.apply_filters(item, {"quality": "Exalted"})
    assert not dota2_filter.apply_filters(item, {"tradable": False})

    # Проверка построения параметров API
    params = dota2_filter.build_api_params(
        {
            "min_price": 5.0,
            "max_price": 50.0,
            "hero": "Pudge",
            "rarity": "Immortal",
            "slot": "Weapon",
            "quality": "Standard",
            "tradable": True,
        },
    )

    assert params["minPrice"] == 500
    assert params["maxPrice"] == 5000
    assert params["hero"] == "Pudge"
    assert params["rarity"] == "Immortal"
    assert params["slot"] == "Weapon"
    assert params["quality"] == "Standard"
    assert params["tradable"] == "true"


def test_filter_factory():
    """Тестирует фабрику фильтров."""
    # Проверка получения фильтров по имени игры
    cs2_filter = FilterFactory.get_filter("csgo")
    dota2_filter = FilterFactory.get_filter("dota2")
    tf2_filter = FilterFactory.get_filter("tf2")
    rust_filter = FilterFactory.get_filter("rust")

    # Проверка типов возвращаемых фильтров
    assert isinstance(cs2_filter, CS2Filter)
    assert isinstance(dota2_filter, Dota2Filter)
    assert isinstance(tf2_filter, TF2Filter)
    assert isinstance(rust_filter, RustFilter)

    # Проверка case-insensitive получения фильтров
    assert isinstance(FilterFactory.get_filter("CSGO"), CS2Filter)
    assert isinstance(FilterFactory.get_filter("Dota2"), Dota2Filter)

    # Проверка, что неподдерживаемые игры вызывают исключение
    with pytest.raises(ValueError):
        FilterFactory.get_filter("unknown_game")

    # Проверка получения списка поддерживаемых игр
    supported_games = FilterFactory.get_supported_games()
    assert "csgo" in supported_games
    assert "dota2" in supported_games
    assert "tf2" in supported_games
    assert "rust" in supported_games
    assert len(supported_games) == 4


def test_apply_filters_to_items():
    """Тестирует применение фильтров к списку предметов."""
    # Создаем тестовые предметы
    items = [
        {
            "price": {"amount": 1000},  # $10.00
            "title": "AK-47 | Redline (Field-Tested)",
            "extra": {
                "category": "Rifle",
                "rarity": "Classified",
                "exterior": "ft",
            },
        },
        {
            "price": {"amount": 5000},  # $50.00
            "title": "Karambit | Fade (Factory New)",
            "extra": {
                "category": "Knife",
                "rarity": "Covert",
                "exterior": "fn",
            },
        },
        {
            "price": {"amount": 2000},  # $20.00
            "title": "AWP | Asiimov (Field-Tested)",
            "extra": {
                "category": "Rifle",
                "rarity": "Covert",
                "exterior": "ft",
            },
        },
    ]

    # Применяем фильтры
    filtered_items = apply_filters_to_items(items, "csgo", {"min_price": 20.0})
    assert len(filtered_items) == 2  # AWP и Karambit

    filtered_items = apply_filters_to_items(items, "csgo", {"category": "Rifle"})
    assert len(filtered_items) == 2  # AK-47 и AWP

    filtered_items = apply_filters_to_items(items, "csgo", {"exterior": "Factory New"})
    assert len(filtered_items) == 1  # Karambit

    filtered_items = apply_filters_to_items(
        items,
        "csgo",
        {"rarity": "Covert", "category": "Rifle"},
    )
    assert len(filtered_items) == 1  # AWP


def test_build_api_params_for_game():
    """Тестирует построение параметров API для конкретной игры."""
    # Проверка для CS2
    params = build_api_params_for_game(
        "csgo",
        {
            "min_price": 10.0,
            "max_price": 100.0,
            "category": "Knife",
            "exterior": "Factory New",
        },
    )

    assert params["gameId"] == "csgo"
    assert params["minPrice"] == 1000
    assert params["maxPrice"] == 10000
    assert params["category"] == "Knife"
    assert params["exterior"] == "Factory New"

    # Проверка для Dota2
    params = build_api_params_for_game(
        "dota2",
        {
            "min_price": 5.0,
            "hero": "Pudge",
            "rarity": "Immortal",
        },
    )

    assert params["gameId"] == "dota2"
    assert params["minPrice"] == 500
    assert params["hero"] == "Pudge"
    assert params["rarity"] == "Immortal"
