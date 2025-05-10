"""Обработчики команд Telegram бота.

Этот модуль содержит функции обработки команд от пользователей.
Все обработчики команд, начинающихся с / собраны здесь.
"""

import logging

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from src.telegram_bot.auto_arbitrage import check_balance_command
from src.telegram_bot.keyboards import (
    get_game_selection_keyboard,
    get_marketplace_comparison_keyboard,
    get_modern_arbitrage_keyboard,
    get_permanent_reply_keyboard,
    get_webapp_button,
)

logger = logging.getLogger(__name__)


async def start_command(update, context):
    """Обрабатывает команду /start.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом

    """
    # Отправляем приветственное сообщение с inline кнопками
    await update.message.reply_text(
        "👋 Привет! Я бот для работы с DMarket API. Выберите действие:",
        reply_markup=get_modern_arbitrage_keyboard(),
        parse_mode=ParseMode.HTML,
    )

    # Добавляем постоянную клавиатуру для быстрого доступа с улучшенными параметрами
    await update.message.reply_text(
        "⚡ <b>Быстрый доступ</b>\n\nИспользуйте клавиатуру ниже для быстрого доступа к основным функциям:",
        reply_markup=get_permanent_reply_keyboard(),
        parse_mode=ParseMode.HTML,
    )

    # Сохраняем в контексте пользователя информацию о том, что клавиатура активирована
    if hasattr(context, "user_data"):
        context.user_data["keyboard_enabled"] = True


async def help_command(update, context):
    """Обрабатывает команду /help.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом

    """
    await update.message.reply_text(
        "❓ <b>Доступные команды:</b>\n"
        "/start - Начать работу с ботом\n"
        "/arbitrage - Меню арбитража\n"
        "/balance - Проверить баланс\n"
        "/webapp - Открыть DMarket в WebApp",
        parse_mode=ParseMode.HTML,
        reply_markup=get_modern_arbitrage_keyboard(),
    )


async def webapp_command(update, context):
    """Обрабатывает команду /webapp.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом

    """
    await update.message.reply_text(
        "🌐 <b>DMarket WebApp</b>\n\n"
        "Нажмите кнопку ниже, чтобы открыть DMarket прямо в Telegram:",
        reply_markup=get_webapp_button(),
        parse_mode=ParseMode.HTML,
    )


async def markets_command(update, context):
    """Обрабатывает команду /markets.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом

    """
    await update.message.reply_text(
        "📊 <b>Сравнение рынков</b>\n\n" "Выберите рынки для сравнения:",
        reply_markup=get_marketplace_comparison_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def dmarket_status_command(update, context):
    """Обрабатывает команду /status или /dmarket.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом

    """
    await update.message.reply_text(
        "🔍 <b>Проверка статуса DMarket API...</b>",
        parse_mode=ParseMode.HTML,
    )


async def arbitrage_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /arbitrage.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом

    """
    await update.effective_chat.send_action(ChatAction.TYPING)

    # Используем современную клавиатуру для арбитража
    keyboard = get_modern_arbitrage_keyboard()
    await update.message.reply_text(
        "🔍 <b>Меню арбитража:</b>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )


async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения от постоянной клавиатуры.

    Args:
        update: Объект Update от Telegram
        context: Контекст взаимодействия с ботом

    """
    text = update.message.text

    # Обрабатываем различные текстовые команды от клавиатуры
    if text == "🔍 Арбитраж":
        await arbitrage_command(update, context)
    elif text == "📊 Баланс":
        await check_balance_command(update.message, context)
    elif text == "🌐 Открыть DMarket":
        await webapp_command(update, context)
    elif text == "📈 Анализ рынка":
        await update.message.reply_text(
            "📊 <b>Анализ рынка</b>\n\n" "Выберите игру для анализа рыночных тенденций и цен:",
            reply_markup=get_game_selection_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    elif text == "⚙️ Настройки":
        await update.message.reply_text(
            "⚙️ <b>Настройки</b>\n\n" "Функция находится в разработке.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_modern_arbitrage_keyboard(),
        )
    elif text == "❓ Помощь":
        await help_command(update, context)


# Экспортируем обработчики команд
__all__ = [
    "arbitrage_command",
    "dmarket_status_command",
    "handle_text_buttons",
    "help_command",
    "markets_command",
    "start_command",
    "webapp_command",
]
