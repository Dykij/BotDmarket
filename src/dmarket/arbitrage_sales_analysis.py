"""
Module for analyzing historical sales data for DMarket arbitrage.

This module provides tools for analyzing:
- Historical sales trends
- Price fluctuations
- Item sales volume
- Time-to-sell estimates for different items
- Profit potential based on historical data

Based on DMarket API documentation: https://docs.dmarket.com/v1/swagger.html
"""

import asyncio
import datetime
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from collections import defaultdict

import pandas as pd
import numpy as np

from src.dmarket.dmarket_api import DMarketAPI
from src.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class SalesAnalyzer:
    """Analyzer for historical sales data on DMarket."""

    def __init__(self, api_client: Optional[DMarketAPI] = None):
        """Initialize Sales Analyzer.

        Args:
            api_client: DMarket API client (optional)
        """
        self.api_client = api_client
        self._sales_cache = {}  # Cache for sales data
        self._cache_ttl = 3600  # Cache TTL (1 hour)
        self._rate_limiter = RateLimiter(is_authorized=True)
        
        # Safe defaults for volume analysis
        self.high_volume_threshold = 10  # Sales per day
        self.medium_volume_threshold = 5  # Sales per day
        self.min_sample_size = 3  # Minimum sales required for meaningful analysis

    async def get_api_client(self) -> DMarketAPI:
        """Get or create API client.

        Returns:
            DMarket API client
        """
        if not self.api_client:
            import os
            self.api_client = DMarketAPI(
                public_key=os.environ.get("DMARKET_PUBLIC_KEY", ""),
                secret_key=os.environ.get("DMARKET_SECRET_KEY", ""),
                api_url=os.environ.get("DMARKET_API_URL", "https://api.dmarket.com")
            )
        return self.api_client

    async def get_item_sales_history(
        self,
        item_name: str,
        game: str = "csgo",
        days: int = 30,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Get sales history for a specific item.

    Args:
            item_name: Item name
            game: Game name (csgo, dota2, etc.)
            days: Number of days to look back
            use_cache: Whether to use cached data

    Returns:
            List of sales data
        """
        cache_key = f"{game}:{item_name}:{days}"
        
        # Check cache first
        if use_cache and cache_key in self._sales_cache:
            cached_data, cache_time = self._sales_cache[cache_key]
            if time.time() - cache_time < self._cache_ttl:
                logger.debug(f"Using cached sales data for {item_name}")
                return cached_data
                
        # Get API client
        api_client = await self.get_api_client()
        
        try:
            # First we need to get the item ID for the given item name
            items_response = await api_client.get_market_items(
        game=game,
                title=item_name,
                limit=1
            )
            
            if "items" not in items_response or not items_response["items"]:
                logger.warning(f"Item not found: {item_name}")
                return []
                
            item_id = items_response["items"][0].get("itemId")
            if not item_id:
                logger.warning(f"Item ID not found for: {item_name}")
                return []
                
            # Calculate date range
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.datetime.timedelta(days=days)
            
            # Format dates for API
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            # Get sales history from API
            # Endpoint: /exchange/v1/sales/history (based on DMarket docs)
            sales_data = await api_client._request(
                method="GET",
                path="/exchange/v1/sales/history",
                params={
                    "gameId": game,
                    "itemId": item_id,
                    "from": start_date_str,
                    "to": end_date_str
                }
            )
            
            # Process sales data
            sales = []
            if "sales" in sales_data:
                sales = sales_data["sales"]
                
            # Cache the results
            self._sales_cache[cache_key] = (sales, time.time())
            
            return sales
            
        except Exception as e:
            logger.error(f"Error getting sales history for {item_name}: {e}")
            return []

    async def analyze_sales_volume(
        self,
        item_name: str,
        game: str = "csgo",
        days: int = 30
    ) -> Dict[str, Any]:
        """Analyze sales volume for an item.

        Args:
            item_name: Item name
            game: Game name
            days: Number of days to analyze
            
        Returns:
            Sales volume statistics
        """
        # Get sales history
        sales = await self.get_item_sales_history(item_name, game, days)
        
        if not sales:
            return {
                "sales_count": 0,
                "sales_per_day": 0,
                "volume_category": "unknown",
                "is_liquid": False
            }
            
        # Calculate sales per day
        sales_count = len(sales)
        sales_per_day = sales_count / min(days, 30)  # In case we have less data than requested
        
        # Categorize volume
        volume_category = "low"
        if sales_per_day >= self.high_volume_threshold:
            volume_category = "high"
        elif sales_per_day >= self.medium_volume_threshold:
            volume_category = "medium"
            
        # Determine if item is liquid (sells quickly)
        is_liquid = sales_per_day >= self.medium_volume_threshold
        
        return {
            "sales_count": sales_count,
            "sales_per_day": round(sales_per_day, 2),
            "volume_category": volume_category,
            "is_liquid": is_liquid
        }

    async def estimate_time_to_sell(
        self,
        item_name: str,
        target_price: float,
        game: str = "csgo",
        days: int = 30
    ) -> Dict[str, Any]:
        """Estimate time needed to sell an item at the target price.

        Args:
            item_name: Item name
            target_price: Target selling price
            game: Game name
            days: Number of days to analyze
            
        Returns:
            Time to sell estimation
        """
        # Get sales history
        sales = await self.get_item_sales_history(item_name, game, days)
        
        if not sales or len(sales) < self.min_sample_size:
            return {
                "estimated_days": None,
                "confidence": "very_low",
                "message": "Insufficient sales data for estimation"
            }
            
        # Convert sales data to pandas DataFrame for analysis
        try:
            sales_df = pd.DataFrame(sales)
            
            # Process timestamps and prices
            sales_df["timestamp"] = pd.to_datetime(sales_df["timestamp"])
            sales_df["price"] = sales_df["price"].apply(lambda x: float(x.get("USD", 0)) / 100)
            
            # Sort by price
            sales_df.sort_values("price", inplace=True)
            
            # Find percentage of sales at or above target price
            price_percentile = (sales_df["price"] >= target_price).mean()
            
            # Estimate time to sell based on volume and price percentile
            volume_stats = await self.analyze_sales_volume(item_name, game, days)
            sales_per_day = volume_stats["sales_per_day"]
            
            if sales_per_day == 0:
                estimated_days = None
                confidence = "very_low"
                message = "No recent sales data available"
            else:
                # Adjust days based on price percentile
                if price_percentile > 0:
                    # Higher percentile means longer time to sell
                    estimated_days = round(1 / (sales_per_day * price_percentile), 1)
                else:
                    # No sales at this price or higher
                    estimated_days = None
                    
                # Determine confidence level
                if len(sales) >= 20 and sales_per_day >= 1:
                    confidence = "high"
                elif len(sales) >= 10:
                    confidence = "medium"
                else:
                    confidence = "low"
                    
                if estimated_days is not None:
                    if estimated_days < 1:
                        message = f"Likely to sell within a day"
                    elif estimated_days < 3:
                        message = f"Likely to sell within {estimated_days} days"
                    elif estimated_days < 7:
                        message = f"May take about a week to sell"
                    else:
                        message = f"May take {int(estimated_days)} days or more to sell"
                else:
                    message = "Price may be too high based on historical data"
            
            return {
                "estimated_days": estimated_days,
                "confidence": confidence,
                "message": message,
                "price_percentile": round(price_percentile, 2),
                "sales_analyzed": len(sales)
            }
            
        except Exception as e:
            logger.error(f"Error estimating time to sell for {item_name}: {e}")
            return {
                "estimated_days": None,
                "confidence": "very_low",
                "message": f"Error analyzing sales data: {str(e)}"
            }

    async def analyze_price_trends(
        self,
        item_name: str,
    game: str = "csgo",
        days: int = 30
) -> Dict[str, Any]:
        """Analyze price trends for an item.

    Args:
            item_name: Item name
            game: Game name
            days: Number of days to analyze

    Returns:
            Price trend analysis
        """
        # Get sales history
        sales = await self.get_item_sales_history(item_name, game, days)
        
        if not sales or len(sales) < self.min_sample_size:
            return {
                "trend": "unknown",
                "price_change_percent": None,
                "volatility": None,
                "message": "Insufficient sales data for analysis"
            }
            
        # Convert sales data to pandas DataFrame for analysis
        try:
            sales_df = pd.DataFrame(sales)
            
            # Process timestamps and prices
            sales_df["timestamp"] = pd.to_datetime(sales_df["timestamp"])
            sales_df["price"] = sales_df["price"].apply(lambda x: float(x.get("USD", 0)) / 100)
            
            # Sort by timestamp
            sales_df.sort_values("timestamp", inplace=True)
            
            # Calculate daily averages
            sales_df["date"] = sales_df["timestamp"].dt.date
            daily_avg = sales_df.groupby("date")["price"].mean().reset_index()
            
            if len(daily_avg) < 2:
                return {
                    "trend": "stable",
                    "price_change_percent": 0,
                    "volatility": 0,
                    "message": "Insufficient data points for trend analysis"
                }
                
            # Calculate trend metrics
            first_price = daily_avg["price"].iloc[0]
            last_price = daily_avg["price"].iloc[-1]
            price_change = last_price - first_price
            price_change_percent = (price_change / first_price * 100) if first_price > 0 else 0
            
            # Calculate volatility (standard deviation as percentage of mean)
            mean_price = daily_avg["price"].mean()
            std_price = daily_avg["price"].std()
            volatility = (std_price / mean_price * 100) if mean_price > 0 else 0
            
            # Determine trend
            if abs(price_change_percent) < 5:
                trend = "stable"
                message = "Price has been relatively stable"
            elif price_change_percent >= 15:
                trend = "strong_upward"
                message = "Price is rising significantly"
            elif price_change_percent >= 5:
                trend = "upward"
                message = "Price has an upward trend"
            elif price_change_percent <= -15:
                trend = "strong_downward"
                message = "Price is falling significantly"
            elif price_change_percent <= -5:
                trend = "downward"
                message = "Price has a downward trend"
            else:
                trend = "slight_fluctuation"
                message = "Price shows slight fluctuations"
                
            # Adjust message based on volatility
            if volatility > 20:
                message += " with high volatility"
            elif volatility > 10:
                message += " with moderate volatility"
            
            return {
                "trend": trend,
                "price_change_percent": round(price_change_percent, 2),
                "price_change": round(price_change, 2),
                "volatility": round(volatility, 2),
                "first_price": round(first_price, 2),
                "last_price": round(last_price, 2),
                "min_price": round(daily_avg["price"].min(), 2),
                "max_price": round(daily_avg["price"].max(), 2),
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Error analyzing price trends for {item_name}: {e}")
            return {
                "trend": "unknown",
                "price_change_percent": None,
                "volatility": None,
                "message": f"Error analyzing price data: {str(e)}"
            }

    async def evaluate_arbitrage_potential(
        self,
        item_name: str,
        buy_price: float,
        sell_price: float,
        game: str = "csgo",
        days: int = 30
    ) -> Dict[str, Any]:
        """Evaluate arbitrage potential based on historical data.

        Args:
            item_name: Item name
            buy_price: Potential buying price
            sell_price: Potential selling price
            game: Game name
            days: Number of days to analyze
            
        Returns:
            Arbitrage potential evaluation
        """
        # Calculate raw profit
        raw_profit = sell_price - buy_price
        profit_percent = (raw_profit / buy_price * 100) if buy_price > 0 else 0
        
        # Get volume analysis
        volume_stats = await self.analyze_sales_volume(item_name, game, days)
        
        # Get time to sell estimation
        time_to_sell = await self.estimate_time_to_sell(item_name, sell_price, game, days)
        
        # Get price trend analysis
        price_trends = await self.analyze_price_trends(item_name, game, days)
        
        # Calculate risk level
        risk_level = "high"  # Default to high risk
        
        if volume_stats["is_liquid"] and time_to_sell["estimated_days"] is not None:
            if time_to_sell["estimated_days"] < 2 and price_trends["trend"] != "strong_downward":
                risk_level = "low"
            elif time_to_sell["estimated_days"] < 5 and price_trends["trend"] not in ["strong_downward", "downward"]:
                risk_level = "medium"
                
        # Calculate ROI (Return on Investment) taking into account time
        daily_roi = None
        if time_to_sell["estimated_days"] is not None and time_to_sell["estimated_days"] > 0:
            daily_roi = profit_percent / time_to_sell["estimated_days"]
            
        # Determine overall rating
        rating = 0  # 0-10 scale
        
        # Base rating on profit
        if profit_percent > 50:
            rating += 3
        elif profit_percent > 25:
            rating += 2
        elif profit_percent > 10:
            rating += 1
            
        # Adjust based on volume
        if volume_stats["volume_category"] == "high":
            rating += 3
        elif volume_stats["volume_category"] == "medium":
            rating += 2
        elif volume_stats["volume_category"] == "low":
            rating += 1
            
        # Adjust based on time to sell
        if time_to_sell["estimated_days"] is not None:
            if time_to_sell["estimated_days"] < 1:
                rating += 3
            elif time_to_sell["estimated_days"] < 3:
                rating += 2
            elif time_to_sell["estimated_days"] < 7:
                rating += 1
                
        # Adjust based on price trend
        if price_trends["trend"] in ["strong_upward", "upward"]:
            rating += 1
        elif price_trends["trend"] in ["strong_downward"]:
            rating -= 1
            
        # Cap rating at 0-10
        rating = max(0, min(10, rating))
        
        # Generate summary message
        if rating >= 8:
            summary = "Excellent arbitrage opportunity with high potential ROI and low risk"
        elif rating >= 6:
            summary = "Good arbitrage opportunity with solid potential returns"
        elif rating >= 4:
            summary = "Average opportunity with moderate risk and returns"
        elif rating >= 2:
            summary = "Below average opportunity with higher risk or lower returns"
        else:
            summary = "Poor arbitrage opportunity with high risk or minimal returns"
            
        return {
            "rating": rating,
            "raw_profit": round(raw_profit, 2),
            "profit_percent": round(profit_percent, 2),
            "risk_level": risk_level,
            "daily_roi": round(daily_roi, 2) if daily_roi is not None else None,
            "volume": volume_stats,
            "time_to_sell": time_to_sell,
            "price_trends": price_trends,
            "summary": summary
        }


async def batch_analyze_items(
    items: List[Dict[str, Any]],
    game: str = "csgo",
    days: int = 30
) -> Dict[str, Dict[str, Any]]:
    """Batch analyze multiple items for arbitrage potential.

    Args:
        items: List of items with name, buy_price, and sell_price
        game: Game name
        days: Number of days to analyze

    Returns:
        Dictionary of item names to analysis results
    """
    analyzer = SalesAnalyzer()
    results = {}
    
    for item in items:
        item_name = item.get("name", "")
        buy_price = item.get("buy_price", 0)
        sell_price = item.get("sell_price", 0)
        
        if not item_name or buy_price <= 0 or sell_price <= 0:
            continue
            
        try:
            analysis = await analyzer.evaluate_arbitrage_potential(
        item_name=item_name,
                buy_price=buy_price,
                sell_price=sell_price,
                game=game,
                days=days
            )
            
            results[item_name] = analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {item_name}: {e}")
            results[item_name] = {
                "error": str(e),
                "success": False
            }
    
    return results


async def find_best_arbitrage_opportunities(
    items: List[Dict[str, Any]],
    game: str = "csgo",
    min_rating: int = 6,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """Find the best arbitrage opportunities from a list of items.

    Args:
        items: List of items with name, buy_price, and sell_price
        game: Game name
        min_rating: Minimum arbitrage rating (0-10)
        max_results: Maximum number of results to return

    Returns:
        Sorted list of best opportunities
    """
    # Analyze all items
    results = await batch_analyze_items(items, game)
    
    # Filter and sort opportunities
    opportunities = []
    
    for item_name, analysis in results.items():
        if "rating" in analysis and analysis["rating"] >= min_rating:
            item_data = next((item for item in items if item.get("name") == item_name), {})
            
            opportunities.append({
                "name": item_name,
                "buy_price": item_data.get("buy_price", 0),
                "sell_price": item_data.get("sell_price", 0),
                "rating": analysis["rating"],
                "profit": analysis["raw_profit"],
                "profit_percent": analysis["profit_percent"],
                "risk_level": analysis["risk_level"],
                "estimated_days_to_sell": analysis["time_to_sell"]["estimated_days"],
                "volume_category": analysis["volume"]["volume_category"],
                "price_trend": analysis["price_trends"]["trend"],
                "summary": analysis["summary"]
            })
    
    # Sort by rating (descending)
    opportunities.sort(key=lambda x: x["rating"], reverse=True)
    
    # Limit results
    return opportunities[:max_results]
