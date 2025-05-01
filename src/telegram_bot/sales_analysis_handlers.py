"""
Модуль с обработчиками для работы с историей продаж и анализа ликвидности.
"""
import logging
from typing import Dict, List, Any, Optional, cast
import json
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler

from src.dmarket.sales_history import analyze_sales_history, get_sales_history
from src.dmarket.arbitrage_sales_analysis import (
    enhanced_arbitrage_search,
    get_sales_volume_stats,
    analyze_item_liquidity
)
from src.utils.api_error_handling import APIError
from src.utils.dmarket_api_utils import execute_api_request

# Настройка логирования
logger = logging.getLogger(__name__)

# Константы для games.py
GAMES = {
    "csgo": "CS2",
    "dota2": "Dota 2",
    "tf2": "Team Fortress 2",
    "rust": "Rust"
}


async def handle_sales_analysis(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает команду /sales_analysis для анализа истории продаж предмета.
    
    Пример использования:
    /sales_analysis AWP | Asiimov (Field-Tested)
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    # Извлекаем название предмета из сообщения
    message = update.message.text.strip()
    parts = message.split(" ", 1)
    
    if len(parts) < 2:
        await update.message.reply_text(
            "⚠️ Необходимо указать название предмета!\n\n"
            "Пример: `/sales_analysis AWP | Asiimov (Field-Tested)`",
            parse_mode='Markdown'
        )
        return
    
    item_name = parts[1].strip()
    
    # Отправляем сообщение о начале анализа
    reply_message = await update.message.reply_text(
        f"🔍 Анализ истории продаж для предмета:\n`{item_name}`\n\n"
        "⏳ Пожалуйста, подождите...",
        parse_mode='Markdown'
    )
    
    try:
        # Создаем функцию для запроса анализа продаж
        async def get_analysis():
            return await analyze_sales_history(
                item_name=item_name,
                days=14  # Анализируем за 2 недели
            )
        
        # Выполняем запрос с использованием обработки ошибок API
        analysis = await execute_api_request(
            request_func=get_analysis,
            endpoint_type="last_sales",
            max_retries=2
        )
        
        # Проверяем результаты анализа
        if not analysis.get("has_data"):
            await reply_message.edit_text(
                f"⚠️ Не удалось найти данные о продажах для предмета:\n`{item_name}`\n\n"
                "Возможно, предмет редко продается или название указано неверно.",
                parse_mode='Markdown'
            )
            return
        
        # Форматируем результаты анализа
        formatted_message = (
            f"📊 Анализ продаж: `{item_name}`\n\n"
            f"💰 Средняя цена: ${analysis['avg_price']:.2f}\n"
            f"⬆️ Максимальная цена: ${analysis['max_price']:.2f}\n"
            f"⬇️ Минимальная цена: ${analysis['min_price']:.2f}\n"
            f"📈 Тренд цены: {get_trend_emoji(analysis['price_trend'])}\n"
            f"🔄 Продаж за период: {analysis['sales_volume']}\n"
            f"📆 Продаж в день: {analysis['sales_per_day']:.2f}\n"
            f"⏱️ Период анализа: {analysis['period_days']} дней\n\n"
        )
        
        # Добавляем информацию о последних продажах
        if analysis['recent_sales']:
            formatted_message += "🕒 Последние продажи:\n"
            # Показываем до 5 последних продаж
            for sale in analysis['recent_sales'][:5]:
                formatted_message += (
                    f"• {sale['date']} - ${sale['price']:.2f} {sale['currency']}\n"
                )
        
        # Добавляем кнопку для показа полной истории продаж
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📊 Подробная история",
                    callback_data=f"sales_history:{item_name}"
                )
            ],
            [
                InlineKeyboardButton(
                    "💧 Анализ ликвидности",
                    callback_data=f"liquidity:{item_name}"
                )
            ]
        ])
        
        # Отправляем результаты анализа
        await reply_message.edit_text(
            text=formatted_message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    except APIError as e:
        # Обработка ошибок API
        logger.error(f"Ошибка API при анализе продаж: {e}")
        await reply_message.edit_text(
            f"❌ Ошибка при получении данных о продажах: {e.message}",
            parse_mode='Markdown'
        )
    except Exception as e:
        # Обработка прочих ошибок
        logger.exception(f"Ошибка при анализе продаж: {str(e)}")
        await reply_message.edit_text(
            f"❌ Произошла ошибка: {str(e)}",
            parse_mode='Markdown'
        )


async def handle_arbitrage_with_sales(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает команду /arbitrage_sales для поиска арбитражных возможностей 
    с учетом истории продаж.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    # Получаем текущую игру из контекста или используем CSGO по умолчанию
    game = "csgo"
    if hasattr(context, 'user_data') and "current_game" in context.user_data:
        game = context.user_data["current_game"]
    
    # Отправляем сообщение о начале поиска
    reply_message = await update.message.reply_text(
        f"🔍 Поиск арбитражных возможностей с учетом истории продаж для {GAMES.get(game, game)}...\n\n"
        "⏳ Пожалуйста, подождите...",
        parse_mode='Markdown'
    )
    
    try:
        # Создаем функцию для запроса арбитражных возможностей
        async def search_arbitrage():
            return await enhanced_arbitrage_search(
                game=game,
                max_items=10,
                min_profit=1.0,
                min_profit_percent=5.0,
                min_sales_per_day=0.3,  # Минимум 1 продажа за 3 дня
                time_period_days=7
            )
        
        # Выполняем запрос с использованием обработки ошибок API
        results = await execute_api_request(
            request_func=search_arbitrage,
            endpoint_type="market",
            max_retries=2
        )
        
        # Проверяем результаты поиска
        opportunities = results.get("opportunities", [])
        if not opportunities:
            await reply_message.edit_text(
                f"⚠️ Не найдено арбитражных возможностей с учетом истории продаж для {GAMES.get(game, game)}.\n\n"
                "Попробуйте изменить параметры фильтрации или выбрать другую игру.",
                parse_mode='Markdown'
            )
            return
        
        # Форматируем результаты поиска
        formatted_message = (
            f"📊 Арбитражные возможности с учетом продаж для {GAMES.get(game, game)}\n\n"
            f"🔎 Найдено предметов: {len(opportunities)}\n"
            f"📆 Период анализа: {results['filters']['time_period_days']} дней\n\n"
        )
        
        # Добавляем информацию о найденных предметах
        for i, item in enumerate(opportunities[:5], 1):
            sales_analysis = item.get("sales_analysis", {})
            
            formatted_message += (
                f"🏆 {i}. `{item['market_hash_name']}`\n"
                f"💰 Прибыль: ${item['profit']:.2f} ({item['profit_percent']:.1f}%)\n"
                f"🛒 Цена покупки: ${item['buy_price']:.2f}\n"
                f"💵 Цена продажи: ${item['sell_price']:.2f}\n"
                f"📈 Тренд: {get_trend_emoji(sales_analysis.get('price_trend', 'stable'))}\n"
                f"🔄 Продаж в день: {sales_analysis.get('sales_per_day', 0):.2f}\n\n"
            )
        
        # Если найдено больше 5 предметов, добавляем сообщение о показе только части
        if len(opportunities) > 5:
            formatted_message += (
                f"_Показаны 5 из {len(opportunities)} найденных возможностей._\n\n"
            )
        
        # Добавляем кнопки управления
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📊 Все возможности", 
                    callback_data=f"all_arbitrage_sales:{game}"
                ),
                InlineKeyboardButton(
                    "🔍 Обновить", 
                    callback_data=f"refresh_arbitrage_sales:{game}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⚙️ Настроить фильтры", 
                    callback_data=f"setup_sales_filters:{game}"
                )
            ]
        ])
        
        # Отправляем результаты поиска
        await reply_message.edit_text(
            text=formatted_message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    except APIError as e:
        # Обработка ошибок API
        logger.error(f"Ошибка API при поиске арбитража с учетом продаж: {e}")
        await reply_message.edit_text(
            f"❌ Ошибка при поиске арбитражных возможностей: {e.message}",
            parse_mode='Markdown'
        )
    except Exception as e:
        # Обработка прочих ошибок
        logger.exception(f"Ошибка при поиске арбитража с учетом продаж: {str(e)}")
        await reply_message.edit_text(
            f"❌ Произошла ошибка: {str(e)}",
            parse_mode='Markdown'
        )


async def handle_liquidity_analysis(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает команду /liquidity для анализа ликвидности предмета.
    
    Пример использования:
    /liquidity AWP | Asiimov (Field-Tested)
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    # Извлекаем название предмета из сообщения
    message = update.message.text.strip()
    parts = message.split(" ", 1)
    
    if len(parts) < 2:
        await update.message.reply_text(
            "⚠️ Необходимо указать название предмета!\n\n"
            "Пример: `/liquidity AWP | Asiimov (Field-Tested)`",
            parse_mode='Markdown'
        )
        return
    
    item_name = parts[1].strip()
    game = "csgo"  # По умолчанию используем CS2
    
    # Если в контексте задана игра, используем её
    if hasattr(context, 'user_data') and "current_game" in context.user_data:
        game = context.user_data["current_game"]
    
    # Отправляем сообщение о начале анализа
    reply_message = await update.message.reply_text(
        f"🔍 Анализ ликвидности предмета:\n`{item_name}`\n\n"
        "⏳ Пожалуйста, подождите...",
        parse_mode='Markdown'
    )
    
    try:
        # Создаем функцию для запроса анализа ликвидности
        async def get_liquidity_analysis():
            return await analyze_item_liquidity(
                item_name=item_name,
                game=game
            )
        
        # Выполняем запрос с использованием обработки ошибок API
        analysis = await execute_api_request(
            request_func=get_liquidity_analysis,
            endpoint_type="market",
            max_retries=2
        )
        
        # Проверяем результаты анализа
        sales_analysis = analysis.get("sales_analysis", {})
        if not sales_analysis.get("has_data"):
            await reply_message.edit_text(
                f"⚠️ Не удалось найти данные о продажах для предмета:\n`{item_name}`\n\n"
                "Возможно, предмет редко продается или название указано неверно.",
                parse_mode='Markdown'
            )
            return
        
        # Получаем эмодзи для категории ликвидности
        liquidity_emoji = get_liquidity_emoji(analysis.get("liquidity_category", "Низкая"))
        
        # Форматируем результаты анализа
        formatted_message = (
            f"💧 Анализ ликвидности: `{item_name}`\n\n"
            f"{liquidity_emoji} Категория: {analysis['liquidity_category']}\n"
            f"📊 Оценка: {analysis['liquidity_score']}/7\n\n"
            f"📈 Тренд цены: {get_trend_emoji(sales_analysis.get('price_trend', 'stable'))}\n"
            f"🔄 Продаж в день: {sales_analysis.get('sales_per_day', 0):.2f}\n"
            f"📆 Всего продаж: {sales_analysis.get('sales_volume', 0)}\n"
            f"💰 Средняя цена: ${sales_analysis.get('avg_price', 0):.2f}\n\n"
        )
        
        # Добавляем информацию о рынке
        market_data = analysis.get("market_data", {})
        formatted_message += (
            f"🛒 Предложений на рынке: {market_data.get('offers_count', 0)}\n"
            f"⬇️ Минимальная цена: ${market_data.get('lowest_price', 0):.2f}\n"
            f"⬆️ Максимальная цена: ${market_data.get('highest_price', 0):.2f}\n\n"
        )
        
        # Добавляем рекомендацию по арбитражу
        if analysis['liquidity_category'] in ['Очень высокая', 'Высокая']:
            formatted_message += "✅ *Рекомендация*: Отлично подходит для арбитража!\n"
        elif analysis['liquidity_category'] == 'Средняя':
            formatted_message += "⚠️ *Рекомендация*: Может подойти для арбитража, но с осторожностью.\n"
        else:
            formatted_message += "❌ *Рекомендация*: Не рекомендуется для арбитража из-за низкой ликвидности.\n"
        
        # Добавляем кнопки управления
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📊 История продаж",
                    callback_data=f"sales_history:{item_name}"
                ),
                InlineKeyboardButton(
                    "🔍 Обновить анализ",
                    callback_data=f"refresh_liquidity:{item_name}"
                )
            ]
        ])
        
        # Отправляем результаты анализа
        await reply_message.edit_text(
            text=formatted_message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    except APIError as e:
        # Обработка ошибок API
        logger.error(f"Ошибка API при анализе ликвидности: {e}")
        await reply_message.edit_text(
            f"❌ Ошибка при анализе ликвидности: {e.message}",
            parse_mode='Markdown'
        )
    except Exception as e:
        # Обработка прочих ошибок
        logger.exception(f"Ошибка при анализе ликвидности: {str(e)}")
        await reply_message.edit_text(
            f"❌ Произошла ошибка: {str(e)}",
            parse_mode='Markdown'
        )


async def handle_sales_volume_stats(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает команду /sales_volume для просмотра статистики объема продаж.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    # Получаем текущую игру из контекста или используем CSGO по умолчанию
    game = "csgo"
    if hasattr(context, 'user_data') and "current_game" in context.user_data:
        game = context.user_data["current_game"]
    
    # Отправляем сообщение о начале запроса
    reply_message = await update.message.reply_text(
        f"🔍 Получение статистики объема продаж для {GAMES.get(game, game)}...\n\n"
        "⏳ Пожалуйста, подождите...",
        parse_mode='Markdown'
    )
    
    try:
        # Создаем функцию для запроса статистики объема продаж
        async def get_volume_stats():
            return await get_sales_volume_stats(
                game=game,
                top_items=30  # Анализируем 30 популярных предметов
            )
        
        # Выполняем запрос с использованием обработки ошибок API
        stats = await execute_api_request(
            request_func=get_volume_stats,
            endpoint_type="market",
            max_retries=2
        )
        
        # Проверяем результаты запроса
        items = stats.get("items", [])
        if not items:
            await reply_message.edit_text(
                f"⚠️ Не удалось получить статистику объема продаж для {GAMES.get(game, game)}.",
                parse_mode='Markdown'
            )
            return
        
        # Форматируем результаты
        formatted_message = (
            f"📊 Статистика объема продаж для {GAMES.get(game, game)}\n\n"
            f"🔎 Проанализировано предметов: {stats['count']}\n"
            f"⬆️ Предметов с растущей ценой: {stats['summary']['up_trend_count']}\n"
            f"⬇️ Предметов с падающей ценой: {stats['summary']['down_trend_count']}\n"
            f"➡️ Предметов со стабильной ценой: {stats['summary']['stable_trend_count']}\n\n"
            f"📈 Топ-5 предметов по объему продаж:\n"
        )
        
        # Добавляем информацию о предметах с наибольшим объемом продаж
        for i, item in enumerate(items[:5], 1):
            formatted_message += (
                f"{i}. `{item['item_name']}`\n"
                f"   🔄 Продаж в день: {item['sales_per_day']:.2f}\n"
                f"   💰 Средняя цена: ${item['avg_price']:.2f}\n"
                f"   📈 Тренд: {get_trend_emoji(item['price_trend'])}\n\n"
            )
        
        # Добавляем кнопки управления
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📊 Показать все предметы",
                    callback_data=f"all_volume_stats:{game}"
                ),
                InlineKeyboardButton(
                    "🔍 Обновить",
                    callback_data=f"refresh_volume_stats:{game}"
                )
            ]
        ])
        
        # Отправляем результаты
        await reply_message.edit_text(
            text=formatted_message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    except APIError as e:
        # Обработка ошибок API
        logger.error(f"Ошибка API при получении статистики объема продаж: {e}")
        await reply_message.edit_text(
            f"❌ Ошибка при получении статистики: {e.message}",
            parse_mode='Markdown'
        )
    except Exception as e:
        # Обработка прочих ошибок
        logger.exception(f"Ошибка при получении статистики объема продаж: {str(e)}")
        await reply_message.edit_text(
            f"❌ Произошла ошибка: {str(e)}",
            parse_mode='Markdown'
        )


# Вспомогательные функции

def get_trend_emoji(trend: str) -> str:
    """Возвращает эмодзи для тренда цены."""
    if trend == "up":
        return "⬆️ Растет"
    elif trend == "down":
        return "⬇️ Падает"
    else:
        return "➡️ Стабилен"


def get_liquidity_emoji(liquidity_category: str) -> str:
    """Возвращает эмодзи для категории ликвидности."""
    if liquidity_category == "Очень высокая":
        return "💧💧💧💧"
    elif liquidity_category == "Высокая":
        return "💧💧💧"
    elif liquidity_category == "Средняя":
        return "💧💧"
    else:
        return "💧"
