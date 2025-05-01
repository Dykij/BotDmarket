"""
Патч для добавления поддержки метода get_user_balance в DMarketAPI.
"""

import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

async def get_user_balance(self) -> Dict[str, Any]:
    """
    Получить баланс пользователя DMarket.
    
    Returns:
        Информация о балансе в формате {"usd": {"amount": value_in_cents}}
    """
    logger.debug("Запрос баланса пользователя DMarket")
    response = await self._request(
        "GET",
        "/account/v1/balance",
        params={}
    )
    
    logger.debug(f"Ответ API баланса: {response}")
    
    # Проверяем на ошибки API
    if isinstance(response, dict) and "error" in response:
        error_code = "unknown"
        error_message = response.get("error", "Неизвестная ошибка")
        
        # Пытаемся извлечь детали ошибки, если они есть
        if "details" in response:
            try:
                # Детали ошибки могут быть в строковом JSON формате
                details = response["details"]
                if isinstance(details, str):
                    details_dict = json.loads(details)
                    if isinstance(details_dict, dict):
                        error_code = details_dict.get("code", error_code)
                        error_message = details_dict.get("message", error_message)
            except Exception as e:
                logger.debug(f"Не удалось разобрать детали ошибки: {e}")
        
        logger.error(f"Ошибка DMarket API при получении баланса: {error_code} - {error_message}")
        return {"usd": {"amount": 0}}
    
    # Проверяем и преобразуем ответ API к ожидаемому формату
    if response and isinstance(response, dict):
        # Проверка на ошибку авторизации
        if response.get("code") == "InvalidToken" or response.get("code") == "Unauthorized":
            logger.error(f"Ошибка авторизации: {response.get('message', 'Доступ запрещен')}")
            return {"usd": {"amount": 0}}
        
        # Проверяем наличие USD баланса в ответе API согласно документации
        # Документация указывает на формат {"usd": "5.00"}
        if "usd" in response:
            try:
                # Если это строка, конвертируем в число
                if isinstance(response["usd"], str):
                    usd_value = float(response["usd"]) * 100  # преобразуем в центы
                    logger.info(f"Баланс (из строки): {response['usd']} -> {usd_value} центов")
                    return {"usd": {"amount": usd_value}}
                # Если это число
                elif isinstance(response["usd"], (int, float)):
                    usd_value = float(response["usd"]) * 100  # преобразуем в центы
                    logger.info(f"Баланс (из числа): {response['usd']} -> {usd_value} центов")
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
    
    # Добавляем метод в класс, если он еще не добавлен
    if not hasattr(DMarketAPI, "get_user_balance") or not callable(getattr(DMarketAPI, "get_user_balance", None)):
        logger.info("Применяем патч метода get_user_balance к классу DMarketAPI")
        DMarketAPI.get_user_balance = get_user_balance
        return True
    
    logger.info("Метод get_user_balance уже существует в классе DMarketAPI")
    return False
