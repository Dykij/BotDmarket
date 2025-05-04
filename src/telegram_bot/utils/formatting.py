"""
Вспомогательные функции для форматирования данных в телеграм-боте
"""
from typing import List, Dict, Any, Optional


def format_dmarket_results(items: Optional[List[Dict[str, Any]]], mode: str, game: str) -> str:
    """
    Форматирует результаты поиска арбитражных возможностей для отображения в Telegram.

    Args:
        items: Список предметов с арбитражными возможностями
        mode: Режим арбитража ('boost', 'mid', 'pro')
        game: Идентификатор игры

    Returns:
        Отформатированный текст для отправки в Telegram
    """
    if not items:
        mode_display = {
            "boost": "режим разгона баланса",
            "mid": "средний режим",
            "pro": "профессиональный режим"
        }
        return f"ℹ️ Не найдено арбитражных возможностей для {game.upper()} ({mode_display.get(mode, mode)})"

    game_display = {
        "csgo": "CS2",
        "dota2": "Dota 2",
        "rust": "Rust",
        "tf2": "Team Fortress 2"
    }

    mode_display = {
        "boost": "быстрый разгон баланса",
        "mid": "средний трейдер",
        "pro": "профессионал"
    }

    text = [f"🔍 Результаты арбитража ({mode_display.get(mode, mode)}):"]
    text.append(f"🎮 Игра: {game_display.get(game, game.upper())}\n")

    for i, item in enumerate(items[:10], 1):
        title = item.get("title", "Неизвестный предмет")
        profit = item.get("profit", 0)
        price = item.get("price", {}).get("USD", 0) / 100 if isinstance(item.get("price", {}), dict) else 0
        profit_percentage = (profit / price) * 100 if price > 0 else 0

        text.append(f"{i}. {title}")
        text.append(f"   💰 Цена: ${price:.2f}")
        text.append(f"   💵 Прибыль: ${profit/100:.2f} ({profit_percentage:.1f}%)")

        if i < len(items[:10]):
            text.append("")  # Пустая строка между предметами

    return "\n".join(text)


def format_best_opportunities(items: List[Dict[str, Any]], game: str) -> str:
    """
    Форматирует лучшие арбитражные возможности для отображения в Telegram.

    Args:
        items: Список предметов с лучшими арбитражными возможностями
        game: Идентификатор игры

    Returns:
        Отформатированный текст для отправки в Telegram
    """
    if not items:
        return f"ℹ️ Не найдено лучших арбитражных возможностей для {game.upper()}"

    game_display = {
        "csgo": "CS2",
        "dota2": "Dota 2",
        "rust": "Rust",
        "tf2": "Team Fortress 2"
    }

    text = [f"🌟 Лучшие арбитражные возможности:"]
    text.append(f"🎮 Игра: {game_display.get(game, game.upper())}\n")

    for i, item in enumerate(items[:10], 1):
        title = item.get("title", "Неизвестный предмет")
        profit = item.get("profit", 0)
        price = item.get("price", 0) / 100 if isinstance(item.get("price"), (int, float)) else 0
        profit_percentage = (profit / price) * 100 if price > 0 else 0

        text.append(f"{i}. {title}")
        text.append(f"   💰 Цена: ${price:.2f}")
        text.append(f"   💵 Прибыль: ${profit/100:.2f} ({profit_percentage:.1f}%)")

        if i < len(items[:10]):
            text.append("")  # Пустая строка между предметами

    return "\n".join(text)


def format_paginated_results(items: List[Dict[str, Any]], game: str, mode: str,
                             current_page: int, total_pages: int) -> str:
    """
    Форматирует результаты с пагинацией для отображения в Telegram.

    Args:
        items: Список предметов на текущей странице
        game: Идентификатор игры
        mode: Режим арбитража
        current_page: Текущая страница (0-based)
        total_pages: Общее количество страниц

    Returns:
        Отформатированный текст для отправки в Telegram
    """
    if not items:
        mode_display = {
            "boost": "авто-буст",
            "mid": "средний режим",
            "pro": "профессиональный режим",
            "auto_boost": "автоматический арбитраж"
        }
        return f"ℹ️ Нет данных об автоматическом арбитраже ({mode})"

    game_display = {
        "csgo": "CS2",
        "dota2": "Dota 2",
        "rust": "Rust",
        "tf2": "Team Fortress 2"
    }

    risk_levels = {
        "high": "высокий",
        "medium": "средний",
        "low": "низкий"
    }

    liquidity_levels = {
        "high": "высокая",
        "medium": "средняя",
        "low": "низкая"
    }

    text = [f"🤖 Результаты автоматического арбитража (средняя прибыль):"]

    for i, item in enumerate(items, 1):
        title = item.get("title", "Неизвестный предмет")
        profit = item.get("profit", 0)
        price = item.get("price", {}).get("amount", 0) / 100 if isinstance(item.get("price", {}), dict) else 0
        profit_percentage = (profit / price) * 100 if price > 0 else 0

        # Дополнительные данные для расширенной информации
        liquidity = item.get("liquidity", "medium")
        risk = item.get("risk", "medium")

        text.append(f"{i}. {title}")
        text.append(f"   🎮 Игра: {game_display.get(game, game.upper())}")
        text.append(f"   💰 Цена: ${price:.2f}")
        text.append(f"   💵 Прибыль: ${profit/100:.2f} ({profit_percentage:.1f}%)")
        text.append(f"   🔄 Ликвидность: {liquidity_levels.get(liquidity, liquidity)}")
        text.append(f"   ⚠️ Риск: {risk_levels.get(risk, risk)}")

        if i < len(items):
            text.append("")  # Пустая строка между предметами

    if total_pages > 1:
        text.append(f"\nСтраница {current_page + 1} из {total_pages}")

    return "\n".join(text)
