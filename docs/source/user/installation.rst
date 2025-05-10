.. _installation:

Установка
========

Этот раздел содержит инструкции по установке и настройке DMarket Bot.

Требования
---------

Для работы DMarket Bot требуются следующие компоненты:

* Python 3.10 или выше
* Зарегистрированный Telegram Bot (через BotFather)
* Учетная запись DMarket с API ключами

Установка из Git репозитория
---------------------------

1. Клонируйте репозиторий:

   .. code-block:: bash

      git clone https://github.com/yourusername/dmarket-bot.git
      cd dmarket-bot

2. Создайте и активируйте виртуальное окружение:

   .. code-block:: bash

      # На Windows
      python -m venv venv
      venv\Scripts\activate

      # На macOS/Linux
      python3 -m venv venv
      source venv/bin/activate

3. Установите необходимые зависимости:

   .. code-block:: bash

      pip install -r requirements.txt

4. Создайте файл с переменными окружения:

   .. code-block:: bash

      cp .env.example .env

5. Откройте файл `.env` в текстовом редакторе и настройте необходимые параметры:

   .. code-block:: text

      TELEGRAM_BOT_TOKEN=your_telegram_bot_token
      DMARKET_PUBLIC_KEY=your_dmarket_public_key
      DMARKET_SECRET_KEY=your_dmarket_secret_key

Установка с помощью Docker
-------------------------

1. Убедитесь, что Docker и Docker Compose установлены на вашей системе.

2. Клонируйте репозиторий:

   .. code-block:: bash

      git clone https://github.com/yourusername/dmarket-bot.git
      cd dmarket-bot

3. Создайте файл с переменными окружения:

   .. code-block:: bash

      cp .env.example .env

4. Отредактируйте файл `.env` с вашими настройками.

5. Запустите контейнер:

   .. code-block:: bash

      docker-compose up -d

   Это создаст и запустит контейнер с ботом в фоновом режиме.

Проверка установки
-----------------

После установки можно проверить работоспособность бота:

1. Запустите бота:

   .. code-block:: bash

      python run_bot.py

2. Найдите вашего бота в Telegram и отправьте команду `/start`.

3. Бот должен ответить приветственным сообщением и предоставить основные команды.

Поздравляем! DMarket Bot успешно установлен. 