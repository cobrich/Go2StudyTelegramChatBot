"""
Base Repository for Neon PostgreSQL Database Operations

Provides unified interface for Neon PostgreSQL operations.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from abc import ABC
from .connection_manager import get_connection_manager

logger = logging.getLogger(__name__)

class BaseRepository(ABC):
    """Base repository for Neon PostgreSQL database operations"""
    
    def __init__(self):
        self.connection_manager = get_connection_manager()
    
    @property
    def is_postgresql(self) -> bool:
        """Check if database is PostgreSQL (always True for Neon PostgreSQL)"""
        return True
    
    def _sync_call(self, coro):
        """Execute async function synchronously"""
        try:
            # Проверяем, есть ли активный event loop
            try:
                loop = asyncio.get_running_loop()
                # Если есть активный loop, используем прямое подключение
                logger.info("🔄 Active event loop detected, using direct connection")
                
                # Извлекаем информацию из контекста вызова
                import inspect
                frame = inspect.currentframe().f_back.f_back  # Поднимаемся на 2 уровня выше
                
                query = None
                params = None
                method_name = None
                
                # Ищем параметры в локальных переменных вызывающего метода
                if frame and frame.f_locals:
                    query = frame.f_locals.get('query')
                    params = frame.f_locals.get('params')
                    method_name = frame.f_code.co_name
                
                if query:
                    logger.info(f"🔍 Выполняем прямой запрос: {query} с параметрами: {params}")
                    return self._execute_direct_query(query, params, method_name)
                else:
                    logger.warning("⚠️ Не удалось извлечь параметры запроса, используем fallback")
                    fallback_value = self._get_fallback_value()
                    return fallback_value
                        
            except RuntimeError:
                # Нет активного event loop, можем использовать asyncio.run
                try:
                    logger.info("✅ No active event loop, using asyncio.run")
                    result = asyncio.run(coro)
                    logger.info(f"✅ Результат asyncio.run: {result}")
                    return result
                except Exception as e:
                    logger.error(f"Error in asyncio.run: {e}")
                    fallback_value = self._get_fallback_value()
                    logger.info(f"🔄 Возвращаем fallback значение после ошибки: {fallback_value}")
                    return fallback_value
                        
        except Exception as e:
            logger.error(f"Error in _sync_call: {e}")
            fallback_value = self._get_fallback_value()
            logger.info(f"🔄 Возвращаем fallback значение после исключения: {fallback_value}")
            return fallback_value
        finally:
            # Закрываем корутину, чтобы избежать warnings
            if hasattr(coro, 'close'):
                try:
                    coro.close()
                except Exception:
                    pass
    
    def _execute_direct_query(self, query: str, params: tuple, method_name: str):
        """Выполняет запрос напрямую в отдельном потоке"""
        import concurrent.futures
        import threading
        import os
        import asyncpg
        
        def run_query_in_thread():
            """Выполняем запрос в новом event loop в отдельном потоке"""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                async def execute():
                    # Получаем строку подключения
                    database_url = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DATABASE_URL')
                    if not database_url:
                        raise ValueError("Database URL not found")
                    
                    # Создаем прямое подключение
                    conn = await asyncpg.connect(database_url, command_timeout=30)
                    try:
                        if method_name == 'fetch_val':
                            if params:
                                return await conn.fetchval(query, *params)
                            else:
                                return await conn.fetchval(query)
                        elif method_name == 'fetch_one':
                            if params:
                                row = await conn.fetchrow(query, *params)
                            else:
                                row = await conn.fetchrow(query)
                            return dict(row) if row else None
                        elif method_name == 'fetch_all':
                            if params:
                                rows = await conn.fetch(query, *params)
                            else:
                                rows = await conn.fetch(query)
                            return [dict(row) for row in rows]
                        elif method_name == 'execute_query':
                            if params:
                                return await conn.execute(query, *params)
                            else:
                                return await conn.execute(query)
                        else:
                            # Fallback - пробуем fetchval
                            if params:
                                return await conn.fetchval(query, *params)
                            else:
                                return await conn.fetchval(query)
                    finally:
                        await conn.close()
                
                return new_loop.run_until_complete(execute())
            finally:
                new_loop.close()
        
        # Выполняем в thread pool
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_query_in_thread)
            try:
                result = future.result(timeout=10)
                logger.info(f"✅ Direct query executed successfully: {result}")
                return result
            except concurrent.futures.TimeoutError:
                logger.error("⏰ Direct query timeout")
                future.cancel()
                return self._get_fallback_value()
            except Exception as e:
                logger.error(f"❌ Direct query failed: {e}")
                return self._get_fallback_value()
    
    def _create_fresh_coroutine(self, method_name, *args, **kwargs):
        """Create a fresh coroutine for the given method"""
        method_map = {
            '_execute_query_async': self._execute_query_async,
            '_fetch_one_async': self._fetch_one_async,
            '_fetch_all_async': self._fetch_all_async,
            '_fetch_val_async': self._fetch_val_async,
        }
        
        if method_name in method_map:
            return method_map[method_name](*args, **kwargs)
        else:
            logger.error(f"Unknown async method: {method_name}")
            return None
    
    async def _execute_query_async(self, query: str, params: tuple = None) -> Any:
        """Execute query asynchronously"""
        try:
            async with self.connection_manager.get_async_connection() as conn:
                if params:
                    return await conn.execute(query, *params)
                else:
                    return await conn.execute(query)
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    async def _fetch_one_async(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch one row asynchronously"""
        try:
            async with self.connection_manager.get_async_connection() as conn:
                if params:
                    row = await conn.fetchrow(query, *params)
                else:
                    row = await conn.fetchrow(query)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching one row: {e}")
            raise
    
    async def _fetch_all_async(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows asynchronously"""
        try:
            async with self.connection_manager.get_async_connection() as conn:
                if params:
                    rows = await conn.fetch(query, *params)
                else:
                    rows = await conn.fetch(query)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching all rows: {e}")
            raise
    
    async def _fetch_val_async(self, query: str, params: tuple = None) -> Any:
        """Fetch single value asynchronously"""
        try:
            async with self.connection_manager.get_async_connection() as conn:
                if params:
                    return await conn.fetchval(query, *params)
                else:
                    return await conn.fetchval(query)
        except Exception as e:
            logger.error(f"Error fetching value: {e}")
            raise
    
    # Unified interface methods (sync wrappers for async operations)
    
    def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute query (sync wrapper)"""
        # Создаем свежую корутину каждый раз
        coro = self._execute_query_async(query, params)
        return self._sync_call(coro)
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch one row (sync wrapper)"""
        # Создаем свежую корутину каждый раз
        coro = self._fetch_one_async(query, params)
        return self._sync_call(coro)
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows (sync wrapper)"""
        # Создаем свежую корутину каждый раз
        coro = self._fetch_all_async(query, params)
        return self._sync_call(coro)
    
    def fetch_val(self, query: str, params: tuple = None) -> Any:
        """Fetch single value (sync wrapper)"""
        logger.debug(f"🔍 BaseRepository.fetch_val: query={query}, params={params}")
        # Создаем свежую корутину каждый раз
        coro = self._fetch_val_async(query, params)
        result = self._sync_call(coro)
        logger.debug(f"📊 BaseRepository.fetch_val: результат={result}")
        return result
    
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