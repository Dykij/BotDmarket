"""Обработчики команд для работы с DMarket.

Этот модуль содержит команды для взаимодействия с API DMarket.
"""

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.dmarket.api.client import DMarketAPI

logger = logging.getLogger(__name__)


class DMarketHandler:
    """Обработчик команд для работы с DMarket."""

    def __init__(self, public_key: str, secret_key: str, api_url: str):
        """Инициализирует обработчик команд DMarket.

        Args:
            public_key: Публичный ключ для доступа к API.
            secret_key: Секретный ключ для доступа к API.
            api_url: URL API DMarket.

        """
        self.public_key = public_key
        self.secret_key = secret_key
        self.api_url = api_url
        self.api = None

        if public_key and secret_key:
            self.initialize_api()

    def initialize_api(self) -> None:
        """Инициализирует API клиент."""
        try:
            self.api = DMarketAPI(
                public_key=self.public_key,
                secret_key=self.secret_key,
                api_url=self.api_url,
            )
            logger.info("DMarket API клиент инициализирован успешно")
        except Exception as e:
            logger.error(f"Не удалось инициализировать DMarket API клиент: {e}", exc_info=True)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Проверяет статус настройки API ключей DMarket."""
        logger.info(f"Пользователь {update.effective_user.id} использовал команду /dmarket")

        if update.message:
            if self.public_key and self.secret_key:
                await update.message.reply_text(
                    f"API ключи DMarket настроены.\nAPI endpoint: {self.api_url}",
                )
            else:
                await update.message.reply_text(
                    "API ключи DMarket не настроены.\nПожалуйста, добавьте их в .env файл.",
                )

    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Проверяет баланс на DMarket."""
        logger.info(f"Пользователь {update.effective_user.id} использовал команду /balance")

        if not self.api:
            if update.message:
                await update.message.reply_text(
                    "API DMarket не инициализирован.\nПожалуйста, проверьте настройки API ключей.",
                )
            return

        try:
            balance = self.api.get_balance()
            available_balance = balance.totalBalance - balance.blockedBalance

            if update.message:
                await update.message.reply_text(
                    f"Баланс на DMarket:\n"
                    f"Общий баланс: ${balance.totalBalance:.2f}\n"
                    f"Заблокировано: ${balance.blockedBalance:.2f}\n"
                    f"Доступно: ${available_balance:.2f}",
                )
        except Exception as e:
            logger.error(f"Ошибка при получении баланса: {e}", exc_info=True)
            if update.message:
                await update.message.reply_text(
                    "Не удалось получить информацию о балансе.\nПожалуйста, попробуйте позже.",
                )


def register_dmarket_handlers(
    app: Application,
    public_key: str,
    secret_key: str,
    api_url: str,
) -> None:
    """Регистрирует обработчики команд DMarket в приложении Telegram.

    Args:
        app: Экземпляр приложения Telegram.
        public_key: Публичный ключ для доступа к API DMarket.
        secret_key: Секретный ключ для доступа к API DMarket.
        api_url: URL API DMarket.

    """
    logger.info("Регистрация обработчиков команд DMarket")

    handler = DMarketHandler(public_key, secret_key, api_url)

    app.add_handler(CommandHandler("dmarket", handler.status_command))
    app.add_handler(CommandHandler("balance", handler.balance_command))
