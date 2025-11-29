#!/bin/bash
# Скрипт для автоматического запуска прогнозирования
# Используется в cron для запуска каждый час

set -e

# Получаем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Логирование
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/predictor_$(date +%Y%m%d_%H%M%S).log"

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Запуск predictor ==="
log "Директория проекта: $PROJECT_DIR"
log "Лог файл: $LOG_FILE"

# Проверяем, запущен ли Docker
if ! docker ps > /dev/null 2>&1; then
    log "ОШИБКА: Docker не запущен"
    exit 1
fi

# Проверяем доступность API
if ! curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    log "ОШИБКА: Backend API недоступен"
    exit 1
fi

# Запускаем predictor через API бэкенда
log "Отправка запроса на генерацию прогнозов..."
RESPONSE=$(curl -s -X POST 'http://localhost:8000/ml/predictor/run' \
    -H 'Content-Type: application/json' \
    -d '{"timeout": 300}' \
    -w "\nHTTP_CODE:%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    log "✅ Прогнозы успешно сгенерированы"
    echo "$BODY" | python3 -m json.tool 2>/dev/null | tee -a "$LOG_FILE" || echo "$BODY" | tee -a "$LOG_FILE"
else
    log "❌ Ошибка при генерации прогнозов: HTTP $HTTP_CODE"
    echo "$BODY" | tee -a "$LOG_FILE"
    exit 1
fi

log "=== Завершение predictor ==="

