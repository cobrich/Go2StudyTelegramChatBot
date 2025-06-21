"""
Connection Manager for Database Operations

Provides unified interface for SQLite and PostgreSQL connections with connection pooling.
"""

import os
import sqlite3
import asyncio
import asyncpg
import logging
from enum import Enum
from typing import Optional, Union, Any, AsyncContextManager
from contextlib import asynccontextmanager, contextmanager

logger = logging.getLogger(__name__)

class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"

class ConnectionManager:
    """Manages database connections with pooling support"""
    
    def __init__(self):
        self.db_type = self._determine_db_type()
        self._pool = None
        self._sqlite_path = None
        self.connection_string = self._get_connection_string()
        
        logger.info(f"Initialized ConnectionManager with {self.db_type.value}")
    
    def _determine_db_type(self) -> DatabaseType:
        """Determine database type from environment variables"""
        db_type = os.getenv('DATABASE_TYPE', 'sqlite').lower()
        
        if db_type == 'postgresql' or db_type == 'supabase':
            return DatabaseType.POSTGRESQL
        elif db_type == 'sqlite':
            return DatabaseType.SQLITE
        else:
            logger.warning(f"Unknown database type: {db_type}, defaulting to SQLite")
            return DatabaseType.SQLITE
    
    def _get_connection_string(self) -> str:
        """Get connection string based on database type"""
        if self.db_type == DatabaseType.POSTGRESQL:
            conn_str = os.getenv('SUPABASE_DATABASE_URL') or os.getenv('DATABASE_URL')
            if not conn_str:
                raise ValueError("PostgreSQL connection string not found in environment variables")
            return conn_str
        else:
            # SQLite
            db_path = os.getenv('SQLITE_PATH')
            if not db_path:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                db_path = os.path.join(project_root, "math_bot.db")
            self._sqlite_path = db_path
            return db_path
    
    async def initialize_pool(self, min_size: int = 1, max_size: int = 10):
        """Initialize connection pool for PostgreSQL"""
        if self.db_type == DatabaseType.POSTGRESQL and not self._pool:
            try:
                # Check if we're in the main thread and have an active event loop
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_closed():
                        raise RuntimeError("Event loop is closed")
                except RuntimeError:
                    # No event loop running, create a new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                self._pool = await asyncpg.create_pool(
                    self.connection_string,
                    min_size=min_size,
                    max_size=max_size,
                    command_timeout=60,
                    server_settings={
                        'application_name': 'go2study_bot',
                    }
                )
                logger.info(f"PostgreSQL connection pool initialized (min={min_size}, max={max_size})")
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL pool: {e}")
                raise
    
    async def close_pool(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")
    
    @asynccontextmanager
    async def get_async_connection(self) -> AsyncContextManager[Any]:
        """Get async database connection (PostgreSQL only)"""
        if self.db_type == DatabaseType.POSTGRESQL:
            if not self._pool:
                await self.initialize_pool()
            
            async with self._pool.acquire() as conn:
                yield conn
        else:
            raise NotImplementedError("Async connections not supported for SQLite")
    
    @contextmanager
    def get_sync_connection(self):
        """Get sync database connection (SQLite only)"""
        if self.db_type == DatabaseType.SQLITE:
            conn = sqlite3.connect(self._sqlite_path)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
        else:
            raise NotImplementedError("Sync connections not supported for PostgreSQL")
    
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL"""
        return self.db_type == DatabaseType.POSTGRESQL
    
    def is_sqlite(self) -> bool:
        """Check if using SQLite"""
        return self.db_type == DatabaseType.SQLITE

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

def get_sync_db_connection():
    """Get sync database connection"""
    manager = get_connection_manager()
    return manager.get_sync_connection()

def is_using_postgresql() -> bool:
    """Check if using PostgreSQL"""
    return get_connection_manager().is_postgresql()

def is_using_sqlite() -> bool:
    """Check if using SQLite"""
    return get_connection_manager().is_sqlite() 