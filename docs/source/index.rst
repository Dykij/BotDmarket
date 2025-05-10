.. DMarket Bot documentation master file

DMarket Bot Documentation
========================

DMarket Bot - это Telegram-бот для торговли игровыми предметами на платформе DMarket.

.. toctree::
   :maxdepth: 2
   :caption: Пользовательская документация

   user/installation
   user/configuration
   user/usage
   user/troubleshooting

.. toctree::
   :maxdepth: 2
   :caption: Руководство разработчика

   dev/architecture
   dev/codebase
   dev/api
   dev/testing
   dev/deployment
   dev/contributing

.. toctree::
   :maxdepth: 2
   :caption: API и модули

   modules/telegram_bot/index
   modules/dmarket/index
   modules/utils/index

.. toctree::
   :maxdepth: 1
   :caption: Дополнительно

   refactoring
   improvements
   performance
   changelog

Индексы и таблицы
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Быстрый старт
=============

1. Установите зависимости:

.. code-block:: bash

   pip install -r requirements.txt

2. Настройте переменные окружения:

.. code-block:: bash

   cp .env.example .env
   # Отредактируйте .env файл, добавив API ключи DMarket и токен Telegram

3. Запустите бота:

.. code-block:: bash

   python run.py 