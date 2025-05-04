# DMarket Tools & Signature Builder

Инструменты и примеры для работы с DMarket API: генерация подписей, автоматизация торговли, Telegram-бот, арбитраж и тестирование.

## Основные возможности
- Генерация подписей для запросов к DMarket API (см. `src/dmarket/dmarket_api.py`)
- Примеры работы с публичными и приватными эндпоинтами
- Telegram-бот для автоматического арбитража (`src/telegram_bot/`)
- Модули для анализа рынка, истории продаж, фильтрации и автоматизации
- Поддержка тестирования (pytest)
- Инструменты для контроля качества кода (Ruff, Black, mypy)

## Быстрый старт

1. Клонируйте репозиторий и создайте виртуальное окружение:
   ```pwsh
   git clone https://github.com/yourusername/dmarket-tools.git
   cd dmarket-tools
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Настройте переменные окружения (создайте `.env`):
   ```env
   DMARKET_PUBLIC_KEY=your_public_key
   DMARKET_SECRET_KEY=your_secret_key
   TELEGRAM_BOT_TOKEN=your_telegram_token
   ```

3. Запустите пример работы с API:
   ```pwsh
   python scripts/dmarket_api_example.py
   ```

4. Запуск Telegram-бота:
   ```pwsh
   python -m src.telegram_bot.bot_v2
   ```

## Документация
- [Официальная документация DMarket API](https://docs.dmarket.com/v1/swagger.html)
- [Руководство по лимитам и обработке ошибок](docs/rate_limiter_and_api_handling_guide.md)
- [Руководство по Telegram-боту](docs/telegram_bot_guide.md)
- [Улучшения арбитража](docs/arbitrage_improvements.md)
- [VS Code настройки](docs/vscode_setup.md)
- [Рекомендации по Copilot](COPILOT_GUIDE.md)
- [Структура проекта](docs/project_structure.md)
- [Руководство по тестированию](docs/testing_guide.md)
- [Логирование и обработка ошибок](docs/logging_and_error_handling.md)
- [Отчет о внесенных улучшениях](docs/additional_improvements_report.md)

## Структура проекта

```
dmarket-tools/
├── src/                   # Основной код проекта
│   ├── dmarket/           # API клиент и логика работы с DMarket
│   ├── telegram_bot/      # Реализация Telegram-бота
│   └── utils/             # Вспомогательные модули и утилиты
├── tests/                 # Тесты
├── scripts/               # Примеры и утилиты
├── docs/                  # Документация
├── config/                # Конфигурационные файлы (устаревшие)
└── .env                   # Файл с переменными окружения (создать вручную)
```

## Настройка окружения для разработки

### Настройка PYTHONPATH

Для корректной работы импортов при запуске тестов и скриптов, убедитесь, что корневая директория проекта добавлена в PYTHONPATH:

```pwsh
# Временная настройка в текущей сессии
$env:PYTHONPATH = "$PWD"

# Для Linux/macOS:
# export PYTHONPATH=$(pwd)
```

В VS Code также можно настроить запуск тестов с корректным PYTHONPATH через settings.json:

```json
{
    "python.testing.pytestEnabled": true,
    "python.envFile": "${workspaceFolder}/.env",
    "python.analysis.extraPaths": ["${workspaceFolder}"]
}
```

### Настройка mypy

Для статической проверки типов используется mypy. Конфигурация находится в `mypy.ini` в корне проекта.

## Тестирование
Для запуска тестов:
```pwsh
pytest tests
```

## Качество кода
- Форматирование: `black .`
- Линтинг: `ruff check .`
- Проверка типов: `mypy .`

## Примеры
Пример генерации подписи для приватного запроса:
```python
from src.dmarket.dmarket_api import DMarketAPI

api = DMarketAPI(public_key, secret_key)
headers = api._generate_signature("POST", "/exchange/v1/target/create", body_json)
```

Пример использования системы логирования и обработки ошибок:
```python
from src.utils.logging_utils import get_logger, log_exceptions
from src.utils.exception_handling import handle_exceptions, APIError

# Создаем логгер с контекстом
logger = get_logger("my_module", {"user_id": 12345})

# Используем декоратор для автоматического логирования исключений
@log_exceptions
def my_function():
    logger.info("Выполняется действие", extra={"context": {"action": "check_balance"}})
    # ...

# Обработка исключений
@handle_exceptions(default_error_message="Ошибка при работе с API")
async def make_api_request():
    try:
        # ...
    except Exception as e:
        raise APIError("Ошибка при запросе", status_code=500)
```

Пример обработки ошибок и лимитов: см. [docs/rate_limiter_and_api_handling_guide.md](docs/rate_limiter_and_api_handling_guide.md)

---
Проект поддерживает автоматическую проверку качества кода и тесты через GitHub Actions (см. `.github/workflows/ci.yml`).
