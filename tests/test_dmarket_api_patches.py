"""
Тестирование патчей для DMarket API.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.dmarket.dmarket_api_patches import apply_balance_patch


@patch('src.dmarket.dmarket_api_balance.apply_balance_patch')
def test_dmarket_api_patches_initialization(mock_apply_balance_patch):
    """
    Проверяет автоматическое применение патчей при импорте модуля.

    Тест проверяет, что при импорте dmarket_api_patches происходит
    вызов функции apply_balance_patch() из модуля dmarket_api_balance.
    """
    # Устанавливаем возвращаемое значение для мока
    mock_apply_balance_patch.return_value = True

    # Импортируем модуль заново, что вызовет выполнение apply_balance_patch()
    import importlib
    import src.dmarket.dmarket_api_patches
    importlib.reload(src.dmarket.dmarket_api_patches)

    # Проверяем, что функция была вызвана
    mock_apply_balance_patch.assert_called_once()
