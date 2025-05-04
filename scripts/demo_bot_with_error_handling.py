"""
Демонстрирует интеграцию системы логирования и обработки ошибок с Telegram-ботом.
"""

import os
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, CallbackContext
)

from src.utils.logging_utils import get_logger, log_exceptions
from src.utils.exception_handling import (
    handle_exceptions, APIError, ValidationError, BusinessLogicError, ErrorCode
)

# Получаем токен бота из переменной окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TOKEN_HERE")

# Создаем логгер для бота с контекстом
bot_logger = get_logger("demo_bot", {"component": "telegram_bot"})


class DemoBot:
    """
    Демонстрационный Telegram-бот с интегрированной системой логирования
    и обработки ошибок.
    """

    def __init__(self, token: str):
        """
        Инициализирует бота.

        Args:
            token: Токен Telegram-бота.
        """
        self.token = token
        # Логгер с контекстом бота
        self.logger = get_logger("demo_bot.instance", {
            "component": "bot_instance",
            "bot_start_time": datetime.now().isoformat()
        })

        # Создаем приложение
        self.application = Application.builder().token(token).build()

        # Регистрируем обработчики
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Регистрирует обработчики команд и коллбэков."""
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("demo", self.demo_command))

        # Обработчики коллбэков
        self.application.add_handler(
            CallbackQueryHandler(self.handle_demo_callback, pattern=r"^demo_")
        )

        # Обработчик ошибок
        self.application.add_error_handler(self.error_handler)

    async def start(self) -> None:
        """Запускает бота."""
        self.logger.info("Запуск демонстрационного бота")
        await self.application.initialize()
        await self.application.start()
        await self.application.run_polling()

    @log_exceptions
    async def stop(self) -> None:
        """Останавливает бота."""
        self.logger.info("Останавливаю бота")
        await self.application.stop()

    @handle_exceptions(default_error_message="Ошибка при обработке команды /start")
    async def start_command(self, update: Update, context: CallbackContext) -> None:
        """
        Обрабатывает команду /start.

        Args:
            update: Объект Update от Telegram.
            context: Контекст CallbackContext.
        """
        user = update.message.from_user
        user_id = user.id

        # Логируем с контекстом пользователя
        self.logger.info(
            f"Пользователь {user.username or user.first_name} запустил бота",
            extra={"context": {"user_id": user_id, "username": user.username}}
        )

        # Отправляем приветственное сообщение
        await update.message.reply_text(
            "👋 Добро пожаловать в демонстрационного бота!\n\n"
            "Этот бот показывает интеграцию системы логирования "
            "и обработки ошибок.\n\n"
            "Команды:\n"
            "/demo - Показать демо возможностей\n"
            "/help - Справка"
        )

    @handle_exceptions(default_error_message="Ошибка при обработке команды /help")
    async def help_command(self, update: Update, context: CallbackContext) -> None:
        """
        Обрабатывает команду /help.

        Args:
            update: Объект Update от Telegram.
            context: Контекст CallbackContext.
        """
        user_id = update.message.from_user.id

        # Логируем с контекстом
        self.logger.info(
            "Запрошена справка",
            extra={"context": {"user_id": user_id}}
        )

        # Отправляем справочное сообщение
        await update.message.reply_text(
            "📋 Справка по демонстрационному боту\n\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать эту справку\n"
            "/demo - Демонстрация обработки ошибок\n\n"
            "Этот бот интегрирует систему логирования и обработки ошибок."
        )

    @handle_exceptions(default_error_message="Ошибка при обработке команды /demo")
    async def demo_command(self, update: Update, context: CallbackContext) -> None:
        """
        Обрабатывает команду /demo.

        Args:
            update: Объект Update от Telegram.
            context: Контекст CallbackContext.
        """
        user_id = update.message.from_user.id

        # Логируем с контекстом
        self.logger.info(
            "Запрошена демонстрация",
            extra={"context": {"user_id": user_id}}
        )

        # Создаем клавиатуру для демонстрации
        keyboard = [
            [
                InlineKeyboardButton(
                    "Успешная операция",
                    callback_data="demo_success"
                ),
                InlineKeyboardButton(
                    "Ошибка API",
                    callback_data="demo_api_error"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Ошибка валидации",
                    callback_data="demo_validation_error"
                ),
                InlineKeyboardButton(
                    "Бизнес-ошибка",
                    callback_data="demo_business_error"
                ),
            ],
        ]

        # Отправляем сообщение с кнопками
        await update.message.reply_text(
            "🧪 Демонстрация обработки ошибок\n\n"
            "Выберите тип операции для демонстрации:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    @handle_exceptions(default_error_message="Ошибка при обработке колбэка")
    async def handle_demo_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Обрабатывает колбэки от кнопок демонстрации.

        Args:
            update: Объект Update от Telegram.
            context: Контекст CallbackContext.
        """
        query = update.callback_query
        user_id = query.from_user.id
        callback_data = query.data

        # Логируем с контекстом
        self.logger.info(
            f"Получен колбэк: {callback_data}",
            extra={"context": {"user_id": user_id, "callback_data": callback_data}}
        )

        # Отвечаем на колбэк
        await query.answer()

        # Обрабатываем различные типы колбэков
        try:
            if callback_data == "demo_success":
                await self._handle_success_demo(query, context)
            elif callback_data == "demo_api_error":
                await self._handle_api_error_demo(query, context)
            elif callback_data == "demo_validation_error":
                await self._handle_validation_error_demo(query, context)
            elif callback_data == "demo_business_error":
                await self._handle_business_error_demo(query, context)
            else:
                self.logger.warning(
                    f"Неизвестный колбэк: {callback_data}",
                    extra={"context": {"user_id": user_id}}
                )
                await query.edit_message_text(
                    "⚠️ Неизвестный тип демонстрации."
                )
        except Exception as e:
            # Это исключение будет обработано через handle_exceptions,
            # но мы также отправляем сообщение пользователю
            await query.edit_message_text(
                f"❌ В процессе демонстрации произошла ошибка: {str(e)}"
            )
            raise

    async def _handle_success_demo(self, query: Any, context: CallbackContext) -> None:
        """
        Демонстрирует успешную операцию.

        Args:
            query: Объект CallbackQuery.
            context: Контекст CallbackContext.
        """
        user_id = query.from_user.id

        self.logger.info(
            "Демонстрация успешной операции",
            extra={"context": {"user_id": user_id}}
        )

        # Имитируем некоторую асинхронную работу
        await asyncio.sleep(1)

        # Отправляем результат
        await query.edit_message_text(
            "✅ Операция успешно выполнена!\n\n"
            "Это демонстрация успешного сценария с логированием."
        )

    async def _handle_api_error_demo(self, query: Any, context: CallbackContext) -> None:
        """
        Демонстрирует ошибку API.

        Args:
            query: Объект CallbackQuery.
            context: Контекст CallbackContext.
        """
        user_id = query.from_user.id

        self.logger.info(
            "Демонстрация ошибки API",
            extra={"context": {"user_id": user_id}}
        )

        # Имитируем вызов API
        await asyncio.sleep(1)

        # Выбрасываем тестовую ошибку API
        raise APIError(
            message="API вернул ошибку",
            status_code=429,
            details={"retry_after": 30}
        )

    async def _handle_validation_error_demo(self, query: Any, context: CallbackContext) -> None:
        """
        Демонстрирует ошибку валидации.

        Args:
            query: Объект CallbackQuery.
            context: Контекст CallbackContext.
        """
        user_id = query.from_user.id

        self.logger.info(
            "Демонстрация ошибки валидации",
            extra={"context": {"user_id": user_id}}
        )

        # Имитируем проверку данных
        await asyncio.sleep(1)

        # Выбрасываем тестовую ошибку валидации
        raise ValidationError(
            message="Некорректное значение параметра",
            field="price",
            details={"value": -10, "valid_range": [0, 1000]}
        )

    async def _handle_business_error_demo(self, query: Any, context: CallbackContext) -> None:
        """
        Демонстрирует ошибку бизнес-логики.

        Args:
            query: Объект CallbackQuery.
            context: Контекст CallbackContext.
        """
        user_id = query.from_user.id

        self.logger.info(
            "Демонстрация ошибки бизнес-логики",
            extra={"context": {"user_id": user_id}}
        )

        # Имитируем бизнес-операцию
        await asyncio.sleep(1)

        # Выбрасываем тестовую ошибку бизнес-логики
        raise BusinessLogicError(
            message="Недостаточно средств для выполнения операции",
            operation="purchase",
            details={"required": 100, "available": 50}
        )

    async def error_handler(self, update: Update, context: CallbackContext) -> None:
        """
        Обрабатывает ошибки, возникающие при работе бота.

        Args:
            update: Объект Update от Telegram.
            context: Контекст CallbackContext.
        """
        # Получаем информацию об ошибке
        error = context.error

        # Логируем ошибку с контекстом
        error_context = {"update_id": update.update_id if update else None}

        if isinstance(error, BaseException):
            # Добавляем тип ошибки в контекст
            error_context["error_type"] = error.__class__.__name__

        # Логируем в зависимости от типа ошибки
        if isinstance(error, APIError):
            self.logger.error(
                f"Ошибка API: {error.message}",
                extra={"context": {**error_context, **error.details}}
            )
            # Отправляем пользователю сообщение о проблеме с API
            message = f"⚠️ Проблема с API: {error.message}"
            if error.status_code == 429:
                message += "\nПожалуйста, повторите попытку позже."

        elif isinstance(error, ValidationError):
            self.logger.warning(
                f"Ошибка валидации: {error.message}",
                extra={"context": {**error_context, **error.details}}
            )
            # Отправляем пользователю сообщение о проблеме с данными
            field = error.details.get("field", "")
            message = f"⚠️ Ошибка валидации {field}: {error.message}"

        elif isinstance(error, BusinessLogicError):
            self.logger.error(
                f"Ошибка бизнес-логики: {error.message}",
                extra={"context": {**error_context, **error.details}}
            )
            # Отправляем пользователю сообщение о бизнес-ошибке
            operation = error.details.get("operation", "")
            message = f"⚠️ Ошибка при выполнении операции {operation}: {error.message}"

        else:
            # Необработанное исключение
            self.logger.error(
                f"Необработанное исключение: {str(error)}",
                extra={"context": error_context}
            )
            message = "❌ Произошла непредвиденная ошибка."

        # Отправляем сообщение пользователю, если возможно
        if update and update.effective_message:
            await update.effective_message.reply_text(message)


async def main() -> None:
    """Основная функция для запуска бота."""
    # Создаем и запускаем бота
    bot_logger.info("Запуск демонстрационного бота")

    # Проверяем наличие токена
    if not TOKEN or TOKEN == "YOUR_TOKEN_HERE":
        bot_logger.error(
            "Токен бота не настроен! Укажите TELEGRAM_BOT_TOKEN в .env файле"
        )
        return

    bot = DemoBot(TOKEN)

    try:
        await bot.start()
    except KeyboardInterrupt:
        bot_logger.info("Бот остановлен пользователем")
        await bot.stop()
    except Exception as e:
        bot_logger.error(f"Ошибка при запуске бота: {e}")


if __name__ == "__main__":
    # Запускаем бота
    asyncio.run(main())
