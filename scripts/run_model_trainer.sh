#!/bin/bash
# Скрипт для автоматического дообучения моделей
# Используется в cron для запуска каждые 7 дней

set -e

# Получаем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Логирование
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/model_trainer_$(date +%Y%m%d_%H%M%S).log"

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Запуск model_trainer ==="
log "Директория проекта: $PROJECT_DIR"
log "Лог файл: $LOG_FILE"

# Проверяем, запущен ли Docker
if ! docker ps > /dev/null 2>&1; then
    log "ОШИБКА: Docker не запущен"
    exit 1
fi

# Запускаем trainer через API бэкенда
log "Отправка запроса на дообучение моделей..."
RESPONSE=$(curl -s -X POST 'http://localhost:8000/ml/trainer/run' \
    -H 'Content-Type: application/json' \
    -d '{"mode": "retrain", "timeout": 7200}' \
    -w "\nHTTP_CODE:%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    log "✅ Дообучение моделей успешно запущено"
    echo "$BODY" | python3 -m json.tool | tee -a "$LOG_FILE"
    
    # После обучения запускаем predictor для обновления прогнозов
    log "Запуск predictor для обновления прогнозов..."
    PRED_RESPONSE=$(curl -s -X POST 'http://localhost:8000/ml/predictor/run' \
        -H 'Content-Type: application/json' \
        -d '{"timeout": 300}' \
        -w "\nHTTP_CODE:%{http_code}")
    
    PRED_HTTP_CODE=$(echo "$PRED_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    PRED_BODY=$(echo "$PRED_RESPONSE" | sed '/HTTP_CODE:/d')
    
    if [ "$PRED_HTTP_CODE" = "200" ]; then
        log "✅ Прогнозы успешно обновлены"
        echo "$PRED_BODY" | python3 -m json.tool | tee -a "$LOG_FILE"
    else
        log "⚠️ Ошибка при обновлении прогнозов: HTTP $PRED_HTTP_CODE"
        echo "$PRED_BODY" | tee -a "$LOG_FILE"
    fi
else
    log "❌ Ошибка при дообучении моделей: HTTP $HTTP_CODE"
    echo "$BODY" | tee -a "$LOG_FILE"
    exit 1
fi

log "=== Завершение model_trainer ==="

