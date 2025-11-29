#!/bin/bash
# Скрипт для настройки cron jobs
# Запускать от имени пользователя, который будет выполнять задачи

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DATA_COLLECTOR_SCRIPT="$SCRIPT_DIR/run_data_collector.sh"
PREDICTOR_SCRIPT="$SCRIPT_DIR/run_predictor.sh"
TRAINER_SCRIPT="$SCRIPT_DIR/run_model_trainer.sh"

echo "=== Настройка Cron Jobs ==="
echo ""

# Проверяем существование скриптов
if [ ! -f "$DATA_COLLECTOR_SCRIPT" ]; then
    echo "❌ Ошибка: Скрипт $DATA_COLLECTOR_SCRIPT не найден"
    exit 1
fi

if [ ! -f "$PREDICTOR_SCRIPT" ]; then
    echo "❌ Ошибка: Скрипт $PREDICTOR_SCRIPT не найден"
    exit 1
fi

if [ ! -f "$TRAINER_SCRIPT" ]; then
    echo "❌ Ошибка: Скрипт $TRAINER_SCRIPT не найден"
    exit 1
fi

# Создаем временный файл для cron
CRON_TMP=$(mktemp)

# Сохраняем текущие cron jobs
crontab -l > "$CRON_TMP" 2>/dev/null || true

# Удаляем старые записи для наших скриптов (если есть)
sed -i.bak "\|$DATA_COLLECTOR_SCRIPT|d" "$CRON_TMP"
sed -i.bak "\|$PREDICTOR_SCRIPT|d" "$CRON_TMP"
sed -i.bak "\|$TRAINER_SCRIPT|d" "$CRON_TMP"
rm -f "${CRON_TMP}.bak"

# Добавляем новые cron jobs
echo "" >> "$CRON_TMP"
echo "# Cryptify: Data collection every hour" >> "$CRON_TMP"
echo "0 * * * * $DATA_COLLECTOR_SCRIPT >> $PROJECT_DIR/logs/cron_data_collector.log 2>&1" >> "$CRON_TMP"
echo "" >> "$CRON_TMP"
echo "# Cryptify: Prediction generation every hour (5 minutes after data collection)" >> "$CRON_TMP"
echo "5 * * * * $PREDICTOR_SCRIPT >> $PROJECT_DIR/logs/cron_predictor.log 2>&1" >> "$CRON_TMP"
echo "" >> "$CRON_TMP"
echo "# Cryptify: Model retraining every 7 days (Sunday at 2 AM)" >> "$CRON_TMP"
echo "0 2 * * 0 $TRAINER_SCRIPT >> $PROJECT_DIR/logs/cron_model_trainer.log 2>&1" >> "$CRON_TMP"

# Устанавливаем новые cron jobs
crontab "$CRON_TMP"
rm "$CRON_TMP"

echo "✅ Cron jobs успешно настроены:"
echo ""
echo "1. Сбор данных: каждый час (0 минут каждого часа)"
echo "   $DATA_COLLECTOR_SCRIPT"
echo ""
echo "2. Генерация прогнозов: каждый час (5 минут каждого часа)"
echo "   $PREDICTOR_SCRIPT"
echo ""
echo "3. Дообучение моделей: каждое воскресенье в 2:00"
echo "   $TRAINER_SCRIPT"
echo ""
echo "Проверить cron jobs: crontab -l"
echo "Логи: $PROJECT_DIR/logs/"

