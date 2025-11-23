# Файл: inference.py

import pandas as pd
from sqlalchemy import create_engine
import joblib 
from datetime import datetime, timedelta
import numpy as np

# --- КОНФИГУРАЦИЯ DB ---
DB_USER = "user"
DB_PASSWORD = "password"
DB_HOST = "db" 
DB_NAME = "my_database"
DB_PORT = "5432"
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
ENGINE = create_engine(DATABASE_URL)

MODEL_FILENAME = "baseline_model.joblib"
TARGET_HORIZON = 3 # Прогноз на 3 часа  вперед
REQUIRED_DATA_HOURS = 50 # Нужно 50 часов для расчета лагов и SMA (10h)

def load_latest_data(required_hours: int):
    """
    Загружает последние N часов данных, необходимых для расчета признаков.
    """
    print(f"Загрузка последних {required_hours} часов данных из raw_bars...")
    
    # SQL-запрос для получения последних N строк, сортированных по времени
    sql_query = f"""
        SELECT * FROM raw_bars 
        ORDER BY timestamp DESC 
        LIMIT {required_hours};
    """
    
    try:
        # Важно: Сортируем ASC после загрузки, чтобы признаки считались корректно!
        df = pd.read_sql(sql_query, ENGINE, index_col='timestamp', parse_dates=['timestamp']).sort_index(ascending=True)
        print(f"Загружено {len(df)} строк. Самая свежая метка: {df.index[-1]}")
        return df
    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")
        return pd.DataFrame()


def create_features(df: pd.DataFrame):
    """
    Создает те же признаки, которые использовались при обучении (lag_1h, lag_2h, lag_24h, SMA_10h, price_change_1h).
    """
    # 1. Создание Признаков (X) - Baseline
    df['lag_1h'] = df['close'].shift(1)
    df['lag_2h'] = df['close'].shift(2)
    df['lag_24h'] = df['close'].shift(24)
    df['SMA_10h'] = df['close'].rolling(window=10).mean()
    df['price_change_1h'] = df['close'] - df['close'].shift(1)

    # Нам нужен только последний, актуальный набор признаков
    features = ['lag_1h', 'lag_2h', 'lag_24h', 'SMA_10h', 'price_change_1h']
    
    # Последняя строка, которая не NaN, содержит признаки для прогноза
    latest_features = df.iloc[-1][features] 
    
    # Преобразуем в формат, ожидаемый моделью (X_single = [[f1, f2, f3, ...]])
    X_single = latest_features.to_numpy().reshape(1, -1)
    
    # Получаем временную метку, по которой делаем прогноз
    prediction_base_time = df.index[-1]
    
    return X_single, prediction_base_time


def save_prediction(base_time: datetime, forecast_value: float):
    """
    Сохраняет прогноз в таблицу predictions.
    """
    # 1. Вычисляем временную метку прогноза (base_time + 48 часов)
    forecast_time = base_time + timedelta(hours=TARGET_HORIZON)

    print(f"Прогноз на {TARGET_HORIZON}h (до {forecast_time}): {forecast_value:.2f} USD")
    
    # 2. Создаем DataFrame для записи
    record = pd.DataFrame({
        'timestamp': [base_time], # Время, по которому сделан прогноз
        'forecast_time': [forecast_time], # Время, на которое сделан прогноз (целевое время)
        'prediction_value': [forecast_value],
        'model_version': ['baseline_v1']
    })

    # 3. Запись в DB
    try:
        record.to_sql(
            name='predictions', 
            con=ENGINE, 
            if_exists='append', 
            index=False
        )
        print("\nПрогноз успешно записан в таблицу 'predictions'.")
    except Exception as e:
        print(f"Ошибка при записи прогноза в DB: {e}")


if __name__ == '__main__':
    
    # 1. Загрузка модели
    try:
        model = joblib.load(MODEL_FILENAME)
        print(f"Модель {MODEL_FILENAME} загружена.")
    except FileNotFoundError:
        print(f"Ошибка: Файл модели {MODEL_FILENAME} не найден! Запустите baseline_trainer.py.")
        exit()

    # 2. Загрузка данных и создание признаков
    latest_df = load_latest_data(REQUIRED_DATA_HOURS)
    if latest_df.empty:
        exit()
        
    X_single, base_time = create_features(latest_df)

    # 3. Инференс
    forecast = model.predict(X_single)[0]

    # 4. Сохранение результата
    save_prediction(base_time, forecast)