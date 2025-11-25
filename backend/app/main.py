from fastapi import FastAPI, Depends, HTTPException, Query, Body, status as http_status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pydantic import BaseModel, ValidationError
import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_db, RawBar, Prediction, ModelMetric, MLModel, BTCFeature
from services.model_service import ModelService
from services.ml_script_service import MLScriptService
from schemas.validation import (
    ScriptRunRequest,
    TrainerRunRequest,
    DataCollectorRunRequest,
    PredictionRunRequest,
    ScriptStatusResponse,
    ErrorResponse
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Criptify Backend API",
    description="Backend API for BTC price prediction application",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
model_service = ModelService(models_directory="/app/trained_models")
ml_script_service = MLScriptService()

# Глобальный обработчик ошибок
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    """Обработчик ошибок валидации Pydantic"""
    return JSONResponse(
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Ошибка валидации данных",
            details={"errors": exc.errors()}
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Глобальный обработчик исключений"""
    logger.error(f"Необработанная ошибка: {exc}", exc_info=True)
    return JSONResponse(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Внутренняя ошибка сервера",
            details={"message": str(exc)}
        ).dict()
    )


# Pydantic models for request/response
class PredictionRequest(BaseModel):
    model_name: str
    prediction_horizon: int
    save_to_db: bool = True


class ModelRegistrationRequest(BaseModel):
    model_name: str
    model_type: str
    prediction_horizons: List[int]
    file_path: str
    feature_config: Optional[Dict] = None
    metrics: Optional[Dict] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "criptify-backend",
    }


@app.get("/history")
async def get_history(
    from_time: Optional[datetime] = Query(
        None, description="Start time for data retrieval"
    ),
    to_time: Optional[datetime] = Query(
        None, description="End time for data retrieval"
    ),
    time_range: Optional[str] = Query(
        None, description="Time range shortcut: 1d, 1w, 1m"
    ),
    model: Optional[str] = Query(
        None, description="Filter predictions by model name"
    ),
    db: Session = Depends(get_db),
):
    """
    Get historical data and predictions for the specified time range.

    Returns combined data from btc_features_1h and predictions tables.
    Format adapted for frontend compatibility.
    """
    try:
        # Handle time_range shortcut parameter
        if time_range and not from_time:
            now = datetime.utcnow()
            if time_range == "1d":
                from_time = now - timedelta(hours=24)
            elif time_range == "1w":
                from_time = now - timedelta(days=7)
            elif time_range == "1m":
                from_time = now - timedelta(days=30)
        
        # Set default time range if not provided (last 7 days)
        if not from_time:
            from_time = datetime.utcnow() - timedelta(days=7)
        if not to_time:
            to_time = datetime.utcnow()

        # Query raw bars data (for frontend compatibility)
        raw_bars_query = (
            db.query(RawBar)
            .filter(and_(RawBar.timestamp >= from_time, RawBar.timestamp <= to_time))
            .order_by(RawBar.timestamp)
        )
        raw_bars = raw_bars_query.all()

        # If no raw_bars, try to use features data and convert to raw_bars format
        if not raw_bars:
            # Используем прямой SQL запрос для обхода проблемы с типами данных
            from sqlalchemy import text
            features_result = db.execute(
                text("""
                    SELECT timestamp, "Close", "Open_Interest", log_return, "SP500_log_return",
                           price_range, price_change, high_to_prev_close, low_to_prev_close,
                           volatility_5, volatility_14, volatility_21,
                           volume_ma_5, volume_ma_14, volume_ma_21, volume_zscore,
                           "MACD_safe", "MACDs_safe", "MACDh_safe", "RSI_safe", "ATR_safe_norm",
                           hour_sin, hour_cos, day_sin, day_cos, month_sin, month_cos
                    FROM btc_features_1h
                    WHERE timestamp >= :from_time AND timestamp <= :to_time
                    ORDER BY timestamp ASC
                """),
                {"from_time": from_time, "to_time": to_time}
            )
            features_rows = features_result.fetchall()
            
            # Convert features to raw_bars format (approximation)
            raw_bars_data = []
            prev_close = None
            for row in features_rows:
                if row[1] is not None:  # Close price
                    # Estimate OHLC from Close price
                    close = float(row[1])
                    timestamp = row[0]
                    if timestamp:
                        # Ensure timestamp is timezone-aware and convert to ISO format
                        if timestamp.tzinfo is None:
                            from datetime import timezone
                            timestamp = timestamp.replace(tzinfo=timezone.utc)
                        
                        # Open should be previous close, not current close
                        if prev_close is not None:
                            open_price = prev_close
                        else:
                            # For first bar, use close as open (or estimate from log_return if available)
                            if len(row) > 3 and row[3] is not None:  # log_return
                                log_return = float(row[3])
                                open_price = close / (1 + log_return) if log_return != 0 else close * 0.999
                            else:
                                open_price = close * 0.999  # Small difference to create body
                        
                        # Calculate high and low based on price movement
                        price_change = close - open_price
                        high_price = max(close, open_price) + abs(price_change) * 0.3
                        low_price = min(close, open_price) - abs(price_change) * 0.3
                        
                        raw_bars_data.append({
                            "timestamp": timestamp.isoformat(),
                            "symbol": "BTCUSDT",
                            "open": open_price,
                            "high": high_price,
                            "low": low_price,
                            "close": close,
                            "volume": float(row[13]) if len(row) > 13 and row[13] is not None else 100.0,  # volume_ma_5
                        })
                        
                        prev_close = close
            
            # Убеждаемся, что данные отсортированы по timestamp
            raw_bars_data.sort(key=lambda x: x["timestamp"])
        else:
            # Format raw bars data for frontend
            raw_bars_data = []
            for bar in raw_bars:
                raw_bars_data.append({
                    "timestamp": bar.timestamp.isoformat(),
                    "symbol": bar.symbol or "BTCUSDT",
                    "open": float(bar.open_price),
                    "high": float(bar.high_price),
                    "low": float(bar.low_price),
                    "close": float(bar.close_price),
                    "volume": float(bar.volume),
                })

        # Query predictions data
        # For short ranges (1d), get the most recent predictions regardless of when they were made
        # This ensures we always show predictions even if data collection is delayed
        time_range_hours = (to_time - from_time).total_seconds() / 3600
        if time_range_hours <= 48:  # For 1d or 2d ranges
            # Get recent predictions (last 7 days) and filter those predicting into our range
            # This handles cases where predictions were made before the time range starts
            predictions_query = (
                db.query(Prediction)
                .filter(Prediction.time >= to_time - timedelta(days=7))
                .filter(Prediction.time <= to_time)
            )
            # We'll filter by predicted_time later in Python
        else:
            # For longer ranges, use normal time filtering
            predictions_query = (
                db.query(Prediction)
                .filter(
                    and_(Prediction.time >= from_time, Prediction.time <= to_time)
                )
            )
        
        # Filter by model if specified
        if model:
            # Map frontend model names to backend model names
            if model == "linear_regression":
                predictions_query = predictions_query.filter(
                    (Prediction.model_name.like("%LinearRegression%")) |
                    (Prediction.model_name.like("%LR%")) |
                    (Prediction.model_name == "linear_regression")
                )
            elif model == "xgboost":
                predictions_query = predictions_query.filter(
                    (Prediction.model_name.like("%XGBoost%")) |
                    (Prediction.model_name.like("%XGB%")) |
                    (Prediction.model_name == "xgboost")
                )
            elif model == "lstm":
                predictions_query = predictions_query.filter(
                    (Prediction.model_name.like("%LSTM%")) |
                    (Prediction.model_name == "lstm")
                )
        
        predictions = predictions_query.order_by(Prediction.time.desc()).all()
        
        # For short ranges (1d), show only the most recent prediction batch (same timestamp)
        if time_range_hours <= 48:
            if predictions:
                # Get the most recent prediction time
                most_recent_time = predictions[0].time
                # Filter to only predictions from the most recent time
                predictions = [p for p in predictions if p.time == most_recent_time]
                # Limit to 9 predictions max (3 models × 3 horizons)
                predictions = predictions[:9]

        # Format predictions data for frontend
        predictions_data = []
        for pred in predictions:
            # For short ranges, filter predictions where predicted_time falls in our range
            pred_time = pred.time
            if pred_time.tzinfo is None:
                from datetime import timezone
                pred_time = pred_time.replace(tzinfo=timezone.utc)
            
            predicted_time = pred_time + timedelta(hours=pred.target_hours)
            
            # For 1d ranges, show recent predictions regardless of predicted_time
            # We already filtered by prediction time (last 7 days), so just take the most recent ones
            # Don't filter by predicted_time for short ranges - show all recent predictions
            if time_range_hours <= 48:
                # For 1d, show all recent predictions (limit to last 10 to avoid too many)
                pass
            # Get the last close price to calculate predicted_value from log_return
            last_close = None
            if raw_bars_data:
                last_close = raw_bars_data[-1]["close"]
            elif pred.prediction_log_return is not None:
                # If we have log_return but no close price, we can't calculate absolute value
                # Frontend will need to handle this
                pass
            
            # Calculate predicted_value from log_return if we have close price
            predicted_value = None
            if pred.prediction_log_return is not None and last_close:
                predicted_value = last_close * (1 + pred.prediction_log_return)
            
            # Map model_name to frontend format
            model_name = pred.model_name or "linear_regression"
            if "LinearRegression" in model_name or "LR" in model_name:
                model_name = "linear_regression"
            elif "XGBoost" in model_name or "XGB" in model_name:
                model_name = "xgboost"
            elif "LSTM" in model_name:
                model_name = "lstm"
            
            # Ensure timestamp is timezone-aware
            pred_time = pred.time
            if pred_time.tzinfo is None:
                from datetime import timezone
                pred_time = pred_time.replace(tzinfo=timezone.utc)
            
            # Convert CI from log_return to absolute price values for frontend
            ci_low_price = None
            ci_high_price = None
            if pred.ci_low is not None and pred.ci_high is not None and last_close:
                # CI в log_return, конвертируем в абсолютные значения цены
                ci_low_price = last_close * (1 + pred.ci_low)
                ci_high_price = last_close * (1 + pred.ci_high)
            
            predictions_data.append({
                "timestamp": pred_time.isoformat(),
                "prediction_horizon": pred.target_hours,
                "predicted_value": predicted_value,
                "predicted_time": (
                    pred_time + timedelta(hours=pred.target_hours)
                ).isoformat(),
                "model": model_name,
                "ci_low": ci_low_price,  # CI в абсолютных значениях цены
                "ci_high": ci_high_price,
            })
        
        # Убеждаемся, что predictions отсортированы по timestamp
        predictions_data.sort(key=lambda x: x["timestamp"])

        return {
            "status": "success",
            "data": {
                "raw_bars": raw_bars_data,
                "predictions": predictions_data,
            },
            "metadata": {
                "bars_count": len(raw_bars_data),
                "predictions_count": len(predictions_data),
            },
            "time_range": {
                "from": from_time.isoformat(),
                "to": to_time.isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении истории: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения данных: {str(e)}"
        )


@app.get("/predictions/latest")
async def get_latest_predictions(
    limit: int = Query(
        10, ge=1, le=100, description="Number of latest predictions to return"
    ),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    horizon: Optional[int] = Query(None, ge=1, le=168, description="Filter by prediction horizon (target_hours)"),
    db: Session = Depends(get_db),
):
    """Get the latest predictions from ML models with optional filters"""
    try:
        # Валидация параметров
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Параметр limit должен быть от 1 до 100"
            )
        
        if horizon is not None and (horizon < 1 or horizon > 168):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Параметр horizon должен быть от 1 до 168 часов"
            )
        query = db.query(Prediction)

        # Apply filters
        if model_name:
            query = query.filter(Prediction.model_name == model_name)
        if horizon:
            query = query.filter(Prediction.target_hours == horizon)

        predictions = query.order_by(desc(Prediction.time)).limit(limit).all()

        predictions_data = []
        for pred in predictions:
            predictions_data.append(
                {
                    "time": pred.time.isoformat(),
                    "model_name": pred.model_name,
                    "target_hours": pred.target_hours,
                    "prediction_log_return": pred.prediction_log_return,
                    "ci_low": pred.ci_low,
                    "ci_high": pred.ci_high,
                    "predicted_time": (
                        pred.time + timedelta(hours=pred.target_hours)
                    ).isoformat(),
                    "created_at": pred.created_at.isoformat() if pred.created_at else None,
                }
            )

        return {
            "status": "success",
            "data": predictions_data,
            "count": len(predictions_data),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении прогнозов: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения прогнозов: {str(e)}"
        )


@app.get("/metrics/latest")
async def get_latest_metrics(
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    db: Session = Depends(get_db),
):
    """Get the latest model performance metrics from ml_models table"""
    try:
        query = db.query(MLModel)

        if model_name:
            query = query.filter(MLModel.model_name == model_name)

        models = query.order_by(desc(MLModel.updated_at)).limit(20).all()

        metrics_data = []
        for model in models:
            metrics_data.append(
                {
                    "model_name": model.model_name,
                    "metrics": model.metrics,  # JSONB field with all metrics
                    "updated_at": model.updated_at.isoformat() if model.updated_at else None,
                }
            )

        return {"status": "success", "data": metrics_data, "count": len(metrics_data)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении метрик: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения метрик: {str(e)}"
        )


@app.get("/models")
async def list_models(db: Session = Depends(get_db)):
    """
    Get list of available ML models from ml_models table

    Returns all models with their metrics
    """
    try:
        models = db.query(MLModel).order_by(desc(MLModel.updated_at)).all()
        
        models_data = []
        for model in models:
            models_data.append(
                {
                    "model_name": model.model_name,
                    "metrics": model.metrics,
                    "updated_at": model.updated_at.isoformat() if model.updated_at else None,
                }
            )
        
        return {"status": "success", "data": models_data, "count": len(models_data)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении списка моделей: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения моделей: {str(e)}"
        )


@app.post("/models/register")
async def register_model(
    request: ModelRegistrationRequest, db: Session = Depends(get_db)
):
    """
    Register a new ML model

    Body parameters:
    - model_name: Unique name for the model
    - model_type: Type of model (e.g., 'LinearRegression', 'RandomForest')
    - prediction_horizons: List of supported horizons in hours [1, 3, 24, 168]
    - file_path: Path to the model file
    - feature_config: Optional configuration for features
    """
    try:
        result = model_service.register_model(
            model_name=request.model_name,
            model_type=request.model_type,
            prediction_horizons=request.prediction_horizons,
            file_path=request.file_path,
            feature_config=request.feature_config,
            metrics=request.metrics,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при регистрации модели: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка регистрации модели: {str(e)}"
        )


@app.post("/predict")
async def make_prediction(request: PredictionRequest, db: Session = Depends(get_db)):
    """
    Make a prediction using a specified model and time horizon

    Body parameters:
    - model_name: Name of the model to use for prediction
    - prediction_horizon: Time horizon in hours (1, 3, 24, 168, etc.)
    - save_to_db: Whether to save the prediction to database (default: true)

    Returns:
    - Prediction value, timestamps, and current price
    """
    try:
        result = model_service.make_prediction(
            model_name=request.model_name,
            horizon=request.prediction_horizon,
            db=db,
            save_to_db=request.save_to_db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error making prediction: {str(e)}"
        )


@app.get("/predict/{model_name}/{horizon}")
async def make_prediction_get(
    model_name: str,
    horizon: int,
    save_to_db: bool = Query(True, description="Save prediction to database"),
    db: Session = Depends(get_db),
):
    """
    Make a prediction using GET request

    Path parameters:
    - model_name: Name of the model to use
    - horizon: Prediction horizon in hours

    Query parameters:
    - save_to_db: Whether to save prediction to database (default: true)
    """
    try:
        result = model_service.make_prediction(
            model_name=model_name, horizon=horizon, db=db, save_to_db=save_to_db
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error making prediction: {str(e)}"
        )


@app.get("/features/latest")
async def get_latest_features(
    limit: int = Query(
        100, ge=1, le=1000, description="Number of latest features to return"
    ),
    db: Session = Depends(get_db),
):
    """Get the latest BTC features from ML pipeline"""
    try:
        features = (
            db.query(BTCFeature)
            .order_by(desc(BTCFeature.timestamp))
            .limit(limit)
            .all()
        )

        features_data = []
        for feat in features:
            features_data.append(
                {
                    "timestamp": feat.timestamp.isoformat(),
                    "close": feat.Close,
                    "open_interest": feat.Open_Interest,
                    "log_return": feat.log_return,
                    "sp500_log_return": feat.sp500_log_return,
                    "price_range": feat.price_range,
                    "price_change": feat.price_change,
                    "volatility_5": feat.volatility_5,
                    "volatility_14": feat.volatility_14,
                    "volatility_21": feat.volatility_21,
                    "volume_ma_5": feat.volume_ma_5,
                    "volume_zscore": feat.volume_zscore,
                    "rsi_safe": feat.rsi_safe,
                    "macd_safe": feat.macd_safe,
                    "atr_safe_norm": feat.atr_safe_norm,
                }
            )

        return {
            "status": "success",
            "data": features_data,
            "count": len(features_data),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving features: {str(e)}"
        )


@app.get("/features")
async def get_features(
    from_time: Optional[datetime] = Query(
        None, description="Start time for data retrieval"
    ),
    to_time: Optional[datetime] = Query(
        None, description="End time for data retrieval"
    ),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of records"),
    db: Session = Depends(get_db),
):
    """Get BTC features for the specified time range"""
    try:
        # Валидация временного диапазона
        if from_time and to_time:
            if from_time >= to_time:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="from_time должен быть раньше to_time"
                )
            # Проверка на слишком большой диапазон (больше 1 года)
            if (to_time - from_time).days > 365:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Временной диапазон не должен превышать 365 дней"
                )
        
        if limit < 1 or limit > 10000:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Параметр limit должен быть от 1 до 10000"
            )
        query = db.query(BTCFeature)

        if from_time:
            query = query.filter(BTCFeature.timestamp >= from_time)
        if to_time:
            query = query.filter(BTCFeature.timestamp <= to_time)

        features = query.order_by(BTCFeature.timestamp).limit(limit).all()

        features_data = []
        for feat in features:
            features_data.append(
                {
                    "timestamp": feat.timestamp.isoformat(),
                    "close": feat.Close,
                    "open_interest": feat.Open_Interest,
                    "log_return": feat.log_return,
                    "sp500_log_return": feat.sp500_log_return,
                    "price_range": feat.price_range,
                    "price_change": feat.price_change,
                    "volatility_5": feat.volatility_5,
                    "volatility_14": feat.volatility_14,
                    "volatility_21": feat.volatility_21,
                    "volume_ma_5": feat.volume_ma_5,
                    "volume_ma_14": feat.volume_ma_14,
                    "volume_ma_21": feat.volume_ma_21,
                    "volume_zscore": feat.volume_zscore,
                    "rsi_safe": feat.rsi_safe,
                    "macd_safe": feat.macd_safe,
                    "macds_safe": feat.macds_safe,
                    "macdh_safe": feat.macdh_safe,
                    "atr_safe_norm": feat.atr_safe_norm,
                    "hour_sin": feat.hour_sin,
                    "hour_cos": feat.hour_cos,
                    "day_sin": feat.day_sin,
                    "day_cos": feat.day_cos,
                    "month_sin": feat.month_sin,
                    "month_cos": feat.month_cos,
                }
            )

        return {
            "status": "success",
            "data": features_data,
            "count": len(features_data),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving features: {str(e)}"
        )


# ============================================================================
# ML SCRIPTS ENDPOINTS
# ============================================================================

@app.post("/ml/scripts/run", response_model=ScriptStatusResponse)
async def run_ml_script(
    request: ScriptRunRequest,
    background_tasks=None
):
    """
    Запускает ML-скрипт асинхронно
    
    Поддерживаемые скрипты:
    - data_collector.py
    - multi_model_trainer.py
    - predictor.py
    - inference.py
    """
    try:
        # Проверяем, не выполняется ли уже скрипт
        if ml_script_service.is_running(request.script_name):
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=f"Скрипт {request.script_name} уже выполняется"
            )
        
        # Запускаем скрипт
        result = await ml_script_service.run_script(
            script_name=request.script_name,
            args=request.args,
            timeout=request.timeout
        )
        
        if result["status"] == "failed":
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Ошибка выполнения скрипта")
            )
        
        return ScriptStatusResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при запуске скрипта {request.script_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка запуска скрипта: {str(e)}"
        )


@app.post("/ml/data-collector/run")
async def run_data_collector(
    request: DataCollectorRunRequest
):
    """
    Запускает сбор данных (data_collector.py)
    
    Режимы:
    - batch: Полный исторический сбор
    - incremental: Инкрементальное обновление
    """
    try:
        # Определяем аргументы в зависимости от режима
        # Режим передается через переменную окружения DATA_COLLECTOR_MODE
        env = {
            'DATA_COLLECTOR_MODE': request.mode  # 'batch' или 'incremental'
        }
        
        result = await ml_script_service.run_script(
            script_name="data_collector.py",
            timeout=request.timeout,
            env=env
        )
        
        if result["status"] == "failed":
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Ошибка сбора данных")
            )
        
        return {
            "status": "success",
            "message": f"Сбор данных запущен в режиме {request.mode}",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при запуске data_collector: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка запуска сбора данных: {str(e)}"
        )


@app.post("/ml/trainer/run")
async def run_trainer(
    request: TrainerRunRequest
):
    """
    Запускает обучение моделей (multi_model_trainer.py)
    
    Режимы:
    - batch: Полное обучение на всех данных
    - retrain: Дообучение на последних 90 днях
    """
    try:
        # Проверяем, не выполняется ли уже обучение
        if ml_script_service.is_running("multi_model_trainer.py"):
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Обучение моделей уже выполняется"
            )
        
        result = await ml_script_service.run_script(
            script_name="multi_model_trainer.py",
            args=[request.mode],
            timeout=request.timeout
        )
        
        if result["status"] == "failed":
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Ошибка обучения моделей")
            )
        
        return {
            "status": "success",
            "message": f"Обучение запущено в режиме {request.mode}",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при запуске trainer: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка запуска обучения: {str(e)}"
        )


@app.post("/ml/predictor/run")
async def run_predictor(
    request: PredictionRunRequest
):
    """
    Запускает прогнозирование (predictor.py)
    """
    try:
        result = await ml_script_service.run_script(
            script_name="predictor.py",
            timeout=request.timeout
        )
        
        if result["status"] == "failed":
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Ошибка прогнозирования")
            )
        
        return {
            "status": "success",
            "message": "Прогнозирование выполнено",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при запуске predictor: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка запуска прогнозирования: {str(e)}"
        )


@app.get("/ml/scripts/status/{script_name}")
async def get_script_status(script_name: str):
    """Получает статус выполнения скрипта"""
    try:
        status = ml_script_service.get_script_status(script_name)
        
        if status is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Статус скрипта {script_name} не найден"
            )
        
        return {
            "status": "success",
            "data": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении статуса: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения статуса: {str(e)}"
        )


@app.get("/ml/scripts/status")
async def get_all_scripts_status():
    """Получает статусы всех скриптов"""
    try:
        statuses = ml_script_service.get_all_statuses()
        return {
            "status": "success",
            "data": statuses,
            "count": len(statuses)
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статусов: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения статусов: {str(e)}"
        )


@app.get("/ml/scripts/available")
async def get_available_scripts():
    """Возвращает список доступных ML-скриптов"""
    try:
        scripts = ml_script_service.get_available_scripts()
        return {
            "status": "success",
            "data": scripts,
            "count": len(scripts)
        }
    except Exception as e:
        logger.error(f"Ошибка при получении списка скриптов: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения списка скриптов: {str(e)}"
        )


@app.post("/ml/scripts/{script_name}/cancel")
async def cancel_script(script_name: str):
    """Отменяет выполнение скрипта"""
    try:
        result = await ml_script_service.cancel_script(script_name)
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Ошибка отмены скрипта")
            )
        
        return {
            "status": "success",
            "message": result.get("message", f"Скрипт {script_name} отменен")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при отмене скрипта: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка отмены скрипта: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
