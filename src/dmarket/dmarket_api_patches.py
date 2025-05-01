"""
Инициализация патча для DMarketAPI.
"""

from .dmarket_api_balance import apply_balance_patch

# Автоматически применяем патч при импорте
apply_balance_patch()
