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
    
    @property
    def is_postgresql(self) -> bool:
        """Check if database is PostgreSQL (always True for Supabase)"""
        return True
    
    def _sync_call(self, coro):
        """Execute async function synchronously"""
        try:
            # Проверяем, есть ли активный event loop
            try:
                loop = asyncio.get_running_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
                
                # Если есть активный loop, создаем новый в отдельном потоке
                import concurrent.futures
                import threading
                
                def run_in_new_thread():
                    """Запускаем корутину в новом потоке с новым event loop"""
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(coro)
                    finally:
                        new_loop.close()
                
                # Запускаем в отдельном потоке
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_new_thread)
                    return future.result(timeout=30)  # 30 секунд таймаут
                    
            except RuntimeError:
                # Нет активного event loop, можем использовать asyncio.run
                try:
                    return asyncio.run(coro)
                except RuntimeError as e:
                    if "cannot be called from a running event loop" in str(e):
                        # Если все же есть loop, но asyncio.run не работает
                        # Создаем новый loop в отдельном потоке
                        import concurrent.futures
                        
                        def run_in_thread():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                return new_loop.run_until_complete(coro)
                            finally:
                                new_loop.close()
                                asyncio.set_event_loop(None)
                        
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(run_in_thread)
                            return future.result(timeout=30)
                    else:
                        raise
                        
        except Exception as e:
            logger.error(f"Error in _sync_call: {e}")
            # Возвращаем fallback значение вместо падения
            return self._get_fallback_value()
    
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