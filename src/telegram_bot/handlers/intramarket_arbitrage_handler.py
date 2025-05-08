"""Обработчик команд для внутрирыночного арбитража на DMarket."""

import asyncio
import logging
from typing import Dict, List, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from src.dmarket.arbitrage import GAMES
from src.dmarket.intramarket_arbitrage import (
    scan_for_intramarket_opportunities,
    find_price_anomalies,
    find_trending_items,
    find_mispriced_rare_items,
    PriceAnomalyType,
)
from src.telegram_bot.keyboards import get_arbitrage_keyboard
from src.telegram_bot.pagination import pagination_manager, format_paginated_results

logger = logging.getLogger(__name__)

# Константы для callback данных
INTRA_ARBITRAGE_ACTION = "intra"
ANOMALY_ACTION = "anomaly"
TRENDING_ACTION = "trend"
RARE_ACTION = "rare"

# Форматирование результатов
def format_intramarket_result(result: Dict[str, Any]) -> str:
    """Форматирует результат внутрирыночного арбитража для отображения.
    
    Args:
        result: Результат арбитража
        
    Returns:
        Отформатированный текст
    """
    result_type = result.get("type", "")
    
    if result_type == PriceAnomalyType.UNDERPRICED:
        # Ценовая аномалия (недооцененный предмет)
        item_to_buy = result.get("item_to_buy", {})
        item_title = item_to_buy.get("title", "Неизвестный предмет")
        buy_price = result.get("buy_price", 0.0)
        sell_price = result.get("sell_price", 0.0)
        profit_percentage = result.get("profit_percentage", 0.0)
        profit_after_fee = result.get("profit_after_fee", 0.0)
        similarity = result.get("similarity", 0.0)
        
        return (
            f"🔍 *{item_title}*\n"
            f"💰 Купить за ${buy_price:.2f}, продать за ${sell_price:.2f}\n"
            f"📈 Прибыль: ${profit_after_fee:.2f} ({profit_percentage:.1f}%)\n"
            f"🔄 Схожесть: {similarity:.0%}\n"
            f"🏷️ ID для покупки: `{item_to_buy.get('itemId', '')}`"
        )
    
    elif result_type == PriceAnomalyType.TRENDING_UP:
        # Растущая цена
        item = result.get("item", {})
        item_title = item.get("title", "Неизвестный предмет")
        current_price = result.get("current_price", 0.0)
        projected_price = result.get("projected_price", 0.0)
        price_change_percent = result.get("price_change_percent", 0.0)
        potential_profit_percent = result.get("potential_profit_percent", 0.0)
        sales_velocity = result.get("sales_velocity", 0)
        
        return (
            f"📈 *{item_title}*\n"
            f"💰 Текущая цена: ${current_price:.2f}\n"
            f"🚀 Прогноз цены: ${projected_price:.2f} (+{price_change_percent:.1f}%)\n"
            f"💵 Потенциальная прибыль: ${projected_price-current_price:.2f} ({potential_profit_percent:.1f}%)\n"
            f"🔄 Объем продаж: {sales_velocity} шт.\n"
            f"🏷️ ID для покупки: `{item.get('itemId', '')}`"
        )
    
    elif result_type == PriceAnomalyType.RARE_TRAITS:
        # Предмет с редкими характеристиками
        item = result.get("item", {})
        item_title = item.get("title", "Неизвестный предмет")
        current_price = result.get("current_price", 0.0)
        estimated_value = result.get("estimated_value", 0.0)
        price_difference_percent = result.get("price_difference_percent", 0.0)
        rare_traits = result.get("rare_traits", [])
        
        traits_text = "\n".join([f"  • {trait}" for trait in rare_traits])
        
        return (
            f"💎 *{item_title}*\n"
            f"💰 Текущая цена: ${current_price:.2f}\n"
            f"⭐ Оценочная стоимость: ${estimated_value:.2f} (+{price_difference_percent:.1f}%)\n"
            f"✨ Редкие особенности:\n{traits_text}\n"
            f"🏷️ ID для покупки: `{item.get('itemId', '')}`"
        )
    
    else:
        # Неизвестный тип
        return "❓ Неизвестный тип результата"

async def start_intramarket_arbitrage(
    update: Update,
    context: CallbackContext,
) -> None:
    """Обрабатывает команду запуска внутрирыночного арбитража."""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    
    # Отправляем сообщение о начале сканирования
    message = await context.bot.send_message(
        chat_id=user_id,
        text="🔍 *Поиск возможностей арбитража внутри DMarket*\n\nВыберите тип арбитража:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔄 Ценовые аномалии", 
                    callback_data=f"{INTRA_ARBITRAGE_ACTION}_{ANOMALY_ACTION}"
                )
            ],
            [
                InlineKeyboardButton(
                    "📈 Растущие в цене", 
                    callback_data=f"{INTRA_ARBITRAGE_ACTION}_{TRENDING_ACTION}"
                )
            ],
            [
                InlineKeyboardButton(
                    "💎 Редкие предметы", 
                    callback_data=f"{INTRA_ARBITRAGE_ACTION}_{RARE_ACTION}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Назад", 
                    callback_data="arbitrage_menu"
                )
            ]
        ])
    )

async def handle_intramarket_callback(
    update: Update,
    context: CallbackContext,
) -> None:
    """Обрабатывает callback-запросы для внутрирыночного арбитража."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    # Парсим данные callback
    data_parts = callback_data.split("_")
    if len(data_parts) < 2:
        await query.edit_message_text(
            "⚠️ Некорректные данные запроса.",
            parse_mode="Markdown"
        )
        return
    
    action_type = data_parts[1]
    game = "csgo"  # По умолчанию CS2
    
    # Если указана игра
    if len(data_parts) >= 3:
        game = data_parts[2]
    
    # Показываем сообщение о начале сканирования
    await query.edit_message_text(
        f"🔍 *Сканирование {GAMES.get(game, game)}*\n\n"
        f"Идет поиск выгодных предложений. Пожалуйста, подождите...",
        parse_mode="Markdown"
    )
    
    # Определяем тип сканирования и запускаем соответствующую функцию
    results = []
    
    try:
        if action_type == ANOMALY_ACTION:
            # Поиск ценовых аномалий
            anomalies = await find_price_anomalies(
                game=game,
                max_results=50,
            )
            results = anomalies
            title = f"🔍 Ценовые аномалии для {GAMES.get(game, game)}"
            
        elif action_type == TRENDING_ACTION:
            # Поиск предметов с растущей ценой
            trending = await find_trending_items(
                game=game,
                max_results=50,
            )
            results = trending
            title = f"📈 Растущие в цене {GAMES.get(game, game)}"
            
        elif action_type == RARE_ACTION:
            # Поиск редких предметов
            rare_items = await find_mispriced_rare_items(
                game=game,
                max_results=50,
            )
            results = rare_items
            title = f"💎 Редкие предметы {GAMES.get(game, game)}"
            
        else:
            # Неизвестный тип действия
            await query.edit_message_text(
                "⚠️ Неизвестный тип сканирования.",
                parse_mode="Markdown"
            )
            return
        
        # Если результаты не найдены
        if not results:
            await query.edit_message_text(
                f"ℹ️ *{title}*\n\n"
                f"Возможности не найдены. Попробуйте другой тип сканирования или игру.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "⬅️ Назад", 
                            callback_data=f"{INTRA_ARBITRAGE_ACTION}"
                        )
                    ]
                ])
            )
            return
        
        # Создаем пагинацию для результатов
        pagination_id = f"intra_{action_type}_{game}_{user_id}"
        pagination_manager.add_items(
            pagination_id, 
            results, 
            format_function=format_intramarket_result
        )
        
        # Форматируем первую страницу результатов
        paginated_text = await format_paginated_results(
            pagination_id,
            title,
            page=1
        )
        
        # Создаем клавиатуру для пагинации
        keyboard = [
            # Кнопки пагинации
            [
                InlineKeyboardButton("⬅️", callback_data=f"page_{pagination_id}_prev"),
                InlineKeyboardButton("1", callback_data=f"page_{pagination_id}_current"),
                InlineKeyboardButton("➡️", callback_data=f"page_{pagination_id}_next"),
            ],
            # Кнопки выбора игры
            [
                InlineKeyboardButton(
                    "CS2 🔫", 
                    callback_data=f"{INTRA_ARBITRAGE_ACTION}_{action_type}_csgo"
                ),
                InlineKeyboardButton(
                    "Dota 2 🧙", 
                    callback_data=f"{INTRA_ARBITRAGE_ACTION}_{action_type}_dota2"
                ),
            ],
            [
                InlineKeyboardButton(
                    "TF2 🎭", 
                    callback_data=f"{INTRA_ARBITRAGE_ACTION}_{action_type}_tf2"
                ),
                InlineKeyboardButton(
                    "Rust 🏕️", 
                    callback_data=f"{INTRA_ARBITRAGE_ACTION}_{action_type}_rust"
                ),
            ],
            # Кнопка возврата
            [
                InlineKeyboardButton(
                    "⬅️ Назад", 
                    callback_data=f"{INTRA_ARBITRAGE_ACTION}"
                )
            ]
        ]
        
        # Отправляем результаты
        await query.edit_message_text(
            paginated_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    except Exception as e:
        logger.error(f"Ошибка при сканировании внутрирыночного арбитража: {e}")
        await query.edit_message_text(
            f"⚠️ *Ошибка при сканировании*\n\n"
            f"Произошла ошибка: {str(e)}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⬅️ Назад", 
                        callback_data=f"{INTRA_ARBITRAGE_ACTION}"
                    )
                ]
            ])
        )

# Список обработчиков для регистрации
handlers = [
    CallbackQueryHandler(
        start_intramarket_arbitrage, 
        pattern=f"^{INTRA_ARBITRAGE_ACTION}$"
    ),
    CallbackQueryHandler(
        handle_intramarket_callback, 
        pattern=f"^{INTRA_ARBITRAGE_ACTION}_"
    ),
] 