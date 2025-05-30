# Рекомендации по работе с GitHub Actions

## Общие принципы

1. **Согласованный подход к установке и запуску инструментов**
   - Используйте либо Poetry во всех workflow, либо прямые вызовы через pip/python
   - Избегайте смешивания различных подходов к управлению зависимостями в разных workflow
   - Для повторяющихся задач создавайте композитные действия в `.github/actions/`

2. **Тестирование workflow локально**
   - Перед отправкой на GitHub тестируйте workflow локально с помощью [act](https://github.com/nektos/act)
   - Команда: `act -j build` для запуска конкретной задачи

3. **Проверка prerequisites**
   - Всегда добавляйте проверку наличия необходимых файлов или условий перед выполнением критических команд
   - Используйте условия и обработку ошибок в shell-скриптах

4. **Безопасность и оптимизация**
   - Используйте `concurrency` для предотвращения параллельных запусков одинаковых workflow
   - Ограничивайте разрешения с помощью `permissions`
   - Используйте последние версии официальных действий (v4+ где возможно)

## Специфические рекомендации для Python-проектов

### Настройка Python-окружения

Используйте композитное действие `.github/actions/setup-python-env`:

```yaml
- name: Setup Python environment
  uses: ./.github/actions/setup-python-env
  with:
    python-version: '3.11'
    install-poetry: 'true'
    install-dev-deps: 'true'
```

Если нужно настроить вручную:

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'

- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    if [ -f requirements.txt ]; then
      pip install -r requirements.txt
    elif [ -f pyproject.toml ]; then
      pip install poetry
      poetry install
    else
      echo "Файл с зависимостями не найден!"
      exit 1
    fi
```

### Линтинг и форматирование

```yaml
- name: Lint with Ruff
  run: |
    # Убедитесь, что Ruff установлен
    pip install ruff==0.3.0
    python -m ruff check . --output-format=github
    
- name: Type check with MyPy
  run: |
    # Убедитесь, что MyPy установлен
    pip install mypy
    python -m mypy .
```

### Тестирование

```yaml
- name: Set up PYTHONPATH
  run: |
    echo "PYTHONPATH=$GITHUB_WORKSPACE:$PYTHONPATH" >> $GITHUB_ENV
    # Для Windows:
    # echo "PYTHONPATH=$env:GITHUB_WORKSPACE;$env:PYTHONPATH" >> $env:GITHUB_ENV

- name: Run tests
  run: |
    pytest -xvs --cov=src --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v4
  with:
    file: ./coverage.xml
    fail_ci_if_error: false
```

## Безопасность и обработка секретов

1. **Используйте секреты GitHub**
   - Храните чувствительные данные в секретах репозитория или организации
   - Обеспечьте наличие fallback-значений для тестирования:
     ```yaml
     env:
       API_KEY: ${{ secrets.API_KEY || 'test_key' }}
     ```

2. **Ограничивайте разрешения**
   ```yaml
   permissions:
     contents: read  # Только чтение содержимого репозитория
     issues: write   # Разрешение на создание issues
     # Другие разрешения по необходимости
   ```

3. **Сканирование зависимостей**
   - Регулярно проверяйте зависимости на наличие уязвимостей
   - Используйте GitHub Dependabot или специализированные инструменты

## Оптимизация производительности

1. **Эффективное кэширование**
   ```yaml
   - name: Set up cache
     uses: actions/cache@v4
     with:
       path: |
         ~/.cache/pip
         .venv
       key: ${{ runner.os }}-python-${{ matrix.python-version }}-${{ hashFiles('**/requirements.txt', '**/poetry.lock') }}
       restore-keys: |
         ${{ runner.os }}-python-${{ matrix.python-version }}-
   ```

2. **Управление параллелизмом**
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```

3. **Условное выполнение задач**
   ```yaml
   - name: Run intensive task
     if: github.event_name == 'push' && github.ref == 'refs/heads/main'
     run: ./intensive_task.sh
   ```

## Диагностика проблем

1. **Включите расширенное логирование**
   ```yaml
   - name: Debug info
     run: |
       python --version
       pip list
       echo $PYTHONPATH
   ```

2. **Используйте действие upload-artifact для сохранения логов**
   ```yaml
   - name: Archive logs
     if: success() || failure()  # Выполняется даже при неудаче
     uses: actions/upload-artifact@v4
     with:
       name: logs
       path: logs/
       retention-days: 5
   ```

## Непрерывная доставка

1. **Автоматическое развертывание документации**
   ```yaml
   - name: Deploy to GitHub Pages
     if: github.event_name == 'push' && github.ref == 'refs/heads/main'
     uses: peaceiris/actions-gh-pages@v3
     with:
       github_token: ${{ secrets.GITHUB_TOKEN }}
       publish_dir: ./docs/build/html
   ```

2. **Публикация пакетов**
   ```yaml
   - name: Build and publish
     if: startsWith(github.ref, 'refs/tags')
     run: |
       pip install build twine
       python -m build
       twine upload dist/*
     env:
       TWINE_USERNAME: ${{ secrets.PYPI_USERNAME }}
       TWINE_PASSWORD: ${{ secrets.PYPI_PASSWORD }}
   ```

## Шаблоны для типичных сценариев

### Матричная стратегия тестирования

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
      fail-fast: false
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python ${{ matrix.python-version }}
        uses: ./.github/actions/setup-python-env
        with:
          python-version: ${{ matrix.python-version }}
```

### Выполнение по расписанию

```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Еженедельно в полночь по воскресеньям
  workflow_dispatch:  # Разрешить ручной запуск
``` 