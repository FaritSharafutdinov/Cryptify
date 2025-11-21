"""
Конфигурационный модуль для ML-скриптов.
Импортирует настройки из корневого config.py или использует значения по умолчанию.
"""
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    # Пытаемся импортировать из корневого config.py
    from config import (
        DATABASE_URL,
        DATABASE_URL_SQLALCHEMY,
        DB_HOST,
        DB_USER,
        DB_PASSWORD,
        DB_NAME,
        DB_PORT,
        DB_TABLE_FEATURES,
        DB_TABLE_PREDICTIONS,
        DB_TABLE_ML_MODELS,
        MODEL_DIR,
        TARGET_HORIZONS,
        get_db_config,
        validate_db_config,
    )
except ImportError:
    # Fallback: используем переменные окружения напрямую
    DB_HOST = os.getenv("DB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
    DB_USER = os.getenv("DB_USER", os.getenv("POSTGRES_USER", "criptify_user"))
    DB_PASSWORD = os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "criptify_password"))
    DB_NAME = os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "criptify_db"))
    DB_PORT = os.getenv("DB_PORT", os.getenv("POSTGRES_PORT", "5432"))
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    DATABASE_URL_SQLALCHEMY = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    
    DB_TABLE_FEATURES = "btc_features_1h"
    DB_TABLE_PREDICTIONS = "predictions"
    DB_TABLE_ML_MODELS = "ml_models"
    MODEL_DIR = os.getenv("MODEL_DIR", ".")
    TARGET_HORIZONS = [6, 12, 24]
    
    def get_db_config():
        return {
            "DB_HOST": DB_HOST,
            "DB_USER": DB_USER,
            "DB_PASSWORD": DB_PASSWORD,
            "DB_NAME": DB_NAME,
            "DB_PORT": DB_PORT,
            "DATABASE_URL": DATABASE_URL,
            "DATABASE_URL_SQLALCHEMY": DATABASE_URL_SQLALCHEMY,
        }
    
    def validate_db_config():
        required = [DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT]
        return all(required) and DATABASE_URL is not None

