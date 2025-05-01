
"""
This script starts the DMarket Telegram Bot.
"""

import os
import sys

# Add the src directory to the path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from telegram_bot.bot_v2 import main

if __name__ == "__main__":
    main()
