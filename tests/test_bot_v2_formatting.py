"""
Тесты для функций форматирования результатов в модуле bot_v2.
"""

import pytest
from unittest.mock import patch


def test_format_dmarket_results_empty():
    """Тест форматирования пустых результатов."""
    from src.telegram_bot.bot_v2 import format_dmarket_results
    
    # Тест с пустыми результатами
    results = []
    mode = "boost"
    game = "csgo"
    
    formatted_text = format_dmarket_results(results, mode, game)
    
    assert "не найдено" in formatted_text.lower()
    assert "Разгон баланса" in formatted_text
    assert "CS2" in formatted_text


def test_format_dmarket_results_with_data():
    """Тест форматирования результатов с данными."""
    from src.telegram_bot.bot_v2 import format_dmarket_results
    
    # Тестовые данные
    results = [
        {
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {"amount": 1000},
            "profit": 100
        },
        {
            "title": "AWP | Asiimov (Field-Tested)",
            "price": {"amount": 3000},
            "profit": 300
        }
    ]
    mode = "mid"
    game = "csgo"
    
    # Патчим GAMES, чтобы не зависеть от его реализации
    with patch("src.telegram_bot.bot_v2.GAMES", {"csgo": "CS:GO"}):
        formatted_text = format_dmarket_results(results, mode, game)
    
    # Проверяем, что результаты отформатированы правильно
    assert "Средний трейдер" in formatted_text
    assert "CS:GO" in formatted_text
    assert "AK-47 | Redline" in formatted_text
    assert "AWP | Asiimov" in formatted_text
    assert "$10.00" in formatted_text  # Цена первого предмета
    assert "$1.00" in formatted_text  # Прибыль первого предмета
    assert "$30.00" in formatted_text  # Цена второго предмета
    assert "$3.00" in formatted_text  # Прибыль второго предмета


def test_format_best_opportunities():
    """Тест форматирования лучших арбитражных возможностей."""
    from src.telegram_bot.bot_v2 import format_best_opportunities
    
    # Тестовые данные
    opportunities = [
        {
            "title": "AK-47 | Redline (Field-Tested)",
            "buyPrice": 1000,
            "sellPrice": 1100,
            "profit": 100,
            "profitPercent": 10.0
        },
        {
            "title": "AWP | Asiimov (Field-Tested)",
            "buyPrice": 3000,
            "sellPrice": 3300,
            "profit": 300,
            "profitPercent": 10.0
        }
    ]
    game = "csgo"
    
    # Патчим GAMES, чтобы не зависеть от его реализации
    with patch("src.telegram_bot.bot_v2.GAMES", {"csgo": "CS:GO"}):
        formatted_text = format_best_opportunities(opportunities, game)
    
    # Проверяем, что результаты отформатированы правильно
    assert "Лучшие арбитражные возможности" in formatted_text
    assert "CS:GO" in formatted_text
    assert "AK-47 | Redline" in formatted_text
    assert "AWP | Asiimov" in formatted_text
    assert "$10.00" in formatted_text  # Цена покупки первого предмета
    assert "$11.00" in formatted_text  # Цена продажи первого предмета
    assert "$1.00" in formatted_text  # Прибыль первого предмета
    assert "10.0%" in formatted_text  # Процент прибыли первого предмета
