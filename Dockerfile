# Образ для деплоя бэкенда + Telegram-бота на Amverum Cloud
# Сборка из корня проекта: docker build -f Dockerfile.amverum -t carwash-amverum .

FROM python:3.12-slim

WORKDIR /app

# Зависимости системы (для asyncpg и т.п.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код приложения
COPY backend ./backend
COPY bot ./bot
COPY scripts/start_amverum.sh ./scripts/
RUN chmod +x ./scripts/start_amverum.sh

# Переменные окружения задаются в панели Amverum (не копируем .env)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Amverum может передавать PORT
EXPOSE 8000

CMD ["./scripts/start_amverum.sh"]
