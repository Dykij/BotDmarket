"""Модуль для исправления проблемы с отображением баланса Dmarket.
При импорте этого модуля автоматически применяется патч для исправления баланса.
"""

import logging

logger = logging.getLogger(__name__)

try:
    # Импорт и применение исправленного патча
    from src.dmarket.dmarket_api_balance_fix import apply_balance_patch

    # Применяем патч при импорте модуля
    apply_balance_patch()
    logger.info("Патч баланса Dmarket успешно применен")
except ImportError as e:
    logger.error(f"Не удалось применить патч баланса Dmarket: {e}")
except Exception as e:
    logger.error(f"Ошибка при применении патча баланса Dmarket: {e}")
