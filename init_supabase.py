#!/usr/bin/env python3
"""
Инициализация таблиц в Supabase

Этот скрипт создает все необходимые таблицы в Supabase
и инициализирует базовую структуру тем.
"""

import asyncio
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

from src.db.connection_manager import get_connection_manager
from src.db.models import DatabaseModels

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def init_supabase():
    """Инициализация Supabase базы данных"""
    print("🚀 Инициализация Supabase...")
    
    # Проверяем connection manager
    manager = get_connection_manager()
    if not manager.is_postgresql():
        print("❌ DATABASE_TYPE должен быть 'supabase' или 'postgresql'")
        return False
    
    print(f"✅ Connection Manager: {manager.db_type.value}")
    
    try:
        # Инициализируем модели
        models = DatabaseModels()
        table_definitions = models.get_table_definitions()
        indexes = models.get_indexes()
        
        print(f"📋 Создание {len(table_definitions)} таблиц...")
        
        # Создаем таблицы
        async with manager.get_async_connection() as conn:
            for table_name, table_sql in table_definitions.items():
                try:
                    await conn.execute(table_sql)
                    print(f"  ✅ {table_name}")
                except Exception as e:
                    print(f"  ❌ {table_name}: {e}")
                    raise
            
            print(f"\n🔍 Создание {len(indexes)} индексов...")
            
            # Создаем индексы
            for index_sql in indexes:
                try:
                    await conn.execute(index_sql)
                except Exception as e:
                    # Индексы могут уже существовать
                    if "already exists" not in str(e):
                        print(f"  ⚠️ Ошибка создания индекса: {e}")
            
            print("  ✅ Индексы созданы")
            
            # Инициализируем базовые темы
            await init_topics(conn)
            
            # Проверим результат
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            
            print(f"\n📊 Результат:")
            print(f"  Создано таблиц: {len(tables)}")
            for table in tables:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM {table["table_name"]}')
                print(f"    {table['table_name']}: {count} записей")
        
        print("\n🎉 Supabase успешно инициализирован!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        return False

async def init_topics(conn):
    """Инициализация базовых тем"""
    print("\n📚 Инициализация тем...")
    
    topics_data = {
        'ru': {
            'Математика': ['Алгебра', 'Геометрия', 'Арифметика', 'Тригонометрия'],
            'Физика': ['Механика', 'Термодинамика', 'Электричество', 'Оптика'],
            'Химия': ['Органическая химия', 'Неорганическая химия', 'Аналитическая химия'],
            'Биология': ['Ботаника', 'Зоология', 'Анатомия', 'Генетика']
        },
        'kk': {
            'Математика': ['Алгебра', 'Геометрия', 'Арифметика', 'Тригонометрия'],
            'Физика': ['Механика', 'Термодинамика', 'Электр', 'Оптика'],
            'Химия': ['Органикалық химия', 'Бейорганикалық химия', 'Аналитикалық химия'],
            'Биология': ['Ботаника', 'Зоология', 'Анатомия', 'Генетика']
        }
    }
    
    for language, main_topics in topics_data.items():
        for main_topic_name, subtopics in main_topics.items():
            # Создаем главную тему
            main_topic_id = await conn.fetchval("""
                INSERT INTO main_topics (topic_name, language)
                VALUES ($1, $2)
                ON CONFLICT (topic_name, language) DO UPDATE SET topic_name = EXCLUDED.topic_name
                RETURNING id
            """, main_topic_name, language)
            
            # Создаем подтемы
            for subtopic_name in subtopics:
                await conn.execute("""
                    INSERT INTO subtopics (main_topic_id, subtopic_name)
                    VALUES ($1, $2)
                    ON CONFLICT (subtopic_name, main_topic_id) DO NOTHING
                """, main_topic_id, subtopic_name)
    
    print("  ✅ Темы инициализированы")

if __name__ == "__main__":
    success = asyncio.run(init_supabase())
    if success:
        print("\n✅ Готово! Теперь можно запускать бота с Supabase.")
    else:
        print("\n❌ Инициализация не удалась.")
        exit(1) 