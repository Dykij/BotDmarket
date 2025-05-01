"""
Модульные тесты для модуля пагинации.
"""

import pytest

from src.telegram_bot.pagination import PaginationManager, format_paginated_results


class TestPaginationManager:
    """Тесты для менеджера пагинации."""
    
    def setup_method(self):
        """Подготовка перед каждым тестом."""
        self.manager = PaginationManager()
        self.user_id = 12345
        
        # Тестовые данные
        self.test_items = [
            {"title": f"Item {i}", "price": {"amount": i * 100}, "profit": i * 10, "profit_percent": 10.0}
            for i in range(1, 21)  # 20 предметов
        ]
    
    def test_add_items_for_user(self):
        """Тест добавления предметов для пользователя."""
        self.manager.add_items_for_user(self.user_id, self.test_items, "test_mode")
        
        # Проверяем, что предметы добавлены
        assert len(self.manager.items_by_user.get(self.user_id, [])) == 20
        
        # Проверяем, что страница сброшена в 0
        assert self.manager.current_page_by_user.get(self.user_id) == 0
        
        # Проверяем, что режим установлен
        assert self.manager.mode_by_user.get(self.user_id) == "test_mode"
    
    def test_get_page_empty(self):
        """Тест получения страницы для пользователя без данных."""
        items, page, total = self.manager.get_page(self.user_id)
        
        assert items == []
        assert page == 0
        assert total == 0
    
    def test_get_page_with_items(self):
        """Тест получения страницы с данными."""
        self.manager.add_items_for_user(self.user_id, self.test_items, "test_mode")
        
        # Получаем первую страницу (по умолчанию 5 элементов на странице)
        items, page, total = self.manager.get_page(self.user_id)
        
        assert len(items) == 5
        assert items[0]["title"] == "Item 1"
        assert items[4]["title"] == "Item 5"
        assert page == 0
        assert total == 4  # 20 элементов / 5 = 4 страницы
    
    def test_next_page(self):
        """Тест перехода к следующей странице."""
        self.manager.add_items_for_user(self.user_id, self.test_items, "test_mode")
        
        # Переходим к следующей странице
        items, page, total = self.manager.next_page(self.user_id)
        
        assert len(items) == 5
        assert items[0]["title"] == "Item 6"
        assert page == 1
        assert total == 4
        
        # Переходим ещё на следующую страницу
        items, page, total = self.manager.next_page(self.user_id)
        
        assert len(items) == 5
        assert items[0]["title"] == "Item 11"
        assert page == 2
        assert total == 4
    
    def test_prev_page(self):
        """Тест перехода к предыдущей странице."""
        self.manager.add_items_for_user(self.user_id, self.test_items, "test_mode")
        
        # Переходим к следующей странице дважды
        self.manager.next_page(self.user_id)
        self.manager.next_page(self.user_id)
        
        # Проверяем, что мы на второй странице
        assert self.manager.current_page_by_user.get(self.user_id) == 2
        
        # Переходим к предыдущей странице
        items, page, total = self.manager.prev_page(self.user_id)
        
        assert len(items) == 5
        assert items[0]["title"] == "Item 6"
        assert page == 1
        assert total == 4
    
    def test_prev_page_at_start(self):
        """Тест перехода к предыдущей странице, когда мы на первой странице."""
        self.manager.add_items_for_user(self.user_id, self.test_items, "test_mode")
        
        # Переходим к предыдущей странице, хотя уже на первой
        items, page, total = self.manager.prev_page(self.user_id)
        
        # Должны остаться на первой странице
        assert len(items) == 5
        assert page == 0
        assert total == 4
    
    def test_next_page_at_end(self):
        """Тест перехода к следующей странице, когда мы на последней."""
        self.manager.add_items_for_user(self.user_id, self.test_items, "test_mode")
        
        # Переходим к последней странице
        for _ in range(3):
            self.manager.next_page(self.user_id)
        
        # Проверяем, что мы на последней странице
        assert self.manager.current_page_by_user.get(self.user_id) == 3
        
        # Пытаемся перейти ещё дальше
        items, page, total = self.manager.next_page(self.user_id)
        
        # Должны остаться на последней странице
        assert len(items) == 5
        assert page == 3
        assert total == 4
    
    def test_get_mode(self):
        """Тест получения режима для пользователя."""
        self.manager.add_items_for_user(self.user_id, self.test_items, "test_mode")
        
        mode = self.manager.get_mode(self.user_id)
        assert mode == "test_mode"
        
        # Для несуществующего пользователя должен быть режим по умолчанию
        mode = self.manager.get_mode(999999)
        assert mode == "default"


def test_format_paginated_results():
    """Тест форматирования результатов с пагинацией."""
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
    
    # С патчем для словаря GAMES в модуле arbitrage
    with pytest.MonkeyPatch.context() as mp:
        # Патчим модуль arbitrage, чтобы не зависеть от его реализации
        mp.setattr("src.dmarket.arbitrage.GAMES", {"csgo": "CS:GO"})
        
        result = format_paginated_results(items, "csgo", "boost", 0, 1)
        
        # Проверяем наличие основных элементов в результате
        assert "CS:GO" in result
        assert "Разгон баланса" in result
        assert "AK-47 | Redline" in result
        assert "AWP | Asiimov" in result
        assert "$10.00" in result  # Цена AK-47
        assert "$30.00" in result  # Цена AWP
        assert "$1.00" in result   # Прибыль AK-47
        assert "$3.00" in result   # Прибыль AWP
        assert "10.0%" in result   # Процент прибыли
        assert "Страница 1/1" in result
