"""Модуль форматирования данных для сообщений Telegram бота.

Содержит функции для форматирования различных типов данных (предметы маркета,
возможности арбитража, баланс и т.д.) в читаемый текст для отправки в сообщениях Telegram.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Максимальная длина сообщения в Telegram
MAX_MESSAGE_LENGTH = 4096

def format_balance(balance_data: Dict[str, Any]) -> str:
    """Форматирует данные о балансе в читаемый текст.
    
    Args:
        balance_data: Словарь с данными о балансе
        
    Returns:
        str: Отформатированный текст с информацией о балансе
    """
    if balance_data.get("error"):
        return f"❌ *Ошибка при получении баланса*: {balance_data.get('error_message', 'Неизвестная ошибка')}"
    
    # Получаем значения баланса
    balance = balance_data.get("balance", 0)
    available_balance = balance_data.get("available_balance", balance)
    total_balance = balance_data.get("total_balance", balance)
    
    # Форматируем сообщение
    message = [
        "💰 *Баланс DMarket*",
        "",
        f"💵 *Доступно*: ${available_balance:.2f} USD",
    ]
    
    # Добавляем общий баланс, если он отличается от доступного
    if total_balance > available_balance:
        message.append(f"🔒 *Заблокировано*: ${total_balance - available_balance:.2f} USD")
    
    message.append(f"📊 *Всего*: ${total_balance:.2f} USD")
    
    # Если баланс слишком мал для торговли
    if available_balance < 1.0:
        message.extend([
            "",
            "⚠️ *Внимание*: Доступный баланс меньше $1. Некоторые операции могут быть недоступны."
        ])
    
    return "\n".join(message)

def format_market_item(item: Dict[str, Any], show_details: bool = True) -> str:
    """Форматирует информацию о предмете маркета.
    
    Args:
        item: Словарь с данными о предмете
        show_details: Показывать ли детальную информацию
        
    Returns:
        str: Отформатированный текст с информацией о предмете
    """
    # Базовая информация
    title = item.get("title", "Неизвестный предмет")
    price_cents = item.get("price", {}).get("USD", 0)
    price_usd = price_cents / 100 if price_cents else 0
    
    message = [
        f"🏷️ *{title}*",
        f"💲 Цена: *${price_usd:.2f}*"
    ]
    
    # Добавляем детали, если нужно
    if show_details:
        # Внешний вид (для CS:GO)
        if "extra" in item and "exteriorName" in item["extra"]:
            message.append(f"🔍 Состояние: _{item['extra']['exteriorName']}_")
        
        # Float (для CS:GO)
        if "extra" in item and "floatValue" in item["extra"]:
            message.append(f"📊 Float: `{item['extra']['floatValue']}`")
        
        # Наклейки (для CS:GO)
        if "extra" in item and "stickers" in item["extra"] and item["extra"]["stickers"]:
            stickers = item["extra"]["stickers"]
            message.append(f"🏵️ Наклейки: {len(stickers)}")
        
        # Ссылка на предмет
        item_id = item.get("itemId", "")
        if item_id:
            message.append(f"🔗 [Открыть на DMarket](https://dmarket.com/ingame-items/item-list/csgo-skins?userOfferId={item_id})")
    
    return "\n".join(message)

def format_market_items(items: List[Dict[str, Any]], page: int = 0, items_per_page: int = 5) -> str:
    """Форматирует список предметов с маркета с пагинацией.
    
    Args:
        items: Список предметов
        page: Номер страницы (начиная с 0)
        items_per_page: Количество предметов на странице
        
    Returns:
        str: Отформатированный текст со списком предметов
    """
    if not items:
        return "🔍 *Предметы не найдены*"
    
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(items))
    
    page_items = items[start_idx:end_idx]
    
    message = [f"📋 *Найдено предметов: {len(items)}*"]
    message.append(f"📄 Страница {page + 1}/{(len(items) + items_per_page - 1) // items_per_page}")
    message.append("")
    
    for i, item in enumerate(page_items, start=start_idx + 1):
        item_text = format_market_item(item, show_details=False)
        message.append(f"{i}. {item_text}")
        message.append("")  # Пустая строка между предметами
    
    return "\n".join(message)

def format_opportunities(opportunities: List[Dict[str, Any]], page: int = 0, items_per_page: int = 3) -> str:
    """Форматирует список арбитражных возможностей с пагинацией.
    
    Args:
        opportunities: Список возможностей для арбитража
        page: Номер страницы (начиная с 0)
        items_per_page: Количество возможностей на странице
        
    Returns:
        str: Отформатированный текст со списком возможностей
    """
    if not opportunities:
        return "🔍 <b>Арбитражные возможности не найдены</b>"
    
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(opportunities))
    
    page_items = opportunities[start_idx:end_idx]
    
    message = [f"💰 <b>Найдено возможностей: {len(opportunities)}</b>"]
    message.append(f"📄 Страница {page + 1}/{(len(opportunities) + items_per_page - 1) // items_per_page}")
    message.append("")
    
    for i, opportunity in enumerate(page_items, start=start_idx + 1):
        # Извлекаем данные
        item_name = opportunity.get("item_name", "Неизвестный предмет")
        buy_price = opportunity.get("buy_price", 0)
        sell_price = opportunity.get("sell_price", 0)
        profit = opportunity.get("profit", 0)
        profit_percent = opportunity.get("profit_percent", 0)
        
        # Форматируем
        message.append(f"{i}. <b>{item_name}</b>")
        message.append(f"💲 Покупка: <b>${buy_price:.2f}</b> ➡️ Продажа: <b>${sell_price:.2f}</b>")
        message.append(f"📈 Прибыль: <b>${profit:.2f}</b> ({profit_percent:.2f}%)")
        
        # Добавляем ссылки если есть
        if "buy_link" in opportunity:
            message.append(f"🔗 <a href='{opportunity['buy_link']}'>Ссылка на покупку</a>")
        
        message.append("")  # Пустая строка между возможностями
    
    # Добавляем время анализа
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message.append(f"🕒 <i>Время анализа: {current_time}</i>")
    
    return "\n".join(message)

def format_error_message(error: Exception, user_friendly: bool = True) -> str:
    """Форматирует сообщение об ошибке.
    
    Args:
        error: Объект исключения
        user_friendly: Если True, возвращает сообщение, понятное пользователю
        
    Returns:
        str: Отформатированное сообщение об ошибке
    """
    if user_friendly:
        return f"❌ *Произошла ошибка*\n\n{str(error)}\n\nПожалуйста, попробуйте позже или обратитесь к команде /help для получения справки."
    
    # Техническое сообщение для отладки
    return f"❌ *Ошибка*: `{type(error).__name__}`\n\n```\n{str(error)}\n```"

def format_sales_history(sales: List[Dict[str, Any]], page: int = 0, items_per_page: int = 5) -> str:
    """Форматирует историю продаж.
    
    Args:
        sales: Список продаж
        page: Номер страницы (начиная с 0)
        items_per_page: Количество записей на странице
        
    Returns:
        str: Отформатированный текст с историей продаж
    """
    if not sales:
        return "📊 *История продаж пуста*"
    
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(sales))
    
    page_items = sales[start_idx:end_idx]
    
    message = [f"📊 *История продаж (последние {len(sales)} записей)*"]
    message.append(f"📄 Страница {page + 1}/{(len(sales) + items_per_page - 1) // items_per_page}")
    message.append("")
    
    for i, sale in enumerate(page_items, start=start_idx + 1):
        # Извлекаем данные
        item_name = sale.get("title", "Неизвестный предмет")
        price_cents = sale.get("price", {}).get("amount", 0)
        price_usd = price_cents / 100 if price_cents else 0
        
        date_str = sale.get("createdAt", "")
        if date_str:
            try:
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date_formatted = date.strftime("%d.%m.%Y %H:%M")
            except:
                date_formatted = date_str
        else:
            date_formatted = "Неизвестно"
        
        # Форматируем
        message.append(f"{i}. *{item_name}*")
        message.append(f"💰 Сумма: *${price_usd:.2f}*")
        message.append(f"🕒 Дата: _{date_formatted}_")
        message.append("")  # Пустая строка между продажами
    
    return "\n".join(message)

def split_long_message(message: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """Разбивает длинное сообщение на части, подходящие для отправки в Telegram.
    
    Args:
        message: Исходное сообщение
        max_length: Максимальная длина части
        
    Returns:
        List[str]: Список частей сообщения
    """
    if len(message) <= max_length:
        return [message]
    
    parts = []
    lines = message.split("\n")
    current_part = ""
    
    for line in lines:
        # Если добавление этой строки превысит максимальную длину,
        # сохраняем текущую часть и начинаем новую
        if len(current_part) + len(line) + 1 > max_length:
            parts.append(current_part)
            current_part = line + "\n"
        else:
            current_part += line + "\n"
    
    # Добавляем последнюю часть, если она не пуста
    if current_part:
        parts.append(current_part)
    
    return parts 