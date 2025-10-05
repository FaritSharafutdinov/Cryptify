from datetime import datetime
import requests
import pandas as pd
from sqlalchemy import create_engine
from time import sleep

# --- КОНФИГУРАЦИЯ БАЗЫ ДАННЫХ (DB) ---
# ВАЖНО: Эти параметры должны совпадать с тем, что настроил Бэкенд в docker-compose.yml!
# DB_HOST - это имя сервиса базы данных в Docker (обычно 'db' или 'postgres')
DB_USER = "user"
DB_PASSWORD = "password"
DB_HOST = "db" 
DB_NAME = "my_database"
DB_PORT = "5432"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- КОНФИГУРАЦИЯ API ---
BYBIT_URL = "https://api.bybit.com/v5/market/kline"
SYMBOL = "BTCUSDT"
INTERVAL = "60"  # 1 час
LIMIT = 1000     # Максимальное количество баров за запрос (для Bybit V5)

# 180 дней * 24 часа = 4320 свечей. Требуется 5 запросов по 1000.
REQUESTS_COUNT = 5 

# --- ФУНКЦИИ ---

def get_db_engine():
    """Создает и возвращает движок SQLAlchemy для подключения к DB."""
    try:
        engine = create_engine(DATABASE_URL)
        # Простая проверка соединения
        with engine.connect() as connection:
            print("Успешное подключение к базе данных.")
        return engine
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        print("Проверьте, запущен ли PostgreSQL-контейнер и верны ли учетные данные/DB_HOST.")
        return None

def fetch_kline_data(end_timestamp_ms: int):
    """Выполняет один запрос к Bybit API и возвращает список данных."""
    params = {
        'category': 'linear', # Используем 'linear' для BTCUSDT Perpetual
        'symbol': SYMBOL,
        'interval': INTERVAL,
        'limit': LIMIT,
        'end': end_timestamp_ms 
    }
    
    try:
        response = requests.get(BYBIT_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()['result']['list']
    except Exception as e:
        print(f"Ошибка при запросе к Bybit API: {e}")
        return []

def save_to_db(df: pd.DataFrame, engine):
    """Записывает Pandas DataFrame в таблицу 'raw_bars'."""
    if df.empty:
        print("Нет данных для записи.")
        return

    print(f"Запись {len(df)} уникальных строк в таблицу 'raw_bars'...")
    
    try:
        df.to_sql(
            name='raw_bars', 
            con=engine, 
            if_exists='append', 
            index=False,        
        )
        print("...Запись завершена успешно.")
    except Exception as e:
        print(f"Ошибка при записи в DB: {e}")
        print("Убедитесь, что таблица 'raw_bars' уже создана Бэкендером (init.sql) и ее схема соответствует данным.")

def run_data_fetcher():
    engine = get_db_engine()
    if not engine:
        return

    # 1. Определяем начальное время (сейчас) в миллисекундах
    end_time = datetime.now()
    end_timestamp_ms = int(end_time.timestamp() * 1000)
    
    all_raw_data = []

    print(f"Начало сбора {REQUESTS_COUNT} блоков данных для {SYMBOL} ({INTERVAL}h)...")
    
    for i in range(REQUESTS_COUNT):
        current_time = datetime.fromtimestamp(end_timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M')
        print(f"  > Запрос {i+1}/{REQUESTS_COUNT}. Конечная точка: {current_time}")
        
        # 2. Получаем данные
        raw_data_block = fetch_kline_data(end_timestamp_ms)
        
        if not raw_data_block:
            print("Нет данных. Пагинация остановлена.")
            break
            
        all_raw_data.extend(raw_data_block)
        
        # 3. Пересчитываем 'end' для следующего запроса
        # API возвращает бары от новых к старым. Последний элемент списка - самый старый.
        # Берем временную метку самого старого бара, чтобы продолжить с него
        end_timestamp_ms = int(raw_data_block[-1][0])
        sleep(0.5) # Небольшая задержка, чтобы не превысить лимит API
    
    if not all_raw_data:
        print("Сбор данных не удался. Завершение.")
        return

    # 4. Преобразование данных (Transform)
    df = pd.DataFrame(
        all_raw_data,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
    )
    if 'turnover' in df.columns:
        df = df.drop(columns=['turnover'])
    
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
    cols_to_convert = ['open', 'high', 'low', 'close', 'volume']
    df[cols_to_convert] = df[cols_to_convert].astype(float)
    
    # Удаляем дубликаты (если API вернул пересекающиеся данные) и сортируем
    df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
    
    # 5. Загрузка в DB (Load)
    save_to_db(df, engine)
    
    print(f"\n--- СБОР ДАННЫХ ЗАВЕРШЕН ---")
    print(f"Уникальных баров записано: {len(df)}")
    print(f"Первая свеча: {df['timestamp'].iloc[0]}")
    print(f"Последняя свеча: {df['timestamp'].iloc[-1]}")


if __name__ == '__main__':
    run_data_fetcher()