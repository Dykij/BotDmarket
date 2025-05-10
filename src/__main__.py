"""Main entry point for the DMarket bot application.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def run_bot():
    """Runs the bot with error handling"""
    try:
        # Import the main bot function
        from telegram_bot.bot_v2 import main

        # Start the bot
        logger.info("Starting Telegram bot...")
        await main()

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        # Pause before retry
        logger.info("Pausing 10 seconds before retry...")
        await asyncio.sleep(10)

        # Restart bot
        logger.info("Restarting bot...")
        await run_bot()


def main():
    """Main entry point function"""
    # Run the bot using asyncio
    try:
        # Check for lock file
        lock_file = Path("bot.lock")
        if lock_file.exists():
            try:
                # Read PID from lock file
                with open(lock_file) as f:
                    pid = int(f.read().strip())

                # Check if process with PID exists
                import psutil

                if psutil.pid_exists(pid):
                    logger.warning(f"Bot already running with PID {pid}. Exiting.")
                    sys.exit(1)
                else:
                    logger.warning("Invalid lock file detected. Overwriting.")
            except Exception as e:
                logger.error(f"Error reading lock file: {e}")

        # Create lock file with current PID
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))

        # Register handler to remove lock file on exit
        import atexit

        def cleanup():
            if lock_file.exists():
                lock_file.unlink()

        atexit.register(cleanup)

        # Start the bot
        asyncio.run(run_bot())

    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        # Remove lock file on exit
        if lock_file.exists():
            lock_file.unlink()


if __name__ == "__main__":
    main()
