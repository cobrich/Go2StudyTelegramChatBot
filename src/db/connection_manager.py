"""
Connection Manager for Neon PostgreSQL Database Operations

Provides unified interface for Neon PostgreSQL connections with connection pooling.
"""

import os
import asyncio
import asyncpg
import logging
import socket
from typing import Optional, Any, AsyncGenerator
from contextlib import asynccontextmanager
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages Neon PostgreSQL database connections with pooling support"""
    
    def __init__(self):
        self._pool = None
        self._tables_initialized = False
        self.connection_string = self._get_connection_string()
        logger.info("Initialized ConnectionManager for Neon PostgreSQL")
    
    def _get_connection_string(self) -> str:
        """Get Neon PostgreSQL connection string from environment variables"""
        conn_str = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DATABASE_URL')
        if not conn_str:
            raise ValueError(
                "Neon PostgreSQL connection string not found. "
                "Please set DATABASE_URL or SUPABASE_DATABASE_URL environment variable."
            )
        return conn_str
    
    async def _check_and_create_tables(self, conn):
        """Check if tables exist and create them if they don't"""
        if self._tables_initialized:
            return
        
        try:
            # Check if main_topics table exists
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'main_topics'
                )
            """)
            
            if not result:
                logger.info("Tables not found. Creating database schema...")
                await self._create_tables(conn)
                await self._init_basic_data(conn)
                logger.info("Database schema created successfully")
            else:
                logger.info("Database tables already exist")
            
            self._tables_initialized = True
            
        except Exception as e:
            logger.error(f"Error checking/creating tables: {e}")
            raise
    
    async def _create_tables(self, conn):
        """Create all necessary tables"""
        tables = {
            'admins': '''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    is_super_admin BOOLEAN DEFAULT FALSE,
                    created_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'allowed_users': '''
                CREATE TABLE IF NOT EXISTS allowed_users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT UNIQUE,
                    full_name TEXT,
                    grade INTEGER CHECK (grade IN (5, 6)),
                    added_by BIGINT REFERENCES admins(user_id),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT FALSE,
                    language TEXT DEFAULT 'ru' CHECK (language IN ('ru', 'kk')),
                    current_topic TEXT,
                    last_activity TIMESTAMP,
                    has_access BOOLEAN DEFAULT TRUE
                )
            ''',
            
            'main_topics': '''
                CREATE TABLE IF NOT EXISTS main_topics (
                    id SERIAL PRIMARY KEY,
                    topic_name TEXT NOT NULL,
                    language TEXT NOT NULL CHECK (language IN ('ru', 'kk')),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(topic_name, language)
                )
            ''',
            
            'subtopics': '''
                CREATE TABLE IF NOT EXISTS subtopics (
                    id SERIAL PRIMARY KEY,
                    subtopic_name TEXT NOT NULL,
                    main_topic_id INTEGER NOT NULL REFERENCES main_topics(id) ON DELETE CASCADE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(subtopic_name, main_topic_id)
                )
            ''',
            
            'questions': '''
                CREATE TABLE IF NOT EXISTS questions (
                    id SERIAL PRIMARY KEY,
                    question_text TEXT NOT NULL,
                    option_a TEXT NOT NULL,
                    option_b TEXT NOT NULL,
                    option_c TEXT NOT NULL,
                    option_d TEXT NOT NULL,
                    correct_answer TEXT NOT NULL CHECK (correct_answer IN ('A', 'B', 'C', 'D')),
                    topic_id INTEGER NOT NULL REFERENCES subtopics(id) ON DELETE CASCADE,
                    source TEXT DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'test_results': '''
                CREATE TABLE IF NOT EXISTS test_results (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES allowed_users(user_id),
                    topic_id INTEGER NOT NULL REFERENCES subtopics(id),
                    percentage REAL NOT NULL CHECK (percentage >= 0 AND percentage <= 100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'user_errors': '''
                CREATE TABLE IF NOT EXISTS user_errors (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES allowed_users(user_id),
                    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                    user_answer TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    error_count INTEGER DEFAULT 1,
                    first_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, question_id)
                )
            '''
        }
        
        # Create tables
        for table_name, table_sql in tables.items():
            await conn.execute(table_sql)
            logger.info(f"Created table: {table_name}")
        
        # Create indexes
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_allowed_users_user_id ON allowed_users(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_questions_topic_id ON questions(topic_id)',
            'CREATE INDEX IF NOT EXISTS idx_test_results_user_id ON test_results(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_test_results_topic_id ON test_results(topic_id)',
            'CREATE INDEX IF NOT EXISTS idx_user_errors_user_id ON user_errors(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_user_errors_question_id ON user_errors(question_id)',
            'CREATE INDEX IF NOT EXISTS idx_subtopics_main_topic_id ON subtopics(main_topic_id)',
            'CREATE INDEX IF NOT EXISTS idx_allowed_users_is_active ON allowed_users(is_active)',
            'CREATE INDEX IF NOT EXISTS idx_main_topics_language ON main_topics(language)',
            'CREATE INDEX IF NOT EXISTS idx_questions_source ON questions(source)',
        ]
        
        for index_sql in indexes:
            await conn.execute(index_sql)
        
        logger.info("Created database indexes")
    
    async def _init_basic_data(self, conn):
        """Initialize full topic structure from constants.py"""
        try:
            # Импортируем иерархию тем с правильным путем
            from pathlib import Path
            
            # Добавляем src в путь если его нет
            src_path = Path(__file__).parent.parent
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))
            
            from config.constants import TOPIC_HIERARCHY
            
            logger.info("Initializing full topic structure...")
            
            # Проверяем, есть ли уже темы в БД
            existing_count = await conn.fetchval(
                "SELECT COUNT(*) FROM main_topics WHERE topic_name = ANY($1)",
                list(TOPIC_HIERARCHY.keys())
            )
            
            if existing_count > 0:
                logger.info(f"Found {existing_count} existing main topics, skipping initialization")
                return
            
            logger.info(f"Creating {len(TOPIC_HIERARCHY)} main topic sections with subtopics...")
            
            # Создаем основные темы и подтемы для русского и казахского языков
            languages = ['ru', 'kk']
            total_main_topics = 0
            total_subtopics = 0
            
            for language in languages:
                lang_name = 'Русский' if language == 'ru' else 'Казахский'
                logger.info(f"Processing language: {lang_name}")
                
                for main_topic, subtopics in TOPIC_HIERARCHY.items():
                    # Создаем основную тему
                    main_topic_id = await conn.fetchval("""
                        INSERT INTO main_topics (topic_name, language, is_active)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (topic_name, language) DO UPDATE SET
                            is_active = EXCLUDED.is_active
                        RETURNING id
                    """, main_topic, language, True)
                    
                    if main_topic_id:
                        total_main_topics += 1
                        logger.info(f"  ✅ Created main topic: {main_topic} (ID: {main_topic_id})")
                        
                        # Создаем подтемы
                        for subtopic in subtopics:
                            await conn.execute("""
                                INSERT INTO subtopics (subtopic_name, main_topic_id, is_active)
                                VALUES ($1, $2, $3)
                                ON CONFLICT (subtopic_name, main_topic_id) DO UPDATE SET
                                    is_active = EXCLUDED.is_active
                            """, subtopic, main_topic_id, True)
                            total_subtopics += 1
                            logger.debug(f"    • Created subtopic: {subtopic}")
            
            logger.info(f"✅ Initialized full topic structure: {total_main_topics} main topics, {total_subtopics} subtopics")
            
            # Логируем статистику
            final_main_count = await conn.fetchval("SELECT COUNT(*) FROM main_topics WHERE is_active = true")
            final_sub_count = await conn.fetchval("SELECT COUNT(*) FROM subtopics WHERE is_active = true")
            logger.info(f"📊 Final statistics: {final_main_count} main topics, {final_sub_count} subtopics")
            
        except Exception as e:
            logger.error(f"Error initializing topic structure: {e}")
            logger.warning("⚠️ Skipping topic initialization - will need to run init_topics.py manually")
            # Не создаем fallback темы - пусть пользователь сам запустит init_topics.py

    async def initialize_pool(self, min_size: int = 1, max_size: int = 10):
        """Initialize connection pool for Neon PostgreSQL"""
        if self._pool:
            # Пул уже инициализирован
            return
            
        if hasattr(self, '_fallback_conn') and self._fallback_conn:
            # Fallback соединение уже есть
            return
            
        try:
            logger.info("Initializing Neon PostgreSQL connection pool...")
            self._pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=min_size,
                max_size=max_size,
                command_timeout=30,  # Уменьшаем таймаут
                server_settings={
                    'application_name': 'go2study_bot',
                },
                # Убираем ssl=None для Neon - используем настройки из строки подключения
                statement_cache_size=0  # Отключаем кэш для стабильности
            )
            logger.info(f"Neon PostgreSQL connection pool initialized (min={min_size}, max={max_size})")
            
            # Initialize tables on first connection
            try:
                async with self._pool.acquire() as conn:
                    await self._check_and_create_tables(conn)
            except Exception as table_error:
                logger.warning(f"Could not initialize tables through pool: {table_error}")
                # Не падаем из-за ошибок инициализации таблиц
                    
        except Exception as e:
            logger.error(f"Failed to initialize Neon PostgreSQL pool: {e}")
            self._pool = None  # Убеждаемся, что пул не в частично инициализированном состоянии
            
            # Try fallback with single connection
            try:
                await self._try_fallback_connection()
            except Exception as fallback_error:
                logger.error(f"Fallback connection also failed: {fallback_error}")
                # Не поднимаем исключение - позволяем приложению продолжить работу
                # Соединение будет создано при первом обращении к базе

    async def _try_fallback_connection(self):
        """Try fallback connection with single persistent connection"""
        last_error = None
        
        try:
            logger.info("Attempting fallback connection with single connection...")
            
            # Try direct connection without pool
            self._fallback_conn = await asyncpg.connect(
                self.connection_string,
                command_timeout=30,
                server_settings={
                    'application_name': 'go2study_bot_fallback',
                },
                # Убираем ssl=None для Neon - используем настройки из строки подключения
            )
            logger.info("Fallback connection successful - using single connection mode")
            
            # Initialize tables with fallback connection
            await self._check_and_create_tables(self._fallback_conn)
            return
            
        except Exception as e:
            last_error = e
            logger.error(f"Direct connection failed: {e}")
            
            # Убираем логику для supabase.co, так как используем Neon
            # If all fails, raise the last error
            raise Exception(f"Connection to Neon PostgreSQL failed: {last_error}")

    async def close_pool(self):
        """Close connection pool or fallback connection"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Neon PostgreSQL connection pool closed")
        
        if hasattr(self, '_fallback_conn') and self._fallback_conn:
            await self._fallback_conn.close()
            self._fallback_conn = None
            logger.info("Neon PostgreSQL fallback connection closed")
    
    @asynccontextmanager
    async def get_async_connection(self) -> AsyncGenerator[Any, None]:
        """Get async Neon PostgreSQL database connection"""
        if not self._pool and not hasattr(self, '_fallback_conn'):
            await self.initialize_pool()
        
        # Use pool if available
        if self._pool:
            conn = None
            try:
                conn = await asyncio.wait_for(self._pool.acquire(), timeout=10.0)
                # Проверяем соединение перед использованием
                await conn.fetchval("SELECT 1")
                yield conn
            except asyncio.TimeoutError:
                logger.error("Timeout acquiring database connection from pool")
                # Попробуем fallback соединение
                if hasattr(self, '_fallback_conn') and self._fallback_conn:
                    try:
                        await self._fallback_conn.fetchval("SELECT 1")
                        yield self._fallback_conn
                        return
                    except Exception:
                        pass
                raise RuntimeError("Database connection timeout")
            except Exception as e:
                logger.error(f"Error acquiring database connection from pool: {e}")
                # Попробуем fallback соединение
                if hasattr(self, '_fallback_conn') and self._fallback_conn:
                    try:
                        await self._fallback_conn.fetchval("SELECT 1")
                        yield self._fallback_conn
                        return
                    except Exception:
                        pass
                raise RuntimeError(f"Database connection error: {e}")
            finally:
                if conn and self._pool:
                    try:
                        # Проверяем, что соединение еще живо перед возвратом в пул
                        if not conn.is_closed():
                            await self._pool.release(conn)
                    except Exception as e:
                        logger.error(f"Error releasing database connection: {e}")
                        # Если не можем вернуть соединение в пул, закрываем его
                        try:
                            await conn.close()
                        except Exception:
                            pass
        
        # Use fallback connection if pool is not available
        elif hasattr(self, '_fallback_conn') and self._fallback_conn:
            try:
                # Check if connection is still alive
                if self._fallback_conn.is_closed():
                    raise Exception("Fallback connection is closed")
                    
                await self._fallback_conn.fetchval("SELECT 1")
                yield self._fallback_conn
            except Exception as e:
                logger.error(f"Fallback connection failed: {e}")
                # Try to reconnect
                try:
                    await self._try_fallback_connection()
                    if hasattr(self, '_fallback_conn') and self._fallback_conn:
                        yield self._fallback_conn
                    else:
                        raise RuntimeError("Failed to establish fallback connection")
                except Exception as reconnect_error:
                    logger.error(f"Failed to reconnect: {reconnect_error}")
                    raise RuntimeError(f"Database connection failed: {reconnect_error}")
        else:
            # Последняя попытка - создать новое соединение
            try:
                await self.initialize_pool()
                # Рекурсивно вызываем себя после инициализации
                async with self.get_async_connection() as conn:
                    yield conn
            except Exception as e:
                logger.error(f"Failed to initialize connection: {e}")
                raise RuntimeError("No available Neon PostgreSQL connection")

# Global connection manager instance
_connection_manager = None

def get_connection_manager() -> ConnectionManager:
    """Get global connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager

def get_database_connection():
    """Get database connection (backwards compatibility)"""
    return get_connection_manager()

# Convenience functions
async def get_async_db_connection():
    """Get async database connection"""
    manager = get_connection_manager()
    return manager.get_async_connection() 