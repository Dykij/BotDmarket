# Инструкция по использованию фильтрации для арбитража

## Обзор функциональности

Добавлена возможность фильтрации предметов из разных игр (CS:GO, Dota 2, TF2, RUST) с различными параметрами для каждой игры.

## Поддерживаемые игры

1. **CS:GO** (cs2)
2. **Dota 2**
3. **Team Fortress 2** (tf2)
4. **RUST**

## Фильтры для CS:GO

- **float_min**, **float_max** - диапазон изношенности (float) скина
- **category** - категория предмета (rifle, pistol, knife, sniper rifle, smg и т.д.)
- **item_type** - тип предмета для поиска в названии (например, "knife", "awp" и т.д.)
- **stattrak** - наличие StatTrak (true/false)
- **rarity** - редкость предмета (Covert, Classified, Restricted, и т.д.)

Пример:
```python
filters = {
    "float_min": 0.0,
    "float_max": 0.07,
    "category": "pistol",
    "rarity": "Covert"
}
```

## Фильтры для Dota 2

- **rarity** - редкость предмета (Immortal, Arcana, Legendary и т.д.)
- **hero** - герой, для которого предназначен предмет
- **quality** - качество предмета (Genuine, Unusual и т.д.)
- **item_type** - категория предмета (weapon, courier и т.д.)

Пример:
```python
filters = {
    "hero": "Zeus",
    "rarity": "Arcana"
}
```

## Фильтры для RUST

- **category** - категория предмета (weapon, construction и т.д.)
- **rarity** - редкость предмета (Common, Rare и т.д.)
- **origin** - источник предмета (Twitch Drop, In-Game Purchase и т.д.)

Пример:
```python
filters = {
    "category": "weapon",
    "origin": "Twitch Drop"
}
```

## Фильтры для Team Fortress 2

- **quality** - качество предмета (Unique, Strange, Unusual и т.д.)
- **class** - класс персонажа (soldier, heavy, scout и т.д.)
- **effect** - эффект предмета (для Unusual предметов)
- **killstreak** - тип killstreak (specialized killstreak, professional killstreak)

Пример:
```python
filters = {
    "class": "soldier",
    "quality": "strange",
    "killstreak": "specialized killstreak"
}
```

## Использование в коде

### С использованием класса ArbitrageScanner

```python
from src.telegram_bot.arbitrage_scanner import ArbitrageScanner

scanner = ArbitrageScanner()

# С фильтрацией
items = await scanner.find_profitable_items(
    game="csgo",
    min_profit_percentage=10.0,
    max_items=5,
    filters={
        "float_min": 0.0,
        "float_max": 0.1,
        "category": "rifle"
    }
)

# Без фильтрации
items = await scanner.find_profitable_items(
    game="dota2",
    min_profit_percentage=15.0,
    max_items=10
)
```

### С использованием функции find_arbitrage_opportunities

```python
from src.telegram_bot.arbitrage_scanner import find_arbitrage_opportunities

# С фильтрацией
items = find_arbitrage_opportunities(
    game="csgo",
    min_profit_percentage=10.0,
    max_items=5,
    filters={
        "float_min": 0.0, 
        "float_max": 0.1
    }
)

# Без фильтрации
items = find_arbitrage_opportunities(
    game="tf2",
    min_profit_percentage=15.0,
    max_items=10
)
```

## Управление запросами к API (RateLimiter)

Добавлен класс `RateLimiter` для управления лимитами запросов к API DMarket. Класс автоматически отслеживает лимиты для разных типов эндпойнтов и обеспечивает соблюдение ограничений.

### Встроенные лимиты
- Для неавторизованных пользователей:
  - signin: 20 запросов в минуту
  - fee: 2 запроса в секунду
  - market: 2 запроса в секунду
  - last_sales: 2 запроса в секунду
  - other: 6 запросов в секунду

- Для авторизованных пользователей:
  - signin: 20 запросов в минуту
  - fee: 110 запросов в секунду
  - market: 10 запросов в секунду
  - last_sales: 6 запросов в секунду
  - other: 20 запросов в секунду
