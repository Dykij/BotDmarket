"""
Обработчики для управления уведомлениями о рынке.

Этот модуль предоставляет обработчики для подписки на уведомления
о значимых изменениях на рынке, трендах и арбитражных возможностях.
"""

import logging
from typing import Dict, Any, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackContext, CommandHandler, CallbackQueryHandler, 
    Application
)

from src.telegram_bot.market_alerts import get_alerts_manager
# Импортируем новый модуль уведомлений
from src.telegram_bot.notifier import (
    load_user_alerts, 
    add_price_alert, 
    remove_price_alert, 
    get_user_alerts,
    update_user_settings,
    register_notification_handlers,
    format_alert_message,
    NOTIFICATION_TYPES
)

# Импортируем DMarketAPI из правильного модуля
from src.dmarket.dmarket_api_fixed import DMarketAPI

# Настройка логирования
logger = logging.getLogger(__name__)


# Функция преобразования типов уведомлений в человекочитаемые названия
ALERT_TYPES = {
    "price_changes": "📈 Изменения цен",
    "trending": "🔥 Трендовые предметы",
    "volatility": "📊 Волатильность рынка",
    "arbitrage": "💰 Арбитражные возможности",
    "price_drop": "⬇️ Падение цены",
    "price_rise": "⬆️ Рост цены",
    "volume_increase": "📊 Рост объема торгов",
    "good_deal": "💰 Выгодное предложение",
    "trend_change": "📊 Изменение тренда"
}


async def alerts_command(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает команду /alerts для управления подписками на уведомления.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст бота
    """
    user_id = update.effective_user.id
    
    # Получаем менеджер уведомлений
    try:
        alerts_manager = get_alerts_manager()
        
        # Получаем текущие подписки пользователя
        user_subscriptions = alerts_manager.get_user_subscriptions(user_id)
        
        # Получаем настроенные оповещения о ценах из нового модуля
        price_alerts = await get_user_alerts(user_id)
        
        # Создаем клавиатуру для управления подписками
        keyboard = []
        
        # Кнопки для глобального мониторинга рынка
        for alert_type, alert_name in ALERT_TYPES.items():
            if alert_type in ["price_changes", "trending", "volatility", "arbitrage"]:
                # Отмечаем активные подписки
                button_text = f"✅ {alert_name}" if alert_type in user_subscriptions else alert_name
                
                keyboard.append([
                    InlineKeyboardButton(
                        button_text, 
                        callback_data=f"alerts:toggle:{alert_type}"
                    )
                ])
        
        # Кнопки для управления оповещениями о конкретных предметах
        keyboard.append([
            InlineKeyboardButton("📊 Мои оповещения", callback_data="alerts:my_alerts")
        ])
        
        keyboard.append([
            InlineKeyboardButton("➕ Добавить оповещение", callback_data="alerts:create_alert")
        ])
        
        # Добавляем кнопки управления
        control_row = []
        
        # Кнопка "Подписаться на все", если есть неактивные подписки
        if len(user_subscriptions) < 4:  # Только для основных 4 типов
            control_row.append(
                InlineKeyboardButton("🔔 Подписаться на все", callback_data="alerts:subscribe_all")
            )
        
        # Кнопка "Отписаться от всех", если есть активные подписки
        if user_subscriptions:
            control_row.append(
                InlineKeyboardButton("🔕 Отписаться от всех", callback_data="alerts:unsubscribe_all")
            )
        
        if control_row:
            keyboard.append(control_row)
        
        # Добавляем кнопку настроек, если есть хотя бы одна подписка
        if user_subscriptions or price_alerts:
            keyboard.append([
                InlineKeyboardButton("⚙️ Настройки уведомлений", callback_data="alerts:settings")
            ])
        
        # Добавляем кнопку возврата к основному меню
        keyboard.append([
            InlineKeyboardButton("⬅️ Назад в меню", callback_data="arbitrage")
        ])
        
        # Формируем сообщение
        message_text = "🔔 *Управление уведомлениями*\n\n"
        
        if user_subscriptions:
            message_text += "Вы подписаны на следующие типы уведомлений о рынке:\n"
            for alert_type in user_subscriptions:
                message_text += f"• {ALERT_TYPES.get(alert_type, alert_type)}\n"
            message_text += "\n"
        
        if price_alerts:
            message_text += f"У вас {len(price_alerts)} активных оповещений о ценах предметов.\n"
            message_text += "Нажмите 'Мои оповещения' для просмотра и управления.\n\n"
            
        if not user_subscriptions and not price_alerts:
            message_text += (
                "Вы не подписаны ни на какие уведомления. Выберите типы уведомлений, "
                "которые хотите получать:\n\n"
                "• 📈 *Изменения цен* - уведомления о значительных изменениях цен на предметы\n"
                "• 🔥 *Трендовые предметы* - уведомления о популярных предметах с высоким спросом\n"
                "• 📊 *Волатильность рынка* - уведомления о нестабильности цен и возможностях для трейдинга\n"
                "• 💰 *Арбитражные возможности* - уведомления о выгодных возможностях для арбитража\n\n"
                "Также вы можете настроить персональные оповещения для конкретных предметов."
            )
        
        # Отправляем сообщение с клавиатурой
        await update.message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /alerts: {e}")
        
        await update.message.reply_text(
            "❌ Произошла ошибка при получении данных о подписках. Попробуйте позже."
        )


async def alerts_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает нажатия на кнопки управления уведомлениями.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст бота
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Разбираем данные колбэка
    parts = query.data.split(":")
    
    if len(parts) < 2:
        await query.answer("Неверный формат данных")
        return
    
    action = parts[1]
    
    try:
        alerts_manager = get_alerts_manager()
        
        # Обрабатываем различные действия
        if action == "toggle":
            # Переключение подписки на конкретный тип уведомлений
            if len(parts) < 3:
                await query.answer("Неверный формат данных")
                return
                
            alert_type = parts[2]
            
            # Проверяем, подписан ли пользователь
            user_subscriptions = alerts_manager.get_user_subscriptions(user_id)
            
            if alert_type in user_subscriptions:
                # Отписываем
                success = alerts_manager.unsubscribe(user_id, alert_type)
                if success:
                    await query.answer(f"Вы отписались от уведомлений: {ALERT_TYPES.get(alert_type, alert_type)}")
                else:
                    await query.answer("Ошибка при отписке от уведомлений")
            else:
                # Подписываем
                success = alerts_manager.subscribe(user_id, alert_type)
                if success:
                    await query.answer(f"Вы подписались на уведомления: {ALERT_TYPES.get(alert_type, alert_type)}")
                else:
                    await query.answer("Ошибка при подписке на уведомления")
            
            # Обновляем клавиатуру
            await update_alerts_keyboard(query, alerts_manager, user_id)
            
        elif action == "subscribe_all":
            # Подписка на все типы уведомлений
            success = True
            
            for alert_type in ["price_changes", "trending", "volatility", "arbitrage"]:
                if not alerts_manager.subscribe(user_id, alert_type):
                    success = False
            
            if success:
                await query.answer("Вы подписались на все типы уведомлений")
            else:
                await query.answer("Возникли ошибки при подписке на некоторые типы уведомлений")
            
            # Обновляем клавиатуру
            await update_alerts_keyboard(query, alerts_manager, user_id)
            
        elif action == "unsubscribe_all":
            # Отписка от всех уведомлений
            success = alerts_manager.unsubscribe_all(user_id)
            
            if success:
                await query.answer("Вы отписались от всех уведомлений")
            else:
                await query.answer("Ошибка при отписке от уведомлений")
            
            # Обновляем клавиатуру
            await update_alerts_keyboard(query, alerts_manager, user_id)
            
        elif action == "settings":
            # Показываем настройки уведомлений
            await show_alerts_settings(query, alerts_manager, user_id)
            
        elif action == "my_alerts":
            # Показываем список оповещений пользователя
            await show_user_alerts_list(query, user_id)
            
        elif action == "create_alert":
            # Показываем форму создания оповещения
            await show_create_alert_form(query, user_id)
            
        elif action == "remove_alert":
            # Удаление оповещения
            if len(parts) < 3:
                await query.answer("Неверный формат данных")
                return
                
            alert_id = parts[2]
            success = await remove_price_alert(user_id, alert_id)
            
            if success:
                await query.answer("Оповещение удалено")
                # Обновляем список оповещений
                await show_user_alerts_list(query, user_id)
            else:
                await query.answer("Ошибка при удалении оповещения")
            
        elif action == "threshold":
            # Обработка изменения порога для уведомлений
            if len(parts) < 4:
                await query.answer("Неверный формат данных")
                return
                
            alert_type = parts[2]
            direction = parts[3]  # "up" или "down"
            
            # Получаем текущие настройки порогов
            threshold_key = {
                "price_changes": "price_change_percent",
                "trending": "trending_popularity",
                "volatility": "volatility_threshold",
                "arbitrage": "arbitrage_profit_percent"
            }.get(alert_type)
            
            if not threshold_key:
                await query.answer("Неизвестный тип уведомлений")
                return
                
            current_threshold = alerts_manager.alert_thresholds.get(threshold_key, 0)
            
            # Изменяем порог
            if direction == "up":
                new_threshold = current_threshold * 1.5
            else:
                new_threshold = max(current_threshold * 0.7, 1.0)  # Не меньше 1%
                
            # Округляем до одного знака после запятой
            new_threshold = round(new_threshold, 1)
            
            # Обновляем порог
            success = alerts_manager.update_alert_threshold(alert_type, new_threshold)
            
            if success:
                await query.answer(f"Порог уведомлений изменен: {new_threshold}")
            else:
                await query.answer("Ошибка при изменении порога уведомлений")
            
            # Обновляем клавиатуру настроек
            await show_alerts_settings(query, alerts_manager, user_id)
            
        elif action == "interval":
            # Обработка изменения интервала проверки
            if len(parts) < 4:
                await query.answer("Неверный формат данных")
                return
                
            alert_type = parts[2]
            direction = parts[3]  # "up" или "down"
            
            # Получаем текущий интервал
            current_interval = alerts_manager.check_intervals.get(alert_type, 3600)
            
            # Изменяем интервал
            if direction == "up":
                new_interval = min(current_interval * 2, 86400)  # Максимум 24 часа
            else:
                new_interval = max(current_interval // 2, 300)  # Минимум 5 минут
                
            # Обновляем интервал
            success = alerts_manager.update_check_interval(alert_type, new_interval)
            
            if success:
                # Форматируем интервал для отображения
                if new_interval >= 3600:
                    interval_display = f"{new_interval // 3600} ч"
                else:
                    interval_display = f"{new_interval // 60} мин"
                    
                await query.answer(f"Интервал проверки изменен: {interval_display}")
            else:
                await query.answer("Ошибка при изменении интервала проверки")
            
            # Обновляем клавиатуру настроек
            await show_alerts_settings(query, alerts_manager, user_id)
            
        elif action == "back_to_alerts":
            # Возврат к главному меню уведомлений
            await update_alerts_keyboard(query, alerts_manager, user_id)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке колбэка уведомлений: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        await query.answer("Произошла ошибка при обработке запроса")


async def update_alerts_keyboard(query, alerts_manager, user_id: int) -> None:
    """
    Обновляет клавиатуру управления уведомлениями.
    
    Args:
        query: Объект запроса колбэка
        alerts_manager: Экземпляр менеджера уведомлений
        user_id: ID пользователя
    """
    # Получаем текущие подписки пользователя
    user_subscriptions = alerts_manager.get_user_subscriptions(user_id)
    
    # Получаем настроенные оповещения о ценах из нового модуля
    price_alerts = await get_user_alerts(user_id)
    
    # Создаем клавиатуру для управления подписками
    keyboard = []
    
    # Кнопки для глобального мониторинга рынка
    for alert_type, alert_name in ALERT_TYPES.items():
        if alert_type in ["price_changes", "trending", "volatility", "arbitrage"]:
            # Отмечаем активные подписки
            button_text = f"✅ {alert_name}" if alert_type in user_subscriptions else alert_name
            
            keyboard.append([
                InlineKeyboardButton(
                    button_text, 
                    callback_data=f"alerts:toggle:{alert_type}"
                )
            ])
    
    # Кнопки для управления оповещениями о конкретных предметах
    keyboard.append([
        InlineKeyboardButton("📊 Мои оповещения", callback_data="alerts:my_alerts")
    ])
    
    keyboard.append([
        InlineKeyboardButton("➕ Добавить оповещение", callback_data="alerts:create_alert")
    ])
    
    # Добавляем кнопки управления
    control_row = []
    
    # Кнопка "Подписаться на все", если есть неактивные подписки
    if len(user_subscriptions) < 4:  # Только для основных 4 типов
        control_row.append(
            InlineKeyboardButton("🔔 Подписаться на все", callback_data="alerts:subscribe_all")
        )
    
    # Кнопка "Отписаться от всех", если есть активные подписки
    if user_subscriptions:
        control_row.append(
            InlineKeyboardButton("🔕 Отписаться от всех", callback_data="alerts:unsubscribe_all")
        )
    
    if control_row:
        keyboard.append(control_row)
    
    # Добавляем кнопку настроек, если есть хотя бы одна подписка
    if user_subscriptions or price_alerts:
        keyboard.append([
            InlineKeyboardButton("⚙️ Настройки уведомлений", callback_data="alerts:settings")
        ])
    
    # Добавляем кнопку возврата к основному меню
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="arbitrage")
    ])
    
    # Формируем сообщение
    message_text = "🔔 *Управление уведомлениями*\n\n"
    
    if user_subscriptions:
        message_text += "Вы подписаны на следующие типы уведомлений о рынке:\n"
        for alert_type in user_subscriptions:
            message_text += f"• {ALERT_TYPES.get(alert_type, alert_type)}\n"
        message_text += "\n"
    
    if price_alerts:
        message_text += f"У вас {len(price_alerts)} активных оповещений о ценах предметов.\n"
        message_text += "Нажмите 'Мои оповещения' для просмотра и управления.\n\n"
        
    if not user_subscriptions and not price_alerts:
        message_text += (
            "Вы не подписаны ни на какие уведомления. Выберите типы уведомлений, "
            "которые хотите получать:\n\n"
            "• 📈 *Изменения цен* - уведомления о значительных изменениях цен на предметы\n"
            "• 🔥 *Трендовые предметы* - уведомления о популярных предметах с высоким спросом\n"
            "• 📊 *Волатильность рынка* - уведомления о нестабильности цен и возможностях для трейдинга\n"
            "• 💰 *Арбитражные возможности* - уведомления о выгодных возможностях для арбитража\n\n"
            "Также вы можете настроить персональные оповещения для конкретных предметов."
        )
    
    # Обновляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_user_alerts_list(query, user_id: int) -> None:
    """
    Показывает список оповещений пользователя из нового модуля notifier.
    
    Args:
        query: Объект запроса колбэка
        user_id: ID пользователя
    """
    # Получаем оповещения пользователя
    alerts = await get_user_alerts(user_id)
    
    if not alerts:
        # Если нет оповещений
        keyboard = [
            [
                InlineKeyboardButton("➕ Создать оповещение", callback_data="alerts:create_alert")
            ],
            [
                InlineKeyboardButton("⬅️ Назад к уведомлениям", callback_data="alerts:back_to_alerts")
            ]
        ]
        
        await query.edit_message_text(
            "🔔 *Мои оповещения*\n\n"
            "У вас нет активных оповещений о ценах предметов.\n"
            "Создайте новое оповещение, чтобы получать уведомления о значимых изменениях цен.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return
    
    # Форматируем список оповещений
    message_text = f"🔔 *Мои оповещения ({len(alerts)})*\n\n"
    
    for i, alert in enumerate(alerts, 1):
        alert_type = NOTIFICATION_TYPES.get(alert["type"], alert["type"])
        title = alert["title"]
        threshold = alert["threshold"]
        
        if alert["type"] == "price_drop":
            message_text += f"{i}. ⬇️ *{title}*\n"
            message_text += f"   Тип: {alert_type}\n"
            message_text += f"   Порог: ${threshold:.2f}\n\n"
        elif alert["type"] == "price_rise":
            message_text += f"{i}. ⬆️ *{title}*\n"
            message_text += f"   Тип: {alert_type}\n"
            message_text += f"   Порог: ${threshold:.2f}\n\n"
        elif alert["type"] == "volume_increase":
            message_text += f"{i}. 📊 *{title}*\n"
            message_text += f"   Тип: {alert_type}\n"
            message_text += f"   Порог: {int(threshold)}\n\n"
        elif alert["type"] == "good_deal":
            message_text += f"{i}. 💰 *{title}*\n"
            message_text += f"   Тип: {alert_type}\n"
            message_text += f"   Порог: {threshold:.2f}%\n\n"
        elif alert["type"] == "trend_change":
            message_text += f"{i}. 📈 *{title}*\n"
            message_text += f"   Тип: {alert_type}\n"
            message_text += f"   Порог: {threshold:.2f}%\n\n"
    
    # Создаем клавиатуру
    keyboard = []
    
    # Кнопки для удаления оповещений
    for i, alert in enumerate(alerts, 1):
        if i <= 5:  # Ограничиваем количество кнопок
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Удалить #{i} ({alert['title'][:15]}...)", 
                    callback_data=f"alerts:remove_alert:{alert['id']}"
                )
            ])
    
    # Кнопки управления
    keyboard.append([
        InlineKeyboardButton("➕ Создать оповещение", callback_data="alerts:create_alert")
    ])
    
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад к уведомлениям", callback_data="alerts:back_to_alerts")
    ])
    
    # Обновляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_create_alert_form(query, user_id: int) -> None:
    """
    Показывает форму создания оповещения.
    
    Args:
        query: Объект запроса колбэка
        user_id: ID пользователя
    """
    # Форматируем инструкцию
    message_text = (
        "➕ *Создание нового оповещения*\n\n"
        "Для создания оповещения используйте команду:\n"
        "`/alert <item_id> <тип_оповещения> <порог>`\n\n"
        "*Типы оповещений:*\n"
        "• `price_drop` - цена упала ниже порога (в $)\n"
        "• `price_rise` - цена выросла выше порога (в $)\n"
        "• `volume_increase` - объем торгов превысил порог (кол-во)\n"
        "• `good_deal` - найдено предложение со скидкой больше порога (%)\n"
        "• `trend_change` - изменился тренд цены (порог в % уверенности)\n\n"
        "*Пример:*\n"
        "`/alert 12345abcde price_drop 50.0`\n\n"
        "Для получения ID предмета, найдите его на DMarket и скопируйте из URL."
    )
    
    # Создаем клавиатуру
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Назад к списку оповещений", callback_data="alerts:my_alerts")
        ],
        [
            InlineKeyboardButton("⬅️ Назад к уведомлениям", callback_data="alerts:back_to_alerts")
        ]
    ]
    
    # Обновляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_alerts_settings(query, alerts_manager, user_id: int) -> None:
    """
    Показывает настройки уведомлений.
    
    Args:
        query: Объект запроса колбэка
        alerts_manager: Экземпляр менеджера уведомлений
        user_id: ID пользователя
    """
    # Получаем текущие подписки пользователя
    user_subscriptions = alerts_manager.get_user_subscriptions(user_id)
    
    # Формируем сообщение с настройками
    message_text = "⚙️ *Настройки уведомлений*\n\n"
    
    if user_subscriptions:
        message_text += "*Уведомления о рынке:*\n"
        
        for alert_type in user_subscriptions:
            alert_name = ALERT_TYPES.get(alert_type, alert_type)
            threshold = 0
            interval = "неизвестно"
            
            # Получаем текущие настройки порогов и интервалов
            if alert_type == "price_changes":
                threshold = alerts_manager.alert_thresholds.get("price_change_percent", 15.0)
                message_text += f"• {alert_name}\n"
                message_text += f"  Порог изменения цены: {threshold}%\n"
            elif alert_type == "trending":
                threshold = alerts_manager.alert_thresholds.get("trending_popularity", 50.0)
                message_text += f"• {alert_name}\n"
                message_text += f"  Порог популярности: {threshold}\n"
            elif alert_type == "volatility":
                threshold = alerts_manager.alert_thresholds.get("volatility_threshold", 25.0)
                message_text += f"• {alert_name}\n"
                message_text += f"  Порог волатильности: {threshold}\n"
            elif alert_type == "arbitrage":
                threshold = alerts_manager.alert_thresholds.get("arbitrage_profit_percent", 10.0)
                message_text += f"• {alert_name}\n"
                message_text += f"  Минимальная прибыль: {threshold}%\n"
                
            # Форматируем интервал для отображения
            current_interval = alerts_manager.check_intervals.get(alert_type, 3600)
            if current_interval >= 3600:
                interval = f"{current_interval // 3600} ч"
            else:
                interval = f"{current_interval // 60} мин"
                
            message_text += f"  Интервал проверки: {interval}\n\n"
    
    # Добавляем настройки личных оповещений
    message_text += "*Настройки личных оповещений:*\n"
    message_text += "Для настройки параметров личных оповещений используйте команду:\n"
    message_text += "`/alertsettings <параметр>=<значение>`\n\n"
    message_text += "Доступные параметры:\n"
    message_text += "• `enabled=true|false` - включить/выключить оповещения\n"
    message_text += "• `min_interval=минуты` - минимальный интервал между оповещениями\n"
    message_text += "• `quiet_start=час` - начало тихих часов (не отправлять оповещения)\n"
    message_text += "• `quiet_end=час` - конец тихих часов\n"
    message_text += "• `max_alerts=число` - максимальное количество оповещений в день\n\n"
    message_text += "Пример: `/alertsettings enabled=true min_interval=30`"
    
    # Создаем клавиатуру для управления настройками
    keyboard = []
    
    # Кнопки управления порогами и интервалами для подписок
    for alert_type in user_subscriptions:
        # Кнопки управления порогами
        threshold_row = [
            InlineKeyboardButton(
                f"⬇️ Порог {alert_type}", 
                callback_data=f"alerts:threshold:{alert_type}:down"
            ),
            InlineKeyboardButton(
                f"⬆️ Порог {alert_type}", 
                callback_data=f"alerts:threshold:{alert_type}:up"
            )
        ]
        keyboard.append(threshold_row)
        
        # Кнопки управления интервалами
        interval_row = [
            InlineKeyboardButton(
                f"⬇️ Интервал {alert_type}", 
                callback_data=f"alerts:interval:{alert_type}:down"
            ),
            InlineKeyboardButton(
                f"⬆️ Интервал {alert_type}", 
                callback_data=f"alerts:interval:{alert_type}:up"
            )
        ]
        keyboard.append(interval_row)
    
    # Кнопка возврата
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад к уведомлениям", callback_data="alerts:back_to_alerts")
    ])
    
    # Обновляем сообщение
    await query.edit_message_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def register_alerts_handlers(application: Application) -> None:
    """
    Регистрирует обработчики для уведомлений о рыночных событиях.
    
    Args:
        application: Экземпляр приложения Telegram
    """
    # Загружаем настройки оповещений о ценах предметов
    load_user_alerts()
    
    # Регистрируем обработчики для управления уведомлениями о рынке
    application.add_handler(CommandHandler("alerts", alerts_command))
    application.add_handler(CallbackQueryHandler(alerts_callback, pattern="^alerts:"))
    
    # Регистрируем обработчики для управления оповещениями о ценах предметов
    register_notification_handlers(application)


async def initialize_alerts_manager(application: Application) -> None:
    """
    Инициализирует менеджер уведомлений.
    
    Args:
        application: Экземпляр приложения Telegram
    """
    try:
        # Пока ничего не инициализируем, это заглушка
        logger.info("Инициализация менеджера уведомлений")
    except Exception as e:
        logger.error(f"Ошибка при инициализации менеджера уведомлений: {e}") 