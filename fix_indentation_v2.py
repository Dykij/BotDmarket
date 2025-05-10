#!/usr/bin/env python3
"""
Улучшенный скрипт для исправления отступов в файле dmarket_api.py
"""
import re

def find_problematic_section(content):
    """Находит проблемный раздел кода с неправильными отступами"""
    problem_found = False
    start_line = 0
    end_line = len(content)
    
    for i, line in enumerate(content):
        if "Формат 1: DMarket API 2023+" in line:
            start_line = i
            problem_found = True
            # Ищем конец этого блока
            for j in range(i, len(content)):
                if "Формат 2:" in content[j]:
                    end_line = j
                    break
            break
    
    return problem_found, start_line, end_line

def fix_section(content, start_line, end_line):
    """Исправляет отступы в проблемном разделе кода"""
    base_indent = len(content[start_line]) - len(content[start_line].lstrip())
    correct_content = []
    
    # Обрабатываем строку заголовка блока
    correct_content.append(content[start_line])
    
    # Раздел начинается с elif блока, устанавливаем правильный отступ
    inside_try_block = False
    inside_if_block = False
    current_try_indent = base_indent
    current_if_indent = base_indent + 4
    expected_indent = base_indent + 4
    
    for i in range(start_line + 1, end_line):
        line = content[i]
        stripped = line.lstrip()
        current_indent = len(line) - len(stripped)
        
        # Определяем текущий контекст и ожидаемые отступы
        if stripped.startswith("try:"):
            inside_try_block = True
            current_try_indent = current_indent
            expected_indent = current_indent + 4
        elif inside_try_block and (stripped.startswith("except") or not stripped):
            inside_try_block = False
            expected_indent = current_try_indent
        
        if stripped.startswith("if "):
            inside_if_block = True
            current_if_indent = current_indent
            expected_indent = current_indent + 4
        elif inside_if_block and stripped.startswith("else:"):
            expected_indent = current_if_indent
        elif inside_if_block and (not stripped or current_indent <= current_if_indent):
            inside_if_block = False
            expected_indent = current_try_indent if inside_try_block else base_indent + 4
        
        # Проверяем, нужно ли исправлять отступ этой строки
        if stripped:
            if inside_try_block:
                if stripped.startswith("if ") or stripped.startswith("else:"):
                    expected_indent = current_try_indent + 4
                elif not stripped.startswith("except"):
                    expected_indent = current_try_indent + 8 if inside_if_block else current_try_indent + 4
            elif inside_if_block:
                expected_indent = current_if_indent + 4
            else:
                expected_indent = base_indent + 4
        
        # Исправляем отступ строки
        if stripped and current_indent != expected_indent and not stripped.startswith("elif ") and not stripped.startswith("except"):
            fixed_line = " " * expected_indent + stripped
            print(f"Исправляю строку {i+1}: {line.strip()[:30]}...")
            correct_content.append(fixed_line + '\n')
        else:
            correct_content.append(line)
    
    # Собираем все обратно
    for i in range(start_line, end_line):
        idx = i - start_line
        if idx < len(correct_content):
            content[i] = correct_content[idx]
    
    return content

def is_valid_python(code):
    """Проверяет, является ли код синтаксически правильным Python кодом"""
    try:
        compile(code, '<string>', 'exec')
        return True
    except SyntaxError:
        return False

def fix_all_indentation_issues(file_path, output_path):
    """Целенаправленно исправляет известные проблемы с отступами в файле dmarket_api.py"""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.readlines()
    
    # Сначала ищем и исправляем проблемный раздел
    problem_found, start_line, end_line = find_problematic_section(content)
    if problem_found:
        content = fix_section(content, start_line, end_line)
    
    # Специально исправляем известную проблему с отступом self._request
    for i, line in enumerate(content):
        if "response = await self._request(" in line and i > 0 and "try:" in content[i-1]:
            try_indent = len(content[i-1]) - len(content[i-1].lstrip())
            current_indent = len(line) - len(line.lstrip())
            if current_indent != try_indent + 4:
                fixed_line = " " * (try_indent + 4) + line.lstrip()
                content[i] = fixed_line
                print(f"Исправляю отступ для вызова self._request в строке {i+1}")
                
                # Также исправляем отступы для параметров запроса
                for j in range(i+1, i+5):
                    if j < len(content) and not content[j].lstrip().startswith("if"):
                        param_line = content[j]
                        param_stripped = param_line.lstrip()
                        if param_stripped and not param_stripped.startswith(")"):
                            fixed_param = " " * (try_indent + 8) + param_stripped
                            content[j] = fixed_param
                            print(f"Исправляю отступ для параметра в строке {j+1}")
    
    # Записываем исправленный контент в выходной файл
    with open(output_path, 'w', encoding='utf-8') as file:
        file.writelines(content)
    
    # Проверяем, является ли файл синтаксически правильным Python кодом
    full_code = ''.join(content)
    is_valid = is_valid_python(full_code)
    if is_valid:
        print(f"Исправления сохранены в {output_path} и код синтаксически правильный!")
    else:
        print(f"Исправления сохранены в {output_path}, но в коде все еще есть синтаксические ошибки.")
    
    return is_valid

# Создаем полностью исправленную версию файла, заменяя проблемный блок кода
def create_fixed_file(input_file, output_file):
    """Создает полностью исправленную версию файла"""
    with open(input_file, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Находим и заменяем весь проблемный блок
    problematic_block = r"""                # Формат 1: DMarket API 2023\+ с usdAvailableToWithdraw и usd
                elif "usdAvailableToWithdraw" in response:
                    try:
                        usd_value = response\["usdAvailableToWithdraw"\]
                        if isinstance\(usd_value, str\):
                            # Строка может быть в формате "5\.00" или "\$5\.00"
                            usd_available = float\(usd_value\.replace\('\$', ''\)\.strip\(\)\) \* 100
                        else:
                            usd_available = float\(usd_value\) \* 100
                        
                        # Также проверяем общий баланс \(если есть\)
            if "usd" in response:
                            usd_value = response\["usd"\]
                            if isinstance\(usd_value, str\):
                                usd_total = float\(usd_value\.replace\('\$', ''\)\.strip\(\)\) \* 100
                            else:
                                usd_total = float\(usd_value\) \* 100
                        else:
                            usd_total = usd_available"""
    
    fixed_block = """                # Формат 1: DMarket API 2023+ с usdAvailableToWithdraw и usd
                elif "usdAvailableToWithdraw" in response:
                    try:
                        usd_value = response["usdAvailableToWithdraw"]
                        if isinstance(usd_value, str):
                            # Строка может быть в формате "5.00" или "$5.00"
                            usd_available = float(usd_value.replace('$', '').strip()) * 100
                        else:
                            usd_available = float(usd_value) * 100
                        
                        # Также проверяем общий баланс (если есть)
                        if "usd" in response:
                            usd_value = response["usd"]
                            if isinstance(usd_value, str):
                                usd_total = float(usd_value.replace('$', '').strip()) * 100
                            else:
                                usd_total = float(usd_value) * 100
                        else:
                            usd_total = usd_available"""
    
    # Заменяем проблемный блок
    fixed_content = re.sub(problematic_block, fixed_block, content, flags=re.DOTALL)
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(fixed_content)
    
    # Проверяем, является ли файл синтаксически правильным Python кодом
    is_valid = is_valid_python(fixed_content)
    if is_valid:
        print(f"Исправления сохранены в {output_file} и код синтаксически правильный!")
    else:
        print(f"Исправления сохранены в {output_file}, но в коде все еще есть синтаксические ошибки.")
    
    return is_valid

if __name__ == "__main__":
    input_file = "src/dmarket/dmarket_api.py"
    temp_file = "src/dmarket/dmarket_api_temp.py"
    output_file = "src/dmarket/dmarket_api_fixed.py"
    
    # Пробуем исправить методом поиска и замены
    print("Пробуем метод поиска и замены проблемного блока...")
    is_success = create_fixed_file(input_file, output_file)
    
    if not is_success:
        print("Метод поиска и замены не сработал. Пробуем метод исправления отступов...")
        is_success = fix_all_indentation_issues(input_file, output_file)
    
    if is_success:
        print("Исправления успешно выполнены. Проверьте файл перед использованием.")
    else:
        print("Автоматическое исправление не удалось. Требуется ручное вмешательство.") 