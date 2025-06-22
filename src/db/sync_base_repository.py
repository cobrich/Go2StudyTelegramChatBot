"""
Synchronous Base Repository for Neon PostgreSQL Database Operations

Provides unified interface for Neon PostgreSQL operations using psycopg2.
"""

import logging
from typing import Any, Dict, List, Optional
from abc import ABC
from .sync_connection_manager import get_sync_connection_manager

logger = logging.getLogger(__name__)

class SyncBaseRepository(ABC):
    """Base repository for synchronous Neon PostgreSQL database operations"""
    
    def __init__(self):
        self.connection_manager = get_sync_connection_manager()
    
    @property
    def is_postgresql(self) -> bool:
        """Check if database is PostgreSQL (always True for Neon PostgreSQL)"""
        return True
    
    def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute query (sync)"""
        try:
            result = self.connection_manager.execute_query(query, params)
            return result
        except Exception as e:
            logger.error(f"❌ Error executing query: {e}")
            raise
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch one row (sync)"""
        try:
            result = self.connection_manager.fetch_one(query, params)
            return result
        except Exception as e:
            logger.error(f"❌ Error fetching one row: {e}")
            raise
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows (sync)"""
        try:
            result = self.connection_manager.fetch_all(query, params)
            return result
        except Exception as e:
            logger.error(f"❌ Error fetching all rows: {e}")
            raise
    
    def fetch_val(self, query: str, params: tuple = None) -> Any:
        """Fetch single value (sync)"""
        try:
            result = self.connection_manager.fetch_val(query, params)
            return result
        except Exception as e:
            logger.error(f"❌ Error fetching value: {e}")
            raise
    
    def _get_placeholder(self, index: int = 1) -> str:
        """Get parameter placeholder for PostgreSQL (%s for psycopg2)"""
        return '%s'
    
    def _get_boolean_value(self, value: bool) -> bool:
        """Get boolean value for PostgreSQL"""
        return value
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp expression for PostgreSQL"""
        return 'CURRENT_TIMESTAMP' 