"""
Модуль содержит конфигурационные функции для организации тестов по категориям.
Это помогает более эффективно запускать тесты соответствующих компонентов.
"""

import pytest

def pytest_configure(config):
    """Добавляет пользовательские маркеры для категоризации тестов."""
    config.addinivalue_line("markers", "bot: тесты функциональности Telegram бота")
    config.addinivalue_line("markers", "api: тесты DMarket API")
    config.addinivalue_line("markers", "arbitrage: тесты арбитражной логики")
    config.addinivalue_line("markers", "integration: интеграционные тесты")
    config.addinivalue_line("markers", "unit: модульные тесты")
