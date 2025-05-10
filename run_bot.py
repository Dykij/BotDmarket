"""
Скрипт запуска Telegram-бота DMarket с расширенной обработкой ошибок и поддержанием работы.
Объединяет функциональность из main.py, run.py и run_bot.py.
"""

import os
import sys
import logging
import asyncio
import time
import argparse
from pathlib import Path

# Настраиваем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/bot_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Добавляем директорию src в путь поиска модулей
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Загрузка переменных окружения из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv не установлен, продолжаем без него")

# Проверка наличия необходимых переменных окружения
def check_environment():
    """Проверяет наличие необходимых переменных окружения"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не настроен в .env файле")
        return False
    
    dmarket_public_key = os.environ.get("DMARKET_PUBLIC_KEY")
    dmarket_secret_key = os.environ.get("DMARKET_SECRET_KEY")
    if not dmarket_public_key or not dmarket_secret_key:
        logger.warning("DMarket API ключи не настроены в .env файле")
    
    return True

async def run_bot():
    """
    Запускает бота с обработкой возможных ошибок
    """
    try:
        # Импортируем основную функцию бота
        from telegram_bot.bot_v2 import main
        
        # Запускаем бота
        logger.info("Запуск Telegram-бота...")
        await main()
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback
        logger.error(f"Трассировка: {traceback.format_exc()}")
        
        # Делаем паузу перед повторной попыткой
        logger.info("Пауза 10 секунд перед повторной попыткой...")
        await asyncio.sleep(10)
        
        # Перезапускаем бота
        logger.info("Перезапуск бота...")
        await run_bot()

def parse_arguments():
    """Обрабатывает аргументы командной строки"""
    parser = argparse.ArgumentParser(description="DMarket Telegram Bot")
    parser.add_argument("--no-lock", action="store_true", help="Не использовать файл блокировки")
    parser.add_argument("--debug", action="store_true", help="Включить режим отладки")
    return parser.parse_args()

if __name__ == "__main__":
    # Создаем директорию для логов, если её нет
    os.makedirs("logs", exist_ok=True)
    
    # Обрабатываем аргументы командной строки
    args = parse_arguments()
    
    # Устанавливаем уровень логов в зависимости от режима
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Включен режим отладки")
    
    # Проверяем переменные окружения
    if not check_environment():
        logger.error("Ошибка в настройке окружения. Выход из программы.")
        sys.exit(1)
    
    # Запускаем бота через asyncio
    try:
        # Проверяем, требуется ли использовать файл блокировки
        if not args.no_lock:
            lock_file = Path("bot.lock")
            if lock_file.exists():
                try:
                    # Читаем PID из файла блокировки
                    with open(lock_file, "r") as f:
                        pid = int(f.read().strip())
                    
                    # Проверяем, существует ли процесс с таким PID
                    import psutil
                    if psutil.pid_exists(pid):
                        logger.warning(f"Бот уже запущен с PID {pid}. Завершаем текущий экземпляр.")
                        sys.exit(1)
                    else:
                        logger.warning(f"Обнаружен недействительный файл блокировки. Перезаписываем.")
                except Exception as e:
                    logger.error(f"Ошибка при чтении файла блокировки: {e}")
            
            # Создаем файл блокировки с текущим PID
            with open(lock_file, "w") as f:
                f.write(str(os.getpid()))
            
            # Регистрируем обработчик для удаления файла блокировки при завершении
            import atexit
            def cleanup():
                if lock_file.exists():
                    lock_file.unlink()
            atexit.register(cleanup)
        else:
            logger.info("Работа без файла блокировки")
        
        # Запускаем бота
        asyncio.run(run_bot())
        
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        import traceback
        logger.error(f"Трассировка: {traceback.format_exc()}")
    finally:
        # Удаляем файл блокировки при выходе, если он используется
        if not args.no_lock:
            lock_file = Path("bot.lock")
            if lock_file.exists():
                lock_file.unlink() 