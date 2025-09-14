from sqlalchemy import create_engine, Column, Integer, Float, DateTime, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://criptify_user:criptify_password@localhost:5432/criptify_db",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class RawBar(Base):
    """Raw OHLCV data from Bybit API"""

    __tablename__ = "raw_bars"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, default="BTCUSDT")
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Prediction(Base):
    """ML model predictions"""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(
        DateTime, nullable=False, index=True
    )  # Time when prediction was made
    prediction_horizon = Column(Integer, nullable=False, default=48)  # Hours ahead
    predicted_value = Column(Float, nullable=False)  # Predicted price
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelMetric(Base):
    """Model performance metrics"""

    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    metric_name = Column(String(50), nullable=False)  # MAE, RMSE, etc.
    metric_value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
