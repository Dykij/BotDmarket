# Использовать Alpine Linux для минимизации уязвимостей
FROM python:alpine

# Установка рабочей директории внутри контейнера
WORKDIR /app

# Установка зависимостей для сборки C-расширений при необходимости
RUN apk add --no-cache gcc musl-dev linux-headers

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода приложения
COPY . .

# Переменные среды для API ключей (заполнить через docker-compose или при запуске)
ENV DMARKET_PUBLIC_KEY=""
ENV DMARKET_SECRET_KEY=""
ENV TELEGRAM_BOT_TOKEN=""

# Запуск приложения
CMD ["python", "main.py"]
