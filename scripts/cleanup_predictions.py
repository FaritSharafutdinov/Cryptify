#!/usr/bin/env python3
"""
Скрипт для очистки старых прогнозов из базы данных.
Удаляет все прогнозы старше указанного количества часов.
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

# Импортируем настройки из общего конфига
try:
    from config import (
        DATABASE_URL_SQLALCHEMY
    )
    DB_URL = DATABASE_URL_SQLALCHEMY
except ImportError:
    # Fallback для обратной совместимости
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "criptify_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "criptify_password")
    DB_NAME = os.getenv("DB_NAME", "criptify_db")
    DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

ENGINE = create_engine(DB_URL)

def cleanup_old_predictions(keep_hours: int = 48, dry_run: bool = False):
    """
    Удаляет старые прогнозы, оставляя только последние N часов.
    
    Args:
        keep_hours: Количество часов прогнозов для сохранения (по умолчанию 48 часов = 2 дня)
        dry_run: Если True, только показывает что будет удалено, не удаляет
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=keep_hours)
    
    # Сначала посчитаем сколько будет удалено
    count_sql = text("""
        SELECT COUNT(*) 
        FROM predictions 
        WHERE time < :cutoff_time
    """)
    
    try:
        with ENGINE.connect() as connection:
            count_result = connection.execute(count_sql, {"cutoff_time": cutoff_time})
            count = count_result.scalar()
        
        if count == 0:
            print(f"✅ Старых прогнозов для удаления не найдено (сохраняем последние {keep_hours} часов)")
            return
        
        print(f"📊 Найдено {count} старых прогнозов для удаления (старше {cutoff_time} UTC)")
        print(f"   Будет сохранено: прогнозы за последние {keep_hours} часов")
        
        if dry_run:
            print("🔍 Режим проверки (dry-run): удаление не выполнено")
            return
        
        # Подтверждение
        print(f"\n⚠️  ВНИМАНИЕ: Будет удалено {count} записей!")
        response = input("Продолжить? (yes/no): ")
        
        if response.lower() not in ['yes', 'y', 'да', 'д']:
            print("❌ Отменено")
            return
        
        # Удаление
        delete_sql = text("""
            DELETE FROM predictions 
            WHERE time < :cutoff_time
        """)
        
        with ENGINE.begin() as connection:
            result = connection.execute(delete_sql, {"cutoff_time": cutoff_time})
            deleted_count = result.rowcount
        
        print(f"✅ Успешно удалено {deleted_count} старых прогнозов")
        
        # Показываем сколько осталось
        remaining_sql = text("SELECT COUNT(*) FROM predictions")
        with ENGINE.connect() as connection:
            remaining = connection.execute(remaining_sql).scalar()
        print(f"📊 Осталось прогнозов в базе: {remaining}")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке старых прогнозов: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Очистка старых прогнозов из базы данных")
    parser.add_argument(
        "--keep-hours",
        type=int,
        default=48,
        help="Количество часов прогнозов для сохранения (по умолчанию: 48 = 2 дня)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Режим проверки: показать что будет удалено, но не удалять"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Удалить ВСЕ прогнозы (осторожно!)"
    )
    
    args = parser.parse_args()
    
    if args.all:
        print("⚠️  ВНИМАНИЕ: Будет удалено ВСЕ прогнозы из базы данных!")
        response = input("Вы уверены? (yes/no): ")
        if response.lower() not in ['yes', 'y', 'да', 'д']:
            print("❌ Отменено")
            sys.exit(0)
        
        try:
            delete_all_sql = text("DELETE FROM predictions")
            with ENGINE.begin() as connection:
                result = connection.execute(delete_all_sql)
                deleted_count = result.rowcount
            print(f"✅ Удалено всех прогнозов: {deleted_count}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            sys.exit(1)
    else:
        cleanup_old_predictions(keep_hours=args.keep_hours, dry_run=args.dry_run)

