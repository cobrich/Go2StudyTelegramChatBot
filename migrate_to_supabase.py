#!/usr/bin/env python3
"""
🚀 Go2Study Bot Migration Script: Neon → Supabase

Этот скрипт переносит все данные из Neon PostgreSQL в Supabase PostgreSQL.
Выполняет полную миграцию с сохранением структуры данных.
"""

import os
import sys
import psycopg2
import logging
from urllib.parse import urlparse
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Класс для миграции данных между PostgreSQL базами"""
    
    def __init__(self, source_url: str, target_url: str):
        self.source_url = source_url
        self.target_url = target_url
        self.source_conn = None
        self.target_conn = None
    
    def _parse_db_url(self, url: str) -> Dict[str, Any]:
        """Парсинг URL подключения к базе данных"""
        parsed = urlparse(url)
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:],
            'user': parsed.username,
            'password': parsed.password,
            'sslmode': 'require'
        }
    
    def connect_databases(self):
        """Подключение к исходной и целевой базам данных"""
        try:
            logger.info("🔗 Connecting to source database (Neon)...")
            source_params = self._parse_db_url(self.source_url)
            self.source_conn = psycopg2.connect(**source_params)
            logger.info("✅ Connected to source database")
            
            logger.info("🔗 Connecting to target database (Supabase)...")
            target_params = self._parse_db_url(self.target_url)
            self.target_conn = psycopg2.connect(**target_params)
            logger.info("✅ Connected to target database")
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def get_table_structure(self, conn, table_name: str) -> str:
        """Получение структуры таблицы"""
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            return cursor.fetchall()
    
    def get_all_tables(self, conn) -> List[str]:
        """Получение списка всех таблиц"""
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            return [row[0] for row in cursor.fetchall()]
    
    def create_table_structure(self):
        """Создание структуры таблиц в целевой базе"""
        logger.info("🏗️ Creating table structure in target database...")
        
        # Получаем SQL схему из исходной базы
        with self.source_conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    'CREATE TABLE ' || tablename || ' (' ||
                    string_agg(column_definition, ', ') || ');'
                FROM (
                    SELECT 
                        t.tablename,
                        a.attname || ' ' || 
                        format_type(a.atttypid, a.atttypmod) ||
                        CASE 
                            WHEN a.attnotnull THEN ' NOT NULL'
                            ELSE ''
                        END ||
                        CASE 
                            WHEN a.atthasdef THEN ' DEFAULT ' || d.adsrc
                            ELSE ''
                        END as column_definition
                    FROM pg_tables t
                    JOIN pg_class c ON c.relname = t.tablename
                    JOIN pg_attribute a ON a.attrelid = c.oid
                    LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
                    WHERE t.schemaname = 'public'
                    AND a.attnum > 0
                    AND NOT a.attisdropped
                    ORDER BY t.tablename, a.attnum
                ) subq
                GROUP BY tablename
                ORDER BY tablename
            """)
            
            create_statements = cursor.fetchall()
            
        # Выполняем создание таблиц в целевой базе
        with self.target_conn.cursor() as cursor:
            for statement in create_statements:
                try:
                    cursor.execute(statement[0])
                    logger.info(f"✅ Created table structure")
                except Exception as e:
                    logger.warning(f"⚠️ Table creation warning: {e}")
        
        self.target_conn.commit()
        logger.info("✅ Table structure created successfully")
    
    def migrate_data(self):
        """Миграция данных из всех таблиц"""
        tables = self.get_all_tables(self.source_conn)
        logger.info(f"📊 Found {len(tables)} tables to migrate")
        
        for table in tables:
            logger.info(f"📁 Migrating table: {table}")
            
            # Получаем данные из исходной таблицы
            with self.source_conn.cursor() as source_cursor:
                source_cursor.execute(f"SELECT * FROM {table}")
                rows = source_cursor.fetchall()
                
                if not rows:
                    logger.info(f"📝 Table {table} is empty, skipping")
                    continue
                
                # Получаем названия колонок
                column_names = [desc[0] for desc in source_cursor.description]
                
            # Вставляем данные в целевую таблицу
            with self.target_conn.cursor() as target_cursor:
                # Создаем плейсхолдеры для вставки
                placeholders = ', '.join(['%s'] * len(column_names))
                columns_str = ', '.join(column_names)
                
                insert_sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
                
                try:
                    target_cursor.executemany(insert_sql, rows)
                    self.target_conn.commit()
                    logger.info(f"✅ Migrated {len(rows)} rows to {table}")
                except Exception as e:
                    logger.error(f"❌ Error migrating {table}: {e}")
                    self.target_conn.rollback()
                    continue
    
    def verify_migration(self):
        """Проверка успешности миграции"""
        logger.info("🔍 Verifying migration...")
        
        tables = self.get_all_tables(self.source_conn)
        
        for table in tables:
            # Подсчет записей в исходной базе
            with self.source_conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                source_count = cursor.fetchone()[0]
            
            # Подсчет записей в целевой базе
            with self.target_conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                target_count = cursor.fetchone()[0]
            
            if source_count == target_count:
                logger.info(f"✅ {table}: {source_count} rows migrated successfully")
            else:
                logger.error(f"❌ {table}: source={source_count}, target={target_count}")
        
        logger.info("✅ Migration verification completed")
    
    def close_connections(self):
        """Закрытие соединений с базами данных"""
        if self.source_conn:
            self.source_conn.close()
        if self.target_conn:
            self.target_conn.close()
        logger.info("🔒 Database connections closed")

def main():
    """Главная функция миграции"""
    logger.info("🚀 Starting Neon → Supabase migration")
    
    # Получаем URL подключений из переменных окружения
    neon_url = os.getenv('NEON_DATABASE_URL')
    supabase_url = os.getenv('SUPABASE_DATABASE_URL') or os.getenv('DATABASE_URL')
    
    if not neon_url:
        logger.error("❌ NEON_DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    if not supabase_url:
        logger.error("❌ SUPABASE_DATABASE_URL or DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    migrator = DatabaseMigrator(neon_url, supabase_url)
    
    try:
        # Подключаемся к базам данных
        migrator.connect_databases()
        
        # Создаем структуру таблиц
        migrator.create_table_structure()
        
        # Мигрируем данные
        migrator.migrate_data()
        
        # Проверяем миграцию
        migrator.verify_migration()
        
        logger.info("🎉 Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)
    
    finally:
        migrator.close_connections()

if __name__ == "__main__":
    main() 