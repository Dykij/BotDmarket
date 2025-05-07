.. DMarket Bot documentation master file

====================================
Документация проекта DMarket Bot
====================================

.. image:: _static/dmarket_logo.png
   :alt: DMarket Logo
   :align: center
   :width: 150px

**DMarket Bot** - это Telegram-бот для автоматического арбитража на платформе DMarket.

Бот позволяет анализировать рынок, находить возможности для арбитража и автоматически
выполнять операции купли-продажи для получения прибыли.

Содержание
==========

.. toctree::
   :maxdepth: 2
   :caption: Руководство пользователя

   user/installation
   user/quickstart
   user/configuration

.. toctree::
   :maxdepth: 2
   :caption: Компоненты системы
   
   modules/dmarket/index
   modules/telegram_bot/index
   modules/utils/index

.. toctree::
   :maxdepth: 1
   :caption: Разработка
   
   dev/contributing
   dev/testing
   dev/deployment

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