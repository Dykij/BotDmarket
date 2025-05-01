"""
Демонстрационный модуль для автоматического арбитража на DMarket
"""

import asyncio
import logging
import os
import random
import time
from typing import List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Симуляция данных с DMarket
GAMES = {
    "csgo": "CS:GO",
    "dota2": "Dota 2",
    "rust": "Rust",
    "tf2": "Team Fortress 2"
}


def generate_random_items(game: str, count: int = 10) -> List[Dict[str, Any]]:
    """
    Генерирует случайные предметы для тестирования.
    
    Args:
        game: Код игры
        count: Количество предметов для генерации
        
    Returns:
        Список предметов
    """
    item_types = {
        "csgo": ["Нож", "AWP", "AK-47", "M4A4", "Desert Eagle", "Перчатки", "USP-S", "Glock-18"],
        "dota2": ["Аркана", "Иммортал", "Курьер", "Сет", "Редкий предмет", "Легендарный предмет"],
        "rust": ["Оружие", "Одежда", "Инструменты", "Ресурсы", "Декор"],
        "tf2": ["Шляпа", "Оружие", "Необычный предмет", "Редкий предмет"]
    }
    
    rarities = ["Обычный", "Необычный", "Редкий", "Мифический", "Легендарный", "Древний", "Бессмертный"]
    colors = ["Красный", "Синий", "Зеленый", "Желтый", "Черный", "Белый", "Розовый"]
    
    items = []
    item_types_for_game = item_types.get(game, ["Предмет"])
    
    for i in range(count):
        item_type = random.choice(item_types_for_game)
        rarity = random.choice(rarities)
        color = random.choice(colors)
        
        # Генерируем случайную цену и прибыль
        buy_price = random.randint(100, 10000)  # цена в центах
        profit_percentage = random.uniform(5.0, 30.0)  # процент прибыли
        profit = int(buy_price * profit_percentage / 100)
        
        # Создаем название предмета
        item_name = f"{rarity} {item_type} | {color}"
        
        # Создаем предмет
        item = {
            "title": item_name,
            "buyPrice": buy_price,
            "sellPrice": buy_price + profit,
            "profit": profit,
            "profitPercent": profit_percentage,
            "gameId": game,
            "rarity": rarity,
            "color": color
        }
        
        items.append(item)
    
    # Сортируем по проценту прибыли
    items.sort(key=lambda x: x["profitPercent"], reverse=True)
    return items


def arbitrage_boost(game: str) -> List[Dict[str, Any]]:
    """
    Получает предметы для арбитража в режиме 'Разгон баланса' (низкая прибыль, но быстрые сделки).
    
    Args:
        game: Код игры
        
    Returns:
        Список предметов
    """
    items = generate_random_items(game, count=15)
    # Фильтруем по низкой цене и небольшой прибыли
    return [item for item in items if item["buyPrice"] < 500 and item["profitPercent"] >= 5.0]


def arbitrage_mid(game: str) -> List[Dict[str, Any]]:
    """
    Получает предметы для арбитража в режиме 'Средний трейдер' (средняя прибыль).
    
    Args:
        game: Код игры
        
    Returns:
        Список предметов
    """
    items = generate_random_items(game, count=20)
    # Фильтруем по средней цене и средней прибыли
    return [item for item in items if 500 <= item["buyPrice"] < 2000 and item["profitPercent"] >= 10.0]


def arbitrage_pro(game: str) -> List[Dict[str, Any]]:
    """
    Получает предметы для арбитража в режиме 'Trade Pro' (высокая прибыль).
    
    Args:
        game: Код игры
        
    Returns:
        Список предметов
    """
    items = generate_random_items(game, count=25)
    # Фильтруем по высокой цене и высокой прибыли
    return [item for item in items if item["buyPrice"] >= 2000 and item["profitPercent"] >= 15.0]


async def auto_arbitrage_demo(game: str = "csgo", mode: str = "medium", iterations: int = 5) -> None:
    """
    Демонстрация работы автоматического арбитража.
    
    Args:
        game: Код игры
        mode: Режим арбитража ('low', 'medium', 'high')
        iterations: Количество итераций
    """
    logger.info(f"Запуск автоматического арбитража для {GAMES.get(game, game)} в режиме {mode}")
    
    try:
        for i in range(iterations):
            logger.info(f"Итерация {i+1} из {iterations}")
            
            # Получаем данные в зависимости от режима
            if mode == "low":
                items = arbitrage_boost(game)
            elif mode == "high":
                items = arbitrage_pro(game)
            else:  # medium
                items = arbitrage_mid(game)
            
            if items:
                logger.info(f"Найдено {len(items)} предметов для арбитража")
                
                # Выводим топ-3 предмета
                for j, item in enumerate(items[:3], start=1):
                    name = item["title"]
                    buy_price = item["buyPrice"] / 100  # переводим центы в доллары
                    profit = item["profit"] / 100
                    profit_percent = item["profitPercent"]
                    
                    logger.info(f"{j}. {name} - ${buy_price:.2f} "
                               f"(Прибыль: ${profit:.2f}, {profit_percent:.1f}%)")
                
                # В реальном приложении здесь могла бы быть логика для выполнения
                # автоматических сделок, но это просто демонстрация
            else:
                logger.info("Не найдено предметов, удовлетворяющих условиям")
            
            # Ждем некоторое время перед следующей итерацией
            await asyncio.sleep(2)
    
    except Exception as e:
        logger.error(f"Ошибка при выполнении автоматического арбитража: {str(e)}")
    
    logger.info("Автоматический арбитраж завершен")


async def main() -> None:
    """Запускает демонстрацию автоматического арбитража."""
    print("""
    =============================================================
    Демонстрация автоматического арбитража для DMarket
    =============================================================
    """)
    
    # Запускаем демонстрацию для разных игр и режимов
    for game in ["csgo", "dota2"]:
        for mode in ["low", "medium", "high"]:
            print(f"\n----- Автоматический арбитраж: {GAMES[game]}, режим: {mode} -----")
            await auto_arbitrage_demo(game=game, mode=mode, iterations=3)
            print("-" * 70)


if __name__ == "__main__":
    # Запускаем асинхронную демонстрацию
    asyncio.run(main())
