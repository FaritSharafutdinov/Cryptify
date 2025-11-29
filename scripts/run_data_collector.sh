#!/bin/bash
# Скрипт для автоматического сбора данных
# Используется в cron для запуска каждый час

set -e

# Получаем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Логирование
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/data_collector_$(date +%Y%m%d_%H%M%S).log"

# Переменные окружения (для локального запуска скриптов напрямую, не через Docker)
# В production используем API бэкенда, поэтому эти переменные не нужны
# export DATABASE_URL="postgresql://criptify_user:criptify_password@localhost:5432/criptify_db"
# export DOCKER_ENV="false"

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Запуск data_collector ==="
log "Директория проекта: $PROJECT_DIR"
log "Лог файл: $LOG_FILE"

# Проверяем, запущен ли Docker
if ! docker ps > /dev/null 2>&1; then
    log "ОШИБКА: Docker не запущен"
    exit 1
fi

# Запускаем data_collector через API бэкенда
log "Отправка запроса на сбор данных..."
RESPONSE=$(curl -s -X POST 'http://localhost:8000/ml/data-collector/run' \
    -H 'Content-Type: application/json' \
    -d '{"mode": "incremental", "timeout": 1800}' \
    -w "\nHTTP_CODE:%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    log "✅ Сбор данных успешно запущен"
    echo "$BODY" | python3 -m json.tool 2>/dev/null | tee -a "$LOG_FILE" || echo "$BODY" | tee -a "$LOG_FILE"
    # Примечание: predictor теперь запускается отдельным cron job в 5 минут каждого часа
    # Это обеспечивает независимость и надежность обновления прогнозов
else
    log "❌ Ошибка при сборе данных: HTTP $HTTP_CODE"
    echo "$BODY" | tee -a "$LOG_FILE"
    exit 1
fi

log "=== Завершение data_collector ==="

