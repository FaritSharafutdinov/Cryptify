from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pydantic import BaseModel
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_db, RawBar, Prediction, ModelMetric
from services.model_service import ModelService

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

# Initialize model service
model_service = ModelService(models_directory="/app/trained_models")


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
    db: Session = Depends(get_db),
):
    """
    Get historical data and predictions for the specified time range.

    Returns combined data from raw_bars and predictions tables.
    """
    try:
        # Set default time range if not provided (last 7 days)
        if not from_time:
            from_time = datetime.utcnow() - timedelta(days=7)
        if not to_time:
            to_time = datetime.utcnow()

        # Query raw bars data
        raw_bars_query = (
            db.query(RawBar)
            .filter(and_(RawBar.timestamp >= from_time, RawBar.timestamp <= to_time))
            .order_by(RawBar.timestamp)
        )

        raw_bars = raw_bars_query.all()

        # Query predictions data
        predictions_query = (
            db.query(Prediction)
            .filter(
                and_(Prediction.timestamp >= from_time, Prediction.timestamp <= to_time)
            )
            .order_by(Prediction.timestamp)
        )

        predictions = predictions_query.all()

        # Format raw bars data
        bars_data = []
        for bar in raw_bars:
            bars_data.append(
                {
                    "timestamp": bar.timestamp.isoformat(),
                    "symbol": bar.symbol,
                    "open": bar.open_price,
                    "high": bar.high_price,
                    "low": bar.low_price,
                    "close": bar.close_price,
                    "volume": bar.volume,
                }
            )

        # Format predictions data
        predictions_data = []
        for pred in predictions:
            predictions_data.append(
                {
                    "timestamp": pred.timestamp.isoformat(),
                    "prediction_horizon": pred.prediction_horizon,
                    "predicted_value": pred.predicted_value,
                    "predicted_time": (
                        pred.timestamp + timedelta(hours=pred.prediction_horizon)
                    ).isoformat(),
                }
            )

        return {
            "status": "success",
            "data": {
                "raw_bars": bars_data,
                "predictions": predictions_data,
                "time_range": {
                    "from": from_time.isoformat(),
                    "to": to_time.isoformat(),
                },
            },
            "metadata": {
                "bars_count": len(bars_data),
                "predictions_count": len(predictions_data),
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving data: {str(e)}")


@app.get("/predictions/latest")
async def get_latest_predictions(
    limit: int = Query(
        10, ge=1, le=100, description="Number of latest predictions to return"
    ),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    horizon: Optional[int] = Query(None, description="Filter by prediction horizon"),
    db: Session = Depends(get_db),
):
    """Get the latest predictions with optional filters"""
    try:
        query = db.query(Prediction)

        # Apply filters
        if model_name:
            query = query.filter(Prediction.model_name == model_name)
        if horizon:
            query = query.filter(Prediction.prediction_horizon == horizon)

        predictions = query.order_by(desc(Prediction.timestamp)).limit(limit).all()

        predictions_data = []
        for pred in predictions:
            predictions_data.append(
                {
                    "timestamp": pred.timestamp.isoformat(),
                    "model_name": pred.model_name,
                    "prediction_horizon": pred.prediction_horizon,
                    "predicted_value": pred.predicted_value,
                    "predicted_time": (
                        pred.timestamp + timedelta(hours=pred.prediction_horizon)
                    ).isoformat(),
                }
            )

        return {
            "status": "success",
            "data": predictions_data,
            "count": len(predictions_data),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving predictions: {str(e)}"
        )


@app.get("/metrics/latest")
async def get_latest_metrics(
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    db: Session = Depends(get_db),
):
    """Get the latest model performance metrics"""
    try:
        query = db.query(ModelMetric)

        if model_name:
            query = query.filter(ModelMetric.model_name == model_name)

        metrics = query.order_by(desc(ModelMetric.created_at)).limit(20).all()

        metrics_data = []
        for metric in metrics:
            metrics_data.append(
                {
                    "model_name": metric.model_name,
                    "metric_name": metric.metric_name,
                    "metric_value": metric.metric_value,
                    "created_at": metric.created_at.isoformat(),
                }
            )

        return {"status": "success", "data": metrics_data, "count": len(metrics_data)}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving metrics: {str(e)}"
        )


@app.get("/models")
async def list_models(db: Session = Depends(get_db)):
    """
    Get list of available ML models

    Returns all registered and active models with their supported prediction horizons
    """
    try:
        models = model_service.get_available_models(db)
        return {"status": "success", "data": models, "count": len(models)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving models: {str(e)}"
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
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error registering model: {str(e)}"
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
