"""Enhanced auto-arbitrage module with comprehensive scanning capabilities.

This module provides improved scanning of the DMarket platform for arbitrage
opportunities with better pagination, rate limiting, and progress tracking.
"""

import asyncio
import logging
import os
from typing import Any, Callable, Dict, List, Optional

from src.dmarket.arbitrage import GAMES, ArbitrageTrader
from src.dmarket.dmarket_api import DMarketAPI
from src.utils.performance import cached, profile_performance
from src.utils.rate_limiter import RateLimiter

# Configure logging
logger = logging.getLogger(__name__)

# Create rate limiter instance
rate_limiter = RateLimiter(is_authorized=True)

# Default price ranges for different games (in USD)
DEFAULT_PRICE_RANGES = {
    "csgo": {"min": 1.0, "max": 500.0},
    "dota2": {"min": 0.5, "max": 200.0},
    "tf2": {"min": 0.5, "max": 150.0},
    "rust": {"min": 0.3, "max": 100.0},
}

# Default price chunks to split scanning into smaller ranges
DEFAULT_PRICE_CHUNKS = [
    (0.0, 1.0),     # $0 - $1
    (1.0, 5.0),     # $1 - $5
    (5.0, 10.0),    # $5 - $10
    (10.0, 20.0),   # $10 - $20
    (20.0, 50.0),   # $20 - $50
    (50.0, 100.0),  # $50 - $100
    (100.0, 200.0), # $100 - $200
    (200.0, 500.0), # $200 - $500
]


@cached("enhanced_arbitrage_scan", ttl=600)
async def scan_game_comprehensively(
    game: str,
    mode: str = "medium",
    max_items_per_range: int = 1000,
    price_ranges: Optional[List[tuple[float, float]]] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    dmarket_api: Optional[DMarketAPI] = None,
) -> List[Dict[str, Any]]:
    """Scan a game comprehensively using multiple price ranges to ensure complete coverage.
    
    Args:
        game: Game code (e.g. "csgo", "dota2", "rust", "tf2")
        mode: Search mode ("low", "medium", "high")
        max_items_per_range: Maximum number of items to fetch per price range
        price_ranges: List of price range tuples (min_price, max_price)
        progress_callback: Callback for reporting progress (items_fetched, total_items, status_message)
        dmarket_api: DMarket API instance or None to create a new one
        
    Returns:
        List of found items for arbitrage

    """
    try:
        # Create API instance if not provided
        if dmarket_api is None:
            public_key = os.environ.get("DMARKET_PUBLIC_KEY", "")
            secret_key = os.environ.get("DMARKET_SECRET_KEY", "")
            api_url = os.environ.get("DMARKET_API_URL", "https://api.dmarket.com")

            dmarket_api = DMarketAPI(
                public_key,
                secret_key,
                api_url,
                max_retries=3,
            )

        # Use default price ranges if not provided
        if price_ranges is None:
            # Use defaults for the given game or fall back to CS2 defaults
            game_defaults = DEFAULT_PRICE_RANGES.get(game, DEFAULT_PRICE_RANGES["csgo"])

            # Use price chunks within the game's min/max range
            price_ranges = []
            for chunk_min, chunk_max in DEFAULT_PRICE_CHUNKS:
                if chunk_max >= game_defaults["min"] and chunk_min <= game_defaults["max"]:
                    # Adjust chunk to be within game min/max
                    adjusted_min = max(chunk_min, game_defaults["min"])
                    adjusted_max = min(chunk_max, game_defaults["max"])
                    price_ranges.append((adjusted_min, adjusted_max))

        # Create ArbitrageTrader for finding profitable items
        trader = ArbitrageTrader()

        # Define profit ranges based on mode
        min_profit_percent = 5.0
        max_profit_percent = 15.0

        if mode == "low":
            min_profit_percent = 3.0
            max_profit_percent = 10.0
        elif mode == "high":
            min_profit_percent = 15.0
            max_profit_percent = 50.0

        # Create async tasks for parallel processing
        # We'll use gather instead of AsyncBatch since we had issues with its implementation

        # Store all results
        all_results = []
        total_items_scanned = 0
        total_items_found = 0

        # Process each price range in parallel
        async def process_price_range(price_from, price_to):
            nonlocal total_items_scanned, total_items_found

            logger.info(f"Scanning {game} in price range ${price_from:.2f}-${price_to:.2f}")

            if progress_callback:
                progress_callback(
                    total_items_found,
                    0,
                    f"Scanning {GAMES.get(game, game)} ${price_from:.2f}-${price_to:.2f}",
                )

            # Respect rate limiting
            await rate_limiter.wait_if_needed("market")

            # Find profitable items in this range
            items = await trader.find_profitable_items(
                game=game,
                min_profit_percentage=min_profit_percent,
                max_items=max_items_per_range,
                min_price=price_from,
                max_price=price_to,
            )

            # Update scan stats
            items_in_range = len(items)
            total_items_scanned += items_in_range
            total_items_found += items_in_range

            if progress_callback:
                progress_callback(
                    total_items_found,
                    0,
                    f"Found {items_in_range} items in range ${price_from:.2f}-${price_to:.2f}",
                )

            return items

        # Create tasks for each price range
        tasks = []
        for price_from, price_to in price_ranges:
            tasks.append(process_price_range(price_from, price_to))

        # Wait for all tasks to complete, limiting concurrency to 2 at a time
        # Process in batches of 2 to maintain rate limits
        price_range_results = []
        for i in range(0, len(tasks), 2):
            batch = tasks[i:i+2]
            batch_results = await asyncio.gather(*batch)
            price_range_results.extend(batch_results)
            # Small delay between batches
            if i + 2 < len(tasks):
                await asyncio.sleep(0.5)

        # Flatten results
        for items in price_range_results:
            all_results.extend(items)

        # Sort by profit percentage
        all_results.sort(key=lambda x: x.get("profit_percentage", 0), reverse=True)

        # Filter out duplicates by item ID
        unique_items = {}
        for item in all_results:
            item_id = item.get("itemId")
            if item_id and item_id not in unique_items:
                unique_items[item_id] = item

        # Convert back to list
        final_results = list(unique_items.values())

        logger.info(
            f"Comprehensive scan completed for {game}. "
            f"Found {len(final_results)} unique arbitrage opportunities.",
        )

        return final_results

    except Exception as e:
        logger.error(f"Error in comprehensive scan for {game}: {e}")
        if progress_callback:
            progress_callback(0, 0, f"Error: {e!s}")
        return []


@profile_performance
async def scan_multiple_games_enhanced(
    games: List[str] = ["csgo", "dota2", "rust", "tf2"],
    mode: str = "medium",
    max_items_per_game: int = 50,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Scan multiple games with enhanced comprehensive scanning.
    
    Args:
        games: List of game codes to scan
        mode: Search mode ("low", "medium", "high")
        max_items_per_game: Maximum items to return per game
        progress_callback: Callback for reporting progress
        
    Returns:
        Dictionary with game codes and lists of found items

    """
    results = {}

    # Create a single API instance for all requests
    dmarket_api = DMarketAPI(
        os.environ.get("DMARKET_PUBLIC_KEY", ""),
        os.environ.get("DMARKET_SECRET_KEY", ""),
        os.environ.get("DMARKET_API_URL", "https://api.dmarket.com"),
        max_retries=3,
    )

    # Process each game
    async def process_game(game):
        game_name = GAMES.get(game, game.upper())

        if progress_callback:
            progress_callback(0, 0, f"Starting scan for {game_name}")

        # Create progress callback for this game
        def game_progress(items_found, total_items, status):
            if progress_callback:
                progress_callback(
                    items_found,
                    total_items,
                    f"{game_name}: {status}",
                )

        # Scan the game comprehensively
        items = await scan_game_comprehensively(
            game=game,
            mode=mode,
            progress_callback=game_progress,
            dmarket_api=dmarket_api,
        )

        # Limit items per game
        return items[:max_items_per_game]

    # Process games sequentially to respect rate limits
    for game in games:
        results[game] = await process_game(game)

    return results


async def start_auto_arbitrage_enhanced(
    games: List[str] = ["csgo"],
    mode: str = "medium",
    max_items: int = 20,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> List[Dict[str, Any]]:
    """Start enhanced auto-arbitrage scanning for specified games.
    
    Args:
        games: List of game codes to scan
        mode: Search mode ("low", "medium", "high")
        max_items: Maximum items to return in total
        progress_callback: Callback for reporting progress
        
    Returns:
        Combined list of arbitrage opportunities

    """
    if progress_callback:
        progress_callback(0, 0, f"Starting enhanced auto-arbitrage for {len(games)} games")

    # Scan all games
    results_by_game = await scan_multiple_games_enhanced(
        games=games,
        mode=mode,
        max_items_per_game=max_items,
        progress_callback=progress_callback,
    )

    # Combine and sort all results
    all_results = []
    for game, items in results_by_game.items():
        all_results.extend(items)

    # Sort by profit percentage
    all_results.sort(key=lambda x: x.get("profit_percentage", 0), reverse=True)

    # Limit to max_items
    final_results = all_results[:max_items]

    if progress_callback:
        progress_callback(
            len(final_results),
            len(all_results),
            f"Found {len(final_results)} arbitrage opportunities",
        )

    return final_results
