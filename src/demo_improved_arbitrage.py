"""
Демонстрация возможностей улучшенного модуля arbitrage.py
"""

import asyncio
import os
import sys
import json
from typing import Dict, List, Any

# Добавляем корневой каталог проекта в путь импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.dmarket.arbitrage import (
    arbitrage_boost_async,
    arbitrage_mid_async,
    arbitrage_pro_async,
    ArbitrageTrader,
    find_arbitrage_opportunities_async,
    GAMES
)


async def demo_improved_arbitrage():
    """Демонстрирует основные возможности улучшенного модуля arbitrage.py"""
    print("=" * 80)
    print("Демонстрация улучшенного модуля arbitrage.py")
    print("=" * 80)
    
    # Демонстрация асинхронного поиска арбитражных возможностей
    print("\n1. Поиск арбитражных возможностей с низкой прибылью (boost)")
    print("-" * 60)
    
    try:
        boost_items = await arbitrage_boost_async(game="csgo")
        print(f"Найдено {len(boost_items)} предметов:")
        for i, item in enumerate(boost_items[:3]):  # Показываем только первые 3
            print(f"  {i+1}. {item.get('name')} - Покупка: {item.get('buy')}, "
                  f"Продажа: {item.get('sell')}, Прибыль: {item.get('profit')}")
        if len(boost_items) > 3:
            print(f"  ... и еще {len(boost_items) - 3} предметов")
    except Exception as e:
        print(f"Ошибка: {str(e)}")
    
    # Демонстрация поиска возможностей со средней прибылью
    print("\n2. Поиск арбитражных возможностей со средней прибылью (mid)")
    print("-" * 60)
    
    try:
        mid_items = await arbitrage_mid_async(game="csgo")
        print(f"Найдено {len(mid_items)} предметов:")
        for i, item in enumerate(mid_items[:3]):  # Показываем только первые 3
            print(f"  {i+1}. {item.get('name')} - Покупка: {item.get('buy')}, "
                  f"Продажа: {item.get('sell')}, Прибыль: {item.get('profit')}")
        if len(mid_items) > 3:
            print(f"  ... и еще {len(mid_items) - 3} предметов")
    except Exception as e:
        print(f"Ошибка: {str(e)}")
    
    # Демонстрация класса ArbitrageTrader
    print("\n3. Использование класса ArbitrageTrader")
    print("-" * 60)
    
    try:
        # Создаем трейдер
        trader = ArbitrageTrader()
        
        # Проверяем баланс
        has_funds, balance = await trader.check_balance()
        print(f"Баланс: ${balance:.2f} - {'Достаточно средств' if has_funds else 'Недостаточно средств'}")
        
        # Поиск выгодных предметов
        print("\nПоиск выгодных предметов:")
        items = await trader.find_profitable_items(
            game="csgo",
            min_profit_percentage=5.0,
            max_items=5
        )
        
        print(f"Найдено {len(items)} выгодных предметов:")
        for i, item in enumerate(items[:3]):
            print(f"  {i+1}. {item.get('name')} - "
                  f"Покупка: ${item.get('buy_price'):.2f}, "
                  f"Продажа: ${item.get('sell_price'):.2f}, "
                  f"Прибыль: ${item.get('profit'):.2f} "
                  f"({item.get('profit_percentage'):.1f}%)")
        
        # Демонстрация настройки лимитов
        print("\nУстановка лимитов торговли:")
        trader.set_trading_limits(max_trade_value=50.0, daily_limit=300.0)
        
        # Получение статуса трейдера
        status = trader.get_status()
        print("Статус торговли:")
        print(f"  Активен: {status.get('active')}")
        print(f"  Игра: {status.get('game_name')}")
        print(f"  Дневной лимит: ${status.get('daily_limit'):.2f}")
        print(f"  Всего сделок: {status.get('transactions_count')}")
    except Exception as e:
        print(f"Ошибка при использовании ArbitrageTrader: {str(e)}")
    
    # Демонстрация поиска арбитражных возможностей по разным играм
    print("\n4. Поиск арбитражных возможностей по разным играм")
    print("-" * 60)
    
    try:
        opportunities = []
        
        print("Доступные игры:")
        for game_code, game_name in GAMES.items():
            print(f"  {game_code}: {game_name}")
            
            # Ищем возможности для каждой игры
            game_opportunities = await find_arbitrage_opportunities_async(
                min_profit_percentage=10.0,
                max_results=3,
                game=game_code
            )
            
            for opp in game_opportunities:
                opp["game_code"] = game_code
                opp["game_name"] = game_name
                opportunities.append(opp)
            
            print(f"    Найдено {len(game_opportunities)} возможностей")
        
        # Сортируем по проценту прибыли
        opportunities = sorted(
            opportunities,
            key=lambda x: x.get("profit_percentage", 0),
            reverse=True
        )
        
        # Выводим топ возможностей
        print("\nЛучшие возможности по всем играм:")
        for i, opp in enumerate(opportunities[:5]):
            print(f"  {i+1}. {opp.get('item_title')} ({opp.get('game_name')}) - "
                  f"Прибыль: ${opp.get('profit_amount'):.2f} "
                  f"({opp.get('profit_percentage'):.1f}%)")
    except Exception as e:
        print(f"Ошибка при поиске арбитражных возможностей: {str(e)}")
    
    # Вывод справочной информации
    print("\n5. Информация о комиссиях и торговле")
    print("-" * 60)
    print("Комиссии DMarket:")
    print("  Высокая ликвидность: 2%")
    print("  Средняя ликвидность: 7%")
    print("  Низкая ликвидность: 10%")
    
    print("\nРекомендации по торговле:")
    print("  - Фокусируйтесь на предметах с высокой ликвидностью")
    print("  - Начинайте с малых сумм для тестирования")
    print("  - Используйте режим auto_medium для баланса риска/прибыли")
    print("  - Настройте лимиты для контроля рисков")


if __name__ == "__main__":
    # Загружаем переменные окружения из .env файла, если он существует
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("dotenv не установлен. Убедитесь, что переменные окружения настроены.")
    
    # Проверяем, что указаны ключи API
    if not os.environ.get("DMARKET_PUBLIC_KEY") or not os.environ.get("DMARKET_SECRET_KEY"):
        print("ВНИМАНИЕ: Не указаны переменные окружения DMARKET_PUBLIC_KEY и DMARKET_SECRET_KEY")
        print("Некоторые функции будут недоступны или вернут пустые результаты.")
    
    # Запускаем демонстрацию
    asyncio.run(demo_improved_arbitrage())
