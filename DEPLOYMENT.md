# Инструкция по деплою на виртуальный сервер

## 📋 Требования

- Ubuntu 20.04+ / Debian 11+ (или другой Linux дистрибутив)
- Docker и Docker Compose установлены
- Git установлен
- Минимум 4GB RAM, 20GB свободного места
- Открытые порты: 80, 443 (для веб-сервера), 8000 (опционально, для прямого доступа к API)

## 🚀 Шаг 1: Подготовка сервера

### 1.1 Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Установка Docker и Docker Compose

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перезайти в систему или выполнить:
newgrp docker
```

### 1.3 Установка Git (если не установлен)

```bash
sudo apt install git -y
```

## 📥 Шаг 2: Клонирование проекта

```bash
# Перейти в домашнюю директорию или создать директорию для проектов
cd ~
mkdir -p projects
cd projects

# Клонировать репозиторий
git clone <YOUR_GITHUB_REPO_URL> cryptify
cd cryptify
```

## ⚙️ Шаг 3: Настройка окружения

### 3.1 Настройка переменных окружения

```bash
# Создать .env файл для бэкенда (если нужно)
cd backend
cp env.example .env
nano .env  # Отредактировать при необходимости
cd ..
```

### 3.2 Настройка docker-compose.yml

Проверьте настройки в `docker-compose.yml`. Для production рекомендуется:
- Использовать переменные окружения для паролей БД
- Настроить volumes для персистентности данных
- Настроить restart policies

## 🐳 Шаг 4: Запуск сервисов

```bash
# Запустить все сервисы
docker-compose up -d

# Проверить статус
docker-compose ps

# Просмотр логов
docker-compose logs -f backend
```

## 🔄 Шаг 5: Настройка автоматизации

### 5.1 Настройка Cron Jobs

```bash
# Запустить скрипт настройки cron
./scripts/setup_cron.sh

# Проверить установленные cron jobs
crontab -l
```

### 5.2 Ручная настройка Cron (альтернатива)

Если скрипт не работает, настройте вручную:

```bash
crontab -e
```

Добавьте следующие строки:

```cron
# Сбор данных каждый час
0 * * * * /path/to/cryptify/scripts/run_data_collector.sh >> /path/to/cryptify/logs/cron_data_collector.log 2>&1

# Дообучение моделей каждое воскресенье в 2:00
0 2 * * 0 /path/to/cryptify/scripts/run_model_trainer.sh >> /path/to/cryptify/logs/cron_model_trainer.log 2>&1
```

**Важно:** Замените `/path/to/cryptify` на реальный путь к проекту.

## 🌐 Шаг 6: Настройка веб-сервера (Nginx)

### 6.1 Установка Nginx

```bash
sudo apt install nginx -y
```

### 6.2 Создание конфигурации Nginx

```bash
sudo nano /etc/nginx/sites-available/cryptify
```

Добавьте следующую конфигурацию:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Замените на ваш домен или IP

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6.3 Активация конфигурации

```bash
sudo ln -s /etc/nginx/sites-available/cryptify /etc/nginx/sites-enabled/
sudo nginx -t  # Проверка конфигурации
sudo systemctl restart nginx
```

## 🔒 Шаг 7: Настройка SSL (Let's Encrypt)

```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx -y

# Получение SSL сертификата
sudo certbot --nginx -d your-domain.com

# Автоматическое обновление сертификата
sudo certbot renew --dry-run
```

## 📊 Шаг 8: Первоначальная настройка данных

После первого запуска нужно собрать данные и обучить модели:

```bash
# Сбор исторических данных (может занять время)
curl -X POST http://localhost:8000/ml/data-collector/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "full", "timeout": 3600}'

# Обучение моделей
curl -X POST http://localhost:8000/ml/trainer/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "full", "timeout": 7200}'

# Генерация первых прогнозов
curl -X POST http://localhost:8000/ml/predictor/run \
  -H "Content-Type: application/json" \
  -d '{"timeout": 300}'
```

## 🔍 Шаг 9: Мониторинг и логи

### Просмотр логов

```bash
# Логи Docker контейнеров
docker-compose logs -f

# Логи cron jobs
tail -f logs/cron_data_collector.log
tail -f logs/cron_model_trainer.log

# Логи отдельных скриптов
ls -lh logs/
```

### Проверка статуса

```bash
# Статус контейнеров
docker-compose ps

# Использование ресурсов
docker stats

# Проверка здоровья API
curl http://localhost:8000/health
```

## 🔄 Обновление проекта

```bash
cd ~/projects/cryptify
git pull origin main
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 🛠️ Устранение неполадок

### Проблема: Cron jobs не выполняются

```bash
# Проверить логи cron
sudo tail -f /var/log/syslog | grep CRON

# Проверить права на скрипты
ls -l scripts/*.sh
chmod +x scripts/*.sh

# Проверить путь к скриптам в crontab
crontab -l
```

### Проблема: Docker контейнеры не запускаются

```bash
# Проверить логи
docker-compose logs

# Пересоздать контейнеры
docker-compose down
docker-compose up -d --force-recreate
```

### Проблема: Недостаточно места на диске

```bash
# Очистка неиспользуемых Docker образов
docker system prune -a

# Очистка старых логов
find logs/ -name "*.log" -mtime +30 -delete
```

## 📝 Полезные команды

```bash
# Перезапуск всех сервисов
docker-compose restart

# Остановка всех сервисов
docker-compose down

# Просмотр логов конкретного сервиса
docker-compose logs -f backend
docker-compose logs -f postgres

# Выполнение команд в контейнере
docker-compose exec backend bash
docker-compose exec postgres psql -U criptify_user -d criptify_db

# Резервное копирование БД
docker-compose exec postgres pg_dump -U criptify_user criptify_db > backup_$(date +%Y%m%d).sql

# Восстановление БД
docker-compose exec -T postgres psql -U criptify_user criptify_db < backup_YYYYMMDD.sql
```

## 🔐 Безопасность

1. **Измените пароли БД** в `docker-compose.yml` для production
2. **Используйте firewall** (ufw):
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```
3. **Регулярно обновляйте систему**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
4. **Настройте автоматические бэкапы БД**

## 📞 Поддержка

При возникновении проблем проверьте:
- Логи в `logs/`
- Логи Docker: `docker-compose logs`
- Статус сервисов: `docker-compose ps`
- Здоровье API: `curl http://localhost:8000/health`

