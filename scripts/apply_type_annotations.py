#!/usr/bin/env python3
"""Скрипт для добавления аннотаций типов в проект.

Использует pytype (или аналогичный инструмент) для анализа типов 
и автоматического добавления аннотаций типов в файлы проекта.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Получаем корневую директорию проекта
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Директории для обработки
DEFAULT_DIRECTORIES = ["src"]


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
    tools = ["mypy", "pytype"]
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


def add_type_annotations(directories, check_only=False):
    """Добавляет аннотации типов в файлы в указанных директориях."""
    for directory in directories:
        dir_path = PROJECT_ROOT / directory
        if not dir_path.exists():
            print(f"Директория {directory} не найдена. Пропускаем.")
            continue

        print(f"Обработка директории {directory}...")

        # Запуск mypy для проверки типов
        mypy_cmd = ["mypy", str(dir_path)]

        print("Запуск MyPy для проверки типов...")
        success, output = run_command(mypy_cmd, cwd=PROJECT_ROOT)
        if output.strip():
            print(output)

        if check_only:
            continue

        # Запуск pytype для генерации аннотаций типов
        pytype_cmd = [
            "pytype",
            "--output-errors-csv",
            "pytype_errors.csv",
            "--keep-going",
            "--analyze-annotated",
            "--generate-config",
            str(dir_path),
        ]

        print("Запуск PyType для анализа типов...")
        success, output = run_command(pytype_cmd, cwd=PROJECT_ROOT)
        if output.strip():
            print(output)

        print(f"Обработка директории {directory} завершена.\n")

        # Запуск pytype для добавления аннотаций
        if not check_only:
            annotate_cmd = [
                "pytype",
                "--annotate-existing",
                "--keep-going",
                str(dir_path),
            ]

            print("Добавление аннотаций типов...")
            success, output = run_command(annotate_cmd, cwd=PROJECT_ROOT)
            if output.strip():
                print(output)


def main():
    """Основная функция скрипта."""
    parser = argparse.ArgumentParser(description="Добавление аннотаций типов в проект.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Только проверить типы без добавления аннотаций",
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=DEFAULT_DIRECTORIES,
        help=f"Директории для обработки (по умолчанию: {', '.join(DEFAULT_DIRECTORIES)})",
    )

    args = parser.parse_args()

    if not check_tools():
        sys.exit(1)

    print("=" * 60)
    print("Запуск добавления аннотаций типов:")
    print(f"Режим: {'проверка' if args.check else 'добавление'}")
    print(f"Директории: {', '.join(args.directories)}")
    print("=" * 60)

    add_type_annotations(args.directories, args.check)

    print("=" * 60)
    print("Добавление аннотаций типов завершено!")
    print("=" * 60)


if __name__ == "__main__":
    main()
