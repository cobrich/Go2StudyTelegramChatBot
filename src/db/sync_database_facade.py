"""
Synchronous Database Facade for Neon PostgreSQL

Provides unified interface for all database operations using synchronous repositories.
"""

import logging
import time
from typing import Optional, List, Dict, Any
from .repositories.sync_admin_repository import SyncAdminRepository
from .repositories.sync_user_repository import SyncUserRepository
from .repositories.sync_question_repository import SyncQuestionRepository
from .repositories.sync_statistics_repository import SyncStatisticsRepository

logger = logging.getLogger(__name__)

class SyncDatabaseFacade:
    """Synchronous facade for database operations"""
    
    def __init__(self):
        self.admins = SyncAdminRepository()
        self.users = SyncUserRepository()
        self.questions = SyncQuestionRepository()
        self.statistics = SyncStatisticsRepository()
        
        # Кеширование для улучшения производительности
        self._cache = {}
        self._cache_ttl = 300  # 5 минут
        
        logger.info("SyncDatabaseFacade initialized for Neon PostgreSQL")
    
    def _get_cache_key(self, operation: str, *args) -> str:
        """Генерирует ключ кеша"""
        return f"{operation}:{':'.join(map(str, args))}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Получает результат из кеша если он не устарел"""
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                # Удаляем устаревший результат
                del self._cache[cache_key]
        return None
    
    def _set_cache_result(self, cache_key: str, result: Any) -> None:
        """Сохраняет результат в кеш"""
        self._cache[cache_key] = (result, time.time())
    
    def _clear_cache_for_user(self, user_id: int) -> None:
        """Очищает кеш для конкретного пользователя"""
        keys_to_remove = []
        for key in self._cache.keys():
            if f":{user_id}" in key or key.endswith(f":{user_id}"):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._cache[key]
    
    def _clear_all_cache(self) -> None:
        """Очищает весь кеш"""
        self._cache.clear()
    
    def check_user_access(self, user_id: int, username: str = None) -> bool:
        """Check if user has access to the bot (sync) - с кешированием"""
        cache_key = self._get_cache_key("user_access", user_id)
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
        
        logger.info(f"🔍 Проверка доступа для пользователя: user_id={user_id}, username={username}")
        
        try:
            # First check if user is admin
            is_admin = self.is_admin(user_id)
            
            if is_admin:
                logger.info(f"✅ Пользователь {user_id} является админом - доступ разрешен")
                self._set_cache_result(cache_key, True)
                return True
            
            # If not admin, check whitelist of regular users
            has_access = self.users.has_user_access(user_id)
            
            if has_access:
                logger.info(f"✅ Пользователь {user_id} найден в whitelist - доступ разрешен")
                self._set_cache_result(cache_key, True)
                return True
            else:
                logger.warning(f"❌ Пользователь {user_id} НЕ найден ни в админах, ни в whitelist - доступ запрещен")
                self._set_cache_result(cache_key, False)
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
        """Check if user is admin (sync) - с кешированием"""
        cache_key = self._get_cache_key("is_admin", user_id)
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
        
        result = self.admins.is_admin(user_id)
        self._set_cache_result(cache_key, result)
        return result
    
    def is_super_admin(self, user_id: int) -> bool:
        """Check if user is super admin (sync) - с кешированием"""
        cache_key = self._get_cache_key("is_super_admin", user_id)
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
        
        result = self.admins.is_super_admin(user_id)
        self._set_cache_result(cache_key, result)
        return result
    
    def get_admin_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get admin by ID (sync) - с кешированием"""
        cache_key = self._get_cache_key("admin_by_id", user_id)
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
        
        result = self.admins.get_admin_by_id(user_id)
        self._set_cache_result(cache_key, result)
        return result
    
    def add_admin(self, user_id: int, username: str = None, full_name: str = None,
                  is_super_admin: bool = False, created_by: int = None) -> bool:
        """Add new admin (sync)"""
        result = self.admins.add_admin(user_id, username, full_name, is_super_admin, created_by)
        if result:
            self._clear_cache_for_user(user_id)
        return result
    
    def remove_admin(self, user_id: int) -> bool:
        """Remove admin (sync)"""
        result = self.admins.remove_admin(user_id)
        if result:
            self._clear_cache_for_user(user_id)
        return result
    
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
        logger.info(f"🔄 Updating language for user {user_id} to {language}")
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
    
    # Question operations
    def get_topic_names(self, active_only: bool = True) -> List[str]:
        """Get topic names (sync)"""
        return self.questions.get_topic_names(active_only)
    
    def get_tasks_for_topic(self, topic: str, limit: int = 20) -> List[Dict]:
        """Get tasks for topic (sync)"""
        return self.questions.get_tasks_for_topic(topic, limit)
    
    def get_explanation_by_question_text(self, question_text: str) -> Optional[str]:
        """Get explanation by question text (sync)"""
        return self.questions.get_explanation_by_question_text(question_text)
    
    def add_question(self, question: dict) -> bool:
        """Add question (sync)"""
        return self.questions.add_question(question)
    
    def get_all_questions(self) -> List[Dict]:
        """Get all questions (sync)"""
        return self.questions.get_all_questions()
    
    def get_questions_by_user_language(self, user_id: int) -> List[Dict]:
        """Get questions available for user based on their language (sync)"""
        user_language = self.get_user_language(user_id)
        return self.questions.get_questions_by_language(user_language)
    
    def delete_question_by_id(self, question_id: int) -> bool:
        """Delete question by ID (sync)"""
        return self.questions.delete_question_by_id(question_id)
    
    def get_all_ai_questions(self) -> List[Dict]:
        """Get all AI-generated questions (sync)"""
        return self.questions.get_all_ai_questions()
    
    # Statistics operations
    def add_test_result(self, user_id: int, topic: str, percentage: float) -> None:
        """Add test result (sync)"""
        self.statistics.add_test_result(user_id, topic, percentage)
    
    def get_user_test_results(self, user_id: int) -> List[Dict]:
        """Get user test results (sync)"""
        return self.statistics.get_user_test_results(user_id)
    
    def get_user_progress(self, user_id: int) -> tuple[int, float]:
        """Get user progress (sync)"""
        return self.statistics.get_user_progress(user_id)
    
    def get_error_tasks_for_user(self, user_id: int, topic: str, limit: int = 10) -> List[Dict]:
        """Get error tasks for user (sync)"""
        return self.statistics.get_error_tasks_for_user(user_id, topic, limit)
    
    def get_error_topics(self, user_id: int) -> List[tuple[str, int]]:
        """Get error topics for user (sync)"""
        return self.statistics.get_error_topics(user_id)
    
    def add_user_error(self, user_id: int, topic: str, question_text: str,
                      user_answer_text: str, correct_answer_text: str,
                      explanation_text: str) -> None:
        """Add user error (sync)"""
        self.statistics.add_user_error(
            user_id, topic, question_text, user_answer_text,
            correct_answer_text, explanation_text
        )
    
    def add_user_error_by_question_id(self, user_id: int, question_id: int, topic: str,
                                     user_answer_text: str, correct_answer_text: str) -> None:
        """Add user error by question ID (sync)"""
        self.statistics.add_user_error_by_question_id(
            user_id, question_id, topic, user_answer_text, correct_answer_text
        )
    
    def get_recent_topics(self, user_id: int, limit: int = 5) -> List[tuple[str, float, str]]:
        """Get recent topics (sync)"""
        return self.statistics.get_recent_topics(user_id, limit)
    
    def get_recent_unique_topics(self, user_id: int, unique_limit: int = 5, 
                                history_limit: int = 20) -> List[tuple[str, int]]:
        """Get recent unique topics (sync)"""
        return self.statistics.get_recent_unique_topics(user_id, unique_limit, history_limit)
    
    def decrement_error_count(self, user_id: int, question_text: str) -> None:
        """Decrement error count (sync)"""
        self.statistics.decrement_error_count(user_id, question_text)
    
    def decrement_error_count_by_question_id(self, user_id: int, question_id: int) -> None:
        """Decrement error count by question ID (sync)"""
        self.statistics.decrement_error_count_by_question_id(user_id, question_id)
    
    def get_student_detailed_statistics(self, user_id: int) -> Optional[Dict]:
        """Get detailed statistics for a student (sync)"""
        return self.statistics.get_student_detailed_statistics(user_id)
    
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