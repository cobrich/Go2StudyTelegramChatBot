"""
Database Module

Provides database connectivity and operations for the educational bot.

Features:
- Connection management with automatic retry and pooling
- Repository pattern for data access
- Models for database schema
- Migrations and table initialization
- Support for both SQLite (development) and PostgreSQL (production)

Main Components:
- SyncConnectionManager: Handles database connections synchronously
- SyncBaseRepository: Base class for all repository operations
- SyncDatabaseFacade: Unified interface for all database operations
- DatabaseModels: Schema definitions and table creation

Usage:
    from src.db import get_sync_database_facade
    
    db = get_sync_database_facade()
    user = db.get_user_by_id(123)
"""

from .sync_database_facade import get_sync_database_facade, SyncDatabaseFacade
from .sync_connection_manager import get_sync_connection_manager

from .models import DatabaseModels

__all__ = [
    'get_sync_database_facade',
    'SyncDatabaseFacade',
    'get_sync_connection_manager',
    'DatabaseModels',
] 