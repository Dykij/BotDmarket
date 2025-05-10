#!/usr/bin/env python3
"""
Скрипт для удаления дублирующихся тестовых файлов после объединения.

Этот скрипт удаляет устаревшие или дублирующиеся тестовые файлы,
содержимое которых было перенесено в объединенные файлы:
- test_api_unified.py
- test_bot_unified.py
- test_arbitrage_unified.py
"""

import os
import sys
import argparse
from pathlib import Path

# Список файлов для удаления
FILES_TO_REMOVE = [
    # Файлы арбитража
    "test_auto_arbitrage.py",
    "test_arbitrage.py",
    "test_arbitrage_scanner.py",
    "test_auto_arbitrage_simple.py",
    "test_arbitrage_boost.py",
    "test_arbitrage_callback.py",
    "test_arbitrage_callback_impl.py",
    "test_arbitrage_sales_analysis.py",
    "test_arbitrage_sales_opportunities.py",
    "test_auto_arbitrage_scanner.py",
    "test_auto_arbitrage_updated.py",
    "test_demo_auto_arbitrage.py",
    
    # Файлы Telegram бота
    "test_bot_v2.py",
    "test_bot_v2_api_error_handling.py",
    "test_bot_v2_arbitrage.py",
    "test_bot_v2_auto_arbitrage.py",
    "test_bot_v2_commands.py",
    "test_bot_v2_commands_sync.py",
    "test_bot_v2_dmarket.py",
    "test_bot_v2_formatting.py",
    "test_bot_v2_functions.py",
    "test_bot_v2_pagination.py",
    "test_bot_v2_updated.py",
    "test_telegram_bot.py",
    
    # Файлы DMarket API
    "test_dmarket_api.py",
    "test_dmarket_api_balance.py",
    "test_dmarket_api_patches.py",
    
    # Файлы обработки ошибок
    "test_error_handling.py",
    "test_error_handling_new.py",
    "test_error_handling_original.py",
    "test_error_handlers.py",
    
    # Файлы фильтров игр
    "test_game_filters.py",
    "test_game_filter_handlers_updated.py",
    
    # Файлы ограничителя скорости
    "test_rate_limiter_api_errors.py",
    "test_rate_limiter_fixed_v3.py",
    
    # Файлы истории продаж
    "test_sales_history.py",
    "test_sales_analysis_callbacks_fixed.py",
]

def get_tests_directory():
    """Определяет путь к директории tests."""
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    return project_root / "tests"

def clean_tests(dry_run=False):
    """Удаляет устаревшие тестовые файлы.
    
    Args:
        dry_run (bool): Если True, только показывает, какие файлы будут удалены, 
                        но не удаляет их.
    """
    tests_dir = get_tests_directory()
    print(f"Директория тестов: {tests_dir}")
    
    # Выводим список существующих файлов
    existing_files = [f.name for f in tests_dir.glob("*.py")]
    print(f"Найдено {len(existing_files)} тестовых файлов в корневой директории")
    
    # Проверяем наличие объединенных файлов
    unified_files = ["test_api_unified.py", "test_bot_unified.py", "test_arbitrage_unified.py"]
    for f in unified_files:
        file_path = tests_dir / f
        if file_path.exists():
            print(f"✓ Найден объединенный файл: {f}")
        else:
            print(f"✗ Не найден объединенный файл: {f}")
    
    missing_files = [f for f in unified_files if not (tests_dir / f).exists()]
    
    if missing_files:
        print(f"Ошибка: следующие объединенные файлы не найдены: {', '.join(missing_files)}")
        print("Убедитесь, что они существуют, прежде чем удалять дублирующиеся файлы.")
        return False
    
    # Удаляем файлы
    files_to_remove_count = 0
    for filename in FILES_TO_REMOVE:
        file_path = tests_dir / filename
        if file_path.exists():
            files_to_remove_count += 1
            if dry_run:
                print(f"Будет удален: {file_path}")
            else:
                try:
                    os.remove(file_path)
                    print(f"Удален: {file_path}")
                except Exception as e:
                    print(f"Ошибка при удалении {file_path}: {e}")
    
    if files_to_remove_count == 0:
        print("Не найдено ни одного файла для удаления.")
    else:
        print(f"Найдено {files_to_remove_count} файлов для удаления.")
    
    return True

def main():
    """Основная функция."""
    parser = argparse.ArgumentParser(description="Удаление дублирующихся тестовых файлов")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Только показать файлы, которые будут удалены, но не удалять их")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("Режим симуляции. Файлы не будут удалены.")
    
    success = clean_tests(dry_run=args.dry_run)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main() 