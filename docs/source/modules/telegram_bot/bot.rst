.. _telegram-bot-module:

Модуль Telegram Bot
=================

Этот модуль реализует Telegram бота для платформы DMarket.

Основной модуль бота
-----------------

Файл ``bot_v2.py`` содержит основную логику работы Telegram бота. Здесь настраиваются обработчики команд, 
управление состоянием пользователя и взаимодействие с API DMarket.

Инициализация и запуск
-------------------

Бот инициализируется с использованием токена из переменных окружения:

.. code-block:: python

    from telegram.ext import Application
    
    def create_application():
        """Создает экземпляр приложения бота."""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        
        application = Application.builder().token(token).build()
        
        # Настройка обработчиков команд
        setup_command_handlers(application)
        
        # Настройка обработчиков ошибок
        setup_error_handlers(application)
        
        return application
    
    async def main():
        """Основная функция для запуска бота."""
        application = create_application()
        await application.run_polling()

Обработчики команд
---------------

Бот поддерживает следующие основные команды:

.. code-block:: python

    def setup_command_handlers(application):
        """Настраивает обработчики команд."""
        # Основные команды
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("balance", balance_command))
        application.add_handler(CommandHandler("market", market_command))
        application.add_handler(CommandHandler("arbitrage", arbitrage_command))
        
        # Дополнительные команды
        application.add_handler(CommandHandler("settings", settings_command))
        application.add_handler(CommandHandler("notifications", notifications_command))
        
        # Обработчики сообщений и обратных вызовов
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        application.add_handler(CallbackQueryHandler(callback_handler))

Примеры обработчиков команд:

.. code-block:: python

    async def start_command(update, context):
        """Обрабатывает команду /start."""
        user = update.effective_user
        welcome_message = (
            f"Добро пожаловать, {user.first_name}! 👋\n\n"
            "Я бот для работы с платформой DMarket.\n"
            "Используйте /help для списка доступных команд."
        )
        await update.message.reply_text(welcome_message, reply_markup=create_main_keyboard())
    
    async def balance_command(update, context):
        """Обрабатывает команду /balance."""
        # Проверяем наличие API ключей
        if not is_api_configured():
            await update.message.reply_text(
                "Ключи API не настроены. Пожалуйста, настройте их в разделе /settings."
            )
            return
        
        # Получаем баланс через API DMarket
        try:
            api = get_dmarket_api()
            balance_data = await api.get_user_balance()
            
            # Форматируем и отправляем сообщение с балансом
            message = format_balance_message(balance_data)
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Ошибка при получении баланса: {e}")
            await update.message.reply_text(
                "Произошла ошибка при получении баланса. Пожалуйста, попробуйте позже."
            )

Обработка ошибок
-------------

Бот включает в себя обработку различных типов ошибок:

.. code-block:: python

    def setup_error_handlers(application):
        """Настраивает обработчики ошибок."""
        application.add_error_handler(handle_error)
    
    async def handle_error(update, context):
        """Обрабатывает ошибки, возникающие во время выполнения."""
        # Получаем информацию об ошибке
        error = context.error
        
        # Логируем ошибку
        logger.error(f"Произошла ошибка: {error}", exc_info=context.error)
        
        # Отправляем уведомление пользователю
        if update and update.effective_chat:
            if isinstance(error, ApiError):
                # Обработка ошибок API
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Ошибка API: {error.message}"
                )
            elif isinstance(error, NetworkError):
                # Обработка сетевых ошибок
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Произошла сетевая ошибка. Пожалуйста, попробуйте позже."
                )
            else:
                # Обработка других ошибок
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Произошла неизвестная ошибка. Наша команда уже работает над решением."
                )

Форматирование сообщений
---------------------

Для форматирования сообщений используются специальные функции:

.. code-block:: python

    def format_balance_message(balance_data):
        """Форматирует сообщение с информацией о балансе."""
        usd_amount = balance_data.get("usd", {}).get("amount", 0) / 100  # Конвертация центов в доллары
        available_balance = balance_data.get("available_balance", 0)
        has_funds = balance_data.get("has_funds", False)
        
        message = (
            "💰 *Ваш баланс*\n\n"
            f"Общий баланс: *${usd_amount:.2f}*\n"
            f"Доступно: *${available_balance:.2f}*\n"
            f"Статус: {'✅ Есть средства' if has_funds else '❌ Нет средств'}"
        )
        
        return message
    
    def format_market_item(item):
        """Форматирует информацию о предмете с маркета."""
        title = item.get("title", "Неизвестно")
        price_usd = item.get("price", {}).get("USD", 0) / 100
        category = item.get("categoryPath", "Категория не указана")
        wear = item.get("extra", {}).get("wear", "Не указано")
        
        message = (
            f"🎮 *{title}*\n"
            f"💵 Цена: *${price_usd:.2f}*\n"
            f"📁 Категория: {category}\n"
            f"👕 Состояние: {wear}\n"
            f"🆔 ID: `{item.get('itemId', 'Нет ID')}`"
        )
        
        return message

Управление состоянием пользователя
-----------------------------

Для управления состоянием пользователя используется контекст бота:

.. code-block:: python

    async def market_command(update, context):
        """Обрабатывает команду /market для поиска предметов."""
        # Сбрасываем состояние поиска
        context.user_data["search_state"] = "awaiting_game"
        
        await update.message.reply_text(
            "Выберите игру для поиска предметов:",
            reply_markup=create_game_selection_keyboard()
        )
    
    async def message_handler(update, context):
        """Обрабатывает текстовые сообщения в зависимости от состояния пользователя."""
        user_state = context.user_data.get("search_state")
        
        if user_state == "awaiting_game":
            # Обрабатываем выбор игры
            game = update.message.text.lower()
            if game in SUPPORTED_GAMES:
                context.user_data["selected_game"] = game
                context.user_data["search_state"] = "awaiting_query"
                
                await update.message.reply_text(
                    "Введите название предмета для поиска:",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                await update.message.reply_text(
                    "Пожалуйста, выберите игру из списка.",
                    reply_markup=create_game_selection_keyboard()
                )
                
        elif user_state == "awaiting_query":
            # Обрабатываем поисковый запрос
            query = update.message.text
            game = context.user_data.get("selected_game")
            
            await update.message.reply_text(f"Ищем предметы для {game}: {query}...")
            
            try:
                api = get_dmarket_api()
                items = await api.get_market_items(
                    game=game,
                    title=query,
                    limit=5
                )
                
                if not items.get("objects"):
                    await update.message.reply_text("По вашему запросу ничего не найдено.")
                    return
                
                # Отправляем результаты поиска
                for item in items.get("objects", []):
                    message = format_market_item(item)
                    await update.message.reply_text(
                        message,
                        parse_mode="Markdown"
                    )
                
                # Сбрасываем состояние
                context.user_data["search_state"] = None
                
            except Exception as e:
                logger.error(f"Ошибка при поиске предметов: {e}")
                await update.message.reply_text(
                    "Произошла ошибка при поиске предметов. Пожалуйста, попробуйте позже."
                )
        else:
            # Обрабатываем сообщения без специального состояния
            await update.message.reply_text(
                "Используйте команды для взаимодействия с ботом.\n"
                "Для списка команд введите /help",
                reply_markup=create_main_keyboard()
            )

Интеграция с DMarket API
---------------------

Бот интегрируется с DMarket API через вспомогательные функции:

.. code-block:: python

    def get_dmarket_api():
        """Возвращает экземпляр DMarket API с ключами из переменных окружения."""
        public_key = os.getenv("DMARKET_PUBLIC_KEY")
        secret_key = os.getenv("DMARKET_SECRET_KEY")
        
        if not public_key or not secret_key:
            raise ValueError("API ключи DMarket не настроены")
        
        return DMarketAPI(public_key, secret_key)
    
    def is_api_configured():
        """Проверяет, настроены ли ключи API."""
        public_key = os.getenv("DMARKET_PUBLIC_KEY")
        secret_key = os.getenv("DMARKET_SECRET_KEY")
        
        return bool(public_key and secret_key)

Модуль также включает реализации для уведомлений, арбитражных стратегий и других функций, которые подробно описаны в соответствующих разделах документации. 