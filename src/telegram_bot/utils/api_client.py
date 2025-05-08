"""
Утилиты для работы с DMarket API.

Этот модуль содержит функции для настройки и инициализации API клиента DMarket.
"""

import os
import logging
from typing import Optional

from src.dmarket.dmarket_api_fixed import DMarketAPI

logger = logging.getLogger(__name__)

def setup_api_client() -> Optional[DMarketAPI]:
    """
    Настраивает API-клиент DMarket с ключами из окружения.
    
    Returns:
        DMarketAPI: Настроенный API-клиент или None в случае ошибки
    """
    # API ключи из переменных окружения
    dmarket_api_key = os.environ.get("DMARKET_PUBLIC_KEY", "")
    dmarket_api_secret = os.environ.get("DMARKET_SECRET_KEY", "")
    
    # Проверка ключей API
    if not dmarket_api_key or not dmarket_api_secret:
        logger.error("API ключи DMarket не настроены!")
        return None
    
    try:
        # Создание клиента с ключами
        api_client = DMarketAPI(
            public_key=dmarket_api_key,
            secret_key=dmarket_api_secret,
            api_url=os.environ.get("DMARKET_API_URL", "https://api.dmarket.com"),
            max_retries=3
        )
        logger.info("API клиент DMarket успешно инициализирован")
        return api_client
        
    except Exception as e:
        logger.error(f"Ошибка при создании API клиента: {e}")
        return None

# Экспортируем функцию настройки API клиента
__all__ = ['setup_api_client'] 