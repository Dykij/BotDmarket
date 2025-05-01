"""
Тестирование работы модуля game_filters.py.

Этот скрипт демонстрирует, что модуль game_filters успешно установлен и работает.
"""

import os
import sys

# Добавляем путь к родительскому каталогу в список путей поиска модулей
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

try:
    # Импортируем функции из модуля game_filters
    from src.dmarket.game_filters import FilterFactory, apply_filters_to_items, build_api_params_for_game
    
    # Проверка поддерживаемых игр
    games = FilterFactory.get_supported_games()
    print("Поддерживаемые игры:", ", ".join(games))
    
    # Создание фильтра для CS2/CSGO
    filter_obj = FilterFactory.get_filter("csgo")
    print("Фильтр создан:", filter_obj.__class__.__name__)
    
    # Проверка поддерживаемых фильтров
    print("Поддерживаемые фильтры:", ", ".join(filter_obj.supported_filters))
    
    # Демонстрация фильтрации
    test_items = [
        {"title": "AK-47 | Redline (Field-Tested)", "price": {"USD": 15}, "category": "Rifle"},
        {"title": "AWP | Dragon Lore (Factory New)", "price": {"USD": 5000}, "category": "Sniper Rifle"},
        {"title": "StatTrak™ M4A4 | Asiimov (Battle-Scarred)", "price": {"USD": 120}, "category": "Rifle"},
        {"title": "Butterfly Knife | Doppler (Factory New)", "price": {"USD": 1200}, "category": "Knife"}
    ]
    
    print("\nФильтрация предметов:")
    
    # Фильтр по цене
    price_filter = {"min_price": 100}
    filtered = apply_filters_to_items(test_items, "csgo", price_filter)
    print(f"Предметы дороже $100 ({len(filtered)} из {len(test_items)}):")
    for item in filtered:
        print(f"- {item['title']}: ${item['price']['USD']}")
    
    # Фильтр по категории
    category_filter = {"category": "Rifle"}
    filtered = apply_filters_to_items(test_items, "csgo", category_filter)
    print(f"\nТолько винтовки ({len(filtered)} из {len(test_items)}):")
    for item in filtered:
        print(f"- {item['title']}: {item['category']}")
    
    # Комбинированный фильтр
    combined_filter = {"min_price": 100, "category": "Rifle"}
    filtered = apply_filters_to_items(test_items, "csgo", combined_filter)
    print(f"\nВинтовки дороже $100 ({len(filtered)} из {len(test_items)}):")
    for item in filtered:
        print(f"- {item['title']}: ${item['price']['USD']}")
    
    # Создание API параметров
    api_params = build_api_params_for_game("csgo", combined_filter)
    print("\nAPI параметры для комбинированного фильтра:")
    for key, value in api_params.items():
        print(f"- {key}: {value}")
    
    print("\nТестирование модуля game_filters.py успешно завершено!")

except Exception as e:
    print(f"Ошибка при импорте или использовании модуля: {type(e).__name__}: {e}")
