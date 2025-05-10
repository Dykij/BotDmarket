@echo off
color 0A
setlocal EnableDelayedExpansion

echo ==========================================
echo   DMarket Bot с улучшенной поддержкой API 
echo ==========================================
echo.

REM Проверяем наличие .env файла
if not exist .env (
    echo .env файл не найден. Создаю новый...
    python create_env_file.py
)

REM Проверяем API ключи DMarket
echo Проверка API ключей DMarket...
python validate_api_keys.py
if %ERRORLEVEL% NEQ 0 (
    echo Ошибка при проверке API ключей.
    echo Пожалуйста, исправьте проблемы с API ключами и запустите снова.
    pause
    exit /b 1
)

echo.
echo Для продолжения нажмите любую клавишу или Ctrl+C для отмены...
pause > nul

REM Активируем виртуальное окружение, если оно есть
if exist venv\Scripts\activate.bat (
    echo Активация виртуального окружения venv...
    call venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
    echo Активация виртуального окружения .venv...
    call .venv\Scripts\activate.bat
) else (
    echo Виртуальное окружение не найдено. Используется системный Python.
)

REM Применяем патчи для DMarket API
echo Применение патчей DMarket API...
python -c "from src.dmarket.dmarket_api_patches import apply_balance_patch; apply_balance_patch()"

REM Проверяем баланс перед запуском
echo Проверка баланса DMarket...
python test_balance.py
echo.
echo Для продолжения нажмите любую клавишу...
pause > nul

REM Запускаем бота
echo Запуск бота с улучшенными возможностями...
echo Для остановки нажмите Ctrl+C
python run.py

REM Если бот завершится, ждем ввода пользователя перед выходом
echo.
echo Бот остановлен. Нажмите любую клавишу для выхода...
pause > nul

endlocal 