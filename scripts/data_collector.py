import pandas as pd
import pandas_ta as ta
import numpy as np
import ccxt
import time
from datetime import datetime, timedelta
import requests
import yfinance as yf
import os
from sqlalchemy import create_engine, text # Добавлены импорты для работы с БД

# ==============================================================================
# 🚀 КОНФИГУРАЦИЯ
# ==============================================================================
# Конфигурация сбора данных
EXCHANGE_ID = 'binance'
SYMBOL = 'BTC/USDT'
TIMEFRAME = '1h'
YEARS_TO_FETCH = 2
SP500_TICKER = 'ES=F'
SP500_INTERVAL = '1h'
OI_SYMBOL_BYBIT = 'BTCUSDT'
OI_CATEGORY_BYBIT = 'linear'
OI_INTERVAL_BYBIT = '1h'
BASE_URL_BYBIT = "https://api.bybit.com"
ENDPOINT_OI_BYBIT = "/v5/market/open-interest"

# --- КОНФИГУРАЦИЯ БАЗЫ ДАННЫХ (DB) ---
# Импортируем настройки из общего конфига
try:
    # Пытаемся импортировать из корневого config.py
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from config import (
        DB_USER, DB_PASSWORD, DB_HOST, DB_NAME, DB_PORT,
        DATABASE_URL, DB_TABLE_FEATURES
    )
    DB_TABLE = DB_TABLE_FEATURES
except ImportError:
    # Fallback для обратной совместимости
    import os
    DB_USER = os.getenv("DB_USER", "criptify_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "criptify_password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "criptify_db")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_TABLE = "btc_features_1h"
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- Конфигурация Пайплайна ---
# Сколько последних баров нужно загрузить, чтобы покрыть максимальное окно
# (окно Z-score = 100) + запас на пересчет.
BARS_TO_FETCH_FOR_UPDATE = 200

# Соответствие колонок для Feature Engineering (Остается без изменений)
COL_MAPPING = {
    'Open': 'BTC_Open',
    'High': 'BTC_High',
    'Low': 'BTC_Low',
    'Close': 'BTC_Close',
    'Volume': 'BTC_Volume',
    'SP500_Close': 'SP500_Close'
}
# ==============================================================================

# ==============================================================================
# 🗄️ ФУНКЦИИ БАЗЫ ДАННЫХ (НОВЫЙ БЛОК)
# ==============================================================================

def get_db_engine():
    """Создает и возвращает движок SQLAlchemy для подключения к DB."""
    # Таймаут на попытку подключения
    for _ in range(5):
        try:
            # Создание движка с увеличенным таймаутом
            engine = create_engine(DATABASE_URL, connect_args={'connect_timeout': 10})
            with engine.connect() as connection:
                print("✅ Успешное подключение к базе данных.")
            return engine
        except Exception as e:
            print(f"❌ Ошибка подключения к базе данных: {e}. Повторная попытка через 5 секунд...")
            time.sleep(5)
    print("❌ Не удалось подключиться к базе данных после нескольких попыток.")
    return None

def get_last_timestamp(engine):
    """Извлекает максимальный timestamp из таблицы фичей."""
    try:
        query = text(f"SELECT MAX(timestamp) FROM {DB_TABLE}")
        with engine.connect() as connection:
            last_ts = connection.execute(query).scalar()
        
        if last_ts:
            # Преобразование datetime.datetime в pandas.Timestamp
            return pd.to_datetime(last_ts)
        return None
    except Exception as e:
        print(f"⚠️ Ошибка при чтении последнего timestamp из БД: {e}. Таблица может отсутствовать.")
        return None

def save_features_to_db(df: pd.DataFrame, engine):
    """Записывает Pandas DataFrame в таблицу фичей с проверкой схемы."""
    if df.empty:
        print("Нет данных для записи.")
        return

    print(f"Запись/обновление {len(df)} строк в таблицу '{DB_TABLE}'...")
    
    # Устанавливаем индекс как колонку (важно для to_sql)
    df_to_save = df.copy()
    df_to_save.index.name = 'timestamp'
    df_to_save = df_to_save.reset_index()

    try:
        # Для инкрементального обновления лучше использовать 'replace' или UPSERT (но это сложнее с to_sql)
        # Для простоты в этом примере, мы будем использовать 'append'
        # и полагаться на то, что в df_features_new нет старых данных.
        df_to_save.to_sql(
            name=DB_TABLE,
            con=engine,
            if_exists='append',
            index=False,
        )
        print(f"✅ Запись {len(df_to_save)} строк завершена успешно.")
    except Exception as e:
        print(f"❌ Ошибка при записи в DB: {e}")
        print(f"Убедитесь, что таблица '{DB_TABLE}' существует и имеет колонку 'timestamp' и все фичи.")

# ==============================================================================
# 🛠️ ФУНКЦИИ СБОРА ДАННЫХ (БЕЗ ИЗМЕНЕНИЙ В ЛОГИКЕ)
# ==============================================================================
# ... (fetch_ohlcv_data, fetch_open_interest_data, fetch_sp500_data - ОСТАВИТЬ БЕЗ ИЗМЕНЕНИЙ)
# Я опускаю их здесь для краткости, но они должны быть в финальном скрипте.

def fetch_ohlcv_data(exchange_id, symbol, timeframe, start_date):
    # Тело функции fetch_ohlcv_data
    # ... (Остается без изменений)
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({'enableRateLimit': True})
    except AttributeError:
        print(f"❌ Биржа {exchange_id} не поддерживается ccxt.")
        return []

    since = int(start_date.timestamp() * 1000)
    all_ohlcv = []
    limit = 1000 # Максимальный лимит для ccxt

    print(f"\n--- 1. Сбор OHLCV ---")
    print(f"Подключение к бирже: {exchange_id.upper()}")
    
    # Динамический вывод, чтобы показать, что это может быть короткий сбор
    fetch_range = datetime.utcnow().replace(minute=0, second=0, microsecond=0) - start_date
    range_str = f"{fetch_range.days} дней" if fetch_range.days > 0 else f"{fetch_range.seconds // 3600} часов"
    print(f"Сбор часовых данных для {symbol} за последние {range_str} начиная с {start_date.strftime('%Y-%m-%d %H:%M:%S')}")

    # Логика пагинации остается для надежного сбора данных с start_date
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)

            if not ohlcv:
                print("Данные OHLCV больше не поступают. Сбор завершен.")
                break

            all_ohlcv.extend(ohlcv)

            since = ohlcv[-1][0] + 1

            next_date = datetime.fromtimestamp(since / 1000)
            print(f"Собрано {len(all_ohlcv)} свечей. Продолжение с {next_date.strftime('%Y-%m-%d %H:%M:%S')}...")
            
            time.sleep(exchange.rateLimit / 1000.0)  

        except ccxt.DDoSProtection as e:
            print(f"🚨 Защита от DDoS: {e}. Ожидание 10 секунд...")
            time.sleep(10)
        except ccxt.ExchangeNotAvailable as e:
            print(f"❌ Биржа недоступна: {e}. Завершение работы.")
            break
        except Exception as e:
            print(f"❌ Произошла ошибка при сборе OHLCV: {e}. Завершение работы.")
            break

    return all_ohlcv

def fetch_open_interest_data(symbol, category, interval, start_date):
    # Тело функции fetch_open_interest_data
    # ... (Остается без изменений)
    url = BASE_URL_BYBIT + ENDPOINT_OI_BYBIT
    start_ts = int(start_date.timestamp() * 1000)

    all_oi_data = []  
    limit = 200
    current_cursor = None
    previous_cursor = None

    print(f"\n--- 2. Сбор Open Interest ---")
    fetch_range = datetime.utcnow().replace(minute=0, second=0, microsecond=0) - start_date
    range_str = f"{fetch_range.days} дней" if fetch_range.days > 0 else f"{fetch_range.seconds // 3600} часов"
    print(f"Сбор часовых данных для {symbol} за последние {range_str} начиная с {start_date.strftime('%Y-%m-%d %H:%M:%S')}")

    while True:
        params = {
            "category": category,
            "symbol": symbol,
            "intervalTime": interval,
            "limit": limit,
        }
        if current_cursor:
            params['cursor'] = current_cursor

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get('retCode') != 0:
                 print(f"❌ Ошибка API Bybit: {data.get('retMsg', 'Неизвестная ошибка')}")
                 break

            result = data.get('result', {})
            oi_list = result.get('list', [])

            if not oi_list:
                print("Данные Open Interest больше не поступают. Сбор завершен.")
                break

            previous_cursor = current_cursor
            current_cursor = result.get('nextPageCursor')

            if current_cursor == previous_cursor and all_oi_data:
                print(f"⚠️ Ошибка пагинации: Курсор не изменился. Завершение сбора.")
                break

            current_oldest_ts = int(oi_list[-1]['timestamp'])
            
            # Логика Bybit API: курсор движется назад по времени. 
            # Мы собираем и переворачиваем, пока не достигнем start_ts.
            oi_list.reverse()
            all_oi_data.extend(oi_list)

            if current_oldest_ts < start_ts:
                 print("✅ Достигнута или пройдена дата начала сбора. Завершение сбора.")
                 break

            if not current_cursor:
                print("Курсор для следующей страницы пуст. Сбор завершен.")
                break

            time.sleep(0.5) 

        except Exception as e:
            print(f"\n❌ Произошла непредвиденная ошибка при запросе Bybit: {e}. Завершение работы.")
            break

    if all_oi_data:
        all_oi_data.sort(key=lambda x: int(x['timestamp']))
        df_oi = pd.DataFrame(all_oi_data)
        df_oi['timestamp'] = pd.to_numeric(df_oi['timestamp'])
        df_oi = df_oi[df_oi['timestamp'] >= start_ts]
        df_oi.drop_duplicates(subset=['timestamp'], keep='first', inplace=True)
        return df_oi

    return pd.DataFrame()


def fetch_sp500_data(ticker, interval, start_date):
    # Тело функции fetch_sp500_data
    # ... (Остается без изменений)
    print(f"\n--- 3. Сбор данных S&P 500 ---")

    try:
        # yfinance может потребовать дату в формате 'YYYY-MM-DD'
        start_date_str = start_date.strftime('%Y-%m-%d')
        df_sp500 = yf.download(
            ticker,
            start=start_date_str,
            interval=interval,
            progress=False,
        )

        if df_sp500.empty:
            print(f"⚠️ Не удалось получить данные для {ticker} или DataFrame пуст.")
            return pd.DataFrame()

        # Очистка имен колонок
        if isinstance(df_sp500.columns, pd.MultiIndex):
            df_sp500.columns = [f'{col[0]}_{col[1]}' if col[0] else col[1] for col in df_sp500.columns]
        
        if 'Adj Close' in df_sp500.columns:
            df_sp500.drop(columns=['Adj Close'], inplace=True)
            
        df_sp500.index.name = 'timestamp'
        df_sp500 = df_sp500.tz_localize(None) 
        
        print(f"✅ Успешно собрано {len(df_sp500)} свечей S&P 500.")
        return df_sp500

    except Exception as e:
        print(f"❌ Произошла ошибка при сборе S&P 500: {e}")
        return pd.DataFrame()

# ==============================================================================
# 🧩 ЛОГИКА ОБЪЕДИНЕНИЯ ДАННЫХ (БЕЗ ИЗМЕНЕНИЙ В ЛОГИКЕ)
# ==============================================================================
def merge_all_data(ohlcv_data, df_oi, df_sp500, sp500_ticker):
    # Тело функции merge_all_data
    # ... (Остается без изменений)
    """
    Объединяет все собранные DataFrame.
    """
    if not ohlcv_data:
        print("Не удалось получить данные OHLCV.")
        return None
    
    # 1. Преобразование OHLCV в DataFrame
    df_ohlcv = pd.DataFrame(ohlcv_data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df_ohlcv['timestamp'] = pd.to_datetime(df_ohlcv['timestamp'], unit='ms')
    df_ohlcv.set_index('timestamp', inplace=True)
    df_ohlcv = df_ohlcv[~df_ohlcv.index.duplicated(keep='first')]
    final_df = df_ohlcv
    
    # 2. Объединение с Open Interest
    if not df_oi.empty:
        df_oi['timestamp'] = pd.to_datetime(df_oi['timestamp'], unit='ms')
        df_oi.set_index('timestamp', inplace=True)
        final_df = final_df.join(df_oi[['openInterest']].rename(
            columns={'openInterest': 'Open_Interest'}), how='left')
    
    # 3. Объединение с S&P 500
    if not df_sp500.empty:
        final_df = final_df.join(df_sp500, how='left')

        # --- Обработка пропусков S&P 500 ---
        # Выбираем колонки S&P 500 и колонки BTC
        sp500_columns = [col for col in final_df.columns if sp500_ticker in str(col) or str(col) in ['Open', 'High', 'Low', 'Close', 'Volume']]

        # ffill и заполнение нулями.
        final_df[sp500_columns] = final_df[sp500_columns].ffill()
        final_df[sp500_columns] = final_df[sp500_columns].fillna(0)

        # Удаление начальных строк, где S&P 500 был равен 0 (актуально для полного бэкфилла)
        is_sp500_zero = (final_df[['Close', 'High', 'Low', 'Open']].eq(0)).all(axis=1) # Проверяем только основные OHLCV
        if False in is_sp500_zero.values:
            first_valid_row_index = is_sp500_zero.idxmin()
            rows_before = final_df.index.get_loc(first_valid_row_index)
            rows_to_drop = final_df.iloc[:rows_before]
            final_df = final_df.drop(rows_to_drop.index, axis=0)

    # 4. Финальное Переименование Столбцов
    btc_rename_map = {
        'Open': 'BTC_Open',
        'High': 'BTC_High',
        'Low': 'BTC_Low',
        'Close': 'BTC_Close',
        'Volume': 'BTC_Volume'
    }
    final_df.rename(columns=btc_rename_map, inplace=True)

    new_column_names = {}
    yfinance_prefix = "SP500_"

    for col in final_df.columns:
        col_str = str(col)
        
        if SP500_TICKER in col_str:
            if 'Close' in col_str:
                new_name = f"{yfinance_prefix}Close"
            elif 'Open' in col_str:
                new_name = f"{yfinance_prefix}Open"
            elif 'High' in col_str:
                new_name = f"{yfinance_prefix}High"
            elif 'Low' in col_str:
                new_name = f"{yfinance_prefix}Low"
            elif 'Volume' in col_str:
                new_name = f"{yfinance_prefix}Volume"
            else:
                new_name = col_str
            new_column_names[col] = new_name

    final_df.rename(columns=new_column_names, inplace=True)
    return final_df

# ==============================================================================
# 📊 ФУНКЦИИ FEATURE ENGINEERING (БЕЗ ИЗМЕНЕНИЙ В ЛОГИКЕ)
# ==============================================================================
def calculate_log_return(series, periods=1):
    # Тело функции calculate_log_return
    # ... (Остается без изменений)
    """
    Расчет логарифмического возврата.
    """
    return np.log(series / series.shift(periods))

def create_advanced_features(df: pd.DataFrame) -> pd.DataFrame:
    # Тело функции create_advanced_features
    # ... (Остается без изменений)
    """
    Создает стационарные фичи, включая SP500 log return,
    и рассчитывает индикаторы без look-ahead bias.
    """
    df_temp = df.copy()
    
    # 1. ПСЕВДОНИМЫ ДЛЯ УНИВЕРСАЛЬНОСТИ (для pandas_ta)
    for old_name, new_name in COL_MAPPING.items():
        if new_name in df_temp.columns and old_name not in df_temp.columns:
            df_temp[old_name] = df_temp[new_name]
            
    # Добавление Open для price_change, если оно еще не создано
    if 'BTC_Open' in df_temp.columns and 'Open' not in df_temp.columns:
        df_temp['Open'] = df_temp['BTC_Open']

    ## 2. ОСНОВНЫЕ ФИЧИ
    df_temp['log_return'] = calculate_log_return(df_temp['Close'])
    df_temp['SP500_log_return'] = calculate_log_return(df_temp['SP500_Close'])
    
    ## 3. СТАЦИОНАРНЫЕ ЦЕНОВЫЕ ПРЕОБРАЗОВАНИЯ (BTC)
    prev_close = df_temp['Close'].shift(1)
    df_temp['price_range'] = (df_temp['High'] - df_temp['Low']) / prev_close
    df_temp['price_change'] = (df_temp['Close'] - df_temp['Open']) / df_temp['Open']
    df_temp['high_to_prev_close'] = (df_temp['High'] - prev_close) / prev_close
    df_temp['low_to_prev_close'] = (df_temp['Low'] - prev_close) / prev_close

    ## 4. ВОЛАТИЛЬНОСТЬ И ОБЪЕМ (Окна 5, 14, 21, 100)
    for window in [5, 14, 21]:
        df_temp[f'volatility_{window}'] = df_temp['log_return'].rolling(window=window).std()
        df_temp[f'volume_ma_{window}'] = df_temp['Volume'].rolling(window=window).mean()
    vol_mean_100 = df_temp['Volume'].rolling(100).mean()
    vol_std_100 = df_temp['Volume'].rolling(100).std()
    df_temp['volume_zscore'] = (df_temp['Volume'] - vol_mean_100) / vol_std_100


    ## 5. БЕЗОПАСНЫЕ ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ (На основе prev_Close)
    df_temp['prev_Close'] = df_temp['Close'].shift(1)
    df_temp['prev_High'] = df_temp['High'].shift(1)
    df_temp['prev_Low'] = df_temp['Low'].shift(1)

    macd_data = df_temp.ta.macd(close='prev_Close', fast=12, slow=26, signal=9)
    if macd_data is not None:
        df_temp['MACD_safe'] = macd_data.iloc[:, 0]
        df_temp['MACDs_safe'] = macd_data.iloc[:, 1]
        df_temp['MACDh_safe'] = macd_data.iloc[:, 2]

    rsi_data = df_temp.ta.rsi(close='prev_Close', length=14)
    if rsi_data is not None:
        df_temp['RSI_safe'] = rsi_data

    atr_data = df_temp.ta.atr(high='prev_High', low='prev_Low', close='prev_Close', length=14)
    if atr_data is not None:
        df_temp['ATR_safe_norm'] = atr_data / df_temp['prev_Close']
    
    df_temp.drop(['prev_Close', 'prev_High', 'prev_Low'], axis=1, inplace=True, errors='ignore')


    ## 6. ВРЕМЕННЫЕ ФИЧИ (ЦИКЛИЧЕСКОЕ КОДИРОВАНИЕ)
    df_temp['hour_sin'] = np.sin(2 * np.pi * df_temp.index.hour / 24)
    df_temp['hour_cos'] = np.cos(2 * np.pi * df_temp.index.hour / 24)
    df_temp['day_sin'] = np.sin(2 * np.pi * df_temp.index.dayofweek / 7)
    df_temp['day_cos'] = np.cos(2 * np.pi * df_temp.index.dayofweek / 7)
    df_temp['month_sin'] = np.sin(2 * np.pi * df_temp.index.month / 12)
    df_temp['month_cos'] = np.cos(2 * np.pi * df_temp.index.month / 12)

    ## 7. ФИНАЛЬНАЯ ОЧИСТКА
    cols_to_drop = list(COL_MAPPING.keys()) + list(COL_MAPPING.values())
    cols_to_drop.extend(['Open', 'High', 'Low', 'Close', 'Volume','SP500_High', 'SP500_Low', 'SP500_Open', 'SP500_Volume'])
    
    final_cols_to_drop = set(c for c in cols_to_drop) - set(['Close']) # 'Close' здесь будет BTC_Close в новом названии

    # Внимание: После переименования BTC_Close остается как 'Close' в df_temp, если не был в COL_MAPPING
    # В исходном коде, COL_MAPPING включает 'Close', который переименовывается в 'BTC_Close'.
    # Я удаляю BTC_Open/High/Low/Volume, но оставляю Close (BTC_Close), как целевую переменную
    final_df = df_temp.drop(columns=list(final_cols_to_drop), errors='ignore')
    
    # Удаляем строки с NaN (появляются из-за rolling windows и shift)
    final_df.dropna(inplace=True) 

    return final_df

# ==============================================================================
# ⚙️ ОСНОВНОЙ ПАЙПЛАЙН: РЕЖИМЫ РАБОТЫ (АДАПТИРОВАН)
# ==============================================================================

def run_batch_history(engine):
    """
    Выполняет полный исторический сбор данных за YEARS_TO_FETCH и создает таблицу БД.
    """
    print("\n" + "="*70)
    print("🤖 ЭТАП: ПОЛНЫЙ ИСТОРИЧЕСКИЙ СБОР И ОБЪЕДИНЕНИЕ")
    print("="*70)
    
    end_date = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=364 * YEARS_TO_FETCH)

    try:
        # 1. Получение данных
        ohlcv_data = fetch_ohlcv_data(EXCHANGE_ID, SYMBOL, TIMEFRAME, start_date)
        df_oi = fetch_open_interest_data(OI_SYMBOL_BYBIT, OI_CATEGORY_BYBIT, OI_INTERVAL_BYBIT, start_date)
        df_sp500 = fetch_sp500_data(SP500_TICKER, SP500_INTERVAL, start_date)

        # 2. Объединение и очистка
        df_raw = merge_all_data(ohlcv_data, df_oi, df_sp500, SP500_TICKER)
        
        if df_raw is None or df_raw.empty:
            print("❌ Pipeline завершен с ошибкой: Объединенный DataFrame пуст.")
            return
            
        print(f"✅ Исходные данные готовы. Размер: {len(df_raw)}")

    except Exception as e:
        print(f"❌ Произошла непредвиденная ошибка на этапе сбора данных: {e}")
        return

    # --- 3. FEATURE ENGINEERING ---
    print("\n" + "="*70)
    print("🔬 ЭТАП 2: СОЗДАНИЕ ИНЖЕНЕРИНГОВЫХ ПРИЗНАКОВ")
    print("="*70)
    
    try:
        df_features = create_advanced_features(df_raw)
        
        # --- 4. ФИНАЛЬНЫЙ ВЫВОД И СОХРАНЕНИЕ В БД ---
        # В режиме batch history мы используем 'replace' для создания/перезаписи таблицы
        df_features.index.name = 'timestamp'
        df_features_to_save = df_features.reset_index()
        
        print(f"💾 Создание/перезапись таблицы '{DB_TABLE}' в БД...")
        df_features_to_save.to_sql(
            name=DB_TABLE,
            con=engine,
            if_exists='replace', # ВАЖНО: 'replace' для исторической перезаписи
            index=False,
        )
        # Дополнительно можно создать индекс для скорости
        with engine.connect() as connection:
            connection.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_timestamp ON {DB_TABLE} (timestamp)"))
            connection.commit()
            
        print(f"✅ Полная историческая база данных сохранена в таблицу: {DB_TABLE}. Размер: {len(df_features)}")
        
    except Exception as e:
          print(f"❌ Произошла ошибка при Feature Engineering или записи в БД: {e}")

def run_incremental_update(engine):
    """
    Основная функция для ежечасного сбора последних N свечей,
    их обработки и добавления в существующую базу в БД.
    """
    print("\n" + "="*70)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🤖 ЭТАП 1: СБОР ИНКРЕМЕНТАЛЬНЫХ ДАННЫХ")
    print("="*70)
    
    # 0. ИНТЕЛЛЕКТУАЛЬНОЕ ОПРЕДЕЛЕНИЕ СТАРТОВОЙ ДАТЫ
    
    end_date = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    # Дефолтная дата начала сбора: 205 часов назад от текущего часа
    start_date_fetch = end_date - timedelta(hours=BARS_TO_FETCH_FOR_UPDATE + 5)
    last_timestamp = None
    
    # ПЕРЕХОД: ЧТЕНИЕ ПОСЛЕДНЕГО TIMESTAMP ИЗ БД
    last_timestamp = get_last_timestamp(engine)
    
    if last_timestamp is not None:
        # Отступаем назад на размер окна (200 часов)
        fetch_from_date = last_timestamp - timedelta(hours=BARS_TO_FETCH_FOR_UPDATE)
        
        # Используем рассчитанную дату, чтобы покрыть пересчет старых фичей
        if fetch_from_date > start_date_fetch:
            start_date_fetch = fetch_from_date
            
        print(f"База данных найдена. Последний timestamp: {last_timestamp}. Начинаем сбор с: {start_date_fetch.strftime('%Y-%m-%d %H:%M:%S')}")
            
    # 1. СБОР И ОБЪЕДИНЕНИЕ
    try:
        ohlcv_data = fetch_ohlcv_data(EXCHANGE_ID, SYMBOL, TIMEFRAME, start_date_fetch)
        df_oi = fetch_open_interest_data(OI_SYMBOL_BYBIT, OI_CATEGORY_BYBIT, OI_INTERVAL_BYBIT, start_date_fetch)
        df_sp500 = fetch_sp500_data(SP500_TICKER, SP500_INTERVAL, start_date_fetch)

        df_raw_new = merge_all_data(ohlcv_data, df_oi, df_sp500, SP500_TICKER)
        
        if df_raw_new is None or df_raw_new.empty:
            print("❌ Pipeline завершен: Объединенный DataFrame пуст.")
            return
            
        print(f"✅ Исходные (последние) данные готовы. Размер: {len(df_raw_new)}")

    except Exception as e:
        print(f"❌ Произошла непредвиденная ошибка на этапе сбора данных: {e}")
        return

    # 2. FEATURE ENGINEERING (Обрабатываем все последние 200+ баров)
    print("\n" + "="*70)
    print("🔬 ЭТАП 2: СОЗДАНИЕ ИНЖЕНЕРИНГОВЫХ ПРИЗНАКОВ")
    print("="*70)
    
    try:
        df_features_new = create_advanced_features(df_raw_new)
        
        if df_features_new.empty:
            print("⚠️ DataFrame фичей пуст после очистки NaN. Обновление не требуется.")
            return

    except Exception as e:
        print(f"❌ Произошла непредвиденная ошибка при Feature Engineering: {e}")
        return

    # 3. ИНКРЕМЕНТАЛЬНОЕ СОХРАНЕНИЕ
    print("\n" + "="*70)
    print("💾 ЭТАП 3: ОБНОВЛЕНИЕ ПОСТОЯННОЙ БАЗЫ ДАННЫХ")
    print("="*70)
    
    # ⚠️ ФИЛЬТРАЦИЯ: Если last_timestamp не None, мы можем обновить базу
    if last_timestamp is not None:
        # Обновляем только те строки, которые новее, чем в базе
        new_features_to_append = df_features_new[df_features_new.index > last_timestamp]
        
        # Если есть строки, которые находятся в окне пересчета (200 баров) и уже есть в БД,
        # их нужно обновить. Но в данном простом сценарии с `if_exists='append'` это сложно.
        # Мы предполагаем, что запуск происходит достаточно часто, чтобы не было дубликатов,
        # идущих сразу за `last_timestamp`. 
        # Если есть риск, то нужно использовать UPSERT (ON CONFLICT DO UPDATE).
        
        if new_features_to_append.empty:
            print("✅ База данных актуальна. Новых строк для добавления нет.")
            return

        # Сохранение (добавление новых строк)
        save_features_to_db(new_features_to_append, engine)
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ База данных фичей успешно обновлена в: {DB_TABLE}. Добавлено: {len(new_features_to_append)}")
    else:
        # Если база не существует (первый запуск инкрементального режима)
        print("База данных не найдена. Создается новая (Batch History).")
        # Переключаемся в режим полной записи (чтобы создать таблицу)
        run_batch_history(engine)
        
    print("="*70)


if __name__ == '__main__':
    engine = get_db_engine()
    if engine is None:
        exit(1) # Выход, если не удалось подключиться к БД

    # ПЕРВЫЙ ЗАПУСК: Раскомментируйте, чтобы создать полную историческую базу (на 2 года).
    # После первого успешного запуска эту строку нужно закомментировать!
    run_batch_history(engine) 
    
    # ЕЖЕЧАСНОЕ ОБНОВЛЕНИЕ: Эта функция должна быть в cron/планировщике.
    run_incremental_update(engine)