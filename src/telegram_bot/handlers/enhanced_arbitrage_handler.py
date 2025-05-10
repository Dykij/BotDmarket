"""Handler for enhanced auto-arbitrage functionality with comprehensive scanning."""

import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from src.dmarket.arbitrage import GAMES
from src.telegram_bot.enhanced_auto_arbitrage import start_auto_arbitrage_enhanced
from src.telegram_bot.keyboards import get_arbitrage_keyboard, create_pagination_keyboard
from src.telegram_bot.pagination import pagination_manager
from src.telegram_bot.utils.formatters import format_opportunities

# Configure logging
logger = logging.getLogger(__name__)

# Track running scans to prevent duplicates
active_scans = {}


async def handle_enhanced_arbitrage_command(update: Update, context: CallbackContext) -> None:
    """Handle the /enhanced_arbitrage command to start comprehensive scanning."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if scan already running for this user
    if active_scans.get(user_id):
        await update.message.reply_text(
            "Enhanced scan is already running. Please wait for it to complete.",
        )
        return

    # Mark this user as having an active scan
    active_scans[user_id] = True

    # Initial message with game selection keyboard
    keyboard = []

    # Add game buttons
    game_row = []
    for game_code, game_name in GAMES.items():
        game_row.append(
            InlineKeyboardButton(
                game_name,
                callback_data=f"enhanced_scan:{game_code}",
            ),
        )
        # Create new row after every 2 games
        if len(game_row) == 2:
            keyboard.append(game_row)
            game_row = []

    # Add any remaining games
    if game_row:
        keyboard.append(game_row)

    # Add mode selection buttons
    keyboard.append(
        [
            InlineKeyboardButton("🟢 Low Risk", callback_data="enhanced_mode:low"),
            InlineKeyboardButton("🟡 Medium Risk", callback_data="enhanced_mode:medium"),
        ]
    )
    keyboard.append(
        [
            InlineKeyboardButton("🔴 High Risk", callback_data="enhanced_mode:high"),
        ]
    )

    # Add scan button
    keyboard.append(
        [
            InlineKeyboardButton("🔍 Start Enhanced Scan", callback_data="enhanced_start"),
        ]
    )

    # Send the message
    await update.message.reply_text(
        text="🚀 *Enhanced Auto-Arbitrage*\n\n"
        "Select the games you want to scan and the risk level, "
        "then press Start Enhanced Scan.\n\n"
        "💡 *Note:* Enhanced scanning performs comprehensive market analysis "
        "with improved rate limiting and pagination.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

    # Initialize context
    if not context.user_data.get("enhanced_arbitrage"):
        context.user_data["enhanced_arbitrage"] = {
            "games": ["csgo"],  # Default to CS2
            "mode": "medium",  # Default to medium risk
            "status": "configuring",
        }

    # Reset active scan flag
    active_scans[user_id] = False


async def handle_enhanced_arbitrage_callback(update: Update, context: CallbackContext) -> None:
    """Handle callback queries for enhanced auto-arbitrage."""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    await query.answer()

    # Initialize user data if not exists
    if not context.user_data.get("enhanced_arbitrage"):
        context.user_data["enhanced_arbitrage"] = {
            "games": ["csgo"],  # Default to CS2
            "mode": "medium",  # Default to medium risk
            "status": "configuring",
        }

    # Extract command and parameter
    parts = data.split(":")
    command = parts[0]
    param = parts[1] if len(parts) > 1 else None

    # Handle game selection
    if command == "enhanced_scan":
        game = param

        # Toggle game selection
        enhanced_data = context.user_data["enhanced_arbitrage"]
        if game in enhanced_data["games"]:
            enhanced_data["games"].remove(game)
        else:
            enhanced_data["games"].append(game)

        # Update the keyboard to reflect selection
        await update_enhanced_arbitrage_keyboard(query, context)

    # Handle mode selection
    elif command == "enhanced_mode":
        mode = param
        context.user_data["enhanced_arbitrage"]["mode"] = mode

        # Update the keyboard to reflect selection
        await update_enhanced_arbitrage_keyboard(query, context)

    # Start the scan
    elif command == "enhanced_start":
        # Check if already running
        if active_scans.get(user_id):
            await query.edit_message_text(
                "Enhanced scan is already running. Please wait for it to complete.",
            )
            return

        # Mark as active
        active_scans[user_id] = True

        # Get scan parameters
        enhanced_data = context.user_data["enhanced_arbitrage"]
        games = enhanced_data["games"]
        mode = enhanced_data["mode"]

        # Check if at least one game is selected
        if not games:
            await query.edit_message_text(
                "Please select at least one game to scan.",
            )
            active_scans[user_id] = False
            return

        # Update status
        enhanced_data["status"] = "scanning"

        # Show scanning message
        await query.edit_message_text(
            f"🔍 Starting enhanced scan for {len(games)} games with {mode} risk...\n\n"
            f"This may take a few minutes. Please be patient.",
        )

        try:
            # Create progress tracking function
            async def report_progress(items_found, total_items, status_message):
                try:
                    # Only update every 3 seconds to avoid flood limits
                    current_time = asyncio.get_event_loop().time()
                    last_update = enhanced_data.get("last_update", 0)

                    if current_time - last_update > 3:
                        enhanced_data["last_update"] = current_time

                        progress_text = (
                            f"🔍 Enhanced scan in progress...\n\n"
                            f"Items found: {items_found}\n"
                            f"Status: {status_message}\n\n"
                            f"⏳ Please wait, this may take a few minutes."
                        )

                        await query.edit_message_text(progress_text)
                except Exception as e:
                    logger.error(f"Error updating progress: {e}")

            # Execute the scan
            async def execute_scan():
                try:
                    results = await start_auto_arbitrage_enhanced(
                        games=games,
                        mode=mode,
                        max_items=50,
                        progress_callback=report_progress,
                    )
                    return results
                except Exception as e:
                    logger.error(f"Error in enhanced scan: {e}")
                    return []

            # Run the scan with a timeout (15 minutes max)
            results = await asyncio.wait_for(
                execute_scan(),
                timeout=900,  # 15 minutes
            )

            # Store results for pagination
            if results:
                # Используем унифицированный менеджер пагинации
                pagination_manager.add_items_for_user(user_id, results, f"enhanced_{mode}")
                items, current_page, total_pages = pagination_manager.get_page(user_id)

                # Форматируем результаты, используя унифицированный форматтер
                formatted_text = format_opportunities(
                    items, 
                    current_page, 
                    pagination_manager.get_items_per_page(user_id)
                )

                # Создаем клавиатуру пагинации, используя унифицированную функцию
                pagination_keyboard = create_pagination_keyboard(
                    current_page=current_page,
                    total_pages=total_pages,
                    prefix=f"enhanced_{mode}_",
                    with_nums=True,
                    back_button=True,
                    back_text="« Back to Arbitrage",
                    back_callback="arbitrage"
                )

                # Отображаем результаты с унифицированной клавиатурой
                await query.edit_message_text(
                    text=f"🔍 *Enhanced Arbitrage Results*\n\n{formatted_text}",
                    reply_markup=pagination_keyboard,
                    parse_mode="Markdown",
                )
            else:
                await query.edit_message_text(
                    "No arbitrage opportunities found. Try adjusting your scan parameters.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Try Again", callback_data="enhanced_arbitrage")],
                        [InlineKeyboardButton("« Back to Arbitrage", callback_data="arbitrage")],
                    ]),
                )

        except asyncio.TimeoutError:
            await query.edit_message_text(
                "⚠️ Enhanced scan timed out. Please try again with fewer games or a different mode.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Try Again", callback_data="enhanced_arbitrage")],
                    [InlineKeyboardButton("« Back to Arbitrage", callback_data="arbitrage")],
                ]),
            )
        except Exception as e:
            logger.error(f"Error in enhanced arbitrage scan: {e}")
            await query.edit_message_text(
                f"❌ Error during enhanced scan: {str(e)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Try Again", callback_data="enhanced_arbitrage")],
                    [InlineKeyboardButton("« Back to Arbitrage", callback_data="arbitrage")],
                ]),
            )
        finally:
            active_scans[user_id] = False
            enhanced_data["status"] = "completed"

    # Handle pagination for enhanced arbitrage results
    elif command == "paginate":
        direction = param
        mode = parts[2] if len(parts) > 2 else "enhanced"

        # Navigate to requested page
        if direction == "next":
            pagination_manager.next_page(user_id)
        elif direction == "prev":
            pagination_manager.prev_page(user_id)

        # Get current page data
        items, current_page, total_pages = pagination_manager.get_page(user_id)

        # Format using the unified formatter
        formatted_text = format_opportunities(
            items,
            current_page,
            pagination_manager.get_items_per_page(user_id)
        )

        # Create pagination keyboard using the unified function
        pagination_keyboard = create_pagination_keyboard(
            current_page=current_page,
            total_pages=total_pages,
            prefix=f"paginate:",
            with_nums=True,
            back_button=True,
            back_text="« Back to Arbitrage",
            back_callback="arbitrage"
        )

        # Display results
        await query.edit_message_text(
            text=f"🔍 *Enhanced Arbitrage Results*\n\n{formatted_text}",
            reply_markup=pagination_keyboard,
            parse_mode="Markdown",
        )


async def update_enhanced_arbitrage_keyboard(query, context: CallbackContext) -> None:
    """Update the enhanced arbitrage keyboard to reflect current selections."""
    # Get user's current selections
    enhanced_data = context.user_data.get("enhanced_arbitrage", {})
    selected_games = enhanced_data.get("games", ["csgo"])
    selected_mode = enhanced_data.get("mode", "medium")

    # Create updated keyboard
    keyboard = []

    # Add game buttons with selection indicators
    game_row = []
    for game_code, game_name in GAMES.items():
        # Add checkmark if game is selected
        button_text = f"✅ {game_name}" if game_code in selected_games else game_name
        game_row.append(
            InlineKeyboardButton(
                button_text,
                callback_data=f"enhanced_scan:{game_code}",
            ),
        )
        # Create new row after every 2 games
        if len(game_row) == 2:
            keyboard.append(game_row)
            game_row = []

    # Add any remaining games
    if game_row:
        keyboard.append(game_row)

    # Add mode selection buttons with indicators
    keyboard.append(
        [
            InlineKeyboardButton(
                f"{'✅ ' if selected_mode == 'low' else ''}🟢 Low Risk",
                callback_data="enhanced_mode:low",
            ),
            InlineKeyboardButton(
                f"{'✅ ' if selected_mode == 'medium' else ''}🟡 Medium Risk",
                callback_data="enhanced_mode:medium",
            ),
        ]
    )
    keyboard.append(
        [
            InlineKeyboardButton(
                f"{'✅ ' if selected_mode == 'high' else ''}🔴 High Risk",
                callback_data="enhanced_mode:high",
            ),
        ]
    )

    # Add scan button
    keyboard.append(
        [
            InlineKeyboardButton("🔍 Start Enhanced Scan", callback_data="enhanced_start"),
        ]
    )

    # Back button
    keyboard.append(
        [
            InlineKeyboardButton("« Back to Arbitrage", callback_data="arbitrage"),
        ]
    )

    # Update the message with the new keyboard
    await query.edit_message_text(
        text="🚀 *Enhanced Auto-Arbitrage*\n\n"
        f"Selected games: {', '.join(GAMES.get(g, g) for g in selected_games)}\n"
        f"Risk level: {selected_mode.capitalize()}\n\n"
        "Select the games you want to scan and the risk level, "
        "then press Start Enhanced Scan.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


def register_enhanced_arbitrage_handlers(dispatcher):
    """Register handlers for enhanced arbitrage functionality."""
    dispatcher.add_handler(CommandHandler("enhanced_arbitrage", handle_enhanced_arbitrage_command))
    dispatcher.add_handler(
        CallbackQueryHandler(handle_enhanced_arbitrage_callback, pattern="^enhanced_")
    )
    # We now use the unified pagination handlers, so no need to register a separate one here

