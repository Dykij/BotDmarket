"""Тесты для функций внутрирыночного арбитража."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dmarket.intramarket_arbitrage import (
    PriceAnomalyType,
    _calculate_similarity_score,
    _extract_item_properties,
    find_mispriced_rare_items,
    find_price_anomalies,
    find_trending_items,
    scan_for_intramarket_opportunities,
)


class TestItemProperties:
    """Тесты для функций работы со свойствами предметов."""

    def test_extract_properties_basic(self):
        """Тест извлечения базовых свойств предмета."""
        item = {
            "title": "AK-47 | Redline",
            "extra": {
                "categoryPath": "Rifle",
                "rarity": "Classified",
                "exterior": "Field-Tested",
            },
        }

        props = _extract_item_properties(item)

        assert props["name"] == "AK-47 | Redline"
        assert props["category"] == "Rifle"
        assert props["rarity"] == "Classified"
        assert props["exterior"] == "Field-Tested"

    def test_extract_properties_with_missing_fields(self):
        """Тест извлечения свойств с отсутствующими полями."""
        item = {
            "title": "AK-47 | Redline",
            "extra": {
                "rarity": "Classified",
            },
        }

        props = _extract_item_properties(item)

        assert props["name"] == "AK-47 | Redline"
        assert props["category"] == ""
        assert props["rarity"] == "Classified"
        assert props["exterior"] == ""

    def test_extract_properties_with_stickers(self):
        """Тест извлечения свойств предмета со стикерами."""
        item = {
            "title": "AK-47 | Redline",
            "extra": {
                "stickers": [
                    {"name": "Sticker 1"},
                    {"name": "Sticker 2"},
                ],
            },
        }

        props = _extract_item_properties(item)

        assert "stickers" in props
        assert len(props["stickers"]) == 2
        assert props["stickers"][0]["name"] == "Sticker 1"

    def test_extract_properties_with_pattern_and_float(self):
        """Тест извлечения паттерна и float value."""
        item = {
            "title": "AK-47 | Case Hardened",
            "extra": {
                "patternIndex": "661",
                "floatValue": "0.0123",
            },
        }

        props = _extract_item_properties(item)

        assert "pattern_index" in props
        assert props["pattern_index"] == "661"
        assert "float_value" in props
        assert props["float_value"] == "0.0123"


class TestSimilarityScore:
    """Тесты для функции расчета схожести предметов."""

    def test_identical_items(self):
        """Тест на полностью идентичные предметы."""
        item1 = {
            "title": "AK-47 | Redline",
            "extra": {
                "categoryPath": "Rifle",
                "rarity": "Classified",
                "exterior": "Field-Tested",
            },
        }

        item2 = {
            "title": "AK-47 | Redline",
            "extra": {
                "categoryPath": "Rifle",
                "rarity": "Classified",
                "exterior": "Field-Tested",
            },
        }

        score = _calculate_similarity_score(item1, item2)
        assert score == 1.0

    def test_different_items(self):
        """Тест на совершенно разные предметы."""
        item1 = {
            "title": "AK-47 | Redline",
            "extra": {
                "categoryPath": "Rifle",
                "rarity": "Classified",
                "exterior": "Field-Tested",
            },
        }

        item2 = {
            "title": "AWP | Asiimov",
            "extra": {
                "categoryPath": "Sniper Rifle",
                "rarity": "Covert",
                "exterior": "Battle-Scarred",
            },
        }

        score = _calculate_similarity_score(item1, item2)
        assert score < 0.5  # Должна быть низкая схожесть

    def test_same_item_different_float(self):
        """Тест на одинаковые предметы с разным float value."""
        item1 = {
            "title": "AK-47 | Redline",
            "extra": {
                "categoryPath": "Rifle",
                "rarity": "Classified",
                "exterior": "Field-Tested",
                "floatValue": "0.15",
            },
        }

        item2 = {
            "title": "AK-47 | Redline",
            "extra": {
                "categoryPath": "Rifle",
                "rarity": "Classified",
                "exterior": "Field-Tested",
                "floatValue": "0.35",
            },
        }

        score = _calculate_similarity_score(item1, item2)
        assert score > 0.7  # Должна быть высокая схожесть, но не 1.0
        assert score < 1.0

    def test_same_item_different_stickers(self):
        """Тест на одинаковые предметы с разными стикерами."""
        item1 = {
            "title": "AK-47 | Redline",
            "extra": {
                "categoryPath": "Rifle",
                "rarity": "Classified",
                "exterior": "Field-Tested",
                "stickers": [
                    {"name": "Sticker 1"},
                    {"name": "Sticker 2"},
                ],
            },
        }

        item2 = {
            "title": "AK-47 | Redline",
            "extra": {
                "categoryPath": "Rifle",
                "rarity": "Classified",
                "exterior": "Field-Tested",
                "stickers": [
                    {"name": "Sticker 3"},
                    {"name": "Sticker 4"},
                ],
            },
        }

        score = _calculate_similarity_score(item1, item2)
        assert score > 0.7  # Должна быть высокая схожесть, но не 1.0
        assert score < 1.0


@pytest.mark.asyncio
class TestPriceAnomalies:
    """Тесты для функций поиска ценовых аномалий."""

    @patch("src.dmarket.intramarket_arbitrage.DMarketAPI")
    async def test_find_price_anomalies(self, mock_api):
        """Тест поиска ценовых аномалий."""
        # Настройка мока API
        api_instance = MagicMock()
        mock_api.return_value = api_instance

        # Создаем тестовые данные - два одинаковых предмета с разной ценой
        item1 = {
            "itemId": "item1",
            "title": "AK-47 | Redline",
            "price": {"amount": 1000},  # $10.00
            "extra": {
                "categoryPath": "Rifle",
                "rarity": "Classified",
                "exterior": "Field-Tested",
            },
        }

        item2 = {
            "itemId": "item2",
            "title": "AK-47 | Redline",
            "price": {"amount": 1500},  # $15.00
            "extra": {
                "categoryPath": "Rifle",
                "rarity": "Classified",
                "exterior": "Field-Tested",
            },
        }

        # Настраиваем возвращаемые значения для API
        api_instance.get_market_items.side_effect = [
            {"items": [item1, item2]},  # Первый вызов
            {"items": []},  # Последующие вызовы - пустые результаты
            {"items": []},
            {"items": []},
            {"items": []},
        ]

        # Отключаем реальную задержку
        with patch("asyncio.sleep", new=AsyncMock()):
            # Вызываем тестируемую функцию
            results = await find_price_anomalies(
                game="csgo",
                similarity_threshold=0.9,
                price_diff_percent=10,
                max_results=10,
                dmarket_api=api_instance,
            )

        # Проверяем, что найдена ценовая аномалия
        assert len(results) > 0
        assert results[0]["type"] == PriceAnomalyType.UNDERPRICED
        assert results[0]["item_to_buy"]["itemId"] == "item1"
        assert results[0]["item_to_sell"]["itemId"] == "item2"
        assert results[0]["buy_price"] == 10.0
        assert results[0]["sell_price"] == 15.0


@pytest.mark.asyncio
class TestTrendingItems:
    """Тесты для функций поиска предметов с растущей ценой."""

    @patch("src.dmarket.intramarket_arbitrage.DMarketAPI")
    @patch("src.dmarket.intramarket_arbitrage.get_sales_history_for_game")
    async def test_find_trending_items(self, mock_history, mock_api):
        """Тест поиска предметов с растущей ценой."""
        # Настройка моков
        api_instance = MagicMock()
        mock_api.return_value = api_instance

        # Создаем тестовые данные
        item1 = {
            "itemId": "item1",
            "title": "AK-47 | Redline",
            "price": {"amount": 1500},  # $15.00
        }

        # Настраиваем историю продаж - цена растет
        sales_history = {
            "AK-47 | Redline": [
                # Ранние продажи (низкие цены)
                {"price": 10.0, "date": "2023-01-01"},
                {"price": 10.5, "date": "2023-01-02"},
                {"price": 11.0, "date": "2023-01-03"},
                {"price": 11.2, "date": "2023-01-04"},
                {"price": 11.5, "date": "2023-01-05"},
                # Поздние продажи (высокие цены)
                {"price": 12.0, "date": "2023-01-06"},
                {"price": 12.5, "date": "2023-01-07"},
                {"price": 13.0, "date": "2023-01-08"},
                {"price": 13.5, "date": "2023-01-09"},
                {"price": 14.0, "date": "2023-01-10"},
            ],
        }

        mock_history.return_value = sales_history

        # Настраиваем возвращаемые значения для API
        api_instance.get_market_items.side_effect = [
            {"items": [item1]},  # Первый вызов
            {"items": []},  # Последующие вызовы - пустые результаты
            {"items": []},
            {"items": []},
            {"items": []},
        ]

        # Отключаем реальную задержку
        with patch("asyncio.sleep", new=AsyncMock()):
            # Вызываем тестируемую функцию
            results = await find_trending_items(
                game="csgo",
                max_results=10,
                dmarket_api=api_instance,
            )

        # Проверяем, что найден предмет с растущей ценой
        assert len(results) > 0
        assert results[0]["type"] == PriceAnomalyType.TRENDING_UP
        assert results[0]["item"]["itemId"] == "item1"
        assert results[0]["current_price"] == 15.0
        assert results[0]["price_change_percent"] > 0  # Процент изменения должен быть положительным


@pytest.mark.asyncio
class TestRareItems:
    """Тесты для функций поиска редких предметов."""

    @patch("src.dmarket.intramarket_arbitrage.DMarketAPI")
    async def test_find_mispriced_rare_items(self, mock_api):
        """Тест поиска редких предметов с неправильной оценкой."""
        # Настройка мока API
        api_instance = MagicMock()
        mock_api.return_value = api_instance

        # Создаем тестовые данные - предмет с редким паттерном
        rare_item = {
            "itemId": "item1",
            "title": "AK-47 | Case Hardened",
            "price": {"amount": 5000},  # $50.00
            "extra": {
                "patternIndex": "387",  # Blue Gem
                "floatValue": "0.09",
            },
        }

        # Настраиваем возвращаемые значения для API
        api_instance.get_market_items.side_effect = [
            {"items": [rare_item]},  # Первый вызов
            {"items": []},  # Последующие вызовы - пустые результаты
            {"items": []},
            {"items": []},
        ]

        # Отключаем реальную задержку
        with patch("asyncio.sleep", new=AsyncMock()):
            # Вызываем тестируемую функцию
            results = await find_mispriced_rare_items(
                game="csgo",
                max_results=10,
                dmarket_api=api_instance,
            )

        # Проверяем, что найден редкий предмет
        assert len(results) > 0
        assert results[0]["type"] == PriceAnomalyType.RARE_TRAITS
        assert results[0]["item"]["itemId"] == "item1"
        assert "Blue Gem" in str(results[0]["rare_traits"])
        assert results[0]["current_price"] == 50.0
        assert results[0]["estimated_value"] > 50.0  # Оценочная стоимость должна быть выше текущей


@pytest.mark.asyncio
class TestIntegration:
    """Интеграционные тесты для функций внутрирыночного арбитража."""

    @patch("src.dmarket.intramarket_arbitrage.find_price_anomalies")
    @patch("src.dmarket.intramarket_arbitrage.find_trending_items")
    @patch("src.dmarket.intramarket_arbitrage.find_mispriced_rare_items")
    async def test_scan_for_intramarket_opportunities(
        self, mock_rare, mock_trending, mock_anomalies
    ):
        """Тест комплексного сканирования внутрирыночных возможностей."""
        # Настраиваем моки возвращаемых результатов
        mock_anomalies.return_value = [{"type": PriceAnomalyType.UNDERPRICED, "game": "csgo"}]
        mock_trending.return_value = [{"type": PriceAnomalyType.TRENDING_UP, "game": "csgo"}]
        mock_rare.return_value = [{"type": PriceAnomalyType.RARE_TRAITS, "game": "csgo"}]

        # Вызываем тестируемую функцию
        results = await scan_for_intramarket_opportunities(
            games=["csgo"],
            max_results_per_game=5,
        )

        # Проверяем результаты
        assert "csgo" in results
        assert "price_anomalies" in results["csgo"]
        assert "trending_items" in results["csgo"]
        assert "rare_mispriced" in results["csgo"]

        # Проверяем, что каждая функция была вызвана с правильными параметрами
        mock_anomalies.assert_awaited_once()
        mock_trending.assert_awaited_once()
        mock_rare.assert_awaited_once()
