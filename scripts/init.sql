-- Файл: init.sql
-- Создание таблицы для исторических данных OHLCV
CREATE TABLE IF NOT EXISTS raw_bars (
    timestamp TIMESTAMP PRIMARY KEY,
    open DECIMAL,
    high DECIMAL,
    low DECIMAL,
    close DECIMAL,
    volume DECIMAL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Создание таблицы для прогнозов (на будущее)
CREATE TABLE IF NOT EXISTS predictions (
    timestamp TIMESTAMP,
    forecast_time TIMESTAMP,
    prediction_value DECIMAL,
    model_version VARCHAR(50),
    PRIMARY KEY (timestamp, forecast_time)
);