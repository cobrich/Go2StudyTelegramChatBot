"""
Database Facade

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
    Unified database interface that maintains compatibility with existing Database class.
    
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
        
        # Initialize database schema
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema if needed."""
        try:
            # Create tables
            table_definitions = self.models.get_table_definitions()
            
            if self.connection_manager.is_postgresql():
                self._init_postgresql_schema(table_definitions)
            else:
                self._init_sqlite_schema(table_definitions)
            
            # Initialize topic structure
            self._init_topic_structure()
            
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def _init_postgresql_schema(self, table_definitions: Dict[str, str]):
        """Initialize PostgreSQL schema."""
        import asyncio
        
        async def create_tables():
            async with self.connection_manager.get_async_connection() as conn:
                for table_name, table_sql in table_definitions.items():
                    try:
                        await conn.execute(table_sql)
                        logger.info(f"Created/verified table: {table_name}")
                    except Exception as e:
                        logger.error(f"Error creating table {table_name}: {e}")
                        raise
        
        # Run in new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(create_tables())
        finally:
            loop.close()
    
    def _init_sqlite_schema(self, table_definitions: Dict[str, str]):
        """Initialize SQLite schema."""
        with self.connection_manager.get_sync_connection() as conn:
            cursor = conn.cursor()
            for table_name, table_sql in table_definitions.items():
                try:
                    cursor.execute(table_sql)
                    logger.info(f"Created/verified table: {table_name}")
                except Exception as e:
                    logger.error(f"Error creating table {table_name}: {e}")
                    raise
            conn.commit()
    
    def _init_topic_structure(self):
        """Initialize basic topic structure for both languages."""
        try:
            # Initialize Russian topics
            self._init_language_topics('ru')
            # Initialize Kazakh topics  
            self._init_language_topics('kk')
            logger.info("Topic structure initialized")
        except Exception as e:
            logger.error(f"Error initializing topic structure: {e}")
    
    def _init_language_topics(self, language: str):
        """Initialize topics for specific language."""
        topics_data = {
            'ru': {
                'Математика': [
                    'Алгебра', 'Геометрия', 'Арифметика', 'Тригонометрия'
                ],
                'Физика': [
                    'Механика', 'Термодинамика', 'Электричество', 'Оптика'
                ],
                'Химия': [
                    'Органическая химия', 'Неорганическая химия', 'Аналитическая химия'
                ],
                'Биология': [
                    'Ботаника', 'Зоология', 'Анатомия', 'Генетика'
                ]
            },
            'kk': {
                'Математика': [
                    'Алгебра', 'Геометрия', 'Арифметика', 'Тригонометрия'
                ],
                'Физика': [
                    'Механика', 'Термодинамика', 'Электр', 'Оптика'
                ],
                'Химия': [
                    'Органикалық химия', 'Бейорганикалық химия', 'Аналитикалық химия'
                ],
                'Биология': [
                    'Ботаника', 'Зоология', 'Анатомия', 'Генетика'
                ]
            }
        }
        
        if language not in topics_data:
            return
        
        for main_topic_name, subtopics in topics_data[language].items():
            # Create main topic if not exists
            main_topic_id = self._create_main_topic_if_not_exists(main_topic_name, language)
            
            # Create subtopics
            for index, subtopic_name in enumerate(subtopics):
                self._create_subtopic_if_not_exists(subtopic_name, main_topic_id, index + 1)
    
    def _create_main_topic_if_not_exists(self, name: str, language: str) -> int:
        """Create main topic if it doesn't exist and return ID."""
        # Check if exists
        check_query = f'SELECT id FROM main_topics WHERE topic_name = {self._get_placeholder(1)} AND language = {self._get_placeholder(2)}'
        existing_id = self.users.fetch_val(check_query, (name, language))
        
        if existing_id:
            return existing_id
        
        # Create main topic (убираем order_index, его нет в новой схеме)
        insert_query = f'''
            INSERT INTO main_topics (topic_name, language)
            VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)})
        '''
        self.users.execute_query(insert_query, (name, language))
        
        # Get the created ID
        return self.users.fetch_val(check_query, (name, language))
    
    def _create_subtopic_if_not_exists(self, name: str, main_topic_id: int, order_index: int):
        """Create subtopic if it doesn't exist."""
        # Check if exists
        check_query = f'SELECT id FROM subtopics WHERE subtopic_name = {self._get_placeholder(1)} AND main_topic_id = {self._get_placeholder(2)}'
        existing_id = self.users.fetch_val(check_query, (name, main_topic_id))
        
        if existing_id:
            return
        
        # Create subtopic (убираем order_index, его нет в новой схеме)
        insert_query = f'''
            INSERT INTO subtopics (main_topic_id, subtopic_name)
            VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)})
        '''
        self.users.execute_query(insert_query, (main_topic_id, name))
    
    def _get_placeholder(self, index: int = 1) -> str:
        """Get parameter placeholder for current database type."""
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
    
    # User Registration Methods
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
    
    # User Listing Methods
    def get_all_allowed_users(self) -> List[Dict]:
        return self.users.get_all_allowed_users()
    
    def get_allowed_user_by_id(self, user_id: int) -> Optional[Dict]:
        return self.users.get_allowed_user_by_id(user_id)
    
    # User Data Cleanup Methods
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
    
    # Topic and Question Methods
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
    
    # Error Tracking Methods
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
    
    # Additional compatibility methods that might be needed
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

# Create a singleton instance for backward compatibility
_database_instance = None

def get_database() -> DatabaseFacade:
    """Get singleton database instance."""
    global _database_instance
    if _database_instance is None:
        _database_instance = DatabaseFacade()
    return _database_instance 