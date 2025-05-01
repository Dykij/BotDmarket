"""
Тесты для функции format_paginated_results в модуле bot_v2.
"""

import pytest
import asyncio
from unittest.mock import patch


@pytest.mark.asyncio
async def test_format_paginated_results_empty():
    """Тест форматирования пустых результатов с пагинацией."""
    # Импортируем функцию непосредственно из модуля auto_arbitrage
    from src.telegram_bot.auto_arbitrage import format_results
    
    # Тестовые данные
    items = []
    game = "csgo"
    mode = "auto_boost"
    
    # Патчим GAMES, чтобы не зависеть от его реализации
    with patch("src.telegram_bot.auto_arbitrage.GAMES", {"csgo": "CS2"}):
        formatted_text = await format_results(items, mode, game)
    
    # Проверки
    assert "не найдено" in formatted_text.lower() or "нет данных" in formatted_text.lower()
    assert "CS2" in formatted_text
    assert "Страница" in formatted_text
    assert "0/0" in formatted_text


@pytest.mark.asyncio
async def test_format_paginated_results_with_data():
    """Тест форматирования результатов с данными и пагинацией."""
    # Импортируем функцию непосредственно из модуля auto_arbitrage
    from src.telegram_bot.auto_arbitrage import format_results
    
    # Тестовые данные
    items = [
        {
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {"amount": 1000},
            "profit": 100,
            "profit_percent": 10.0
        },
        {
            "title": "AWP | Asiimov (Field-Tested)",
            "price": {"amount": 3000},
            "profit": 300,
            "profit_percent": 10.0
        }
    ]
    game = "csgo"
    mode = "auto_medium"
    
    # Патчим GAMES, чтобы не зависеть от его реализации
    with patch("src.telegram_bot.auto_arbitrage.GAMES", {"csgo": "CS2"}):
        formatted_text = await format_results(items, mode, game)
    
    # Проверки
    assert "Средний трейдер" in formatted_text
    assert "CS2" in formatted_text
    assert "AK-47 | Redline" in formatted_text
    assert "AWP | Asiimov" in formatted_text
    assert "$10.00" in formatted_text  # Цена первого предмета
    assert "$1.00" in formatted_text  # Прибыль первого предмета
    assert "$30.00" in formatted_text  # Цена второго предмета
    assert "$3.00" in formatted_text  # Прибыль второго предмета
    assert "Страница 2/3" in formatted_text  # Страницы отображаются с +1


def test_pagination_manager():
    """Тест менеджера пагинации."""
    # Импортируем менеджер пагинации
    from src.telegram_bot.pagination import PaginationManager
    
    # Создаем экземпляр менеджера
    manager = PaginationManager()
    
    # Тестовые данные
    user_id = 12345
    test_items = [
        {"title": f"Item {i}", "price": {"amount": i * 100}, "profit": i * 10, "profit_percent": 10.0}
        for i in range(1, 21)  # 20 предметов
    ]
    mode = "auto_medium"
    
    # Добавляем предметы
    manager.add_items_for_user(user_id, test_items, mode)
    
    # Проверяем, что предметы добавлены и страница сброшена в 0
    assert len(manager.items_by_user.get(user_id, [])) == 20
    assert manager.current_page_by_user.get(user_id) == 0
    assert manager.mode_by_user.get(user_id) == mode
    
    # Проверяем получение первой страницы (5 элементов)
    items, page, total = manager.get_page(user_id)
    assert len(items) == 5
    assert items[0]["title"] == "Item 1"
    assert items[-1]["title"] == "Item 5"
    assert page == 0
    assert total == 4  # 20 предметов / 5 = 4 страницы
    
    # Проверяем переход к следующей странице
    items, page, total = manager.next_page(user_id)
    assert len(items) == 5
    assert items[0]["title"] == "Item 6"
    assert page == 1
    assert total == 4
    
    # Проверяем переход к предыдущей странице
    items, page, total = manager.prev_page(user_id)
    assert len(items) == 5
    assert items[0]["title"] == "Item 1"
    assert page == 0
    assert total == 4
    
    # Проверяем получение режима
    mode_value = manager.get_mode(user_id)
    assert mode_value == mode
