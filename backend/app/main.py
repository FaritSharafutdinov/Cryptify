from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime, timedelta
from typing import Optional, List
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_db, RawBar, Prediction, ModelMetric

app = FastAPI(
    title="Criptify Backend API",
    description="Backend API for BTC price prediction application",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    db: Session = Depends(get_db),
):
    """Get the latest predictions"""
    try:
        predictions = (
            db.query(Prediction).order_by(desc(Prediction.timestamp)).limit(limit).all()
        )

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
            "data": predictions_data,
            "count": len(predictions_data),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving predictions: {str(e)}"
        )


@app.get("/metrics/latest")
async def get_latest_metrics(db: Session = Depends(get_db)):
    """Get the latest model performance metrics"""
    try:
        metrics = (
            db.query(ModelMetric).order_by(desc(ModelMetric.created_at)).limit(20).all()
        )

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
