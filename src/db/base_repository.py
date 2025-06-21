"""
Base Repository with common database operations

Provides unified interface for both SQLite and PostgreSQL operations.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod
from .connection_manager import get_connection_manager

logger = logging.getLogger(__name__)

class BaseRepository(ABC):
    """Base repository with common database operations"""
    
    def __init__(self):
        self.connection_manager = get_connection_manager()
        self.is_postgresql = self.connection_manager.is_postgresql()
    
    def _sync_call(self, coro):
        """Execute async function synchronously (for PostgreSQL compatibility)"""
        if self.is_postgresql:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"Error in _sync_call: {e}")
                raise
        else:
            # For SQLite, we shouldn't reach here as we use sync methods directly
            raise NotImplementedError("_sync_call should not be used with SQLite")
    
    async def _execute_query_async(self, query: str, params: tuple = None) -> Any:
        """Execute query asynchronously (PostgreSQL)"""
        async with self.connection_manager.get_async_connection() as conn:
            if params:
                return await conn.execute(query, *params)
            else:
                return await conn.execute(query)
    
    async def _fetch_one_async(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch one row asynchronously (PostgreSQL)"""
        async with self.connection_manager.get_async_connection() as conn:
            if params:
                row = await conn.fetchrow(query, *params)
            else:
                row = await conn.fetchrow(query)
            return dict(row) if row else None
    
    async def _fetch_all_async(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows asynchronously (PostgreSQL)"""
        async with self.connection_manager.get_async_connection() as conn:
            if params:
                rows = await conn.fetch(query, *params)
            else:
                rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
    async def _fetch_val_async(self, query: str, params: tuple = None) -> Any:
        """Fetch single value asynchronously (PostgreSQL)"""
        async with self.connection_manager.get_async_connection() as conn:
            if params:
                return await conn.fetchval(query, *params)
            else:
                return await conn.fetchval(query)
    
    def _execute_query_sync(self, query: str, params: tuple = None) -> Any:
        """Execute query synchronously (SQLite)"""
        with self.connection_manager.get_sync_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor
    
    def _fetch_one_sync(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch one row synchronously (SQLite)"""
        with self.connection_manager.get_sync_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def _fetch_all_sync(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows synchronously (SQLite)"""
        with self.connection_manager.get_sync_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def _fetch_val_sync(self, query: str, params: tuple = None) -> Any:
        """Fetch single value synchronously (SQLite)"""
        with self.connection_manager.get_sync_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            return row[0] if row else None
    
    # Unified interface methods (these adapt to the database type)
    
    def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute query (unified interface)"""
        if self.is_postgresql:
            return self._sync_call(self._execute_query_async(query, params))
        else:
            return self._execute_query_sync(query, params)
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch one row (unified interface)"""
        if self.is_postgresql:
            return self._sync_call(self._fetch_one_async(query, params))
        else:
            return self._fetch_one_sync(query, params)
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows (unified interface)"""
        if self.is_postgresql:
            return self._sync_call(self._fetch_all_async(query, params))
        else:
            return self._fetch_all_sync(query, params)
    
    def fetch_val(self, query: str, params: tuple = None) -> Any:
        """Fetch single value (unified interface)"""
        if self.is_postgresql:
            return self._sync_call(self._fetch_val_async(query, params))
        else:
            return self._fetch_val_sync(query, params)
    
    def _adapt_query_params(self, query: str, params: tuple = None) -> tuple:
        """Adapt query parameters for different database types"""
        if self.is_postgresql:
            # PostgreSQL uses $1, $2, etc.
            if params:
                # Convert ? placeholders to $1, $2, etc.
                param_count = query.count('?')
                for i in range(param_count, 0, -1):
                    query = query.replace('?', f'${i}', 1)
                return query, params
            return query, params
        else:
            # SQLite uses ? placeholders (no change needed)
            return query, params
    
    def _get_placeholder(self, index: int = 1) -> str:
        """Get parameter placeholder for current database type"""
        if self.is_postgresql:
            return f'${index}'
        else:
            return '?'
    
    def _get_boolean_value(self, value: bool) -> Union[bool, int]:
        """Get boolean value for current database type"""
        if self.is_postgresql:
            return value
        else:
            return 1 if value else 0
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp expression for current database type"""
        if self.is_postgresql:
            return 'CURRENT_TIMESTAMP'
        else:
            return 'CURRENT_TIMESTAMP' 