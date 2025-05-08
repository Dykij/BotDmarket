"""
Обработчики ошибок Telegram бота.

Этот модуль содержит функции обработки различных ошибок,
возникающих в процессе работы бота.
"""

import logging
import traceback
from typing import Optional, Dict, Any

from telegram import Update, ParseMode
from telegram.ext import ContextTypes, CallbackContext

from src.utils.api_error_handling import APIError, handle_api_error
from src.telegram_bot.keyboards import get_back_to_arbitrage_keyboard

logger = logging.getLogger(__name__)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает ошибки, возникающие при работе бота.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом
    """
    error = context.error

    # Логируем ошибку
    logger.error(f"Exception while handling an update: {error}")
    logger.error(traceback.format_exc())

    # Отправляем сообщение пользователю в зависимости от типа ошибки
    if isinstance(error, APIError):
        error_message = (
            f"❌ <b>Ошибка API DMarket:</b>\n"
            f"Код: {error.status_code}\n"
            f"Сообщение: {error!s}"
        )
    else:
        error_message = (
            "⚠️ <b>Произошла ошибка при выполнении команды.</b>\n\n"
            "Детали были записаны в журнал для анализа разработчиками.\n"
            "Пожалуйста, попробуйте позднее или свяжитесь с администратором."
        )

    # Отправляем сообщение, если это возможно
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                error_message,
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_to_arbitrage_keyboard() if isinstance(error, APIError) else None
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")

# Экспортируем обработчик ошибок
__all__ = ['error_handler']
