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
        
        # Initialize repositories
        self.users = UserRepository()
        self.admins = AdminRepository()
        self.questions = QuestionRepository()
        self.statistics = StatisticsRepository()
        
        logger.info("DatabaseFacade initialized for Supabase")
    
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

def get_database() -> DatabaseFacade:
    """Get global database facade instance"""
    global _database_facade
    if '_database_facade' not in globals():
        _database_facade = DatabaseFacade()
    return _database_facade 