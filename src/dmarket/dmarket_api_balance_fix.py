"""
Патч для исправления эндпоинта баланса в DMarket API.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def patched_get_user_balance(self) -> Dict[str, Any]:
    """
    Получить баланс пользователя DMarket с использованием правильного эндпоинта.
    
    Returns:
        Информация о балансе в формате {"usd": {"amount": value_in_cents}}
    """
    logger.debug("Запрос баланса пользователя DMarket через патч")
    # Сначала пробуем новый эндпоинт из документации
    try:
        logger.info("Пробуем получить баланс через новый эндпоинт /v1/user/balance")
        response = await self._request(
            "GET",
            "/v1/user/balance",
            params={}
        )
        logger.debug(f"Ответ нового API баланса: {response}")
    except Exception as e:
        logger.warning(f"Ошибка при запросе /v1/user/balance: {str(e)}")
        # Если новый эндпоинт не работает, используем старый
        logger.info("Пробуем получить баланс через старый эндпоинт /account/v1/balance")
        response = await self._request(
            "GET",
            "/account/v1/balance",
            params={}
        )
        logger.debug(f"Ответ старого API баланса: {response}")
    
    # Проверяем и преобразуем ответ API к ожидаемому формату
    if response and isinstance(response, dict):
        # Проверяем наличие USD баланса в ответе API
        if "usd" in response:
            try:
                # Если это строка, конвертируем в число
                if isinstance(response["usd"], str):
                    usd_value = float(response["usd"]) * 100  # преобразуем в центы
                    logger.info(f"Баланс из строки: {response['usd']} -> {usd_value} центов")
                    return {"usd": {"amount": usd_value}}
                # Если это число
                elif isinstance(response["usd"], (int, float)):
                    usd_value = float(response["usd"]) * 100  # преобразуем в центы
                    logger.info(f"Баланс из числа: {response['usd']} -> {usd_value} центов")
                    return {"usd": {"amount": usd_value}}
                # Если это уже нужный формат с вложенным объектом
                elif isinstance(response["usd"], dict) and "amount" in response["usd"]:
                    logger.info(f"Баланс (правильный формат): {response['usd']['amount']} центов")
                    return response
            except (ValueError, TypeError) as e:
                logger.error(f"Ошибка преобразования баланса: {e}")
        
        # Если баланс в другом формате, преобразуем его
        if "balance" in response and isinstance(response["balance"], dict):
            usd_balance = response["balance"].get("usd", 0)
            logger.info(f"Баланс из поля balance: {usd_balance} центов")
            return {"usd": {"amount": usd_balance}}
            
        # Если есть поле usdAvailableToWithdraw (из документации)
        if "usdAvailableToWithdraw" in response:
            try:
                usd_value = float(response["usdAvailableToWithdraw"]) * 100
                logger.info(f"Баланс из usdAvailableToWithdraw: {usd_value} центов")
                return {"usd": {"amount": usd_value}}
            except (ValueError, TypeError) as e:
                logger.error(f"Ошибка преобразования usdAvailableToWithdraw: {e}")
    
    # Если все проверки не прошли, возвращаем нулевой баланс
    logger.warning(f"Не удалось получить корректные данные о балансе: {response}")
    return {"usd": {"amount": 0}}

def apply_balance_patch():
    """
    Применяет патч метода get_user_balance к классу DMarketAPI.
    """
    from src.dmarket.dmarket_api import DMarketAPI
    
    logger.info("Применяем патч для исправления эндпоинта баланса в DMarketAPI")
    # Заменяем метод на нашу версию
    DMarketAPI.get_user_balance = patched_get_user_balance
    logger.info("Патч успешно применен")
    return True
