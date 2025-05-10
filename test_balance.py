#!/usr/bin/env python3
"""
Скрипт для тестирования получения баланса DMarket API с расширенной диагностикой.
Позволяет проверить работу API ключей и выявить проблемы с аутентификацией.
"""

import os
import sys
import json
import asyncio
import logging
import argparse
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

# Добавляем корневой каталог проекта в путь поиска модулей
sys.path.insert(0, os.path.dirname(__file__))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env файла
try:
    from dotenv import load_dotenv
load_dotenv()
    logger.info("Переменные окружения загружены из .env файла")
except ImportError:
    logger.warning("Библиотека python-dotenv не установлена. Продолжаем без неё.")
except Exception as e:
    logger.error(f"Ошибка при загрузке .env файла: {e}")

# Добавляем обработку аргументов командной строки
parser = argparse.ArgumentParser(description="Тестирование баланса DMarket API")
parser.add_argument("--test-mode", action="store_true", help="Запустить в тестовом режиме с виртуальным балансом")
parser.add_argument("--balance", type=float, default=100.0, help="Тестовый баланс в USD (только для тестового режима)")
args = parser.parse_args()

# Константы для тестового режима
TEST_MODE = args.test_mode or os.environ.get("TEST_MODE") == "1"
TEST_BALANCE = float(os.environ.get("TEST_BALANCE", args.balance))

def get_api_keys() -> Dict[str, str]:
    """
    Получает API ключи из переменных окружения или запрашивает у пользователя.
    
    Returns:
        Словарь с ключами API
    """
    # Получаем ключи из переменных окружения
        public_key = os.environ.get("DMARKET_PUBLIC_KEY", "")
        secret_key = os.environ.get("DMARKET_SECRET_KEY", "")
    api_url = os.environ.get("DMARKET_API_URL", "https://api.dmarket.com")
    
    # Если мы в тестовом режиме и нет ключей, используем тестовые
    if TEST_MODE and (not public_key or not secret_key):
        logger.info(f"Используем тестовые API ключи (тестовый режим)")
        return {
            "public_key": "test_public_key",
            "secret_key": "test_secret_key",
            "api_url": api_url
        }
    
    # Если ключи не найдены, запрашиваем у пользователя
    if not public_key or not secret_key:
        logger.warning("API ключи не найдены в переменных окружения")
        if not TEST_MODE:
            print("\nВведите ваши API ключи DMarket:")
            public_key = input("Публичный ключ: ").strip()
            secret_key = input("Секретный ключ: ").strip()
        
        if not public_key or not secret_key:
            if not TEST_MODE:
                logger.error("API ключи обязательны для тестирования")
                sys.exit(1)
            else:
                # В тестовом режиме используем заглушки
                public_key = "test_public_key"
                secret_key = "test_secret_key"
    
    return {
        "public_key": public_key,
        "secret_key": secret_key,
        "api_url": api_url
    }

async def test_dmarket_api(api_keys: Dict[str, str], endpoint: str) -> Dict[str, Any]:
    """
    Тестирует API DMarket, выполняя запрос к указанному эндпоинту.
    
    Args:
        api_keys: Словарь с ключами API
        endpoint: Эндпоинт для тестирования
        
    Returns:
        Результаты теста
    """
    # В тестовом режиме возвращаем фиктивный успешный ответ
    if TEST_MODE:
        logger.info(f"Тестовый режим: имитируем успешный ответ для {endpoint}")
        return {
            "success": True,
            "endpoint": endpoint,
            "response": {
                "usd": {"amount": TEST_BALANCE * 100},  # баланс в центах
                "test_mode": True
            }
        }
    
    try:
        # Импортируем DMarketAPI
        try:
            from src.dmarket.dmarket_api import DMarketAPI
        except ImportError:
            logger.error("Не удалось импортировать класс DMarketAPI")
            return {
                "success": False,
                "endpoint": endpoint,
                "error": "Не удалось импортировать класс DMarketAPI"
            }
        
        # Создаем экземпляр API
        from src.utils.rate_limiter import RateLimiter
        rate_limiter = RateLimiter(is_authorized=True)
        logger.info("Инициализирован контроллер лимитов запросов API")
        
        api = DMarketAPI(
            public_key=api_keys["public_key"],
            secret_key=api_keys["secret_key"],
            api_url=api_keys["api_url"],
            max_retries=2
        )
        logger.info(f"Initialized DMarketAPI client (authorized: {bool(api_keys['public_key'] and api_keys['secret_key'])})")
        
        # Выполняем запрос
        logger.info(f"Тестирование эндпоинта {endpoint}...")
        try:
            # Исправлено согласно сигнатуре метода _request
            response = await api._request(
                method="GET",
                path=endpoint
            )
            
            # Проверяем успешность запроса
            success = response and isinstance(response, dict) and not ("error" in response or "code" in response)
            
            if success:
                logger.info(f"✅ Успешный ответ от эндпоинта {endpoint}")
            else:
                error_code = response.get("code", "unknown") if isinstance(response, dict) else "unknown"
                error_message = response.get("message", "Неизвестная ошибка") if isinstance(response, dict) else str(response)
                logger.error(f"❌ Ошибка от эндпоинта {endpoint}: {error_code} - {error_message}")
            
            return {
                "success": success,
                "endpoint": endpoint,
                "response": response
            }
                
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса: {str(e)}")
            return {
                "success": False,
                "endpoint": endpoint,
                "error": str(e)
            }
            
    except Exception as e:
        logger.error(f"❌ Ошибка при запросе к эндпоинту {endpoint}: {str(e)}")
        return {
            "success": False,
            "endpoint": endpoint,
            "error": str(e)
        }

async def test_all_endpoints(api_keys: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """
    Тестирует все известные эндпоинты API DMarket.
    
    Args:
        api_keys: Словарь с ключами API
        
    Returns:
        Результаты теста для всех эндпоинтов
    """
    # Обновленные эндпоинты согласно документации
    endpoints = [
        "/api/v1/account/balance",          # Актуальный эндпоинт баланса
        "/api/v1/account/wallet/balance",   # Альтернативный эндпоинт
        "/exchange/v1/user/balance",        # Эндпоинт биржи
        "/account/v1/balance"               # Старый эндпоинт (для обратной совместимости)
    ]
    
    results = {}
    success = False
    
    # В тестовом режиме возвращаем фиктивный успешный ответ
    if TEST_MODE:
        logger.info("Тестовый режим: пропускаем проверку эндпоинтов")
        return {
            "/api/v1/account/balance": {
                "success": True,
                "endpoint": "/api/v1/account/balance",
                "response": {
                    "usd": {"amount": TEST_BALANCE * 100},  # баланс в центах
                    "test_mode": True
                }
            }
        }
    
    # Проверяем все эндпоинты
    for endpoint in endpoints:
        result = await test_dmarket_api(api_keys, endpoint)
        results[endpoint] = result
        
        if result["success"]:
            success = True
            break
    
    if not success:
        logger.warning("⚠️ Не удалось получить успешный ответ ни от одного эндпоинта")
    
    return results

async def test_patched_get_balance(api_keys: Dict[str, str]) -> Dict[str, Any]:
    """
    Тестирует улучшенную функцию получения баланса.
    
    Args:
        api_keys: Словарь с ключами API
        
    Returns:
        Результаты теста
    """
    # В тестовом режиме возвращаем фиктивный успешный ответ
    if TEST_MODE:
        logger.info("Тестовый режим: имитируем успешное получение баланса")
        return {
            "success": True,
            "balance": {
                "usd": {"amount": TEST_BALANCE * 100},  # баланс в центах
                "has_funds": TEST_BALANCE >= 1.0,
                "balance": TEST_BALANCE,
                "available_balance": TEST_BALANCE,
                "total_balance": TEST_BALANCE,
                "error": False,
                "additional_info": {"test_mode": True}
            }
        }
    
    try:
        # Импортируем DMarketAPI
        from src.dmarket.dmarket_api import DMarketAPI
        from src.utils.rate_limiter import RateLimiter
        
        # Создаем экземпляр API
        rate_limiter = RateLimiter(is_authorized=True)
        api = DMarketAPI(
            public_key=api_keys["public_key"],
            secret_key=api_keys["secret_key"],
            api_url=api_keys["api_url"],
            max_retries=3
        )
        
        # Проверяем наличие метода get_user_balance
        if not hasattr(api, "get_user_balance") or not callable(getattr(api, "get_user_balance")):
            logger.error("Метод get_user_balance не найден в DMarketAPI")
            return {
                "success": False,
                "error": "Метод get_user_balance не найден в DMarketAPI"
            }
        
        # Вызываем метод get_user_balance
        logger.info("Вызов улучшенной функции получения баланса...")
        balance_result = await api.get_user_balance()
        
        return {
            "success": True,
            "balance": balance_result
        }
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании улучшенной функции: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }

def create_mock_patched_api():
    """
    Создает патч DMarketAPI для тестового режима.
    """
    if not TEST_MODE:
        return
    
    try:
        from src.dmarket.dmarket_api import DMarketAPI
        
        # Оригинальный метод _request
        original_request = DMarketAPI._request
        
        # Мок _request, который возвращает фиктивный баланс
        async def mock_request(self, method, path, **kwargs):
            if "balance" in path or "funds" in path:
                logger.info(f"Тестовый режим: возвращаем фиктивный баланс для {path}")
                return {
                    "usd": {"amount": TEST_BALANCE * 100},  # баланс в центах
                    "test_mode": True
                }
            else:
                # Для других запросов используем оригинальный метод
                return await original_request(self, method, path, **kwargs)
        
        # Мок get_user_balance
        async def mock_get_user_balance(self):
            logger.info("Тестовый режим: возвращаем фиктивный результат баланса")
            return {
                "usd": {"amount": TEST_BALANCE * 100},  # баланс в центах
                "has_funds": TEST_BALANCE >= 1.0,
                "balance": TEST_BALANCE,
                "available_balance": TEST_BALANCE,
                "total_balance": TEST_BALANCE,
                "error": False,
                "additional_info": {"test_mode": True}
            }
        
        # Применяем патчи
        DMarketAPI._request = mock_request
        DMarketAPI.get_user_balance = mock_get_user_balance
        
        logger.info(f"Тестовый режим: патч DMarketAPI применен с балансом ${TEST_BALANCE:.2f}")
        
    except ImportError:
        logger.error("Не удалось импортировать класс DMarketAPI для патча тестового режима")
    except Exception as e:
        logger.error(f"Ошибка при применении патча для тестового режима: {e}")

async def main():
    """Основная функция."""
    # Если включен тестовый режим, применяем патч для тестовых данных
    if TEST_MODE:
        logger.info(f"Запуск в ТЕСТОВОМ РЕЖИМЕ с виртуальным балансом ${TEST_BALANCE:.2f}")
        create_mock_patched_api()
    
    # Получаем API ключи
    api_keys = get_api_keys()
    
    if not TEST_MODE:
        # Проверяем все известные эндпоинты
        await test_all_endpoints(api_keys)
    
    # Проверяем улучшенную функцию получения баланса
    logger.info("\n====== Тестирование улучшенной функции получения баланса ======")
    logger.info("Использование улучшенной функции получения баланса...")
    
    balance_result = await test_patched_get_balance(api_keys)
    
    if balance_result.get("success", False):
        logger.info("✅ Улучшенная функция получения баланса работает корректно!")
        
        # Показываем информацию о балансе
        balance_data = balance_result.get("balance", {})
        has_funds = balance_data.get("has_funds", False)
        balance = balance_data.get("balance", 0.0)
        available_balance = balance_data.get("available_balance", 0.0)
        total_balance = balance_data.get("total_balance", 0.0)
        error = balance_data.get("error", False)
        
        logger.info("Результат получения баланса:")
        logger.info(f"  - Баланс: ${balance:.2f}")
        logger.info(f"  - Доступный баланс: ${available_balance:.2f}")
        logger.info(f"  - Общий баланс: ${total_balance:.2f}")
        logger.info(f"  - Достаточно средств: {'Да' if has_funds else 'Нет'}")
        
        if error:
            error_message = balance_data.get("error_message", "Неизвестная ошибка")
            logger.error(f"  - Ошибка: {error_message}")
    else:
        error = balance_result.get("error", "Неизвестная ошибка")
        logger.error(f"❌ Ошибка при тестировании улучшенной функции: {error}")
    
    logger.info("\n====== Тест завершен ======")
    
    # Выводим рекомендации, если не в тестовом режиме и баланс равен 0
    if not TEST_MODE and (not balance_result.get("success", False) or balance_result.get("balance", {}).get("balance", 0) == 0):
        logger.info("\nРекомендации по устранению проблем:")
        logger.info("1. Проверьте правильность API ключей")
        logger.info("2. Убедитесь, что API ключи не истекли")
        logger.info("3. Проверьте, что у вас есть доступ к API DMarket")
        logger.info("4. Попробуйте сгенерировать новые API ключи в личном кабинете DMarket")
        logger.info("5. Для тестирования бота без API ключей, запустите: python test_balance.py --test-mode")

if __name__ == "__main__":
    asyncio.run(main())
