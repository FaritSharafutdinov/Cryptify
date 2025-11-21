# Файл: multi_model_trainer.py

import json
import pandas as pd
import numpy as np
import sys
from sqlalchemy import create_engine, text
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import joblib
import json
from tensorflow.keras.metrics import MeanSquaredError

# 3rd Party Models
import xgboost as xgb
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.metrics import MeanSquaredError # Добавлен импорт для load_model

# --- КОНФИГУРАЦИЯ DB ---
# Импортируем настройки из общего конфига
try:
    from config import DATABASE_URL, DB_TABLE_FEATURES, TARGET_HORIZONS
    DB_TABLE_FEATURES = DB_TABLE_FEATURES
    TARGET_HORIZONS = TARGET_HORIZONS
except ImportError:
    # Fallback для обратной совместимости
    import os
    DB_USER = os.getenv("DB_USER", "criptify_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "criptify_password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "criptify_db")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    DB_TABLE_FEATURES = "btc_features_1h"
    TARGET_HORIZONS = [6, 12, 24]

ENGINE = create_engine(DATABASE_URL)

# --- ПАРАМЕТРЫ МОДЕЛЕЙ ---
TARGET_HORIZONS = [6, 12, 24] # Прогноз Log Return на 6, 12 и 24 часа
LSTM_WINDOW_SIZE = 48 # Размер скользящего окна для LSTM
RETRAIN_PERIOD_DAYS = 90 # Дообучаем на данных за последние 90 дней
METRICS_FILENAME = "prediction_metrics.json"

# Фичи, которые были сгенерированы в data_fetcher
BASE_FEATURES = [
    'log_return', 'SP500_log_return', 'price_range', 'price_change',
    'volatility_5', 'volatility_14', 'volume_ma_5', 'volume_zscore',
    'MACD_safe', 'RSI_safe', 'ATR_safe_norm', 'hour_sin', 'hour_cos'
]
MODEL_ERRORS = {}
# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---

def load_data():
    """Загружает все данные из новой таблицы btc_features_1h."""
    print("Загрузка данных из новой таблицы features...")

    sql_query = f"SELECT * FROM {DB_TABLE_FEATURES} ORDER BY timestamp ASC;"

    try:
        df = pd.read_sql(
            sql_query, ENGINE, index_col="timestamp", parse_dates=["timestamp"]
        )
        # ⚠️ ВАЖНО: УДАЛЯЕМ КОЛОНКИ OPEN_INTEREST И SP500, КОТОРЫЕ НЕ ФИЧИ,
        # ЕСЛИ ОНИ БЫЛИ СОХРАНЕНЫ.
        # В вашем data_collector.py фичи создаются, поэтому BASE_FEATURES
        # должен быть достаточен.
        df = df.dropna()
        print(f"Загружено {len(df)} строк.")
        return df
    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")
        return pd.DataFrame()

def save_model_metrics(model_name: str, target: str, metrics: dict):
    """Сохраняет метрики в таблицу ml_models, используя уникальный ключ (model_name, target)."""
    full_model_name = f"{model_name}_{target}"
    
    sql_query = text(
        """
        INSERT INTO ml_models (model_name, metrics, updated_at)
        VALUES (:model_name_param, CAST(:metrics_param AS jsonb), NOW())
        ON CONFLICT (model_name) DO UPDATE
        SET metrics = CAST(:metrics_param AS jsonb), updated_at = NOW()
        """
    )
    
    try:
        metrics_payload = json.dumps(metrics)
        with ENGINE.begin() as connection:
            connection.execute(
                sql_query,
                {
                    "metrics_param": metrics_payload, 
                    "model_name_param": full_model_name
                },
            )
            print(f"Метрики модели {full_model_name} сохранены/обновлены.")
    except Exception as e:
        print(f"Ошибка при сохранении метрик: {e}")
        print(f"SQL State: {e.orig.pgcode if hasattr(e.orig, 'pgcode') else 'N/A'}")
        
def ensure_table_exists():
    """Проверяет и создает таблицу ml_models, если она не существует."""
    print("Проверка и создание таблицы ml_models...")
    
    create_table_sql = text("""
        CREATE TABLE IF NOT EXISTS ml_models (
            model_name VARCHAR(255) PRIMARY KEY,
            metrics JSONB,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    
    try:
        with ENGINE.begin() as connection:
            connection.execute(create_table_sql)
        print("Таблица ml_models готова.")
    except Exception as e:
        print(f"❌ Критическая ошибка при создании таблицы ml_models: {e}")
        sys.exit(1)

# --- ФУНКЦИЯ СОЗДАНИЯ ТАРГЕТОВ ---

def create_targets(df: pd.DataFrame):
    """
    Создает три целевые переменные (Y): Log Return на 6h, 12h, 24h.
    """
    df_temp = df.copy()
    
    # ⚠️ ВАЖНО: Используем 'BTC_Close' или 'Close' в зависимости от того, как
    # вы назвали колонку после Feature Engineering. Судя по вашему
    # data_collector.py, после final_df.drop 'BTC_Close' останется, если вы 
    # не переименовали его обратно в 'Close'. Используем безопасный вариант:
    if 'BTC_Close' in df_temp.columns:
        close_prices = df_temp['BTC_Close']
    elif 'Close' in df_temp.columns:
        close_prices = df_temp['Close']
    else:
        print("❌ Критическая ошибка: Колонка 'Close' или 'BTC_Close' не найдена.")
        sys.exit(1)
    
    for h in TARGET_HORIZONS:
        future_close = close_prices.shift(-h)
        target_col = f"log_return_{h}h"
        # Log Return: ln(Future_Close / Current_Close)
        df_temp[target_col] = np.log(future_close / close_prices)
        print(f"Создан таргет: {target_col}")

    df_temp.dropna(inplace=True)
    
    X = df_temp[BASE_FEATURES].copy()
    Y = df_temp[[f"log_return_{h}h" for h in TARGET_HORIZONS]].copy()

    return X, Y


# --- ПРЕОБРАБОТКА ДАННЫХ ДЛЯ МОДЕЛЕЙ ---

def preprocess_linear_xgb(X: pd.DataFrame, Y: pd.DataFrame, test_size=0.2):
    """
    Предобработка для LR и XGBoost: Разбиение, Нормализация X и 
    возврат скейлера.
    """
    
    if test_size == 0.0:
        print("    [Info] Используется весь набор данных для обучения (test_size=0.0).")
        X_train, X_test = X, pd.DataFrame()
        Y_train, Y_test = Y, pd.DataFrame()
    else:
        X_train, X_test, Y_train, Y_test = train_test_split(
            X, Y, test_size=test_size, shuffle=False
        )
    
    # 1. StandardScaler для LR
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    if not X_test.empty:
        X_test_scaled = scaler.transform(X_test)
    else:
        X_test_scaled = np.array([])
    
    return (
        X_train_scaled, X_test_scaled, X_train.values, X_test.values, 
        Y_train, Y_test, scaler # ⚠️ ДОБАВЛЕН ВОЗВРАТ СКЕЙЛЕРА
    )

def create_sliding_window(data, window_size):
    """Создает скользящие окна для данных LSTM."""
    X_windowed, Y_windowed = [], []
    for i in range(len(data) - window_size):
        # Окно X (48 предыдущих шагов)
        X_windowed.append(data[i:(i + window_size), :])
        # Целевое Y (значение в конце окна)
        Y_windowed.append(data[i + window_size, :])
    return np.array(X_windowed), np.array(Y_windowed)

def save_metrics(metrics):
    """Сохраняет метрики RSE/RMSE в JSON-файл."""
    with open(METRICS_FILENAME, 'w') as f:
        json.dump(metrics, f, indent=4)
    print(f"  -> Сохранены метрики ошибок в {METRICS_FILENAME}.")
    
    
def preprocess_lstm(X: pd.DataFrame, Y: pd.DataFrame, test_size=0.2, window_size=LSTM_WINDOW_SIZE):
    """
    Предобработка для LSTM: Нормализация X, Y, Создание скользящего окна 
    и возврат скейлеров.
    """
    
    # 1. Нормализация X и Y
    scaler_x = MinMaxScaler()
    X_scaled = scaler_x.fit_transform(X)
    scaler_y = MinMaxScaler()
    Y_scaled = scaler_y.fit_transform(Y) # Y масштабируется отдельно для денормализации
    
    # 2. Объединение X и Y для создания окна
    combined_scaled = np.hstack((X_scaled, Y_scaled))

    # 3. Создание скользящего окна
    # Y_temp содержит масштабированные X и Y в конце окна
    X_windowed, Y_temp = create_sliding_window(combined_scaled, window_size)
    
    # Отделяем таргеты Y (последние N колонок Y_temp)
    Y_windowed = Y_temp[:, -len(TARGET_HORIZONS):]
    
    # Отделяем фичи X (первые N колонок)
    X_windowed = X_windowed[:, :, :len(BASE_FEATURES)]

    # 4. Разбиение данных
    test_split_index = int(len(X_windowed) * (1 - test_size))
    
    X_train = X_windowed[:test_split_index]
    X_test = X_windowed[test_split_index:]
    Y_train = Y_windowed[:test_split_index]
    Y_test = Y_windowed[test_split_index:]
    
    return X_train, X_test, Y_train, Y_test, scaler_y, scaler_x # ⚠️ ДОБАВЛЕН ВОЗВРАТ СКЕЙЛЕРА X


# --- ФУНКЦИИ ОБУЧЕНИЯ И ОЦЕНКИ ---
# (Остаются без изменений)

def train_and_evaluate_lr(X_train, X_test, Y_train, Y_test):
    # ... (Остается без изменений)
    model_name = "LinearRegression"
    for i, h in enumerate(TARGET_HORIZONS):
        target_name = f"log_return_{h}h"
        model = LinearRegression()
        model.fit(X_train, Y_train.iloc[:, i]) 
        
        if len(X_test) > 0:
            predictions = model.predict(X_test)
            mae = mean_absolute_error(Y_test.iloc[:, i], predictions)
            mse = mean_squared_error(Y_test.iloc[:, i], predictions)
            rmse = np.sqrt(mse)
            metrics = {"mae": float(mae), "mse": float(mse)}
            print(f"  -> {model_name} | MAE: {mae:.6f} | RMSE: {rmse:.6f}")
            save_model_metrics(model_name, target_name, metrics)
            MODEL_ERRORS[model_name] = rmse
        joblib.dump(model, f"{model_name}_{target_name}.joblib")

def train_and_evaluate_xgb(X_train, X_test, Y_train, Y_test):
    # ... (Остается без изменений)
    model_name = "XGBoost"
    for i, h in enumerate(TARGET_HORIZONS):
        target_name = f"log_return_{h}h"
        model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, random_state=42)
        model.fit(X_train, Y_train.iloc[:, i])
        
        if len(X_test) > 0:
            predictions = model.predict(X_test)
            mae = mean_absolute_error(Y_test.iloc[:, i], predictions)
            mse = mean_squared_error(Y_test.iloc[:, i], predictions)
            rmse = np.sqrt(mse)
            print(f"  -> {model_name} | MAE: {mae:.6f} | RMSE: {rmse:.6f}")
            MODEL_ERRORS[model_name] = rmse
            metrics = {"mae": float(mae), "mse": float(mse)}
            print(f"     MAE: {mae:.6f}, MSE: {mse:.6f}")
            save_model_metrics(model_name, target_name, metrics)
            
        joblib.dump(model, f"{model_name}_{target_name}.joblib")

def train_and_evaluate_lstm(X_train, X_test, Y_train, Y_test, scaler_y, scaler_x): # ⚠️ ДОБАВЛЕН СКЕЙЛЕР X
    """Обучает одну LSTM для всех 3 таргетов."""
    print("\n\n--- Обучение LSTM ---")
    
    model_name = "LSTM"
    target_names = [f"log_return_{h}h" for h in TARGET_HORIZONS]
    
    # 1. Создание модели LSTM
    model = Sequential([
        LSTM(64, activation='relu', input_shape=(X_train.shape[1], X_train.shape[2]), return_sequences=False),
        Dropout(0.2),
        Dense(len(TARGET_HORIZONS))
    ])
    model.compile(optimizer='adam', loss='mse')
    
    callbacks = []
    if len(X_test) > 0:
        es = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
        callbacks.append(es)
        
    print(f"  -> Обучение LSTM (окно {X_train.shape[1]})...")
    
    # 2. Обучение
    model.fit(
        X_train, Y_train,
        epochs=50, 
        batch_size=32,
        validation_data=(X_test, Y_test) if len(X_test) > 0 else None,
        callbacks=callbacks,
        verbose=0
    )
    
    # 3. Оценка (только если есть тестовый набор)
    if len(X_test) > 0:
        predictions_scaled = model.predict(X_test)
        
        Y_test_denorm = scaler_y.inverse_transform(Y_test)
        predictions_denorm = scaler_y.inverse_transform(predictions_scaled)
        
        for i, target_name in enumerate(target_names):
            mae = mean_absolute_error(Y_test_denorm[:, i], predictions_denorm[:, i])
            mse = mean_squared_error(Y_test_denorm[:, i], predictions_denorm[:, i])
            rmse = np.sqrt(mse)
            metrics = {"mae": float(mae), "mse": float(mse)}
            print(f"  -> {target_name} | MAE: {mae:.6f}, MSE: {mse:.6f}")
            save_model_metrics(model_name, target_name, metrics)
            MODEL_ERRORS[model_name] = rmse
    # 4. Сохранение
    model.save(f"{model_name}.h5", save_format='tf')
    
    # ⚠️ НОВОЕ: Сохранение скейлеров X и Y для LSTM
    joblib.dump(scaler_x, f"{model_name}_X_scaler.joblib")
    print(f"  -> Сохранен {model_name}_X_scaler.joblib.")
    
    # ⚠️ НОВОЕ: Сохранение скейлеров Y (target) для LSTM 
    # (Хотя predictor.py использует заглушки, это правильно для полноты)
    for h in TARGET_HORIZONS:
        # NOTE: Поскольку LSTM использует один MinMaxScaler для всех Y, 
        # для LR/XGB в продакшене нужно использовать отдельные скейлеры Y.
        joblib.dump(scaler_y, f"{model_name}_Y_scaler_{h}h.joblib")
        
    print("==================================================================")
    print("✅ Обучение завершено. Сохранение ошибок моделей (RMSE).")
    try:
        with open("model_errors.json", "w") as f:
            json.dump(MODEL_ERRORS, f, indent=4)
        print("  -> Ошибки сохранены в model_errors.json")
    except Exception as e:
        print(f"  ❌ Ошибка сохранения model_errors.json: {e}")


# --- ЛОГИКА ДООБУЧЕНИЯ (RETRAIN) ---

def get_retrain_data(X_base, Y_base, days_to_fetch):
    """Обрезает X и Y для дообучения на последних N днях."""
    end_date = X_base.index.max()
    start_date_retrain = end_date - pd.Timedelta(days=days_to_fetch)
    
    X_retrain = X_base[X_base.index >= start_date_retrain]
    Y_retrain = Y_base[Y_base.index >= start_date_retrain]
    
    print(f"✅ Дообучение будет выполнено на данных с {start_date_retrain.date()} ({len(X_retrain)} строк).")
    
    return X_retrain, Y_retrain

def retrain_all_models(X_base, Y_base):
    """Осуществляет дообучение всех моделей на последних RETRAIN_PERIOD_DAYS."""
    print(f"\n\n======================================================================")
    print(f"🔄 СТАРТ ДООБУЧЕНИЯ (RETRAIN) на последних {RETRAIN_PERIOD_DAYS} днях")
    print(f"======================================================================")
    
    X_retrain, Y_retrain = get_retrain_data(X_base, Y_base, RETRAIN_PERIOD_DAYS)
    
    # 1. LR и XGBoost (Полное переобучение на свежем наборе)
    Y_train_full = Y_retrain
    
    print("\n--- Дообучение LR/XGB (Полное переобучение на свежих данных) ---")
    
    # Предобработка (масштабирование для LR)
    # ⚠️ ИЗМЕНЕНИЕ: Сохраняем возвращенный скейлер (последний элемент)
    X_lr_scaled, _, X_xgb_raw, _, Y_train_df, _, scaler_x_lr = preprocess_linear_xgb(X_retrain, Y_retrain, test_size=0.0)
    
    # ⚠️ НОВОЕ: СОХРАНЕНИЕ СКЕЙЛЕРА X ДЛЯ LR/XGB
    joblib.dump(scaler_x_lr, "LR_X_scaler.joblib")
    print("  -> Сохранен LR_X_scaler.joblib.")
    
    for i, h in enumerate(TARGET_HORIZONS):
        target_name = f"log_return_{h}h"
        
        # LR
        lr_model = LinearRegression()
        lr_model.fit(X_lr_scaled, Y_train_full.iloc[:, i])
        joblib.dump(lr_model, f"LinearRegression_{target_name}.joblib")
        
        # XGBoost
        xgb_model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, random_state=42)
        xgb_model.fit(X_xgb_raw, Y_train_full.iloc[:, i])
        joblib.dump(xgb_model, f"XGBoost_{target_name}.joblib")
        
        print(f"  -> {target_name} обновлен для LR и XGBoost.")

    # 2. LSTM (Fine-tuning)
    print("\n--- Дообучение LSTM (Fine-tuning) ---")
    
    # Предобработка LSTM данных
    # ⚠️ ИЗМЕНЕНИЕ: Сохраняем возвращенный скейлер X и Y для LSTM
    X_lstm_full, _, Y_lstm_full, _, scaler_y_lstm, scaler_x_lstm = preprocess_lstm(X_retrain, Y_retrain, test_size=0.0)
    
    # ⚠️ НОВОЕ: СОХРАНЕНИЕ СКЕЙЛЕРОВ X И Y ДЛЯ LSTM
    joblib.dump(scaler_x_lstm, "LSTM_X_scaler.joblib")
    print("  -> Сохранен LSTM_X_scaler.joblib.")
    for h in TARGET_HORIZONS:
        joblib.dump(scaler_y_lstm, f"LSTM_Y_scaler_{h}h.joblib")

    try:
        # ⚠️ КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Добавлено MeanSquaredError в custom_objects.
        lstm_model = load_model(
            "LSTM.h5", 
            custom_objects={
                'loss': 'mse',
                'MeanSquaredError': MeanSquaredError
            }
        )
        
        # Продолжаем обучение на небольшом количестве эпох
        print("  -> Загрузка и дообучение существующей LSTM модели...")
        lstm_model.fit(
            X_lstm_full, Y_lstm_full, 
            epochs=5,
            batch_size=32, 
            verbose=0
        )
        
        # Сохранение
        lstm_model.save("LSTM.h5")
        print(f"  -> LSTM модель успешно дообучена и сохранена в LSTM.h5.")
        
    except Exception as e:
        print(f"❌ Ошибка при дообучении LSTM. Возможно, модель LSTM.h5 не найдена. Обучите её сначала в режиме 'batch'. Ошибка: {e}")


# --- ОСНОВНАЯ ЛОГИКА ---

if __name__ == "__main__":
    
    mode = 'batch'
    if len(sys.argv) > 1 and sys.argv[1] == 'retrain':
        mode = 'retrain'

    print(f"\n======================================================================")
    print(f"🚀 ТРЕНЕР МОДЕЛЕЙ: РЕЖИМ - {mode.upper()}")
    print(f"======================================================================")

    ensure_table_exists()
    
    data = load_data()
    if data.empty:
        sys.exit(1)
        
    X_base, Y_base = create_targets(data)
    
    if mode == 'batch':
        # --- ПОЛНОЕ ОБУЧЕНИЕ (BATCH TRAINING) ---

        # 1. Предобработка для LR и XGBoost
        # ⚠️ ИЗМЕНЕНИЕ: Сохраняем скейлер X для LR/XGB
        (
            X_lr_train, X_lr_test, 
            X_xgb_train, X_xgb_test, 
            Y_train_df, Y_test_df, 
            scaler_x_lr # ⚠️ НОВЫЙ ВОЗВРАЩАЕМЫЙ ПАРАМЕТР
        ) = preprocess_linear_xgb(X_base, Y_base)
        
        # ⚠️ НОВОЕ: Сохранение скейлера X для LR/XGB
        joblib.dump(scaler_x_lr, "LR_X_scaler.joblib")
        print("  -> Сохранен LR_X_scaler.joblib.")
        
        # 2. Обучение и оценка LR
        train_and_evaluate_lr(
            pd.DataFrame(X_lr_train, columns=X_base.columns), 
            pd.DataFrame(X_lr_test, columns=X_base.columns), 
            Y_train_df, Y_test_df
        )
        
        # 3. Обучение и оценка XGBoost
        train_and_evaluate_xgb(
            pd.DataFrame(X_xgb_train, columns=X_base.columns), 
            pd.DataFrame(X_xgb_test, columns=X_base.columns), 
            Y_train_df, Y_test_df
        )
        
        # 4. Предобработка, Обучение и оценка LSTM
        # ⚠️ ИЗМЕНЕНИЕ: Сохраняем скейлер X для LSTM
        X_lstm_train, X_lstm_test, Y_lstm_train, Y_lstm_test, scaler_y_lstm, scaler_x_lstm = preprocess_lstm(X_base, Y_base)
        train_and_evaluate_lstm(X_lstm_train, X_lstm_test, Y_lstm_train, Y_lstm_test, scaler_y_lstm, scaler_x_lstm)

    elif mode == 'retrain':
        # --- ДООБУЧЕНИЕ (RETRAIN MODE) ---
        retrain_all_models(X_base, Y_base)
        
    print("\n\n✅ Обучение/Дообучение всех моделей завершено.")