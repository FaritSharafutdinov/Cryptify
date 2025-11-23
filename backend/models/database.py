from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    Float,
    Numeric,
    DateTime,
    String,
    JSON,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
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
    """ML model predictions (updated to match ML scripts schema)"""

    __tablename__ = "predictions"

    # Composite primary key matching ML scripts
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False, index=True)
    model_name = Column(String(255), primary_key=True, nullable=False)
    target_hours = Column(Integer, primary_key=True, nullable=False)
    
    # Prediction value (log return)
    prediction_log_return = Column(Float, nullable=True)
    
    # Confidence intervals
    ci_low = Column(Float, nullable=True)
    ci_high = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Index for faster queries
    __table_args__ = (
        Index('idx_predictions_time', 'time'),
    )


class ModelMetric(Base):
    """Model performance metrics"""

    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    metric_name = Column(String(50), nullable=False)  # MAE, RMSE, etc.
    metric_value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MLModel(Base):
    """ML model registry (updated to match ML scripts schema)"""

    __tablename__ = "ml_models"

    model_name = Column(String(255), primary_key=True, nullable=False, index=True)
    metrics = Column(JSONB, nullable=True)  # JSONB for better performance in PostgreSQL
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class BTCFeature(Base):
    """BTC features table from ML data collector"""

    __tablename__ = "btc_features_1h"

    timestamp = Column(DateTime(timezone=False), primary_key=True, nullable=False, index=True)
    
    # Basic price data
    Close = Column(Numeric, nullable=True)
    Open_Interest = Column(Numeric, nullable=True)
    
    # Returns and price changes
    log_return = Column(Numeric, nullable=True)
    sp500_log_return = Column("SP500_log_return", Numeric, nullable=True)
    price_range = Column(Numeric, nullable=True)
    price_change = Column(Numeric, nullable=True)
    high_to_prev_close = Column(Numeric, nullable=True)
    low_to_prev_close = Column(Numeric, nullable=True)
    
    # Volatility and volume
    volatility_5 = Column(Numeric, nullable=True)
    volatility_14 = Column(Numeric, nullable=True)
    volatility_21 = Column(Numeric, nullable=True)
    volume_ma_5 = Column(Numeric, nullable=True)
    volume_ma_14 = Column(Numeric, nullable=True)
    volume_ma_21 = Column(Numeric, nullable=True)
    volume_zscore = Column(Numeric, nullable=True)
    
    # Technical indicators
    macd_safe = Column("MACD_safe", Numeric, nullable=True)
    macds_safe = Column("MACDs_safe", Numeric, nullable=True)
    macdh_safe = Column("MACDh_safe", Numeric, nullable=True)
    rsi_safe = Column("RSI_safe", Numeric, nullable=True)
    atr_safe_norm = Column("ATR_safe_norm", Numeric, nullable=True)
    
    # Temporal features
    hour_sin = Column(Numeric, nullable=True)
    hour_cos = Column(Numeric, nullable=True)
    day_sin = Column(Numeric, nullable=True)
    day_cos = Column(Numeric, nullable=True)
    month_sin = Column(Numeric, nullable=True)
    month_cos = Column(Numeric, nullable=True)
    
    __table_args__ = (
        Index('idx_features_timestamp', 'timestamp', unique=True),
    )


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
