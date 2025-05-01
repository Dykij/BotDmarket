"""
Main entry point for the DMarket Telegram Bot application.
"""

import os
import sys

# Add the parent directory to the path to find packages
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_bot.bot import main

if __name__ == "__main__":
    main()
