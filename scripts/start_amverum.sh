#!/bin/sh
# Запуск бэкенда (FastAPI) и бота в одном контейнере на Amverum Cloud.
# Бэкенд слушает порт из переменной PORT (по умолчанию 8000).

set -e
PORT="${PORT:-8000}"

# Запуск uvicorn в фоне (бэкенд API)
uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT" &
UVICORN_PID=$!

# Даём API пару секунд на старт
sleep 3

# Бот обращается к API по localhost (то же контейнер)
export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:$PORT}"
exec python -m bot.bot
