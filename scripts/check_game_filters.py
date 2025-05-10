"""Проверка работы модуля game_filters.py.

Этот скрипт демонстрирует базовую функциональность модуля без необходимости
импортировать модуль через стандартные imports, что позволяет избежать
проблем с зависимостями.
"""

import copy
import json
import os

# Путь к нашему модулю
module_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src",
    "dmarket",
    "game_filters.py",
)

# Загружаем модуль напрямую
module_globals = {}
with open(module_path, encoding="utf-8") as f:
    exec(f.read(), module_globals)

# Теперь у нас есть доступ к классам и функциям из модуля:
BaseGameFilter = module_globals["BaseGameFilter"]
CS2Filter = module_globals["CS2Filter"]
Dota2Filter = module_globals["Dota2Filter"]
TF2Filter = module_globals["TF2Filter"]
RustFilter = module_globals["RustFilter"]
FilterFactory = module_globals["FilterFactory"]
apply_filters_to_items = module_globals["apply_filters_to_items"]
build_api_params_for_game = module_globals["build_api_params_for_game"]


def print_separator(char="-", length=60):
    """Печатает разделительную линию."""
    print(char * length)


def print_title(title):
    """Печатает заголовок."""
    print_separator()
    print(f"### {title} ###")
    print_separator()


# --- Тестовые данные ---
CS2_ITEMS = [
    {
        "title": "AK-47 | Redline (Field-Tested)",
        "price": {"USD": 15},
        "category": "Rifle",
        "rarity": "Classified",
        "float": 0.25,
    },
    {
        "title": "StatTrak™ AWP | Asiimov (Battle-Scarred)",
        "price": {"USD": 120},
        "category": "Sniper Rifle",
        "rarity": "Covert",
        "float": 0.52,
    },
    {
        "title": "Butterfly Knife | Doppler (Factory New)",
        "price": {"USD": 1200},
        "category": "Knife",
        "rarity": "Covert",
        "float": 0.01,
    },
    {
        "title": "Souvenir AWP | Dragon Lore (Field-Tested)",
        "price": {"USD": 15000},
        "category": "Sniper Rifle",
        "rarity": "Covert",
        "float": 0.27,
    },
]


# --- Тесты ---
def test_base_filter():
    """Тест базового фильтра."""
    print_title("Тест базового фильтра")

    filter_obj = BaseGameFilter()

    # Тест фильтрации по цене
    min_price_filter = {"min_price": 100}
    max_price_filter = {"max_price": 200}
    range_filter = {"min_price": 50, "max_price": 200}

    print("Тест фильтрации по минимальной цене (мин. цена = $100):")
    filtered = [item for item in CS2_ITEMS if filter_obj.apply_filters(item, min_price_filter)]

    print(f"Результаты ({len(filtered)} предмета из {len(CS2_ITEMS)}):")
    for item in filtered:
        print(f"- {item['title']}: ${item['price']['USD']}")

    print("\nТест фильтрации по диапазону цен ($50-$200):")
    filtered = [item for item in CS2_ITEMS if filter_obj.apply_filters(item, range_filter)]

    print(f"Результаты ({len(filtered)} предмета из {len(CS2_ITEMS)}):")
    for item in filtered:
        print(f"- {item['title']}: ${item['price']['USD']}")

    print("\nАPI параметры для разных фильтров цены:")
    print(f"- min_price=100: {filter_obj.build_api_params(min_price_filter)}")
    print(f"- max_price=200: {filter_obj.build_api_params(max_price_filter)}")
    print(f"- min_price=50, max_price=200: {filter_obj.build_api_params(range_filter)}")


def test_cs2_filter():
    """Тест CS2 фильтра."""
    print_title("Тест CS2 фильтра")

    filter_obj = CS2Filter()

    print("Поддерживаемые фильтры:")
    print(", ".join(filter_obj.supported_filters))

    # Тестовые фильтры
    float_filter = {"float_min": 0.2, "float_max": 0.3}
    category_filter = {"category": "Rifle"}
    stattrak_filter = {"stattrak": True}
    souvenir_filter = {"souvenir": True}
    combined_filter = {
        "min_price": 100,
        "rarity": "Covert",
        "category": "Sniper Rifle",
    }

    # Результаты тестов
    print("\nПредметы с float между 0.2 и 0.3:")
    filtered = [item for item in CS2_ITEMS if filter_obj.apply_filters(item, float_filter)]
    for item in filtered:
        print(f"- {item['title']}: float {item['float']}")

    print("\nВинтовки (категория Rifle):")
    filtered = [item for item in CS2_ITEMS if filter_obj.apply_filters(item, category_filter)]
    for item in filtered:
        print(f"- {item['title']}: {item['category']}")

    print("\nПредметы StatTrak™:")
    filtered = [item for item in CS2_ITEMS if filter_obj.apply_filters(item, stattrak_filter)]
    for item in filtered:
        print(f"- {item['title']}")

    print("\nПредметы Souvenir:")
    filtered = [item for item in CS2_ITEMS if filter_obj.apply_filters(item, souvenir_filter)]
    for item in filtered:
        print(f"- {item['title']}")

    print("\nКомбинированный фильтр:")
    print(f"Фильтр: {json.dumps(combined_filter)}")
    filtered = [item for item in CS2_ITEMS if filter_obj.apply_filters(item, combined_filter)]

    print(f"Результаты ({len(filtered)} предмета из {len(CS2_ITEMS)}):")
    for item in filtered:
        print(
            f"- {item['title']}: ${item['price']['USD']} "
            f"(Категория: {item['category']}, Редкость: {item['rarity']})"
        )

    # API параметры
    print("\nАPI параметры для комбинированного фильтра:")
    api_params = filter_obj.build_api_params(combined_filter)
    print(json.dumps(api_params, indent=2))

    # Описание фильтра
    print("\nЧеловеко-читаемое описание фильтра:")
    description = filter_obj.get_filter_description(combined_filter)
    print(description)


def test_filter_factory():
    """Тест фабрики фильтров."""
    print_title("Тест фабрики фильтров")

    print("Поддерживаемые игры:")
    games = FilterFactory.get_supported_games()
    print(", ".join(games))

    print("\nСоздание фильтров для различных игр:")
    for game in games:
        filter_obj = FilterFactory.get_filter(game)
        print(
            f"- {game}: {filter_obj.__class__.__name__}, поддерживаемые фильтры: {len(filter_obj.supported_filters)}"
        )

    print("\nПопытка создать фильтр для несуществующей игры вызовет ошибку:")
    try:
        FilterFactory.get_filter("nonexistent_game")
    except ValueError as e:
        print(f"Ошибка (ожидаемая): {e}")


def test_helper_functions():
    """Тест вспомогательных функций."""
    print_title("Тест вспомогательных функций")

    # Тест apply_filters_to_items
    print("Тест функции apply_filters_to_items:")

    # Копия, чтобы не изменять глобальные данные
    items = copy.deepcopy(CS2_ITEMS)

    filter_data = {"min_price": 100}
    print(f"\nФильтр: {json.dumps(filter_data)}")

    filtered = apply_filters_to_items(items, "csgo", filter_data)
    print(f"Результаты ({len(filtered)} из {len(items)}):")
    for item in filtered:
        print(f"- {item['title']}: ${item['price']['USD']}")

    # Тест build_api_params_for_game
    print("\nТест функции build_api_params_for_game:")

    filter_data = {
        "min_price": 50,
        "category": "Knife",
        "stattrak": True,
        "exterior": "Factory New",
    }
    print(f"Фильтр: {json.dumps(filter_data)}")

    api_params = build_api_params_for_game("csgo", filter_data)
    print(f"API параметры: {json.dumps(api_params, indent=2)}")


def run_all_tests():
    """Запускает все тесты."""
    print("Проверка работы модуля game_filters.py")
    print("=====================================")

    test_base_filter()
    print("\n")
    test_cs2_filter()
    print("\n")
    test_filter_factory()
    print("\n")
    test_helper_functions()

    print("\n")
    print_separator("=")
    print("Все тесты выполнены успешно!")
    print_separator("=")


if __name__ == "__main__":
    run_all_tests()
