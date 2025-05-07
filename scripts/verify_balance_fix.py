#!/usr/bin/env python3
"""Скрипт для проверки работы исправленного патча баланса DMarket.
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Добавляем корневой каталог проекта в путь импорта
python_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if python_path not in sys.path:
    sys.path.insert(0, python_path)

# Явно импортируем и применяем патч для проверки его работы
try:
    from src.dmarket.fix_balance import apply_balance_patch
    logger.info("Патч баланса успешно импортирован")
except ImportError as e:
    logger.error(f"Ошибка импорта патча баланса: {e}")

from src.dmarket.dmarket_api import DMarketAPI
from src.telegram_bot.auto_arbitrage_scanner import check_user_balance


async def test_balance_with_patch():
    """Тестирование работы патча баланса DMarket."""
    # Загружаем переменные окружения из .env файла
    load_dotenv()

    # Получаем API ключи DMarket из окружения
    public_key = os.environ.get("DMARKET_PUBLIC_KEY", "")
    secret_key = os.environ.get("DMARKET_SECRET_KEY", "")

    if not public_key or not secret_key:
        logger.error("Не настроены API ключи DMarket (DMARKET_PUBLIC_KEY и DMARKET_SECRET_KEY)")
        return

    logger.info(f"Используем публичный ключ: {public_key[:5]}... (длина: {len(public_key)})")
    logger.info(f"Секретный ключ имеет длину: {len(secret_key)}")

    # Создаем API клиент
    api = DMarketAPI(
        public_key=public_key,
        secret_key=secret_key,
        api_url="https://api.dmarket.com",
        max_retries=5,
    )

    logger.info("=== Проверка баланса с исправленным патчем ===")

    # Прямая проверка через API
    try:
        logger.info("Получаем баланс через API напрямую...")
        async with api:
            balance_data = await api.get_user_balance()

        logger.info(f"Ответ API: {balance_data}")

        if not balance_data or "usd" not in balance_data:
            logger.error("Не удалось получить данные о балансе (прямой вызов)")
        else:
            balance_cents = float(balance_data["usd"]["amount"])
            balance_dollars = balance_cents / 100  # центы в доллары
            logger.info(f"Ваш текущий баланс (прямой вызов): ${balance_dollars:.2f}")
    except Exception as e:
        logger.error(f"Ошибка при прямом вызове API: {e}")

    # Проверка через функцию check_user_balance
    try:
        logger.info("Проверяем баланс через check_user_balance...")
        has_funds, balance = await check_user_balance(api)

        logger.info(f"Результат check_user_balance: has_funds={has_funds}, balance=${balance:.2f}")

        if has_funds:
            logger.info("У вас достаточно средств для торговли!")
        else:
            logger.info("У вас недостаточно средств для торговли.")
            if balance > 0:
                logger.info(f"Баланс составляет ${balance:.2f}, но это меньше минимального требуемого ($1.00)")
    except Exception as e:
        logger.error(f"Ошибка при вызове check_user_balance: {e}")
        import traceback
        logger.error(f"Трассировка: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_balance_with_patch())
