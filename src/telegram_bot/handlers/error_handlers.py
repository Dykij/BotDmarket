from telegram import Update
from telegram.ext import CallbackContext
from typing import Optional
from src.utils.api_error_handling import APIError

async def error_handler(update: Optional[Update], context: CallbackContext) -> None:
    error = context.error
    error_message = "😔 Произошла ошибка при обработке вашего запроса. Попробуйте позже."
    if isinstance(error, APIError):
        if error.status_code == 429:
            error_message = "⏱️ Превышен лимит запросов к DMarket API. Пожалуйста, подождите несколько минут."
        elif error.status_code == 401:
            error_message = "🔑 Ошибка авторизации в DMarket API. Проверьте API-ключи в настройках."
        elif error.status_code == 404:
            error_message = "🔍 Запрашиваемый ресурс не найден в DMarket."
        elif error.status_code >= 500:
            error_message = "🛑 Серверная ошибка DMarket API. Пожалуйста, попробуйте позже."
        else:
            error_message = f"❌ Ошибка DMarket API: {error.message}"
    if update and update.effective_message:
        await update.effective_message.reply_text(error_message)
