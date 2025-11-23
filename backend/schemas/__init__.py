"""
Схемы валидации для API
"""
from .validation import (
    ScriptRunRequest,
    TrainerRunRequest,
    DataCollectorRunRequest,
    PredictionRunRequest,
    ScriptStatusResponse,
    ErrorResponse
)

__all__ = [
    "ScriptRunRequest",
    "TrainerRunRequest",
    "DataCollectorRunRequest",
    "PredictionRunRequest",
    "ScriptStatusResponse",
    "ErrorResponse",
]

