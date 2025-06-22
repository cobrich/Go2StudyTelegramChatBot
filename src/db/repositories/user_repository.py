"""
User Repository

Handles all user-related database operations.
"""

import logging
from typing import Dict, List, Optional, Tuple
from ..base_repository import BaseRepository

logger = logging.getLogger(__name__)

class UserRepository(BaseRepository):
    """Repository for user operations"""
    
    def __init__(self):
        super().__init__()
    
    def _get_fallback_value(self):
        """Get fallback value when database is unreachable"""
        # Для пользовательских операций возвращаем пустые списки/словари
        # Это позволит системе работать без данных
        return []
    
    # ============== USER ACTIVITY METHODS ==============
    
    def set_user_active(self, user_id: int, topic: str) -> None:
        """Set user as active with current topic."""
        query = f'''
            UPDATE allowed_users 
            SET is_active = {self._get_placeholder(1)}, 
                current_topic = {self._get_placeholder(2)}, 
                last_activity = {self._get_current_timestamp()} 
            WHERE user_id = {self._get_placeholder(3)}
        '''
        params = (self._get_boolean_value(True), topic, user_id)
        self.execute_query(query, params)
    
    def set_user_inactive(self, user_id: int) -> None:
        """Set user as inactive and clear current topic."""
        query = f'''
            UPDATE allowed_users 
            SET is_active = {self._get_placeholder(1)}, 
                current_topic = NULL, 
                last_activity = {self._get_current_timestamp()} 
            WHERE user_id = {self._get_placeholder(2)}
        '''
        params = (self._get_boolean_value(False), user_id)
        self.execute_query(query, params)
    
    def is_user_active(self, user_id: int) -> bool:
        """Check if user is currently active (taking a test)."""
        query = f'SELECT is_active FROM allowed_users WHERE user_id = {self._get_placeholder(1)}'
        result = self.fetch_val(query, (user_id,))
        return bool(result)
    
    def update_user_activity(self, user_id: int) -> None:
        """Update user's last activity timestamp."""
        query = f'''
            UPDATE allowed_users 
            SET last_activity = {self._get_current_timestamp()} 
            WHERE user_id = {self._get_placeholder(1)}
        '''
        self.execute_query(query, (user_id,))
    
    # ============== USER INFO METHODS ==============
    
    def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Get basic user information."""
        query = f'''
            SELECT full_name, grade, language 
            FROM allowed_users 
            WHERE user_id = {self._get_placeholder(1)}
        '''
        return self.fetch_one(query, (user_id,))
    
    def get_user_full_profile(self, user_id: int) -> Optional[Dict]:
        """Get complete user profile."""
        query = f'''
            SELECT 
                user_id, username, full_name, grade, language,
                is_active, current_topic, last_activity, added_at
            FROM allowed_users
            WHERE user_id = {self._get_placeholder(1)}
        '''
        return self.fetch_one(query, (user_id,))
    
    def set_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        """Set user information (create or update)."""
        query = f'''
            INSERT INTO allowed_users (user_id, full_name, grade, last_activity)
            VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_placeholder(3)}, {self._get_current_timestamp()})
            ON CONFLICT (user_id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                grade = EXCLUDED.grade,
                last_activity = {self._get_current_timestamp()}
        ''' if self.is_postgresql else f'''
            INSERT OR REPLACE INTO allowed_users (user_id, full_name, grade, last_activity)
            VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_placeholder(3)}, {self._get_current_timestamp()})
        '''
        self.execute_query(query, (user_id, full_name, grade))
    
    def set_user_info_with_language(self, user_id: int, full_name: str, grade: int, language: str) -> None:
        """Set user information with language (create or update)."""
        query = f'''
            INSERT INTO allowed_users (user_id, full_name, grade, language, last_activity)
            VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_placeholder(3)}, {self._get_placeholder(4)}, {self._get_current_timestamp()})
            ON CONFLICT (user_id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                grade = EXCLUDED.grade,
                language = EXCLUDED.language,
                last_activity = {self._get_current_timestamp()}
        ''' if self.is_postgresql else f'''
            INSERT OR REPLACE INTO allowed_users (user_id, full_name, grade, language, last_activity)
            VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_placeholder(3)}, {self._get_placeholder(4)}, {self._get_current_timestamp()})
        '''
        self.execute_query(query, (user_id, full_name, grade, language))
    
    def update_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        """Update user information."""
        query = f'''
            UPDATE allowed_users 
            SET full_name = {self._get_placeholder(1)}, 
                grade = {self._get_placeholder(2)}, 
                last_activity = {self._get_current_timestamp()} 
            WHERE user_id = {self._get_placeholder(3)}
        '''
        self.execute_query(query, (full_name, grade, user_id))
    
    # ============== USER LANGUAGE METHODS ==============
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's language."""
        query = f'SELECT language FROM allowed_users WHERE user_id = {self._get_placeholder(1)}'
        result = self.fetch_val(query, (user_id,))
        return result or 'ru'
    
    def update_user_language(self, user_id: int, language: str) -> None:
        """Update user's language and clear their data if language changed."""
        # Get current language
        current_language = self.get_user_language(user_id)
        
        # Update language
        query = f'''
            UPDATE allowed_users 
            SET language = {self._get_placeholder(1)}, 
                last_activity = {self._get_current_timestamp()} 
            WHERE user_id = {self._get_placeholder(2)}
        '''
        self.execute_query(query, (language, user_id))
        
        # Clear data if language changed
        if current_language != language:
            logger.info(f"Language changed for user {user_id}: {current_language} -> {language}, clearing data")
            self.clear_user_data_on_language_change(user_id)
    
    def clear_user_data_on_language_change(self, user_id: int) -> None:
        """Clear user errors and test results when language changes."""
        try:
            # Clear user errors
            query1 = f'DELETE FROM user_errors WHERE user_id = {self._get_placeholder(1)}'
            self.execute_query(query1, (user_id,))
            
            # Clear test results
            query2 = f'DELETE FROM test_results WHERE user_id = {self._get_placeholder(1)}'
            self.execute_query(query2, (user_id,))
            
            logger.info(f"Cleared data for user {user_id} due to language change")
        except Exception as e:
            logger.error(f"Error clearing data for user {user_id}: {e}")
    
    # ============== USER ACCESS METHODS ==============
    
    def is_user_allowed(self, username: str) -> bool:
        """Check if user is in whitelist and has access by username."""
        if not username:
            return False
        
        query = f'SELECT has_access FROM allowed_users WHERE username = {self._get_placeholder(1)}'
        result = self.fetch_val(query, (username,))
        return bool(result)
    
    def is_user_allowed_by_id(self, user_id: int) -> bool:
        """Check if user is allowed by user_id and has access."""
        logger.debug(f"🔍 UserRepository.is_user_allowed_by_id: проверяем user_id={user_id}")
        query = f'SELECT has_access FROM allowed_users WHERE user_id = {self._get_placeholder(1)}'
        result = self.fetch_val(query, (user_id,))
        allowed_result = bool(result)
        logger.debug(f"📊 UserRepository.is_user_allowed_by_id: query result={result}, allowed={allowed_result}")
        return allowed_result
    
    def has_user_access(self, user_id: int) -> bool:
        """Check if user has access to the system."""
        logger.debug(f"🔍 UserRepository.has_user_access: проверяем user_id={user_id}")
        result = self.is_user_allowed_by_id(user_id)
        logger.debug(f"📊 UserRepository.has_user_access: result={result}")
        return result
    
    def set_user_access(self, user_id: int, has_access: bool) -> bool:
        """Set user access status (enable/disable user)."""
        try:
            query = f'''
                UPDATE allowed_users 
                SET has_access = {self._get_placeholder(1)}, 
                    last_activity = {self._get_current_timestamp()} 
                WHERE user_id = {self._get_placeholder(2)}
            '''
            self.execute_query(query, (self._get_boolean_value(has_access), user_id))
            return True
        except Exception as e:
            logger.error(f"Error setting user access: {e}")
            return False
    
    # ============== USER REGISTRATION METHODS ==============
    
    def add_allowed_user(self, username: str, full_name: str, grade: int, added_by: int, 
                        user_id: int = None, language: str = "ru") -> bool:
        """Add user to whitelist with language support."""
        try:
            if not user_id:
                return False
            
            query = f'''
                INSERT INTO allowed_users (username, full_name, grade, user_id, added_by, language, is_active)
                VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_placeholder(3)}, 
                        {self._get_placeholder(4)}, {self._get_placeholder(5)}, {self._get_placeholder(6)}, 
                        {self._get_placeholder(7)})
            '''
            params = (username, full_name, grade, user_id, added_by, language, self._get_boolean_value(False))
            self.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error adding allowed user: {e}")
            return False
    
    def add_allowed_user_by_id(self, user_id: int, full_name: str, grade: int, added_by: int, 
                              username: str = None, language: str = "ru") -> bool:
        """Add user to whitelist by user_id."""
        try:
            if not user_id:
                return False
            
            query = f'''
                INSERT INTO allowed_users (user_id, username, full_name, grade, added_by, language, is_active)
                VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_placeholder(3)}, 
                        {self._get_placeholder(4)}, {self._get_placeholder(5)}, {self._get_placeholder(6)}, 
                        {self._get_placeholder(7)})
            '''
            params = (user_id, username, full_name, grade, added_by, language, self._get_boolean_value(False))
            self.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error adding allowed user by ID: {e}")
            return False
    
    def remove_allowed_user(self, username: str) -> bool:
        """Remove user from whitelist by username."""
        try:
            query = f'DELETE FROM allowed_users WHERE username = {self._get_placeholder(1)}'
            self.execute_query(query, (username,))
            return True
        except Exception as e:
            logger.error(f"Error removing allowed user: {e}")
            return False
    
    def remove_allowed_user_by_id(self, user_id: int) -> bool:
        """Remove user from whitelist by user_id."""
        try:
            query = f'DELETE FROM allowed_users WHERE user_id = {self._get_placeholder(1)}'
            self.execute_query(query, (user_id,))
            return True
        except Exception as e:
            logger.error(f"Error removing allowed user by ID: {e}")
            return False
    
    # ============== USER LISTING METHODS ==============
    
    def get_all_allowed_users(self) -> List[Dict]:
        """Get all allowed users."""
        query = '''
            SELECT user_id, username, full_name, grade, is_active, added_at
            FROM allowed_users
            ORDER BY added_at DESC
        '''
        return self.fetch_all(query)
    
    def get_allowed_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get allowed user information by ID."""
        query = f'''
            SELECT user_id, username, full_name, grade, is_active, added_at, added_by, language
            FROM allowed_users
            WHERE user_id = {self._get_placeholder(1)}
        '''
        return self.fetch_one(query, (user_id,))
    
    # ============== USER DATA CLEANUP METHODS ==============
    
    def delete_all_user_data(self, user_id: int) -> bool:
        """Delete all data associated with a user."""
        try:
            # Delete test results
            query1 = f'DELETE FROM test_results WHERE user_id = {self._get_placeholder(1)}'
            self.execute_query(query1, (user_id,))
            
            # Delete user errors
            query2 = f'DELETE FROM user_errors WHERE user_id = {self._get_placeholder(1)}'
            self.execute_query(query2, (user_id,))
            
            # Reset user state
            query3 = f'''
                UPDATE allowed_users 
                SET is_active = {self._get_placeholder(1)}, 
                    current_topic = NULL, 
                    last_activity = {self._get_current_timestamp()} 
                WHERE user_id = {self._get_placeholder(2)}
            '''
            self.execute_query(query3, (self._get_boolean_value(False), user_id))
            
            return True
        except Exception as e:
            logger.error(f"Error deleting user data: {e}")
            return False
    
    def clear_user_activity(self, user_id: int) -> None:
        """Clear user activity and set as inactive."""
        query = f'''
            UPDATE allowed_users 
            SET is_active = {self._get_placeholder(1)}, 
                current_topic = NULL, 
                last_activity = {self._get_current_timestamp()} 
            WHERE user_id = {self._get_placeholder(2)}
        '''
        self.execute_query(query, (self._get_boolean_value(False), user_id))
    
    def set_all_users_inactive(self):
        """Set all users as inactive."""
        query = f'UPDATE allowed_users SET is_active = {self._get_placeholder(1)}, current_topic = NULL'
        self.execute_query(query, (self._get_boolean_value(False),))
    
    # ============== UTILITY METHODS ==============
    
    def register_user(self, user_id: int, username: str) -> None:
        """Register user if they don't exist in allowed_users."""
        # Check if user exists
        existing = self.get_allowed_user_by_id(user_id)
        if existing:
            return
        
        # Register only if needed (backwards compatibility)
        query = f'''
            INSERT INTO allowed_users (user_id, username, last_activity)
            VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_current_timestamp()})
            ON CONFLICT (user_id) DO NOTHING
        ''' if self.is_postgresql else f'''
            INSERT OR IGNORE INTO allowed_users (user_id, username, last_activity)
            VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_current_timestamp()})
        '''
        self.execute_query(query, (user_id, username))
    
    def auto_update_username_from_telegram(self, user_id: int, username: str) -> bool:
        """Automatically update username from Telegram data."""
        try:
            query = f'''
                UPDATE allowed_users 
                SET username = {self._get_placeholder(1)}, 
                    last_activity = {self._get_current_timestamp()}
                WHERE user_id = {self._get_placeholder(2)} AND (username IS NULL OR username != {self._get_placeholder(3)})
            '''
            self.execute_query(query, (username, user_id, username))
            return True
        except Exception as e:
            logger.error(f"Error auto-updating username: {e}")
            return False 