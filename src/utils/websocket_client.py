"""WebSocket client module for DMarket API.

Provides a client for real-time updates from DMarket WebSocket API.
Based on DMarket API documentation at https://docs.dmarket.com/v1/swagger.html
"""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

import aiohttp
from aiohttp import ClientSession

from src.dmarket.dmarket_api import DMarketAPI

logger = logging.getLogger(__name__)


class DMarketWebSocketClient:
    """WebSocket client for DMarket API."""

    # WebSocket endpoint
    WS_ENDPOINT = "wss://ws.dmarket.com"

    def __init__(self, api_client: DMarketAPI):
        """Initialize WebSocket client.

        Args:
            api_client: DMarket API client for authentication

        """
        self.api_client = api_client
        self.session: ClientSession | None = None
        self.ws_connection = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10

        # Message handlers by event type
        self.handlers = {}

        # Authenticated state
        self.authenticated = False

        # Subscriptions
        self.subscriptions = set()

        # Connection ID for tracking
        self.connection_id = str(uuid.uuid4())

    async def connect(self) -> bool:
        """Connect to DMarket WebSocket API.

        Returns:
            bool: True if connection was successful

        """
        if self.is_connected:
            logger.info("WebSocket already connected")
            return True

        logger.info(f"Connecting to DMarket WebSocket ({self.WS_ENDPOINT})...")

        try:
            # Create new session if needed
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession()

            # Connect to WebSocket
            self.ws_connection = await self.session.ws_connect(
                self.WS_ENDPOINT,
                timeout=30.0,
                heartbeat=30.0,
            )

            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("Connected to DMarket WebSocket API")

            # Authenticate if needed
            if self.api_client.public_key and self.api_client.secret_key:
                await self._authenticate()

            # Resubscribe to previously active subscriptions
            await self._resubscribe()

            return True

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to connect to DMarket WebSocket: {e}")
            self.is_connected = False
            return False

    async def close(self) -> None:
        """Close WebSocket connection."""
        if self.ws_connection:
            logger.info("Closing WebSocket connection...")

            # Unsubscribe from everything before closing
            await self._unsubscribe_all()

            await self.ws_connection.close()
            self.ws_connection = None
            self.is_connected = False

            logger.info("WebSocket connection closed")

        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def listen(self) -> None:
        """Listen for WebSocket messages in a loop.

        This method should be run in a separate task.
        """
        while self.is_connected:
            try:
                message = await self.ws_connection.receive()

                if message.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(message.data)

                elif message.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("WebSocket connection closed by server")
                    self.is_connected = False
                    await self._attempt_reconnect()

                elif message.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket connection error: {message.data}")
                    self.is_connected = False
                    await self._attempt_reconnect()

            except (aiohttp.ClientError, asyncio.CancelledError) as e:
                if isinstance(e, asyncio.CancelledError):
                    # Task was cancelled, just exit
                    logger.info("WebSocket listen task cancelled")
                    break

                logger.error(f"WebSocket error: {e}")
                self.is_connected = False
                await self._attempt_reconnect()

    async def _attempt_reconnect(self) -> None:
        """Attempt to reconnect to WebSocket."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"Failed to reconnect after {self.reconnect_attempts} attempts, giving up")
            return

        self.reconnect_attempts += 1
        delay = min(2**self.reconnect_attempts, 60)  # Exponential backoff with 60s max

        logger.info(
            f"Attempting to reconnect in {delay} seconds (attempt {self.reconnect_attempts})"
        )
        await asyncio.sleep(delay)

        success = await self.connect()
        if not success:
            logger.warning(f"Reconnect attempt {self.reconnect_attempts} failed")

    async def _handle_message(self, data: str) -> None:
        """Handle incoming WebSocket message.

        Args:
            data: Raw message data

        """
        try:
            message = json.loads(data)

            # Handle authentication response
            if "type" in message and message["type"] == "auth":
                self._handle_auth_response(message)
                return

            # Handle subscription response
            if "type" in message and message["type"] == "subscription":
                logger.debug(f"Subscription response: {message}")
                return

            # Handle event message with handlers
            if "type" in message and message["type"] in self.handlers:
                event_type = message["type"]
                handlers = self.handlers.get(event_type, [])

                # Execute all handlers for this event type
                for handler in handlers:
                    try:
                        await handler(message)
                    except Exception as e:
                        logger.error(f"Error in event handler for {event_type}: {e}")

        except json.JSONDecodeError:
            logger.error(f"Failed to parse WebSocket message: {data}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    def _handle_auth_response(self, message: dict[str, Any]) -> None:
        """Handle authentication response.

        Args:
            message: Authentication response message

        """
        if message.get("status") == "success":
            self.authenticated = True
            logger.info("Successfully authenticated with DMarket WebSocket API")
        else:
            error = message.get("error", "Unknown error")
            self.authenticated = False
            logger.error(f"Authentication failed: {error}")

    async def _authenticate(self) -> None:
        """Authenticate with the WebSocket API using API keys."""
        if not self.ws_connection or not self.is_connected:
            logger.error("Cannot authenticate: WebSocket not connected")
            return

        if not self.api_client.public_key or not self.api_client.secret_key:
            logger.warning("Authentication skipped: No API keys provided")
            return

        # Construct authentication message according to DMarket API docs
        timestamp = str(int(time.time()))
        auth_message = {
            "type": "auth",
            "apiKey": self.api_client.public_key,
            "timestamp": timestamp,
        }

        # Send authentication message
        await self.ws_connection.send_json(auth_message)
        logger.debug("Sent authentication request")

    async def _resubscribe(self) -> None:
        """Resubscribe to previously active topics after reconnection."""
        if not self.subscriptions:
            return

        logger.info(f"Resubscribing to {len(self.subscriptions)} topics")

        for topic in self.subscriptions.copy():
            await self.subscribe(topic)

    async def _unsubscribe_all(self) -> None:
        """Unsubscribe from all active subscriptions."""
        if not self.subscriptions:
            return

        logger.info(f"Unsubscribing from {len(self.subscriptions)} topics")

        for topic in self.subscriptions.copy():
            await self.unsubscribe(topic)

    async def subscribe(self, topic: str, params: dict[str, Any] | None = None) -> bool:
        """Subscribe to a topic.

        Args:
            topic: Topic to subscribe to
            params: Additional parameters for subscription

        Returns:
            bool: True if subscription was successful

        """
        if not self.ws_connection or not self.is_connected:
            logger.error(f"Cannot subscribe to {topic}: WebSocket not connected")
            return False

        # Build subscription message
        subscription = {
            "type": "subscribe",
            "topic": topic,
        }

        if params:
            subscription["params"] = params

        # Send subscription request
        await self.ws_connection.send_json(subscription)
        logger.info(f"Subscribed to {topic}")

        # Add to active subscriptions
        self.subscriptions.add(topic)
        return True

    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from a topic.

        Args:
            topic: Topic to unsubscribe from

        Returns:
            bool: True if unsubscription was successful

        """
        if not self.ws_connection or not self.is_connected:
            logger.error(f"Cannot unsubscribe from {topic}: WebSocket not connected")
            return False

        # Build unsubscription message
        unsubscription = {
            "type": "unsubscribe",
            "topic": topic,
        }

        # Send unsubscription request
        await self.ws_connection.send_json(unsubscription)
        logger.info(f"Unsubscribed from {topic}")

        # Remove from active subscriptions
        if topic in self.subscriptions:
            self.subscriptions.remove(topic)

        return True

    def register_handler(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        """Register a handler for an event type.

        Args:
            event_type: Event type to handle
            handler: Handler function

        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []

        self.handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event type {event_type}")

    def unregister_handler(
        self, event_type: str, handler: Callable[[dict[str, Any]], None]
    ) -> None:
        """Unregister a handler for an event type.

        Args:
            event_type: Event type
            handler: Handler function

        """
        if event_type in self.handlers and handler in self.handlers[event_type]:
            self.handlers[event_type].remove(handler)
            logger.debug(f"Unregistered handler for event type {event_type}")

    async def send_message(self, message: dict[str, Any]) -> bool:
        """Send a custom message to the WebSocket.

        Args:
            message: Message to send

        Returns:
            bool: True if message was sent successfully

        """
        if not self.ws_connection or not self.is_connected:
            logger.error("Cannot send message: WebSocket not connected")
            return False

        await self.ws_connection.send_json(message)
        return True

    async def subscribe_to_market_updates(self, game: str = "csgo") -> bool:
        """Subscribe to market updates for a specific game.

        Args:
            game: Game ID (e.g., "csgo", "dota2")

        Returns:
            bool: True if subscription was successful

        """
        return await self.subscribe("market:update", {"gameId": game})

    async def subscribe_to_item_updates(self, item_ids: list[str]) -> bool:
        """Subscribe to updates for specific items.

        Args:
            item_ids: List of item IDs to track

        Returns:
            bool: True if subscription was successful

        """
        return await self.subscribe("items:update", {"itemIds": item_ids})
