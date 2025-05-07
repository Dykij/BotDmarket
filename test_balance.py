#!/usr/bin/env python3
"""Скрипт для проверки баланса DMarket."""

import asyncio
import json
import logging
import os
import sys

from dotenv import load_dotenv

# Настраиваем логирование
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

async def test_balance():
    """Тестирует получение баланса DMarket."""
    # Импортируем API клиент и патч для баланса
    from src.dmarket.dmarket_api import DMarketAPI
    from src.dmarket.dmarket_api_patch import apply_balance_patch

    # Получаем ключи API из переменных окружения
    public_key = os.getenv("DMARKET_PUBLIC_KEY", "")
    secret_key = os.getenv("DMARKET_SECRET_KEY", "")
    api_url = os.getenv("DMARKET_API_URL", "https://api.dmarket.com")

    if not public_key or not secret_key:
        logger.error("API ключи не найдены в переменных окружения")
        return

    logger.info(f"Используем API ключи: PUBLIC={public_key[:8]}..., SECRET={secret_key[:8]}...")

    try:
        # Применяем патч для get_user_balance
        apply_balance_patch()

        # Создаем API клиент
        api_client = DMarketAPI(
            public_key=public_key,
            secret_key=secret_key,
            api_url=api_url,
        )

        # Проверяем встроенный метод get_user_balance
        logger.info("Проверяем встроенный метод get_user_balance...")
        async with api_client:
            result = await api_client.get_user_balance()

        logger.info(f"Результат get_user_balance: {json.dumps(result, indent=2)}")

        # Проверяем патч метода get_user_balance
        logger.info("Проверяем патч из dmarket_api_balance...")
        from src.telegram_bot.auto_arbitrage_scanner import check_user_balance

        async with api_client:
            has_funds, balance = await check_user_balance(api_client)

        logger.info(f"Результат check_user_balance: has_funds={has_funds}, balance=${balance:.2f}")

        # Проверяем прямой запрос к API
        logger.info("Проверяем прямой запрос к API...")
        from src.dmarket.dmarket_api_balance import get_user_balance

        async with api_client:
            direct_result = await get_user_balance.__get__(api_client)(api_client)

        logger.info(f"Прямой результат get_user_balance: {json.dumps(direct_result, indent=2)}")

        # Проверяем новый эндпоинт баланса
        logger.info("Проверяем новый эндпоинт баланса...")
        import hashlib
        import hmac
        import time

        import httpx

        timestamp = str(int(time.time()))
        method = "GET"
        path = "/v1/user/balance"
        string_to_sign = timestamp + method + path

        signature = hmac.new(
            secret_key.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "X-Api-Key": public_key,
            "X-Request-Sign": f"timestampString={timestamp};signatureString={signature}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{api_url}{path}",
                headers=headers,
            )

        logger.info(f"Статус: {response.status_code}")
        logger.info(f"Результат нового эндпоинта: {response.text}")

        if response.status_code == 200:
            try:
                balance_data = response.json()
                logger.info(f"Распарсенный ответ: {json.dumps(balance_data, indent=2)}")
            except json.JSONDecodeError:
                logger.error("Невозможно распарсить ответ как JSON")

    except Exception as e:
        logger.error(f"Ошибка при проверке баланса: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_balance())
