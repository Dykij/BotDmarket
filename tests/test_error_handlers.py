"""
Тесты для обработчиков ошибок из модуля error_handlers.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update
from telegram.ext import CallbackContext

from src.telegram_bot.handlers.error_handlers import error_handler
from src.utils.api_error_handling import APIError


@pytest.mark.asyncio
async def test_error_handler_api_error_rate_limit():
    """Тест обработки ошибки превышения лимита запросов API."""
    # Создаем моки для объектов Update и CallbackContext
    update = MagicMock(spec=Update)
    update.effective_message = AsyncMock()

    context = MagicMock(spec=CallbackContext)
    context.error = APIError("Rate limit exceeded", 429)

    # Вызываем обработчик
    await error_handler(update, context)

    # Проверяем, что было отправлено правильное сообщение
    update.effective_message.reply_text.assert_called_once()
    args, kwargs = update.effective_message.reply_text.call_args
    assert "лимит запросов" in args[0]
    assert "подождите" in args[0]


@pytest.mark.asyncio
async def test_error_handler_api_error_unauthorized():
    """Тест обработки ошибки авторизации API."""
    # Создаем моки для объектов Update и CallbackContext
    update = MagicMock(spec=Update)
    update.effective_message = AsyncMock()

    context = MagicMock(spec=CallbackContext)
    context.error = APIError("Unauthorized", 401)

    # Вызываем обработчик
    await error_handler(update, context)

    # Проверяем, что было отправлено правильное сообщение
    update.effective_message.reply_text.assert_called_once()
    args, kwargs = update.effective_message.reply_text.call_args
    assert "авторизации" in args[0]
    assert "API-ключи" in args[0]


@pytest.mark.asyncio
async def test_error_handler_api_error_not_found():
    """Тест обработки ошибки 404 из API."""
    # Создаем моки для объектов Update и CallbackContext
    update = MagicMock(spec=Update)
    update.effective_message = AsyncMock()

    context = MagicMock(spec=CallbackContext)
    context.error = APIError("Not Found", 404)

    # Вызываем обработчик
    await error_handler(update, context)

    # Проверяем, что было отправлено правильное сообщение
    update.effective_message.reply_text.assert_called_once()
    args, kwargs = update.effective_message.reply_text.call_args
    assert "не найден" in args[0]


@pytest.mark.asyncio
async def test_error_handler_api_error_server_error():
    """Тест обработки серверной ошибки из API."""
    # Создаем моки для объектов Update и CallbackContext
    update = MagicMock(spec=Update)
    update.effective_message = AsyncMock()

    context = MagicMock(spec=CallbackContext)
    context.error = APIError("Internal Server Error", 500)

    # Вызываем обработчик
    await error_handler(update, context)

    # Проверяем, что было отправлено правильное сообщение
    update.effective_message.reply_text.assert_called_once()
    args, kwargs = update.effective_message.reply_text.call_args
    assert "Серверная ошибка" in args[0]
    assert "попробуйте позже" in args[0]


@pytest.mark.asyncio
async def test_error_handler_api_error_other():
    """Тест обработки других API ошибок."""
    # Создаем моки для объектов Update и CallbackContext
    update = MagicMock(spec=Update)
    update.effective_message = AsyncMock()

    context = MagicMock(spec=CallbackContext)
    context.error = APIError("Bad Request", 400)

    # Вызываем обработчик
    await error_handler(update, context)

    # Проверяем, что было отправлено правильное сообщение
    update.effective_message.reply_text.assert_called_once()
    args, kwargs = update.effective_message.reply_text.call_args
    assert "Ошибка DMarket API" in args[0]
    assert "Bad Request" in args[0]


@pytest.mark.asyncio
async def test_error_handler_other_error():
    """Тест обработки других типов ошибок."""
    # Создаем моки для объектов Update и CallbackContext
    update = MagicMock(spec=Update)
    update.effective_message = AsyncMock()

    context = MagicMock(spec=CallbackContext)
    context.error = ValueError("Some other error")

    # Вызываем обработчик
    await error_handler(update, context)

    # Проверяем, что было отправлено общее сообщение об ошибке
    update.effective_message.reply_text.assert_called_once()
    args, kwargs = update.effective_message.reply_text.call_args
    assert "Произошла ошибка" in args[0]
    assert "Попробуйте позже" in args[0]


@pytest.mark.asyncio
async def test_error_handler_no_update():
    """Тест обработки ошибок без объекта Update."""
    # Создаем мок только для CallbackContext
    context = MagicMock(spec=CallbackContext)
    context.error = ValueError("Error without update")

    # Вызываем обработчик
    await error_handler(None, context)

    # Проверяем, что функция не вызвала исключение и корректно завершилась


@pytest.mark.asyncio
async def test_error_handler_no_message():
    """Тест обработки ошибок без сообщения в Update."""
    # Создаем моки для объектов Update и CallbackContext
    update = MagicMock(spec=Update)
    update.effective_message = None

    context = MagicMock(spec=CallbackContext)
    context.error = ValueError("Error with no message")

    # Вызываем обработчик
    await error_handler(update, context)

    # Проверяем, что функция не вызвала исключение и корректно завершилась
