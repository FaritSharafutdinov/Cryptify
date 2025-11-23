"""
ML Model Service
Handles loading, managing, and making predictions with ML models
"""

import os
import joblib
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import MLModel, RawBar, Prediction


class ModelService:
    """Service for managing and using ML models"""

    def __init__(self, models_directory: str = "/app/trained_models"):
        self.models_directory = models_directory
        self._loaded_models = {}  # Cache for loaded models

    def get_available_models(self, db: Session) -> List[Dict]:
        """Get list of available models from database"""
        models = db.query(MLModel).filter(MLModel.is_active == 1).all()

        result = []
        for model in models:
            result.append(
                {
                    "model_name": model.model_name,
                    "model_type": model.model_type,
                    "prediction_horizons": model.prediction_horizons,
                    "file_path": model.file_path,
                    "metrics": model.metrics,
                    "is_active": model.is_active,
                    "created_at": (
                        model.created_at.isoformat() if model.created_at else None
                    ),
                }
            )
        return result

    def load_model(self, model_name: str, db: Session):
        """Load a model from disk and cache it"""
        # Check if already loaded
        if model_name in self._loaded_models:
            return self._loaded_models[model_name]

        # Get model metadata from database
        model_info = (
            db.query(MLModel)
            .filter(MLModel.model_name == model_name, MLModel.is_active == 1)
            .first()
        )

        if not model_info:
            raise ValueError(f"Model '{model_name}' not found or inactive")

        # Load the model file
        model_path = model_info.file_path
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        try:
            model = joblib.load(model_path)
            self._loaded_models[model_name] = {"model": model, "info": model_info}
            return self._loaded_models[model_name]
        except Exception as e:
            raise Exception(f"Error loading model: {str(e)}")

    def create_features(
        self, df: pd.DataFrame, horizon: int
    ) -> Tuple[np.ndarray, datetime]:
        """
        Create features from raw data for prediction

        Args:
            df: DataFrame with raw OHLCV data (must be sorted by timestamp)
            horizon: Prediction horizon in hours

        Returns:
            Tuple of (features array, base timestamp)
        """
        # Create basic features (same as baseline trainer)
        df["lag_1h"] = df["close_price"].shift(1)
        df["lag_2h"] = df["close_price"].shift(2)
        df["lag_24h"] = df["close_price"].shift(24)
        df["SMA_10h"] = df["close_price"].rolling(window=10).mean()
        df["price_change_1h"] = df["close_price"] - df["close_price"].shift(1)

        # Additional features based on horizon
        if horizon >= 24:
            df["lag_48h"] = df["close_price"].shift(48)
            df["SMA_24h"] = df["close_price"].rolling(window=24).mean()
            df["price_change_24h"] = df["close_price"] - df["close_price"].shift(24)

        if horizon >= 168:  # 1 week
            df["lag_168h"] = df["close_price"].shift(168)
            df["SMA_168h"] = df["close_price"].rolling(window=168).mean()

        # Get the last valid row
        features_list = ["lag_1h", "lag_2h", "lag_24h", "SMA_10h", "price_change_1h"]

        # Use only the base features for now (can be extended)
        latest_features = df.iloc[-1][features_list]
        X_single = latest_features.to_numpy().reshape(1, -1)
        base_time = df.index[-1]

        return X_single, base_time

    def make_prediction(
        self, model_name: str, horizon: int, db: Session, save_to_db: bool = True
    ) -> Dict:
        """
        Make a prediction using the specified model and horizon

        Args:
            model_name: Name of the model to use
            horizon: Prediction horizon in hours
            db: Database session
            save_to_db: Whether to save the prediction to database

        Returns:
            Dictionary with prediction results
        """
        # Load the model
        model_data = self.load_model(model_name, db)
        model = model_data["model"]
        model_info = model_data["info"]

        # Validate horizon
        if horizon not in model_info.prediction_horizons:
            raise ValueError(
                f"Horizon {horizon}h not supported by model '{model_name}'. "
                f"Supported horizons: {model_info.prediction_horizons}"
            )

        # Get required data (need enough history for feature calculation)
        required_hours = max(168, horizon * 2)  # At least 168 hours or 2x horizon

        # Query raw data
        raw_data = (
            db.query(RawBar)
            .order_by(desc(RawBar.timestamp))
            .limit(required_hours)
            .all()
        )

        if not raw_data:
            raise ValueError("No historical data available for prediction")

        # Convert to DataFrame
        df = pd.DataFrame(
            [
                {
                    "timestamp": bar.timestamp,
                    "open_price": float(bar.open_price),
                    "high_price": float(bar.high_price),
                    "low_price": float(bar.low_price),
                    "close_price": float(bar.close_price),
                    "volume": float(bar.volume),
                }
                for bar in raw_data
            ]
        )

        # Sort by timestamp ascending
        df = df.sort_values("timestamp").set_index("timestamp")

        # Create features
        X_single, base_time = self.create_features(df, horizon)

        # Make prediction
        predicted_value = float(model.predict(X_single)[0])
        predicted_time = base_time + timedelta(hours=horizon)

        result = {
            "status": "success",
            "model_name": model_name,
            "base_timestamp": base_time.isoformat(),
            "prediction_horizon": horizon,
            "predicted_value": predicted_value,
            "predicted_time": predicted_time.isoformat(),
            "current_price": float(df.iloc[-1]["close_price"]),
        }

        # Save to database if requested
        if save_to_db:
            prediction = Prediction(
                timestamp=base_time,
                model_name=model_name,
                prediction_horizon=horizon,
                predicted_value=predicted_value,
            )
            db.add(prediction)
            db.commit()
            result["saved_to_db"] = True

        return result

    def register_model(
        self,
        model_name: str,
        model_type: str,
        prediction_horizons: List[int],
        file_path: str,
        feature_config: Optional[Dict] = None,
        metrics: Optional[Dict] = None,
        db: Session = None,
    ) -> Dict:
        """
        Register a new model in the database

        Args:
            model_name: Unique name for the model
            model_type: Type of model (e.g., 'LinearRegression', 'RandomForest')
            prediction_horizons: List of supported horizons in hours
            file_path: Path to the model file
            feature_config: Optional configuration for features
            metrics: Optional performance metrics to store with the model
            db: Database session

        Returns:
            Dictionary with registration result
        """
        # Check if model already exists
        existing = db.query(MLModel).filter(MLModel.model_name == model_name).first()

        if existing:
            raise ValueError(f"Model '{model_name}' already exists")

        # Create new model entry
        new_model = MLModel(
            model_name=model_name,
            model_type=model_type,
            prediction_horizons=prediction_horizons,
            file_path=file_path,
            feature_config=feature_config or {},
            metrics=metrics,
            is_active=1,
        )

        db.add(new_model)
        db.commit()
        db.refresh(new_model)

        return {
            "status": "success",
            "message": f"Model '{model_name}' registered successfully",
            "model_id": new_model.id,
        }
