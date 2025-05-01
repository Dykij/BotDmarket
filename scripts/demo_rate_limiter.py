"""
Демонстрационный скрипт для тестирования Rate Limiter.
"""

import sys
import os
import asyncio
import time

# Добавляем корневой каталог проекта в путь импорта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.rate_limiter import RateLimiter


async def demo_rate_limiter():
    """Демонстрация работы RateLimiter."""
    print("Демонстрация работы RateLimiter")
    print("-" * 40)
    
    # Создаем лимитер для неавторизованного пользователя
    limiter = RateLimiter(is_authorized=False)
    print("1. Создан Rate Limiter для неавторизованного пользователя")
    
    # Тестируем определение типа эндпоинта
    endpoints = [
        "/signin",
        "/fee/calculator",
        "/marketplace-api/v1/items",
        "/market-api/v1/last-sales",
        "/user/balance"
    ]
    
    print("\n2. Определение типов эндпоинтов:")
    for path in endpoints:
        endpoint_type = limiter.get_endpoint_type(path)
        print(f"   Путь: {path} -> Тип: {endpoint_type}")
    
    # Тестируем ожидание для соблюдения лимитов
    print("\n3. Тестирование ожидания для соблюдения лимитов:")
    
    # Делаем серию запросов к "market" эндпоинту (лимит 2 RPS)
    endpoint_type = "market"
    requests_count = 5
    
    print(f"   Отправка {requests_count} запросов к эндпоинту типа '{endpoint_type}' (лимит: 2 RPS)...")
    
    for i in range(requests_count):
        start_time = time.time()
        
        await limiter.wait_if_needed(endpoint_type)
        
        elapsed = time.time() - start_time
        print(f"   Запрос {i+1}: Ожидание {elapsed:.4f}с")
    
    # Тестируем обновление лимитов из заголовков
    print("\n4. Обновление лимитов из заголовков:")
    
    # Имитируем заголовки ответа API
    headers = {
        "X-RateLimit-Limit-Second": "5",
        "X-RateLimit-Remaining-Second": "4",
        "X-RateLimit-Reset-Second": "1619955600",
        "X-RateLimit-Limit-Minute": "100",
        "X-RateLimit-Remaining-Minute": "95",
        "X-Market-RateLimit-Limit-Second": "15",
    }
    
    print("   Заголовки до обновления:")
    print(f"   Лимит для 'market': {limiter.limits.get('market')} RPS")
    print(f"   Пользовательские лимиты: {limiter.custom_limits}")
    
    # Обновляем лимиты
    limiter.update_from_headers(headers)
    
    print("\n   Заголовки после обновления:")
    print(f"   Лимит для 'market': {limiter.limits.get('market')} RPS")
    print(f"   Пользовательские лимиты: {limiter.custom_limits}")
    
    print("\n5. Повторное тестирование с обновленными лимитами:")
    
    # Делаем серию запросов с обновленными лимитами
    for i in range(3):
        start_time = time.time()
        
        await limiter.wait_if_needed(endpoint_type)
        
        elapsed = time.time() - start_time
        print(f"   Запрос {i+1}: Ожидание {elapsed:.4f}с")


if __name__ == "__main__":
    asyncio.run(demo_rate_limiter())
