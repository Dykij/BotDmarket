"""
Проверка импорта класса PaginationManager.
"""
import sys
print(f"Python path: {sys.path}")

try:
    from src.telegram_bot.pagination import PaginationManager
    print("Успешный импорт PaginationManager")
    print(f"Class attributes: {dir(PaginationManager)}")
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    
    # Пробуем импортировать модуль
    try:
        import src.telegram_bot.pagination as pagination_module
        print(f"Модуль импортирован: {pagination_module}")
        print(f"Атрибуты модуля: {dir(pagination_module)}")
    except ImportError as e2:
        print(f"Ошибка импорта модуля: {e2}")
