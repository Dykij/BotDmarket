"""Утилиты для работы с API DMarket в контексте Telegram бота.

Данный модуль предоставляет функции для инициализации и настройки
API клиента DMarket для использования в обработчиках бота.
"""

import logging
import os
from typing import Optional, Tuple

from src.dmarket.dmarket_api import DMarketAPI

logger = logging.getLogger(__name__)

def setup_api_client() -> Optional[DMarketAPI]:
    """Создает и настраивает экземпляр API-клиента DMarket.
    
    Использует переменные окружения DMARKET_PUBLIC_KEY и DMARKET_SECRET_KEY
    для инициализации клиента.
    
    Returns:
        Optional[DMarketAPI]: Настроенный API-клиент или None, если ключи не найдены
    """
    # Получение ключей API из переменных окружения
    public_key = os.environ.get("DMARKET_PUBLIC_KEY")
    secret_key = os.environ.get("DMARKET_SECRET_KEY")
    api_url = os.environ.get("DMARKET_API_URL", "https://api.dmarket.com")
    
    # Проверка наличия ключей
    if not public_key or not secret_key:
        logger.error("Ключи API DMarket не найдены в переменных окружения!")
        return None
    
    try:
        # Создание клиента с улучшенными параметрами
        api_client = DMarketAPI(
            public_key=public_key,
            secret_key=secret_key,
            api_url=api_url,
            max_retries=3,  # Повторные попытки при ошибках 
            connection_timeout=30.0,  # Таймаут соединения
            enable_cache=True,  # Включаем кэширование для уменьшения нагрузки
        )
        
        logger.info("API клиент DMarket успешно инициализирован")
        return api_client
    
    except Exception as e:
        logger.error(f"Ошибка при инициализации API клиента DMarket: {e}")
        return None

def setup_api_client_with_keys(public_key: str, secret_key: str) -> Optional[DMarketAPI]:
    """Создает API-клиент с заданными ключами.
    
    Args:
        public_key (str): Публичный ключ API DMarket
        secret_key (str): Секретный ключ API DMarket
        
    Returns:
        Optional[DMarketAPI]: Настроенный API-клиент или None при ошибке
    """
    if not public_key or not secret_key:
        logger.error("Переданы пустые ключи API DMarket")
        return None
    
    try:
        api_url = os.environ.get("DMARKET_API_URL", "https://api.dmarket.com")
        
        api_client = DMarketAPI(
            public_key=public_key,
            secret_key=secret_key,
            api_url=api_url,
            max_retries=3,
            connection_timeout=30.0,
            enable_cache=True,
        )
        
        logger.info("API клиент DMarket успешно инициализирован с пользовательскими ключами")
        return api_client
    
    except Exception as e:
        logger.error(f"Ошибка при инициализации API клиента DMarket с пользовательскими ключами: {e}")
        return None

async def validate_api_keys(public_key: str, secret_key: str) -> Tuple[bool, str]:
    """Проверяет валидность API ключей DMarket, пытаясь получить баланс.
    
    Args:
        public_key (str): Публичный ключ API DMarket
        secret_key (str): Секретный ключ API DMarket
        
    Returns:
        tuple[bool, str]: (успех, сообщение)
    """
    api_client = setup_api_client_with_keys(public_key, secret_key)
    
    if not api_client:
        return False, "Не удалось создать клиент API с предоставленными ключами"
    
    try:
        async with api_client:
            # Пробуем получить баланс для проверки работоспособности ключей
            balance = await api_client.get_balance()
            
            if "error" in balance and balance["error"]:
                error_message = balance.get("error_message", "Неизвестная ошибка")
                return False, f"Ошибка при проверке ключей API: {error_message}"
            
            # Успешная валидация
            return True, "Ключи API DMarket валидны"
    
    except Exception as e:
        logger.error(f"Ошибка при валидации ключей API: {e}")
        return False, f"Ошибка при проверке ключей API: {str(e)}"

# Экспортируем функции настройки API клиента
__all__ = ["setup_api_client", "setup_api_client_with_keys", "validate_api_keys"]
