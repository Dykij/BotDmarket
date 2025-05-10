"""Самостоятельный скрипт для проверки баланса DMarket без импорта сломанного API.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DirectBalanceChecker:
    """Проверка баланса DMarket напрямую без импорта основного API."""

    def __init__(self, public_key: str, secret_key: str, api_url: str = "https://api.dmarket.com"):
        """Инициализация с API ключами."""
        self.public_key = public_key
        self.secret_key = secret_key.encode("utf-8")
        self.api_url = api_url

    def generate_signature(self, method: str, path: str, body: str = "") -> dict[str, str]:
        """Генерирует подпись для авторизации запросов к Dmarket API."""
        timestamp = str(int(time.time()))
        string_to_sign = timestamp + method + path
        if body:
            string_to_sign += body

        signature = hmac.new(
            self.secret_key,
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return {
            "X-Api-Key": self.public_key,
            "X-Request-Sign": f"timestampString={timestamp};signatureString={signature}",
            "Content-Type": "application/json",
        }

    async def check_balance(self) -> dict[str, Any]:
        """Проверяет баланс, пробуя оба эндпоинта API."""
        # Пробуем новый эндпоинт из документации
        new_path = "/v1/user/balance"
        new_headers = self.generate_signature("GET", new_path)
        new_url = f"{self.api_url}{new_path}"

        try:
            logger.info(f"Запрос баланса через новый эндпоинт: {new_url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(new_url, headers=new_headers, timeout=30.0)
                logger.info(f"Статус ответа нового API: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Ответ нового API: {result}")
                    return self.parse_balance(result)
                logger.warning(f"Ошибка нового API: {response.text}")
        except Exception as e:
            logger.warning(f"Ошибка при запросе через новый эндпоинт: {e!s}")

        # Пробуем старый эндпоинт
        old_path = "/account/v1/balance"
        old_headers = self.generate_signature("GET", old_path)
        old_url = f"{self.api_url}{old_path}"

        try:
            logger.info(f"Запрос баланса через старый эндпоинт: {old_url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(old_url, headers=old_headers, timeout=30.0)
                logger.info(f"Статус ответа старого API: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Ответ старого API: {result}")
                    return self.parse_balance(result)
                logger.warning(f"Ошибка старого API: {response.text}")
        except Exception as e:
            logger.error(f"Ошибка при запросе через старый эндпоинт: {e!s}")

        return {"error": "Не удалось получить баланс", "balance_usd": 0.0}

    def parse_balance(self, response: dict[str, Any]) -> dict[str, Any]:
        """Обрабатывает ответ API с балансом.
        Поддерживает различные форматы ответа.
        """
        result = {"raw_response": response, "balance_usd": 0.0}

        try:
            # Вариант 1: {"usd": "5.00"}
            if "usd" in response and isinstance(response["usd"], str):
                balance = float(response["usd"])
                logger.info(f"Баланс (из строки): ${balance:.2f}")
                result["balance_usd"] = balance
                return result

            # Вариант 2: {"usd": 5.00}
            if "usd" in response and isinstance(response["usd"], (int, float)):
                balance = float(response["usd"])
                logger.info(f"Баланс (из числа): ${balance:.2f}")
                result["balance_usd"] = balance
                return result

            # Вариант 3: {"usd": {"amount": 500}}
            if (
                "usd" in response
                and isinstance(response["usd"], dict)
                and "amount" in response["usd"]
            ):
                balance = float(response["usd"]["amount"]) / 100  # центы в доллары
                logger.info(f"Баланс (из объекта): ${balance:.2f}")
                result["balance_usd"] = balance
                return result

            # Вариант 4: {"balance": {"usd": 500}}
            if (
                "balance" in response
                and isinstance(response["balance"], dict)
                and "usd" in response["balance"]
            ):
                balance = float(response["balance"]["usd"]) / 100  # центы в доллары
                logger.info(f"Баланс (из объекта balance): ${balance:.2f}")
                result["balance_usd"] = balance
                return result

            # Вариант 5: {"usdAvailableToWithdraw": "5.00"}
            if "usdAvailableToWithdraw" in response:
                balance = float(response["usdAvailableToWithdraw"])
                logger.info(f"Баланс (из usdAvailableToWithdraw): ${balance:.2f}")
                result["balance_usd"] = balance
                return result

        except Exception as e:
            logger.error(f"Ошибка при парсинге баланса: {e!s}")

        logger.warning(f"Не удалось определить баланс в ответе: {response}")
        return result


async def main():
    """Основная функция скрипта."""
    # Загружаем переменные окружения из .env
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    load_dotenv(dotenv_path=dotenv_path, override=True)

    # Получаем API ключи
    public_key = os.environ.get("DMARKET_PUBLIC_KEY")
    secret_key = os.environ.get("DMARKET_SECRET_KEY")
    api_url = os.environ.get("DMARKET_API_URL", "https://api.dmarket.com")

    if not public_key or not secret_key:
        logger.error("Отсутствуют API ключи DMarket в переменных окружения!")
        return

    logger.info(f"Используем API ключи: PUBLIC_KEY={public_key[:10]}..., API_URL={api_url}")

    # Создаем проверяльщик баланса
    checker = DirectBalanceChecker(public_key, secret_key, api_url)

    # Получаем и обрабатываем баланс
    result = await checker.check_balance()

    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ПРОВЕРКИ БАЛАНСА DMARKET")
    print("=" * 60)

    if "error" in result:
        print(f"ОШИБКА: {result['error']}")

    balance_usd = result.get("balance_usd", 0.0)
    print(f"\nБаланс: ${balance_usd:.2f}")

    if balance_usd == 0 and "raw_response" in result:
        print("\nИсходный ответ API:")
        print(json.dumps(result["raw_response"], indent=2, ensure_ascii=False))

    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
