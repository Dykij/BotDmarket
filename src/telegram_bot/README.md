# DMarket Telegram Bot

## Обзор

DMarket Telegram Bot - это полнофункциональный бот для анализа рынка DMarket, поиска арбитражных возможностей и автоматизации сбора данных о ценах предметов. Бот предоставляет интерфейс для доступа к различным видам анализа через Telegram.

## Основные возможности

- 🔍 **Поиск арбитражных возможностей** - находите выгодные предложения для покупки и продажи с расчетом прибыли
- 📊 **Аналитика рынка** - отслеживайте тренды, волатильность и изменения цен на различных рынках
- 🔔 **Уведомления** - получайте оповещения о выгодных предложениях и изменениях рынка
- 💼 **Управление API ключами** - безопасное хранение и использование API ключей DMarket
- 👤 **Профили пользователей** - разные уровни доступа и персонализированные настройки

## Архитектура

Бот имеет модульную архитектуру, позволяющую легко добавлять новые функции и поддерживать существующие:

```
src/telegram_bot/
├── handlers/           # Обработчики команд и коллбэков
├── utils/              # Вспомогательные утилиты и форматтеры
├── keyboards.py        # Унифицированное создание клавиатур
├── pagination.py       # Менеджер пагинации для результатов
├── initialization.py   # Инициализация и настройка бота
├── user_profiles.py    # Управление профилями пользователей
└── smart_notifier.py   # Интеллектуальные уведомления
```

## Быстрый старт

### Установка и настройка

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Настройте переменные окружения в `.env` файле:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   DMARKET_PUBLIC_KEY=your_dmarket_public_key
   DMARKET_SECRET_KEY=your_dmarket_secret_key
   ```

3. Запустите бота:
   ```bash
   python run_bot.py
   ```

### Примеры использования

#### Создание клавиатуры с пагинацией

```python
from src.telegram_bot.keyboards import create_pagination_keyboard

# Создание клавиатуры пагинации
keyboard = create_pagination_keyboard(
    current_page=1,
    total_pages=5,
    prefix="items_",
    with_nums=True,
    back_button=True,
    back_text="« Назад",
    back_callback="main_menu"
)

# Использование в сообщении
await message.reply_text("Результаты:", reply_markup=keyboard)
```

#### Работа с пагинацией

```python
from src.telegram_bot.pagination import pagination_manager

# Сохранение результатов для пагинации
pagination_manager.add_items_for_user(user_id, results, "opportunities")

# Получение текущей страницы
items, current_page, total_pages = pagination_manager.get_page(user_id)

# Переход к следующей странице
pagination_manager.next_page(user_id)

# Форматирование текущей страницы
formatted_text = pagination_manager.format_current_page(
    user_id,
    content_type="opportunities"
)
```

#### Работа с API клиентом

```python
from src.telegram_bot.utils.api_client import create_api_client, create_api_client_from_env

# Создание клиента из переменных окружения
api_client = create_api_client_from_env()

# Создание клиента с явными ключами
api_client = create_api_client(
    public_key="your_public_key",
    secret_key="your_secret_key"
)

# Выполнение запроса
balance = await api_client.get_balance()
```

#### Форматирование данных

```python
from src.telegram_bot.utils.formatters import format_opportunities, format_market_items

# Форматирование арбитражных возможностей
formatted_text = format_opportunities(opportunities, current_page, items_per_page)

# Форматирование рыночных предметов
formatted_text = format_market_items(
    items,
    current_page,
    items_per_page,
    show_price_change=True
)
```

#### Обработка ошибок

```python
from src.telegram_bot.utils.error_handler import handle_api_error, safe_api_call

# Обработка API ошибок
try:
    result = await api_client.get_items()
except Exception as e:
    error_message = await handle_api_error(e)
    await message.reply_text(f"Произошла ошибка: {error_message}")

# Безопасный вызов API с обработкой ошибок
result = await safe_api_call(
    api_client.get_items,
    default_value=[],
    notify_user=True,
    update=update
)
```

#### Проверка прав доступа

```python
from src.telegram_bot.user_profiles import check_user_access, require_access_level

# Проверка доступа в функции
if await check_user_access(update, context, "advanced_arbitrage"):
    # Код для доступа к расширенному арбитражу
    ...

# Использование декоратора для проверки доступа
@require_access_level("basic_arbitrage")
async def arbitrage_command(update, context):
    # Эта функция будет выполнена только если у пользователя есть доступ
    ...
```

## Расширение функциональности

### Добавление нового обработчика команд

1. Создайте новый файл в директории `handlers/`:

```python
# src/telegram_bot/handlers/my_feature_handler.py

from telegram import Update
from telegram.ext import CallbackContext

async def my_feature_command(update: Update, context: CallbackContext) -> None:
    """Обработчик новой команды."""
    await update.message.reply_text("Это новая функция!")

def register_handlers(dispatcher):
    """Регистрирует обработчики."""
    dispatcher.add_handler(CommandHandler("my_feature", my_feature_command))
```

2. Зарегистрируйте обработчик в основном файле запуска:

```python
# run_bot.py
from src.telegram_bot.handlers.my_feature_handler import register_handlers

# В функции регистрации обработчиков
register_handlers(application)
```

## Требования к безопасности

- Не сохраняйте API ключи в коде или истории коммитов
- Используйте модуль `user_profiles` для безопасного хранения чувствительных данных
- Проверяйте права доступа для всех защищенных функций
- Логируйте все критические операции для аудита

## Troubleshooting

### Ошибки подключения к API

1. Проверьте корректность API ключей в переменных окружения
2. Убедитесь, что API DMarket доступен
3. Проверьте соединение с интернетом

### Проблемы с ботом

1. Проверьте токен бота в переменных окружения
2. Убедитесь, что бот не запущен в другом процессе
3. Проверьте наличие прав у бота в группах
