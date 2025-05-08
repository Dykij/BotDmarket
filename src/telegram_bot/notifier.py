"""
Модуль для отправки уведомлений о рыночных изменениях пользователям.

Поддерживаемые типы уведомлений:
- Цена предмета упала ниже порога
- Появление выгодного предложения для покупки/продажи
- Изменение цен в наблюдаемом списке предметов
- Рост объема торгов предмета
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path  # Добавляем импорт для работы с путями

from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

from src.dmarket.dmarket_api_fixed import DMarketAPI
from src.utils.price_analyzer import get_item_price_history, analyze_supply_demand, calculate_price_trend

# Импортируем константы игр
from src.dmarket.arbitrage import GAMES

# Настраиваем логирование
logger = logging.getLogger(__name__)

# Типы уведомлений
NOTIFICATION_TYPES = {
    "price_drop": "Падение цены",
    "price_rise": "Рост цены",
    "volume_increase": "Рост объема торгов",
    "good_deal": "Выгодное предложение",
    "arbitrage": "Арбитражная возможность",
    "trend_change": "Изменение тренда"
}

# Формат хранения настроек оповещений пользователя
# {
#     "user_id": {
#         "alerts": [
#             {
#                 "id": "alert_1",
#                 "item_id": "item_123",
#                 "title": "AWP | Asiimov",
#                 "game": "csgo",
#                 "type": "price_drop",
#                 "threshold": 50.0,
#                 "created_at": timestamp,
#                 "active": True
#             },
#             ...
#         ],
#         "settings": {
#             "enabled": True,
#             "language": "ru",
#             "min_interval": 3600,  # Минимальный интервал между оповещениями (в секундах)
#             "quiet_hours": {"start": 23, "end": 8},  # Тихие часы (не отправлять оповещения)
#             "max_alerts_per_day": 10
#         },
#         "last_notification": timestamp,
#         "daily_notifications": 0,
#         "last_day": "2023-06-01"
#     }
# }
_user_alerts = {}
# Используем pathlib для более надежной работы с путями
_alerts_file = str(Path(__file__).parents[2] / "data" / "user_alerts.json")

# Кэш для текущих цен предметов для уменьшения количества запросов к API
# {item_id: {"price": price, "timestamp": timestamp}}
_current_prices_cache = {}
_PRICE_CACHE_TTL = 300  # Время жизни кэша цен (5 минут)


def load_user_alerts() -> None:
    """Загружает настройки оповещений пользователей из файла."""
    global _user_alerts
    
    try:
        alerts_path = Path(_alerts_file)
        if alerts_path.exists():
            with open(alerts_path, 'r', encoding='utf-8') as f:
                _user_alerts = json.load(f)
            logger.info(f"Загружено {len(_user_alerts)} пользовательских настроек оповещений")
        else:
            logger.warning(f"Файл с настройками оповещений не найден: {_alerts_file}")
            # Создаем директорию data если она не существует
            alerts_path.parent.mkdir(parents=True, exist_ok=True)
            _user_alerts = {}
    except Exception as e:
        logger.error(f"Ошибка при загрузке настроек оповещений: {e}")
        _user_alerts = {}


def save_user_alerts() -> None:
    """Сохраняет настройки оповещений пользователей в файл."""
    try:
        with open(_alerts_file, 'w', encoding='utf-8') as f:
            json.dump(_user_alerts, f, ensure_ascii=False, indent=2)
        logger.debug("Настройки оповещений пользователей сохранены")
    except Exception as e:
        logger.error(f"Ошибка при сохранении настроек оповещений: {e}")


async def add_price_alert(
    user_id: int, 
    item_id: str, 
    title: str, 
    game: str, 
    alert_type: str, 
    threshold: float
) -> Dict[str, Any]:
    """
    Добавляет новое оповещение о цене для пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        item_id: ID предмета на DMarket
        title: Название предмета
        game: Код игры (csgo, dota2, etc)
        alert_type: Тип оповещения (price_drop, price_rise, etc)
        threshold: Пороговое значение для оповещения
        
    Returns:
        Информация о созданном оповещении
    """
    # Создаем запись для пользователя если она не существует
    if str(user_id) not in _user_alerts:
        _user_alerts[str(user_id)] = {
            "alerts": [],
            "settings": {
                "enabled": True,
                "language": "ru",
                "min_interval": 3600,
                "quiet_hours": {"start": 23, "end": 8},
                "max_alerts_per_day": 10
            },
            "last_notification": 0,
            "daily_notifications": 0,
            "last_day": datetime.now().strftime("%Y-%m-%d")
        }
    
    # Генерируем ID для оповещения
    alert_id = f"alert_{int(time.time())}_{user_id}"
    
    # Создаем оповещение
    alert = {
        "id": alert_id,
        "item_id": item_id,
        "title": title,
        "game": game,
        "type": alert_type,
        "threshold": threshold,
        "created_at": time.time(),
        "active": True
    }
    
    # Добавляем оповещение в список
    _user_alerts[str(user_id)]["alerts"].append(alert)
    
    # Сохраняем изменения
    save_user_alerts()
    
    logger.info(f"Добавлено оповещение {alert_type} для пользователя {user_id}: {title}")
    
    return alert


async def remove_price_alert(user_id: int, alert_id: str) -> bool:
    """
    Удаляет оповещение для пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        alert_id: ID оповещения
        
    Returns:
        True если оповещение удалено, False если не найдено
    """
    user_id_str = str(user_id)
    if user_id_str not in _user_alerts:
        return False
    
    alerts = _user_alerts[user_id_str]["alerts"]
    for i, alert in enumerate(alerts):
        if alert["id"] == alert_id:
            del alerts[i]
            save_user_alerts()
            logger.info(f"Удалено оповещение {alert_id} для пользователя {user_id}")
            return True
    
    return False


async def get_user_alerts(user_id: int) -> List[Dict[str, Any]]:
    """
    Получает список активных оповещений пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        
    Returns:
        Список активных оповещений пользователя
    """
    user_id_str = str(user_id)
    if user_id_str not in _user_alerts:
        return []
    
    return [alert for alert in _user_alerts[user_id_str]["alerts"] if alert["active"]]


async def update_user_settings(
    user_id: int, 
    settings: Dict[str, Any]
) -> None:
    """
    Обновляет настройки оповещений пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        settings: Новые настройки
    """
    user_id_str = str(user_id)
    if user_id_str not in _user_alerts:
        _user_alerts[user_id_str] = {
            "alerts": [],
            "settings": {
                "enabled": True,
                "language": "ru",
                "min_interval": 3600,
                "quiet_hours": {"start": 23, "end": 8},
                "max_alerts_per_day": 10
            },
            "last_notification": 0,
            "daily_notifications": 0,
            "last_day": datetime.now().strftime("%Y-%m-%d")
        }
    
    # Обновляем настройки
    _user_alerts[user_id_str]["settings"].update(settings)
    
    # Сохраняем изменения
    save_user_alerts()
    
    logger.info(f"Обновлены настройки оповещений для пользователя {user_id}")


async def get_current_price(
    api: DMarketAPI, 
    item_id: str, 
    force_update: bool = False
) -> Optional[float]:
    """
    Получает текущую цену предмета с использованием кэша.
    
    Args:
        api: Экземпляр DMarketAPI
        item_id: ID предмета
        force_update: Принудительно обновить цену, игнорируя кэш
        
    Returns:
        Текущая цена предмета или None в случае ошибки
    """
    current_time = time.time()
    
    # Проверяем кэш
    if not force_update and item_id in _current_prices_cache:
        cache_data = _current_prices_cache[item_id]
        if current_time - cache_data["timestamp"] < _PRICE_CACHE_TTL:
            return cache_data["price"]
    
    try:
        # Получаем данные о предмете из API
        item_data = await api._request(
            "GET",
            f"/market/items/{item_id}",
            params={}
        )
        
        if not item_data:
            logger.warning(f"Не удалось получить данные о предмете {item_id}")
            return None
        
        # Извлекаем цену
        price = float(item_data.get("price", {}).get("amount", 0)) / 100  # центы в доллары
        
        # Обновляем кэш
        _current_prices_cache[item_id] = {
            "price": price,
            "timestamp": current_time
        }
        
        return price
    
    except Exception as e:
        logger.error(f"Ошибка при получении текущей цены предмета {item_id}: {e}")
        return None


async def check_price_alert(
    api: DMarketAPI, 
    alert: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Проверяет, сработало ли оповещение о цене.
    
    Args:
        api: Экземпляр DMarketAPI
        alert: Данные оповещения
        
    Returns:
        Информация о сработавшем оповещении или None
    """
    item_id = alert["item_id"]
    alert_type = alert["type"]
    threshold = alert["threshold"]
    
    current_price = await get_current_price(api, item_id)
    if current_price is None:
        logger.warning(f"Не удалось получить текущую цену для оповещения {alert['id']}")
        return None
    
    # Проверяем условие в зависимости от типа оповещения
    triggered = False
    
    if alert_type == "price_drop" and current_price <= threshold:
        triggered = True
    elif alert_type == "price_rise" and current_price >= threshold:
        triggered = True
    elif alert_type == "volume_increase":
        # Для этого типа нужно анализировать объем торгов
        price_history = await get_item_price_history(api, item_id, days=1)
        if price_history:
            volume = sum(entry.get("volume", 1) for entry in price_history)
            if volume >= threshold:
                triggered = True
    elif alert_type == "trend_change":
        # Для этого типа нужно анализировать тренд цены
        trend_info = await calculate_price_trend(api, item_id)
        if trend_info["trend"] != "stable" and trend_info["confidence"] >= threshold / 100:
            triggered = True
    
    if triggered:
        return {
            "alert": alert,
            "current_price": current_price,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    return None


async def check_good_deal_alerts(
    api: DMarketAPI, 
    user_id: int
) -> List[Dict[str, Any]]:
    """
    Проверяет наличие выгодных предложений для покупки.
    
    Args:
        api: Экземпляр DMarketAPI
        user_id: ID пользователя в Telegram
        
    Returns:
        Список сработавших оповещений
    """
    user_id_str = str(user_id)
    if user_id_str not in _user_alerts:
        return []
    
    alerts = _user_alerts[user_id_str]["alerts"]
    good_deal_alerts = [a for a in alerts if a["type"] == "good_deal" and a["active"]]
    
    if not good_deal_alerts:
        return []
    
    triggered_alerts = []
    
    for alert in good_deal_alerts:
        item_id = alert["item_id"]
        threshold = alert["threshold"]  # в процентах скидки
        
        try:
            # Получаем спрос и предложение для предмета
            supply_demand = await analyze_supply_demand(api, item_id)
            
            # Получаем историю цен для сравнения
            price_history = await get_item_price_history(api, item_id, days=7)
            
            if not price_history:
                continue
                
            # Рассчитываем среднюю цену
            prices = [entry["price"] for entry in price_history]
            avg_price = sum(prices) / len(prices) if prices else 0
            
            # Получаем лучшую цену продажи
            min_sell_price = supply_demand.get("min_sell_price", 0)
            
            if avg_price > 0 and min_sell_price > 0:
                discount = (avg_price - min_sell_price) / avg_price * 100
                
                if discount >= threshold:
                    triggered_alerts.append({
                        "alert": alert,
                        "current_price": min_sell_price,
                        "avg_price": avg_price,
                        "discount": discount,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
        
        except Exception as e:
            logger.error(f"Ошибка при проверке выгодных предложений для {item_id}: {e}")
    
    return triggered_alerts


async def check_all_alerts(
    api: DMarketAPI, 
    bot: Bot
) -> None:
    """
    Проверяет все активные оповещения и отправляет уведомления.
    
    Args:
        api: Экземпляр DMarketAPI
        bot: Экземпляр Telegram Bot
    """
    for user_id_str, user_data in _user_alerts.items():
        try:
            # Проверяем, включены ли оповещения
            if not user_data["settings"].get("enabled", True):
                continue
                
            # Проверяем лимит оповещений в день
            today = datetime.now().strftime("%Y-%m-%d")
            if user_data["last_day"] != today:
                user_data["last_day"] = today
                user_data["daily_notifications"] = 0
                
            if user_data["daily_notifications"] >= user_data["settings"].get("max_alerts_per_day", 10):
                logger.debug(f"Достигнут дневной лимит оповещений для пользователя {user_id_str}")
                continue
                
            # Проверяем тихие часы
            current_hour = datetime.now().hour
            quiet_hours = user_data["settings"].get("quiet_hours", {"start": 23, "end": 8})
            
            if quiet_hours["start"] <= quiet_hours["end"]:
                # Обычный интервал (например, с 23 до 8)
                if quiet_hours["start"] <= current_hour < quiet_hours["end"]:
                    logger.debug(f"Тихие часы для пользователя {user_id_str}")
                    continue
            else:
                # Интервал через полночь (например, с 23 до 8)
                if quiet_hours["start"] <= current_hour or current_hour < quiet_hours["end"]:
                    logger.debug(f"Тихие часы для пользователя {user_id_str}")
                    continue
                    
            # Проверяем минимальный интервал между оповещениями
            min_interval = user_data["settings"].get("min_interval", 3600)
            if time.time() - user_data.get("last_notification", 0) < min_interval:
                logger.debug(f"Слишком частые оповещения для пользователя {user_id_str}")
                continue
                
            # Получаем активные оповещения пользователя
            alerts = [a for a in user_data["alerts"] if a["active"]]
            
            if not alerts:
                continue
                
            # Проверяем каждое оповещение
            triggered_alerts = []
            
            for alert in alerts:
                alert_type = alert["type"]
                
                if alert_type in ["price_drop", "price_rise", "volume_increase", "trend_change"]:
                    result = await check_price_alert(api, alert)
                    if result:
                        triggered_alerts.append(result)
            
            # Проверяем выгодные предложения
            if any(a["type"] == "good_deal" for a in alerts):
                good_deals = await check_good_deal_alerts(api, int(user_id_str))
                triggered_alerts.extend(good_deals)
            
            # Отправляем уведомления о сработавших оповещениях
            for alert_data in triggered_alerts:
                alert = alert_data["alert"]
                current_price = alert_data["current_price"]
                
                # Формируем сообщение
                game_display = GAMES.get(alert["game"], alert["game"])
                message = f"🔔 *Оповещение сработало!*\n\n"
                message += f"*{alert['title']}* ({game_display})\n\n"
                
                if alert["type"] == "price_drop":
                    message += f"⬇️ Цена упала до *${current_price:.2f}*\n"
                    message += f"Установленный порог: *${alert['threshold']:.2f}*"
                elif alert["type"] == "price_rise":
                    message += f"⬆️ Цена выросла до *${current_price:.2f}*\n"
                    message += f"Установленный порог: *${alert['threshold']:.2f}*"
                elif alert["type"] == "volume_increase":
                    message += f"📈 Увеличился объем торгов!\n"
                    message += f"Текущая цена: *${current_price:.2f}*"
                elif alert["type"] == "good_deal":
                    avg_price = alert_data.get("avg_price", 0)
                    discount = alert_data.get("discount", 0)
                    message += f"💰 Выгодное предложение!\n"
                    message += f"Текущая цена: *${current_price:.2f}*\n"
                    message += f"Средняя цена: *${avg_price:.2f}*\n"
                    message += f"Скидка: *{discount:.2f}%*"
                elif alert["type"] == "trend_change":
                    message += f"📊 Изменение тренда цены!\n"
                    message += f"Текущая цена: *${current_price:.2f}*"
                
                # Создаем инлайн-клавиатуру
                keyboard = [
                    [
                        InlineKeyboardButton("🔍 Открыть на DMarket", url=f"https://dmarket.com/ingame-items/item-list/csgo-skins?userOfferId={alert['item_id']}")
                    ],
                    [
                        InlineKeyboardButton("🔕 Отключить оповещение", callback_data=f"disable_alert:{alert['id']}")
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    # Отправляем сообщение
                    await bot.send_message(
                        chat_id=int(user_id_str),
                        text=message,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                    
                    # Обновляем время последнего оповещения и счетчик
                    user_data["last_notification"] = time.time()
                    user_data["daily_notifications"] += 1
                    
                    logger.info(f"Отправлено оповещение пользователю {user_id_str}: {alert['title']}")
                    
                    # Если это одноразовое оповещение, деактивируем его
                    if alert.get("one_time", False):
                        alert["active"] = False
                    
                    # Сохраняем изменения
                    save_user_alerts()
                    
                    # Делаем небольшую паузу между сообщениями, чтобы избежать флуда
                    await asyncio.sleep(0.5)
                
                except Exception as e:
                    logger.error(f"Ошибка при отправке оповещения пользователю {user_id_str}: {e}")
        
        except Exception as e:
            logger.error(f"Ошибка при проверке оповещений для пользователя {user_id_str}: {e}")


async def run_alerts_checker(
    api: DMarketAPI, 
    bot: Bot, 
    interval: int = 300
) -> None:
    """
    Запускает периодическую проверку оповещений.
    
    Args:
        api: Экземпляр DMarketAPI
        bot: Экземпляр Telegram Bot
        interval: Интервал проверки в секундах
    """
    while True:
        try:
            logger.debug("Проверка оповещений...")
            await check_all_alerts(api, bot)
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении проверки оповещений: {e}")
        
        finally:
            # Ожидаем до следующей проверки
            await asyncio.sleep(interval)


async def handle_alert_callback(
    update,
    context: CallbackContext
) -> None:
    """
    Обрабатывает callback-запросы для оповещений.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст CallbackContext
    """
    query = update.callback_query
    user_id = query.from_user.id
    callback_data = query.data
    
    # Обрабатываем отключение оповещения
    if callback_data.startswith("disable_alert:"):
        alert_id = callback_data.split(":", 1)[1]
        
        # Отключаем оповещение
        success = await remove_price_alert(user_id, alert_id)
        
        if success:
            await query.answer("Оповещение отключено")
            await query.edit_message_reply_markup(reply_markup=None)
        else:
            await query.answer("Оповещение не найдено")
    else:
        await query.answer("Неизвестная команда")


def format_alert_message(alert: Dict[str, Any]) -> str:
    """
    Форматирует сообщение о настройке оповещения.
    
    Args:
        alert: Данные оповещения
        
    Returns:
        Отформатированное сообщение
    """
    game_display = GAMES.get(alert["game"], alert["game"])
    alert_type_display = NOTIFICATION_TYPES.get(alert["type"], alert["type"])
    
    message = f"*{alert['title']}* ({game_display})\n"
    message += f"Тип: {alert_type_display}\n"
    
    if alert["type"] == "price_drop":
        message += f"Порог: ${alert['threshold']:.2f} (уведомить, когда цена упадет до этого значения)"
    elif alert["type"] == "price_rise":
        message += f"Порог: ${alert['threshold']:.2f} (уведомить, когда цена вырастет до этого значения)"
    elif alert["type"] == "volume_increase":
        message += f"Порог: {int(alert['threshold'])} (уведомить, когда объем торгов превысит это значение)"
    elif alert["type"] == "good_deal":
        message += f"Порог: {alert['threshold']:.2f}% (уведомить о скидке больше этого значения)"
    elif alert["type"] == "trend_change":
        message += f"Порог уверенности: {alert['threshold']:.2f}% (уведомить при изменении тренда)"
    
    return message


async def create_alert_command(
    update, 
    context: CallbackContext,
    api: DMarketAPI
) -> None:
    """
    Обрабатывает команду /alert для создания оповещения.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст CallbackContext
        api: Экземпляр DMarketAPI
    """
    # Проверяем, переданы ли все необходимые аргументы
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "Используйте команду в формате:\n"
            "/alert <item_id> <тип_оповещения> <порог>\n\n"
            "Типы оповещений:\n"
            "- price_drop: цена упала ниже порога\n"
            "- price_rise: цена выросла выше порога\n"
            "- volume_increase: объем торгов превысил порог\n"
            "- good_deal: найдено предложение со скидкой больше порога (%)\n"
            "- trend_change: изменился тренд цены (порог - % уверенности)\n\n"
            "Пример: /alert 12345abcde price_drop 50.0"
        )
        return
    
    item_id = context.args[0]
    alert_type = context.args[1]
    
    # Проверяем тип оповещения
    if alert_type not in NOTIFICATION_TYPES:
        await update.message.reply_text(
            f"Неизвестный тип оповещения: {alert_type}\n"
            "Доступные типы: price_drop, price_rise, volume_increase, good_deal, trend_change"
        )
        return
    
    # Парсим порог
    try:
        threshold = float(context.args[2])
    except ValueError:
        await update.message.reply_text("Порог должен быть числом")
        return
    
    # Получаем информацию о предмете
    try:
        item_data = await api._request(
            "GET",
            f"/market/items/{item_id}",
            params={}
        )
        
        if not item_data:
            await update.message.reply_text(f"Предмет с ID {item_id} не найден")
            return
        
        title = item_data.get("title", "Неизвестный предмет")
        game = item_data.get("gameId", "csgo")
        
        # Создаем оповещение
        alert = await add_price_alert(
            update.effective_user.id,
            item_id,
            title,
            game,
            alert_type,
            threshold
        )
        
        # Отправляем сообщение о создании оповещения
        message = f"✅ Оповещение создано!\n\n"
        message += format_alert_message(alert)
        
        keyboard = [
            [
                InlineKeyboardButton("🔍 Открыть на DMarket", url=f"https://dmarket.com/ingame-items/item-list/csgo-skins?userOfferId={item_id}")
            ],
            [
                InlineKeyboardButton("🔕 Отключить оповещение", callback_data=f"disable_alert:{alert['id']}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при создании оповещения: {e}")
        await update.message.reply_text(f"Произошла ошибка при создании оповещения: {str(e)}")


async def list_alerts_command(
    update, 
    context: CallbackContext
) -> None:
    """
    Обрабатывает команду /alerts для просмотра списка оповещений.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст CallbackContext
    """
    user_id = update.effective_user.id
    
    # Получаем список оповещений пользователя
    alerts = await get_user_alerts(user_id)
    
    if not alerts:
        await update.message.reply_text("У вас нет активных оповещений")
        return
    
    # Формируем сообщение со списком оповещений
    message = f"📋 *Ваши активные оповещения ({len(alerts)}):*\n\n"
    
    for i, alert in enumerate(alerts, 1):
        message += f"{i}. *{alert['title']}*\n"
        message += f"   Тип: {NOTIFICATION_TYPES.get(alert['type'], alert['type'])}\n"
        
        if alert["type"] == "price_drop":
            message += f"   Порог: ${alert['threshold']:.2f}\n"
        elif alert["type"] == "price_rise":
            message += f"   Порог: ${alert['threshold']:.2f}\n"
        elif alert["type"] == "volume_increase":
            message += f"   Порог: {int(alert['threshold'])}\n"
        elif alert["type"] == "good_deal":
            message += f"   Порог: {alert['threshold']:.2f}%\n"
        elif alert["type"] == "trend_change":
            message += f"   Порог: {alert['threshold']:.2f}%\n"
        
        message += "\n"
    
    # Добавляем инструкцию по удалению
    message += "Чтобы удалить оповещение, используйте команду:\n"
    message += "/removealert <номер_оповещения>"
    
    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


async def remove_alert_command(
    update, 
    context: CallbackContext
) -> None:
    """
    Обрабатывает команду /removealert для удаления оповещения.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст CallbackContext
    """
    user_id = update.effective_user.id
    
    # Проверяем, передан ли номер оповещения
    if not context.args:
        await update.message.reply_text(
            "Используйте команду в формате:\n"
            "/removealert <номер_оповещения>\n\n"
            "Чтобы увидеть список оповещений и их номера, используйте /alerts"
        )
        return
    
    try:
        # Преобразуем номер оповещения в индекс
        alert_num = int(context.args[0])
        
        # Получаем список оповещений
        alerts = await get_user_alerts(user_id)
        
        if not alerts:
            await update.message.reply_text("У вас нет активных оповещений")
            return
        
        if alert_num < 1 or alert_num > len(alerts):
            await update.message.reply_text(f"Неверный номер оповещения. Доступны: 1-{len(alerts)}")
            return
        
        # Получаем ID оповещения
        alert_id = alerts[alert_num - 1]["id"]
        title = alerts[alert_num - 1]["title"]
        
        # Удаляем оповещение
        success = await remove_price_alert(user_id, alert_id)
        
        if success:
            await update.message.reply_text(f"Оповещение для {title} успешно удалено")
        else:
            await update.message.reply_text("Не удалось удалить оповещение")
        
    except ValueError:
        await update.message.reply_text("Номер оповещения должен быть числом")
    except Exception as e:
        logger.error(f"Ошибка при удалении оповещения: {e}")
        await update.message.reply_text(f"Произошла ошибка: {str(e)}")


async def settings_command(
    update, 
    context: CallbackContext
) -> None:
    """
    Обрабатывает команду /alertsettings для настройки параметров оповещений.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст CallbackContext
    """
    user_id = update.effective_user.id
    user_id_str = str(user_id)
    
    # Создаем запись для пользователя если её нет
    if user_id_str not in _user_alerts:
        _user_alerts[user_id_str] = {
            "alerts": [],
            "settings": {
                "enabled": True,
                "language": "ru",
                "min_interval": 3600,
                "quiet_hours": {"start": 23, "end": 8},
                "max_alerts_per_day": 10
            },
            "last_notification": 0,
            "daily_notifications": 0,
            "last_day": datetime.now().strftime("%Y-%m-%d")
        }
    
    # Получаем текущие настройки
    settings = _user_alerts[user_id_str]["settings"]
    
    # Проверяем, переданы ли параметры для изменения
    if context.args:
        # Обрабатываем аргументы
        for arg in context.args:
            if "=" in arg:
                key, value = arg.split("=", 1)
                
                if key == "enabled":
                    settings["enabled"] = value.lower() == "true"
                elif key == "language":
                    settings["language"] = value
                elif key == "min_interval":
                    try:
                        settings["min_interval"] = int(value)
                    except ValueError:
                        pass
                elif key == "quiet_start":
                    try:
                        settings["quiet_hours"]["start"] = int(value)
                    except ValueError:
                        pass
                elif key == "quiet_end":
                    try:
                        settings["quiet_hours"]["end"] = int(value)
                    except ValueError:
                        pass
                elif key == "max_alerts":
                    try:
                        settings["max_alerts_per_day"] = int(value)
                    except ValueError:
                        pass
        
        # Сохраняем изменения
        await update_user_settings(user_id, settings)
        
        await update.message.reply_text("Настройки оповещений обновлены")
    
    # Формируем сообщение с текущими настройками
    enabled = "Включены" if settings["enabled"] else "Отключены"
    language = settings["language"]
    min_interval = settings["min_interval"] // 60  # конвертируем в минуты
    quiet_start = settings["quiet_hours"]["start"]
    quiet_end = settings["quiet_hours"]["end"]
    max_alerts = settings["max_alerts_per_day"]
    
    message = f"⚙️ *Настройки оповещений*\n\n"
    message += f"• Состояние: *{enabled}*\n"
    message += f"• Язык: *{language}*\n"
    message += f"• Минимальный интервал: *{min_interval} минут*\n"
    message += f"• Тихие часы: *{quiet_start}:00 - {quiet_end}:00*\n"
    message += f"• Макс. оповещений в день: *{max_alerts}*\n\n"
    
    message += "Чтобы изменить настройки, используйте команду с параметрами:\n"
    message += "/alertsettings enabled=true|false language=ru|en min_interval=минуты quiet_start=час quiet_end=час max_alerts=число\n\n"
    message += "Пример:\n"
    message += "/alertsettings enabled=true min_interval=30 quiet_start=22 quiet_end=9"
    
    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


# Функция для регистрации обработчиков
def register_notification_handlers(application) -> None:
    """
    Регистрирует обработчики команд для оповещений.
    
    Args:
        application: Экземпляр Application
    """
    from telegram.ext import CommandHandler, CallbackQueryHandler
    
    # Загружаем настройки оповещений
    load_user_alerts()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("alert", lambda update, context: create_alert_command(update, context, application.bot_data["dmarket_api"])))
    application.add_handler(CommandHandler("alerts", list_alerts_command))
    application.add_handler(CommandHandler("removealert", remove_alert_command))
    application.add_handler(CommandHandler("alertsettings", settings_command))
    
    # Добавляем обработчик callback-запросов
    application.add_handler(CallbackQueryHandler(handle_alert_callback, pattern=r"^disable_alert:"))
    
    # Запускаем периодическую проверку оповещений
    api = application.bot_data.get("dmarket_api")
    if api:
        asyncio.create_task(run_alerts_checker(api, application.bot, interval=300))
        logger.info("Запущена периодическая проверка оповещений")
    else:
        logger.error("Не удалось запустить проверку оповещений: DMarketAPI не найден в bot_data") 