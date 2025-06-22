"""
Synchronous Connection Manager for Neon PostgreSQL Database Operations

Provides unified interface for Neon PostgreSQL connections using psycopg2.
"""

import os
import logging
import psycopg2
import psycopg2.extras
from typing import Optional, Any, Dict, List
from contextlib import contextmanager
import threading
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SyncConnectionManager:
    """Manages Neon PostgreSQL database connections synchronously"""
    
    def __init__(self):
        self._connection_params = self._get_connection_params()
        self._local = threading.local()
        logger.info("Initialized SyncConnectionManager for Neon PostgreSQL")
    
    def _get_connection_params(self) -> Dict[str, Any]:
        """Get Neon PostgreSQL connection parameters from environment variables"""
        database_url = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DATABASE_URL')
        if not database_url:
            raise ValueError(
                "Neon PostgreSQL connection string not found. "
                "Please set DATABASE_URL or SUPABASE_DATABASE_URL environment variable."
            )
        
        # Парсим URL
        parsed = urlparse(database_url)
        
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:],  # убираем ведущий слэш
            'user': parsed.username,
            'password': parsed.password,
            'sslmode': 'require',  # Neon требует SSL
            'connect_timeout': 10,  # Уменьшено с 30 до 10 секунд
            'application_name': 'go2study_bot_sync',
            # Оптимизация производительности
            'keepalives_idle': 600,
            'keepalives_interval': 30,
            'keepalives_count': 3,
            'tcp_user_timeout': 1000,
        }
    
    def _get_connection(self):
        """Get connection for current thread"""
        if not hasattr(self._local, 'connection') or self._local.connection is None or self._local.connection.closed:
            try:
                self._local.connection = psycopg2.connect(**self._connection_params)
                self._local.connection.autocommit = True  # Включаем автокоммит
                logger.debug("Created new database connection for current thread")
            except Exception as e:
                logger.error(f"Failed to create database connection: {e}")
                raise
        
        return self._local.connection
    
    @contextmanager
    def get_connection(self):
        """Get database connection context manager"""
        conn = None
        try:
            conn = self._get_connection()
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            # Пытаемся переподключиться
            if hasattr(self._local, 'connection'):
                try:
                    self._local.connection.close()
                except:
                    pass
                self._local.connection = None
            raise
        finally:
            # Не закрываем соединение - оставляем его для повторного использования
            pass
    
    def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute query and return result"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.statusmessage
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch one row"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                row = cursor.fetchone()
                return dict(row) if row else None
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
    
    def fetch_val(self, query: str, params: tuple = None) -> Any:
        """Fetch single value"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                row = cursor.fetchone()
                return row[0] if row else None
    
    def close_all_connections(self):
        """Close all thread-local connections"""
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.close()
                logger.info("Closed database connection")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self._local.connection = None

# Global connection manager instance
_sync_connection_manager = None

def get_sync_connection_manager() -> SyncConnectionManager:
    """Get global synchronous connection manager instance"""
    global _sync_connection_manager
    if _sync_connection_manager is None:
        _sync_connection_manager = SyncConnectionManager()
    return _sync_connection_manager 