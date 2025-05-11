# Композитные действия для GitHub Actions

В этой директории содержатся композитные действия (composite actions) для использования в GitHub Actions workflows.

## Доступные действия

### setup-python-env

Настраивает Python-окружение, устанавливает зависимости и конфигурирует среду разработки.

#### Параметры

| Параметр | Описание | Обязательный | По умолчанию |
|----------|----------|:------------:|:------------:|
| `python-version` | Версия Python для использования | нет | `3.11` |
| `install-poetry` | Установить и использовать Poetry | нет | `false` |
| `install-dev-deps` | Установить зависимости для разработки | нет | `true` |
| `create-env-file` | Создать .env файл из .env.example | нет | `true` |

#### Пример использования

```yaml
- name: Setup Python environment
  uses: ./.github/actions/setup-python-env
  with:
    python-version: '3.11'
    install-poetry: 'true'
    install-dev-deps: 'true'
```

### security-check

Проверяет код и зависимости на наличие уязвимостей безопасности.

#### Параметры

| Параметр | Описание | Обязательный | По умолчанию |
|----------|----------|:------------:|:------------:|
| `python-version` | Версия Python для использования | нет | `3.11` |
| `scan-dependencies` | Проверять зависимости на уязвимости | нет | `true` |
| `scan-code` | Сканировать код на уязвимости | нет | `true` |
| `src-directory` | Директория с исходным кодом для сканирования | нет | `./src` |
| `fail-on-high` | Завершить с ошибкой при обнаружении критических уязвимостей | нет | `false` |
| `generate-report` | Генерировать отчет о безопасности | нет | `true` |

#### Пример использования

```yaml
- name: Run Security Check
  uses: ./.github/actions/security-check
  with:
    python-version: '3.11'
    scan-dependencies: 'true'
    scan-code: 'true'
    src-directory: './src'
    fail-on-high: 'false'
```

## Создание нового композитного действия

1. Создайте новую директорию в `.github/actions/` с названием действия
2. Создайте файл `action.yml` в этой директории, соблюдая [спецификацию GitHub](https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions)
3. Добавьте информацию о новом действии в этот README.md
4. Обновите GITHUB_ACTIONS_GUIDELINES.md, если ваше действие является рекомендованным для использования

## Дополнительная информация

Дополнительную информацию о работе с GitHub Actions можно найти в [GITHUB_ACTIONS_GUIDELINES.md](../../GITHUB_ACTIONS_GUIDELINES.md) в корне репозитория. 