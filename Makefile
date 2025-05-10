# Makefile для управления проектом DMarket Bot

.PHONY: help install dev clean lint format test coverage docs run check-types add-types all

PYTHON := python
PIP := $(PYTHON) -m pip
VENV := .venv
VENV_BIN := $(VENV)/bin
VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_PYTHON) -m pip

# Цель по умолчанию, показывает справку
help:
	@echo "Доступные команды:"
	@echo "  help         - показать эту справку"
	@echo "  install      - установить зависимости"
	@echo "  dev          - установить зависимости для разработки"
	@echo "  clean        - очистить временные файлы и кэш"
	@echo "  lint         - проверить код с помощью линтеров"
	@echo "  format       - отформатировать код"
	@echo "  test         - запустить тесты"
	@echo "  coverage     - проверить покрытие кода тестами"
	@echo "  docs         - сгенерировать документацию"
	@echo "  run          - запустить бота"
	@echo "  check-types  - проверить типы с помощью mypy"
	@echo "  add-types    - добавить аннотации типов"
	@echo "  all          - выполнить все проверки (lint, test, coverage, docs)"

# Создание и активация виртуального окружения
$(VENV):
	$(PYTHON) -m venv $(VENV)

# Установка зависимостей
install: $(VENV)
	$(VENV_PIP) install -r requirements.txt

# Установка зависимостей для разработки
dev: $(VENV)
	$(VENV_PIP) install -e ".[dev]"

# Очистка временных файлов и кэша
clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ .mypy_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete

# Проверка кода с помощью линтеров
lint: $(VENV)
	$(VENV_BIN)/ruff check src tests scripts
	$(VENV_BIN)/black --check src tests scripts

# Форматирование кода
format: $(VENV)
	$(VENV_PYTHON) scripts/format_code.py

# Запуск тестов
test: $(VENV)
	$(VENV_BIN)/pytest

# Проверка покрытия кода тестами
coverage: $(VENV)
	$(VENV_BIN)/pytest --cov=src --cov-report=html --cov-report=term

# Генерация документации
docs: $(VENV)
	$(VENV_BIN)/sphinx-build -b html docs/source docs/build/html

# Запуск бота
run: $(VENV)
	$(VENV_PYTHON) run_bot.py

# Проверка типов с помощью mypy
check-types: $(VENV)
	$(VENV_BIN)/mypy src

# Добавление аннотаций типов
add-types: $(VENV)
	$(VENV_PYTHON) scripts/apply_type_annotations.py

# Выполнение всех проверок
all: lint test coverage docs
