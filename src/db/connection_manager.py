"""
Connection Manager for Supabase Database Operations

Provides unified interface for Supabase PostgreSQL connections with connection pooling.
"""

import os
import asyncio
import asyncpg
import logging
import socket
from typing import Optional, Any, AsyncGenerator
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages Supabase database connections with pooling support"""
    
    def __init__(self):
        self._pool = None
        self._tables_initialized = False
        self.connection_string = self._get_connection_string()
        logger.info("Initialized ConnectionManager for Supabase")
    
    def _get_connection_string(self) -> str:
        """Get Supabase connection string from environment variables"""
        conn_str = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DATABASE_URL')
        if not conn_str:
            raise ValueError(
                "Supabase connection string not found. "
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
        """Initialize basic topics data"""
        topics_data = [
            ('Математика', 'ru'),
            ('Физика', 'ru'),
            ('Химия', 'ru'),
            ('Биология', 'ru'),
            ('Математика', 'kk'),
            ('Физика', 'kk'),
            ('Химия', 'kk'),
            ('Биология', 'kk'),
        ]
        
        for topic_name, language in topics_data:
            await conn.execute("""
                INSERT INTO main_topics (topic_name, language)
                VALUES ($1, $2)
                ON CONFLICT (topic_name, language) DO NOTHING
            """, topic_name, language)
        
        logger.info("Initialized basic topics data")

    async def initialize_pool(self, min_size: int = 1, max_size: int = 10):
        """Initialize connection pool for Supabase"""
        if not self._pool and not hasattr(self, '_fallback_conn'):
            try:
                self._pool = await asyncpg.create_pool(
                    self.connection_string,
                    min_size=min_size,
                    max_size=max_size,
                    command_timeout=60,
                    server_settings={
                        'application_name': 'go2study_bot',
                    },
                    ssl=None,  # Явно устанавливаем None для избежания проблем
                    statement_cache_size=0  # Отключаем кэш для стабильности
                )
                logger.info(f"Supabase connection pool initialized (min={min_size}, max={max_size})")
                
                # Initialize tables on first connection
                async with self._pool.acquire() as conn:
                    await self._check_and_create_tables(conn)
                    
            except Exception as e:
                logger.error(f"Failed to initialize Supabase pool: {e}")
                # Try fallback with single connection
                try:
                    await self._try_fallback_connection()
                except Exception as fallback_error:
                    logger.error(f"Fallback connection also failed: {fallback_error}")
                    raise

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
                ssl=None
            )
            logger.info("Fallback connection successful - using single connection mode")
            
            # Initialize tables with fallback connection
            await self._check_and_create_tables(self._fallback_conn)
            return
            
        except Exception as e:
            last_error = e
            logger.error(f"Direct connection failed: {e}")
            
            # Try with IPv4 resolution if possible
            if 'supabase.co' in self.connection_string:
                try:
                    import re
                    # Extract host from connection string
                    host_match = re.search(r'@([^:]+):', self.connection_string)
                    if host_match:
                        original_host = host_match.group(1)
                        logger.info(f"Attempting to resolve {original_host} to IPv4...")
                        
                        # Try to resolve to IPv4
                        try:
                            import socket
                            ipv4_addr = socket.getaddrinfo(original_host, None, socket.AF_INET)[0][4][0]
                            modified_conn_str = self.connection_string.replace(original_host, ipv4_addr)
                            logger.info(f"Resolved {original_host} to {ipv4_addr}")
                            
                            self._fallback_conn = await asyncpg.connect(
                                modified_conn_str,
                                command_timeout=30,
                                server_settings={
                                    'application_name': 'go2study_bot_ipv4',
                                },
                                ssl=None
                            )
                            logger.info("Fallback connection successful with IPv4 address")
                            
                            # Initialize tables with fallback connection
                            await self._check_and_create_tables(self._fallback_conn)
                            return
                            
                        except socket.gaierror as e:
                            last_error = e
                            logger.warning(f"Failed to resolve {original_host} to IPv4: {e}")
                        
                except Exception as e:
                    last_error = e
                    logger.warning(f"Failed to modify connection string: {e}")
            
            # If all fails, raise the last error
            raise Exception(f"All connection attempts failed: {last_error}")

    async def close_pool(self):
        """Close connection pool or fallback connection"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Supabase connection pool closed")
        
        if hasattr(self, '_fallback_conn') and self._fallback_conn:
            await self._fallback_conn.close()
            self._fallback_conn = None
            logger.info("Supabase fallback connection closed")
    
    @asynccontextmanager
    async def get_async_connection(self) -> AsyncGenerator[Any, None]:
        """Get async Supabase database connection"""
        if not self._pool and not hasattr(self, '_fallback_conn'):
            await self.initialize_pool()
        
        # Use pool if available
        if self._pool:
            conn = None
            try:
                conn = await asyncio.wait_for(self._pool.acquire(), timeout=10.0)
                yield conn
            except asyncio.TimeoutError:
                logger.error("Timeout acquiring database connection from pool")
                raise
            except Exception as e:
                logger.error(f"Error acquiring database connection from pool: {e}")
                raise
            finally:
                if conn:
                    try:
                        await self._pool.release(conn)
                    except Exception as e:
                        logger.error(f"Error releasing database connection: {e}")
        
        # Use fallback connection if pool is not available
        elif hasattr(self, '_fallback_conn') and self._fallback_conn:
            try:
                # Check if connection is still alive
                await self._fallback_conn.fetchval("SELECT 1")
                yield self._fallback_conn
            except Exception as e:
                logger.error(f"Fallback connection failed: {e}")
                # Try to reconnect
                try:
                    await self._try_fallback_connection()
                    yield self._fallback_conn
                except Exception as reconnect_error:
                    logger.error(f"Failed to reconnect: {reconnect_error}")
                    raise
        else:
            raise RuntimeError("No available PostgreSQL connection")

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