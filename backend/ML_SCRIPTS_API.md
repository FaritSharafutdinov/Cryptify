# API для управления ML-скриптами

## Обзор

API предоставляет endpoints для запуска и мониторинга ML-скриптов из папки `scripts/`.

## Endpoints

### 1. Запуск ML-скрипта

**POST `/ml/scripts/run`**

Запускает любой ML-скрипт асинхронно.

**Тело запроса:**
```json
{
  "script_name": "data_collector.py",
  "args": [],
  "timeout": 1800
}
```

**Параметры:**
- `script_name` (required): Имя скрипта (data_collector.py, multi_model_trainer.py, predictor.py, inference.py)
- `args` (optional): Дополнительные аргументы командной строки
- `timeout` (optional): Таймаут выполнения в секундах (1-3600)

**Ответ:**
```json
{
  "script_name": "data_collector.py",
  "status": "completed",
  "return_code": 0,
  "stdout": "...",
  "stderr": "",
  "started_at": "2024-01-01T12:00:00",
  "completed_at": "2024-01-01T12:30:00"
}
```

### 2. Запуск сбора данных

**POST `/ml/data-collector/run`**

Запускает сбор данных (data_collector.py).

**Тело запроса:**
```json
{
  "mode": "incremental",
  "timeout": 1800
}
```

**Параметры:**
- `mode` (optional): Режим сбора - "batch" (полный) или "incremental" (инкрементальный). По умолчанию: "incremental"
- `timeout` (optional): Таймаут в секундах (60-3600). По умолчанию: 1800

### 3. Запуск обучения моделей

**POST `/ml/trainer/run`**

Запускает обучение моделей (multi_model_trainer.py).

**Тело запроса:**
```json
{
  "mode": "batch",
  "timeout": 3600
}
```

**Параметры:**
- `mode` (required): Режим обучения - "batch" (полное) или "retrain" (дообучение). По умолчанию: "batch"
- `timeout` (optional): Таймаут в секундах (60-7200). По умолчанию: 3600

### 4. Запуск прогнозирования

**POST `/ml/predictor/run`**

Запускает прогнозирование (predictor.py).

**Тело запроса:**
```json
{
  "timeout": 300
}
```

**Параметры:**
- `timeout` (optional): Таймаут в секундах (30-600). По умолчанию: 300

### 5. Получение статуса скрипта

**GET `/ml/scripts/status/{script_name}`**

Получает статус выполнения конкретного скрипта.

**Пример:**
```
GET /ml/scripts/status/data_collector.py
```

**Ответ:**
```json
{
  "status": "success",
  "data": {
    "status": "running",
    "started_at": "2024-01-01T12:00:00",
    "command": "python data_collector.py"
  }
}
```

### 6. Получение статусов всех скриптов

**GET `/ml/scripts/status`**

Получает статусы всех запущенных скриптов.

**Ответ:**
```json
{
  "status": "success",
  "data": {
    "data_collector.py": {
      "status": "completed",
      "started_at": "2024-01-01T12:00:00",
      "completed_at": "2024-01-01T12:30:00"
    }
  },
  "count": 1
}
```

### 7. Список доступных скриптов

**GET `/ml/scripts/available`**

Возвращает список всех доступных ML-скриптов.

**Ответ:**
```json
{
  "status": "success",
  "data": [
    "data_collector.py",
    "multi_model_trainer.py",
    "predictor.py",
    "inference.py"
  ],
  "count": 4
}
```

### 8. Отмена выполнения скрипта

**POST `/ml/scripts/{script_name}/cancel`**

Отменяет выполнение запущенного скрипта.

**Пример:**
```
POST /ml/scripts/data_collector.py/cancel
```

**Ответ:**
```json
{
  "status": "success",
  "message": "Скрипт data_collector.py отменен"
}
```

## Статусы выполнения

- `pending` - Ожидает запуска
- `running` - Выполняется
- `completed` - Успешно завершен
- `failed` - Завершен с ошибкой
- `cancelled` - Отменен

## Обработка ошибок

Все endpoints возвращают стандартизированные ошибки:

```json
{
  "status": "error",
  "error": "Описание ошибки",
  "timestamp": "2024-01-01T12:00:00",
  "details": {
    "additional_info": "..."
  }
}
```

**Коды HTTP:**
- `400` - Ошибка валидации данных
- `404` - Ресурс не найден
- `409` - Конфликт (скрипт уже выполняется)
- `422` - Ошибка валидации Pydantic
- `500` - Внутренняя ошибка сервера

## Примеры использования

### Запуск полного сбора данных

```bash
curl -X POST http://localhost:8000/ml/data-collector/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "batch", "timeout": 3600}'
```

### Запуск обучения моделей

```bash
curl -X POST http://localhost:8000/ml/trainer/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "batch", "timeout": 3600}'
```

### Проверка статуса

```bash
curl http://localhost:8000/ml/scripts/status/data_collector.py
```

### Отмена выполнения

```bash
curl -X POST http://localhost:8000/ml/scripts/data_collector.py/cancel
```

## Безопасность

- Валидация имен скриптов (только разрешенные скрипты)
- Валидация аргументов (защита от инъекций)
- Ограничение таймаутов
- Логирование всех операций

## Примечания

- Скрипты выполняются асинхронно
- Один скрипт не может быть запущен дважды одновременно
- Статусы сохраняются в памяти (при перезапуске сервера теряются)
- Для production рекомендуется использовать внешнюю систему очередей (Celery, RQ)

