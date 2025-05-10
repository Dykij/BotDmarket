#!/usr/bin/env python3
"""This script shows DMarket API usage examples.
"""

import asyncio
import json
import os
import sys

# Add the src directory to the path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from dmarket.dmarket_api import DMarketAPI

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Get API keys from environment variables
PUBLIC_KEY = os.environ.get("DMARKET_PUBLIC_KEY", "")
SECRET_KEY = os.environ.get("DMARKET_SECRET_KEY", "")

if not PUBLIC_KEY or not SECRET_KEY:
    print("Error: DMARKET_PUBLIC_KEY and DMARKET_SECRET_KEY must be set in .env file")
    sys.exit(1)


async def main():
    """Run DMarket API examples."""
    # Create API client
    api = DMarketAPI(PUBLIC_KEY, SECRET_KEY)

    # Get user balance
    print("Getting user balance...")
    balance = await api.get_user_balance()
    print(f"Balance: {json.dumps(balance, indent=2)}")

    # Get market items for CS:GO
    print("\nGetting CS:GO market items...")
    items = await api.get_market_items(game="csgo", limit=5)
    print(f"Found {len(items.get('objects', []))} items")
    print(f"Items: {json.dumps(items.get('objects', [])[:2], indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
