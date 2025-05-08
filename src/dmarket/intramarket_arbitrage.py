"""
Advanced intramarket arbitrage module for DMarket.

This module provides methods for finding arbitrage opportunities within DMarket itself:
- Price anomaly detection 
- Trend analysis for profitable items
- Pattern recognition for market fluctuations
- Detection of mispriced rare items
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta

# DMarket API
from src.dmarket.dmarket_api import DMarketAPI

# Logger
logger = logging.getLogger(__name__)

# Cache for search results to minimize API calls
_cache = {}
_cache_ttl = 300  # Cache TTL in seconds (5 min)

async def find_price_anomalies(
    game: str,
    similarity_threshold: float = 0.85,
    price_diff_percent: float = 10.0,
    max_results: int = 20,
    min_price: float = 1.0,
    max_price: float = 100.0,
    dmarket_api: Optional[DMarketAPI] = None
) -> List[Dict[str, Any]]:
    """
    Finds price anomalies within DMarket for the same or highly similar items.
    
    Args:
        game: Game code (csgo, dota2, tf2, rust)
        similarity_threshold: Threshold for item similarity (0-1)
        price_diff_percent: Minimum price difference percentage for arbitrage
        max_results: Maximum number of results to return
        min_price: Minimum item price to consider
        max_price: Maximum item price to consider
        dmarket_api: DMarket API instance or None to create a new one
        
    Returns:
        List of price anomaly opportunities
    """
    logger.info(f"Searching for price anomalies in {game} (min diff: {price_diff_percent}%)")
    
    # Check if we need to create a new API client
    close_api = False
    if dmarket_api is None:
        from src.telegram_bot.auto_arbitrage import create_dmarket_api_client
        from telegram.ext import CallbackContext
        dmarket_api = await create_dmarket_api_client(CallbackContext())
        close_api = True
    
    try:
        # Get market items
        items_response = await dmarket_api.get_market_items(
            game=game,
            limit=200,
            offset=0,
            price_from=min_price,
            price_to=max_price,
            sort="price"
        )
        
        items = items_response.get("items", [])
        if not items:
            logger.warning(f"No items found for {game}")
            return []
            
        # Group items by title/name for comparison
        grouped_items = {}
        
        for item in items:
            title = item.get("title", "")
            if not title:
                continue
                
            # Skip unwanted items (stickers, etc. for CS2)
            if game == "csgo" and any(x in title.lower() for x in ["sticker", "graffiti", "patch"]):
                continue
                
            # Extract key attributes for comparison
            key_parts = []
            
            # Title base (remove wear/exterior from CS:GO items if present)
            if game == "csgo" and " | " in title and " (" in title:
                base_title = title.split(" (")[0]
                key_parts.append(base_title)
                
                # Add exterior as separate part
                exterior = title.split("(")[-1].split(")")[0] if "(" in title else ""
                if exterior:
                    key_parts.append(exterior)
            else:
                key_parts.append(title)
                
            # Extract other attributes for grouping
            if game == "csgo":
                # Check if StatTrak or Souvenir
                is_stattrak = "StatTrak™" in title
                is_souvenir = "Souvenir" in title
                if is_stattrak:
                    key_parts.append("StatTrak")
                if is_souvenir:
                    key_parts.append("Souvenir")
                    
            # Create a composite key 
            composite_key = "|".join(key_parts)
            
            if composite_key not in grouped_items:
                grouped_items[composite_key] = []
                
            # Add price info
            price = None
            if "price" in item:
                if isinstance(item["price"], dict) and "amount" in item["price"]:
                    price = int(item["price"]["amount"]) / 100  # Convert from cents to USD
                elif isinstance(item["price"], (int, float)):
                    price = float(item["price"])
            
            if price is not None:
                grouped_items[composite_key].append({
                    "item": item,
                    "price": price
                })
        
        # Find anomalies within each group
        anomalies = []
        
        for key, items_list in grouped_items.items():
            # Skip if only one price point
            if len(items_list) < 2:
                continue
                
            # Sort by price
            items_list.sort(key=lambda x: x["price"])
            
            # Compare each item with others to find price differences
            for i in range(len(items_list)):
                low_item = items_list[i]
                
                for j in range(i+1, len(items_list)):
                    high_item = items_list[j]
                    
                    # Calculate price difference
                    price_diff = high_item["price"] - low_item["price"]
                    price_diff_pct = (price_diff / low_item["price"]) * 100
                    
                    # Apply minimum difference threshold
                    if price_diff_pct >= price_diff_percent:
                        # Calculate profit after fees
                        fee_percent = 7.0  # DMarket fee
                        profit_after_fee = high_item["price"] * (1 - fee_percent/100) - low_item["price"]
                        
                        # Only include if profitable after fees
                        if profit_after_fee > 0:
                            anomalies.append({
                                "game": game,
                                "item_to_buy": low_item["item"],
                                "item_to_sell": high_item["item"],
                                "buy_price": low_item["price"],
                                "sell_price": high_item["price"],
                                "price_difference": price_diff,
                                "profit_percentage": price_diff_pct,
                                "profit_after_fee": profit_after_fee,
                                "fee_percent": fee_percent,
                                "composite_key": key
                            })
        
        # Sort by profit percentage in descending order
        anomalies.sort(key=lambda x: x["profit_percentage"], reverse=True)
        
        # Return top results
        return anomalies[:max_results]
        
    except Exception as e:
        logger.error(f"Error in find_price_anomalies: {str(e)}")
        return []
    finally:
        if close_api and hasattr(dmarket_api, "_close_client"):
            await dmarket_api._close_client()

async def find_trending_items(
    game: str,
    min_price: float = 5.0,
    max_price: float = 500.0,
    max_results: int = 10,
    dmarket_api: Optional[DMarketAPI] = None
) -> List[Dict[str, Any]]:
    """
    Finds trending items with potential for price increase in near future.
    
    Args:
        game: Game code (csgo, dota2, tf2, rust)
        min_price: Minimum item price to consider
        max_price: Maximum item price to consider
        max_results: Maximum number of results to return
        dmarket_api: DMarket API instance
        
    Returns:
        List of trending items with potential profit
    """
    logger.info(f"Searching for trending items in {game}")
    
    # Check if we need to create API client
    close_api = False
    if dmarket_api is None:
        from src.telegram_bot.auto_arbitrage import create_dmarket_api_client
        from telegram.ext import CallbackContext
        dmarket_api = await create_dmarket_api_client(CallbackContext())
        close_api = True
    
    try:
        # Get recent sales history and popular items
        trending_items = []
        
        # Get recently sold items (high demand)
        recently_sold = await dmarket_api.get_sales_history(
            game=game,
            days=3,
            currency="USD"
        )
        
        # Get current market listings
        market_items = await dmarket_api.get_market_items(
            game=game,
            limit=300,
            price_from=min_price,
            price_to=max_price
        )
        
        if not market_items.get("items"):
            return []
        
        # Analyze market trends
        market_data = {}
        
        # Process market items
        for item in market_items.get("items", []):
            title = item.get("title", "")
            if not title:
                continue
                
            # Get price
            price = None
            if "price" in item:
                if isinstance(item["price"], dict) and "amount" in item["price"]:
                    price = int(item["price"]["amount"]) / 100
                elif isinstance(item["price"], (int, float)):
                    price = float(item["price"])
            
            if price is None or price < min_price or price > max_price:
                continue
                
            # Get recommended price if available
            suggested_price = 0
            if "suggestedPrice" in item:
                if isinstance(item["suggestedPrice"], dict) and "amount" in item["suggestedPrice"]:
                    suggested_price = int(item["suggestedPrice"]["amount"]) / 100
                elif isinstance(item["suggestedPrice"], (int, float)):
                    suggested_price = float(item["suggestedPrice"])
            
            # Check available quantity
            market_data[title] = {
                "item": item,
                "current_price": price,
                "suggested_price": suggested_price,
                "supply": 1,  # Start with 1, will increment if more found
                "game": game
            }
        
        # Combine data with sales history for trend analysis
        sales_data = recently_sold.get("items", [])
        for sale in sales_data:
            title = sale.get("title", "")
            if title in market_data:
                # Item exists in market data, update with sales info
                if "last_sold_price" not in market_data[title]:
                    # Get sale price
                    sale_price = None
                    if "price" in sale:
                        if isinstance(sale["price"], dict) and "amount" in sale["price"]:
                            sale_price = int(sale["price"]["amount"]) / 100
                        elif isinstance(sale["price"], (int, float)):
                            sale_price = float(sale["price"])
                    
                    if sale_price:
                        market_data[title]["last_sold_price"] = sale_price
                
                # Increment sales count
                market_data[title]["sales_count"] = market_data[title].get("sales_count", 0) + 1
        
        # Analyze for trends
        for title, data in market_data.items():
            # Skip items with insufficient data
            if "last_sold_price" not in data:
                continue
                
            current_price = data["current_price"]
            last_sold_price = data["last_sold_price"]
            sales_count = data.get("sales_count", 0)
            
            # Calculate metrics
            price_change = ((current_price - last_sold_price) / last_sold_price) * 100
            
            # Project future price based on trends
            projected_price = current_price
            
            # Upward trend - selling higher than last sold prices
            if price_change > 5 and sales_count >= 2:
                # Projecting further upward movement
                projected_price = current_price * 1.1  # Project 10% increase
                potential_profit = projected_price - current_price
                potential_profit_percent = (potential_profit / current_price) * 100
                
                # If profitable, add to trending list
                if potential_profit > 0.5:  # At least $0.50 potential profit
                    trending_items.append({
                        "item": data["item"],
                        "current_price": current_price,
                        "last_sold_price": last_sold_price,
                        "price_change_percent": price_change,
                        "projected_price": projected_price,
                        "potential_profit": potential_profit,
                        "potential_profit_percent": potential_profit_percent,
                        "sales_count": sales_count,
                        "game": game,
                        "trend": "upward"
                    })
            
            # Downward trend but with recovery potential
            elif price_change < -15 and sales_count >= 3:
                # Items that recently crashed hard might bounce back
                projected_price = last_sold_price * 0.9  # Project recovery to 90% of last sold
                potential_profit = projected_price - current_price
                potential_profit_percent = (potential_profit / current_price) * 100
                
                if potential_profit > 1.0:  # At least $1.00 potential profit
                    trending_items.append({
                        "item": data["item"],
                        "current_price": current_price,
                        "last_sold_price": last_sold_price,
                        "price_change_percent": price_change,
                        "projected_price": projected_price,
                        "potential_profit": potential_profit,
                        "potential_profit_percent": potential_profit_percent,
                        "sales_count": sales_count,
                        "game": game,
                        "trend": "recovery"
                    })
        
        # Sort by potential profit percentage
        trending_items.sort(key=lambda x: x["potential_profit_percent"], reverse=True)
        
        return trending_items[:max_results]
        
    except Exception as e:
        logger.error(f"Error in find_trending_items: {str(e)}")
        return []
    finally:
        if close_api and hasattr(dmarket_api, "_close_client"):
            await dmarket_api._close_client()

async def find_mispriced_rare_items(
    game: str, 
    min_price: float = 10.0,
    max_price: float = 1000.0,
    max_results: int = 5,
    dmarket_api: Optional[DMarketAPI] = None
) -> List[Dict[str, Any]]:
    """
    Finds rare items that appear to be mispriced compared to their usual value.
    
    Args:
        game: Game code (csgo, dota2, tf2, rust)
        min_price: Minimum item price to consider
        max_price: Maximum item price to consider
        max_results: Maximum number of results to return
        dmarket_api: DMarket API instance
        
    Returns:
        List of mispriced rare items
    """
    logger.info(f"Searching for mispriced rare items in {game}")
    
    # Check if we need to create API client
    close_api = False
    if dmarket_api is None:
        from src.telegram_bot.auto_arbitrage import create_dmarket_api_client
        from telegram.ext import CallbackContext
        dmarket_api = await create_dmarket_api_client(CallbackContext())
        close_api = True
    
    try:
        # Define traits that make items rare per game
        rare_traits = {
            "csgo": {
                "Knife": 100,  # Weight for rarity value
                "Gloves": 90,
                "Covert": 70,
                "StatTrak™": 50,
                "Souvenir": 60,
                "Factory New": 40,
                "Case Hardened": 50,
                "Fade": 60,
                "Doppler": 60,
                "Crimson Web": 50,
                "★": 100,  # Star symbol for knives
            },
            "dota2": {
                "Arcana": 100,
                "Immortal": 80,
                "Unusual": 90,
                "Inscribed": 30,
                "Genuine": 40,
                "Corrupted": 60,
                "Exalted": 50,
                "Autographed": 40,
            },
            "tf2": {
                "Unusual": 100,
                "Vintage": 50,
                "Genuine": 40,
                "Strange": 30,
                "Haunted": 60,
                "Australium": 80,
                "Collector's": 70,
            },
            "rust": {
                "Glowing": 70,
                "Limited": 80,
                "Unique": 50,
                "Complete Set": 60,
            }
        }
        
        # Get market items with higher limit for rare items search
        items_response = await dmarket_api.get_market_items(
            game=game,
            limit=500,
            offset=0,
            price_from=min_price,
            price_to=max_price
        )
        
        items = items_response.get("items", [])
        if not items:
            return []
        
        # Analyze items for rare traits
        scored_items = []
        
        for item in items:
            title = item.get("title", "")
            if not title:
                continue
                
            # Get price
            price = None
            if "price" in item:
                if isinstance(item["price"], dict) and "amount" in item["price"]:
                    price = int(item["price"]["amount"]) / 100
                elif isinstance(item["price"], (int, float)):
                    price = float(item["price"])
            
            if price is None or price < min_price or price > max_price:
                continue
            
            # Score item rarity based on traits
            rarity_score = 0
            detected_traits = []
            
            # Check title for rare traits
            for trait, weight in rare_traits.get(game, {}).items():
                if trait in title:
                    rarity_score += weight
                    detected_traits.append(trait)
            
            # Add other factors like float value for CS:GO
            if game == "csgo" and "float" in item:
                float_value = float(item.get("float", 1.0))
                if float_value < 0.01:  # Extremely low float
                    rarity_score += 70
                    detected_traits.append(f"Float: {float_value:.4f}")
                elif float_value < 0.07:  # Very low float
                    rarity_score += 40
                    detected_traits.append(f"Float: {float_value:.4f}")
            
            # Only consider items with some rarity
            if rarity_score > 30:
                # Check against average price or suggested price
                suggested_price = 0
                if "suggestedPrice" in item:
                    if isinstance(item["suggestedPrice"], dict) and "amount" in item["suggestedPrice"]:
                        suggested_price = int(item["suggestedPrice"]["amount"]) / 100
                    elif isinstance(item["suggestedPrice"], (int, float)):
                        suggested_price = float(item["suggestedPrice"])
                
                # If no suggested price, estimate based on rarity score
                if suggested_price == 0:
                    # Simple model: higher rarity should command higher price
                    suggested_price = price * (1 + (rarity_score / 200))
                
                # Calculate estimated value based on rarity
                estimated_value = max(suggested_price, price * (1 + (rarity_score / 300)))
                
                # Calculate price difference
                price_difference = estimated_value - price
                price_difference_percent = (price_difference / price) * 100
                
                # If item appears undervalued, add to results
                if price_difference > 2.0 and price_difference_percent > 10:
                    scored_items.append({
                        "item": item,
                        "rarity_score": rarity_score,
                        "rare_traits": detected_traits,
                        "current_price": price,
                        "estimated_value": estimated_value,
                        "price_difference": price_difference,
                        "price_difference_percent": price_difference_percent,
                        "game": game
                    })
        
        # Sort by price difference percentage
        scored_items.sort(key=lambda x: x["price_difference_percent"], reverse=True)
        
        return scored_items[:max_results]
        
    except Exception as e:
        logger.error(f"Error in find_mispriced_rare_items: {str(e)}")
        return []
    finally:
        if close_api and hasattr(dmarket_api, "_close_client"):
            await dmarket_api._close_client()

async def scan_for_intramarket_opportunities(
    games: List[str] = ["csgo", "dota2", "tf2", "rust"],
    max_results_per_game: int = 10,
    min_price: float = 1.0,
    max_price: float = 500.0,
    include_anomalies: bool = True,
    include_trending: bool = True,
    include_rare: bool = True,
    dmarket_api: Optional[DMarketAPI] = None
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Comprehensive scan for all types of intramarket opportunities.
    
    Args:
        games: List of game codes to scan
        max_results_per_game: Maximum results per game and category
        min_price: Minimum item price
        max_price: Maximum item price
        include_anomalies: Include price anomalies in results
        include_trending: Include trending items in results
        include_rare: Include mispriced rare items in results
        dmarket_api: DMarket API instance
        
    Returns:
        Dictionary with game codes as keys and dictionaries of opportunity types as values
    """
    logger.info(f"Starting comprehensive intramarket scan for {len(games)} games")
    
    # Check if we need to create API client
    close_api = False
    if dmarket_api is None:
        from src.telegram_bot.auto_arbitrage import create_dmarket_api_client
        from telegram.ext import CallbackContext
        dmarket_api = await create_dmarket_api_client(CallbackContext())
        close_api = True
    
    try:
        results = {}
        tasks = []
        
        # Create tasks for all requested opportunity types and games
        for game in games:
            results[game] = {}
            
            if include_anomalies:
                tasks.append(("anomalies", game, find_price_anomalies(
                    game=game,
                    similarity_threshold=0.9,
                    price_diff_percent=10.0,
                    max_results=max_results_per_game,
                    min_price=min_price,
                    max_price=max_price,
                    dmarket_api=dmarket_api
                )))
            
            if include_trending:
                tasks.append(("trending", game, find_trending_items(
                    game=game,
                    min_price=min_price,
                    max_price=max_price,
                    max_results=max_results_per_game,
                    dmarket_api=dmarket_api
                )))
            
            if include_rare:
                tasks.append(("rare", game, find_mispriced_rare_items(
                    game=game,
                    min_price=min_price,
                    max_price=max_price,
                    max_results=max_results_per_game,
                    dmarket_api=dmarket_api
                )))
        
        # Run all tasks concurrently
        for category, game, task_coroutine in tasks:
            try:
                result = await task_coroutine
                
                # Store results by category
                if category == "anomalies":
                    results[game]["price_anomalies"] = result
                elif category == "trending":
                    results[game]["trending_items"] = result
                elif category == "rare":
                    results[game]["rare_mispriced"] = result
                
                logger.info(f"Found {len(result)} {category} for {game}")
                
            except Exception as e:
                logger.error(f"Error in {category} scan for {game}: {str(e)}")
                if category == "anomalies":
                    results[game]["price_anomalies"] = []
                elif category == "trending":
                    results[game]["trending_items"] = []
                elif category == "rare":
                    results[game]["rare_mispriced"] = []
        
        return results
        
    except Exception as e:
        logger.error(f"Error in scan_for_intramarket_opportunities: {str(e)}")
        return {game: {"price_anomalies": [], "trending_items": [], "rare_mispriced": []} for game in games}
    finally:
        if close_api and hasattr(dmarket_api, "_close_client"):
            await dmarket_api._close_client() 