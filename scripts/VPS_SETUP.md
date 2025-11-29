# Настройка на VPS

## 🚀 Быстрая настройка

### 1. Убедитесь, что все скрипты имеют права на выполнение

```bash
chmod +x scripts/*.sh
```

### 2. Настройте cron jobs

```bash
cd /path/to/cryptify
./scripts/setup_cron.sh
```

### 3. Проверьте настройку cron

```bash
crontab -l
```

Должны быть видны три задачи:
- `0 * * * *` - сбор данных каждый час
- `5 * * * *` - генерация прогнозов каждый час
- `0 2 * * 0` - дообучение моделей каждое воскресенье

## 🔍 Диагностика проблем

### Проблема: Cron jobs не выполняются

1. **Проверьте права на скрипты:**
   ```bash
   ls -la scripts/*.sh
   chmod +x scripts/*.sh
   ```

2. **Проверьте пути в crontab (должны быть абсолютные):**
   ```bash
   crontab -l
   ```
   Если пути относительные, исправьте вручную:
   ```bash
   crontab -e
   ```

3. **Проверьте системные логи cron:**
   ```bash
   # Ubuntu/Debian
   sudo tail -f /var/log/syslog | grep CRON
   
   # CentOS/RHEL
   sudo tail -f /var/log/cron
   ```

4. **Проверьте логи скриптов:**
   ```bash
   tail -f logs/cron_data_collector.log
   tail -f logs/cron_predictor.log
   ```

### Проблема: Backend API недоступен

1. **Проверьте, что Docker контейнеры запущены:**
   ```bash
   docker-compose ps
   ```

2. **Проверьте здоровье API:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Проверьте логи бэкенда:**
   ```bash
   docker-compose logs backend
   ```

### Проблема: Недостаточно данных

Если при первом запуске нет данных:

1. **Запустите полный сбор данных вручную:**
   ```bash
   curl -X POST 'http://localhost:8000/ml/data-collector/run' \
     -H 'Content-Type: application/json' \
     -d '{"mode": "batch", "timeout": 3600}'
   ```

2. **После сбора данных запустите predictor:**
   ```bash
   curl -X POST 'http://localhost:8000/ml/predictor/run' \
     -H 'Content-Type: application/json' \
     -d '{"timeout": 300}'
   ```

### Проблема: Прогнозы не обновляются каждый час

1. **Проверьте, что cron job для predictor настроен:**
   ```bash
   crontab -l | grep predictor
   ```

2. **Проверьте логи predictor:**
   ```bash
   tail -f logs/cron_predictor.log
   ```

3. **Запустите predictor вручную для проверки:**
   ```bash
   ./scripts/run_predictor.sh
   ```

## 📝 Ручная настройка cron (если setup_cron.sh не работает)

1. Откройте crontab:
   ```bash
   crontab -e
   ```

2. Добавьте следующие строки (замените `/path/to/cryptify` на реальный путь):
   ```cron
   # Cryptify: Data collection every hour
   0 * * * * /path/to/cryptify/scripts/run_data_collector.sh >> /path/to/cryptify/logs/cron_data_collector.log 2>&1
   
   # Cryptify: Prediction generation every hour
   5 * * * * /path/to/cryptify/scripts/run_predictor.sh >> /path/to/cryptify/logs/cron_predictor.log 2>&1
   
   # Cryptify: Model retraining every 7 days
   0 2 * * 0 /path/to/cryptify/scripts/run_model_trainer.sh >> /path/to/cryptify/logs/cron_model_trainer.log 2>&1
   ```

3. Сохраните и закройте редактор.

## ✅ Проверка работы

После настройки проверьте:

1. **Cron jobs настроены:**
   ```bash
   crontab -l
   ```

2. **Логи создаются:**
   ```bash
   ls -la logs/
   ```

3. **Скрипты работают вручную:**
   ```bash
   ./scripts/run_data_collector.sh
   ./scripts/run_predictor.sh
   ```

4. **Данные обновляются:**
   ```bash
   # Проверьте последние записи в БД через API
   curl http://localhost:8000/predictions/latest
   ```

## 🔧 Обновление после изменений

Если вы обновили скрипты:

1. Перезапустите cron jobs:
   ```bash
   ./scripts/setup_cron.sh
   ```

2. Или обновите вручную через `crontab -e`

