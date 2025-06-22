"""
Database Facade for Supabase

Provides unified interface to all database operations through repositories.
This maintains compatibility with the existing Database class interface.
"""

import logging
from typing import Dict, List, Optional, Tuple

from .connection_manager import get_connection_manager
from .models import DatabaseModels
from .repositories import UserRepository, AdminRepository, QuestionRepository, StatisticsRepository

logger = logging.getLogger(__name__)

class DatabaseFacade:
    """
    Unified Supabase database interface that maintains compatibility with existing Database class.
    
    This facade delegates operations to appropriate repositories while maintaining
    the same method signatures as the original Database class.
    """
    
    def __init__(self):
        """Initialize the database facade with all repositories."""
        self.connection_manager = get_connection_manager()
        self.models = DatabaseModels()
        self._tables_initialized = False
        
        # Initialize repositories
        self.users = UserRepository()
        self.admins = AdminRepository()
        self.questions = QuestionRepository()
        self.statistics = StatisticsRepository()
        
        logger.info("DatabaseFacade initialized for Supabase")
    
    async def ensure_tables_exist(self):
        """Ensure database tables exist (lazy initialization)"""
        if not self._tables_initialized:
            try:
                await self.connection_manager.initialize_pool()
                self._tables_initialized = True
                logger.info("Database tables ensured to exist")
            except Exception as e:
                logger.error(f"Failed to ensure tables exist: {e}")
                # Не поднимаем исключение, позволяем системе работать
    
    def init_tables_sync(self):
        """Synchronous wrapper for table initialization"""
        import asyncio
        import concurrent.futures
        
        def run_in_thread():
            """Запускаем инициализацию в отдельном потоке с новым event loop"""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(self.ensure_tables_exist())
            except Exception as e:
                logger.error(f"Error in table initialization thread: {e}")
                # Не поднимаем исключение, позволяем боту работать
                return None
            finally:
                new_loop.close()
        
        try:
            # Проверяем, есть ли активный event loop
            try:
                loop = asyncio.get_running_loop()
                # Если есть активный loop, запускаем в отдельном потоке
                logger.info("Active event loop detected, initializing tables in separate thread...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_in_thread)
                    try:
                        future.result(timeout=60)  # 60 секунд на инициализацию
                        logger.info("Database tables initialization completed")
                    except concurrent.futures.TimeoutError:
                        logger.warning("Database initialization timeout - will initialize on first access")
                    except Exception as e:
                        logger.warning(f"Database initialization error: {e} - will initialize on first access")
                        
            except RuntimeError:
                # Нет активного event loop, можем использовать asyncio.run
                try:
                    asyncio.run(self.ensure_tables_exist())
                    logger.info("Database tables initialization completed")
                except Exception as e:
                    logger.warning(f"Database initialization error: {e} - will initialize on first access")
                    
        except Exception as e:
            logger.warning(f"Could not initialize tables: {e}. Bot will try to initialize them on first database access.")
    
    def _get_placeholder(self, index: int = 1) -> str:
        """Get parameter placeholder for PostgreSQL."""
        return self.users._get_placeholder(index)
    
    # ============== COMPATIBILITY METHODS ==============
    # These methods maintain compatibility with the original Database class interface
    
    # User Activity Methods
    def set_user_active(self, user_id: int, topic: str) -> None:
        return self.users.set_user_active(user_id, topic)
    
    def set_user_inactive(self, user_id: int) -> None:
        return self.users.set_user_inactive(user_id)
    
    def is_user_active(self, user_id: int) -> bool:
        return self.users.is_user_active(user_id)
    
    def update_user_activity(self, user_id: int) -> None:
        return self.users.update_user_activity(user_id)
    
    # User Info Methods
    def get_user_info(self, user_id: int) -> Optional[Dict]:
        return self.users.get_user_info(user_id)
    
    def get_user_full_profile(self, user_id: int) -> Optional[Dict]:
        return self.users.get_user_full_profile(user_id)
    
    def set_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        return self.users.set_user_info(user_id, full_name, grade)
    
    def set_user_info_with_language(self, user_id: int, full_name: str, grade: int, language: str) -> None:
        return self.users.set_user_info_with_language(user_id, full_name, grade, language)
    
    def update_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        return self.users.update_user_info(user_id, full_name, grade)
    
    # User Language Methods
    def get_user_language(self, user_id: int) -> str:
        return self.users.get_user_language(user_id)
    
    def update_user_language(self, user_id: int, language: str) -> None:
        return self.users.update_user_language(user_id, language)
    
    # User Access Methods
    def is_user_allowed(self, username: str) -> bool:
        return self.users.is_user_allowed(username)
    
    def is_user_allowed_by_id(self, user_id: int) -> bool:
        return self.users.is_user_allowed_by_id(user_id)
    
    def has_user_access(self, user_id: int) -> bool:
        return self.users.has_user_access(user_id)
    
    def set_user_access(self, user_id: int, has_access: bool) -> bool:
        return self.users.set_user_access(user_id, has_access)
    
    def add_allowed_user(self, username: str, full_name: str, grade: int, added_by: int, 
                        user_id: int = None, language: str = "ru") -> bool:
        return self.users.add_allowed_user(username, full_name, grade, added_by, user_id, language)
    
    def add_allowed_user_by_id(self, user_id: int, full_name: str, grade: int, added_by: int, 
                              username: str = None, language: str = "ru") -> bool:
        return self.users.add_allowed_user_by_id(user_id, full_name, grade, added_by, username, language)
    
    def remove_allowed_user(self, username: str) -> bool:
        return self.users.remove_allowed_user(username)
    
    def remove_allowed_user_by_id(self, user_id: int) -> bool:
        return self.users.remove_allowed_user_by_id(user_id)
    
    def get_all_allowed_users(self) -> List[Dict]:
        return self.users.get_all_allowed_users()
    
    def get_allowed_user_by_id(self, user_id: int) -> Optional[Dict]:
        return self.users.get_allowed_user_by_id(user_id)
    
    def delete_all_user_data(self, user_id: int) -> bool:
        return self.users.delete_all_user_data(user_id)
    
    def clear_user_activity(self, user_id: int) -> None:
        return self.users.clear_user_activity(user_id)
    
    def set_all_users_inactive(self):
        return self.users.set_all_users_inactive()
    
    # Admin Methods
    def is_super_admin(self, user_id: int) -> bool:
        return self.admins.is_super_admin(user_id)
    
    def is_admin(self, user_id: int) -> bool:
        return self.admins.is_admin(user_id)
    
    def add_admin(self, user_id: int, username: str, full_name: str, is_super: bool = False, added_by: int = None) -> bool:
        return self.admins.add_admin(user_id, username, full_name, is_super, added_by)
    
    def remove_admin(self, user_id: int) -> bool:
        return self.admins.remove_admin(user_id)
    
    def get_all_admins(self) -> List[Dict]:
        return self.admins.get_all_admins()
    
    def get_admin_info(self, user_id: int) -> Optional[Dict]:
        return self.admins.get_admin_info(user_id)
    
    # Topic Methods
    def get_all_topics(self, active_only: bool = True) -> List[Dict]:
        return self.questions.get_all_topics(active_only)
    
    def get_topics_by_language(self, language: str, active_only: bool = True) -> Dict[str, List[Dict]]:
        return self.questions.get_topics_by_language(language, active_only)
    
    def get_topic_names(self, active_only: bool = True) -> List[str]:
        return self.questions.get_topic_names(active_only)
    
    def get_tasks_for_topic(self, topic: str, limit: int = 20) -> List[Dict]:
        return self.questions.get_tasks_for_topic(topic, limit)
    
    def get_all_questions(self) -> List[Dict]:
        return self.questions.get_all_questions()
    
    def add_question(self, question: dict) -> bool:
        return self.questions.add_question(question)
    
    def add_topic(self, name: str, description: str = None, created_by: int = None, main_topic_name: str = None) -> bool:
        return self.questions.add_topic(name, description, created_by, main_topic_name)
    
    def get_topics_with_question_counts(self, active_only: bool = True) -> List[Dict]:
        return self.questions.get_topics_with_question_counts(active_only)
    
    # Statistics Methods
    def add_test_result(self, user_id: int, topic: str, percentage: float) -> None:
        return self.statistics.add_test_result(user_id, topic, percentage)
    
    def get_user_test_results(self, user_id: int) -> List[Dict]:
        return self.statistics.get_user_test_results(user_id)
    
    def get_user_progress(self, user_id: int) -> Tuple[int, float]:
        return self.statistics.get_user_progress(user_id)
    
    def get_recent_topics(self, user_id: int, limit: int = 5) -> List[Tuple[str, float, str]]:
        return self.statistics.get_recent_topics(user_id, limit)
    
    def get_recent_unique_topics(self, user_id: int, unique_limit: int = 5, history_limit: int = 20) -> List[Tuple[str, int]]:
        return self.statistics.get_recent_unique_topics(user_id, unique_limit, history_limit)
    
    # Error Methods
    def add_user_error(self, user_id: int, topic: str, question_text: str,
                      user_answer_text: str, correct_answer_text: str,
                      explanation_text: str) -> None:
        return self.statistics.add_user_error(user_id, topic, question_text,
                                            user_answer_text, correct_answer_text, explanation_text)
    
    def get_error_tasks_for_user(self, user_id: int, topic: str, limit: int = 10) -> List[Dict]:
        return self.statistics.get_error_tasks_for_user(user_id, topic, limit)
    
    def get_error_topics(self, user_id: int) -> List[Tuple[str, int]]:
        return self.statistics.get_error_topics(user_id)
    
    def decrement_error_count(self, user_id: int, question_text: str) -> None:
        return self.statistics.decrement_error_count(user_id, question_text)
    
    # Advanced Statistics Methods
    def get_user_historical_stats(self, user_id: int) -> Dict:
        return self.statistics.get_user_historical_stats(user_id)
    
    def get_student_detailed_statistics(self, user_id: int) -> Optional[Dict]:
        return self.statistics.get_student_detailed_statistics(user_id)
    
    def get_all_students_summary(self) -> List[Dict]:
        return self.statistics.get_all_students_summary()
    
    def get_class_statistics(self, grade: int = None) -> Dict:
        return self.statistics.get_class_statistics(grade)
    
    # Utility Methods
    def register_user(self, user_id: int, username: str) -> None:
        return self.users.register_user(user_id, username)
    
    def get_explanation_by_question_text(self, question_text: str) -> Optional[str]:
        return self.questions.get_explanation_by_question_text(question_text)
    
    def update_question(self, question_text: str, new_answer: str, new_explanation: str) -> bool:
        return self.questions.update_question(question_text, new_answer, new_explanation)
    
    def delete_question_by_id(self, question_id: int) -> bool:
        return self.questions.delete_question_by_id(question_id)
    
    def get_all_ai_questions(self) -> List[Dict]:
        return self.questions.get_all_ai_questions()
    
    # Additional methods for questions management
    def search_questions(self, search_term: str, limit: int = 50) -> List[Dict]:
        """Search questions by text"""
        return self.questions.search_questions(search_term, limit)
    
    def get_question_by_id(self, question_id: int) -> Optional[Dict]:
        """Get question by ID"""
        return self.questions.get_question_by_id(question_id)
    
    def update_question_explanation(self, question_id: int, explanation: str) -> bool:
        """Update question explanation"""
        return self.questions.update_question_explanation(question_id, explanation)
    
    def update_question_text(self, question_id: int, question_text: str) -> bool:
        """Update question text"""
        return self.questions.update_question_text(question_id, question_text)
    
    def update_question_correct_answer(self, question_id: int, correct_answer: str) -> bool:
        """Update question correct answer"""
        return self.questions.update_question_correct_answer(question_id, correct_answer)
    
    def update_question_options(self, question_id: int, options: List[str]) -> bool:
        """Update question options"""
        return self.questions.update_question_options(question_id, options)
    
    def update_question_topic(self, question_id: int, topic_id: int) -> bool:
        """Update question topic"""
        return self.questions.update_question_topic(question_id, topic_id)
    
    def delete_questions_by_topic_id(self, topic_id: int) -> int:
        """Delete all questions for a topic and return count"""
        return self.questions.delete_questions_by_topic_id(topic_id)
    
    def get_questions_without_explanation(self, limit: int = 50) -> List[Dict]:
        """Get questions without explanations"""
        return self.questions.get_questions_without_explanation(limit)
    
    def get_questions_with_short_explanation(self, max_length: int = 50, limit: int = 50) -> List[Dict]:
        """Get questions with short explanations"""
        return self.questions.get_questions_with_short_explanation(max_length, limit)
    
    def get_questions_by_user_language(self, user_id: int) -> List[Dict]:
        """Get questions available for user based on their language"""
        user_language = self.get_user_language(user_id)
        return self.questions.get_questions_by_language(user_language)
    
    def get_main_topics_by_language(self, language: str, active_only: bool = True) -> List[Dict]:
        """Get main topics by language"""
        return self.questions.get_main_topics_by_language(language, active_only)
    
    def get_subtopics_by_main_topic(self, main_topic_name: str, user_language: str = None) -> List[Dict]:
        """Get subtopics for a main topic."""
        return self.questions.get_subtopics_by_main_topic(main_topic_name, user_language)
    
    # Additional methods for user management
    def update_allowed_user_by_id(self, user_id: int, **kwargs) -> bool:
        """Update allowed user by ID with any fields"""
        return self.users.update_allowed_user_by_id(user_id, **kwargs)
    
    def clear_user_test_activity(self, user_id: int) -> None:
        """Clear user test activity (current topic)"""
        return self.users.clear_user_test_activity(user_id)
    
    def clear_user_data_on_language_change(self, user_id: int) -> None:
        """Clear user data when language changes"""
        return self.users.clear_user_data_on_language_change(user_id)
    
    def check_user_access(self, user_id: int, username: str = None) -> bool:
        """Check if user has access to the bot"""
        return self.users.has_user_access(user_id)
    
    # Additional methods for error tracking with question IDs
    def add_user_error_by_question_id(self, user_id: int, question_id: int, topic: str,
                                     user_answer_text: str, correct_answer_text: str) -> None:
        """Add user error by question ID"""
        return self.statistics.add_user_error_by_question_id(user_id, question_id, topic,
                                                           user_answer_text, correct_answer_text)
    
    def decrement_error_count_by_question_id(self, user_id: int, question_id: int) -> None:
        """Decrement error count by question ID"""
        return self.statistics.decrement_error_count_by_question_id(user_id, question_id)
    
    def get_explanation_fuzzy_by_question_text(self, question_text: str) -> Optional[str]:
        """Get explanation using fuzzy search"""
        return self.questions.get_explanation_fuzzy_by_question_text(question_text)
    
    # ============== ADDITIONAL ADMIN METHODS ==============
    
    def count_questions_by_topic_name(self, topic_name: str) -> int:
        """Count questions for a topic by name."""
        return self.questions.count_questions_by_topic_name(topic_name)
    
    def delete_questions_by_topic_name(self, topic_name: str) -> int:
        """Delete all questions for a topic by name and return count."""
        return self.questions.delete_questions_by_topic_name(topic_name)
    
    def get_question_with_topic_by_id(self, question_id: int) -> Optional[Dict]:
        """Get question with topic information by ID."""
        return self.questions.get_question_with_topic_by_id(question_id)
    
    def get_active_topics_for_selection(self) -> List[Dict]:
        """Get active topics formatted for selection UI."""
        return self.questions.get_active_topics_for_selection()
    
    def get_topic_language(self, topic_name: str) -> str:
        """Get language for a topic by name."""
        return self.questions.get_topic_language(topic_name)
    
    def search_questions_for_edit(self, search_term: str, limit: int = 10) -> List[Tuple]:
        """Search questions for editing with topic information."""
        return self.questions.search_questions_for_edit(search_term, limit)
    
    def search_questions_for_deletion(self, search_term: str, limit: int = 10) -> List[Tuple]:
        """Search questions for deletion."""
        return self.questions.search_questions_for_deletion(search_term, limit)
    
    def get_topics_for_editing(self) -> List[Tuple]:
        """Get topics for editing with IDs and names."""
        return self.questions.get_topics_for_editing()
    
    def get_topic_name_by_id_for_edit(self, topic_id: int) -> Optional[str]:
        """Get topic name by ID for editing operations."""
        return self.questions.get_topic_name_by_id_for_edit(topic_id)
    
    def update_question_in_database(self, question_id: int, field: str, value: str) -> bool:
        """Generic method to update any question field."""
        return self.questions.update_question_in_database(question_id, field, value)
    
    def get_questions_for_explanation_improvement(self, improvement_type: str, limit: int = 50) -> List[Tuple]:
        """Get questions that need explanation improvement."""
        return self.questions.get_questions_for_explanation_improvement(improvement_type, limit)
    
    def get_explanation_improvement_stats(self) -> Dict[str, int]:
        """Get statistics for explanation improvement."""
        return self.questions.get_explanation_improvement_stats()

def get_database() -> DatabaseFacade:
    """Get global database facade instance"""
    global _database_facade
    if '_database_facade' not in globals():
        _database_facade = DatabaseFacade()
    return _database_facade 