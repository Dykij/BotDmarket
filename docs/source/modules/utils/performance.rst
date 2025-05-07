.. _performance_module:

=====================
Модуль performance
=====================

.. module:: src.utils.performance

Модуль предоставляет инструменты для оптимизации производительности приложения,
включая продвинутое кеширование и профилирование функций.

Классы
------

AdvancedCache
^^^^^^^^^^^^^

.. autoclass:: src.utils.performance.AdvancedCache
   :members:
   :special-members: __init__

AsyncBatch
^^^^^^^^^^

.. autoclass:: src.utils.performance.AsyncBatch
   :members:
   :special-members: __init__

Декораторы
----------

cached
^^^^^^

.. autofunction:: src.utils.performance.cached

Декоратор ``cached`` используется для кеширования результатов функций:

.. code-block:: python

   from src.utils.performance import cached
   
   @cached("my_cache", ttl=60)  # Кеш живет 60 секунд
   async def expensive_operation(param1, param2):
       # Эта функция будет выполняться только если результат не найден в кеше
       result = await some_slow_api_call(param1, param2)
       return result

profile_performance
^^^^^^^^^^^^^^^^^^

.. autofunction:: src.utils.performance.profile_performance

Декоратор ``profile_performance`` используется для замера времени выполнения функций:

.. code-block:: python

   from src.utils.performance import profile_performance
   
   @profile_performance
   async def my_function():
       # Выполнение функции
       result = await do_something()
       return result
   
   # При вызове функции в лог будет записано время её выполнения:
   # INFO: Время выполнения my_function: 0.1234 сек

Практические примеры
-------------------

Использование кеша и профилирования
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Пример оптимизации функции с использованием кеширования и профилирования:

.. code-block:: python

   from src.utils.performance import cached, profile_performance
   
   @profile_performance
   @cached("api_results", ttl=300)
   async def fetch_market_data(game_id, item_type):
       """Получить данные с рынка.
       
       Результаты кешируются на 5 минут (300 секунд).
       """
       # Выполнение запроса к API
       return await api_client.get_market_data(game_id, item_type)

Обработка пакетных асинхронных операций
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Пример использования AsyncBatch для оптимизации параллельных запросов:

.. code-block:: python

   from src.utils.performance import AsyncBatch
   
   async def process_multiple_items(items):
       # Создаем экземпляр для выполнения максимум 5 запросов одновременно
       batch = AsyncBatch(max_concurrent=5)
       
       # Создаем задачи
       tasks = [process_item(item) for item in items]
       
       # Выполняем задачи пакетами
       results = await batch.execute(tasks)
       
       return results 