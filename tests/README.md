# Тесты проекта DMarket Bot

В этой директории содержатся тесты для различных компонентов проекта DMarket Bot.

## Структура тестов

- `test_api_unified.py` - объединенные тесты для DMarket API
- `test_bot_unified.py` - объединенные тесты для Telegram бота
- `test_arbitrage_unified.py` - объединенные тесты для модулей арбитража
- `dmarket/` - тесты для модулей DMarket API
- `telegram_bot/` - тесты для модулей Telegram бота
- `utils/` - тесты для вспомогательных модулей
- `fixtures/` - общие фикстуры для тестов

## Информация о рефакторинге

В ходе рефакторинга были объединены дублирующиеся тесты в единые файлы по категориям:

1. **DMarket API**: Файлы `test_dmarket_api.py`, `test_dmarket_api_balance.py`, `test_dmarket_api_patches.py` объединены в `test_api_unified.py`.

2. **Telegram бот**: Файлы `test_bot_v2.py`, `test_bot_v2_api_error_handling.py`, `test_bot_v2_commands.py` и др. объединены в `test_bot_unified.py`.

3. **Арбитраж**: Файлы `test_arbitrage.py`, `test_auto_arbitrage.py`, `test_arbitrage_scanner.py` и др. объединены в `test_arbitrage_unified.py`.

## Удаленные файлы:

Следующие файлы были удалены как устаревшие или дублирующиеся:

```
test_auto_arbitrage.py
test_arbitrage.py
test_arbitrage_scanner.py
test_auto_arbitrage_simple.py
test_arbitrage_boost.py
test_arbitrage_callback.py
test_arbitrage_callback_impl.py
test_arbitrage_sales_analysis.py
test_arbitrage_sales_opportunities.py
test_auto_arbitrage_scanner.py
test_auto_arbitrage_updated.py
test_demo_auto_arbitrage.py
test_bot_v2.py
test_bot_v2_api_error_handling.py
test_bot_v2_arbitrage.py
test_bot_v2_auto_arbitrage.py
test_bot_v2_commands.py
test_bot_v2_commands_sync.py
test_bot_v2_dmarket.py
test_bot_v2_formatting.py
test_bot_v2_functions.py
test_bot_v2_pagination.py
test_bot_v2_updated.py
test_telegram_bot.py
test_dmarket_api.py
test_dmarket_api_balance.py
test_dmarket_api_patches.py
test_error_handling.py
test_error_handling_new.py
test_error_handling_original.py
test_error_handlers.py
test_game_filters.py
test_game_filter_handlers_updated.py
test_rate_limiter_api_errors.py
test_rate_limiter_fixed_v3.py
test_sales_history.py
test_sales_analysis_callbacks_fixed.py
```

## Запуск тестов

Для запуска всех тестов:

```bash
pytest -xvs
```

Для запуска определенной категории тестов:

```bash
pytest -xvs test_api_unified.py  # тесты DMarket API
pytest -xvs test_bot_unified.py  # тесты Telegram бота
pytest -xvs test_arbitrage_unified.py  # тесты арбитража
```

## Замечания

- Все новые тесты следует добавлять в соответствующие унифицированные файлы.
- При создании новых тестовых файлов следует придерживаться структуры проекта.
- Для фикстур, используемых в нескольких тестовых файлах, стоит использовать директорию `fixtures/`.
