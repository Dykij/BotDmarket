"""Тесты для модуля sales_history.py."""

import time
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.dmarket.sales_history import analyze_sales_history, get_sales_history
from src.utils.api_error_handling import APIError


@pytest.fixture
def mock_api_client():
    """Создает мок DMarket API клиента."""
    client = AsyncMock()
    client.request = AsyncMock()
    return client



