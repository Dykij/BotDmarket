"""
DMarket API client module for interacting with DMarket API.
"""

import hashlib
import hmac
import json
import time
from typing import Dict, Any, Optional
from urllib.parse import urlencode
import httpx


class DMarketAPI:
    """
    DMarket API client for interacting with the DMarket API service.
    This class provides methods to sign requests and interact with the API endpoints.
    """

    def __init__(
        self,
        public_key: str,
        secret_key: str,
        api_url: str = "https://api.dmarket.com"
    ):
        """
        Initialize DMarket API client.

        Args:
            public_key: DMarket API public key
            secret_key: DMarket API secret key
            api_url: API URL (default is https://api.dmarket.com)
        """
        self.public_key = public_key
        self.secret_key = secret_key.encode("utf-8")
        self.api_url = api_url    def _generate_signature(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """
        Generate signature for DMarket API requests.

        Args:
            method: HTTP method (GET, POST etc)
            path: API method path without domain
            body: Request body as JSON string (for POST requests)

        Returns:
            Dict with authorization headers
        """
        timestamp = str(int(time.time()))
        string_to_sign = f"{method.upper()}{path}{timestamp}{body}"
        signature = hmac.new(
            self.secret_key,
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return {
            "X-Api-Key": self.public_key,
            "X-Request-Sign": f"timestampString={timestamp};signatureString={signature}",
            "Content-Type": "application/json",
        }

    async    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute request to DMarket API.

        Args:
            method: HTTP method (GET, POST etc)
            path: API method path without domain
            params: Request parameters for GET
            data: Data for POST request

        Returns:
            API response as dict
        """
        url = f"{self.api_url}{path}"

        # Add parameters to URL for GET requests
        if params and method.upper() == "GET":
            url = f"{url}?{urlencode(params)}"

        # Convert body to JSON for POST requests
        body = ""
        if data and method.upper() in ["POST", "PUT"]:
            body = json.dumps(data)

        headers = self._generate_signature(method, path, body)

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=data if method.upper() in ["POST", "PUT"] else None,
            )

            try:
                return response.json()
            except ValueError:
                return {"error": "Invalid JSON response", "status": response.status_code}    async def get_user_balance(self) -> Dict[str, Any]:
        """
        Get user balance.

        Returns:
            User balance as dict
        """
        return await self._request(
            "GET",
            "/account/v1/balance"
        )async def get_market_items(
        self, game: str = "csgo", limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get list of items in the marketplace.

        Args:
            game: Game name (csgo, dota2, rust etc)
            limit: Items limit (max 100)
            offset: Offset for pagination

        Returns:
            List of items as dict
        """
        params = {
            "gameId": game,
            "limit": str(limit),
            "offset": str(offset),
        }
        return await self._request(
            "GET",
            "/marketplace-api/v1/items",
            params=params
        )
