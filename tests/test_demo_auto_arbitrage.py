"""
Тестирование демонстрационного модуля автоматического арбитража.
"""

import pytest
from unittest.mock import patch, MagicMock
import random

from src.demo_auto_arbitrage import (
    generate_random_items,
    arbitrage_boost,
    arbitrage_mid,
    arbitrage_pro,
    auto_arbitrage_demo,
    main
)


@patch("random.randint")
@patch("random.uniform")
@patch("random.choice")
def test_generate_random_items(mock_choice, mock_uniform, mock_randint):
    """
    Проверяет корректность генерации случайных предметов.
    """
    # Настраиваем моки для предсказуемых результатов
    mock_choice.side_effect = ["AK-47", "Редкий", "Красный"]
    mock_randint.return_value = 500
    mock_uniform.return_value = 10.0

    # Вызываем тестируемую функцию
    items = generate_random_items("csgo", count=1)

    # Проверяем результат
    assert len(items) == 1
    item = items[0]
    assert item["title"] == "Редкий AK-47 | Красный"
    assert item["buyPrice"] == 500
    assert item["profit"] == 50  # 10% от 500
    assert item["profitPercent"] == 10.0
    assert item["gameId"] == "csgo"


def test_arbitrage_boost():
    """
    Проверяет фильтрацию предметов для режима Boost.
    """
    # Создаем тестовые данные
    test_items = [
        {"buyPrice": 300, "profitPercent": 6.0},  # подходит
        {"buyPrice": 400, "profitPercent": 5.0},  # подходит
        {"buyPrice": 600, "profitPercent": 7.0},  # не подходит (цена > 500)
        {"buyPrice": 200, "profitPercent": 4.0}   # не подходит (прибыль < 5.0%)
    ]

    # Мокаем функцию generate_random_items
    with patch("src.demo_auto_arbitrage.generate_random_items", return_value=test_items):
        # Вызываем тестируемую функцию
        result = arbitrage_boost("csgo")

        # Проверяем результат
        assert len(result) == 2
        assert result[0]["buyPrice"] == 300
        assert result[1]["buyPrice"] == 400


def test_arbitrage_mid():
    """
    Проверяет фильтрацию предметов для режима Mid.
    """
    # Создаем тестовые данные
    test_items = [
        {"buyPrice": 600, "profitPercent": 11.0},  # подходит
        {"buyPrice": 1500, "profitPercent": 10.0},  # подходит
        {"buyPrice": 400, "profitPercent": 15.0},   # не подходит (цена < 500)
        {"buyPrice": 1000, "profitPercent": 9.0},   # не подходит (прибыль < 10.0%)
        {"buyPrice": 2500, "profitPercent": 12.0}   # не подходит (цена > 2000)
    ]

    # Мокаем функцию generate_random_items
    with patch("src.demo_auto_arbitrage.generate_random_items", return_value=test_items):
        # Вызываем тестируемую функцию
        result = arbitrage_mid("csgo")

        # Проверяем результат
        assert len(result) == 2
        assert result[0]["buyPrice"] == 600
        assert result[1]["buyPrice"] == 1500


def test_arbitrage_pro():
    """
    Проверяет фильтрацию предметов для режима Pro.
    """
    # Создаем тестовые данные
    test_items = [
        {"buyPrice": 2500, "profitPercent": 16.0},  # подходит
        {"buyPrice": 3000, "profitPercent": 15.0},  # подходит
        {"buyPrice": 1800, "profitPercent": 20.0},  # не подходит (цена < 2000)
        {"buyPrice": 2200, "profitPercent": 14.0}   # не подходит (прибыль < 15.0%)
    ]

    # Мокаем функцию generate_random_items
    with patch("src.demo_auto_arbitrage.generate_random_items", return_value=test_items):
        # Вызываем тестируемую функцию
        result = arbitrage_pro("csgo")

        # Проверяем результат
        assert len(result) == 2
        assert result[0]["buyPrice"] == 2500
        assert result[1]["buyPrice"] == 3000


@pytest.mark.asyncio
@patch("src.demo_auto_arbitrage.arbitrage_boost")
@patch("src.demo_auto_arbitrage.arbitrage_mid")
@patch("src.demo_auto_arbitrage.arbitrage_pro")
@patch("src.demo_auto_arbitrage.logger")
@patch("asyncio.sleep")
async def test_auto_arbitrage_demo_low_mode(
    mock_sleep, mock_logger, mock_pro, mock_mid, mock_boost
):
    """
    Тестирует демонстрацию автоматического арбитража в режиме low.
    """
    # Настраиваем моки
    mock_boost.return_value = [
        {"title": "Тест 1", "buyPrice": 300, "profit": 30, "profitPercent": 10.0}
    ]
    mock_sleep.return_value = None

    # Вызываем тестируемую функцию
    await auto_arbitrage_demo(game="csgo", mode="low", iterations=2)

    # Проверяем, что правильный арбитражный режим был вызван
    mock_boost.assert_called_with("csgo")
    mock_mid.assert_not_called()
    mock_pro.assert_not_called()

    # Проверяем количество вызовов
    assert mock_boost.call_count == 2
    assert mock_sleep.call_count == 2


@pytest.mark.asyncio
@patch("src.demo_auto_arbitrage.arbitrage_boost")
@patch("src.demo_auto_arbitrage.arbitrage_mid")
@patch("src.demo_auto_arbitrage.arbitrage_pro")
@patch("src.demo_auto_arbitrage.logger")
@patch("asyncio.sleep")
async def test_auto_arbitrage_demo_medium_mode(
    mock_sleep, mock_logger, mock_pro, mock_mid, mock_boost
):
    """
    Тестирует демонстрацию автоматического арбитража в режиме medium.
    """
    # Настраиваем моки
    mock_mid.return_value = [
        {"title": "Тест 1", "buyPrice": 1000, "profit": 100, "profitPercent": 10.0}
    ]
    mock_sleep.return_value = None

    # Вызываем тестируемую функцию
    await auto_arbitrage_demo(game="csgo", mode="medium", iterations=1)

    # Проверяем, что правильный арбитражный режим был вызван
    mock_mid.assert_called_with("csgo")
    mock_boost.assert_not_called()
    mock_pro.assert_not_called()


@pytest.mark.asyncio
@patch("src.demo_auto_arbitrage.arbitrage_boost")
@patch("src.demo_auto_arbitrage.arbitrage_mid")
@patch("src.demo_auto_arbitrage.arbitrage_pro")
@patch("src.demo_auto_arbitrage.logger")
@patch("asyncio.sleep")
async def test_auto_arbitrage_demo_high_mode(
    mock_sleep, mock_logger, mock_pro, mock_mid, mock_boost
):
    """
    Тестирует демонстрацию автоматического арбитража в режиме high.
    """
    # Настраиваем моки
    mock_pro.return_value = [
        {"title": "Тест 1", "buyPrice": 2500, "profit": 500, "profitPercent": 20.0}
    ]
    mock_sleep.return_value = None

    # Вызываем тестируемую функцию
    await auto_arbitrage_demo(game="csgo", mode="high", iterations=1)

    # Проверяем, что правильный арбитражный режим был вызван
    mock_pro.assert_called_with("csgo")
    mock_boost.assert_not_called()
    mock_mid.assert_not_called()


@pytest.mark.asyncio
@patch("src.demo_auto_arbitrage.auto_arbitrage_demo")
@patch("builtins.print")
async def test_main(mock_print, mock_auto_arbitrage_demo):
    """
    Тестирует основную функцию main.
    """
    # Настраиваем мок
    mock_auto_arbitrage_demo.return_value = None

    # Вызываем тестируемую функцию
    await main()

    # Проверяем, что auto_arbitrage_demo вызывается с правильными параметрами
    assert mock_auto_arbitrage_demo.call_count == 6  # 2 игры * 3 режима

    # Проверяем вызовы для разных игр и режимов
    mock_auto_arbitrage_demo.assert_any_call(game="csgo", mode="low", iterations=3)
    mock_auto_arbitrage_demo.assert_any_call(game="csgo", mode="medium", iterations=3)
    mock_auto_arbitrage_demo.assert_any_call(game="csgo", mode="high", iterations=3)
    mock_auto_arbitrage_demo.assert_any_call(game="dota2", mode="low", iterations=3)
    mock_auto_arbitrage_demo.assert_any_call(game="dota2", mode="medium", iterations=3)
    mock_auto_arbitrage_demo.assert_any_call(game="dota2", mode="high", iterations=3)
