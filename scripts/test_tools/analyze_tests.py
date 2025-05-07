#!/usr/bin/env python
"""
Скрипт для анализа тестовых файлов и обнаружения дублирований.
"""

import os
import re
import sys
from collections import defaultdict


def get_test_files(directory):
    """Получает список файлов тестов.
    
    Args:
        directory (str): Путь к директории тестов
        
    Returns:
        list: Список путей к тестовым файлам
    """
    test_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                test_files.append(os.path.join(root, file))
    return test_files


def get_file_content(file_path):
    """Читает содержимое файла.
    
    Args:
        file_path (str): Путь к файлу
        
    Returns:
        str: Содержимое файла или пустая строка при ошибке
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Ошибка при чтении {file_path}: {e}")
        return ""


def parse_docstring(content):
    """Извлекает информацию из docstring файла.
    
    Args:
        content (str): Содержимое файла
        
    Returns:
        str or None: Название тестируемого модуля или None
    """
    docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
    if not docstring_match:
        return None
    
    docstring = docstring_match.group(1)
    
    # Поиск упоминания модуля в docstring
    module_match = re.search(r'(?:для|module|модул[а-я]+)\s+([\w\.]+)', 
                           docstring, re.IGNORECASE)
    if module_match:
        return module_match.group(1)
    return None


def extract_imports(content):
    """Извлекает импорты из файла.
    
    Args:
        content (str): Содержимое файла
        
    Returns:
        list: Список импортируемых модулей
    """
    imports = []
    for line in content.split("\n"):
        if line.startswith("from"):
            match = re.search(r"from\s+([\w\.]+)\s+import", line)
            if match:
                imports.append(match.group(1))
        elif line.startswith("import"):
            match = re.search(r"import\s+([\w\.]+)", line)
            if match:
                imports.append(match.group(1))
    return imports


def group_test_files(test_files):
    """Группирует тестовые файлы по базовым именам.
    
    Args:
        test_files (list): Список путей к тестовым файлам
        
    Returns:
        dict: Словарь групп файлов
    """
    base_groups = defaultdict(list)
    module_groups = defaultdict(list)
    
    for file_path in test_files:
        filename = os.path.basename(file_path)
        content = get_file_content(file_path)
        
        # Группировка по базовому имени (без суффиксов _fixed, _updated и т.д.)
        base_match = re.match(r"test_([\w]+)(?:_.*)?\.py$", filename)
        if base_match:
            base_name = base_match.group(1)
            base_groups[base_name].append(file_path)
        
        # Группировка по тестируемому модулю из docstring
        module_name = parse_docstring(content)
        if module_name:
            module_groups[module_name].append(file_path)
        else:
            # Если модуль не найден в docstring, пробуем определить по импортам
            imports = extract_imports(content)
            for imp in imports:
                if imp.startswith("src."):
                    module_groups[imp].append(file_path)
                    break
    
    return base_groups, module_groups


def print_suggestions(base_groups, module_groups):
    """Выводит рекомендации по объединению файлов.
    
    Args:
        base_groups (dict): Группы файлов по базовым именам
        module_groups (dict): Группы файлов по модулям
    """
    print("\n=== Файлы с похожими именами ===\n")
    for base_name, files in base_groups.items():
        if len(files) > 1:
            print(f"Базовое имя: {base_name}")
            for file_path in files:
                print(f"  - {os.path.basename(file_path)}")
            print("  Рекомендация: объединить в один файл test_{}.py\n".format(base_name))
    
    print("\n=== Файлы, тестирующие один модуль ===\n")
    for module_name, files in module_groups.items():
        if len(files) > 1:
            print(f"Модуль: {module_name}")
            for file_path in files:
                print(f"  - {os.path.basename(file_path)}")
            print()


def main():
    """Основная функция скрипта."""
    if len(sys.argv) > 1:
        test_dir = sys.argv[1]
    else:
        test_dir = "tests"
    
    print(f"Анализируем тестовые файлы в директории: {test_dir}")
    test_files = get_test_files(test_dir)
    print(f"Найдено {len(test_files)} тестовых файлов.")
    
    base_groups, module_groups = group_test_files(test_files)
    
    print_suggestions(base_groups, module_groups)


if __name__ == "__main__":
    main()
