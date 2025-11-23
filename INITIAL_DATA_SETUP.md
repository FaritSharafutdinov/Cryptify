# Первоначальная настройка данных на сервере

## Проблема
Фронтенд показывает мок-данные, потому что в базе данных нет реальных данных.

## Решение: Запустить сбор данных и генерацию прогнозов

### Шаг 1: Проверить, что бэкенд работает

```bash
# Проверить статус контейнеров
docker-compose ps

# Проверить health endpoint
curl http://localhost:8000/health
```

Должен вернуть: `{"status":"healthy",...}`

### Шаг 2: Собрать исторические данные

**Важно:** Это может занять 10-30 минут в зависимости от объема данных.

```bash
# Запустить полный сбор данных (исторические данные)
curl -X POST http://localhost:8000/ml/data-collector/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "full", "timeout": 3600}'
```

**Режимы:**
- `"full"` - полный сбор исторических данных (рекомендуется для первого запуска)
- `"incremental"` - только новые данные (для регулярных обновлений)

**Проверка прогресса:**
```bash
# Смотреть логи бэкенда
docker-compose logs -f backend

# Или проверить количество записей в БД (если есть доступ к psql)
docker-compose exec db psql -U postgres -d cryptify -c "SELECT COUNT(*) FROM raw_bars;"
```

### Шаг 3: Обучить модели (если еще не обучены)

**Важно:** Это может занять 30-60 минут.

```bash
# Запустить обучение моделей
curl -X POST http://localhost:8000/ml/trainer/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "full", "timeout": 7200}'
```

**Режимы:**
- `"full"` - полное обучение с нуля
- `"incremental"` - дообучение на новых данных

**Проверка:**
```bash
# Проверить, что модели сохранены
ls -la scripts/models/
# Должны быть файлы: LinearRegression_*.pkl, XGBoost_*.pkl, LSTM_*.h5
```

### Шаг 4: Сгенерировать прогнозы

После того как данные собраны и модели обучены:

```bash
# Запустить генерацию прогнозов
curl -X POST http://localhost:8000/ml/predictor/run \
  -H "Content-Type: application/json" \
  -d '{"timeout": 300}'
```

Это должно занять 1-5 минут.

### Шаг 5: Проверить данные в БД

```bash
# Проверить количество raw_bars
curl "http://localhost:8000/history" | jq '.metadata.bars_count'

# Проверить количество predictions
curl "http://localhost:8000/history" | jq '.metadata.predictions_count'
```

Или через API напрямую:
```bash
# Получить последние данные
curl "http://localhost:8000/history?from_time=$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S)&to_time=$(date -u +%Y-%m-%dT%H:%M:%S)" | jq '.'
```

### Шаг 6: Обновить фронтенд

После того как данные собраны:

1. Обновите страницу в браузере (Ctrl+Shift+R)
2. Проверьте, что показывается "Real" вместо "Mock"
3. Проверьте, что график показывает реальные данные BTC

## Автоматизация

После первоначальной настройки, данные будут обновляться автоматически через cron:

- **Каждый час:** сбор новых данных (`run_data_collector.sh`)
- **Каждое воскресенье в 2:00:** дообучение моделей (`run_model_trainer.sh`)

Проверить cron jobs:
```bash
crontab -l
```

## Устранение проблем

### Если data_collector не запускается:

```bash
# Проверить логи
docker-compose logs backend | grep -i "data-collector"

# Проверить, что скрипты доступны
docker-compose exec backend ls -la /scripts/
```

### Если trainer не запускается:

```bash
# Проверить логи
docker-compose logs backend | grep -i "trainer"

# Проверить наличие данных для обучения
docker-compose exec db psql -U postgres -d cryptify -c "SELECT COUNT(*) FROM btc_features_1h;"
```

### Если predictor не генерирует прогнозы:

```bash
# Проверить логи
docker-compose logs backend | grep -i "predictor"

# Проверить наличие моделей
docker-compose exec backend ls -la /scripts/models/
```

### Если фронтенд всё ещё показывает моки:

1. **Проверить, что бэкенд возвращает данные:**
```bash
curl "http://localhost:8000/history" | jq '.metadata'
```

2. **Проверить консоль браузера (F12):**
   - Ошибки сети?
   - Правильный URL запроса?

3. **Проверить прокси в vite.config.ts:**
   - Должен быть `target: 'http://localhost:8000'`

4. **Перезапустить фронтенд:**
```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

## Быстрая проверка всего пайплайна

```bash
# 1. Проверить бэкенд
curl http://localhost:8000/health

# 2. Запустить сбор данных (в фоне)
curl -X POST http://localhost:8000/ml/data-collector/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "full", "timeout": 3600}' &

# 3. Подождать завершения (проверять логи)
docker-compose logs -f backend | grep -i "data-collector"

# 4. Обучить модели
curl -X POST http://localhost:8000/ml/trainer/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "full", "timeout": 7200}'

# 5. Сгенерировать прогнозы
curl -X POST http://localhost:8000/ml/predictor/run \
  -H "Content-Type: application/json" \
  -d '{"timeout": 300}'

# 6. Проверить результат
curl "http://localhost:8000/history" | jq '.metadata'
```

## Ожидаемый результат

После выполнения всех шагов:

```json
{
  "metadata": {
    "bars_count": 168,  // или больше (зависит от периода)
    "predictions_count": 9  // 3 модели × 3 горизонта (6h, 12h, 24h)
  }
}
```

И фронтенд должен показывать:
- ✅ "Real" вместо "Mock"
- ✅ Реальные цены BTC на графике
- ✅ Прогнозы от ML моделей

