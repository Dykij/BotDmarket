"""Обработчик уведомлений о ценах в Telegram боте.

Этот модуль обеспечивает функциональность получения уведомлений
о ценах на предметы DMarket в реальном времени через Telegram.
"""

import asyncio
from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.dmarket.dmarket_api import DMarketAPI
from src.dmarket.realtime_price_watcher import PriceAlert, RealtimePriceWatcher
from src.telegram_bot.constants import PRICE_ALERT_STORAGE_KEY

# Состояния для ConversationHandler
ITEM_NAME, ALERT_PRICE, ALERT_CONDITION = range(3)

# Колбэк-данные для клавиатур
CALLBACK_ALERT_LIST = "alert_list"
CALLBACK_ADD_ALERT = "add_alert"
CALLBACK_REMOVE_ALERT = "rem_alert:"
CALLBACK_CANCEL = "alert_cancel"
CALLBACK_CONDITION_BELOW = "cond_below"
CALLBACK_CONDITION_ABOVE = "cond_above"


class PriceAlertsHandler:
    """Обработчик уведомлений о ценах в Telegram боте."""

    def __init__(self, api_client: DMarketAPI):
        """Инициализация обработчика уведомлений о ценах.

        Args:
            api_client: Экземпляр DMarketAPI для работы с API

        """
        self.api_client = api_client
        self.price_watcher = RealtimePriceWatcher(api_client)
        self._user_temp_data = {}  # Временные данные для диалогов
        self._is_watcher_started = False

        # Регистрируем обработчик оповещений
        self.price_watcher.register_alert_handler(self._handle_alert_triggered)

    async def ensure_watcher_started(self) -> None:
        """Убеждаемся, что наблюдатель за ценами запущен."""
        if not self._is_watcher_started:
            success = await self.price_watcher.start()
            self._is_watcher_started = success

    async def _handle_alert_triggered(
        self,
        alert: PriceAlert,
        current_price: float,
    ) -> None:
        """Обработчик срабатывания оповещения.

        Args:
            alert: Сработавшее оповещение
            current_price: Текущая цена предмета

        """
        # Здесь будет логика отправки уведомления пользователю
        # Однако, этот метод вызывается не в контексте обработчика Telegram,
        # поэтому нужно будет сохранить информацию о сработавшем оповещении
        # и обработать ее позже в контексте Telegram.

    async def handle_price_alerts_command(
        self,
        update: Update,
        context: CallbackContext,
    ) -> None:
        """Обработчик команды /price_alerts.

        Args:
            update: Объект Update от Telegram
            context: Контекст вызова

        """
        await self.ensure_watcher_started()

        keyboard = [
            [
                InlineKeyboardButton(
                    "📋 Список оповещений",
                    callback_data=CALLBACK_ALERT_LIST,
                ),
            ],
            [
                InlineKeyboardButton(
                    "➕ Добавить оповещение",
                    callback_data=CALLBACK_ADD_ALERT,
                ),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🔔 *Оповещения о ценах*\n\n"
            "Создавайте оповещения о ценах на предметы и получайте уведомления "
            "в реальном времени, когда цена достигнет указанного значения.",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    async def handle_alert_list_callback(
        self,
        update: Update,
        context: CallbackContext,
    ) -> None:
        """Обработчик колбэка для отображения списка оповещений.

        Args:
            update: Объект Update от Telegram
            context: Контекст вызова

        """
        query = update.callback_query
        await query.answer()

        user_id = str(update.effective_user.id)

        # Получаем оповещения пользователя из user_data
        alerts_data = context.user_data.get(PRICE_ALERT_STORAGE_KEY, {})

        if not alerts_data:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "➕ Добавить оповещение",
                        callback_data=CALLBACK_ADD_ALERT,
                    ),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "🔍 У вас пока нет активных оповещений о ценах.\n\n"
                "Нажмите кнопку ниже, чтобы добавить новое оповещение.",
                reply_markup=reply_markup,
            )
            return

        # Формируем сообщение со списком оповещений
        message_text = "🔔 *Ваши оповещения о ценах:*\n\n"

        keyboard = []

        for alert_id, alert_data in alerts_data.items():
            item_name = alert_data["market_hash_name"]
            target_price = alert_data["target_price"]
            condition = alert_data["condition"]
            condition_text = "≤" if condition == "below" else "≥"

            message_text += f"• *{item_name}*\n"
            message_text += f"  Цена {condition_text} ${target_price:.2f}\n\n"

            # Добавляем кнопку для удаления этого оповещения
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"❌ Удалить {item_name}",
                        callback_data=f"{CALLBACK_REMOVE_ALERT}{alert_id}",
                    ),
                ],
            )

        # Добавляем кнопку для создания нового оповещения
        keyboard.append(
            [
                InlineKeyboardButton(
                    "➕ Добавить оповещение",
                    callback_data=CALLBACK_ADD_ALERT,
                ),
            ],
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    async def handle_add_alert_callback(
        self,
        update: Update,
        context: CallbackContext,
    ) -> int:
        """Обработчик колбэка для добавления нового оповещения (шаг 1).

        Args:
            update: Объект Update от Telegram
            context: Контекст вызова

        Returns:
            int: Следующее состояние разговора

        """
        query = update.callback_query
        await query.answer()

        user_id = str(update.effective_user.id)
        self._user_temp_data[user_id] = {}

        await query.edit_message_text(
            "🔍 *Добавление оповещения о цене*\n\n"
            "Введите полное название предмета (market_hash_name), "
            "например: `AWP | Asiimov (Field-Tested)`\n\n"
            "Или отправьте /cancel для отмены.",
            parse_mode="Markdown",
        )

        return ITEM_NAME

    async def handle_item_name_input(
        self,
        update: Update,
        context: CallbackContext,
    ) -> int:
        """Обработчик ввода названия предмета для оповещения (шаг 2).

        Args:
            update: Объект Update от Telegram
            context: Контекст вызова

        Returns:
            int: Следующее состояние разговора

        """
        user_id = str(update.effective_user.id)
        item_name = update.message.text.strip()

        # Сохраняем введенное название предмета
        self._user_temp_data[user_id]["item_name"] = item_name

        # Здесь можно добавить проверку существования предмета через API

        await update.message.reply_text(
            f"📝 Выбран предмет: *{item_name}*\n\n"
            "Теперь введите целевую цену в USD (только число), "
            "например: `50.5` для 50.50$\n\n"
            "Или отправьте /cancel для отмены.",
            parse_mode="Markdown",
        )

        return ALERT_PRICE

    async def handle_alert_price_input(
        self,
        update: Update,
        context: CallbackContext,
    ) -> int:
        """Обработчик ввода целевой цены для оповещения (шаг 3).

        Args:
            update: Объект Update от Telegram
            context: Контекст вызова

        Returns:
            int: Следующее состояние разговора

        """
        user_id = str(update.effective_user.id)
        price_text = update.message.text.strip()

        try:
            target_price = float(price_text)
            if target_price <= 0:
                raise ValueError("Цена должна быть положительной")
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите корректное число для цены.\n\n"
                "Например: `50.5` для 50.50$\n\n"
                "Или отправьте /cancel для отмены.",
                parse_mode="Markdown",
            )
            return ALERT_PRICE

        # Сохраняем введенную целевую цену
        self._user_temp_data[user_id]["target_price"] = target_price

        # Предлагаем выбрать условие срабатывания
        keyboard = [
            [
                InlineKeyboardButton(
                    "⬇️ Цена опустится НИЖЕ или РАВНА",
                    callback_data=CALLBACK_CONDITION_BELOW,
                ),
            ],
            [
                InlineKeyboardButton(
                    "⬆️ Цена поднимется ВЫШЕ или РАВНА",
                    callback_data=CALLBACK_CONDITION_ABOVE,
                ),
            ],
            [InlineKeyboardButton("❌ Отмена", callback_data=CALLBACK_CANCEL)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"💲 Целевая цена: *${target_price:.2f}*\n\n"
            "Выберите условие срабатывания оповещения:",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        return ALERT_CONDITION

    async def handle_alert_condition_callback(
        self,
        update: Update,
        context: CallbackContext,
    ) -> int:
        """Обработчик выбора условия срабатывания оповещения (шаг 4).

        Args:
            update: Объект Update от Telegram
            context: Контекст вызова

        Returns:
            int: Следующее состояние разговора (ConversationHandler.END)

        """
        query = update.callback_query
        await query.answer()

        user_id = str(update.effective_user.id)
        callback_data = query.data

        if callback_data == CALLBACK_CANCEL:
            await query.edit_message_text("❌ Создание оповещения отменено.")
            return ConversationHandler.END

        # Определяем условие срабатывания
        condition = "below" if callback_data == CALLBACK_CONDITION_BELOW else "above"
        condition_text = "ниже или равна" if condition == "below" else "выше или равна"

        # Получаем данные из временного хранилища
        item_data = self._user_temp_data.get(user_id, {})
        item_name = item_data.get("item_name", "")
        target_price = item_data.get("target_price", 0.0)

        # Создаем уникальный ID для оповещения
        import uuid

        alert_id = str(uuid.uuid4())

        # Сохраняем оповещение в user_data
        if PRICE_ALERT_STORAGE_KEY not in context.user_data:
            context.user_data[PRICE_ALERT_STORAGE_KEY] = {}

        context.user_data[PRICE_ALERT_STORAGE_KEY][alert_id] = {
            "market_hash_name": item_name,
            "target_price": target_price,
            "condition": condition,
            "created_at": asyncio.get_event_loop().time(),
            "is_triggered": False,
        }

        # TODO: Получить item_id для предмета через API и создать реальное оповещение
        # в price_watcher

        await query.edit_message_text(
            f"✅ Оповещение успешно создано!\n\n"
            f"*{item_name}*\n"
            f"Вы получите уведомление, когда цена будет {condition_text} "
            f"*${target_price:.2f}*",
            parse_mode="Markdown",
        )

        # Очищаем временные данные
        if user_id in self._user_temp_data:
            del self._user_temp_data[user_id]

        return ConversationHandler.END

    async def handle_remove_alert_callback(
        self,
        update: Update,
        context: CallbackContext,
    ) -> None:
        """Обработчик колбэка для удаления оповещения.

        Args:
            update: Объект Update от Telegram
            context: Контекст вызова

        """
        query = update.callback_query
        await query.answer()

        user_id = str(update.effective_user.id)
        callback_data = query.data

        # Извлекаем ID оповещения из callback_data
        alert_id = callback_data.replace(CALLBACK_REMOVE_ALERT, "")

        # Проверяем, существует ли оповещение
        alerts_data = context.user_data.get(PRICE_ALERT_STORAGE_KEY, {})
        if alert_id not in alerts_data:
            await query.edit_message_text("❌ Оповещение не найдено или уже удалено.")
            return

        # Получаем информацию об оповещении для отображения
        alert_info = alerts_data[alert_id]
        item_name = alert_info["market_hash_name"]

        # Удаляем оповещение
        del context.user_data[PRICE_ALERT_STORAGE_KEY][alert_id]

        # TODO: Удалить оповещение из price_watcher, если оно там есть

        # Возвращаемся к списку оповещений
        await self.handle_alert_list_callback(update, context)

    async def handle_cancel(self, update: Update, context: CallbackContext) -> int:
        """Обработчик команды /cancel для отмены создания оповещения.

        Args:
            update: Объект Update от Telegram
            context: Контекст вызова

        Returns:
            int: Состояние окончания разговора (ConversationHandler.END)

        """
        user_id = str(update.effective_user.id)

        # Очищаем временные данные
        if user_id in self._user_temp_data:
            del self._user_temp_data[user_id]

        await update.message.reply_text(
            "❌ Создание оповещения отменено.",
        )

        return ConversationHandler.END

    async def handle_alert_notification(
        self,
        alert: PriceAlert,
        current_price: float,
        context: CallbackContext,
    ) -> None:
        """Отправляет уведомление о сработавшем оповещении.

        Args:
            alert: Сработавшее оповещение
            current_price: Текущая цена предмета
            context: Контекст вызова

        """
        # TODO: Реализовать отправку уведомления пользователю

    def get_handlers(self) -> List:
        """Возвращает список обработчиков для регистрации в диспетчере.

        Returns:
            List: Список обработчиков Telegram

        """
        # Обработчик команды /price_alerts
        price_alerts_handler = CommandHandler(
            "price_alerts",
            self.handle_price_alerts_command,
        )

        # Обработчики колбэков для основного меню
        alert_list_handler = CallbackQueryHandler(
            self.handle_alert_list_callback,
            pattern=f"^{CALLBACK_ALERT_LIST}$",
        )
        remove_alert_handler = CallbackQueryHandler(
            self.handle_remove_alert_callback,
            pattern=f"^{CALLBACK_REMOVE_ALERT}",
        )

        # Разговор для добавления оповещения
        add_alert_conversation = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    self.handle_add_alert_callback,
                    pattern=f"^{CALLBACK_ADD_ALERT}$",
                ),
            ],
            states={
                ITEM_NAME: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_item_name_input,
                    ),
                ],
                ALERT_PRICE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_alert_price_input,
                    ),
                ],
                ALERT_CONDITION: [
                    CallbackQueryHandler(
                        self.handle_alert_condition_callback,
                        pattern=f"^({CALLBACK_CONDITION_BELOW}|{CALLBACK_CONDITION_ABOVE}|{CALLBACK_CANCEL})$",
                    ),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.handle_cancel)],
            per_user=True,
        )

        return [
            price_alerts_handler,
            alert_list_handler,
            remove_alert_handler,
            add_alert_conversation,
        ]
