#!/bin/sh
# Формируем config.json из переменной BACKEND_URL и запускаем nginx

CONFIG_PATH="/usr/share/nginx/html/config.json"
if [ -n "$BACKEND_URL" ]; then
    # Убираем завершающий слэш
    URL=$(echo "$BACKEND_URL" | sed 's#/$##')
    echo "{\"backendUrl\": \"$URL\"}" > "$CONFIG_PATH"
fi

exec nginx -g "daemon off;"
