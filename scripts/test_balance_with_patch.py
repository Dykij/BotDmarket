"""
Тест патча баланса для DMarket API.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Добавляем корневой каталог проекта в путь импорта
python_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if python_path not in sys.path:
    sys.path.insert(0, python_path)

# Импортируем патч и применяем его
from src.dmarket.dmarket_api_patches import apply_balance_patch
from src.dmarket.dmarket_api import DMarketAPI
from src.telegram_bot.auto_arbitrage_scanner import check_user_balance

async def test_balance_with_patch():
    """
    Тестирует получение баланса с использованием патча.
    """
    # Загружаем переменные окружения из файла .env в корневой директории
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    load_dotenv(dotenv_path=dotenv_path, override=True)
    
    # Получаем API ключи из переменных окружения
    public_key = os.environ.get("DMARKET_PUBLIC_KEY", "")
    secret_key = os.environ.get("DMARKET_SECRET_KEY", "")
    
    if not public_key or not secret_key:
        logger.error("API ключи DMarket не настроены!")
        return
    
    logger.info(f"Используем публичный ключ: {public_key[:10]}... (длина: {len(public_key)})")
    
    # Создаем экземпляр API клиента
    api = DMarketAPI(
        public_key=public_key,
        secret_key=secret_key
    )
    
    try:
        # Проверяем доступность метода
        if not hasattr(api, "get_user_balance") or not callable(getattr(api, "get_user_balance", None)):
            logger.error("Метод get_user_balance не был добавлен в класс DMarketAPI")
            return
            
        logger.info("Получаем баланс через API...")
        
        # Метод 1: Прямой вызов API
        async with api:
            balance_data = await api.get_user_balance()
        
        logger.info(f"Ответ API (прямой вызов): {balance_data}")
        
        if not balance_data or "usd" not in balance_data:
            logger.error("Не удалось получить данные о балансе (прямой вызов)")
        else:
            balance_cents = float(balance_data["usd"]["amount"])
            balance_dollars = balance_cents / 100  # центы в доллары
            logger.info(f"Ваш текущий баланс (прямой вызов): ${balance_dollars:.2f}")
        
        # Метод 2: Вызов через check_user_balance
        has_funds, balance = await check_user_balance(api)
        
        logger.info(f"Результат check_user_balance: has_funds={has_funds}, balance=${balance:.2f}")
        
        if has_funds:
            logger.info("У вас достаточно средств для торговли!")
        else:
            logger.info("У вас недостаточно средств для торговли.")
        
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {str(e)}")
        import traceback
        logger.error(f"Трассировка: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_balance_with_patch())
