"""Скрипт для остановки Telegram-бота DMarket.
"""

import logging
from pathlib import Path

# Настраиваем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename="bot_service.log",
)
logger = logging.getLogger(__name__)


def stop_bot_service():
    """Останавливает работающего бота"""
    try:
        # Получаем текущую директорию проекта
        project_dir = Path(__file__).parent.absolute()

        # Проверяем наличие файла блокировки
        lock_file = project_dir / "bot.lock"
        if not lock_file.exists():
            logger.warning("Файл блокировки не найден. Возможно, бот не запущен.")
            print("Бот не запущен (файл блокировки не найден).")
            return False

        # Читаем PID из файла блокировки
        try:
            with open(lock_file) as f:
                pid = int(f.read().strip())
        except Exception as e:
            logger.error(f"Ошибка при чтении файла блокировки: {e}")
            print(f"Ошибка при чтении файла блокировки: {e}")
            return False

        logger.info(f"Найден запущенный бот с PID: {pid}")
        print(f"Останавливаем бота с PID: {pid}...")

        # Отправляем сигнал SIGTERM процессу
        try:
            import psutil

            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                process.terminate()  # Отправляем SIGTERM

                logger.info(f"Отправлен сигнал завершения процессу {pid}")

                # Ждем завершения процесса
                gone, still_alive = psutil.wait_procs([process], timeout=5)
                if still_alive:
                    # Если процесс не завершился, убиваем его
                    logger.warning(
                        f"Процесс {pid} не завершился корректно. Принудительное завершение."
                    )
                    process.kill()  # Отправляем SIGKILL

                # Удаляем файл блокировки
                if lock_file.exists():
                    lock_file.unlink()
                    logger.info("Файл блокировки удален")

                logger.info(f"Бот с PID {pid} успешно остановлен")
                print(f"Бот с PID {pid} успешно остановлен.")
                return True
            logger.warning(f"Процесс с PID {pid} не найден. Удаляем файл блокировки.")
            if lock_file.exists():
                lock_file.unlink()
            print(f"Процесс с PID {pid} не найден. Файл блокировки удален.")
            return False
        except Exception as e:
            logger.error(f"Ошибка при остановке бота: {e}")
            print(f"Ошибка при остановке бота: {e}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при остановке бота: {e}")
        import traceback

        logger.error(f"Трассировка: {traceback.format_exc()}")
        print(f"Ошибка при остановке бота: {e}")
        return False


if __name__ == "__main__":
    stop_bot_service()
