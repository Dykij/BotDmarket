"""Модуль для управления пагинацией результатов в Telegram-боте."""

import logging
from collections.abc import Callable
from typing import Any, List, Dict, Tuple, Optional, Union

from telegram import InlineKeyboardMarkup

from src.telegram_bot.keyboards import create_pagination_keyboard
from src.telegram_bot.utils.formatters import format_opportunities

logger = logging.getLogger(__name__)


class PaginationManager:
    """Менеджер пагинации для хранения и отображения страниц результатов."""

    def __init__(self, default_items_per_page: int = 5):
        """Инициализация менеджера пагинации.

        Args:
            default_items_per_page: Количество элементов на странице по умолчанию

        """
        self.items_by_user = {}  # Dict[int, List[Any]]
        self.current_page_by_user = {}  # Dict[int, int]
        self.mode_by_user = {}  # Dict[int, str]
        self.default_items_per_page = default_items_per_page
        self.user_settings = {}  # Dict[int, Dict[str, Any]]
        self.page_cache = {}  # Dict[int, Dict[int, Tuple[List[Any], int, int]]]

    def add_items_for_user(self, user_id: int, items: list[Any], mode: str = "default") -> None:
        """Добавляет элементы для пагинации конкретному пользователю.

        Args:
            user_id: Идентификатор пользователя
            items: Список элементов для пагинации
            mode: Режим пагинации (для разных типов содержимого)

        """
        self.items_by_user[user_id] = items
        self.current_page_by_user[user_id] = 0
        self.mode_by_user[user_id] = mode

        # Сбрасываем кэш при обновлении данных
        if user_id in self.page_cache:
            del self.page_cache[user_id]

    # Алиас для совместимости с вызовами add_items
    def add_items(self, user_id: int, items: list[Any], mode: str = "default") -> None:
        """Алиас для add_items_for_user

        Args:
            user_id: Идентификатор пользователя
            items: Список элементов для пагинации
            mode: Режим пагинации (для разных типов содержимого)

        """
        return self.add_items_for_user(user_id, items, mode)

    def get_items_per_page(self, user_id: int) -> int:
        """Возвращает количество элементов на странице для пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Количество элементов на странице

        """
        if user_id in self.user_settings and "items_per_page" in self.user_settings[user_id]:
            return self.user_settings[user_id]["items_per_page"]
        return self.default_items_per_page

    def set_items_per_page(self, user_id: int, value: int) -> None:
        """Устанавливает количество элементов на странице для пользователя.

        Args:
            user_id: Идентификатор пользователя
            value: Количество элементов на странице (от 1 до 20)

        """
        # Ограничиваем значение между 1 и 20
        value = max(1, min(value, 20))

        # Инициализируем настройки пользователя, если их еще нет
        if user_id not in self.user_settings:
            self.user_settings[user_id] = {}

        self.user_settings[user_id]["items_per_page"] = value

        # Сбрасываем кэш при изменении настроек
        if user_id in self.page_cache:
            del self.page_cache[user_id]

        # Сбрасываем текущую страницу
        self.current_page_by_user[user_id] = 0

        logger.debug(f"Установлено элементов на странице для {user_id}: {value}")

    def get_page(self, user_id: int) -> tuple[list[Any], int, int]:
        """Возвращает текущую страницу элементов для пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Кортеж из (элементы_страницы, номер_страницы, всего_страниц)

        """
        # Проверяем наличие данных
        if user_id not in self.items_by_user or not self.items_by_user[user_id]:
            return [], 0, 0

        # Получаем текущую страницу
        current_page = self.current_page_by_user.get(user_id, 0)

        # Проверяем кэш
        if user_id in self.page_cache and current_page in self.page_cache[user_id]:
            return self.page_cache[user_id][current_page]

        # Если нет в кэше, вычисляем
        items = self.items_by_user[user_id]
        items_per_page = self.get_items_per_page(user_id)

        # Вычисляем общее количество страниц
        total_pages = (len(items) + items_per_page - 1) // items_per_page

        # Проверяем корректность текущей страницы
        if current_page >= total_pages:
            current_page = total_pages - 1
            self.current_page_by_user[user_id] = current_page

        if current_page < 0:
            current_page = 0
            self.current_page_by_user[user_id] = current_page

        # Вычисляем диапазон элементов для текущей страницы
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(items))

        # Получаем элементы текущей страницы
        page_items = items[start_idx:end_idx]
        result = (page_items, current_page, total_pages)

        # Кэшируем результат
        if user_id not in self.page_cache:
            self.page_cache[user_id] = {}
        self.page_cache[user_id][current_page] = result

        return result

    def next_page(self, user_id: int) -> tuple[list[Any], int, int]:
        """Переходит к следующей странице для пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Кортеж из (элементы_страницы, номер_страницы, всего_страниц)

        """
        if user_id not in self.items_by_user:
            return [], 0, 0

        # Получаем текущую страницу и общее количество страниц
        current_page = self.current_page_by_user.get(user_id, 0)
        items = self.items_by_user[user_id]
        items_per_page = self.get_items_per_page(user_id)
        total_pages = (len(items) + items_per_page - 1) // items_per_page

        # Увеличиваем номер текущей страницы, если возможно
        if current_page < total_pages - 1:
            self.current_page_by_user[user_id] = current_page + 1

        return self.get_page(user_id)

    def prev_page(self, user_id: int) -> tuple[list[Any], int, int]:
        """Переходит к предыдущей странице для пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Кортеж из (элементы_страницы, номер_страницы, всего_страниц)

        """
        if user_id not in self.items_by_user:
            return [], 0, 0

        # Уменьшаем номер текущей страницы, если возможно
        current_page = self.current_page_by_user.get(user_id, 0)

        if current_page > 0:
            self.current_page_by_user[user_id] = current_page - 1

        return self.get_page(user_id)

    def filter_items(self, user_id: int, filter_func: Callable[[Any], bool]) -> None:
        """Фильтрует элементы для пользователя по условию.

        Args:
            user_id: Идентификатор пользователя
            filter_func: Функция фильтрации, принимает элемент -> bool

        """
        if user_id in self.items_by_user:
            items = self.items_by_user[user_id]
            filtered = list(filter(filter_func, items))
            self.items_by_user[user_id] = filtered
            self.current_page_by_user[user_id] = 0  # Сбрасываем страницу

            # Сбрасываем кэш
            if user_id in self.page_cache:
                del self.page_cache[user_id]

    def sort_items(
        self, user_id: int, key_func: Callable[[Any], Any], reverse: bool = False
    ) -> None:
        """Сортирует элементы для пользователя.

        Args:
            user_id: Идентификатор пользователя
            key_func: Функция для извлечения ключа для сортировки
            reverse: Сортировка в обратном порядке если True

        """
        if user_id in self.items_by_user:
            self.items_by_user[user_id] = sorted(
                self.items_by_user[user_id],
                key=key_func,
                reverse=reverse,
            )
            self.current_page_by_user[user_id] = 0  # Сбрасываем страницу

            # Сбрасываем кэш
            if user_id in self.page_cache:
                del self.page_cache[user_id]

    def get_mode(self, user_id: int) -> str:
        """Возвращает текущий режим пагинации для пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Режим пагинации

        """
        return self.mode_by_user.get(user_id, "default")

    def clear_user_data(self, user_id: int) -> None:
        """Очищает все данные пользователя.

        Args:
            user_id: Идентификатор пользователя

        """
        if user_id in self.items_by_user:
            del self.items_by_user[user_id]
        if user_id in self.current_page_by_user:
            del self.current_page_by_user[user_id]
        if user_id in self.mode_by_user:
            del self.mode_by_user[user_id]
        if user_id in self.user_settings:
            del self.user_settings[user_id]
        if user_id in self.page_cache:
            del self.page_cache[user_id]

    def get_pagination_keyboard(self, user_id: int, prefix: str = "") -> InlineKeyboardMarkup:
        """Создает клавиатуру пагинации для текущей страницы пользователя.
        
        Использует унифицированную функцию create_pagination_keyboard из модуля keyboards.
        
        Args:
            user_id: Идентификатор пользователя
            prefix: Префикс для callback_data
            
        Returns:
            InlineKeyboardMarkup: Клавиатура с пагинацией
        """
        if user_id not in self.items_by_user:
            # Если у пользователя нет данных, возвращаем пустую клавиатуру
            return create_pagination_keyboard(0, 1, prefix=prefix)
            
        # Получаем текущую страницу и общее количество страниц
        _, current_page, total_pages = self.get_page(user_id)
        
        # Создаем клавиатуру с помощью унифицированной функции
        return create_pagination_keyboard(
            current_page=current_page,
            total_pages=total_pages,
            prefix=prefix,
            with_nums=True,
            back_button=True,
            back_text="« Назад",
            back_callback="back_to_menu",
        )

    def format_current_page(
        self, 
        user_id: int, 
        formatter: Optional[Callable] = None,
        content_type: str = "opportunities",
        **kwargs
    ) -> str:
        """Форматирует текущую страницу результатов.
        
        Интегрируется с функциями форматирования из utils.formatters,
        но позволяет передать свою функцию-форматтер при необходимости.
        
        Args:
            user_id: Идентификатор пользователя
            formatter: Опциональная функция форматирования (если None, используется стандартная)
            content_type: Тип контента для выбора стандартного форматтера
            **kwargs: Дополнительные параметры для передачи в форматтер
            
        Returns:
            str: Отформатированный текст для текущей страницы
        """
        if user_id not in self.items_by_user:
            return "Нет доступных данных для отображения."
            
        # Получаем текущую страницу
        items, current_page, total_pages = self.get_page(user_id)
        
        if not items:
            return "На этой странице нет данных."
            
        # Если передан пользовательский форматтер, используем его
        if formatter is not None:
            return formatter(items, current_page, total_pages, **kwargs)
            
        # Используем стандартные форматтеры в зависимости от типа контента
        if content_type == "opportunities":
            return format_opportunities(items, current_page, self.get_items_per_page(user_id))
        elif content_type == "inventory":
            # Проверяем наличие и импортируем только при необходимости
            try:
                from src.telegram_bot.utils.formatters import format_inventory_items
                return format_inventory_items(items, current_page, self.get_items_per_page(user_id))
            except ImportError:
                logger.warning("Форматтер format_inventory_items не найден, используем стандартный.")
                return self._default_format(items, current_page, total_pages)
        elif content_type == "market":
            try:
                from src.telegram_bot.utils.formatters import format_market_items
                return format_market_items(items, current_page, self.get_items_per_page(user_id))
            except ImportError:
                logger.warning("Форматтер format_market_items не найден, используем стандартный.")
                return self._default_format(items, current_page, total_pages)
        else:
            # Если тип не распознан, возвращаем базовое форматирование
            return self._default_format(items, current_page, total_pages)
            
    def _default_format(self, items: List[Any], current_page: int, total_pages: int) -> str:
        """Стандартное форматирование для элементов страницы.
        
        Args:
            items: Список элементов на странице
            current_page: Номер текущей страницы
            total_pages: Общее количество страниц
            
        Returns:
            str: Базово отформатированный текст
        """
        header = f"📄 Страница {current_page + 1} из {total_pages}\n\n"
        
        formatted_items = []
        for i, item in enumerate(items):
            # Пытаемся форматировать элемент по имени или str repr
            if isinstance(item, dict) and "name" in item:
                formatted_items.append(f"{i + 1}. {item['name']}")
            elif hasattr(item, "__str__"):
                formatted_items.append(f"{i + 1}. {str(item)}")
            else:
                formatted_items.append(f"{i + 1}. Элемент #{i + 1}")
                
        return header + "\n".join(formatted_items)


# Создаем глобальный экземпляр менеджера пагинации
pagination_manager = PaginationManager()


def format_paginated_results(
    items: list[dict[str, Any]],
    game: str,
    mode: str,
    current_page: int,
    total_pages: int,
) -> str:
    """Форматирует результаты пагинации в читаемый текст.
    
    Для обратной совместимости, используйте методы класса PaginationManager.
    
    Args:
        items: Элементы текущей страницы
        game: Код игры
        mode: Режим отображения
        current_page: Номер текущей страницы (начиная с 0)
        total_pages: Общее количество страниц
        
    Returns:
        str: Отформатированный текст с результатами
    """
    # Для обратной совместимости используем существующие форматтеры
    if mode in ["arbitrage", "auto_arbitrage"]:
        return format_opportunities(items, current_page, 5) 
    
    # Базовое форматирование для других типов данных
    header = f"📄 Страница {current_page + 1} из {total_pages}\n\n"
    game_emoji = {"csgo": "🔫", "dota2": "🏆", "rust": "🏝️", "tf2": "🎩"}.get(game, "🎮")
    
    formatted_items = []
    for i, item in enumerate(items):
        title = item.get("title", f"Элемент #{i+1}")
        price = item.get("price", {}).get("USD", 0) / 100 if isinstance(item.get("price"), dict) else 0
        formatted_items.append(f"{i+1}. {game_emoji} {title} - ${price:.2f}")
    
    return header + "\n".join(formatted_items)
