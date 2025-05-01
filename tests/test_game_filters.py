"""
Тесты для модуля game_filters.

Запустите этот файл для проверки функциональности фильтров:
python -m tests.test_game_filters
"""
import sys
import os
import pytest
from typing import Dict, Any, List

# Добавляем корневой каталог проекта в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dmarket.game_filters import (
    BaseGameFilter, CS2Filter, Dota2Filter, TF2Filter, RustFilter,
    FilterFactory, apply_filters_to_items, build_api_params_for_game
)


class TestBaseGameFilter:
    """Тесты для базового класса фильтров."""
    
    def test_price_filters(self):
        """Тест фильтрации по цене."""
        filter_obj = BaseGameFilter()
        
        # Проверка минимальной цены
        assert filter_obj.apply_filters({"price": 100}, {"min_price": 50})
        assert not filter_obj.apply_filters({"price": 30}, {"min_price": 50})
        
        # Проверка максимальной цены
        assert filter_obj.apply_filters({"price": 30}, {"max_price": 50})
        assert not filter_obj.apply_filters({"price": 100}, {"max_price": 50})
        
        # Проверка диапазона цен
        assert filter_obj.apply_filters(
            {"price": 75}, {"min_price": 50, "max_price": 100}
        )
        assert not filter_obj.apply_filters(
            {"price": 150}, {"min_price": 50, "max_price": 100}
        )
        
    def test_price_extraction(self):
        """Тест извлечения цены из разных форматов."""
        filter_obj = BaseGameFilter()
        
        # Прямое число
        assert filter_obj._get_price_value({"price": 100}) == 100
        
        # Строка
        assert filter_obj._get_price_value({"price": "50"}) == 50
        
        # Словарь с USD
        assert filter_obj._get_price_value({"price": {"USD": 75}}) == 75
        
        # Словарь с amount (цена в центах)
        assert filter_obj._get_price_value(
            {"price": {"amount": 10000, "currency": "USD"}}
        ) == 100
        
        # Отсутствие цены
        assert filter_obj._get_price_value({}) == 0


class TestCS2Filter:
    """Тесты для CS2 фильтров."""
    
    def test_cs2_specific_filters(self):
        """Тест CS2-специфичных фильтров."""
        filter_obj = CS2Filter()
        
        # Тест float (износа)
        item = {
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {"USD": 15},
            "float": 0.25
        }
        
        assert filter_obj.apply_filters(item, {"float_min": 0.2})
        assert not filter_obj.apply_filters(item, {"float_min": 0.3})
        assert filter_obj.apply_filters(item, {"float_max": 0.3})
        assert not filter_obj.apply_filters(item, {"float_max": 0.2})
        
        # Тест категории
        item = {
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {"USD": 15},
            "category": "Rifle"
        }
        
        assert filter_obj.apply_filters(item, {"category": "Rifle"})
        assert not filter_obj.apply_filters(item, {"category": "Pistol"})
        
        # Тест редкости
        item = {
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {"USD": 15},
            "rarity": "Classified"
        }
        
        assert filter_obj.apply_filters(item, {"rarity": "Classified"})
        assert not filter_obj.apply_filters(item, {"rarity": "Covert"})
        
        # Тест внешнего вида (из названия)
        item = {"title": "AK-47 | Redline (Field-Tested)"}
        
        assert filter_obj.apply_filters(item, {"exterior": "Field-Tested"})
        assert not filter_obj.apply_filters(item, {"exterior": "Factory New"})
        
        # Тест StatTrak
        item = {"title": "StatTrak™ AK-47 | Redline (Field-Tested)"}
        
        assert filter_obj.apply_filters(item, {"stattrak": True})
        assert not filter_obj.apply_filters(
            {"title": "AK-47 | Redline (Field-Tested)"}, 
            {"stattrak": True}
        )
        
        # Тест Souvenir
        item = {"title": "Souvenir AK-47 | Redline (Field-Tested)"}
        
        assert filter_obj.apply_filters(item, {"souvenir": True})
        assert not filter_obj.apply_filters(
            {"title": "AK-47 | Redline (Field-Tested)"}, 
            {"souvenir": True}
        )

    def test_cs2_build_api_params(self):
        """Тест создания CS2-специфичных параметров API."""
        filter_obj = CS2Filter()
        
        filters = {
            "min_price": 50,
            "float_min": 0.15,
            "float_max": 0.37,
            "category": "Rifle",
            "rarity": "Classified",
            "exterior": "Field-Tested",
            "stattrak": True,
            "souvenir": False
        }
        
        params = filter_obj.build_api_params(filters)
        
        assert params["minPrice"] == 5000
        assert params["floatMin"] == 0.15
        assert params["floatMax"] == 0.37
        assert params["category"] == "Rifle"
        assert params["rarity"] == "Classified"
        assert params["exterior"] == "Field-Tested"
        assert params["statTrak"] == "true"
        assert params["souvenir"] == "false"


class TestDota2Filter:
    """Тесты для Dota 2 фильтров."""
    
    def test_dota2_specific_filters(self):
        """Тест Dota 2-специфичных фильтров."""
        filter_obj = Dota2Filter()
        
        # Тест hero
        item = {
            "title": "Arcana Phantom Assassin",
            "price": {"USD": 35},
            "hero": "Phantom Assassin"
        }
        
        assert filter_obj.apply_filters(item, {"hero": "Phantom Assassin"})
        assert not filter_obj.apply_filters(item, {"hero": "Pudge"})
        
        # Тест rarity
        item = {
            "title": "Arcana Phantom Assassin",
            "price": {"USD": 35},
            "rarity": "Arcana"
        }
        
        assert filter_obj.apply_filters(item, {"rarity": "Arcana"})
        assert not filter_obj.apply_filters(item, {"rarity": "Immortal"})
        
        # Тест slot
        item = {
            "title": "Arcana Phantom Assassin",
            "price": {"USD": 35},
            "slot": "Weapon"
        }
        
        assert filter_obj.apply_filters(item, {"slot": "Weapon"})
        assert not filter_obj.apply_filters(item, {"slot": "Head"})
        
        # Тест quality
        item = {
            "title": "Arcana Phantom Assassin",
            "price": {"USD": 35},
            "quality": "Exalted"
        }
        
        assert filter_obj.apply_filters(item, {"quality": "Exalted"})
        assert not filter_obj.apply_filters(item, {"quality": "Genuine"})
        
        # Тест tradable
        item = {
            "title": "Arcana Phantom Assassin",
            "price": {"USD": 35},
            "tradable": True
        }
        
        assert filter_obj.apply_filters(item, {"tradable": True})
        assert not filter_obj.apply_filters(item, {"tradable": False})
        
    def test_dota2_build_api_params(self):
        """Тест создания Dota 2-специфичных параметров API."""
        filter_obj = Dota2Filter()
        
        filters = {
            "min_price": 20,
            "hero": "Juggernaut",
            "rarity": "Immortal",
            "slot": "Weapon",
            "quality": "Standard",
            "tradable": True
        }
        
        params = filter_obj.build_api_params(filters)
        
        assert params["minPrice"] == 2000
        assert params["hero"] == "Juggernaut"
        assert params["rarity"] == "Immortal"
        assert params["slot"] == "Weapon"
        assert params["quality"] == "Standard"
        assert params["tradable"] == "true"


class TestFilterFactory:
    """Тесты для фабрики фильтров."""
    
    def test_get_filter(self):
        """Тест создания фильтров для разных игр."""
        # Проверка регистронезависимости
        assert isinstance(FilterFactory.get_filter("CSGO"), CS2Filter)
        assert isinstance(FilterFactory.get_filter("csgo"), CS2Filter)
        
        # Проверка всех поддерживаемых игр
        games = FilterFactory.get_supported_games()
        assert "csgo" in games
        assert "dota2" in games
        assert "tf2" in games
        assert "rust" in games
        
        # Проверка ошибки для неподдерживаемой игры
        with pytest.raises(ValueError):
            FilterFactory.get_filter("nonexistent_game")


class TestHelperFunctions:
    """Тесты для вспомогательных функций."""
    
    def test_apply_filters_to_items(self):
        """Тест применения фильтров к списку предметов."""
        items = [
            {
                "title": "AK-47 | Redline (Field-Tested)",
                "price": {"USD": 15},
                "category": "Rifle",
                "rarity": "Classified"
            },
            {
                "title": "AWP | Dragon Lore (Factory New)",
                "price": {"USD": 5000},
                "category": "Sniper Rifle",
                "rarity": "Covert"
            },
            {
                "title": "StatTrak™ M4A4 | Asiimov (Battle-Scarred)",
                "price": {"USD": 120},
                "category": "Rifle",
                "rarity": "Covert"
            }
        ]
        
        # Фильтр по цене
        filtered = apply_filters_to_items(items, "csgo", {"min_price": 100})
        assert len(filtered) == 2
        
        # Фильтр по категории
        filtered = apply_filters_to_items(items, "csgo", {"category": "Rifle"})
        assert len(filtered) == 2
        
        # Комбинированный фильтр
        filtered = apply_filters_to_items(
            items, 
            "csgo", 
            {"min_price": 100, "category": "Rifle"}
        )
        assert len(filtered) == 1
        assert filtered[0]["title"] == "StatTrak™ M4A4 | Asiimov (Battle-Scarred)"
        
    def test_build_api_params(self):
        """Тест создания параметров для API."""
        # Базовые параметры
        params = build_api_params_for_game(
            "csgo", 
            {"min_price": 50, "max_price": 100}
        )
        
        assert params["minPrice"] == 5000  # в центах
        assert params["maxPrice"] == 10000  # в центах
        assert params["gameId"] == "csgo"
        
        # CS2-специфичные параметры
        params = build_api_params_for_game(
            "csgo", 
            {
                "min_price": 50,
                "category": "Rifle",
                "stattrak": True,
                "exterior": "Field-Tested",
                "float_min": 0.15,
                "float_max": 0.37
            }
        )
        
        assert params["minPrice"] == 5000
        assert params["gameId"] == "csgo"
        assert params["category"] == "Rifle"
        assert params["statTrak"] == "true"
        assert params["exterior"] == "Field-Tested"
        assert params["floatMin"] == 0.15
        assert params["floatMax"] == 0.37


def test_filter_descriptions():
    """Тест человеко-читаемых описаний фильтров."""
    # Получаем фильтр для CS2/CSGO
    filter_obj = FilterFactory.get_filter("csgo")
    
    # Проверяем описание фильтров
    description = filter_obj.get_filter_description({
        "min_price": 50,
        "max_price": 100,
        "category": "Rifle",
        "rarity": "Classified",
        "stattrak": True
    })
    
    # Проверяем, что все компоненты фильтра присутствуют в описании
    assert "Price from $50.00" in description
    assert "Price to $100.00" in description
    assert "Category: Rifle" in description
    assert "Rarity: Classified" in description
    assert "StatTrak™" in description


if __name__ == "__main__":
    print("Запуск тестов для модуля game_filters...")
    
    # Запуск тестов с помощью pytest
    pytest.main(["-xvs", __file__])
