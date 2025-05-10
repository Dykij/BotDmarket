#!/usr/bin/env python3
"""Скрипт для унификации стиля кода во всем проекте.

Использует ruff и black для форматирования кода в соответствии 
с настройками из pyproject.toml.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Получаем корневую директорию проекта
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Директории для форматирования
DEFAULT_DIRECTORIES = ["src", "tests", "scripts"]


def run_command(cmd, cwd=None):
    """Запускает команду и возвращает результат."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr


def check_tools():
    """Проверяет наличие необходимых инструментов."""
    tools = ["ruff", "black"]
    missing = []

    for tool in tools:
        success, _ = run_command([tool, "--version"])
        if not success:
            missing.append(tool)

    if missing:
        print(f"Ошибка: Не найдены следующие инструменты: {', '.join(missing)}")
        print("Установите их с помощью команды:")
        print(f"pip install {' '.join(missing)}")
        return False

    return True


def format_code(directories, check_only=False):
    """Форматирует код в указанных директориях."""
    for directory in directories:
        dir_path = PROJECT_ROOT / directory
        if not dir_path.exists():
            print(f"Директория {directory} не найдена. Пропускаем.")
            continue

        print(f"Обработка директории {directory}...")

        # Запуск Ruff для проверки и автоматического исправления
        ruff_cmd = ["ruff", "check", str(dir_path)]
        if not check_only:
            ruff_cmd.append("--fix")

        print(f"Запуск Ruff {'(проверка)' if check_only else '(исправление)'}...")
        success, output = run_command(ruff_cmd, cwd=PROJECT_ROOT)
        if output.strip():
            print(output)

        # Запуск Black для форматирования
        black_cmd = ["black", str(dir_path)]
        if check_only:
            black_cmd.append("--check")

        print(f"Запуск Black {'(проверка)' if check_only else '(форматирование)'}...")
        success, output = run_command(black_cmd, cwd=PROJECT_ROOT)
        if output.strip():
            print(output)

        print(f"Обработка директории {directory} завершена.\n")


def main():
    """Основная функция скрипта."""
    parser = argparse.ArgumentParser(description="Унификация стиля кода проекта.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Только проверить стиль кода без внесения изменений",
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=DEFAULT_DIRECTORIES,
        help=f"Директории для форматирования (по умолчанию: {', '.join(DEFAULT_DIRECTORIES)})",
    )

    args = parser.parse_args()

    if not check_tools():
        sys.exit(1)

    print("=" * 60)
    print("Запуск унификации стиля кода:")
    print(f"Режим: {'проверка' if args.check else 'форматирование'}")
    print(f"Директории: {', '.join(args.directories)}")
    print("=" * 60)

    format_code(args.directories, args.check)

    print("=" * 60)
    print("Унификация стиля кода завершена!")
    print("=" * 60)


if __name__ == "__main__":
    main()
