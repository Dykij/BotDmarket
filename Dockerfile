# Использовать Alpine Linux для минимизации уязвимостей
FROM python:3.11-slim

# Установка рабочей директории внутри контейнера
WORKDIR /app

# Установка зависимостей для сборки C-расширений при необходимости
RUN apk add --no-cache gcc musl-dev linux-headers

# Создание директории для логов
RUN mkdir -p /app/logs /app/data

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
ENV DMARKET_API_URL="https://api.dmarket.com"
ENV PYTHONPATH="/app"
ENV LOG_LEVEL="INFO"

# Use a non-root user for better security
RUN useradd -m botuser && \
    chown -R botuser:botuser /app
USER botuser

# Запуск приложения
CMD ["python", "-m", "src"]
