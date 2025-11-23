# Исправление ошибки numpy/scikit-learn на сервере

## Проблема
```
ValueError: numpy.dtype size changed, may indicate binary incompatibility. 
Expected 96 from C header, got 88 from PyObject
```

## Причина
Несовместимость версий numpy и scikit-learn из-за того, что scikit-learn был скомпилирован с другой версией numpy.

## Решение

### Вариант 1: Пересобрать Docker контейнер (рекомендуется)

```bash
# Остановить контейнеры
docker-compose down

# Пересобрать образ с исправленными зависимостями
docker-compose build --no-cache backend

# Запустить заново
docker-compose up -d

# Проверить, что всё работает
docker-compose logs backend | tail -20
```

### Вариант 2: Исправить в запущенном контейнере (быстрое решение)

```bash
# Войти в контейнер
docker-compose exec backend bash

# Переустановить numpy и scikit-learn
pip install --force-reinstall --no-cache-dir numpy==1.26.3 scikit-learn==1.4.0

# Выйти из контейнера
exit

# Перезапустить контейнер
docker-compose restart backend
```

### Вариант 3: Обновить код и пересобрать

```bash
# На локальной машине (уже сделано):
# - Обновлен scripts/requirements.txt
# - Обновлен backend/Dockerfile

# На сервере:
cd ~/projects/cryptify
git pull origin dev

# Пересобрать контейнер
docker-compose build --no-cache backend
docker-compose up -d
```

## Проверка

После исправления проверьте:

```bash
# Проверить версии в контейнере
docker-compose exec backend python -c "import numpy; import sklearn; print(f'numpy: {numpy.__version__}, sklearn: {sklearn.__version__}')"

# Попробовать запустить trainer
curl -X POST http://localhost:8000/ml/trainer/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "full", "timeout": 7200}'
```

## Ожидаемый результат

Должно работать без ошибок. Если всё ок, вы увидите в логах:
```
✅ Модели успешно обучены
```

