#!/usr/bin/env python
"""Скрипт для анализа и объединения дублирующихся тестовых файлов.
Помогает идентифицировать похожие тестовые файлы, чтобы затем их можно было объединить.
"""

import os
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher


def get_test_files(directory: str) -> list[str]:
    """Получить список тестовых файлов в указанной директории.

    Args:
        directory: Путь к директории с тестовыми файлами

    Returns:
        Список относительных путей к тестовым файлам

    """
    test_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, file), directory)
                test_files.append(rel_path)
    return test_files


def get_file_content(file_path: str) -> str:
    """Получить содержимое файла."""
    try:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Ошибка при чтении {file_path}: {e}")
        return ""


def find_similar_files(
    test_files: list[str],
    base_dir: str,
    threshold: float = 0.6,
) -> dict[str, list[tuple[str, float]]]:
    """Найти похожие файлы на основе их содержимого.

    Args:
        test_files: Список путей к тестовым файлам
        base_dir: Базовая директория
        threshold: Минимальный порог сходства (от 0 до 1)

    Returns:
        Словарь, где ключи - базовые имена файлов, значения - списки
        похожих файлов и степень их сходства

    """
    # Извлекаем базовые имена файлов (без суффиксов)
    base_names = {}
    for file in test_files:
        match = re.match(r"test_(.+?)(?:_.*)?\.py", os.path.basename(file))
        if match:
            base_name = match.group(1)
            if base_name not in base_names:
                base_names[base_name] = []
            base_names[base_name].append(file)

    # Для каждой группы базовых имен находим похожие файлы
    similar_files = defaultdict(list)
    for base_name, files in base_names.items():
        if len(files) > 1:  # Если есть несколько файлов с одним базовым именем
            for i, file1 in enumerate(files):
                content1 = get_file_content(os.path.join(base_dir, file1))
                for j, file2 in enumerate(files):
                    if i >= j:
                        continue
                    content2 = get_file_content(os.path.join(base_dir, file2))
                    similarity = SequenceMatcher(None, content1, content2).ratio()
                    if similarity >= threshold:
                        similar_files[base_name].append((file1, file2, similarity))

    return similar_files


def group_similar_files(
    similar_files: dict[str, list[tuple[str, str, float]]],
) -> dict[str, list[list[str]]]:
    """Группировка похожих файлов для объединения.

    Args:
        similar_files: Словарь с похожими файлами

    Returns:
        Словарь с группами файлов для объединения

    """
    groups = {}
    for base_name, similarities in similar_files.items():
        # Строим граф схожести
        graph = defaultdict(set)
        for file1, file2, _ in similarities:
            graph[file1].add(file2)
            graph[file2].add(file1)

        # Находим компоненты связности (группы похожих файлов)
        visited = set()
        file_groups = []

        for file in graph:
            if file in visited:
                continue

            group = []
            stack = [file]
            while stack:
                current = stack.pop()
                if current not in visited:
                    visited.add(current)
                    group.append(current)
                    stack.extend(neighbor for neighbor in graph[current] if neighbor not in visited)

            if group:
                file_groups.append(sorted(group))

        groups[base_name] = file_groups

    return groups


def print_suggested_merges(groups: dict[str, list[list[str]]]) -> None:
    """Вывести предложения по объединению файлов.

    Args:
        groups: Словарь с группами файлов для объединения

    """
    print("\nРекомендации по объединению тестовых файлов:")
    print("=" * 50)

    for base_name, file_groups in groups.items():
        if not file_groups:
            continue

        print(f"\nМодуль: {base_name}")
        print("-" * 50)

        for i, group in enumerate(file_groups, 1):
            if len(group) > 1:
                print(f"Группа {i}:")
                for file in group:
                    print(f"  - {file}")
                # Предлагаем оставить файл без суффикса или с самым простым суффиксом
                target_file = None
                for file in group:
                    if re.match(f"test_{base_name}\\.py$", os.path.basename(file)):
                        target_file = file
                        break
                if not target_file:
                    # Если нет файла без суффикса, выбираем файл с самым коротким именем
                    target_file = min(group, key=lambda x: len(x))
                print(f"  => Объединить в: {target_file}")


def analyze_test_purposes(test_files: List[str], base_dir: str) -> Dict[str, List[str]]:
    """Анализирует цели тестовых файлов на основе содержимого docstrings и импортов.

    Args:
        test_files: Список тестовых файлов
        base_dir: Базовая директория

    Returns:
        Словарь где ключ - тестируемый модуль, значение - список тестовых файлов

    """
    module_tests = defaultdict(list)

    for file in test_files:
        path = os.path.join(base_dir, file)
        content = get_file_content(path)

        # Ищем import или from ... import в файле
        imports = set()
        for line in content.split("\n"):
            if line.startswith(("import ", "from ")):
                match = re.search(r"from\s+([\w\.]+)\s+import", line)
                if match:
                    module = match.group(1)
                    imports.add(module)
                match = re.search(r"import\s+([\w\.]+)", line)
                if match:
                    module = match.group(1)
                    imports.add(module)

        # Ищем комментарий с упоминанием модуля
        docstring_match = re.search(
            r'""".*?(для|модул[а-я]+)\s+([\w\.]+).*?"""',
            content,
            re.DOTALL,
        )
        tested_module = None
        if docstring_match:
            module_name = docstring_match.group(2)
            tested_module = module_name

        if tested_module:
            module_tests[tested_module].append(file)
        else:
            # Если в комментариях не указан модуль, группируем по общим импортам
            for imp in imports:
                if imp.startswith("src.") or imp.startswith("tests."):
                    module_tests[imp].append(file)

    return module_tests


def print_module_tests(module_tests: Dict[str, List[str]]) -> None:
    """Выводит группы тестов, относящиеся к одному модулю."""
    print("\nТесты, относящиеся к одному модулю:")
    print("=" * 50)

    for module, files in module_tests.items():
        if len(files) > 1:
            print(f"\nМодуль: {module}")
            print("-" * 50)
            for file in sorted(files):
                print(f"  - {file}")


def main() -> None:
    """Основная функция."""
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"Анализируем тестовые файлы в {base_dir}...")
    test_files = get_test_files(base_dir)
    print(f"Найдено {len(test_files)} тестовых файлов.")

    # Анализ по сходству содержимого
    similar_files = find_similar_files(test_files, base_dir)
    groups = group_similar_files(similar_files)
    print_suggested_merges(groups)

    # Анализ по назначению тестов
    module_tests = analyze_test_purposes(test_files, base_dir)
    print_module_tests(module_tests)


if __name__ == "__main__":
    main()
