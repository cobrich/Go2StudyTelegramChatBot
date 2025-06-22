#!/usr/bin/env python3
"""
Скрипт для инициализации схемы базы данных

Создает все необходимые таблицы и индексы в Neon PostgreSQL.
Должен быть запущен перед первым использованием бота.
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Загружаем переменные окружения
try:
    from dotenv import load_dotenv
    env_path = root_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        print(f"✅ Загружен .env файл: {env_path}")
    else:
        print(f"⚠️ .env файл не найден: {env_path}")
except ImportError:
    print("⚠️ dotenv не установлен - переменные окружения не загружены")

# Импортируем нашу базу данных и модели
from src.db.sync_connection_manager import get_sync_connection_manager
from src.db.models import DatabaseModels

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_database_connection():
    """Проверяем подключение к базе данных"""
    try:
        conn_manager = get_sync_connection_manager()
        result = conn_manager.fetch_val("SELECT 1")
        return result == 1
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        return False

def create_tables():
    """Создаем все таблицы"""
    try:
        print("🏗️ Создаем таблицы...")
        
        conn_manager = get_sync_connection_manager()
        models = DatabaseModels()
        
        # Получаем определения таблиц
        table_definitions = models.get_table_definitions()
        
        # Создаем таблицы в правильном порядке (с учетом внешних ключей)
        table_order = [
            'admins',
            'allowed_users', 
            'main_topics',
            'subtopics',
            'questions',
            'test_results',
            'user_errors'
        ]
        
        for table_name in table_order:
            if table_name in table_definitions:
                print(f"  📋 Создаем таблицу: {table_name}")
                conn_manager.execute_query(table_definitions[table_name])
                print(f"    ✅ Таблица {table_name} создана")
        
        print("✅ Все таблицы созданы")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        return False

def create_indexes():
    """Создаем индексы"""
    try:
        print("🔍 Создаем индексы...")
        
        conn_manager = get_sync_connection_manager()
        models = DatabaseModels()
        
        # Получаем определения индексов
        indexes = models.get_indexes()
        
        for index_sql in indexes:
            try:
                conn_manager.execute_query(index_sql)
                # Извлекаем имя индекса из SQL
                index_name = index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else 'unknown'
                print(f"  ✅ Индекс idx_{index_name} создан")
            except Exception as e:
                print(f"  ⚠️ Индекс пропущен (возможно уже существует): {e}")
        
        print("✅ Индексы созданы")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании индексов: {e}")
        return False

def check_tables_exist():
    """Проверяем, существуют ли таблицы"""
    try:
        conn_manager = get_sync_connection_manager()
        
        # Проверяем основные таблицы
        tables_to_check = ['admins', 'allowed_users', 'main_topics', 'subtopics', 'questions', 'test_results', 'user_errors']
        
        existing_tables = []
        for table in tables_to_check:
            result = conn_manager.fetch_one(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                (table,)
            )
            if result and result.get('exists'):
                existing_tables.append(table)
        
        return existing_tables
        
    except Exception as e:
        print(f"❌ Ошибка при проверке таблиц: {e}")
        return []

def init_database():
    """Основная функция инициализации базы данных"""
    print("🔧 Инициализация схемы базы данных...")
    
    # Проверяем подключение к БД
    if not check_database_connection():
        print("\n❌ ОШИБКА: Нет подключения к базе данных!")
        print("\n🔧 РЕШЕНИЕ:")
        print("1. Проверьте переменные окружения DATABASE_URL")
        print("2. Убедитесь, что PostgreSQL сервер доступен")
        return False
    
    try:
        # Проверяем, существуют ли уже таблицы
        existing_tables = check_tables_exist()
        
        if existing_tables:
            print(f"\n📋 Найдены существующие таблицы: {', '.join(existing_tables)}")
            choice = input("Пересоздать все таблицы? (да/нет): ").lower().strip()
            
            if choice not in ['да', 'yes', 'y', 'д']:
                print("✅ Инициализация пропущена - таблицы уже существуют")
                return True
            
            # Удаляем существующие таблицы в обратном порядке
            print("🗑️ Удаляем существующие таблицы...")
            conn_manager = get_sync_connection_manager()
            
            drop_order = ['user_errors', 'test_results', 'questions', 'subtopics', 'main_topics', 'allowed_users', 'admins']
            for table in drop_order:
                try:
                    conn_manager.execute_query(f"DROP TABLE IF EXISTS {table} CASCADE")
                    print(f"  ✅ Таблица {table} удалена")
                except Exception as e:
                    print(f"  ⚠️ Ошибка удаления {table}: {e}")
        
        # Создаем таблицы
        if not create_tables():
            return False
        
        # Создаем индексы
        if not create_indexes():
            return False
        
        print("\n✅ ИНИЦИАЛИЗАЦИЯ СХЕМЫ ЗАВЕРШЕНА УСПЕШНО!")
        print("\n🎯 РЕЗУЛЬТАТ:")
        print("✅ Все таблицы созданы")
        print("✅ Индексы созданы")
        print("✅ База данных готова к работе")
        print("\n📝 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Запустите: python src/init_superadmin.py")
        print("2. Запустите: python src/init_topics.py")
        print("3. Запустите бота: python main.py")
        
        return True
        
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
        return False

def main():
    """Главная функция"""
    try:
        success = init_database()
        if success:
            print("\n🚀 Инициализация схемы завершена успешно!")
            return 0
        else:
            print("\n💥 Инициализация схемы завершилась с ошибками!")
            return 1
    except KeyboardInterrupt:
        print("\n⚠️ Операция прервана пользователем")
        return 130
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 