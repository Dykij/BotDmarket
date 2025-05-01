# Руководство по использованию модуля фильтрации предметов по играм

## Общее описание

Модуль `game_filters.py` предоставляет гибкую систему фильтрации предметов для различных игр на платформе DMarket. Он позволяет легко фильтровать списки предметов по различным параметрам, специфичным для каждой игры, а также создавать API-параметры для запросов к API DMarket.

Поддерживаемые игры:
- CS2/CSGO (`csgo`)
- Dota 2 (`dota2`) 
- Team Fortress 2 (`tf2`)
- Rust (`rust`)

## Основные компоненты

### Базовый класс `BaseGameFilter`

Предоставляет общие методы фильтрации, которые работают для всех игр:

- Фильтрация по цене (мин/макс)
- Извлечение цены из различных форматов
- Построение параметров API
- Получение читаемого описания фильтров

### Классы фильтров для конкретных игр

Каждый игровой класс наследуется от `BaseGameFilter` и добавляет поддержку специфичных для игры фильтров:

#### CS2Filter (CSGO)
- `float_min`, `float_max`: диапазон значений float (износа скина)
- `category`: категория предмета (Rifle, Knife, Pistol, etc.)
- `rarity`: редкость предмета (Covert, Classified, etc.)
- `exterior`: состояние предмета (Factory New, Field-Tested, etc.)
- `stattrak`: наличие StatTrak (true/false)
- `souvenir`: является ли предмет сувенирным (true/false)

#### Dota2Filter
- `hero`: герой (Pudge, Juggernaut, etc.)
- `rarity`: редкость (Immortal, Arcana, etc.)
- `slot`: слот предмета (Weapon, Head, etc.)
- `quality`: качество (Genuine, Unusual, Exalted, etc.)
- `tradable`: возможность обмена (true/false)

#### TF2Filter
- `class`: класс (Scout, Soldier, etc.)
- `quality`: качество (Unusual, Genuine, etc.)
- `type`: тип предмета (Hat, Weapon, etc.)
- `effect`: эффект (для необычных предметов)
- `killstreak`: уровень счетчика убийств
- `australium`: является ли предмет золотым (true/false)

#### RustFilter
- `category`: категория
- `type`: тип предмета
- `rarity`: редкость

### Фабрика фильтров

Класс `FilterFactory` предоставляет удобные методы для получения экземпляра нужного фильтра:

```python
filter_obj = FilterFactory.get_filter("csgo")  # Получение фильтра CS2/CSGO
```

## Основные функции

### apply_filters_to_items

```python
filtered_items = apply_filters_to_items(items, "csgo", {"min_price": 100, "category": "Knife"})
```

Фильтрует список предметов по указанным параметрам. Аргументы:
- `items`: список предметов для фильтрации
- `game`: идентификатор игры (`csgo`, `dota2`, `tf2` или `rust`)
- `filters`: словарь фильтров 

### build_api_params_for_game

```python
api_params = build_api_params_for_game("csgo", {"min_price": 50, "category": "Rifle"})
```

Создает словарь параметров для API-запросов к DMarket. Аргументы:
- `game`: идентификатор игры
- `filters`: словарь фильтров

## Примеры использования

### Фильтрация списка предметов

```python
from dmarket.game_filters import apply_filters_to_items

# Фильтрация списка предметов CS2/CSGO
items = [
    {"title": "AK-47 | Redline (Field-Tested)", "price": {"USD": 15}, "category": "Rifle"},
    {"title": "AWP | Dragon Lore (Factory New)", "price": {"USD": 5000}, "category": "Sniper Rifle"},
    # ... другие предметы
]

# Получение винтовок дороже $100
filtered_items = apply_filters_to_items(
    items,
    "csgo",
    {"min_price": 100, "category": "Rifle"}
)

# Получение Factory New предметов
filtered_items = apply_filters_to_items(
    items,
    "csgo",
    {"exterior": "Factory New"}
)
```

### Создание параметров API-запроса

```python
from dmarket.game_filters import build_api_params_for_game

# Создание параметров для поиска CS2 ножей StatTrak
api_params = build_api_params_for_game(
    "csgo",
    {
        "category": "Knife",
        "stattrak": True,
        "min_price": 200,
        "max_price": 500
    }
)

# Запрос к API DMarket (пример)
# response = dmarket_api.get_items_for_sale(api_params)
```

### Использование фильтров напрямую

```python
from dmarket.game_filters import FilterFactory

# Получение фильтра для CS2/CSGO
cs2_filter = FilterFactory.get_filter("csgo")

# Проверка соответствия предмета фильтрам
item = {
    "title": "StatTrak™ AK-47 | Redline (Field-Tested)",
    "price": {"USD": 75},
    "category": "Rifle",
    "rarity": "Classified"
}

passes = cs2_filter.apply_filters(
    item,
    {
        "min_price": 50,
        "category": "Rifle",
        "stattrak": True
    }
)  # Вернет True

# Получение читаемого описания фильтра
description = cs2_filter.get_filter_description({
    "min_price": 50,
    "category": "Rifle",
    "stattrak": True
})  # "Price from $50.00, Category: Rifle, StatTrak™"
```

## Расширение системы фильтров

Для добавления поддержки новой игры необходимо:

1. Создать новый класс, наследуясь от `BaseGameFilter`
2. Определить поддерживаемые фильтры в `supported_filters`
3. Реализовать методы `apply_filters()`, `build_api_params()` и `get_filter_description()`
4. Добавить новый фильтр в словарь `_filters` в классе `FilterFactory`

Пример:

```python
class NewGameFilter(BaseGameFilter):
    game_name = "new_game"
    supported_filters = BaseGameFilter.supported_filters + [
        "custom_filter1", "custom_filter2"
    ]
    
    def apply_filters(self, item, filters):
        if not super().apply_filters(item, filters):
            return False
            
        # Логика проверки кастомных фильтров
        # ...
        
        return True
        
    # ... другие методы
    
# Добавление в фабрику
FilterFactory._filters["new_game"] = NewGameFilter
```

## Заключение

Модуль `game_filters.py` предоставляет мощный и расширяемый механизм фильтрации предметов из различных игр. Он существенно упрощает работу с предметами DMarket и позволяет легко интегрировать фильтрацию в другие модули системы.
