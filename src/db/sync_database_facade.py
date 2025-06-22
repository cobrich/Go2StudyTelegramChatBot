"""
Synchronous Database Facade for Neon PostgreSQL

Provides unified interface for all database operations using synchronous repositories.
"""

import logging
from typing import Optional, List, Dict, Any
from .repositories.sync_admin_repository import SyncAdminRepository
from .repositories.sync_user_repository import SyncUserRepository

logger = logging.getLogger(__name__)

class SyncDatabaseFacade:
    """Synchronous facade for database operations"""
    
    def __init__(self):
        self.admins = SyncAdminRepository()
        self.users = SyncUserRepository()
        logger.info("SyncDatabaseFacade initialized for Neon PostgreSQL")
    
    def check_user_access(self, user_id: int, username: str = None) -> bool:
        """Check if user has access to the bot (sync)"""
        logger.info(f"🔍 Проверка доступа для пользователя: user_id={user_id}, username={username}")
        
        try:
            # First check if user is admin
            logger.info(f"📋 Проверяем является ли пользователь {user_id} админом...")
            is_admin = self.admins.is_admin(user_id)
            logger.info(f"🔧 Результат проверки админа для {user_id}: {is_admin}")
            
            if is_admin:
                logger.info(f"✅ Пользователь {user_id} является админом - доступ разрешен")
                return True
            
            # If not admin, check whitelist of regular users
            logger.info(f"👤 Пользователь {user_id} не админ, проверяем в whitelist обычных пользователей...")
            has_access = self.users.has_user_access(user_id)
            logger.info(f"📝 Результат проверки whitelist для {user_id}: {has_access}")
            
            if has_access:
                logger.info(f"✅ Пользователь {user_id} найден в whitelist - доступ разрешен")
                return True
            else:
                logger.warning(f"❌ Пользователь {user_id} НЕ найден ни в админах, ни в whitelist - доступ запрещен")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке доступа для пользователя {user_id}: {e}")
            return False
    
    def auto_update_username_from_telegram(self, user_id: int, telegram_data: Dict[str, Any]) -> bool:
        """Auto-update username from Telegram data (sync)"""
        logger.info(f"🔄 Auto-updating username for user {user_id} from Telegram data")
        
        try:
            username = telegram_data.get('username')
            first_name = telegram_data.get('first_name', '')
            last_name = telegram_data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip()
            
            # Check if user is admin and update admin info
            if self.admins.is_admin(user_id):
                return self.admins.update_admin_info(user_id, username, full_name)
            
            # Check if user exists in allowed_users and update
            user = self.users.get_user_by_id(user_id)
            if user:
                # Update existing user (this would need a new method in UserRepository)
                logger.info(f"User {user_id} exists in allowed_users, would update info")
                return True
            
            logger.info(f"User {user_id} not found in any table for auto-update")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error auto-updating username for {user_id}: {e}")
            return False
    
    def auto_setup_user_from_whitelist(self, user_id: int, telegram_data: Dict[str, Any]) -> bool:
        """Auto-setup user from whitelist (sync) - stub implementation"""
        logger.info(f"🔧 Auto-setup user {user_id} from whitelist - stub implementation")
        # This would be implemented based on specific business logic
        return False
    
    # Admin operations
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin (sync)"""
        return self.admins.is_admin(user_id)
    
    def is_super_admin(self, user_id: int) -> bool:
        """Check if user is super admin (sync)"""
        return self.admins.is_super_admin(user_id)
    
    def get_admin_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get admin by ID (sync)"""
        return self.admins.get_admin_by_id(user_id)
    
    def add_admin(self, user_id: int, username: str = None, full_name: str = None,
                  is_super_admin: bool = False, created_by: int = None) -> bool:
        """Add new admin (sync)"""
        return self.admins.add_admin(user_id, username, full_name, is_super_admin, created_by)
    
    def remove_admin(self, user_id: int) -> bool:
        """Remove admin (sync)"""
        return self.admins.remove_admin(user_id)
    
    def get_all_admins(self) -> List[Dict[str, Any]]:
        """Get all admins (sync)"""
        return self.admins.get_all_admins()
    
    # User operations
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID (sync)"""
        return self.users.get_user_by_id(user_id)
    
    def add_user(self, user_id: int, username: str = None, full_name: str = None,
                 grade: int = None, language: str = 'ru', added_by: int = None) -> bool:
        """Add new user (sync)"""
        return self.users.add_user(user_id, username, full_name, grade, language, added_by)
    
    def remove_user_access(self, user_id: int) -> bool:
        """Remove user access (sync)"""
        return self.users.remove_user_access(user_id)
    
    def restore_user_access(self, user_id: int) -> bool:
        """Restore user access (sync)"""
        return self.users.restore_user_access(user_id)
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (sync)"""
        return self.users.get_all_users()
    
    def update_user_activity(self, user_id: int, current_topic: str = None) -> bool:
        """Update user activity (sync)"""
        return self.users.update_user_activity(user_id, current_topic)
    
    def close_connections(self):
        """Close all database connections"""
        try:
            self.admins.connection_manager.close_all_connections()
            logger.info("🔒 All database connections closed")
        except Exception as e:
            logger.error(f"❌ Error closing connections: {e}")

# Global facade instance
_sync_database_facade = None

def get_sync_database_facade() -> SyncDatabaseFacade:
    """Get global synchronous database facade instance"""
    global _sync_database_facade
    if _sync_database_facade is None:
        _sync_database_facade = SyncDatabaseFacade()
    return _sync_database_facade 