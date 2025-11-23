# Интеграция ML-части с Backend

## Обзор

Backend теперь полностью интегрирован с ML-пайплайном из папки `scripts/`. Все endpoints обновлены для работы с новой схемой базы данных.

## Обновленная схема базы данных

### Таблицы ML-пайплайна

1. **`btc_features_1h`** - Инженерные признаки BTC/USDT
   - Создается скриптом `data_collector.py`
   - Содержит все фичи для обучения моделей

2. **`predictions`** - Прогнозы моделей
   - Создается скриптом `predictor.py`
   - Структура: `(time, model_name, target_hours)` - составной первичный ключ
   - Поля: `prediction_log_return`, `ci_low`, `ci_high`

3. **`ml_models`** - Метрики моделей
   - Обновляется скриптом `multi_model_trainer.py`
   - Структура: `model_name` (PK), `metrics` (JSONB), `updated_at`

## Новые и обновленные API Endpoints

### 1. Получение прогнозов

**GET `/predictions/latest`**
- Возвращает последние прогнозы из ML-таблицы
- Параметры:
  - `limit` (default: 10) - количество записей
  - `model_name` (optional) - фильтр по модели
  - `horizon` (optional) - фильтр по горизонту (target_hours)
- Пример ответа:
```json
{
  "status": "success",
  "data": [
    {
      "time": "2024-01-01T12:00:00",
      "model_name": "LinearRegression",
      "target_hours": 6,
      "prediction_log_return": 0.001234,
      "ci_low": 0.000500,
      "ci_high": 0.002000,
      "predicted_time": "2024-01-01T18:00:00"
    }
  ],
  "count": 1
}
```

### 2. Получение метрик моделей

**GET `/metrics/latest`**
- Возвращает метрики из таблицы `ml_models`
- Параметры:
  - `model_name` (optional) - фильтр по модели
- Пример ответа:
```json
{
  "status": "success",
  "data": [
    {
      "model_name": "LinearRegression_log_return_6h",
      "metrics": {
        "mae": 0.000123,
        "mse": 0.000045
      },
      "updated_at": "2024-01-01T12:00:00"
    }
  ],
  "count": 1
}
```

### 3. Получение features

**GET `/features/latest`**
- Возвращает последние features из `btc_features_1h`
- Параметры:
  - `limit` (default: 100) - количество записей

**GET `/features`**
- Возвращает features за указанный период
- Параметры:
  - `from_time` (optional) - начало периода
  - `to_time` (optional) - конец периода
  - `limit` (default: 1000) - максимальное количество записей

### 4. Обновленный endpoint истории

**GET `/history`**
- Теперь возвращает данные из `btc_features_1h` и `predictions`
- Формат ответа обновлен для соответствия новой схеме

### 5. Список моделей

**GET `/models`**
- Возвращает список всех моделей из `ml_models`
- Включает метрики и дату обновления

## Обновленные модели БД

Все модели в `backend/models/database.py` обновлены:

- **`Prediction`** - соответствует схеме из `predictor.py`
- **`MLModel`** - соответствует схеме из `multi_model_trainer.py`
- **`BTCFeature`** - новая модель для таблицы `btc_features_1h`

## Инициализация базы данных

Файл `docker/init.sql` обновлен и создает:
- Все таблицы ML-пайплайна
- Индексы для оптимизации запросов
- Legacy таблицы для обратной совместимости

## Использование

### 1. Запуск ML-пайплайна

```bash
# Сбор данных
cd scripts
python data_collector.py

# Обучение моделей
python multi_model_trainer.py batch

# Прогнозирование
python predictor.py
```

### 2. Использование API

```bash
# Получить последние прогнозы
curl http://localhost:8000/predictions/latest?limit=10

# Получить прогнозы конкретной модели
curl http://localhost:8000/predictions/latest?model_name=LinearRegression&horizon=6

# Получить метрики моделей
curl http://localhost:8000/metrics/latest

# Получить последние features
curl http://localhost:8000/features/latest?limit=50
```

## Примечания

- Все временные метки в ML-таблицах используют `TIMESTAMP WITHOUT TIME ZONE` или `TIMESTAMP WITH TIME ZONE` в зависимости от таблицы
- Прогнозы сохраняются как `log_return` (логарифмическая доходность), а не абсолютная цена
- Доверительные интервалы (CI) включены в ответы для оценки неопределенности прогнозов

