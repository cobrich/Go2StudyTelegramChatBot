"""
Database service module.
Provides database instance for the application.
"""

from src.db.sync_database_facade import get_sync_database_facade

def get_database_instance():
    """
    Get database instance.
    This is an alias for get_sync_database_facade() to maintain compatibility.
    """
    return get_sync_database_facade()

__all__ = ['get_database_instance'] 