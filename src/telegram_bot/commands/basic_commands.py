"""Базовые команды для Telegram бота.

Этот модуль содержит основные команды для взаимодействия
пользователя с Telegram ботом.
"""

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение при команде /start."""
    logger.info(f"Пользователь {update.effective_user.id} использовал команду /start")

    if update.message:
        await update.message.reply_text(
            "Привет! Я бот для работы с DMarket. Используй /help, чтобы увидеть доступные команды.",
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет список доступных команд при команде /help."""
    logger.info(f"Пользователь {update.effective_user.id} использовал команду /help")

    if update.message:
        await update.message.reply_text(
            "Доступные команды:\n"
            "/start — приветствие\n"
            "/help — показать это сообщение\n"
            "/dmarket — проверить статус API DMarket\n"
            "/balance — проверить баланс на DMarket\n"
            "/arbitrage — поиск арбитражных возможностей",
        )


def register_basic_commands(app: Application) -> None:
    """Регистрирует базовые команды в приложении Telegram."""
    logger.info("Регистрация базовых команд")

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
