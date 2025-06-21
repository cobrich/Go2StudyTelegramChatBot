#!/usr/bin/env python3
"""
Миграция данных с SQLite на Supabase

Этот скрипт переносит все данные из локальной SQLite базы данных в Supabase.
"""

import asyncio
import sqlite3
import logging
from typing import Dict, List, Any
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

from src.db.connection_manager import get_connection_manager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SQLiteToSupabaseMigrator:
    """Класс для миграции данных с SQLite на Supabase"""
    
    def __init__(self, sqlite_path: str = "math_bot.db"):
        self.sqlite_path = sqlite_path
        self.connection_manager = get_connection_manager()
        
    async def migrate_all_data(self):
        """Мигрировать все данные"""
        print("🚀 Начинаем миграцию данных с SQLite на Supabase...")
        
        # Проверяем наличие SQLite файла
        try:
            sqlite_conn = sqlite3.connect(self.sqlite_path)
            sqlite_conn.row_factory = sqlite3.Row
            print(f"✅ SQLite база найдена: {self.sqlite_path}")
        except Exception as e:
            print(f"❌ Ошибка подключения к SQLite: {e}")
            return False
        
        try:
            async with self.connection_manager.get_async_connection() as supabase_conn:
                print("✅ Подключение к Supabase установлено")
                
                # Мигрируем в правильном порядке (с учетом внешних ключей)
                await self._migrate_admins(sqlite_conn, supabase_conn)
                await self._migrate_allowed_users(sqlite_conn, supabase_conn)
                await self._migrate_main_topics(sqlite_conn, supabase_conn)
                await self._migrate_subtopics(sqlite_conn, supabase_conn)
                await self._migrate_questions(sqlite_conn, supabase_conn)
                await self._migrate_test_results(sqlite_conn, supabase_conn)
                await self._migrate_user_errors(sqlite_conn, supabase_conn)
                
                print("\n🎉 Миграция завершена успешно!")
                return True
                
        except Exception as e:
            print(f"❌ Ошибка миграции: {e}")
            return False
        finally:
            sqlite_conn.close()
    
    async def _migrate_admins(self, sqlite_conn, supabase_conn):
        """Мигрировать администраторов"""
        print("\n👥 Миграция администраторов...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM admins")
        rows = cursor.fetchall()
        
        if not rows:
            print("  ⚠️ Нет данных для миграции")
            return
        
        for row in rows:
            await supabase_conn.execute("""
                INSERT INTO admins (user_id, username, full_name, is_super_admin, created_by, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    is_super_admin = EXCLUDED.is_super_admin,
                    updated_at = CURRENT_TIMESTAMP
            """, 
            row['user_id'], row['username'], row['full_name'], 
            bool(row['is_super_admin']), row['created_by'], 
            row['created_at'], row['updated_at'])
        
        print(f"  ✅ Мигрировано {len(rows)} администраторов")
    
    async def _migrate_allowed_users(self, sqlite_conn, supabase_conn):
        """Мигрировать разрешенных пользователей"""
        print("\n👤 Миграция пользователей...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM allowed_users")
        rows = cursor.fetchall()
        
        if not rows:
            print("  ⚠️ Нет данных для миграции")
            return
        
        for row in rows:
            await supabase_conn.execute("""
                INSERT INTO allowed_users (
                    user_id, username, full_name, grade, added_by, added_at, updated_at,
                    is_active, language, current_topic, last_activity, has_access
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    grade = EXCLUDED.grade,
                    is_active = EXCLUDED.is_active,
                    language = EXCLUDED.language,
                    current_topic = EXCLUDED.current_topic,
                    last_activity = EXCLUDED.last_activity,
                    has_access = EXCLUDED.has_access,
                    updated_at = CURRENT_TIMESTAMP
            """, 
            row['user_id'], row['username'], row['full_name'], row['grade'],
            row['added_by'], row['added_at'], row['updated_at'],
            bool(row['is_active']), row['language'], row['current_topic'],
            row['last_activity'], bool(row['has_access']))
        
        print(f"  ✅ Мигрировано {len(rows)} пользователей")
    
    async def _migrate_main_topics(self, sqlite_conn, supabase_conn):
        """Мигрировать основные темы"""
        print("\n📚 Миграция основных тем...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM main_topics")
        rows = cursor.fetchall()
        
        if not rows:
            print("  ⚠️ Нет данных для миграции")
            return
        
        for row in rows:
            await supabase_conn.execute("""
                INSERT INTO main_topics (id, topic_name, language, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (topic_name, language) DO UPDATE SET
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
            """, 
            row['id'], row['topic_name'], row['language'],
            bool(row['is_active']), row['created_at'], row['updated_at'])
        
        print(f"  ✅ Мигрировано {len(rows)} основных тем")
    
    async def _migrate_subtopics(self, sqlite_conn, supabase_conn):
        """Мигрировать подтемы"""
        print("\n📖 Миграция подтем...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM subtopics")
        rows = cursor.fetchall()
        
        if not rows:
            print("  ⚠️ Нет данных для миграции")
            return
        
        for row in rows:
            await supabase_conn.execute("""
                INSERT INTO subtopics (id, subtopic_name, main_topic_id, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (subtopic_name, main_topic_id) DO UPDATE SET
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
            """, 
            row['id'], row['subtopic_name'], row['main_topic_id'],
            bool(row['is_active']), row['created_at'], row['updated_at'])
        
        print(f"  ✅ Мигрировано {len(rows)} подтем")
    
    async def _migrate_questions(self, sqlite_conn, supabase_conn):
        """Мигрировать вопросы"""
        print("\n❓ Миграция вопросов...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM questions")
        rows = cursor.fetchall()
        
        if not rows:
            print("  ⚠️ Нет данных для миграции")
            return
        
        for row in rows:
            await supabase_conn.execute("""
                INSERT INTO questions (
                    id, question_text, option_a, option_b, option_c, option_d,
                    correct_answer, topic_id, source, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO UPDATE SET
                    question_text = EXCLUDED.question_text,
                    option_a = EXCLUDED.option_a,
                    option_b = EXCLUDED.option_b,
                    option_c = EXCLUDED.option_c,
                    option_d = EXCLUDED.option_d,
                    correct_answer = EXCLUDED.correct_answer,
                    topic_id = EXCLUDED.topic_id,
                    source = EXCLUDED.source,
                    updated_at = CURRENT_TIMESTAMP
            """, 
            row['id'], row['question_text'], row['option_a'], row['option_b'],
            row['option_c'], row['option_d'], row['correct_answer'],
            row['topic_id'], row['source'], row['created_at'], row['updated_at'])
        
        print(f"  ✅ Мигрировано {len(rows)} вопросов")
    
    async def _migrate_test_results(self, sqlite_conn, supabase_conn):
        """Мигрировать результаты тестов"""
        print("\n📊 Миграция результатов тестов...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM test_results")
        rows = cursor.fetchall()
        
        if not rows:
            print("  ⚠️ Нет данных для миграции")
            return
        
        for row in rows:
            await supabase_conn.execute("""
                INSERT INTO test_results (id, user_id, topic_id, percentage, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    topic_id = EXCLUDED.topic_id,
                    percentage = EXCLUDED.percentage,
                    updated_at = CURRENT_TIMESTAMP
            """, 
            row['id'], row['user_id'], row['topic_id'],
            row['percentage'], row['created_at'], row['updated_at'])
        
        print(f"  ✅ Мигрировано {len(rows)} результатов тестов")
    
    async def _migrate_user_errors(self, sqlite_conn, supabase_conn):
        """Мигрировать ошибки пользователей"""
        print("\n❌ Миграция ошибок пользователей...")
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM user_errors")
        rows = cursor.fetchall()
        
        if not rows:
            print("  ⚠️ Нет данных для миграции")
            return
        
        for row in rows:
            await supabase_conn.execute("""
                INSERT INTO user_errors (
                    id, user_id, question_id, user_answer, correct_answer,
                    error_count, first_error_date, last_error_date, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (user_id, question_id) DO UPDATE SET
                    user_answer = EXCLUDED.user_answer,
                    correct_answer = EXCLUDED.correct_answer,
                    error_count = EXCLUDED.error_count,
                    last_error_date = EXCLUDED.last_error_date,
                    updated_at = CURRENT_TIMESTAMP
            """, 
            row['id'], row['user_id'], row['question_id'],
            row['user_answer'], row['correct_answer'], row['error_count'],
            row['first_error_date'], row['last_error_date'], row['updated_at'])
        
        print(f"  ✅ Мигрировано {len(rows)} ошибок пользователей")

async def main():
    """Основная функция миграции"""
    migrator = SQLiteToSupabaseMigrator()
    success = await migrator.migrate_all_data()
    
    if success:
        print("\n✅ Миграция завершена! Теперь можно:")
        print("1. Установить DATABASE_TYPE=supabase в .env файле")
        print("2. Запустить бота с Supabase")
        print("3. Удалить файл math_bot.db после проверки")
    else:
        print("\n❌ Миграция не удалась. Проверьте логи ошибок.")

if __name__ == "__main__":
    asyncio.run(main()) 