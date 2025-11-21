-- Database initialization script for Cryptify project
-- Creates tables for ML pipeline and backend

-- ============================================================================
-- 1. ML PIPELINE TABLES
-- ============================================================================

-- Table for BTC features (from data_collector.py)
CREATE TABLE IF NOT EXISTS btc_features_1h (
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    
    -- Basic price data
    "Close" DOUBLE PRECISION, 
    "Open_Interest" DOUBLE PRECISION,
    "SP500_Close" DOUBLE PRECISION,
    
    -- Returns and price changes
    log_return DOUBLE PRECISION,
    SP500_log_return DOUBLE PRECISION,
    price_range DOUBLE PRECISION,
    price_change DOUBLE PRECISION,
    high_to_prev_close DOUBLE PRECISION,
    low_to_prev_close DOUBLE PRECISION,
    
    -- Volatility and volume
    volatility_5 DOUBLE PRECISION,
    volatility_14 DOUBLE PRECISION,
    volatility_21 DOUBLE PRECISION,
    volume_ma_5 DOUBLE PRECISION,
    volume_ma_14 DOUBLE PRECISION,
    volume_ma_21 DOUBLE PRECISION,
    volume_zscore DOUBLE PRECISION,
    
    -- Technical indicators
    MACD_safe DOUBLE PRECISION,
    MACDs_safe DOUBLE PRECISION,
    MACDh_safe DOUBLE PRECISION,
    RSI_safe DOUBLE PRECISION,
    ATR_safe_norm DOUBLE PRECISION,
    
    -- Temporal features
    hour_sin DOUBLE PRECISION,
    hour_cos DOUBLE PRECISION,
    day_sin DOUBLE PRECISION,
    day_cos DOUBLE PRECISION,
    month_sin DOUBLE PRECISION,
    month_cos DOUBLE PRECISION,
    
    PRIMARY KEY (timestamp)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_features_timestamp ON btc_features_1h (timestamp);

-- Table for ML predictions (from predictor.py)
CREATE TABLE IF NOT EXISTS predictions (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    target_hours INTEGER NOT NULL,
    prediction_log_return FLOAT,
    ci_low FLOAT,
    ci_high FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (time, model_name, target_hours)
);

CREATE INDEX IF NOT EXISTS idx_predictions_time ON predictions (time);

-- Table for ML model metrics (from multi_model_trainer.py)
CREATE TABLE IF NOT EXISTS ml_models (
    model_name VARCHAR(255) PRIMARY KEY,
    metrics JSONB,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 2. LEGACY/BACKEND TABLES (for backward compatibility)
-- ============================================================================

-- Table for raw OHLCV data (legacy, may be used by old endpoints)
CREATE TABLE IF NOT EXISTS raw_bars (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    symbol VARCHAR(20) NOT NULL DEFAULT 'BTCUSDT',
    open_price DOUBLE PRECISION NOT NULL,
    high_price DOUBLE PRECISION NOT NULL,
    low_price DOUBLE PRECISION NOT NULL,
    close_price DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_bars_timestamp ON raw_bars (timestamp);

-- Table for model metrics (legacy, for backward compatibility)
CREATE TABLE IF NOT EXISTS model_metrics (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_metrics_model_name ON model_metrics (model_name);

-- Table for ML model registry (legacy, for backward compatibility)
CREATE TABLE IF NOT EXISTS ml_model_registry (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL UNIQUE,
    model_type VARCHAR(50) NOT NULL,
    prediction_horizons JSONB NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    feature_config JSONB,
    metrics JSONB,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ml_model_registry_model_name ON ml_model_registry (model_name);
