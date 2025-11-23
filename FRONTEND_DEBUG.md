# Диагностика проблемы с мок-данными на сервере

## Проблема
Фронтенд показывает мок-данные вместо реальных данных с бэкенда.

## Причина
Фронтенд автоматически переключается на моки, если health check не проходит. Это было исправлено - теперь фронтенд всегда пытается использовать реальный API.

## Шаги для диагностики на сервере

### 1. Проверить, что бэкенд работает

```bash
# Проверить статус контейнеров
docker-compose ps

# Проверить логи бэкенда
docker-compose logs backend | tail -50

# Проверить health endpoint напрямую
curl http://localhost:8000/health
```

Должен вернуть: `{"status":"healthy",...}`

### 2. Проверить, что фронтенд может достучаться до бэкенда

На сервере, где запущен фронтенд:

```bash
# Проверить, что бэкенд доступен
curl http://localhost:8000/health

# Проверить history endpoint
curl "http://localhost:8000/history?from_time=2024-01-01T00:00:00Z&to_time=2024-01-02T00:00:00Z"
```

### 3. Проверить прокси в браузере

1. Откройте DevTools (F12) в браузере
2. Перейдите на вкладку Network
3. Обновите страницу
4. Найдите запрос к `/api/health` или `/api/history`
5. Проверьте:
   - Статус ответа (должен быть 200)
   - URL запроса (должен быть `/api/...`)
   - Ответ сервера

### 4. Проверить консоль браузера

Откройте консоль (F12 → Console) и проверьте ошибки:
- `Failed to fetch history data: ...`
- `Health check failed: ...`

### 5. Проверить переменные окружения

Убедитесь, что фронтенд не использует моки принудительно:

```bash
cd frontend
# Проверить, что нет VITE_USE_MOCK_FALLBACK=true
env | grep VITE
```

### 6. Перезапустить фронтенд с очисткой кэша

```bash
cd frontend
rm -rf node_modules/.vite  # Очистить кэш Vite
npm run dev -- --host 0.0.0.0 --force
```

### 7. Проверить CORS на бэкенде

Убедитесь, что бэкенд разрешает запросы с фронтенда. Проверьте `backend/app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Или конкретный IP/домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 8. Проверить, что прокси работает

В `vite.config.ts` прокси настроен на `http://localhost:8000`. Это должно работать, если:
- Бэкенд запущен на том же сервере
- Бэкенд доступен на `localhost:8000`

Если бэкенд на другом хосте, нужно изменить:

```typescript
proxy: {
    '/api': {
        target: 'http://YOUR_BACKEND_IP:8000',  // Или другой адрес
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, ''),
    },
},
```

## Быстрое решение

Если всё выше не помогло, попробуйте:

1. **Остановить и перезапустить всё:**
```bash
# Остановить
docker-compose down
cd frontend
# Остановить фронтенд (Ctrl+C)

# Запустить заново
docker-compose up -d
cd frontend
npm run dev -- --host 0.0.0.0
```

2. **Проверить, что порты не заняты:**
```bash
netstat -tulpn | grep -E ':(8000|5173)'
```

3. **Проверить firewall:**
```bash
sudo ufw status
# Если нужно, открыть порты
sudo ufw allow 8000/tcp
sudo ufw allow 5173/tcp
```

## После исправления

После того как исправления применены (коммит в dev ветку):

1. На сервере:
```bash
cd ~/projects/cryptify  # или где у вас проект
git pull origin dev
cd frontend
npm install  # если нужно
npm run dev -- --host 0.0.0.0
```

2. Очистить кэш браузера (Ctrl+Shift+R)

3. Проверить, что теперь показывается "Real" вместо "Mock" в интерфейсе

