"""Модуль для управления пагинацией результатов в Telegram-боте."""

import logging
from typing import List, Dict, Any, Tuple, Callable

logger = logging.getLogger(__name__)


class PaginationManager:
    """Менеджер пагинации для хранения и отображения страниц результатов."""

    def __init__(self, default_items_per_page: int = 5):
        """
        Инициализация менеджера пагинации.

        Args:
            default_items_per_page: Количество элементов на странице по умолчанию
        """
        self.items_by_user = {}  # Dict[int, List[Any]]
        self.current_page_by_user = {}  # Dict[int, int]
        self.mode_by_user = {}  # Dict[int, str]
        self.default_items_per_page = default_items_per_page
        self.user_settings = {}  # Dict[int, Dict[str, Any]]
        self.page_cache = {}  # Dict[int, Dict[int, Tuple[List[Any], int, int]]]

    def add_items_for_user(self, user_id: int, items: List[Any], mode: str = "default") -> None:
        """
        Добавляет элементы для пагинации конкретному пользователю.

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

    def get_items_per_page(self, user_id: int) -> int:
        """
        Возвращает количество элементов на странице для пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Количество элементов на странице
        """
        if (user_id in self.user_settings and
                "items_per_page" in self.user_settings[user_id]):
            return self.user_settings[user_id]["items_per_page"]
        return self.default_items_per_page

    def set_items_per_page(self, user_id: int, value: int) -> None:
        """
        Устанавливает количество элементов на странице для пользователя.

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

    def get_page(self, user_id: int) -> Tuple[List[Any], int, int]:
        """
        Возвращает текущую страницу элементов для пользователя.

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

    def next_page(self, user_id: int) -> Tuple[List[Any], int, int]:
        """
        Переходит к следующей странице для пользователя.

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

    def prev_page(self, user_id: int) -> Tuple[List[Any], int, int]:
        """
        Переходит к предыдущей странице для пользователя.

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
        """
        Фильтрует элементы для пользователя по условию.

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

    def sort_items(self, user_id: int, key_func: Callable[[Any], Any],
                  reverse: bool = False) -> None:
        """
        Сортирует элементы для пользователя.

        Args:
            user_id: Идентификатор пользователя
            key_func: Функция для извлечения ключа для сортировки
            reverse: Сортировка в обратном порядке если True
        """
        if user_id in self.items_by_user:
            self.items_by_user[user_id] = sorted(
                self.items_by_user[user_id],
                key=key_func,
                reverse=reverse
            )
            self.current_page_by_user[user_id] = 0  # Сбрасываем страницу

            # Сбрасываем кэш
            if user_id in self.page_cache:
                del self.page_cache[user_id]

    def get_mode(self, user_id: int) -> str:
        """
        Возвращает текущий режим пагинации для пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Режим пагинации
        """
        return self.mode_by_user.get(user_id, "default")

    def clear_user_data(self, user_id: int) -> None:
        """
        Очищает все данные пользователя.

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


# Создаем глобальный экземпляр менеджера пагинации
pagination_manager = PaginationManager()


def format_paginated_results(
    items: List[Dict[str, Any]],
    game: str,
    mode: str,
    current_page: int,
    total_pages: int
) -> str:
    """
    Форматирует элементы страницы результатов для отображения в Telegram.

    Args:
        items: Список элементов текущей страницы
        game: Код игры (csgo, dota2, rust, tf2)
        mode: Режим пагинации
        current_page: Номер текущей страницы
        total_pages: Общее количество страниц

    Returns:
        Отформатированный текст для отображения в сообщении
    """
    from src.dmarket.arbitrage import GAMES

    game_display = GAMES.get(game, game)
    mode_display = {
        "boost": "Разгон баланса",
        "mid": "Средний трейдер",
        "pro": "Профессионал",
        "auto": "Автоматический арбитраж",
        "auto_low": "Авто (мин. прибыль)",
        "auto_medium": "Авто (сред. прибыль)",
        "auto_high": "Авто (выс. прибыль)",
        "default": "Режим по умолчанию"
    }.get(mode, mode)

    if not items:
        return f"🔍 Нет результатов для {game_display} ({mode_display})"

    header = f"<b>🔍 Результаты для {game_display} ({mode_display}):</b>\n\n"
    items_text = []

    for i, item in enumerate(items, start=1):
        name = item.get("title", "Неизвестный предмет")
        price = float(item.get("price", {}).get("amount", 0)) / 100
        profit = float(item.get("profit", 0)) / 100
        profit_percent = item.get("profit_percent", 0)

        item_text = (
            f"{i}. <b>{name}</b>\n"
            f"   💰 Цена: <code>${price:.2f}</code>\n"
            f"   💵 Прибыль: <code>${profit:.2f} ({profit_percent:.1f}%)</code>\n"
        )
        items_text.append(item_text)

    page_info = f"\n📄 Страница {current_page + 1}/{total_pages}"

    return header + "\n".join(items_text) + page_info
