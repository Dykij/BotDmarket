"""Enhanced notification system for DMarket trading opportunities.

This module provides sophisticated, context-aware notifications for:
- Smart market opportunity alerts based on analysis
- Personalized notifications based on user preferences
- Multi-channel delivery (Telegram, email, etc.)
- Smart notification scheduling and throttling
- Advanced market condition triggers
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from src.dmarket.dmarket_api import DMarketAPI
from src.telegram_bot.utils.formatters import (
    format_market_item,
    format_opportunities,
    split_long_message,
)
from src.utils.market_analyzer import (
    TREND_DOWN,
    TREND_UP,
    MarketAnalyzer,
    analyze_market_opportunity,
)

# Logger
logger = logging.getLogger(__name__)

# Notification types
NOTIFICATION_TYPES = {
    "market_opportunity": "Market Opportunity",
    "price_alert": "Price Alert",
    "trend_alert": "Trend Alert",
    "pattern_alert": "Pattern Alert",
    "watchlist_update": "Watchlist Update",
    "arbitrage_opportunity": "Arbitrage Opportunity",
    "system_alert": "System Alert",
}

# Notification storage file
DATA_DIR = Path("data") / "notifications"
SMART_ALERTS_FILE = DATA_DIR / "smart_alerts.json"

# In-memory storage
_user_preferences = {}
_active_alerts = {}
_notification_history = {}

# Alert cooldown periods (seconds)
DEFAULT_COOLDOWN = {
    "market_opportunity": 3600,  # 1 hour
    "price_alert": 1800,  # 30 minutes
    "trend_alert": 7200,  # 2 hours
    "pattern_alert": 3600,  # 1 hour
    "watchlist_update": 14400,  # 4 hours
    "arbitrage_opportunity": 900,  # 15 minutes
    "system_alert": 300,  # 5 minutes
}

# Initialize data directory
if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_user_preferences() -> None:
    """Load user notification preferences from storage."""
    global _user_preferences

    try:
        if SMART_ALERTS_FILE.exists():
            with open(SMART_ALERTS_FILE) as f:
                data = json.load(f)
                _user_preferences = data.get("user_preferences", {})
                _active_alerts = data.get("active_alerts", {})
                logger.info(
                    f"Loaded preferences for {len(_user_preferences)} users and {len(_active_alerts)} alerts"
                )
    except Exception as e:
        logger.error(f"Error loading user preferences: {e}")
        _user_preferences = {}
        _active_alerts = {}


def save_user_preferences() -> None:
    """Save user notification preferences to storage."""
    try:
        with open(SMART_ALERTS_FILE, "w") as f:
            json.dump(
                {
                    "user_preferences": _user_preferences,
                    "active_alerts": _active_alerts,
                    "updated_at": datetime.now().timestamp(),
                },
                f,
                indent=2,
            )
        logger.debug("User preferences saved successfully")
    except Exception as e:
        logger.error(f"Error saving user preferences: {e}")


async def register_user(user_id: int, chat_id: int | None = None) -> None:
    """Register a user for notifications with default settings.

    Args:
        user_id: Telegram user ID
        chat_id: Optional chat ID (defaults to user_id)

    """
    user_id_str = str(user_id)
    chat_id = chat_id if chat_id is not None else user_id

    if user_id_str not in _user_preferences:
        _user_preferences[user_id_str] = {
            "chat_id": chat_id,
            "enabled": True,
            "channels": ["telegram"],
            "frequency": "normal",  # low, normal, high
            "quiet_hours": {"start": 23, "end": 8},
            "min_opportunity_score": 60,  # Minimum opportunity score to notify
            "notifications": {
                "market_opportunity": True,
                "price_alert": True,
                "trend_alert": True,
                "pattern_alert": True,
                "watchlist_update": True,
                "arbitrage_opportunity": True,
                "system_alert": True,
            },
            "games": {
                "csgo": True,
                "dota2": True,
                "tf2": True,
                "rust": True,
            },
            "preferences": {
                "min_price": 1.0,
                "max_price": 1000.0,
                "min_profit": 5.0,  # Minimum profit percentage
                "notification_style": "detailed",  # detailed or compact
            },
            "last_notification": {},
            "registered_at": datetime.now().timestamp(),
        }

        save_user_preferences()
        logger.info(f"User {user_id} registered for notifications")


async def update_user_preferences(
    user_id: int,
    preferences: dict[str, Any],
) -> None:
    """Update a user's notification preferences.

    Args:
        user_id: Telegram user ID
        preferences: Dictionary of preference updates

    """
    user_id_str = str(user_id)

    # Register if not already registered
    if user_id_str not in _user_preferences:
        await register_user(user_id)

    # Update preferences
    for key, value in preferences.items():
        if key in _user_preferences[user_id_str]:
            if isinstance(_user_preferences[user_id_str][key], dict) and isinstance(value, dict):
                # Merge dictionaries for nested settings
                _user_preferences[user_id_str][key].update(value)
            else:
                # Direct assignment for simple values
                _user_preferences[user_id_str][key] = value

    save_user_preferences()
    logger.debug(f"Updated preferences for user {user_id}")


async def create_alert(
    user_id: int,
    alert_type: str,
    item_id: str | None = None,
    item_name: str | None = None,
    game: str = "csgo",
    conditions: dict[str, Any] | None = None,
    one_time: bool = False,
) -> str:
    """Create a new alert for a user.

    Args:
        user_id: Telegram user ID
        alert_type: Type of alert (price_alert, trend_alert, etc.)
        item_id: Optional DMarket item ID
        item_name: Optional item name
        game: Game code (csgo, dota2, tf2, rust)
        conditions: Dictionary of alert conditions
        one_time: Whether the alert should trigger only once

    Returns:
        Alert ID

    """
    user_id_str = str(user_id)

    # Register if not already registered
    if user_id_str not in _user_preferences:
        await register_user(user_id)

    # Generate alert ID
    import uuid

    alert_id = str(uuid.uuid4())

    # Create alert data
    alert_data = {
        "id": alert_id,
        "user_id": user_id_str,
        "type": alert_type,
        "item_id": item_id,
        "item_name": item_name,
        "game": game,
        "conditions": conditions or {},
        "one_time": one_time,
        "created_at": datetime.now().timestamp(),
        "last_triggered": None,
        "trigger_count": 0,
        "active": True,
    }

    # Add to active alerts
    if user_id_str not in _active_alerts:
        _active_alerts[user_id_str] = []

    _active_alerts[user_id_str].append(alert_data)

    save_user_preferences()
    logger.info(
        f"Created {alert_type} alert for user {user_id} on {item_name or 'market conditions'}"
    )

    return alert_id


async def deactivate_alert(user_id: int, alert_id: str) -> bool:
    """Deactivate an alert for a user.

    Args:
        user_id: Telegram user ID
        alert_id: Alert ID to deactivate

    Returns:
        True if successful, False otherwise

    """
    user_id_str = str(user_id)

    if user_id_str not in _active_alerts:
        return False

    for alert in _active_alerts[user_id_str]:
        if alert["id"] == alert_id:
            alert["active"] = False
            save_user_preferences()
            logger.debug(f"Deactivated alert {alert_id} for user {user_id}")
            return True

    return False


async def get_user_alerts(user_id: int) -> list[dict[str, Any]]:
    """Get a user's active alerts.

    Args:
        user_id: Telegram user ID

    Returns:
        List of active alerts

    """
    user_id_str = str(user_id)

    if user_id_str not in _active_alerts:
        return []

    return [alert for alert in _active_alerts[user_id_str] if alert["active"]]


async def check_price_alerts(api: DMarketAPI, bot: Bot) -> None:
    """Check price alerts for all users and send notifications.

    Args:
        api: DMarketAPI instance
        bot: Telegram Bot instance

    """
    for user_id_str, alerts in _active_alerts.items():
        # Skip if no active alerts
        active_alerts = [a for a in alerts if a["active"] and a["type"] == "price_alert"]
        if not active_alerts:
            continue

        # Get user preferences
        user_prefs = _user_preferences.get(user_id_str, {})
        if not user_prefs.get("enabled", True):
            continue

        try:
            # Group alerts by game to minimize API calls
            game_alerts = {}
            for alert in active_alerts:
                game = alert.get("game", "csgo")
                if game not in game_alerts:
                    game_alerts[game] = []
                game_alerts[game].append(alert)

            # Check alerts for each game
            for game, game_alerts_list in game_alerts.items():
                item_ids = [a["item_id"] for a in game_alerts_list if a["item_id"]]
                if not item_ids:
                    continue

                # Get current market data for items
                market_data = await get_market_data_for_items(api, item_ids, game)

                # Process each alert
                for alert in game_alerts_list:
                    item_id = alert.get("item_id")
                    if not item_id or item_id not in market_data:
                        continue

                    item_data = market_data[item_id]
                    current_price = get_item_price(item_data)

                    conditions = alert.get("conditions", {})
                    threshold = conditions.get("price", 0)
                    direction = conditions.get("direction", "below")

                    # Check if alert condition is met
                    alert_triggered = False
                    if (direction == "below" and current_price <= threshold) or (
                        direction == "above" and current_price >= threshold
                    ):
                        alert_triggered = True

                    if alert_triggered:
                        await send_price_alert_notification(
                            bot,
                            int(user_id_str),
                            alert,
                            item_data,
                            current_price,
                            user_prefs,
                        )

                        # Update alert data
                        alert["last_triggered"] = datetime.now().timestamp()
                        alert["trigger_count"] += 1

                        # Deactivate one-time alerts
                        if alert.get("one_time", False):
                            alert["active"] = False

        except Exception as e:
            logger.error(f"Error checking price alerts for user {user_id_str}: {e}")

    # Save changes
    save_user_preferences()


async def check_market_opportunities(api: DMarketAPI, bot: Bot) -> None:
    """Scan for market opportunities and send notifications to interested users.

    Args:
        api: DMarketAPI instance
        bot: Telegram Bot instance

    """
    # Get users interested in market opportunities
    interested_users = {
        user_id: prefs
        for user_id, prefs in _user_preferences.items()
        if prefs.get("enabled", True)
        and prefs.get("notifications", {}).get("market_opportunity", True)
    }

    if not interested_users:
        return

    try:
        # Scan for opportunities in each game
        for game in ["csgo", "dota2", "tf2", "rust"]:
            # Skip games that no users are interested in
            if not any(
                prefs.get("games", {}).get(game, False) for prefs in interested_users.values()
            ):
                continue

            # Get market data for analysis
            market_items = await get_market_items_for_game(api, game)

            if not market_items:
                logger.warning(f"No market items found for {game}")
                continue

            # Get price history for promising items
            items_to_analyze = market_items[:50]  # Limit to top 50 items for efficiency

            # Get price history for these items
            price_histories = await get_price_history_for_items(
                api, [item.get("itemId") for item in items_to_analyze], game
            )

            # Analyze for opportunities
            analyzer = MarketAnalyzer()
            opportunities = []

            for item in items_to_analyze:
                item_id = item.get("itemId")
                if not item_id or item_id not in price_histories:
                    continue

                try:
                    # Analyze the item
                    history = price_histories[item_id]
                    opportunity = await analyze_market_opportunity(item, history, game)

                    # Add to opportunities if score is high enough
                    if opportunity["opportunity_score"] >= 60:
                        opportunities.append(opportunity)
                except Exception as e:
                    logger.error(f"Error analyzing item {item_id}: {e}")

            # Sort opportunities by score
            opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)

            # Send notifications to interested users
            for user_id, prefs in interested_users.items():
                if not prefs.get("games", {}).get(game, False):
                    continue

                # Filter opportunities based on user preferences
                min_score = prefs.get("preferences", {}).get("min_opportunity_score", 60)
                min_price = prefs.get("preferences", {}).get("min_price", 1.0)
                max_price = prefs.get("preferences", {}).get("max_price", 1000.0)

                filtered_opportunities = [
                    opp
                    for opp in opportunities
                    if opp["opportunity_score"] >= min_score
                    and min_price <= opp["current_price"] <= max_price
                ]

                # Limit to top 3 opportunities per user per game
                top_opportunities = filtered_opportunities[:3]

                # Send notifications
                for opportunity in top_opportunities:
                    # Check cooldown
                    if await should_throttle_notification(
                        user_id,
                        "market_opportunity",
                        opportunity["item_id"],
                    ):
                        continue

                    await send_market_opportunity_notification(
                        bot,
                        int(user_id),
                        opportunity,
                        prefs,
                    )

    except Exception as e:
        logger.error(f"Error checking market opportunities: {e}")


async def should_throttle_notification(
    user_id: int,
    notification_type: str,
    item_id: str | None = None,
) -> bool:
    """Check if a notification should be throttled based on previous notifications.

    Args:
        user_id: Telegram user ID
        notification_type: Type of notification
        item_id: Optional item ID

    Returns:
        True if notification should be throttled, False otherwise

    """
    user_id_str = str(user_id)

    # Get user preferences
    prefs = _user_preferences.get(user_id_str, {})
    frequency = prefs.get("frequency", "normal")

    # Get history key
    history_key = f"{notification_type}:{item_id}" if item_id else notification_type

    # Get cooldown period based on frequency
    base_cooldown = DEFAULT_COOLDOWN.get(notification_type, 3600)

    if frequency == "low":
        cooldown = base_cooldown * 2
    elif frequency == "high":
        cooldown = base_cooldown / 2
    else:  # normal
        cooldown = base_cooldown

    # Check quiet hours
    now = datetime.now()
    quiet_hours = prefs.get("quiet_hours", {"start": 23, "end": 8})

    if quiet_hours["start"] <= now.hour < quiet_hours["end"]:
        return True  # Don't notify during quiet hours

    # Check last notification time
    last_notifications = prefs.get("last_notification", {})
    last_time = last_notifications.get(history_key, 0)

    if time.time() - last_time < cooldown:
        return True  # Throttle notification

    return False


async def record_notification(
    user_id: int,
    notification_type: str,
    item_id: str | None = None,
) -> None:
    """Record that a notification was sent to a user.

    Args:
        user_id: Telegram user ID
        notification_type: Type of notification
        item_id: Optional item ID

    """
    user_id_str = str(user_id)

    if user_id_str not in _user_preferences:
        return

    # Get history key
    history_key = f"{notification_type}:{item_id}" if item_id else notification_type

    # Update last notification time
    if "last_notification" not in _user_preferences[user_id_str]:
        _user_preferences[user_id_str]["last_notification"] = {}

    _user_preferences[user_id_str]["last_notification"][history_key] = time.time()

    # Save changes
    save_user_preferences()


async def send_price_alert_notification(
    bot: Bot,
    user_id: int,
    alert: dict[str, Any],
    item_data: dict[str, Any],
    current_price: float,
    user_prefs: dict[str, Any],
) -> None:
    """Send a price alert notification to a user.

    Args:
        bot: Telegram bot instance
        user_id: User ID to notify
        alert: Alert data
        item_data: Item data from DMarket
        current_price: Current price of the item
        user_prefs: User preferences

    """
    try:
        chat_id = user_prefs.get("chat_id", user_id)
        notification_style = user_prefs.get("preferences", {}).get("notification_style", "detailed")
        
        # Get alert conditions
        conditions = alert.get("conditions", {})
        target_price = conditions.get("price", 0)
        condition = conditions.get("condition", "below")
        
        # Format item details using the formatter
        item_formatted = format_market_item(item_data, show_details=True)
        
        # Build the notification text
        title = f"💰 <b>Уведомление о цене: {alert.get('item_name', 'Предмет')}</b>"
        alert_details = ""
        
        if condition == "below":
            alert_details = f"📉 Цена упала до <b>${current_price:.2f}</b> (ниже ${target_price:.2f})"
        elif condition == "above":
            alert_details = f"📈 Цена поднялась до <b>${current_price:.2f}</b> (выше ${target_price:.2f})"
        else:
            alert_details = f"🔄 Текущая цена: <b>${current_price:.2f}</b> (целевая: ${target_price:.2f})"
        
        # Create the message
        message = f"{title}\n\n{alert_details}\n\n{item_formatted}"
        
        # Add action buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    "🛒 Купить", 
                    url=f"https://dmarket.com/ingame-items/item-list/{alert.get('game', 'csgo')}-skins?userOfferId={item_data.get('itemId', '')}"
                ),
                InlineKeyboardButton(
                    "🔕 Удалить оповещение", 
                    callback_data=f"alert_delete:{alert.get('id', '')}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📊 Аналитика цен", 
                    callback_data=f"price_analytics:{item_data.get('itemId', '')}"
                ),
                InlineKeyboardButton(
                    "⏰ Новое оповещение", 
                    callback_data=f"alert_create:{item_data.get('itemId', '')}"
                ),
            ],
        ]
        
        markup = InlineKeyboardMarkup(keyboard)
        
        # Ensure message isn't too long
        if len(message) > 4000:
            message = message[:3900] + "...\n\n(Сообщение было сокращено)"
        
        # Send the notification
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
            disable_web_page_preview=False,
        )
        
        logger.info(f"Sent price alert notification to user {user_id} for {alert.get('item_name')}")
        
        # Update notification history
        await record_notification(user_id, "price_alert", alert.get("item_id"))
        
        # Update alert if one-time
        if alert.get("one_time", False):
            # Mark as inactive
            alert["active"] = False
            save_user_preferences()
    
    except Exception as e:
        logger.error(f"Error sending price alert notification: {e}")


async def send_market_opportunity_notification(
    bot: Bot,
    user_id: int,
    opportunity: dict[str, Any],
    user_prefs: dict[str, Any],
) -> None:
    """Send a market opportunity notification to a user.

    Args:
        bot: Telegram bot instance
        user_id: User ID to notify
        opportunity: Market opportunity data
        user_prefs: User preferences

    """
    try:
        chat_id = user_prefs.get("chat_id", user_id)
        notification_style = user_prefs.get("preferences", {}).get("notification_style", "detailed")
        
        # Extract opportunity details
        item_name = opportunity.get("item_name", "Unknown Item")
        game = opportunity.get("game", "csgo")
        score = opportunity.get("opportunity_score", 0)
        buy_price = opportunity.get("buy_price", 0)
        potential_profit = opportunity.get("potential_profit", 0)
        profit_percent = opportunity.get("profit_percent", 0)
        trend = opportunity.get("trend", "stable")
        
        # Format opportunity as an arbitrage opportunity for proper formatting
        formatted_opportunities = [
            {
                "item_name": item_name,
                "buy_price": buy_price,
                "sell_price": buy_price + potential_profit,
                "profit": potential_profit,
                "profit_percent": profit_percent,
                "game": game,
                "buy_item_id": opportunity.get("item_id", ""),
                "timestamp": datetime.now().isoformat(),
            }
        ]
        
        # Use the standardized formatter for opportunities
        if notification_style == "compact":
            # For compact style, use a simplified notification
            title = f"🔍 <b>Рыночная возможность</b>"
            
            if score >= 80:
                title = f"🔥 <b>ГОРЯЧАЯ ВОЗМОЖНОСТЬ!</b>"
            elif score >= 60:
                title = f"⭐ <b>Хорошая возможность</b>"
                
            message = (
                f"{title}\n\n"
                f"<b>{item_name}</b>\n"
                f"💲 Цена: <b>${buy_price:.2f}</b>\n"
                f"📈 Потенциальная прибыль: <b>${potential_profit:.2f}</b> ({profit_percent:.1f}%)\n"
                f"📊 Рейтинг: <b>{score}/100</b>\n\n"
                f"🕒 <i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>"
            )
        else:
            # For detailed style, use the standard formatter
            formatted_text = format_opportunities(formatted_opportunities, 0, 1)
            
            # Add a custom header
            header = (
                f"🔍 <b>Рыночная возможность обнаружена</b>\n\n"
                f"📊 Рейтинг: <b>{score}/100</b>\n"
                f"📈 Тренд: <b>{trend.upper()}</b>\n\n"
            )
            
            message = header + formatted_text
        
        # Add action buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    "🛒 Купить", 
                    url=f"https://dmarket.com/ingame-items/item-list/{game}-skins?userOfferId={opportunity.get('item_id', '')}"
                ),
                InlineKeyboardButton(
                    "📊 Подробный анализ", 
                    callback_data=f"analyze_opportunity:{opportunity.get('item_id', '')}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔔 Создать оповещение", 
                    callback_data=f"create_alert:{opportunity.get('item_id', '')}"
                ),
                InlineKeyboardButton(
                    "🚫 Отключить уведомления", 
                    callback_data="disable_notifications"
                ),
            ],
        ]
        
        markup = InlineKeyboardMarkup(keyboard)
        
        # Split message if needed
        messages = split_long_message(message)
        
        # Send the notification(s)
        for i, msg_part in enumerate(messages):
            # Send markup only with the last part
            await bot.send_message(
                chat_id=chat_id,
                text=msg_part,
                parse_mode=ParseMode.HTML,
                reply_markup=markup if i == len(messages) - 1 else None,
                disable_web_page_preview=True,
            )
        
        logger.info(f"Sent market opportunity notification to user {user_id} for {item_name}")
        
        # Update notification history
        await record_notification(user_id, "market_opportunity", opportunity.get("item_id"))
    
    except Exception as e:
        logger.error(f"Error sending market opportunity notification: {e}")


async def handle_notification_callback(update: Update, context: CallbackContext) -> None:
    """Handle callback queries from notification buttons.

    Args:
        update: Update object
        context: CallbackContext object

    """
    query = update.callback_query
    await query.answer()

    if query.data.startswith("disable_alert:"):
        alert_id = query.data.split(":", 1)[1]
        success = await deactivate_alert(query.from_user.id, alert_id)

        if success:
            await query.edit_message_text(
                text=f"{query.message.text}\n\n✅ Alert has been disabled.",
                reply_markup=None,
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await query.edit_message_reply_markup(reply_markup=None)

    elif query.data.startswith("track_item:"):
        parts = query.data.split(":", 2)
        item_id = parts[1]
        game = parts[2] if len(parts) > 2 else "csgo"

        # Create price alert for the item
        api = context.bot_data.get("dmarket_api")

        if not api:
            await query.edit_message_text(
                text=f"{query.message.text}\n\n❌ Could not create alert: API not available.",
                reply_markup=None,
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        try:
            # Get current item data
            item_data = await get_item_by_id(api, item_id, game)

            if not item_data:
                await query.edit_message_text(
                    text=f"{query.message.text}\n\n❌ Could not create alert: Item not found.",
                    reply_markup=None,
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

            item_name = item_data.get("title", "Unknown item")
            current_price = get_item_price(item_data)

            # Create price alerts for both directions
            below_alert_id = await create_alert(
                query.from_user.id,
                "price_alert",
                item_id=item_id,
                item_name=item_name,
                game=game,
                conditions={
                    "price": current_price * 0.9,  # 10% below current price
                    "direction": "below",
                },
            )

            above_alert_id = await create_alert(
                query.from_user.id,
                "price_alert",
                item_id=item_id,
                item_name=item_name,
                game=game,
                conditions={
                    "price": current_price * 1.1,  # 10% above current price
                    "direction": "above",
                },
            )

            # Update message
            keyboard = [
                [
                    InlineKeyboardButton(
                        "View on DMarket",
                        url=f"https://dmarket.com/ingame-items/{game}/skin/{item_id}",
                    ),
                ],
                [
                    InlineKeyboardButton("View Alerts", callback_data="view_alerts"),
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=f"{query.message.text}\n\n✅ Alerts created for price changes on this item.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN,
            )

            logger.info(f"Created price alerts for user {query.from_user.id} on item {item_name}")

        except Exception as e:
            logger.error(
                f"Error creating alert for user {query.from_user.id} on item {item_id}: {e}"
            )

            await query.edit_message_text(
                text=f"{query.message.text}\n\n❌ Error creating alert: {e!s}",
                reply_markup=None,
                parse_mode=ParseMode.MARKDOWN,
            )


async def get_market_data_for_items(
    api: DMarketAPI,
    item_ids: list[str],
    game: str,
) -> dict[str, dict[str, Any]]:
    """Get market data for multiple items from DMarket.

    Args:
        api: DMarketAPI instance
        item_ids: List of item IDs
        game: Game code

    Returns:
        Dictionary mapping item IDs to item data

    """
    result = {}

    try:
        # Get market items in batches
        batch_size = 50
        for i in range(0, len(item_ids), batch_size):
            batch_ids = item_ids[i : i + batch_size]

            # Construct query parameters
            params = {
                "itemId": batch_ids,
                "gameId": game,
                "currency": "USD",
            }

            # Make API request
            response = await api._request(
                "GET",
                "/exchange/v1/market/items",
                params=params,
            )

            items = response.get("items", [])

            # Index by item ID
            for item in items:
                item_id = item.get("itemId")
                if item_id:
                    result[item_id] = item

            # Small delay between batches
            if i + batch_size < len(item_ids):
                await asyncio.sleep(0.5)

    except Exception as e:
        logger.error(f"Error getting market data for items: {e}")

    return result


async def get_item_by_id(
    api: DMarketAPI,
    item_id: str,
    game: str,
) -> dict[str, Any] | None:
    """Get data for a single item by ID.

    Args:
        api: DMarketAPI instance
        item_id: Item ID
        game: Game code

    Returns:
        Item data or None if not found

    """
    try:
        # Construct query parameters
        params = {
            "itemId": [item_id],
            "gameId": game,
            "currency": "USD",
        }

        # Make API request
        response = await api._request(
            "GET",
            "/exchange/v1/market/items",
            params=params,
        )

        items = response.get("items", [])

        if items:
            return items[0]

    except Exception as e:
        logger.error(f"Error getting item {item_id}: {e}")

    return None


async def get_market_items_for_game(
    api: DMarketAPI,
    game: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get market items for a game.

    Args:
        api: DMarketAPI instance
        game: Game code
        limit: Maximum number of items to return

    Returns:
        List of market items

    """
    try:
        # Make API request
        response = await api._request(
            "GET",
            "/exchange/v1/market/items",
            params={
                "gameId": game,
                "limit": limit,
                "currency": "USD",
                "orderBy": "popular",
            },
        )

        return response.get("items", [])

    except Exception as e:
        logger.error(f"Error getting market items for game {game}: {e}")
        return []


async def get_price_history_for_items(
    api: DMarketAPI,
    item_ids: list[str],
    game: str,
) -> dict[str, list[dict[str, Any]]]:
    """Get price history for multiple items.

    Args:
        api: DMarketAPI instance
        item_ids: List of item IDs
        game: Game code

    Returns:
        Dictionary mapping item IDs to price history

    """
    result = {}

    try:
        # Get price history for each item
        for item_id in item_ids:
            # Make API request
            response = await api._request(
                "GET",
                "/exchange/v1/market/price-history",
                params={
                    "itemId": item_id,
                    "gameId": game,
                    "currency": "USD",
                    "period": "last_month",
                },
            )

            history = response.get("data", [])

            if history:
                result[item_id] = history

            # Small delay between requests
            await asyncio.sleep(0.2)

    except Exception as e:
        logger.error(f"Error getting price history for items: {e}")

    return result


def get_item_price(item_data: dict[str, Any]) -> float:
    """Extract price from item data.

    Args:
        item_data: Item data from DMarket

    Returns:
        Item price as float

    """
    if "price" in item_data:
        if isinstance(item_data["price"], dict) and "amount" in item_data["price"]:
            return float(item_data["price"]["amount"]) / 100
        if isinstance(item_data["price"], (int, float)):
            return float(item_data["price"])

    return 0.0


async def notify_user(
    bot: Bot,
    user_id: int,
    message: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    """Send a notification to a user.

    Args:
        bot: Telegram Bot instance
        user_id: Telegram user ID
        message: Message text
        reply_markup: Optional reply markup

    Returns:
        True if notification was sent successfully, False otherwise

    """
    try:
        await bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending notification to user {user_id}: {e}")
        return False


async def start_notification_checker(
    api: DMarketAPI,
    bot: Bot,
    interval: int = 300,
) -> None:
    """Start the notification checker loop.

    Args:
        api: DMarketAPI instance
        bot: Telegram Bot instance
        interval: Check interval in seconds

    """
    # Load user preferences
    load_user_preferences()

    while True:
        try:
            # Check price alerts
            await check_price_alerts(api, bot)

            # Check market opportunities
            await check_market_opportunities(api, bot)

            # Log progress
            logger.debug("Notification check complete")

        except Exception as e:
            logger.error(f"Error in notification checker: {e}")

        # Wait for next cycle
        await asyncio.sleep(interval)


def register_notification_handlers(application) -> None:
    """Register notification handlers with the application.

    Args:
        application: Application instance

    """
    from telegram.ext import CallbackQueryHandler

    # Register smart notification callback handler
    application.add_handler(
        CallbackQueryHandler(
            handle_notification_callback,
            pattern=r"^(disable_alert:|track_item:)",
        )
    )

    # Start notification checker
    api = application.bot_data.get("dmarket_api")
    if api:
        asyncio.create_task(start_notification_checker(api, application.bot, interval=300))
        logger.info("Started notification checker")
    else:
        logger.error("Could not start notification checker: DMarketAPI not found in bot_data")
