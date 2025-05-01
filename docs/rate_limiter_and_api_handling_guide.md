# Руководство по обработке ошибок API и управлению лимитами запросов

## Введение

Данное руководство описывает новый механизм обработки ошибок API и управления лимитами запросов, реализованный в DMarket Bot. Механизм предназначен для надежной обработки различных ошибок API, автоматических повторных попыток и соблюдения ограничений скорости API.

## Компоненты системы

Система состоит из трех основных компонентов:

1. **RateLimiter** (`src/utils/rate_limiter.py`) - класс для контроля скорости запросов к API
2. **APIError и обработчики** (`src/utils/api_error_handling.py`) - классы исключений и функции для обработки ошибок API
3. **Утилиты для запросов к API** (`src/utils/dmarket_api_utils.py`) - вспомогательные функции для выполнения запросов с учетом ограничений и обработки ошибок

## RateLimiter

`RateLimiter` контролирует частоту запросов к API DMarket:

```python
from src.utils.rate_limiter import RateLimiter

# Создаем лимитер запросов
limiter = RateLimiter(is_authorized=True)

# Использование лимитера
async def some_function():
    # Ожидаем разрешения на запрос
    await limiter.wait_for_call('market')
    
    # Выполняем запрос
    # ...
    
    # Обновляем состояние лимитера после запроса
    limiter.update_after_call('market')
    
    # Если получена ошибка 429 (превышение лимита)
    limiter.mark_rate_limited('market', retry_after=60)
```

### Типы эндпоинтов

При использовании лимитера можно указывать тип эндпоинта для более точного управления:

- `market` - запросы к маркету (10 запросов в секунду)
- `trade` - торговые операции (5 запросов в секунду) 
- `user` - пользовательские данные (3 запроса в секунду)
- `other` - другие запросы (15 запросов в секунду)

## Обработка ошибок API

Система обрабатывает различные типы ошибок API:

```python
from src.utils.api_error_handling import APIError, retry_request

# Использование retry_request с обработкой ошибок
async def make_api_call():
    try:
        result = await retry_request(
            request_func=some_api_function,
            max_retries=3
        )
        return result
    except APIError as e:
        if e.status_code == 429:  # Превышение лимита
            # Обработка превышения лимита
            print(f"Превышен лимит запросов. Повтор через {e.retry_after} секунд")
        elif e.status_code == 401:  # Ошибка авторизации
            # Обработка ошибки авторизации
            print("Ошибка авторизации")
        # И т.д.
```

### Типы исключений

- `APIError` - базовый класс для всех ошибок API
- `AuthenticationError` - ошибки авторизации (401)
- `RateLimitExceeded` - превышение лимита запросов (429)
- `NotFoundError` - ресурс не найден (404)
- `ServerError` - серверная ошибка (5xx)
- `BadRequestError` - ошибка в запросе клиента (400)

## Утилиты для запросов к API

`execute_api_request` предоставляет удобный способ выполнения запросов с полной обработкой ошибок и соблюдением лимитов:

```python
from src.utils.dmarket_api_utils import execute_api_request
from src.dmarket.dmarket_api import DMarketAPI

# Пример использования
async def check_api_status():
    # Определяем функцию для запроса
    async def api_call():
        api = DMarketAPI()
        return await api.ping()
    
    # Выполняем запрос через утилиту
    try:
        result = await execute_api_request(
            request_func=api_call,
            endpoint_type="other",
            max_retries=2
        )
        return result
    except APIError as e:
        print(f"API ошибка: {e.message}")
        return None
```

## Интеграция с Telegram-ботом

В Telegram-боте обработка ошибок API интегрирована в обработчики команд:

```python
async def some_command_handler(update, context):
    try:
        # Используем execute_api_request
        result = await execute_api_request(
            request_func=some_api_function,
            endpoint_type="market",
            max_retries=2
        )
        
        # Обработка успешного результата
        await update.message.reply_text("Успешно!")
        
    except APIError as e:
        # Формируем понятное сообщение об ошибке для пользователя
        if e.status_code == 429:
            error_message = "⏱️ Превышен лимит запросов. Пожалуйста, подождите."
        elif e.status_code == 401:
            error_message = "🔐 Ошибка авторизации. Проверьте API ключи."
        else:
            error_message = f"❌ Ошибка DMarket API: {e.message}"
            
        await update.message.reply_text(error_message)
```

## Глобальный обработчик ошибок

Для обработки неперехваченных ошибок в боте используется глобальный обработчик:

```python
async def error_handler(update, context):
    error = context.error
    
    if isinstance(error, APIError):
        # Обработка ошибок API
        if error.status_code == 429:
            error_message = "Превышен лимит запросов."
        elif error.status_code == 401:
            error_message = "Ошибка авторизации."
        # И т.д.
    else:
        error_message = "Произошла ошибка при обработке запроса."
        
    # Отправляем сообщение пользователю
    if update and update.effective_message:
        await update.effective_message.reply_text(error_message)
```

## Рекомендации по использованию

1. **Всегда используйте `execute_api_request`** для запросов к API DMarket вместо прямых вызовов.

2. **Обрабатывайте исключения `APIError`** в обработчиках команд для предоставления пользователям понятных сообщений.

3. **Используйте подходящий `endpoint_type`** для корректного управления лимитами запросов:
   - `market` - для запросов к рынку
   - `trade` - для операций купли-продажи
   - `user` - для пользовательских данных
   - `other` - для остальных запросов

4. **Настройте `max_retries`** в зависимости от критичности запроса.

5. **Добавляйте локализацию сообщений об ошибках** для разных языков, используемых в боте.

## Пример полной интеграции

```python
async def get_market_items(game_id, limit=10):
    """Получение предметов с рынка с полной обработкой ошибок."""
    
    # Функция для выполнения запроса
    async def fetch_items():
        api = DMarketAPI()
        return await api.get_market_items(game=game_id, limit=limit)
    
    # Выполнение запроса через утилиту
    try:
        return await execute_api_request(
            request_func=fetch_items,
            endpoint_type="market",
            max_retries=3
        )
    except APIError as e:
        logger.error(f"Ошибка при получении предметов рынка: {e.message}")
        # Переформатируем ошибку и пробрасываем дальше
        if e.status_code == 429:
            raise APIError("Слишком много запросов. Пожалуйста, повторите позже.", 
                          e.status_code, e.response_data)
        else:
            raise  # Пробрасываем оригинальную ошибку
```

## Тестирование

Для тестирования обработки ошибок API используйте моки и предоставленные тестовые файлы:

- `test_rate_limiter.py` - тесты для RateLimiter
- `test_rate_limiter_api_errors.py` - тесты для обработки ошибок API
- `test_bot_v2_api_error_handling.py` - тесты для интеграции обработки ошибок в боте

## Заключение

Новая система обработки ошибок API и управления лимитами запросов обеспечивает:

1. Соблюдение лимитов запросов DMarket API
2. Автоматические повторные попытки при временных ошибках
3. Понятные сообщения для пользователей при ошибках API
4. Централизованную обработку всех типов ошибок API

Используйте описанные компоненты для обеспечения надежной работы вашего бота с API DMarket.
