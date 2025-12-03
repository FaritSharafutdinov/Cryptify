# predictor.py

import os
import sys
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from sqlalchemy import create_engine, text
from sklearn.preprocessing import StandardScaler
from scipy.stats import norm

# Установка переменных окружения для TensorFlow (для чистоты)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
try:
    from tensorflow.keras.models import load_model
    from tensorflow.keras.metrics import MeanSquaredError
except ImportError:
    print("❌ Предупреждение: TensorFlow не установлен. Функции LSTM будут недоступны.")
    load_model = None
    MeanSquaredError = None

# --- КОНСТАНТЫ И НАСТРОЙКИ ---
# Импортируем настройки из общего конфига
try:
    from config import (
        DATABASE_URL_SQLALCHEMY, DB_TABLE_FEATURES, TARGET_HORIZONS
    )
    DB_URL = DATABASE_URL_SQLALCHEMY
    DB_TABLE_FEATURES = DB_TABLE_FEATURES
    TARGET_HORIZONS = TARGET_HORIZONS
except ImportError:
    # Fallback для обратной совместимости
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "criptify_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "criptify_password")
    DB_NAME = os.getenv("DB_NAME", "criptify_db")
    DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
    DB_TABLE_FEATURES = "btc_features_1h"
    TARGET_HORIZONS = [6, 12, 24]

ENGINE = create_engine(DB_URL)

MODEL_DIR = "."  # Модели хранятся в текущей директории
TARGET_HORIZONS = [6, 12, 24] # Часы
Z_SCORE_95 = 1.96
MODEL_ERRORS = {}

# ⚠️ ИМЯ ТАБЛИЦЫ ФИЧЕЙ ДОЛЖНО СООТВЕТСТВОВАТЬ data_collector.py
# DB_TABLE_FEATURES уже импортирован выше
LSTM_TIME_STEPS = 48 # Окно для LSTM

# 🔑 КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: СПИСОК ПРИЗНАКОВ для фильтрации
BASE_FEATURES = [
    'log_return', 'SP500_log_return', 'price_range', 'price_change',
    'volatility_5', 'volatility_14', 'volume_ma_5', 'volume_zscore',
    'MACD_safe', 'RSI_safe', 'ATR_safe_norm', 'hour_sin', 'hour_cos'
]
# ----------------------------------------------------------------------

# --- ГЛОБАЛЬНЫЕ ИНСТРУМЕНТЫ (для денормализации Y) ---
# ⚠️ ВАЖНО: Мы создаем заглушку, так как в продакшене нужно сохранять/загружать
# скейлер Y, который использовался при обучении.
def create_dummy_scaler(mean, scale):
    """Создает заглушку скейлера с заданным mean и scale для имитации обратного преобразования."""
    scaler = StandardScaler()
    # Задаем среднее и масштаб, на которых был обучен скейлер
    scaler.mean_ = np.array([mean])
    scaler.scale_ = np.array([scale])
    scaler.var_ = np.array([scale**2])
    scaler.n_features_in_ = 1
    return scaler

# Условные значения для Log Return (должны быть получены из обучения)
DUMMY_SCALER_PARAMS = {
    6: {'mean': 0.000001, 'scale': 0.005},
    12: {'mean': 0.000002, 'scale': 0.008},
    24: {'mean': 0.000005, 'scale': 0.012},
}
# ----------------------------------------------------------------------

def ensure_prediction_table_exists():
    """Создает таблицу для сохранения прогнозов, если она не существует."""
    print("Проверка и создание таблицы predictions...")
    
    create_table_sql = text("""
        CREATE TABLE IF NOT EXISTS predictions (
            time TIMESTAMP WITH TIME ZONE NOT NULL,
            model_name VARCHAR(255) NOT NULL,
            target_hours INTEGER NOT NULL,
            prediction_log_return FLOAT, -- Сохраняем немасштабированный лог-доход
            ci_low FLOAT, -- Нижняя граница доверительного интервала
            ci_high FLOAT, -- Верхняя граница доверительного интервала
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (time, model_name, target_hours)
        );
        CREATE INDEX IF NOT EXISTS idx_predictions_time ON predictions (time);
    """)
    
    # Добавляем колонки ci_low и ci_high если таблица уже существует
    alter_table_sql = text("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='predictions' AND column_name='ci_low') THEN
                ALTER TABLE predictions ADD COLUMN ci_low FLOAT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='predictions' AND column_name='ci_high') THEN
                ALTER TABLE predictions ADD COLUMN ci_high FLOAT;
            END IF;
        END $$;
    """)
    
    try:
        with ENGINE.begin() as connection:
            connection.execute(create_table_sql)
            # Добавляем колонки если таблица уже существовала
            connection.execute(alter_table_sql)
        print("Таблица predictions готова.")
    except Exception as e:
        print(f"❌ Критическая ошибка при создании таблицы predictions: {e}")
        sys.exit(1)


def load_latest_data(minutes_count: int = 50):
    """
    Загружает последние данные из таблицы features для создания окна 
    прогнозирования.
    """
    print(f"Загрузка последних {minutes_count} строк фич из DB...")
    
    # ⚠️ Загружаем все столбцы, чтобы потом отфильтровать нужные
    query = f"""
    SELECT *
    FROM {DB_TABLE_FEATURES}
    ORDER BY timestamp DESC
    LIMIT {minutes_count};
    """
    try:
        with ENGINE.connect() as connection:
            df = pd.read_sql(query, connection, index_col='timestamp') 
        
        # Сортируем в хронологическом порядке
        df = df.sort_index()
        print(f"Загружено {len(df)} строк фич. Самая последняя: {df.index[-1]}")
        
        return df
        
    except Exception as e:
        print(f"❌ Ошибка загрузки данных для прогноза (таблица {DB_TABLE_FEATURES} пуста или не существует): {e}")
        return pd.DataFrame()

# predictor.py (функция save_prediction)

def load_model_errors():
    """Загружает RMSE моделей из model_errors.json."""
    global MODEL_ERRORS
    try:
        with open(os.path.join(MODEL_DIR, "model_errors.json"), "r") as f:
            MODEL_ERRORS = json.load(f)
        print("✅ Ошибки моделей (RMSE) успешно загружены.")
    except FileNotFoundError:
        print("❌ Ошибка: Файл model_errors.json не найден. Интервалы CI будут 0.")
    except Exception as e:
        print(f"❌ Ошибка загрузки model_errors.json: {e}")

def cleanup_old_predictions(keep_hours: int = 48):
    """
    Удаляет старые прогнозы, оставляя только последние N часов.
    
    Args:
        keep_hours: Количество часов прогнозов для сохранения (по умолчанию 48 часов = 2 дня)
    """
    try:
        from datetime import timezone
        # Используем timezone-aware datetime для корректного сравнения
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=keep_hours)
        
        # Сначала посчитаем сколько будет удалено
        count_sql = text("""
            SELECT COUNT(*) 
            FROM predictions 
            WHERE time < :cutoff_time
        """)
        
        with ENGINE.connect() as connection:
            count_result = connection.execute(count_sql, {"cutoff_time": cutoff_time})
            count = count_result.scalar()
        
        if count == 0:
            print(f"✅ Старых прогнозов для удаления не найдено (сохраняем последние {keep_hours} часов)")
            return
        
        print(f"🧹 Найдено {count} старых прогнозов для удаления (старше {cutoff_time} UTC)")
        
        delete_sql = text("""
            DELETE FROM predictions 
            WHERE time < :cutoff_time
        """)
        
        with ENGINE.begin() as connection:
            result = connection.execute(delete_sql, {"cutoff_time": cutoff_time})
            deleted_count = result.rowcount
        
        if deleted_count > 0:
            print(f"🧹 Удалено {deleted_count} старых прогнозов (старше {keep_hours} часов)")
            
            # Показываем сколько осталось
            remaining_sql = text("SELECT COUNT(*) FROM predictions")
            with ENGINE.connect() as connection:
                remaining = connection.execute(remaining_sql).scalar()
            print(f"📊 Осталось прогнозов в базе: {remaining}")
        else:
            print(f"⚠️ Запрос на удаление выполнен, но ничего не удалено")
    except Exception as e:
        print(f"⚠️ Ошибка при очистке старых прогнозов: {e}")
        import traceback
        traceback.print_exc()
        
# Файл: predictor.py

# ИЗМЕНЕНИЕ СИГНАТУРЫ: Теперь функция принимает 6 аргументов вместо 4
def save_prediction(time: datetime, model_name: str, target_hours: int, prediction: float, ci_low: float, ci_high: float):
    """
    Сохраняет один прогноз (логарифмический доход) и его доверительный интервал
    в таблицу predictions, используя UPSERT.
    """
    
    prediction_val = float(prediction)
    ci_low_val = float(ci_low)
    ci_high_val = float(ci_high) 
    
    # 💡 ИЗМЕНЕНИЕ DML: Добавлены ci_low и ci_high в INSERT и UPDATE
    sql_query = text("""
        INSERT INTO predictions (time, model_name, target_hours, prediction_log_return, ci_low, ci_high)
        VALUES (:time, :model_name, :target_hours, :prediction, :ci_low, :ci_high)
        ON CONFLICT (time, model_name, target_hours) DO UPDATE
        SET prediction_log_return = :prediction, 
            ci_low = :ci_low, 
            ci_high = :ci_high, 
            created_at = NOW()
        """
    )
    
    try:
        with ENGINE.begin() as connection:
            connection.execute(
                sql_query,
                {
                    "time": time, 
                    "model_name": model_name,
                    "target_hours": target_hours,
                    "prediction": prediction_val, 
                    "ci_low": ci_low_val, # ⚠️ НОВЫЙ ПАРАМЕТР
                    "ci_high": ci_high_val # ⚠️ НОВЫЙ ПАРАМЕТР
                }
            )
    except Exception as e:
        print(f"❌ Ошибка при сохранении прогноза {model_name}/{target_hours}h: {e}")


def load_model_and_predict(model_path: str, model_type: str, X_latest: pd.DataFrame, target_h: int = None):
    """
    Загружает модель, выполняет прогнозирование и деномализует результат.
    Возвращает список деномализованных прогнозов (лог-доход).
    """
    predictions_scaled = []
    
    # 1. LR и XGBoost
    if model_type in ['LR', 'XGB']:
        try:
            model = joblib.load(model_path)
        except Exception as e:
            print(f"   ⚠️ Модель {model_type}_{target_h}h или файл скейлера не найден: {e}")
            return [np.nan]

        # ⚠️ КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Используем только BASE_FEATURES для прогноза
        # Для прогноза берем только последнюю строку, отфильтрованную по нужным фичам
        X_pred_series = X_latest.iloc[-1][BASE_FEATURES] 

        if model_type == 'LR':
            try:
                # LR использует масштабированные признаки X
                scaler_X = joblib.load(os.path.join(MODEL_DIR, "LR_X_scaler.joblib")) 
                X_pred_scaled = scaler_X.transform(X_pred_series.values.reshape(1, -1))
            except Exception as e:
                print(f"   ❌ Ошибка загрузки/применения LR_X_scaler: {e}")
                return [np.nan]
        else:
            # XGBoost использует не масштабированные признаки X
            X_pred_scaled = X_pred_series.values.reshape(1, -1)
            
        preds_scaled = model.predict(X_pred_scaled)
        predictions_scaled = preds_scaled.flatten().tolist()

    # 2. LSTM
    elif model_type == 'LSTM':
        if load_model is None:
            return [np.nan] * len(TARGET_HORIZONS)
        
        try:
            # ⚠️ ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ KERAS
            lstm_model = load_model(model_path, compile=False)
        except Exception as e:
            print(f"   ⚠️ Модель LSTM не найдена или ошибка десериализации: {e}")
            return [np.nan] * len(TARGET_HORIZONS)

        # 1. Формирование окна для прогноза (последние 48 строк)
        if len(X_latest) < LSTM_TIME_STEPS:
            print(f"   ⚠️ Недостаточно данных ({len(X_latest)} < {LSTM_TIME_STEPS}) для окна LSTM.")
            return [np.nan] * len(TARGET_HORIZONS)

        # ⚠️ КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Используем только BASE_FEATURES
        X_window = X_latest.iloc[-LSTM_TIME_STEPS:][BASE_FEATURES].values
        
        # 2. Масштабирование (должен использоваться скейлер X_LSTM)
        try:
            scaler_X = joblib.load(os.path.join(MODEL_DIR, "LSTM_X_scaler.joblib")) 
            X_scaled = scaler_X.transform(X_window)
        except Exception as e:
            print(f"   ❌ Ошибка загрузки/применения LSTM_X_scaler: {e}")
            return [np.nan] * len(TARGET_HORIZONS)
            
        # 3. Решейп для LSTM: (1, 48, n_features)
        X_pred = X_scaled.reshape(1, LSTM_TIME_STEPS, X_scaled.shape[1])
        
        # 4. Прогноз
        preds_scaled = lstm_model.predict(X_pred, verbose=0)
        predictions_scaled = preds_scaled.flatten().tolist()
    
    else:
        return [np.nan] * len(TARGET_HORIZONS)
    
    # --- ДЕНОРМАЛИЗАЦИЯ ПРОГНОЗА ---
    predictions_denorm = []
    
    # Определяем горизонты для денормализации
    horizons_to_process = TARGET_HORIZONS if model_type == 'LSTM' else [target_h]

    for i, h in enumerate(horizons_to_process):
        # ⚠️ Загружаем или создаем заглушку скейлера для этого горизонта
        scaler_y = create_dummy_scaler(**DUMMY_SCALER_PARAMS.get(h, {'mean': 0, 'scale': 1}))
        
        # Денормализация: scaler.inverse_transform([[scaled_value]])
        if predictions_scaled and i < len(predictions_scaled):
            scaled_val = predictions_scaled[i]
            denorm_val = scaler_y.inverse_transform([[scaled_val]])[0][0]
            predictions_denorm.append(denorm_val)
        else:
            predictions_denorm.append(np.nan)
        
    return predictions_denorm


def run_prediction():
    """Главная функция для выполнения прогнозов всеми моделями."""
    
    print("\n=================================================")
    print("✨ СТАРТ ПРОГНОЗИРОВАНИЯ (INFERENCE)")
    print("=================================================")
    
    ensure_prediction_table_exists()
    
    # Очистка старых прогнозов перед генерацией новых
    # Оставляем только последние 48 часов (2 дня) прогнозов
    cleanup_old_predictions(keep_hours=48)
    
    # 1. Загружаем данные
    # Загружаем с запасом на LSTM (48) + 5
    X_latest_df = load_latest_data(minutes_count=LSTM_TIME_STEPS + 5) 
    if X_latest_df.empty:
        print("Не удалось загрузить данные. Завершение.")
        return
        
    # Время, для которого делается прогноз (время последней строки)
    prediction_time = X_latest_df.index[-1].to_pydatetime()
    print(f"Прогноз выполняется для времени: {prediction_time}")

    MODELS = {
        'LinearRegression': 'LR',
        'XGBoost': 'XGB',
        'LSTM': 'LSTM'
    }
    
    # ⚠️ ДОБАВЛЕНО: Загрузка ошибок моделей для расчета CI
    load_model_errors() 
    
    # 2. Выполняем прогноз для каждой модели
    for model_name_full, model_type in MODELS.items():
        
        if model_type == 'LSTM':
            # LSTM прогнозирует все 3 таргета сразу
            model_path = os.path.join(MODEL_DIR, "LSTM.h5")
            preds_denorm = load_model_and_predict(model_path, model_type, X_latest_df)
            
            for i, h in enumerate(TARGET_HORIZONS):
                # ⚠️ НОВОЕ: Определяем прогноз и полное имя модели
                prediction = preds_denorm[i]
                model_name = f"{model_name_full}_log_return_{h}h"
                
                # ⚠️ НОВОЕ: Расчет доверительного интервала (CI)
                # Получаем RMSE (используем базовое имя модели, т.к. в model_errors.json ключи без суффикса)
                rmse = MODEL_ERRORS.get(model_name_full, 0)
                ci_margin = Z_SCORE_95 * rmse
                ci_low = prediction - ci_margin
                ci_high = prediction + ci_margin
                
                # ⚠️ ИЗМЕНЕНИЕ ВЫЗОВА: Теперь передаем CI границы
                save_prediction(prediction_time, model_name, h, prediction, ci_low, ci_high)
                
                # ⚠️ ИЗМЕНЕНИЕ ВЫВОДА: Теперь выводим CI
                print(f"  -> {model_name_full} {h}h Log Ret: {prediction:.8f} | CI 95%: [{ci_low:.8f}, {ci_high:.8f}]")
                
        else:
            # LR и XGBoost прогнозируют каждый таргет отдельно
            for h in TARGET_HORIZONS:
                model_name = f"{model_name_full}_log_return_{h}h"
                model_path = os.path.join(MODEL_DIR, f"{model_name}.joblib")
                
                # Загружаем и предсказываем
                preds_denorm = load_model_and_predict(model_path, model_type, X_latest_df, target_h=h)
                
                # Сохраняем результат. У этих моделей только один прогноз
                prediction_val = preds_denorm[0] if preds_denorm and np.isfinite(preds_denorm[0]) else np.nan
                
                # ⚠️ НОВОЕ: Расчет доверительного интервала (CI)
                prediction = prediction_val
                # Используем базовое имя модели (без суффикса), т.к. в model_errors.json ключи без суффикса
                base_model_name = model_name_full  # "LinearRegression" или "XGBoost"
                rmse = MODEL_ERRORS.get(base_model_name, 0)
                ci_margin = Z_SCORE_95 * rmse
                ci_low = prediction - ci_margin
                ci_high = prediction + ci_margin
                
                # ⚠️ ИЗМЕНЕНИЕ ВЫЗОВА: Теперь передаем CI границы
                save_prediction(prediction_time, model_name, h, prediction_val, ci_low, ci_high)
                
                # ⚠️ ИЗМЕНЕНИЕ ВЫВОДА: Теперь выводим CI
                print(f"  -> {model_name} {h}h Log Ret: {prediction_val:.8f} | CI 95%: [{ci_low:.8f}, {ci_high:.8f}]")

    print("\n✅ Прогнозирование завершено.")


if __name__ == "__main__":
    run_prediction()