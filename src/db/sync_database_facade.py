"""
Synchronous Database Facade for Neon PostgreSQL

Provides unified interface for all database operations using synchronous repositories.
"""

import logging
import time
from typing import Optional, List, Dict, Any, Tuple
from .repositories.sync_admin_repository import SyncAdminRepository
from .repositories.sync_user_repository import SyncUserRepository
from .repositories.sync_question_repository import SyncQuestionRepository
from .repositories.sync_statistics_repository import SyncStatisticsRepository
from .repositories.sync_topic_repository import SyncTopicRepository

logger = logging.getLogger(__name__)

class SyncDatabaseFacade:
    """Synchronous facade for database operations"""
    
    def __init__(self):
        self.admins = SyncAdminRepository()
        self.users = SyncUserRepository()
        self.questions = SyncQuestionRepository()
        self.statistics = SyncStatisticsRepository()
        self.topics = SyncTopicRepository()
        
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
    
    def get_admin_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get admin information by user_id"""
        return self.admins.get_admin_by_id(user_id)
    
    def update_admin_info(self, user_id: int, full_name: str) -> bool:
        """Update admin's full name"""
        result = self.admins.update_admin_info(user_id, full_name=full_name)
        if result:
            self._clear_cache_for_user(user_id)
        return result
    
    # User operations - delegate to UserRepository
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
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's language"""
        user = self.users.get_user_by_id(user_id)
        return user.get('language', 'ru') if user else 'ru'
    
    def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information"""
        return self.users.get_user_by_id(user_id)
    
    def set_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        """Set user information (create or update)"""
        self.users.set_user_info(user_id, full_name, grade)
    
    def set_user_info_with_language(self, user_id: int, full_name: str, grade: int, language: str) -> None:
        """Set user information with language (create or update)"""
        self.users.set_user_info_with_language(user_id, full_name, grade, language)
    
    def update_user_language(self, user_id: int, language: str) -> None:
        """Update user's language"""
        self.users.update_user_language(user_id, language)
    
    # User activity methods
    def is_user_active(self, user_id: int) -> bool:
        """Check if user is currently active (taking a test)"""
        user = self.users.get_user_by_id(user_id)
        return user.get('is_active', False) if user else False
    
    def set_user_active(self, user_id: int, topic: str) -> None:
        """Set user as active with current topic"""
        self.users.update_user_activity(user_id, topic)
    
    def set_user_inactive(self, user_id: int) -> None:
        """Set user as inactive and clear current topic"""
        self.users.update_user_activity(user_id, None)
    
    # Additional user access methods from main branch - delegate to UserRepository
    def has_user_access(self, user_id: int) -> bool:
        """Check if user has access to the system"""
        return self.users.has_user_access(user_id)
    
    def is_user_allowed(self, username: str) -> bool:
        """Check if user is in whitelist by username"""
        return self.users.is_user_allowed(username)
    
    def is_user_allowed_by_id(self, user_id: int) -> bool:
        """Check if user is allowed by user_id"""
        return self.users.has_user_access(user_id)
    
    def add_allowed_user(self, username: str, full_name: str, grade: int, added_by: int, 
                        user_id: int = None, language: str = "ru") -> bool:
        """Add user to whitelist"""
        return self.users.add_allowed_user(username, full_name, grade, added_by, user_id, language)
    
    def add_allowed_user_by_id(self, user_id: int, full_name: str, grade: int, added_by: int, 
                              username: str = None, language: str = "ru") -> bool:
        """Add user to whitelist by user_id"""
        return self.users.add_user(user_id, username, full_name, grade, language, added_by)
    
    def remove_allowed_user(self, username: str) -> bool:
        """Remove user from whitelist by username"""
        return self.users.remove_allowed_user(username)
    
    def remove_allowed_user_by_id(self, user_id: int) -> bool:
        """Remove user from whitelist by user_id"""
        return self.users.remove_user_access(user_id)
    
    def update_allowed_user(self, username: str, full_name: str = None, grade: int = None, 
                           is_active: bool = None) -> bool:
        """Update allowed user info by username"""
        return self.users.update_allowed_user(username, full_name, grade, is_active)
    
    def update_allowed_user_by_id(self, user_id: int, full_name: str = None, grade: int = None, 
                                 has_access: bool = None) -> bool:
        """Update allowed user info by user_id"""
        return self.users.update_allowed_user_by_id(user_id, full_name, grade, has_access)
    
    def get_all_allowed_users(self) -> List[Dict[str, Any]]:
        """Get all allowed users"""
        return self.users.get_all_users()
    
    def get_allowed_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get allowed user by ID"""
        return self.users.get_allowed_user_by_id(user_id)
    
    # Topic operations - delegate to TopicRepository
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
        """Get questions by user language (sync)"""
        return self.questions.get_questions_by_user_language(user_id)
    
    def delete_question_by_id(self, question_id: int) -> bool:
        """Delete question by ID (sync)"""
        return self.questions.delete_question_by_id(question_id)
    
    def get_all_ai_questions(self) -> List[Dict]:
        """Get all AI questions (sync)"""
        return self.questions.get_all_ai_questions()
    
    # Additional topic methods from main branch - delegate to TopicRepository
    def get_all_topics(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all topics"""
        return self.topics.get_all_topics(active_only)
    
    def add_topic(self, name: str, description: str = None, created_by: int = None, 
                  main_topic_name: str = None) -> bool:
        """Add new topic"""
        # Find main topic ID by name if provided
        if main_topic_name:
            main_topics = self.topics.get_main_topics_by_language('ru')  # Default to Russian
            for mt in main_topics:
                if mt['name'] == main_topic_name:
                    return self.topics.add_topic(name, mt['id'], created_by)
        return False
    
    def update_topic(self, topic_id: int, name: str = None, description: str = None, 
                    is_active: bool = None) -> bool:
        """Update topic"""
        return self.topics.update_topic(topic_id, name, is_active)
    
    def delete_topic(self, topic_id: int) -> bool:
        """Delete topic (soft delete)"""
        return self.topics.delete_topic(topic_id)
    
    def delete_topic_permanently(self, topic_id: int) -> bool:
        """Permanently delete topic and all related data"""
        return self.topics.delete_topic_permanently(topic_id)
    
    # Statistics operations - delegate to StatisticsRepository
    def add_test_result(self, user_id: int, topic: str, percentage: float) -> None:
        """Add test result (sync)"""
        self.statistics.add_test_result(user_id, topic, percentage)
        self._clear_cache_for_user(user_id)
    
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
        """Get error topics (sync)"""
        return self.statistics.get_error_topics(user_id)
    
    def add_user_error(self, user_id: int, topic: str, question_text: str,
                      user_answer_text: str, correct_answer_text: str,
                      explanation_text: str) -> None:
        """Add user error (sync)"""
        self.statistics.add_user_error(user_id, topic, question_text, 
                                     user_answer_text, correct_answer_text)
        self._clear_cache_for_user(user_id)
    
    def add_user_error_by_question_id(self, user_id: int, question_id: int, topic: str,
                                     user_answer_text: str, correct_answer_text: str) -> None:
        """Add user error by question ID (sync)"""
        self.statistics.add_user_error_by_question_id(user_id, question_id, topic,
                                                     user_answer_text, correct_answer_text)
        self._clear_cache_for_user(user_id)
    
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
        self._clear_cache_for_user(user_id)
    
    def decrement_error_count_by_question_id(self, user_id: int, question_id: int) -> None:
        """Decrement error count by question ID (sync)"""
        self.statistics.decrement_error_count_by_question_id(user_id, question_id)
        self._clear_cache_for_user(user_id)
    
    def get_student_detailed_statistics(self, user_id: int) -> Optional[Dict]:
        """Get detailed student statistics (sync)"""
        return self.statistics.get_student_detailed_statistics(user_id)
    
    # Additional methods from main branch - delegate to appropriate repositories
    def get_explanation_fuzzy_by_question_text(self, question_text: str) -> Optional[str]:
        """Get explanation using fuzzy matching"""
        return self.questions.get_explanation_fuzzy_by_question_text(question_text)
    
    def delete_all_user_data(self, user_id: int) -> bool:
        """Delete all data associated with a user"""
        return self.users.delete_all_user_data(user_id)
    
    def set_all_users_inactive(self) -> None:
        """Set all users as inactive"""
        self.users.set_all_users_inactive()
    
    def clear_user_activity(self, user_id: int) -> None:
        """Clear user activity and set as inactive"""
        self.users.clear_user_activity(user_id)
    
    def register_user(self, user_id: int, username: str) -> None:
        """Register user if they don't exist"""
        self.users.register_user(user_id, username)
    
    def update_question(self, question_text: str, new_answer: str, new_explanation: str) -> None:
        """Update a question's answer and explanation"""
        self.questions.update_question(question_text, new_answer, new_explanation)
    
    def update_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        """Update user information"""
        self.users.update_user_info(user_id, full_name, grade)
    
    # Topic structure methods - delegate to TopicRepository
    def get_base_topic_structure(self) -> Dict[str, List[str]]:
        """Get base topic structure"""
        return self.topics.get_base_topic_structure()
    
    def get_base_topic_structure_by_language(self, language: str) -> Dict[str, List[str]]:
        """Get base topic structure by language"""
        return self.topics.get_base_topic_structure_by_language(language)
    
    def add_base_topic_section(self, main_topic: str, subtopics: List[str], created_by: int = None) -> bool:
        """Add base topic section"""
        return self.topics.add_main_topic_with_language(main_topic, 'ru', subtopics, created_by)
    
    def update_topic_section(self, topic_id: int, new_main_topic_name: str) -> bool:
        """Update topic section"""
        # Helper function to clean topic name from emojis
        def clean_topic_name(name: str) -> str:
            clean_name = name
            emojis_to_remove = ['📊', '📐', '🔢', '🔤', '🧠', '⚡', '🎯', '💡', '🔥', '✨']
            for emoji in emojis_to_remove:
                clean_name = clean_name.replace(emoji, '')
            return clean_name.strip()
        
        # Find new main topic ID in all languages
        # First try Russian
        ru_topics = self.topics.get_main_topics_by_language('ru')
        for mt in ru_topics:
            # Check exact match first
            if mt['name'] == new_main_topic_name:
                return self.topics.update_topic_section(topic_id, mt['id'])
            
            # Check if topic name matches without emoji
            if clean_topic_name(mt['name']) == new_main_topic_name:
                return self.topics.update_topic_section(topic_id, mt['id'])
        
        # Then try Kazakh
        kk_topics = self.topics.get_main_topics_by_language('kk')
        for mt in kk_topics:
            # Check exact match first
            if mt['name'] == new_main_topic_name:
                return self.topics.update_topic_section(topic_id, mt['id'])
            
            # Check if topic name matches without emoji
            if clean_topic_name(mt['name']) == new_main_topic_name:
                return self.topics.update_topic_section(topic_id, mt['id'])
        
        return False
    
    def delete_base_topic_section(self, main_topic: str, hard_delete: bool = False) -> bool:
        """Delete base topic section"""
        if hard_delete:
            # Для полного удаления нужно знать язык, попробуем найти его
            # Сначала попробуем русский
            ru_topics = self.topics.get_main_topics_by_language('ru', active_only=False)
            for topic in ru_topics:
                if topic['name'] == main_topic:
                    return self.topics.delete_main_topic_permanently(main_topic, 'ru')
            
            # Если не найден в русских, попробуем казахский
            kk_topics = self.topics.get_main_topics_by_language('kk', active_only=False)
            for topic in kk_topics:
                if topic['name'] == main_topic:
                    return self.topics.delete_main_topic_permanently(main_topic, 'kk')
            
            # Если не найден ни в одном языке, попробуем удалить без указания языка
            return self.topics.delete_main_topic_permanently(main_topic)
        else:
            # Мягкое удаление - просто деактивация
            return self.topics.toggle_main_topic_status(main_topic)
    
    def delete_base_topic_section_with_language(self, main_topic: str, language: str, hard_delete: bool = False) -> bool:
        """Delete base topic section with specific language"""
        if hard_delete:
            return self.topics.delete_main_topic_permanently(main_topic, language)
        else:
            return self.topics.toggle_main_topic_status_by_language(main_topic, language)
    
    def add_base_subtopic(self, main_topic: str, subtopic: str) -> bool:
        """Add base subtopic"""
        # Find main topic ID
        main_topics = self.topics.get_main_topics_by_language('ru')
        for mt in main_topics:
            if mt['name'] == main_topic:
                return self.topics.add_topic(subtopic, mt['id'])
        return False
    
    def remove_base_subtopic(self, main_topic: str, subtopic: str) -> bool:
        """Remove base subtopic"""
        # Find subtopic and deactivate it
        all_topics = self.topics.get_all_topics(active_only=False)
        for topic in all_topics:
            if topic['name'] == subtopic and topic['main_topic'] == main_topic:
                return self.topics.update_topic(topic['id'], is_active=False)
        return False
    
    def get_user_full_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get complete user profile"""
        return self.users.get_user_by_id(user_id)
    
    def sync_user_with_whitelist(self, user_id: int, username: str) -> bool:
        """Sync user with whitelist"""
        return self.users.sync_user_with_whitelist(user_id, username)
    
    def get_user_historical_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user historical statistics"""
        return self.users.get_user_historical_stats(user_id)
    
    def get_all_users_with_history(self) -> List[Dict[str, Any]]:
        """Get all users with history"""
        return self.users.get_all_users_with_history()
    
    def get_topic_question_counts(self) -> Dict[str, int]:
        """Get question count for each topic"""
        return self.topics.get_topic_question_counts()
    
    def get_topics_with_question_counts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get topics with question counts"""
        return self.topics.get_topics_with_question_counts(active_only)
    
    def get_all_students_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all students"""
        return self.users.get_all_students_summary()
    
    def get_class_statistics(self, grade: int = None) -> Dict[str, Any]:
        """Get class statistics"""
        return self.users.get_class_statistics(grade)
    
    def get_detailed_class_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics grouped by class"""
        return self.users.get_detailed_class_statistics()
    
    def get_student_contact_info(self, user_id: int) -> Dict[str, Any]:
        """Get student contact info"""
        return self.statistics.get_student_contact_info(user_id)
    
    def find_student_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Find student by identifier"""
        return self.users.find_student_by_identifier(identifier)
    
    def get_comprehensive_user_access_check(self, user_id: int, username: str = None) -> Dict[str, Any]:
        """Comprehensive user access check"""
        return self.users.get_comprehensive_user_access_check(user_id, username)
    
    # Language-related methods
    def clear_user_data_on_language_change(self, user_id: int) -> None:
        """Clear user data on language change"""
        self.users.clear_user_data_on_language_change(user_id)
    
    def get_topics_by_language(self, language: str, active_only: bool = True) -> List[Dict]:
        """Get topics by language"""
        return self.questions.get_topics_by_language(language, active_only)
    
    def get_questions_by_user_language(self, user_id: int, topic: str = None) -> List[Dict]:
        """Get questions by user language"""
        return self.questions.get_questions_by_user_language(user_id, topic)
    
    def add_topic_with_language(self, name: str, language: str, main_topic_name: str, 
                               created_by: int = None) -> bool:
        """Add topic with language"""
        # Find main topic ID by name and language
        main_topics = self.topics.get_main_topics_by_language(language)
        for mt in main_topics:
            # Check exact match first
            if mt['name'] == main_topic_name:
                return self.topics.add_topic(name, mt['id'], created_by)
            
            # Check if topic name matches without emoji (for backward compatibility)
            # Remove emoji and extra spaces from stored topic name
            clean_stored_name = mt['name']
            # Remove common emojis
            emojis_to_remove = ['📊', '📐', '🔢', '🔤', '🧠', '⚡', '🎯', '💡', '🔥', '✨']
            for emoji in emojis_to_remove:
                clean_stored_name = clean_stored_name.replace(emoji, '')
            clean_stored_name = clean_stored_name.strip()
            
            if clean_stored_name == main_topic_name:
                return self.topics.add_topic(name, mt['id'], created_by)
        
        return False
    
    def get_topics_with_language_info(self, active_only: bool = True, for_admin: bool = False) -> List[Dict[str, Any]]:
        """Get topics with language info"""
        return self.questions.get_topics_with_language_info(active_only, for_admin)
    
    def create_kazakh_main_topics(self) -> bool:
        """Create Kazakh main topics"""
        logger.warning("create_kazakh_main_topics not implemented - requires specific topic data")
        return False
    
    def create_russian_main_topics(self) -> bool:
        """Create Russian main topics"""
        logger.warning("create_russian_main_topics not implemented - requires specific topic data")
        return False
    
    def get_main_topics_by_language(self, language: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get main topics by language"""
        return self.topics.get_main_topics_by_language(language, active_only)
    
    def get_full_topic_structure_by_language(self, language: str, active_only: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """Get full topic structure by language"""
        return self.topics.get_full_topic_structure_by_language(language, active_only)
    
    def get_topic_language(self, topic_name: str) -> str:
        """Get topic language"""
        return self.topics.get_topic_language(topic_name)
    
    def get_main_topic_and_language_for_subtopic(self, subtopic_name: str) -> Tuple[Optional[str], str]:
        """Get main topic and language for subtopic"""
        return self.topics.get_main_topic_and_language_for_subtopic(subtopic_name)
    
    def sync_subtopic_languages_with_main_topics(self) -> bool:
        """Sync subtopic languages with main topics"""
        logger.warning("sync_subtopic_languages_with_main_topics complex operation - not implemented")
        return False
    
    def get_user_display_info(self, user_id: int) -> Dict[str, Any]:
        """Get user display info"""
        return self.statistics.get_user_display_info(user_id)
    
    # Topic management methods - delegate to TopicRepository
    def get_subtopics_by_main_topic(self, main_topic_name: str) -> List[str]:
        """Get subtopics by main topic"""
        return self.topics.get_subtopics_by_main_topic(main_topic_name)
    
    def toggle_topic_status(self, topic_id: int) -> bool:
        """Toggle topic status"""
        return self.topics.toggle_topic_status(topic_id)
    
    def update_topic_name(self, topic_id: int, new_name: str) -> bool:
        """Update topic name"""
        return self.topics.update_topic_name(topic_id, new_name)
    
    def delete_topic_completely(self, topic_id: int) -> bool:
        """Delete topic completely"""
        return self.topics.delete_topic_completely(topic_id)
    
    def add_main_topic_with_language(self, main_topic: str, language: str, 
                                    subtopics: List[str] = None, created_by: int = None) -> bool:
        """Add main topic with language"""
        return self.topics.add_main_topic_with_language(main_topic, language, subtopics, created_by)
    
    def toggle_main_topic_status(self, main_topic_name: str) -> bool:
        """Toggle main topic status"""
        return self.topics.toggle_main_topic_status(main_topic_name)
    
    def toggle_main_topic_status_by_language(self, main_topic_name: str, language: str) -> bool:
        """Toggle main topic status by name and language"""
        return self.topics.toggle_main_topic_status_by_language(main_topic_name, language)
    
    def clear_user_test_activity(self, user_id: int) -> None:
        """Clear user test activity"""
        self.users.update_user_activity(user_id, None)
    
    def is_user_system_active(self, user_id: int) -> bool:
        """Check if user is active in system"""
        return self.users.has_user_access(user_id)
    
    def set_user_access(self, user_id: int, has_access: bool) -> bool:
        """Set user access status"""
        if has_access:
            return self.users.restore_user_access(user_id)
        else:
            return self.users.remove_user_access(user_id)
    
    # New topic_id methods - delegate to appropriate repositories
    def get_tasks_for_topic_id(self, topic_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get tasks for topic by ID"""
        return self.questions.get_tasks_for_topic_id(topic_id, limit)
    
    def get_error_tasks_for_user_by_topic_id(self, user_id: int, topic_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get error tasks for user by topic ID"""
        return self.statistics.get_error_tasks_for_user_by_topic_id(user_id, topic_id, limit)
    
    def add_question_with_topic_id(self, question: dict, topic_id: int) -> bool:
        """Add question with topic ID"""
        return self.questions.add_question_with_topic_id(question, topic_id)
    
    def get_topic_question_counts_by_id(self) -> Dict[int, Dict[str, Any]]:
        """Get topic question counts by ID"""
        return self.topics.get_topic_question_counts_by_id()
    
    def rename_topic_by_id(self, topic_id: int, new_name: str) -> bool:
        """Rename topic by ID"""
        return self.topics.rename_topic_by_id(topic_id, new_name)
    
    def rename_topic_by_name(self, old_name: str, new_name: str) -> bool:
        """Rename topic by name"""
        return self.topics.rename_topic_by_name(old_name, new_name)
    
    def get_topic_hierarchy_kk(self) -> Dict[str, Any]:
        """Get Kazakh topic hierarchy"""
        try:
            from src.config.constants_kk import TOPIC_HIERARCHY_KK
            return TOPIC_HIERARCHY_KK
        except ImportError:
            logger.warning("Failed to import TOPIC_HIERARCHY_KK")
            return {}
    
    def get_topic_hierarchy_ru(self) -> Dict[str, Any]:
        """Get Russian topic hierarchy"""
        try:
            from src.config.constants import TOPIC_HIERARCHY
            return TOPIC_HIERARCHY
        except ImportError:
            logger.warning("Failed to import TOPIC_HIERARCHY")
            return {}
    
    def close_connections(self):
        """Close database connections"""
        # In the current implementation, repositories handle their own connections
        logger.info("Database connections closed")

def get_sync_database_facade() -> SyncDatabaseFacade:
    """
    Get singleton instance of SyncDatabaseFacade
    """
    global _sync_database_facade_instance
    if '_sync_database_facade_instance' not in globals():
        _sync_database_facade_instance = SyncDatabaseFacade()
    return _sync_database_facade_instance 