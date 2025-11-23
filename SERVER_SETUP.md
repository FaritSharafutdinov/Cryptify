# Полный алгоритм запуска проекта на новом сервере

## 📋 Шаг 1: Подключение к серверу

```bash
ssh user@your-server-ip
# Например: ssh root@89.104.67.225
```

## 🔧 Шаг 2: Установка необходимого ПО

### 2.1 Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### 2.2 Установка Docker

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Перезайти в систему или выполнить:
newgrp docker

# Проверка
docker --version
```

### 2.3 Установка Docker Compose

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверка
docker-compose --version
```

### 2.4 Установка Node.js (для фронтенда)

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Проверка
node --version
npm --version
```

### 2.5 Установка Git (если не установлен)

```bash
sudo apt install git -y
```

## 📥 Шаг 3: Клонирование проекта

```bash
# Перейти в домашнюю директорию или создать директорию для проектов
cd ~
mkdir -p projects
cd projects

# Клонировать репозиторий
git clone <YOUR_GITHUB_REPO_URL> cryptify
cd cryptify

# Переключиться на нужную ветку (если не main)
git checkout dev
```

## 🐳 Шаг 4: Запуск бэкенда (Docker)

```bash
# Запустить PostgreSQL и FastAPI бэкенд
docker-compose up -d

# Проверить статус
docker-compose ps

# Просмотр логов (опционально)
docker-compose logs -f backend
```

**Проверка бэкенда:**
```bash
curl http://localhost:8000/health
```

Должен вернуть: `{"status":"healthy",...}`

## 🎨 Шаг 5: Запуск фронтенда

```bash
# Перейти в папку фронтенда
cd frontend

# Установить зависимости (первый раз)
npm install

# Запустить dev сервер
npm run dev -- --host 0.0.0.0
```

**Фронтенд будет доступен на:** `http://YOUR_SERVER_IP:5173`

## 🔥 Шаг 6: Настройка Firewall (если нужно)

```bash
# Разрешить порты
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (для Nginx)
sudo ufw allow 443/tcp   # HTTPS (для Nginx)
sudo ufw allow 5173/tcp  # Frontend dev server
sudo ufw allow 8000/tcp  # Backend API (опционально)

# Включить firewall
sudo ufw enable

# Проверить статус
sudo ufw status
```

## 📊 Шаг 7: Первоначальная настройка данных

### 7.1 Сбор исторических данных

```bash
# Это может занять 10-30 минут
curl -X POST http://localhost:8000/ml/data-collector/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "full", "timeout": 3600}'
```

### 7.2 Обучение моделей

```bash
# Это может занять 30-60 минут
curl -X POST http://localhost:8000/ml/trainer/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "full", "timeout": 7200}'
```

### 7.3 Генерация прогнозов

```bash
curl -X POST http://localhost:8000/ml/predictor/run \
  -H "Content-Type: application/json" \
  -d '{"timeout": 300}'
```

## ⏰ Шаг 8: Настройка автоматизации (Cron)

```bash
# Вернуться в корень проекта
cd ~/projects/cryptify

# Настроить cron jobs
./scripts/setup_cron.sh

# Проверить
crontab -l
```

## 🌐 Шаг 9: Настройка Nginx (опционально, для production)

### 9.1 Установка Nginx

```bash
sudo apt install nginx -y
```

### 9.2 Создание конфигурации

```bash
sudo nano /etc/nginx/sites-available/cryptify
```

Добавить:

```nginx
server {
    listen 80;
    server_name YOUR_SERVER_IP;  # или ваш домен

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

### 9.3 Активация конфигурации

```bash
sudo ln -s /etc/nginx/sites-available/cryptify /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## ✅ Шаг 10: Проверка работы

```bash
# Проверить бэкенд
curl http://localhost:8000/health

# Проверить фронтенд
curl http://localhost:5173

# Проверить данные
curl http://localhost:8000/history | head -20
```

## 🔄 Запуск фронтенда в фоне (для постоянной работы)

### Вариант 1: Screen

```bash
# Установить screen (если нет)
sudo apt install screen -y

# Создать новую сессию
screen -S frontend

# Запустить фронтенд
cd ~/projects/cryptify/frontend
npm run dev -- --host 0.0.0.0

# Отсоединиться: Ctrl+A, затем D
# Подключиться обратно: screen -r frontend
```

### Вариант 2: Systemd service (рекомендуется для production)

Создать файл `/etc/systemd/system/cryptify-frontend.service`:

```ini
[Unit]
Description=Cryptify Frontend
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/projects/cryptify/frontend
ExecStart=/usr/bin/npm run dev -- --host 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активация:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cryptify-frontend
sudo systemctl start cryptify-frontend
sudo systemctl status cryptify-frontend
```

## 📝 Полезные команды

```bash
# Просмотр логов бэкенда
docker-compose logs -f backend

# Перезапуск бэкенда
docker-compose restart backend

# Остановка всех сервисов
docker-compose down

# Просмотр логов cron
tail -f ~/projects/cryptify/logs/cron_data_collector.log
tail -f ~/projects/cryptify/logs/cron_model_trainer.log

# Проверка статуса контейнеров
docker-compose ps

# Использование ресурсов
docker stats
```

## 🎯 Итоговый чеклист

- [ ] Docker установлен и работает
- [ ] Docker Compose установлен
- [ ] Node.js установлен
- [ ] Проект клонирован
- [ ] Бэкенд запущен (`docker-compose up -d`)
- [ ] Бэкенд отвечает (`curl http://localhost:8000/health`)
- [ ] Фронтенд запущен (`npm run dev`)
- [ ] Фронтенд доступен по IP:5173
- [ ] Данные собраны
- [ ] Модели обучены
- [ ] Cron jobs настроены
- [ ] Firewall настроен (если нужен)

## 🔗 Доступ к проекту

После выполнения всех шагов:

- **Фронтенд:** `http://YOUR_SERVER_IP:5173`
- **Backend API:** `http://YOUR_SERVER_IP:8000`
- **API Docs:** `http://YOUR_SERVER_IP:8000/docs`

Если настроен Nginx:
- **Фронтенд:** `http://YOUR_SERVER_IP` (через Nginx)

