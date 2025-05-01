"""
Тесты для проверки функциональности обработки ошибок API в боте.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update
from telegram.ext import CallbackContext

from src.utils.api_error_handling import APIError
from src.telegram_bot.bot_v2 import dmarket_status, error_handler


@pytest.mark.asyncio
async def test_dmarket_status_success():
    """Проверка успешного ответа от API при запросе статуса."""
    # Создаем моки для объектов Telegram
    update = MagicMock(spec=Update)
    context = MagicMock(spec=CallbackContext)
    message = AsyncMock()
    update.message = message
    
    # Мокаем функцию execute_api_request для возврата успешного результата
    success_result = {"success": True, "status": 200}
    with patch("src.telegram_bot.bot_v2.execute_api_request", 
              return_value=success_result) as mock_execute:
        await dmarket_status(update, context)
    
    # Проверка вызовов
    assert message.reply_text.called
    status_message = message.reply_text.return_value
    assert status_message.edit_text.called
    
    # Проверяем, что в сообщении есть информация об успешном статусе
    call_args = status_message.edit_text.call_args[0][0]
    assert "✅ API DMarket работает нормально" in call_args


@pytest.mark.asyncio
async def test_dmarket_status_error_api():
    """Проверка обработки ошибки API при запросе статуса."""
    # Создаем моки для объектов Telegram
    update = MagicMock(spec=Update)
    context = MagicMock(spec=CallbackContext)
    message = AsyncMock()
    update.message = message
    
    # Мокаем функцию execute_api_request для имитации ошибки API
    with patch("src.telegram_bot.bot_v2.execute_api_request", 
              side_effect=APIError("Тестовая ошибка API", 429)) as mock_execute:
        await dmarket_status(update, context)
    
    # Проверка вызовов
    assert message.reply_text.called
    status_message = message.reply_text.return_value
    assert status_message.edit_text.called
    
    # Проверяем, что в сообщении есть информация об ошибке
    call_args = status_message.edit_text.call_args[0][0]
    assert "❌ Ошибка при проверке API DMarket" in call_args


@pytest.mark.asyncio
async def test_error_handler_api_error():
    """Проверка обработчика ошибок для APIError."""
    # Создаем моки для объектов
    update = MagicMock(spec=Update)
    context = MagicMock(spec=CallbackContext)
    message = AsyncMock()
    update.effective_message = message
    
    # Создаем ошибку API с кодом 429 (превышение лимита запросов)
    api_error = APIError("Превышен лимит запросов", 429)
    context.error = api_error
    
    # Вызываем обработчик ошибок
    await error_handler(update, context)
    
    # Проверка вызовов
    assert message.reply_text.called
    
    # Проверяем, что в сообщении есть информация о правильном типе ошибки
    call_args = message.reply_text.call_args[0][0]
    assert "Превышен лимит запросов" in call_args
    assert "подождите" in call_args


@pytest.mark.asyncio
async def test_error_handler_other_error():
    """Проверка обработчика ошибок для обычного исключения."""
    # Создаем моки для объектов
    update = MagicMock(spec=Update)
    context = MagicMock(spec=CallbackContext)
    message = AsyncMock()
    update.effective_message = message
    
    # Создаем обычную ошибку
    general_error = ValueError("Обычная ошибка")
    context.error = general_error
    
    # Вызываем обработчик ошибок
    await error_handler(update, context)
    
    # Проверка вызовов
    assert message.reply_text.called
    
    # Проверяем, что в сообщении есть общая информация об ошибке
    call_args = message.reply_text.call_args[0][0]
    assert "Произошла ошибка" in call_args
