"""
API GUIDELINES ДЛЯ DMARKET И TELEGRAM API

Данный файл содержит подробные рекомендации по работе с DMarket API и Telegram Bot API,
основанные на официальной документации. Используйте его как справочник при разработке.
"""

# ============================================================================
# ============================= DMARKET API ==================================
# ============================================================================

# Базовые URL и эндпоинты
DMARKET_BASE_URL = "https://api.dmarket.com"

# Основные эндпоинты
ENDPOINTS = {
    'MARKET_ITEMS': "/exchange/v1/market/items",  # Получение предметов с маркета
    'USER_INVENTORY': "/exchange/v1/user/inventory",  # Получение инвентаря пользователя 
    'USER_BALANCE': "/account/v1/balance",  # Получение баланса пользователя
    'PURCHASE': "/exchange/v1/market/items/buy",  # Покупка предмета
    'SELL': "/exchange/v1/user/inventory/sell",  # Продажа предмета
    'SALES_HISTORY': "/account/v1/sales-history",  # История продаж
    'TARGET_LIST': "/exchange/v1/target-lists",  # Списки целевых предметов
    'USER_OFFERS': "/exchange/v1/user/offers",  # Активные предложения пользователя
    'MARKET_PRICE_AGGREGATED': "/exchange/v1/market/aggregated-prices"  # Агрегированные цены
}

# Важные особенности DMarket API

# 1. Все денежные значения указываются в центах (100 центов = 1 USD)
# 2. Все запросы должны быть подписаны с использованием HMAC-SHA256
# 3. Запросы ограничены по частоте (rate limiting)
# 4. При ошибках 429 (Too Many Requests) необходимо реализовать повторные попытки с задержкой
# 5. Все запросы должны содержать заголовки X-Api-Key и X-Request-Sign

# Пример генерации подписи для запросов к DMarket API
def generate_signature_example(method, path, body, secret_key):
    """
    Пример генерации подписи для запросов к DMarket API.
    
    Args:
        method: HTTP метод (GET, POST и т.д.)
        path: Путь запроса (например, "/account/v1/balance")
        body: Тело запроса (для POST/PUT)
        secret_key: Секретный ключ API
        
    Returns:
        str: Хеш-подпись для запроса
    """
    import hmac
    import hashlib
    
    # Создаем строку для подписи
    message = f"{method}{path}{body}"
    
    # Генерируем HMAC-SHA256 подпись
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature


# Пример использования подписи в запросе
def auth_headers_example(public_key, secret_key, method, path, body=""):
    """
    Пример создания заголовков для запроса к DMarket API.
    
    Args:
        public_key: Публичный ключ API
        secret_key: Секретный ключ API
        method: HTTP метод
        path: Путь запроса
        body: Тело запроса (для POST/PUT)
        
    Returns:
        dict: Заголовки для запроса
    """
    import time
    
    # Создаем подпись
    signature = generate_signature_example(method, path, body, secret_key)
    
    # Формируем заголовки
    headers = {
        "X-Api-Key": public_key,
        "X-Request-Sign": signature,
        "X-Sign-Date": str(int(time.time())),
        "Content-Type": "application/json"
    }
    
    return headers


# Параметры запроса предметов с маркета
MARKET_ITEMS_PARAMS = {
    "gameId": "Идентификатор игры (csgo, dota2, ...)",
    "limit": "Количество предметов на страницу (макс. 100)",
    "offset": "Смещение для пагинации",
    "orderBy": "Поле для сортировки (price, title, ...)",
    "orderDir": "Направление сортировки (asc, desc)",
    "title": "Фильтр по названию предмета",
    "priceFrom": "Минимальная цена в центах",
    "priceTo": "Максимальная цена в центах",
    "treeFilters": "Фильтр по категориям предметов",
    "gameType": "Тип игры",
    "types": "Типы предметов"
}

# Параметры запроса инвентаря
INVENTORY_PARAMS = {
    "gameId": "Идентификатор игры",
    "limit": "Количество предметов на страницу (макс. 100)",
    "offset": "Смещение для пагинации",
    "orderBy": "Поле для сортировки",
    "orderDir": "Направление сортировки",
    "statuses": "Статусы предметов (active, onsale, ...)",
    "cursor": "Курсор для пагинации (альтернатива offset)"
}

# Формат запроса на покупку предмета
PURCHASE_REQUEST = {
    "itemId": "UUID предмета",
    "price": {
        "amount": "Цена в центах",
        "currency": "USD"
    },
    "gameType": "Тип игры (optional)"
}

# Формат запроса на продажу предмета
SELL_REQUEST = {
    "itemId": "UUID предмета из инвентаря",
    "price": {
        "amount": "Цена в центах",
        "currency": "USD"
    }
}

# Коды ошибок и их обработка
DMARKET_ERROR_CODES = {
    400: "Неверный запрос или параметры",
    401: "Неверная аутентификация",
    403: "Доступ запрещен",
    404: "Ресурс не найден",
    429: "Слишком много запросов (rate limit)",
    500: "Внутренняя ошибка сервера",
    502: "Bad Gateway",
    503: "Сервис недоступен",
    504: "Gateway Timeout"
}

# Примеры ответов API

# Ответ при получении баланса
BALANCE_RESPONSE = {
    "usd": {
        "amount": 10000,  # 100 USD в центах
        "currency": "USD"
    },
    "has_funds": True,
    "available_balance": 100.0
}

# Ответ с предметами маркета
MARKET_ITEMS_RESPONSE = {
    "objects": [
        {
            "itemId": "00000000-0000-0000-0000-000000000000",
            "title": "AK-47 | Redline (Field-Tested)",
            "price": {
                "USD": 1000  # 10 USD в центах
            },
            "classId": "1234567890",
            "gameId": "csgo",
            "categoryPath": "Rifle",
            "image": "https://cdn.dmarket.com/path/to/image.png",
            "extra": {
                "float": "0.25634",
                "stickers": [],
                "wear": "Field-Tested"
            }
        }
    ],
    "total": 1
}

# Рекомендации по реализации клиента DMarket API

"""
Класс для работы с DMarket API должен включать:

1. Инициализацию с ключами API:
   - public_key - публичный API ключ
   - secret_key - секретный API ключ

2. Метод для создания подписи запросов

3. Метод для выполнения HTTP-запросов с обработкой ошибок:
   - Поддержка повторных попыток при ошибках 429 и 5xx
   - Логирование ошибок
   - Корректная обработка ответов

4. Методы для работы с каждым эндпоинтом:
   - get_balance - получение баланса пользователя
   - get_market_items - получение предметов с маркета
   - get_user_inventory - получение инвентаря пользователя
   - buy_item - покупка предмета
   - sell_item - продажа предмета
   - и другие

5. Правильное закрытие HTTP-клиента при завершении работы
"""


# ============================================================================
# =========================== TELEGRAM BOT API ===============================
# ============================================================================

# Основные компоненты Telegram Bot API

"""
Telegram Bot API используется для создания ботов в Telegram.
Основные компоненты:
1. Токен бота - уникальный идентификатор вашего бота
2. Обновления (Updates) - сообщения и действия пользователей
3. Обработчики команд и сообщений
4. Клавиатуры и инлайн-кнопки
5. Отправка разных типов сообщений (текст, медиа, файлы)
"""

# Типы обновлений (Updates)
TELEGRAM_UPDATE_TYPES = {
    "message": "Обычное сообщение",
    "edited_message": "Отредактированное сообщение",
    "channel_post": "Пост в канале",
    "edited_channel_post": "Отредактированный пост в канале",
    "inline_query": "Inline-запрос пользователя",
    "chosen_inline_result": "Выбранный результат inline-запроса",
    "callback_query": "Нажатие на инлайн-кнопку",
    "shipping_query": "Запрос на доставку товара",
    "pre_checkout_query": "Запрос перед оплатой",
    "poll": "Опрос",
    "poll_answer": "Ответ на опрос",
    "my_chat_member": "Изменение статуса бота в чате",
    "chat_member": "Изменение статуса участника чата",
    "chat_join_request": "Запрос на вступление в чат"
}

# Типы клавиатур
TELEGRAM_KEYBOARD_TYPES = {
    "ReplyKeyboardMarkup": "Обычная клавиатура под полем ввода",
    "InlineKeyboardMarkup": "Инлайн-клавиатура внутри сообщения",
    "ReplyKeyboardRemove": "Удаление клавиатуры",
    "ForceReply": "Принудительный ответ на сообщение"
}

# Примеры создания клавиатур

def create_main_keyboard_example():
    """
    Пример создания обычной клавиатуры для Telegram бота.
    
    Returns:
        ReplyKeyboardMarkup: Объект клавиатуры
    """
    from telegram import ReplyKeyboardMarkup
    
    keyboard = [
        ["👛 Баланс", "🔍 Поиск предметов"],
        ["💹 Арбитраж", "⚙️ Настройки"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_game_selection_keyboard_example():
    """
    Пример создания инлайн-клавиатуры для Telegram бота.
    
    Returns:
        InlineKeyboardMarkup: Объект инлайн-клавиатуры
    """
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = [
        [
            InlineKeyboardButton("CS:GO", callback_data="game_csgo"),
            InlineKeyboardButton("Dota 2", callback_data="game_dota2")
        ],
        [
            InlineKeyboardButton("Rust", callback_data="game_rust"),
            InlineKeyboardButton("Team Fortress 2", callback_data="game_tf2")
        ],
        [InlineKeyboardButton("Отмена", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Примеры обработчиков команд и сообщений

async def start_command_example(update, context):
    """
    Пример обработчика команды /start.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст обработчика
    """
    await update.message.reply_text(
        "Привет! Я бот для работы с DMarket.",
        reply_markup=create_main_keyboard_example()
    )


async def message_handler_example(update, context):
    """
    Пример обработчика обычных сообщений.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст обработчика
    """
    text = update.message.text
    
    # Обработка на основе текста или состояния пользователя
    if "Баланс" in text:
        await balance_command_example(update, context)
    elif "Поиск" in text:
        await market_command_example(update, context)
    else:
        await update.message.reply_text("Пожалуйста, используйте меню.")


async def button_handler_example(update, context):
    """
    Пример обработчика нажатий на инлайн-кнопки.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст обработчика
    """
    query = update.callback_query
    await query.answer()  # Важно: отвечаем на callback query
    
    data = query.data
    if data.startswith("game_"):
        game = data.split("_")[1]
        context.user_data["selected_game"] = game
        await query.edit_message_text(f"Выбрана игра: {game}")


# Форматирование текста
TELEGRAM_TEXT_FORMATTING = {
    "HTML": """
<b>Жирный текст</b>
<i>Курсив</i>
<code>Моноширинный текст</code>
<pre>Блок кода</pre>
<a href="https://example.com">Ссылка</a>
    """,
    
    "Markdown": """
*Жирный текст*
_Курсив_
`Моноширинный текст`
```
Блок кода
```
[Ссылка](https://example.com)
    """
}

# Ограничения Telegram API

"""
1. Сообщения: максимум 4096 символов в одном сообщении
2. Медиа-подписи: максимум 1024 символа
3. Кнопки: до 100 кнопок в одном сообщении
4. Частота запросов: до 30 сообщений в секунду всего, до 20 сообщений в минуту в один чат
5. Размер файлов: до 50 МБ для файлов, до 20 МБ для фото и стикеров
6. Инлайн-результаты: до 50 результатов в одном ответе
"""

# Управление состоянием диалога

def conversation_handler_example():
    """
    Пример создания конечного автомата (FSM) для управления диалогом.
    
    Returns:
        ConversationHandler: Обработчик диалога
    """
    from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters

    # Определение состояний
    SELECTING_GAME, ENTERING_QUERY, VIEWING_RESULTS = range(3)

    # Пример функций обработчиков (не реализованы, только для демонстрации)
    async def start_search(update, context):
        """Пример функции для начала поиска."""
        await update.message.reply_text("Выберите игру:")
        return SELECTING_GAME
        
    async def select_game(update, context):
        """Пример функции для выбора игры."""
        game = update.message.text
        context.user_data["game"] = game
        await update.message.reply_text(f"Выбрана игра {game}. Введите поисковый запрос:")
        return ENTERING_QUERY
        
    async def process_query(update, context):
        """Пример функции для обработки поискового запроса."""
        query = update.message.text
        context.user_data["query"] = query
        await update.message.reply_text(f"Ищем '{query}' в игре {context.user_data['game']}...")
        return VIEWING_RESULTS
        
    async def show_results(update, context):
        """Пример функции для отображения результатов."""
        await update.message.reply_text("Вот результаты поиска.")
        return ConversationHandler.END
        
    async def cancel_search(update, context):
        """Пример функции для отмены поиска."""
        await update.message.reply_text("Поиск отменен.")
        return ConversationHandler.END
    
    # Обработчики для разных состояний
    entry_points = [CommandHandler("search", start_search)]
    
    states = {
        SELECTING_GAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_game)],
        ENTERING_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_query)],
        VIEWING_RESULTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_results)]
    }
    
    fallbacks = [CommandHandler("cancel", cancel_search)]
    
    return ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=fallbacks
    )


# Пример обработки ошибок

async def error_handler_example(update, context):
    """
    Пример обработчика ошибок для Telegram бота.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст обработчика с информацией об ошибке
    """
    import logging
    from telegram.error import NetworkError
    
    logger = logging.getLogger(__name__)
    logger.error(f"Произошла ошибка: {context.error}")
    
    # Уведомляем пользователя
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="К сожалению, произошла ошибка. Пожалуйста, попробуйте позже."
        )
    
    # Для сетевых ошибок
    if isinstance(context.error, NetworkError):
        logger.error("Сетевая ошибка - повторная попытка через 10 секунд")
        # Здесь можно реализовать повторные попытки


# Интеграция Telegram с DMarket

async def balance_command_example(update, context):
    """
    Пример команды для проверки баланса DMarket через Telegram бота.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст обработчика
    """
    # Проверяем наличие API ключей
    api_keys = get_api_keys_example(context)
    if not api_keys:
        await update.message.reply_text(
            "Ключи API DMarket не настроены. Пожалуйста, настройте их в /settings."
        )
        return
    
    # Создаем клиент DMarket API
    from src.dmarket.dmarket_api import DMarketAPI
    dmarket_api = DMarketAPI(api_keys["public_key"], api_keys["secret_key"])
    
    try:
        # Получаем баланс
        balance = await dmarket_api.get_balance()
        
        # Форматируем сообщение о балансе
        if balance.get("error"):
            message = f"Ошибка при получении баланса: {balance.get('message')}"
        else:
            amount = balance.get("usd", {}).get("amount", 0) / 100  # центы в доллары
            message = f"Ваш баланс: ${amount:.2f}"
        
        # Отправляем пользователю
        await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при получении баланса: {str(e)}")
    finally:
        # Закрываем API клиент
        await dmarket_api._close_client()


def get_api_keys_example(context):
    """
    Пример получения API ключей из контекста Telegram бота.
    
    Args:
        context: Контекст обработчика
        
    Returns:
        dict: Словарь с API ключами или None
    """
    user_id = context.effective_user.id
    
    # Получаем ключи из данных пользователя или бота
    user_data = context.user_data
    api_keys = user_data.get("api_keys")
    
    if not api_keys:
        # Можно также проверить в данных бота (общие настройки)
        bot_data = context.bot_data
        api_keys = bot_data.get("default_api_keys")
    
    return api_keys


async def market_command_example(update, context):
    """
    Пример команды для поиска предметов на маркете.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст обработчика
    """
    # Запрашиваем у пользователя выбор игры
    keyboard = create_game_selection_keyboard_example()
    
    await update.message.reply_text(
        "Выберите игру для поиска предметов:",
        reply_markup=keyboard
    )
    
    # Устанавливаем состояние диалога
    context.user_data["search_state"] = "awaiting_game"


# Рекомендации по реализации Telegram бота

"""
1. Структура приложения:
   - Организация модулей по функционалу (handlers, utils, keyboards)
   - Выделение повторяющегося кода в отдельные функции
   - Асинхронное программирование для всех операций ввода-вывода

2. Обработка команд и сообщений:
   - Четкое разделение обработчиков по назначению
   - Использование фильтров для точного выбора обработчиков
   - Структурирование диалога с пользователем

3. Хранение данных:
   - Использование context.user_data для хранения состояния пользователя
   - context.bot_data для общих данных бота
   - context.chat_data для данных конкретного чата

4. Безопасность:
   - Проверка прав доступа к функциям бота
   - Валидация пользовательского ввода
   - Безопасное хранение ключей API и токенов

5. Обработка ошибок:
   - Глобальный обработчик ошибок
   - Логирование всех исключений
   - Информативные сообщения для пользователей
"""


# Пример полной интеграции арбитража DMarket с Telegram ботом

async def arbitrage_command_example(update, context):
    """
    Пример команды для поиска арбитражных возможностей.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст обработчика
    """
    # Проверяем наличие API ключей
    api_keys = get_api_keys_example(context)
    if not api_keys:
        await update.message.reply_text(
            "Ключи API DMarket не настроены. Пожалуйста, настройте их в /settings."
        )
        return
    
    # Отправляем сообщение о начале сканирования
    message = await update.message.reply_text("Начинаю поиск арбитражных возможностей...")
    
    try:
        # Создаем клиент DMarket API
        from src.dmarket.dmarket_api import DMarketAPI
        dmarket_api = DMarketAPI(api_keys["public_key"], api_keys["secret_key"])
        
        # Получаем возможности для арбитража
        # В модуле arbitrage должна быть функция для сканирования возможностей
        from src.dmarket.arbitrage import find_arbitrage_opportunities
        opportunities = await find_arbitrage_opportunities(dmarket_api)
        
        if not opportunities:
            await message.edit_text("Арбитражные возможности не найдены.")
            return
        
        # Форматируем результаты с пагинацией
        # Создаем или используем функцию форматирования
        from src.telegram_bot.utils.formatters import format_opportunities
        results_text = format_opportunities(opportunities)
        
        # Создаем клавиатуру для пагинации
        from src.telegram_bot.keyboards import create_pagination_keyboard
        keyboard = create_pagination_keyboard(0, len(opportunities) // 5 + 1)
        
        # Отправляем результаты
        await message.edit_text(
            results_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        
        # Сохраняем данные для пагинации
        context.user_data["arbitrage_results"] = opportunities
        context.user_data["current_page"] = 0
        
    except Exception as e:
        await message.edit_text(f"Ошибка при поиске арбитража: {str(e)}")
    finally:
        # Закрываем API клиент
        await dmarket_api._close_client() 