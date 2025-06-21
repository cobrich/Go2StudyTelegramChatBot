"""
Database Package - Supabase Architecture

Provides modular database architecture with Supabase PostgreSQL support.

⚠️ ВАЖНО: Эта версия поддерживает ТОЛЬКО Supabase PostgreSQL.
SQLite больше не поддерживается.

Для миграции с SQLite:
1. Запустите: python init_supabase.py
2. Запустите: python migrate_to_supabase.py
3. Установите DATABASE_TYPE=supabase в .env

Архитектура:
- ConnectionManager: Управление подключениями к Supabase
- BaseRepository: Базовый класс для всех репозиториев
- DatabaseModels: Схемы таблиц PostgreSQL
- DatabaseFacade: Единый интерфейс для всех операций с БД
- Repositories: Модульные репозитории по доменам

Использование:
```python
from src.db import get_database

db = get_database()
user_info = db.get_user_info(user_id)
```
"""

from .database_facade import get_database, DatabaseFacade
from .connection_manager import get_connection_manager
from .models import DatabaseModels

__all__ = [
    'get_database',
    'DatabaseFacade', 
    'get_connection_manager',
    'DatabaseModels'
] 