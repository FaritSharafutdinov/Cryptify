"""
Общий конфигурационный модуль для всего проекта.
Унифицирует настройки подключения к БД для ML-скриптов и бекенда.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (если есть)
load_dotenv()

# ============================================================================
# НАСТРОЙКИ БАЗЫ ДАННЫХ
# ============================================================================

# Приоритет: DATABASE_URL > отдельные переменные > значения по умолчанию
DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

# Если DATABASE_URL не задан, собираем из отдельных переменных
if not DATABASE_URL:
    DB_HOST = os.getenv("DB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
    DB_USER = os.getenv("DB_USER", os.getenv("POSTGRES_USER", "criptify_user"))
    DB_PASSWORD = os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "criptify_password"))
    DB_NAME = os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "criptify_db"))
    DB_PORT = os.getenv("DB_PORT", os.getenv("POSTGRES_PORT", "5432"))
    
    # Формируем DATABASE_URL
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # Если DATABASE_URL задан, извлекаем компоненты для обратной совместимости
    # Простой парсинг (для более сложных случаев можно использовать urllib.parse)
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
    if match:
        DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME = match.groups()
    else:
        # Fallback значения
        DB_HOST = "localhost"
        DB_USER = "criptify_user"
        DB_PASSWORD = "criptify_password"
        DB_NAME = "criptify_db"
        DB_PORT = "5432"

# Для SQLAlchemy (используется в ML-скриптах)
DATABASE_URL_SQLALCHEMY = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# ============================================================================
# НАСТРОЙКИ ML-ПАЙПЛАЙНА
# ============================================================================

# Имена таблиц
DB_TABLE_FEATURES = "btc_features_1h"
DB_TABLE_PREDICTIONS = "predictions"
DB_TABLE_ML_MODELS = "ml_models"

# Директория для моделей
MODEL_DIR = os.getenv("MODEL_DIR", "./scripts")

# Горизонты прогнозирования
TARGET_HORIZONS = [6, 12, 24]  # Часы

# ============================================================================
# НАСТРОЙКИ API
# ============================================================================

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_db_config() -> dict:
    """Возвращает словарь с настройками БД для обратной совместимости"""
    return {
        "DB_HOST": DB_HOST,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
        "DB_NAME": DB_NAME,
        "DB_PORT": DB_PORT,
        "DATABASE_URL": DATABASE_URL,
        "DATABASE_URL_SQLALCHEMY": DATABASE_URL_SQLALCHEMY,
    }

def validate_db_config() -> bool:
    """Проверяет, что все необходимые настройки БД заданы"""
    required = [DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT]
    return all(required) and DATABASE_URL is not None

