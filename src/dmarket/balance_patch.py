"""
Инициализация патчей для DMarketAPI.
"""

from .dmarket_api_balance_fix import apply_balance_patch

# Автоматически применяем патч при импорте
apply_balance_patch()
