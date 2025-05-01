# Makefile для проекта DMarket Tools
# Используйте это для запуска общих задач

.PHONY: setup test lint format clean run

# Настройка окружения
setup:
	python -m pip install -r requirements.txt

# Запуск тестов
test:
	python -m pytest tests

# Проверка кода линтером
lint:
	ruff check src tests scripts
	mypy src

# Форматирование кода
format:
	ruff format src tests scripts

# Очистка временных файлов
clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info

# Запуск бота
run:
	python run.py
