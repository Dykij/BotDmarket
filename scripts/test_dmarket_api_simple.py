"""
Простой тест для DMarket API.
"""

import os
import sys
import asyncio

# Добавляем корневой каталог проекта в путь импорта
python_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if python_path not in sys.path:
    sys.path.insert(0, python_path)

from src.dmarket.dmarket_api import DMarketAPI

async def main():
    print("Проверка DMarket API...")
    api = DMarketAPI()
    
    try:
        # Проверяем доступность API
        print("Проверка подключения...")
        ping_result = await api.ping()
        print(f"Результат ping: {ping_result}")
        
        # Получаем курсы валют
        print("\nПолучение курсов валют...")
        currencies = await api.get_currencies()
        print(f"Курсы валют: {currencies}")
        
        # Получаем доступные игры
        print("\nПолучение списка игр...")
        games = await api.get_available_games()
        print(f"Доступные игры: {games}")
        
        # Получаем рыночные предметы для CS:GO
        print("\nПолучение предметов CS:GO...")
        csgo_items = await api.get_market_items(
            game="csgo",
            limit=5,
            offset=0,
            orderBy="price",
            orderDir="asc",
            currency="USD"
        )
        print(f"Найдено предметов: {len(csgo_items.get('items', []))}")
        
        # Выводим информацию о первых предметах
        for i, item in enumerate(csgo_items.get('items', [])[:3]):
            price = float(item.get('price', {}).get('amount', 0)) / 100
            title = item.get('title')
            print(f"{i+1}. {title} - ${price:.2f}")
        
        print("\nВсе тесты успешно выполнены!")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
