import os
import pytest
import asyncio
from src.dmarket.arbitrage import (
    arbitrage_boost, arbitrage_mid, arbitrage_pro,
    arbitrage_boost_async, arbitrage_mid_async, arbitrage_pro_async
)

# Тесты для MOCK-логики (быстрые, не требуют API)
def test_arbitrage_boost_mock():
    results = arbitrage_boost()
    for skin in results:
        profit = float(skin["profit"].replace("$", ""))
        assert 1 <= profit <= 5

def test_arbitrage_mid_mock():
    results = arbitrage_mid()
    for skin in results:
        profit = float(skin["profit"].replace("$", ""))
        assert 5 <= profit <= 20

def test_arbitrage_pro_mock():
    results = arbitrage_pro()
    for skin in results:
        profit = float(skin["profit"].replace("$", ""))
        assert 20 <= profit <= 100

# Асинхронные тесты для реального API (будут пропущены, если нет ключей)
@pytest.mark.asyncio
async def test_arbitrage_boost_async():
    if not os.environ.get("DMARKET_PUBLIC_KEY") or not os.environ.get("DMARKET_SECRET_KEY"):
        pytest.skip("No DMarket API keys set")
    results = await arbitrage_boost_async()
    assert isinstance(results, list)
    # Можно добавить проверки диапазона прибыли, если API возвращает реальные данные

@pytest.mark.asyncio
async def test_arbitrage_mid_async():
    if not os.environ.get("DMARKET_PUBLIC_KEY") or not os.environ.get("DMARKET_SECRET_KEY"):
        pytest.skip("No DMarket API keys set")
    results = await arbitrage_mid_async()
    assert isinstance(results, list)

@pytest.mark.asyncio
async def test_arbitrage_pro_async():
    if not os.environ.get("DMARKET_PUBLIC_KEY") or not os.environ.get("DMARKET_SECRET_KEY"):
        pytest.skip("No DMarket API keys set")
    results = await arbitrage_pro_async()
    assert isinstance(results, list)
