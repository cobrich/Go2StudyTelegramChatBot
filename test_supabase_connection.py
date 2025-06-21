#!/usr/bin/env python3
"""
Тестовый скрипт для проверки подключения к Supabase PostgreSQL
"""
import os
import sys
from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_direct_connection():
    """Тест прямого подключения к Supabase"""
    print("=== ТЕСТ 1: Прямое подключение к Supabase ===")
    
    try:
        import asyncio
        import asyncpg
        
        async def connect_test():
            # Ваша строка подключения
            connection_string = "postgresql://postgres.msglxbessktlrormbaxx:beka2004abc@aws-0-eu-north-1.pooler.supabase.com:6543/postgres"
            
            conn = await asyncpg.connect(connection_string)
            print("✅ Прямое подключение к Supabase успешно!")
            
            # Проверим базовые запросы
            version = await conn.fetchval('SELECT version()')
            print(f"📊 Версия PostgreSQL: {version[:50]}...")
            
            # Проверим существующие таблицы
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            if tables:
                print(f"📋 Существующие таблицы ({len(tables)}):")
                for table in tables:
                    print(f"   - {table['table_name']}")
            else:
                print("📋 Таблиц не найдено (новая БД)")
            
            await conn.close()
            return True
            
        return asyncio.run(connect_test())
        
    except Exception as e:
        print(f"❌ Ошибка прямого подключения: {e}")
        return False

def test_supabase_database_class():
    """Тест класса SupabaseDatabase"""
    print("\n=== ТЕСТ 2: Класс SupabaseDatabase ===")
    
    try:
        # Устанавливаем переменные окружения
        os.environ['DATABASE_TYPE'] = 'supabase'
        os.environ['SUPABASE_DATABASE_URL'] = 'postgresql://postgres.msglxbessktlrormbaxx:beka2004abc@aws-0-eu-north-1.pooler.supabase.com:6543/postgres'
        
        from src.services.supabase_database import SupabaseDatabase
        
        print("📦 Создание экземпляра SupabaseDatabase...")
        db = SupabaseDatabase()
        print("✅ SupabaseDatabase создан успешно!")
        
        # Тестируем базовые методы
        print("🔍 Тестирование базовых методов...")
        
        # Тест получения тем
        topics = db.get_all_topics()
        print(f"📋 Получено тем: {len(topics)}")
        
        if topics:
            print("🎯 Первые несколько тем:")
            for topic in topics[:3]:
                print(f"   - {topic.get('name')} ({topic.get('language')})")
        
        # Тест получения вопросов
        questions = db.get_all_questions()
        print(f"❓ Получено вопросов: {len(questions)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка класса SupabaseDatabase: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_config():
    """Тест конфигурации базы данных"""
    print("\n=== ТЕСТ 3: DatabaseConfig ===")
    
    try:
        # Устанавливаем переменные окружения
        os.environ['DATABASE_TYPE'] = 'supabase'
        os.environ['SUPABASE_DATABASE_URL'] = 'postgresql://postgres.msglxbessktlrormbaxx:beka2004abc@aws-0-eu-north-1.pooler.supabase.com:6543/postgres'
        
        from src.config.database_config import get_configured_database, is_using_supabase, get_current_db_type
        
        print(f"🔧 Тип БД: {get_current_db_type()}")
        print(f"🔧 Используется Supabase: {is_using_supabase()}")
        
        print("📦 Получение настроенной БД...")
        db = get_configured_database()
        print(f"✅ Получен экземпляр: {type(db).__name__}")
        
        # Проверяем что это именно Supabase
        from src.services.supabase_database import SupabaseDatabase
        if isinstance(db, SupabaseDatabase):
            print("✅ Тип БД корректный: SupabaseDatabase")
        else:
            print(f"❌ Неожиданный тип БД: {type(db)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка DatabaseConfig: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ С SUPABASE")
    print("=" * 50)
    
    # Загружаем переменные окружения
    load_dotenv()
    
    results = []
    
    # Тест 1: Прямое подключение
    results.append(test_direct_connection())
    
    # Тест 2: Класс SupabaseDatabase
    results.append(test_supabase_database_class())
    
    # Тест 3: DatabaseConfig
    results.append(test_database_config())
    
    # Итоги
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    
    test_names = [
        "Прямое подключение к Supabase",
        "Класс SupabaseDatabase", 
        "DatabaseConfig"
    ]
    
    passed = 0
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{i+1}. {name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Итого: {passed}/{len(results)} тестов пройдено")
    
    if passed == len(results):
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Supabase готов к использованию!")
    else:
        print("⚠️  Есть проблемы, требующие исправления.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 