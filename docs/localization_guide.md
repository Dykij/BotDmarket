# Руководство по локализации и пользовательским профилям в DMarket Bot

## Обзор

В этом руководстве представлена информация о системе локализации и пользовательских профилях, добавленных в DMarket Bot. Эти улучшения позволяют боту предоставлять контент на разных языках и сохранять индивидуальные настройки для каждого пользователя.

## Поддерживаемые языки

В текущей версии поддерживаются следующие языки:

- 🇷🇺 Русский (ru) - основной язык
- 🇬🇧 English (en)
- 🇪🇸 Español (es)
- 🇩🇪 Deutsch (de)

## Структура пользовательских профилей

Каждый пользователь бота имеет собственный профиль, который содержит следующие настройки:

```json
{
  "language": "ru",
  "api_key": "ваш_api_ключ",
  "api_secret": "ваш_секретный_ключ",
  "auto_trading_enabled": false,
  "trade_settings": {
    "min_profit": 2.0,
    "max_price": 50.0,
    "max_trades": 3,
    "risk_level": "medium"
  },
  "last_activity": 1619712345.67
}
```

### Описание полей

- **language**: Выбранный язык пользователя (ru, en, es, de)
- **api_key**: Публичный ключ API DMarket
- **api_secret**: Секретный ключ API DMarket
- **auto_trading_enabled**: Флаг, включена ли автоматическая торговля
- **trade_settings**: Настройки торговли
  - **min_profit**: Минимальная прибыль для автоматической торговли (в долларах)
  - **max_price**: Максимальная цена предмета для автоматической покупки (в долларах)
  - **max_trades**: Максимальное количество сделок за одну сессию
  - **risk_level**: Уровень риска (low, medium, high)
- **last_activity**: Время последней активности (Unix timestamp)

## Использование в коде

### Получение локализованного текста

Для получения локализованного текста используйте функцию `get_localized_text`:

```python
from src.telegram_bot.settings_handlers import get_localized_text

# Получение локализованного приветствия для пользователя
welcome_text = get_localized_text(
    user_id=123456789,
    key="welcome",
    user="John Doe"  # Параметры для подстановки в строку
)
```

### Получение профиля пользователя

Для получения или создания профиля пользователя:

```python
from src.telegram_bot.settings_handlers import get_user_profile

# Получение профиля пользователя
profile = get_user_profile(user_id=123456789)

# Доступ к настройкам пользователя
language = profile["language"]
api_key = profile["api_key"]
trade_settings = profile["trade_settings"]
```

### Сохранение изменений в профиле

После внесения изменений в профиль не забудьте сохранить его:

```python
from src.telegram_bot.settings_handlers import get_user_profile, save_user_profiles

# Получение профиля
profile = get_user_profile(user_id=123456789)

# Обновление настроек
profile["language"] = "en"
profile["trade_settings"]["min_profit"] = 3.0

# Сохранение изменений
save_user_profiles()
```

## Профили риска

Система поддерживает три предустановленных профиля риска:

### Низкий риск (low)
- Минимальная прибыль: $1.00
- Максимальная цена покупки: $30.00
- Максимум сделок: 2

### Средний риск (medium)
- Минимальная прибыль: $2.00
- Максимальная цена покупки: $50.00
- Максимум сделок: 5

### Высокий риск (high)
- Минимальная прибыль: $5.00
- Максимальная цена покупки: $100.00
- Максимум сделок: 10

## Миграция пользовательских данных

Для миграции существующих пользовательских данных в новую структуру используется скрипт `migrate_users.py`. Запустите его следующим образом:

```bash
python scripts/migrate_users.py --data-dir path/to/data --backup
```

Флаг `--backup` создаст резервные копии существующих данных перед миграцией.

## Добавление новых языков

Чтобы добавить новый язык:

1. Откройте файл `localization.py`
2. Добавьте новый язык в словарь `LANGUAGES`
3. Создайте соответствующий подсловарь в `LOCALIZATIONS` с переводами всех строк
4. Убедитесь, что все ключи из базового языка (ru) присутствуют в новом языке

Пример добавления нового языка:

```python
# Добавление в LANGUAGES
LANGUAGES = {
    "ru": "Русский",
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "fr": "Français"  # Новый язык
}

# Добавление в LOCALIZATIONS
LOCALIZATIONS["fr"] = {
    "welcome": "Bonjour, {user}! 👋\n\nJe suis un bot d'arbitrage DMarket...",
    # ... другие строки ...
}
```

## Интеграция с основным модулем бота

Чтобы интегрировать систему локализации и пользовательских профилей с основным модулем бота, добавьте следующий код в файл `bot_v2.py`:

```python
from src.telegram_bot.settings_handlers import register_localization_handlers

# В функции main():
register_localization_handlers(application)
```

## Вопросы и ответы

### Q: Что произойдет, если запрошенный ключ отсутствует в выбранном языке?
A: Если ключ отсутствует в выбранном языке, система попробует найти его в русском языке (базовый язык). Если ключ отсутствует и там, будет возвращена строка "[Missing: ключ]".

### Q: Где хранятся пользовательские профили?
A: Пользовательские профили хранятся в файле `user_profiles.json` в директории `telegram_bot`.

### Q: Как изменить настройки для профилей риска?
A: Вы можете изменить настройки профилей риска в файле `settings_handlers.py` в функции `settings_callback` в ветке `elif data.startswith("risk:")`.
