# Файл: baseline_trainer.py

import json
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib  # Для сохранения модели

# --- КОНФИГУРАЦИЯ DB (те же параметры, что и в data_fetcher.py) ---
DB_USER = "user"
DB_PASSWORD = "password"
DB_HOST = "db"
DB_NAME = "my_database"
DB_PORT = "5432"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
ENGINE = create_engine(DATABASE_URL)

MODEL_FILENAME = "baseline_model.joblib"
MODEL_NAME = "baseline"
TARGET_HORIZON = 3  # Прогноз на 3 часа вперед


def load_data():
    """Загружает все данные из таблицы raw_bars."""
    print("Загрузка данных из DB...")

    # SQL-запрос для извлечения данных, сортируем по времени
    sql_query = "SELECT * FROM raw_bars ORDER BY timestamp ASC;"

    try:
        # Pandas может напрямую читать данные из DB через SQLAlchemy
        df = pd.read_sql(
            sql_query, ENGINE, index_col="timestamp", parse_dates=["timestamp"]
        )
        print(f"Загружено {len(df)} строк.")
        return df
    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")
        return pd.DataFrame()


def create_features_and_target(df: pd.DataFrame):
    """
    Создает целевую переменную (Y) и признаки (X) для обучения.
    """
    # 1. Определение Целевой Переменной (Y)
    # Наша цель: предсказать цену ЗАКРЫТИЯ через 48 часов.
    # .shift(-48) сдвигает цену закрытия на 48 строк ВВЕРХ,
    # чтобы текущая строка содержала цену из будущего.
    df["target"] = df["close"].shift(-TARGET_HORIZON)

    print(f"Создана целевая переменная (цена через {TARGET_HORIZON} часов).")

    # 2. Создание Признаков (X) - Baseline
    # Для baseline-модели используем простейшие лаги цены:
    df["lag_1h"] = df["close"].shift(1)  # Цена 1 час назад
    df["lag_2h"] = df["close"].shift(2)  # Цена 2 часа назад
    df["lag_24h"] = df["close"].shift(24)  # Цена 24 часа назад (сутки)

    # Простая Скользящая Средняя (SMA)
    df["SMA_10h"] = df["close"].rolling(window=10).mean()

    # Изменение цены
    df["price_change_1h"] = df["close"] - df["close"].shift(1)

    print("Созданы 5 baseline-признаков (лаги, SMA, изменение).")

    # 3. Очистка и подготовка
    # Удаляем строки, которые содержат NaN (возникли из-за .shift() и .rolling())
    df_clean = df.dropna()

    # Определяем X и Y
    features = ["lag_1h", "lag_2h", "lag_24h", "SMA_10h", "price_change_1h"]
    X = df_clean[features]
    Y = df_clean["target"]

    return X, Y


def save_model_metrics(model_name: str, metrics: dict):
    try:
        metrics_payload = json.dumps(metrics)
        with ENGINE.begin() as connection:
            result = connection.execute(
                text(
                    """
                    UPDATE ml_models
                    SET metrics = :metrics::jsonb,
                        updated_at = NOW()
                    WHERE model_name = :model_name
                    """
                ),
                {"metrics": metrics_payload, "model_name": model_name},
            )
            if result.rowcount:
                print(f"Метрики модели {model_name} сохранены.")
            else:
                print(
                    f"Модель {model_name} не найдена в таблице ml_models. Зарегистрируйте модель перед сохранением метрик."
                )
    except Exception as e:
        print(f"Ошибка при сохранении метрик: {e}")


def train_and_save_model(X, Y):
    """Обучает простую Линейную Регрессию и сохраняет модель."""

    # 1. Разбиение данных (хотя для MVP это может быть упрощено)
    # Используем 80% данных для обучения
    X_train, X_test, Y_train, Y_test = train_test_split(
        X, Y, test_size=0.2, shuffle=False
    )

    print(f"Данные для обучения: {len(X_train)} строк.")

    # 2. Инициализация и обучение модели
    model = LinearRegression()
    model.fit(X_train, Y_train)

    # 3. Оценка (для вашего внутреннего понимания)
    predictions = model.predict(X_test)
    mae = mean_absolute_error(Y_test, predictions)
    rmse = mean_squared_error(Y_test, predictions, squared=False)
    r2 = model.score(X_test, Y_test)
    print(f"Коэффициент детерминации (R^2) на тестовых данных: {r2:.4f}")
    print(f"Средняя абсолютная ошибка (MAE): {mae:.4f}")
    print(f"Среднеквадратичная ошибка (RMSE): {rmse:.4f}")
    metrics = {"r2": float(r2), "mae": float(mae), "rmse": float(rmse)}

    # 4. Сохранение модели
    joblib.dump(model, MODEL_FILENAME)
    print(f"Модель сохранена как {MODEL_FILENAME}")
    save_model_metrics(MODEL_NAME, metrics)


if __name__ == "__main__":
    data = load_data()
    if not data.empty:
        X, Y = create_features_and_target(data)
        if not X.empty:
            train_and_save_model(X, Y)
