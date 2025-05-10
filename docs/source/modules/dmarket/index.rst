.. _dmarket-api:

DMarket API
==========

Модуль для взаимодействия с API платформы DMarket.

.. toctree::
   :maxdepth: 2

   api
   auto_arbitrage

Основные возможности
-----------------

Модуль ``dmarket_api.py`` предоставляет следующие возможности:

* Аутентификация на платформе DMarket
* Получение информации о предметах на маркете
* Получение баланса пользователя
* Покупка и продажа предметов
* Работа с лимитами запросов и обработка ошибок

Автоматический арбитраж
--------------------

Модуль ``auto_arbitrage.py`` предоставляет функциональность для автоматического арбитража:

* Поиск прибыльных арбитражных возможностей
* Фильтрация предметов по различным параметрам
* Три режима работы арбитража (Разгон баланса, Средний трейдер, Trade Pro)
* Демонстрационный режим для тестирования стратегий

Примеры использования
------------------

Инициализация клиента API:

.. code-block:: python

   from dmarket.dmarket_api import DMarketAPI
   
   # Инициализация с ключами API
   api = DMarketAPI(
       public_key="your_public_key",
       secret_key="your_secret_key",
       max_retries=3
   )

Получение баланса:

.. code-block:: python

   balance = await api.get_user_balance()
   print(f"Доступный баланс: ${balance['available_balance']:.2f}")

Получение предметов с маркета:

.. code-block:: python

   # Получение предметов CS:GO с ценой от $1 до $10
   items = await api.get_market_items(
       game="csgo",
       limit=10,
       price_from=100,  # в центах ($1.00)
       price_to=1000    # в центах ($10.00)
   )
   
   for item in items.get("objects", []):
       title = item.get("title", "Без названия")
       price = item.get("price", {}).get("USD", 0) / 100
       print(f"{title}: ${price:.2f}")

Использование автоматического арбитража:

.. code-block:: python

   from dmarket.auto_arbitrage import arbitrage_boost, auto_arbitrage_demo
   
   # Получение предметов для режима "Разгон баланса"
   boost_items = arbitrage_boost("csgo")
   
   # Запуск демонстрации арбитража
   await auto_arbitrage_demo(game="csgo", mode="medium", iterations=3) 