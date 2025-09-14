-- Criptify Database Initialization Script
-- This script creates the necessary tables for the BTC price prediction application

-- Create database if it doesn't exist (handled by POSTGRES_DB env var)
-- CREATE DATABASE criptify_db;

-- Connect to the database
\c criptify_db;

-- Create raw_bars table for storing OHLCV data from Bybit API
CREATE TABLE IF NOT EXISTS raw_bars (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL DEFAULT 'BTCUSDT',
    open_price DECIMAL(20, 8) NOT NULL,
    high_price DECIMAL(20, 8) NOT NULL,
    low_price DECIMAL(20, 8) NOT NULL,
    close_price DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on timestamp for faster queries
CREATE INDEX IF NOT EXISTS idx_raw_bars_timestamp ON raw_bars(timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_bars_symbol ON raw_bars(symbol);

-- Create predictions table for storing ML model predictions
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    prediction_horizon INTEGER NOT NULL DEFAULT 48,
    predicted_value DECIMAL(20, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on timestamp for faster queries
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp);

-- Create model_metrics table for storing model performance metrics
CREATE TABLE IF NOT EXISTS model_metrics (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    metric_value DECIMAL(20, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on created_at for faster queries
CREATE INDEX IF NOT EXISTS idx_model_metrics_created_at ON model_metrics(created_at);

-- Create ml_features table for storing engineered features (for ML pipeline)
CREATE TABLE IF NOT EXISTS ml_features (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL DEFAULT 'BTCUSDT',
    -- Technical indicators
    sma_50 DECIMAL(20, 8),
    sma_200 DECIMAL(20, 8),
    rsi DECIMAL(10, 4),
    bb_upper DECIMAL(20, 8),
    bb_middle DECIMAL(20, 8),
    bb_lower DECIMAL(20, 8),
    -- Time features
    hour_of_day INTEGER,
    day_of_week INTEGER,
    -- Target variable
    price_in_48h DECIMAL(20, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on timestamp for faster queries
CREATE INDEX IF NOT EXISTS idx_ml_features_timestamp ON ml_features(timestamp);

-- Insert some sample data for testing (optional)
-- INSERT INTO raw_bars (timestamp, symbol, open_price, high_price, low_price, close_price, volume)
-- VALUES
--     ('2024-01-01 00:00:00', 'BTCUSDT', 42000.00, 42500.00, 41800.00, 42200.00, 100.5),
--     ('2024-01-01 01:00:00', 'BTCUSDT', 42200.00, 42800.00, 42100.00, 42600.00, 120.3);

-- Grant permissions to the application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO criptify_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO criptify_user;
