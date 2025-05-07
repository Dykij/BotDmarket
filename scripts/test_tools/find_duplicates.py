import os
import re
import sys
from collections import defaultdict


def analyze_test_files(directory):
    """Анализирует имена тестовых файлов для поиска дублирующихся.

    Args:
        directory: Директория с тестами

    """
    # Список всех тестовых файлов
    test_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                test_files.append(file)

    print(f"Найдено {len(test_files)} тестовых файлов.")

    # Группировка по базовому имени (без суффиксов)
    base_names = defaultdict(list)
    for file in test_files:
        # Извлекаем базовое имя (test_X.py или test_X_*.py -> X)
        match = re.match(r"test_(.+?)(?:_.*)?\.py", file)
        if match:
            base_name = match.group(1)
            base_names[base_name].append(file)

    # Вывод групп файлов с одинаковым базовым именем
    print("\nГруппы файлов с одинаковым базовым именем:")
    print("-" * 50)

    for base_name, files in base_names.items():
        if len(files) > 1:  # Если есть несколько файлов с одним базовым именем
            print(f"\nБазовое имя: {base_name}")
            for file in files:
                print(f"  - {file}")
            print(f"  => Рекомендуется объединить в: test_{base_name}.py")


if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    analyze_test_files(directory)
