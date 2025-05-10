#!/usr/bin/env python
"""Скрипт для запуска проверки кода с помощью Ruff и MyPy.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Запускает команду и выводит результат."""
    print(f"\n{'-'*80}\n{description}\n{'-'*80}")
    result = subprocess.run(cmd, shell=True, text=True)
    return result.returncode == 0


def main():
    """Запускает проверки кода."""
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    # Переходим в корень проекта
    os.chdir(project_root)

    success = True

    # Проверка типов с mypy
    cmd_mypy = "python -m mypy src"
    if not run_command(cmd_mypy, "Запуск проверки типов с MyPy"):
        success = False

    # Проверка стиля с ruff
    cmd_ruff = "python -m ruff check src"
    if not run_command(cmd_ruff, "Запуск проверки стиля с Ruff"):
        success = False

    # Форматирование кода с ruff
    cmd_ruff_format = "python -m ruff format src"
    if not run_command(cmd_ruff_format, "Форматирование кода с Ruff"):
        success = False

    if success:
        print("\n✅ Все проверки пройдены успешно!")
        return 0
    print("\n❌ Некоторые проверки не прошли. Исправьте ошибки перед коммитом.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
