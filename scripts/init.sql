-- init.sql: Схема базы данных для хранения инженерных признаков BTC/USDT

-- Таблица для хранения финальных признаков (features)
CREATE TABLE IF NOT EXISTS btc_features_1h (
    -- 1. ОСНОВНОЙ КЛЮЧ
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,

    -- 2. ОСНОВНЫЕ СОХРАНЯЕМЫЕ ЦЕНЫ/ДАННЫЕ
    -- 'Close' - Это финальная BTC_Close из исходного DF
    "Close" DOUBLE PRECISION, 
    "Open_Interest" DOUBLE PRECISION,
    "SP500_Close" DOUBLE PRECISION,

    -- 3. СТАЦИОНАРНЫЕ ВОЗВРАТЫ И ИЗМЕНЕНИЯ ЦЕНЫ
    log_return DOUBLE PRECISION,
    SP500_log_return DOUBLE PRECISION,
    price_range DOUBLE PRECISION,
    price_change DOUBLE PRECISION,
    high_to_prev_close DOUBLE PRECISION,
    low_to_prev_close DOUBLE PRECISION,
    
    -- 4. ВОЛАТИЛЬНОСТЬ И ОБЪЕМ (Rolling Windows)
    volatility_5 DOUBLE PRECISION,
    volatility_14 DOUBLE PRECISION,
    volatility_21 DOUBLE PRECISION,
    volume_ma_5 DOUBLE PRECISION,
    volume_ma_14 DOUBLE PRECISION,
    volume_ma_21 DOUBLE PRECISION,
    volume_zscore DOUBLE PRECISION,
    
    -- 5. ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ (Safe, на основе shift(1))
    MACD_safe DOUBLE PRECISION,
    MACDs_safe DOUBLE PRECISION,
    MACDh_safe DOUBLE PRECISION,
    RSI_safe DOUBLE PRECISION,
    ATR_safe_norm DOUBLE PRECISION,

    -- 6. ВРЕМЕННЫЕ ФИЧИ (Циклическое кодирование)
    hour_sin DOUBLE PRECISION,
    hour_cos DOUBLE PRECISION,
    day_sin DOUBLE PRECISION,
    day_cos DOUBLE PRECISION,
    month_sin DOUBLE PRECISION,
    month_cos DOUBLE PRECISION,
    
    -- Определение первичного ключа для обеспечения уникальности
    PRIMARY KEY (timestamp)
);


-- Создание уникального индекса для быстрого поиска последнего timestamp
CREATE UNIQUE INDEX IF NOT EXISTS idx_features_timestamp ON btc_features_1h (timestamp);

-- ОПЦИОНАЛЬНО: Удаление старой таблицы, если она больше не нужна
-- DROP TABLE IF EXISTS raw_bars;