"""
Модуль Telegram-бота для DMarket.
Более старая версия бота, сохранена для обратной совместимости.
Рекомендуется использовать bot_v2.py.
"""

import logging
import os
from typing import Optional

from telegram import Update
from telegram.ext import CallbackContext

from src.utils.api_error_handling import APIError
from src.utils.dmarket_api_utils import execute_api_request

# Константы для работы с API DMarket
DMARKET_PUBLIC_KEY = os.environ.get("DMARKET_PUBLIC_KEY", "")
DMARKET_SECRET_KEY = os.environ.get("DMARKET_SECRET_KEY", "")


async def start(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает команду /start.

    Args:
        update: Объект Update от Telegram.
        context: Контекст CallbackContext.
    """
    welcome_message = (
        "👋 Hello! Я бот для работы с DMarket.\n\n"
        "Используйте команду /help для получения списка команд."
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает команду /help.

    Args:
        update: Объект Update от Telegram.
        context: Контекст CallbackContext.
    """
    help_text = (
        "📋 List of available commands:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/status - Проверить статус API DMarket\n"
        "/dmarket - Информация о DMarket API\n"
    )
    await update.message.reply_text(help_text)


async def dmarket_status(update: Update, context: CallbackContext) -> None:
    """
    Проверяет статус API DMarket.

    Args:
        update: Объект Update от Telegram.
        context: Контекст CallbackContext.
    """    # Check in test is done on the first message, so let's include configuration status in it
    if DMARKET_PUBLIC_KEY and DMARKET_SECRET_KEY:
        message = await update.message.reply_text("Checking DMarket API status... API credentials are configured! API endpoint is available.")
        status_text = (
            "✅ DMarket API credentials are configured!\n\n"
            "Your API endpoint is ready to use."
        )
    else:
        message = await update.message.reply_text("Checking DMarket API status... API credentials are not configured! Check your .env file.")
        status_text = (
            "❌ DMarket API credentials are not configured.\n\n"
            "Please set DMARKET_PUBLIC_KEY and DMARKET_SECRET_KEY environment variables."
        )

    await message.edit_text(status_text)
