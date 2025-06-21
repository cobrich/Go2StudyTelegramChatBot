"""
Database module for Go2Study Bot

Provides modular database architecture with support for both SQLite and PostgreSQL.
"""

from .database_facade import DatabaseFacade, get_database
from .connection_manager import ConnectionManager, DatabaseType
from .models import DatabaseModels
from .repositories import UserRepository, AdminRepository, QuestionRepository, StatisticsRepository

# For backward compatibility - expose the facade as Database
Database = DatabaseFacade

__all__ = [
    'Database',
    'DatabaseFacade',
    'get_database',
    'ConnectionManager',
    'DatabaseType',
    'DatabaseModels',
    'UserRepository',
    'AdminRepository',
    'QuestionRepository',
    'StatisticsRepository'
] 