# Быстрый старт на сервере

## 🚀 Минимальные шаги для деплоя

### 1. Клонирование и запуск

```bash
# Клонировать проект
git clone <YOUR_REPO_URL> cryptify
cd cryptify

# Запустить сервисы
docker-compose up -d

# Проверить статус
docker-compose ps
```

### 2. Настройка автоматизации

```bash
# Настроить cron jobs (сбор данных каждый час, обучение каждые 7 дней)
./scripts/setup_cron.sh

# Проверить
crontab -l
```

### 3. Первоначальная настройка данных

```bash
# Собрать данные (может занять 10-30 минут)
curl -X POST http://localhost:8000/ml/data-collector/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "full", "timeout": 3600}'

# Обучить модели (может занять 30-60 минут)
curl -X POST http://localhost:8000/ml/trainer/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "full", "timeout": 7200}'

# Сгенерировать прогнозы
curl -X POST http://localhost:8000/ml/predictor/run \
  -H "Content-Type: application/json" \
  -d '{"timeout": 300}'
```

### 4. Настройка Nginx (опционально)

```bash
# Установить Nginx
sudo apt install nginx -y

# Создать конфигурацию (см. DEPLOYMENT.md)
sudo nano /etc/nginx/sites-available/cryptify

# Активировать
sudo ln -s /etc/nginx/sites-available/cryptify /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 📋 Расписание автоматизации

- **Сбор данных**: Каждый час (0 минут каждого часа)
- **Дообучение моделей**: Каждое воскресенье в 2:00

## 📊 Проверка работы

```bash
# Проверить здоровье API
curl http://localhost:8000/health

# Проверить логи cron
tail -f logs/cron_data_collector.log
tail -f logs/cron_model_trainer.log

# Проверить статус контейнеров
docker-compose ps
```

## 🔄 Обновление

```bash
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

Подробная инструкция: [DEPLOYMENT.md](DEPLOYMENT.md)

