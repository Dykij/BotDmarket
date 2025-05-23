"""
Тест для проверки баланса DMarket API.
"""

import os
import sys
import time
import hmac
import hashlib
import asyncio
import logging
from typing import Dict, Any

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Добавляем корневой каталог проекта в путь импорта
python_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if python_path not in sys.path:
    sys.path.insert(0, python_path)

from src.dmarket.dmarket_api import DMarketAPI

# Добавляем новый метод в класс DMarketAPI для получения баланса
async def get_user_balance(self) -> Dict[str, Any]:
    """
    Get user account balance.

    Returns:
        User balance information in format {"usd": {"amount": value_in_cents}}
    """
    response = await self._request(
        "GET",
        "/account/v1/balance",
        params={}
    )

    # Подробное логирование для диагностики
    logger.debug(f"Ответ API баланса: {response}")

    # Проверяем и преобразуем ответ API к ожидаемому формату
    if response and isinstance(response, dict):
        # Проверка на ошибку авторизации
        if response.get("code") == "InvalidToken":
            logger.error(f"Ошибка авторизации: {response.get('message', 'Неверный токен')}")
            return {"usd": {"amount": 0}}

        # Проверяем наличие USD баланса в ответе API согласно документации
        # Документация указывает на формат {"usd": "5.00"}
        if "usd" in response:
            try:
                # Если это строка, конвертируем в число
                if isinstance(response["usd"], str):
                    usd_value = float(response["usd"]) * 100  # преобразуем в центы
                    logger.info(f"Обрабатываем баланс из строки: {response['usd']} -> {usd_value} центов")
                    return {"usd": {"amount": usd_value}}
                # Если это уже нужный формат с вложенным объектом
                elif isinstance(response["usd"], dict) and "amount" in response["usd"]:
                    logger.info(f"Баланс уже в правильном формате: {response['usd']['amount']} центов")
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
                logger.info(f"Баланс из usdAvailableToWithdraw: {response['usdAvailableToWithdraw']} -> {usd_value} центов")
                return {"usd": {"amount": usd_value}}
            except (ValueError, TypeError) as e:
                logger.error(f"Ошибка преобразования usdAvailableToWithdraw: {e}")

    # Проблема с ответом
    logger.warning(f"Не удалось получить корректные данные о балансе: {response}")
    return {"usd": {"amount": 0}}

# Добавляем метод в класс
DMarketAPI.get_user_balance = get_user_balance

async def main():
    # Получаем API ключи из переменных окружения
    import os
    from dotenv import load_dotenv

    # Загружаем переменные окружения из файла .env (с перезаписью)
    load_dotenv(override=True)

    # Принудительно обновляем ключи из файла .env в корневой директории
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    load_dotenv(dotenv_path=dotenv_path, override=True)

    public_key = os.environ.get("DMARKET_PUBLIC_KEY", "")
    secret_key = os.environ.get("DMARKET_SECRET_KEY", "")

    if not public_key or not secret_key:
        logger.error("API ключи DMarket не настроены!")
        return

    logger.info(f"Используем публичный ключ: {public_key[:10]}...")

    # Создаем экземпляр API клиента
    api = DMarketAPI(
        public_key=public_key,
        secret_key=secret_key
    )
     try:
        logger.info("Получаем баланс...")
        logger.info(f"API URL: {api.api_url}")
        logger.info(f"Public Key: {public_key[:10]}... (длина: {len(public_key)})")
        logger.info(f"Secret Key: {secret_key[:10]}... (длина: {len(secret_key)})")

        # Генерируем заголовки вручную для проверки
        timestamp = str(int(time.time()))
        method = "GET"
        path = "/account/v1/balance"
        string_to_sign = timestamp + method + path

        signature = hmac.new(
            secret_key.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "X-Api-Key": public_key,
            "X-Request-Sign": f"timestampString={timestamp};signatureString={signature}",
            "Content-Type": "application/json",
        }

        logger.info(f"Заголовки: {headers}")

        # Получаем баланс через API
        async with api:
            balance_data = await api.get_user_balance()

        logger.info(f"Ответ API: {balance_data}")

        if not balance_data or "usd" not in balance_data:
            logger.error("Не удалось получить данные о балансе")
            return

        balance = float(balance_data["usd"]["amount"]) / 100  # центы в доллары
        logger.info(f"Ваш текущий баланс: ${balance:.2f}")

    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
