"""
Base Repository for Supabase Database Operations

Provides unified interface for Supabase PostgreSQL operations.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from abc import ABC
from .connection_manager import get_connection_manager

logger = logging.getLogger(__name__)

class BaseRepository(ABC):
    """Base repository for Supabase database operations"""
    
    def __init__(self):
        self.connection_manager = get_connection_manager()
    
    def _sync_call(self, coro):
        """Execute async function synchronously"""
        try:
            # Проверяем, есть ли активный event loop
            try:
                loop = asyncio.get_running_loop()
                # Если есть активный loop, создаем задачу и ждем ее выполнения
                import concurrent.futures
                import threading
                
                # Создаем новый event loop в отдельном потоке
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(coro)
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result()
                    
            except RuntimeError:
                # Нет активного loop, можем создать новый
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()
        except OSError as e:
            if "Network is unreachable" in str(e):
                logger.warning(f"Database unreachable (IPv6 issue): {e}. Returning fallback value.")
                # Возвращаем безопасные fallback значения
                return self._get_fallback_value()
            else:
                logger.error(f"Database connection error: {e}")
                raise
        except Exception as e:
            logger.error(f"Error in _sync_call: {e}")
            raise
    
    async def _execute_query_async(self, query: str, params: tuple = None) -> Any:
        """Execute query asynchronously"""
        async with self.connection_manager.get_async_connection() as conn:
            if params:
                return await conn.execute(query, *params)
            else:
                return await conn.execute(query)
    
    async def _fetch_one_async(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch one row asynchronously"""
        async with self.connection_manager.get_async_connection() as conn:
            if params:
                row = await conn.fetchrow(query, *params)
            else:
                row = await conn.fetchrow(query)
            return dict(row) if row else None
    
    async def _fetch_all_async(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows asynchronously"""
        async with self.connection_manager.get_async_connection() as conn:
            if params:
                rows = await conn.fetch(query, *params)
            else:
                rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
    async def _fetch_val_async(self, query: str, params: tuple = None) -> Any:
        """Fetch single value asynchronously"""
        async with self.connection_manager.get_async_connection() as conn:
            if params:
                return await conn.fetchval(query, *params)
            else:
                return await conn.fetchval(query)
    
    # Unified interface methods (sync wrappers for async operations)
    
    def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute query (sync wrapper)"""
        return self._sync_call(self._execute_query_async(query, params))
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch one row (sync wrapper)"""
        return self._sync_call(self._fetch_one_async(query, params))
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows (sync wrapper)"""
        return self._sync_call(self._fetch_all_async(query, params))
    
    def fetch_val(self, query: str, params: tuple = None) -> Any:
        """Fetch single value (sync wrapper)"""
        return self._sync_call(self._fetch_val_async(query, params))
    
    def _get_placeholder(self, index: int = 1) -> str:
        """Get parameter placeholder for PostgreSQL ($1, $2, etc.)"""
        return f'${index}'
    
    def _get_boolean_value(self, value: bool) -> bool:
        """Get boolean value for PostgreSQL"""
        return value
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp expression for PostgreSQL"""
        return 'CURRENT_TIMESTAMP'
    
    def _get_fallback_value(self):
        """Get fallback value when database is unreachable"""
        # Возвращаем None для большинства случаев
        # Конкретные repositories могут переопределить этот метод
        return None 