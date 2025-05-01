'
# Проверка модуля game_filters
import os, sys

# Добавляем путь к родительскому каталогу в список путей поиска модулей
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Импортируем функции из модуля game_filters
try:
    from src.dmarket.game_filters import FilterFactory
    
    # Проверка доступности функций
    games = FilterFactory.get_supported_games()
    print("Поддерживаемые игры:", ", ".join(games))
    
    # Создание фильтра для CS2/CSGO
    filter_obj = FilterFactory.get_filter("csgo")
    print("Фильтр создан:", filter_obj.__class__.__name__)
    print("Поддерживаемые фильтры:", ", ".join(filter_obj.supported_filters))
    
    print("Тест успешно завершен!")
except Exception as e:
    print(f"Ошибка при импорте или использовании модуля: {type(e).__name__}: {e}")
'
