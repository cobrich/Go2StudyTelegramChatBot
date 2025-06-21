"""
Connection Manager for Supabase Database Operations

Provides unified interface for Supabase PostgreSQL connections with connection pooling.
"""

import os
import asyncio
import asyncpg
import logging
from typing import Optional, Any, AsyncContextManager
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages Supabase database connections with pooling support"""
    
    def __init__(self):
        self._pool = None
        self.connection_string = self._get_connection_string()
        logger.info("Initialized ConnectionManager for Supabase")
    
    def _get_connection_string(self) -> str:
        """Get Supabase connection string from environment variables"""
        conn_str = os.getenv('SUPABASE_DATABASE_URL') or os.getenv('DATABASE_URL')
        if not conn_str:
            raise ValueError(
                "Supabase connection string not found. "
                "Please set SUPABASE_DATABASE_URL or DATABASE_URL environment variable."
            )
        return conn_str
    
    async def initialize_pool(self, min_size: int = 1, max_size: int = 10):
        """Initialize connection pool for Supabase"""
        if not self._pool:
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
                logger.info(f"Supabase connection pool initialized (min={min_size}, max={max_size})")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase pool: {e}")
                raise
    
    async def close_pool(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Supabase connection pool closed")
    
    @asynccontextmanager
    async def get_async_connection(self) -> AsyncContextManager[Any]:
        """Get async Supabase database connection"""
        if not self._pool:
            await self.initialize_pool()
        
        async with self._pool.acquire() as conn:
            yield conn

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