# Руководство по запуску тестов

В этом руководстве объясняется, как правильно запустить тесты в проекте DMarket Tools с корректной настройкой PYTHONPATH.

## Настройка PYTHONPATH

Тесты в проекте DMarket Tools используют относительные импорты из корневой директории проекта. Для корректной работы этих импортов необходимо добавить корневую директорию проекта в PYTHONPATH.

### Windows (PowerShell)

```powershell
# Временная настройка в текущей сессии
$env:PYTHONPATH = "$(Get-Location)"

# Запуск всех тестов
python -m pytest tests

# Запуск конкретного теста
python -m pytest tests/test_bot_v2.py
```

### Linux/macOS (Bash)

```bash
# Временная настройка в текущей сессии
export PYTHONPATH=$(pwd)

# Запуск всех тестов
python -m pytest tests

# Запуск конкретного теста
python -m pytest tests/test_bot_v2.py
```

## Использование VS Code

### Настройка VS Code для тестирования

1. Откройте VS Code settings.json (Ctrl+Shift+P -> Preferences: Open Settings (JSON))
2. Добавьте следующие настройки:

```json
{
    "python.testing.pytestEnabled": true,
    "python.envFile": "${workspaceFolder}/.env",
    "python.analysis.extraPaths": ["${workspaceFolder}"]
}
```

3. Теперь вы можете использовать встроенную в VS Code панель тестирования для запуска тестов.

## Запуск конкретных тестов

### Запуск по имени модуля

```
python -m pytest tests/test_bot_v2.py
```

### Запуск по имени теста

```
python -m pytest tests/test_bot_v2.py::test_start_command
```

### Запуск с повышенной детализацией

```
python -m pytest tests/test_bot_v2.py -v
```

## Отладка тестов

### Отладка в VS Code

1. Установите точки останова в коде теста
2. Выберите тест в панели тестирования VS Code
3. Щелкните правой кнопкой мыши и выберите "Debug Test"

### Отладка с помощью pdb

```
python -m pytest tests/test_bot_v2.py --pdb
```

## Дополнительные опции pytest

- `--pdb`: Вход в отладчик при ошибке
- `-v`: Подробный вывод
- `-xvs`: Отключает захват вывода, полезно для отладки
- `--no-header --no-summary -q`: Минимальный вывод
- `-k "expression"`: Запускает тесты, соответствующие выражению

## Примечания

- Тесты используют асинхронные функции, требующие поддержки pytest-asyncio
- Файл конфигурации pytest находится в `pyproject.toml`
- При запуске тестов через VS Code убедитесь, что выбран правильный интерпретатор Python
