"""Скрипт для запуска тестов с проверкой покрытия кода.

Этот скрипт автоматизирует запуск различных наборов тестов
и генерирует отчеты о покрытии кода.
"""

import argparse
import subprocess
import sys


def run_command(command):
    """Запускает команду и выводит результат."""
    print(f"Выполняется: {command}")
    process = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True,
    )

    print(process.stdout)
    if process.stderr:
        print(f"Ошибки: {process.stderr}")

    return process.returncode


def run_tests(module=None, html_report=False, xml_report=False):
    """Запускает тесты для указанного модуля или всех тестов."""
    cmd = ["python -m pytest"]

    # Добавляем параметры покрытия
    cmd.append("--cov=src")

    # Выбираем модуль для тестирования
    if module:
        if module == "dmarket":
            cmd.append("tests/dmarket/")
        elif module == "telegram_bot":
            cmd.append("tests/telegram_bot/")
        elif module == "utils":
            cmd.append("tests/utils/")
        else:
            cmd.append(f"tests/{module}")

    # Добавляем параметры для отчетов
    if html_report:
        cmd.append("--cov-report=html")
    if xml_report:
        cmd.append("--cov-report=xml")

    # Добавляем параметр для вывода непокрытых строк кода
    cmd.append("--cov-report=term-missing:skip-covered")

    # Запускаем команду
    return run_command(" ".join(cmd))


def main():
    """Основная функция скрипта."""
    parser = argparse.ArgumentParser(description="Запуск тестов и проверка покрытия кода")
    parser.add_argument(
        "--module",
        "-m",
        choices=["dmarket", "telegram_bot", "utils", "all"],
        default="all",
        help="Модуль для тестирования",
    )
    parser.add_argument(
        "--html",
        "-html",
        action="store_true",
        help="Генерировать HTML-отчет",
    )
    parser.add_argument(
        "--xml",
        "-xml",
        action="store_true",
        help="Генерировать XML-отчет",
    )

    args = parser.parse_args()

    # Запускаем тесты для выбранного модуля
    module = None if args.module == "all" else args.module
    return run_tests(module, args.html, args.xml)


if __name__ == "__main__":
    sys.exit(main())
