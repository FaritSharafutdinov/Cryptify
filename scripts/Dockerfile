# Dockerfile
# Используем более полный базовый образ Python (для TensorFlow)
FROM python:3.12

# Устанавливаем необходимые пакеты ОС
# 'build-essential' нужен для компиляции некоторых библиотек
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    # Очистка кэша
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем скрипт и требования
COPY multi_model_trainer.py .
COPY requirements.txt .

# Устанавливаем Python-зависимости (теперь из файла)
RUN pip install -r requirements.txt

# Команда для запуска (режим 'batch')
# В режиме проверки мы запускаем полное обучение
CMD ["python", "multi_model_trainer.py", "batch"]