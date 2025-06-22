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
    
    # User profile and language methods
    def get_user_language(self, user_id: int) -> str:
        """Get user language (sync)"""
        user = self.users.get_user_by_id(user_id)
        return user.get('language', 'ru') if user else 'ru'
    
    def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user info (sync)"""
        return self.users.get_user_by_id(user_id)
    
    def set_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        """Set user info (sync)"""
        self.users.add_user(user_id, full_name=full_name, grade=grade)
    
    def set_user_info_with_language(self, user_id: int, full_name: str, grade: int, language: str) -> None:
        """Set user info with language (sync)"""
        self.users.add_user(user_id, full_name=full_name, grade=grade, language=language)
    
    def update_user_language(self, user_id: int, language: str) -> None:
        """Update user language (sync)"""
        # This would need to be implemented in SyncUserRepository
        logger.info(f"🔄 Updating language for user {user_id} to {language}")
        # For now, we'll use add_user which handles updates via ON CONFLICT
        user = self.users.get_user_by_id(user_id)
        if user:
            self.users.add_user(
                user_id=user_id,
                username=user.get('username'),
                full_name=user.get('full_name'),
                grade=user.get('grade'),
                language=language,
                added_by=user.get('added_by')
            )
    
    def is_user_active(self, user_id: int) -> bool:
        """Check if user is active in a test (sync)"""
        user = self.users.get_user_by_id(user_id)
        return user.get('is_active', False) if user else False
    
    def set_user_active(self, user_id: int, topic: str) -> None:
        """Set user as active in a test (sync)"""
        self.users.update_user_activity(user_id, topic)
    
    def set_user_inactive(self, user_id: int) -> None:
        """Set user as inactive (sync)"""
        self.users.update_user_activity(user_id, None)
    
    # Additional methods needed by the bot
    def get_topic_names(self, active_only: bool = True) -> List[str]:
        """Get topic names (sync) - stub implementation"""
        # This would need to be implemented in sync repositories
        logger.warning("get_topic_names called but not fully implemented in sync facade")
        return []
    
    def get_tasks_for_topic(self, topic: str, limit: int = 20) -> List[Dict]:
        """Get tasks for topic (sync) - stub implementation"""
        logger.warning("get_tasks_for_topic called but not fully implemented in sync facade")
        return []
    
    def get_explanation_by_question_text(self, question_text: str) -> Optional[str]:
        """Get explanation by question text (sync) - stub implementation"""
        logger.warning("get_explanation_by_question_text called but not fully implemented in sync facade")
        return None
    
    def add_question(self, question: dict) -> bool:
        """Add question (sync) - stub implementation"""
        logger.warning("add_question called but not fully implemented in sync facade")
        return False
    
    def add_test_result(self, user_id: int, topic: str, percentage: float) -> None:
        """Add test result (sync) - stub implementation"""
        logger.warning("add_test_result called but not fully implemented in sync facade")
    
    def get_error_tasks_for_user(self, user_id: int, topic: str, limit: int = 10) -> List[Dict]:
        """Get error tasks for user (sync) - stub implementation"""
        logger.warning("get_error_tasks_for_user called but not fully implemented in sync facade")
        return []
    
    def add_user_error(self, user_id: int, topic: str, question_text: str,
                      user_answer_text: str, correct_answer_text: str,
                      explanation_text: str) -> None:
        """Add user error (sync) - stub implementation"""
        logger.warning("add_user_error called but not fully implemented in sync facade")
    
    def add_user_error_by_question_id(self, user_id: int, question_id: int, topic: str,
                                     user_answer_text: str, correct_answer_text: str) -> None:
        """Add user error by question ID (sync) - stub implementation"""
        logger.warning("add_user_error_by_question_id called but not fully implemented in sync facade")

# Global facade instance
_sync_database_facade = None

def get_sync_database_facade() -> SyncDatabaseFacade:
    """Get global synchronous database facade instance"""
    global _sync_database_facade
    if _sync_database_facade is None:
        _sync_database_facade = SyncDatabaseFacade()
    return _sync_database_facade 