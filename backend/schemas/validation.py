"""
Схемы валидации для API endpoints.
Использует Pydantic для валидации входных данных.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime


class ScriptRunRequest(BaseModel):
    """Запрос на запуск ML-скрипта"""
    script_name: str = Field(..., description="Имя скрипта для запуска")
    args: Optional[List[str]] = Field(default=[], description="Дополнительные аргументы")
    timeout: Optional[int] = Field(default=None, ge=1, le=3600, description="Таймаут в секундах (1-3600)")
    
    @validator('script_name')
    def validate_script_name(cls, v):
        """Валидация имени скрипта"""
        allowed_scripts = [
            'data_collector.py',
            'multi_model_trainer.py',
            'predictor.py',
            'inference.py'
        ]
        if v not in allowed_scripts:
            raise ValueError(f"Скрипт {v} не разрешен. Разрешенные: {', '.join(allowed_scripts)}")
        return v
    
    @validator('args')
    def validate_args(cls, v):
        """Валидация аргументов"""
        if v is None:
            return []
        # Проверяем, что аргументы не содержат опасных символов
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>']
        for arg in v:
            if any(char in arg for char in dangerous_chars):
                raise ValueError(f"Аргумент содержит недопустимые символы: {arg}")
        return v


class TrainerRunRequest(BaseModel):
    """Запрос на запуск обучения моделей"""
    mode: Literal['batch', 'retrain'] = Field(default='batch', description="Режим обучения")
    timeout: Optional[int] = Field(default=3600, ge=60, le=7200, description="Таймаут в секундах (60-7200)")


class DataCollectorRunRequest(BaseModel):
    """Запрос на запуск сбора данных"""
    mode: Literal['batch', 'incremental'] = Field(
        default='incremental',
        description="Режим сбора: batch (полный) или incremental (инкрементальный)"
    )
    timeout: Optional[int] = Field(default=1800, ge=60, le=3600, description="Таймаут в секундах (60-3600)")


class PredictionRunRequest(BaseModel):
    """Запрос на запуск прогнозирования"""
    timeout: Optional[int] = Field(default=300, ge=30, le=600, description="Таймаут в секундах (30-600)")


class ScriptStatusResponse(BaseModel):
    """Ответ со статусом скрипта"""
    script_name: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    return_code: Optional[int] = None
    error: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class ErrorResponse(BaseModel):
    """Стандартный ответ об ошибке"""
    status: str = "error"
    error: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    details: Optional[dict] = None

