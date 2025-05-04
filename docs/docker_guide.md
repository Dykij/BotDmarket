# Руководство по использованию Docker с BotDmarket

## Введение

Этот документ описывает процесс запуска BotDmarket в контейнере Docker для изоляции окружения и упрощения развертывания.

## Предварительные требования

- Docker Engine (версия 19.03.0+)
- Docker Compose (версия 1.27.0+)

## Быстрый старт

### 1. Настройка переменных окружения

Перед запуском необходимо настроить файл `.env` в корне проекта:

```bash
# Настройте свои API ключи
DMARKET_PUBLIC_KEY=your_public_key_here
DMARKET_SECRET_KEY=your_secret_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Опциональные настройки
LOG_LEVEL=INFO
ENABLE_AUTO_ARBITRAGE=false
```

### 2. Сборка и запуск контейнера

```bash
# Сборка образа
docker-compose build

# Запуск контейнера в фоновом режиме
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

### 3. Остановка контейнера

```bash
docker-compose down
```

## Структура Docker-конфигурации

### Dockerfile

Мы используем образ Alpine Linux для минимизации размера и повышения безопасности:

```dockerfile
FROM python:alpine
WORKDIR /app
RUN apk add --no-cache gcc musl-dev linux-headers
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### docker-compose.yml

```yaml
version: '3.8'
services:
  bot:
    build: .
    container_name: dmarket_bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./error_analytics.json:/app/error_analytics.json
    environment:
      - LOG_LEVEL=INFO
      - ENABLE_AUTO_ARBITRAGE=false
```

## Управление данными

По умолчанию логи и файл аналитики ошибок сохраняются через тома (volumes) в локальную директорию на хост-машине.

## Возможные проблемы и их решения

### Проблема с правами доступа к файлам логов

Если возникают проблемы с записью логов, выполните:

```bash
mkdir -p logs
chmod 777 logs
```

### Ошибки сборки C-расширений

При проблемах сборки Python-модулей с C-расширениями проверьте, что установлены необходимые пакеты в Dockerfile:

```dockerfile
RUN apk add --no-cache gcc musl-dev linux-headers
```

## Обновление контейнера

При обновлении кода:

```bash
git pull
docker-compose build
docker-compose down
docker-compose up -d
```

## Продвинутые настройки

### Мониторинг использования ресурсов

```bash
docker stats dmarket_bot
```

### Доступ к контейнеру

```bash
docker exec -it dmarket_bot sh
```
