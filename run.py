
"""
Модуль запуска Telegram-бота DMarket.

Этот скрипт инициализирует окружение, добавляя директорию src в sys.path, и запускает основную функцию Telegram-бота.

Запуск:
    python run.py

Назначение:
    - Подготовка окружения для корректного импорта модулей из src
    - Запуск основной логики бота через telegram_bot.bot_v2.main
"""

import os
import sys

# Абсолютный путь к директории src, необходимый для корректного импорта модулей.
src_path: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)  # Добавляем src в sys.path, если ещё не добавлен

# Импорт основной функции запуска Telegram-бота
from telegram_bot.bot_v2 import main

def _entry_point():
    """
    Точка входа для запуска Telegram-бота DMarket.
    Вызывает функцию main из telegram_bot.bot_v2.
    """
    main()

if __name__ == "__main__":
    _entry_point()
