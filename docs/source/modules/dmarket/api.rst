.. _dmarket-api-details:

DMarket API Модуль
================

Этот модуль предоставляет интерфейс для взаимодействия с DMarket API.

Обзор
----

Класс ``DMarketAPI`` инкапсулирует всю логику работы с API платформы DMarket, включая:

- Аутентификацию с использованием пары ключей (public и secret)
- Подписание запросов в соответствии с требованиями API
- Обработку ошибок и повторные попытки при сетевых проблемах
- Методы для получения информации о предметах, балансе и транзакциях
- Методы для покупки и продажи предметов

Основные функции
--------------

Инициализация
~~~~~~~~~~~

.. code-block:: python

    api = DMarketAPI(
        public_key="your_public_key", 
        secret_key="your_secret_key",
        max_retries=3
    )

Получение баланса
~~~~~~~~~~~~~~

.. code-block:: python

    balance = await api.get_user_balance()
    
    # Баланс содержит информацию в формате:
    # {
    #     "usd": {"amount": 10000},  # 100 USD в центах
    #     "has_funds": True,
    #     "available_balance": 100.0
    # }

Получение предметов с маркета
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Поиск предметов CS:GO с ценой от $1 до $10
    items = await api.get_market_items(
        game="csgo",
        limit=10,
        price_from=100,  # в центах ($1.00)
        price_to=1000    # в центах ($10.00)
    )
    
    # Обработка результатов
    for item in items.get("objects", []):
        title = item.get("title")
        price = item.get("price", {}).get("USD", 0) / 100  # Конвертация из центов в доллары
        print(f"{title}: ${price:.2f}")

Покупка предмета
~~~~~~~~~~~~~

.. code-block:: python

    result = await api.buy_item(
        item_id="item_id_from_market",
        price=1000  # Цена в центах ($10.00)
    )
    
    if result.get("status") == "SUCCESS":
        print("Покупка успешна!")
    else:
        print(f"Ошибка: {result.get('error', {}).get('message')}")

Продажа предмета
~~~~~~~~~~~~~

.. code-block:: python

    result = await api.sell_item(
        item_id="item_id_from_inventory",
        price=1250  # Цена продажи в центах ($12.50)
    )
    
    if result.get("status") == "SUCCESS":
        print("Предмет выставлен на продажу!")
    else:
        print(f"Ошибка: {result.get('error', {}).get('message')}")

Обработка ошибок
--------------

Модуль включает встроенные механизмы обработки ошибок:

1. **Повторные попытки при временных проблемах**
   
   При ошибках сети или временных проблемах API (коды 429, 500, 502, 503, 504) модуль автоматически повторяет запросы до `max_retries` раз с экспоненциальным ожиданием между попытками.

2. **Расширенная информация об ошибках**
   
   В случае критических ошибок модуль предоставляет подробную информацию для диагностики:
   
   .. code-block:: python
   
       try:
           balance = await api.get_user_balance()
       except Exception as e:
           print(f"Ошибка: {e}")
           print(f"Статус код: {getattr(e, 'status_code', 'Неизвестно')}")
           print(f"Ответ: {getattr(e, 'response', 'Нет данных')}")

Безопасность
---------

API-ключи должны храниться в безопасном месте и никогда не должны быть доступны публично. Рекомендуется:

1. Использовать переменные окружения для хранения ключей
2. Не включать ключи в код или систему контроля версий
3. Использовать файл `.env` для локальной разработки (с добавлением `.env` в `.gitignore`)

Параметры API-клиента
------------------

DMarketAPI принимает следующие параметры:

- ``public_key`` (str): Публичный ключ API DMarket
- ``secret_key`` (str): Секретный ключ API DMarket
- ``max_retries`` (int, optional): Максимальное количество повторных попыток при ошибках. По умолчанию 3.
- ``retry_delay`` (float, optional): Базовая задержка между повторными попытками в секундах. По умолчанию 1.0.
- ``timeout`` (float, optional): Тайм-аут для HTTP-запросов в секундах. По умолчанию 10.0.

Типичные ошибки
------------

1. **Неверные ключи API**: Проверьте правильность ключей и убедитесь, что они активны в панели управления DMarket.

2. **Недостаточно средств**: При покупке предметов убедитесь, что на балансе достаточно средств.

3. **Недействительные параметры**: Проверьте правильность параметров запроса, особенно game IDs и ценовые диапазоны.

4. **Превышение лимитов API**: DMarket имеет ограничения на количество запросов в единицу времени. Модуль автоматически обрабатывает эти ограничения, но при массовых запросах может потребоваться дополнительная оптимизация.

Расширенное использование
--------------------

### Пагинация результатов

Для работы с большими объемами данных используйте пагинацию:

.. code-block:: python

    offset = 0
    limit = 50
    all_items = []
    
    while True:
        items = await api.get_market_items(
            game="csgo",
            offset=offset,
            limit=limit
        )
        
        batch = items.get("objects", [])
        if not batch:
            break
            
        all_items.extend(batch)
        offset += limit
        
        if len(all_items) >= items.get("total", 0):
            break

### Фильтрация предметов

API поддерживает различные параметры фильтрации:

.. code-block:: python

    # Поиск предметов определенного типа
    items = await api.get_market_items(
        game="csgo",
        title="AK-47",  # Поиск по названию
        category_path="Rifle",  # Категория
        min_float=0.01,  # Минимальное значение Float
        max_float=0.15   # Максимальное значение Float
    )

### Подписка на события рынка

Для получения обновлений в реальном времени:

.. code-block:: python

    async def price_drop_handler(item):
        print(f"Цена на {item['title']} упала до ${item['price']['USD']/100:.2f}!")
    
    # Настройка обработчика событий
    api.add_event_handler("price_drop", price_drop_handler)
    
    # Запуск прослушивания событий
    await api.start_market_listener(["csgo"], ["price_drop"]) 