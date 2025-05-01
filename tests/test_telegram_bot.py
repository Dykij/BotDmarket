"""
Test module for Telegram Bot.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the bot module to test
from src.telegram_bot.bot import dmarket_status, help_command, start


@pytest.fixture
def mock_update():
    """Create a mock Update object."""
    update = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_start_command(mock_update):
    """Test the start command."""
    context = MagicMock()

    # Call the start function
    await start(mock_update, context)

    # Check that reply_text was called once
    mock_update.message.reply_text.assert_called_once()

    # Check the content of the message
    args, kwargs = mock_update.message.reply_text.call_args
    assert "Hello!" in args[0]
    assert "help" in args[0].lower()


@pytest.mark.asyncio
async def test_help_command(mock_update):
    """Test the help command."""
    context = MagicMock()

    # Call the help function
    await help_command(mock_update, context)

    # Check that reply_text was called once
    mock_update.message.reply_text.assert_called_once()

    # Check the content of the message
    args, kwargs = mock_update.message.reply_text.call_args
    assert "commands" in args[0].lower()
    assert "/start" in args[0]
    assert "/help" in args[0]
    assert "/dmarket" in args[0]


@pytest.mark.asyncio
async def test_dmarket_status_with_keys(mock_update):
    """Test the dmarket_status command when keys are configured."""
    context = MagicMock()

    # Patch environment variables
    with patch.dict(os.environ, {
        "DMARKET_PUBLIC_KEY": "test_key",
        "DMARKET_SECRET_KEY": "test_secret"
    }):
        # Patch the imported constant in the module
        with patch("src.telegram_bot.bot.DMARKET_PUBLIC_KEY", "test_key"), \
             patch("src.telegram_bot.bot.DMARKET_SECRET_KEY", "test_secret"):

            # Call the dmarket_status function
            await dmarket_status(mock_update, context)

            # Check that reply_text was called once
            mock_update.message.reply_text.assert_called_once()

            # Check the content of the message
            args, kwargs = mock_update.message.reply_text.call_args
            assert "configured" in args[0].lower()
            assert "API endpoint" in args[0]


@pytest.mark.asyncio
async def test_dmarket_status_without_keys(mock_update):
    """Test the dmarket_status command when keys are not configured."""
    context = MagicMock()

    # Patch the imported constant in the module
    with patch("src.telegram_bot.bot.DMARKET_PUBLIC_KEY", ""), \
         patch("src.telegram_bot.bot.DMARKET_SECRET_KEY", ""):

        # Call the dmarket_status function
        await dmarket_status(mock_update, context)

        # Check that reply_text was called once
        mock_update.message.reply_text.assert_called_once()

        # Check the content of the message
        args, kwargs = mock_update.message.reply_text.call_args
        assert "not configured" in args[0].lower()
        assert ".env file" in args[0]
