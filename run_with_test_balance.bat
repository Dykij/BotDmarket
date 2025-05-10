@echo off
color 0A
setlocal EnableDelayedExpansion

echo ==========================================
echo   DMarket Bot - ДЕМО РЕЖИМ (тестовый баланс)
echo ==========================================
echo.
echo Этот режим позволяет запустить бота без действующих API ключей DMarket.
echo Будет использоваться виртуальный баланс для демонстрации функций.
echo.

:: Устанавливаем переменную окружения для тестового режима
set TEST_MODE=1
set TEST_BALANCE=100.00

:: Проверяем наличие .env файла
if not exist .env (
    echo .env файл не найден. Создаю новый...
    python create_env_file.py
)

echo.
echo Для продолжения нажмите любую клавишу или Ctrl+C для отмены...
pause > nul

:: Активируем виртуальное окружение, если оно есть
if exist venv\Scripts\activate.bat (
    echo Активация виртуального окружения venv...
    call venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
    echo Активация виртуального окружения .venv...
    call .venv\Scripts\activate.bat
) else (
    echo Виртуальное окружение не найдено. Используется системный Python.
)

:: Запускаем скрипт тестового баланса
echo Применение патча тестового баланса...
python test_balance.py --test-mode

:: Запускаем бота
echo Запуск бота в демо-режиме с тестовым балансом $%TEST_BALANCE%...
echo Для остановки нажмите Ctrl+C
python run.py --test-mode

:: Если бот завершится, ждем ввода пользователя перед выходом
echo.
echo Бот остановлен. Нажмите любую клавишу для выхода...
pause > nul

endlocal 