"""Запуск Telegram-бота DMarket как фонового сервиса в Windows.
"""

import logging
import subprocess
import sys
from pathlib import Path

# Настраиваем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename="bot_service.log",
)
logger = logging.getLogger(__name__)


def start_bot_service():
    """Запускает бота в фоновом режиме"""
    try:
        # Получаем текущую директорию проекта
        project_dir = Path(__file__).parent.absolute()
        logger.info(f"Директория проекта: {project_dir}")

        # Проверяем наличие файла bot.lock
        lock_file = project_dir / "bot.lock"
        if lock_file.exists():
            logger.warning("Обнаружен файл блокировки. Возможно, бот уже запущен.")
            try:
                with open(lock_file) as f:
                    pid = f.read().strip()
                logger.warning(f"PID запущенного бота: {pid}")
            except Exception as e:
                logger.error(f"Ошибка при чтении файла блокировки: {e}")

        # Путь к Python интерпретатору в текущем окружении
        python_path = sys.executable
        logger.info(f"Используемый Python: {python_path}")

        # Путь к скрипту бота
        bot_script = project_dir / "src" / "telegram_bot" / "bot_v2.py"

        # Запускаем бота в отдельном процессе
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE - скрыть окно

        # Создаем процесс бота с перенаправлением вывода в лог
        process = subprocess.Popen(
            [python_path, str(bot_script)],
            cwd=str(project_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        )

        logger.info(f"Бот запущен с PID: {process.pid}")

        # Записываем PID в отдельный файл для отслеживания
        with open(project_dir / "bot_service_pid.txt", "w") as f:
            f.write(str(process.pid))

        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback

        logger.error(f"Трассировка: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = start_bot_service()
    if success:
        print("Бот успешно запущен в фоновом режиме. См. bot_service.log для деталей.")
    else:
        print("Ошибка при запуске бота. См. bot_service.log для деталей.")
