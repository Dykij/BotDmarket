"""
Функции инициализации Telegram бота.

Этот модуль содержит функции для инициализации и настройки бота при запуске.
"""

import logging
from typing import List

from telegram import BotCommand, BotCommandScopeDefault
from telegram.ext import Application

from src.telegram_bot.handlers.market_alerts_handler import initialize_alerts_manager

logger = logging.getLogger(__name__)

async def set_bot_commands(application: Application) -> None:
    """
    Устанавливает команды бота для отображения в меню команд Telegram.
    
    Args:
        application: Экземпляр приложения Telegram
    """
    commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("help", "Показать справку"),
        BotCommand("status", "Проверить статус API DMarket"),
        BotCommand("arbitrage", "Показать меню арбитража"),
        BotCommand("filters", "Управление фильтрами предметов"),
        BotCommand("balance", "Проверить баланс DMarket"),
        BotCommand("market_analysis", "Анализ тенденций рынка"),
        BotCommand("alerts", "Управление уведомлениями"),
        BotCommand("webapp", "Открыть DMarket в WebApp"),
        BotCommand("markets", "Сравнение рынков"),
    ]
    
    await application.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    logger.info("Команды бота успешно установлены")


async def initialize_application(application: Application) -> None:
    """
    Инициализирует приложение бота.
    
    Args:
        application: Экземпляр приложения Telegram
    """
    # Устанавливаем команды бота
    await set_bot_commands(application)
    
    # Инициализируем менеджер уведомлений
    await initialize_alerts_manager(application)
    
    logger.info("Инициализация бота завершена")

# Экспортируем функции инициализации
__all__ = ['set_bot_commands', 'initialize_application'] 