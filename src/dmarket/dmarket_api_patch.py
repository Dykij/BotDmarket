"""
Патч для класса DMarketAPI, добавляющий метод получения баланса пользователя.
"""

from typing import Dict, Any
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

async def get_user_balance(self) -> Dict[str, Any]:
    """
    Получить баланс пользователя.
    
    Returns:
        Информация о балансе пользователя в формате {"usd": {"amount": value_in_cents}}
    """
    # Сначала пробуем новый эндпоинт из документации
    try:
        response = await self._request(
            "GET",
            "/v1/user/balance",
            params={}
        )
    except Exception as e:
        logger.debug(f"Ошибка при запросе /v1/user/balance: {str(e)}")
        # Если новый эндпоинт не работает, используем старый
        response = await self._request(
            "GET",
            "/account/v1/balance",
            params={}
        )
    
    # Проверяем и преобразуем ответ API к ожидаемому формату
    if response and isinstance(response, dict):
        # Проверяем наличие USD баланса в ответе API
        if "usd" in response:
            # Если формат уже соответствует ожидаемому
            return response
        
        # Если баланс в другом формате, преобразуем его
        if "balance" in response and isinstance(response["balance"], dict):
            usd_balance = response["balance"].get("usd", 0)
            return {"usd": {"amount": usd_balance}}
        
    # Возвращаем баланс по умолчанию, если нет данных или некорректный формат
    logger.warning("Не удалось получить корректные данные о балансе, возвращаем нулевой баланс")
    return {"usd": {"amount": 0}}

# Функция для применения патча
def apply_patch():
    """
    Применить патч к классу DMarketAPI.
    """
    from src.dmarket.dmarket_api import DMarketAPI
    
    # Добавляем метод в класс
    if not hasattr(DMarketAPI, 'get_user_balance') or not callable(getattr(DMarketAPI, 'get_user_balance', None)):
        logger.info("Применяем патч метода get_user_balance к классу DMarketAPI")
        DMarketAPI.get_user_balance = get_user_balance
    else:
        logger.info("Метод get_user_balance уже существует в классе DMarketAPI")
