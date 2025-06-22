"""
Synchronous User Repository for Neon PostgreSQL

Handles user-related database operations synchronously.
"""

import logging
from typing import Optional, List, Dict, Any
from ..sync_base_repository import SyncBaseRepository

logger = logging.getLogger(__name__)

class SyncUserRepository(SyncBaseRepository):
    """Synchronous repository for user operations"""
    
    def has_user_access(self, user_id: int) -> bool:
        """Check if user has access (sync)"""
        try:
            query = "SELECT 1 FROM allowed_users WHERE user_id = %s AND has_access = %s"
            result = self.fetch_val(query, (user_id, True))
            return result is not None
            
        except Exception as e:
            logger.error(f"❌ Error checking user access for {user_id}: {e}")
            return False
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID (sync)"""
        logger.info(f"🔍 Getting user by ID: {user_id}")
        
        try:
            query = """
                SELECT user_id, username, full_name, grade, language, 
                       is_active, has_access, current_topic, last_activity,
                       added_by, added_at, updated_at
                FROM allowed_users 
                WHERE user_id = %s
            """
            result = self.fetch_one(query, (user_id,))
            logger.info(f"📊 User found: {result is not None}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting user {user_id}: {e}")
            return None
    
    def add_user(self, user_id: int, username: str = None, full_name: str = None,
                 grade: int = None, language: str = 'ru', added_by: int = None) -> bool:
        """Add new user (sync)"""
        logger.info(f"➕ Adding user: user_id={user_id}, username={username}")
        
        try:
            query = """
                INSERT INTO allowed_users (user_id, username, full_name, grade, language, added_by, has_access)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    grade = EXCLUDED.grade,
                    language = EXCLUDED.language,
                    has_access = EXCLUDED.has_access,
                    updated_at = CURRENT_TIMESTAMP
            """
            self.execute_query(query, (user_id, username, full_name, grade, language, added_by, True))
            logger.info(f"✅ User {user_id} added/updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding user {user_id}: {e}")
            return False
    
    def remove_user_access(self, user_id: int) -> bool:
        """Remove user access (sync)"""
        logger.info(f"🔒 Removing access for user: {user_id}")
        
        try:
            query = "UPDATE allowed_users SET has_access = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s"
            self.execute_query(query, (False, user_id))
            logger.info(f"✅ Access removed for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing access for user {user_id}: {e}")
            return False
    
    def restore_user_access(self, user_id: int) -> bool:
        """Restore user access (sync)"""
        logger.info(f"🔓 Restoring access for user: {user_id}")
        
        try:
            query = "UPDATE allowed_users SET has_access = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s"
            self.execute_query(query, (True, user_id))
            logger.info(f"✅ Access restored for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error restoring access for user {user_id}: {e}")
            return False
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (sync)"""
        logger.info("📋 Getting all users")
        
        try:
            query = """
                SELECT user_id, username, full_name, grade, language, 
                       is_active, has_access, current_topic, last_activity,
                       added_by, added_at, updated_at
                FROM allowed_users 
                ORDER BY added_at DESC
            """
            result = self.fetch_all(query)
            logger.info(f"📊 Found {len(result)} users")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting all users: {e}")
            return []
    
    def update_user_activity(self, user_id: int, current_topic: str = None) -> bool:
        """Update user activity (sync)"""
        logger.debug(f"📈 Updating activity for user: {user_id}")
        
        try:
            if current_topic:
                query = """
                    UPDATE allowed_users 
                    SET last_activity = CURRENT_TIMESTAMP, current_topic = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """
                self.execute_query(query, (current_topic, user_id))
            else:
                query = """
                    UPDATE allowed_users 
                    SET last_activity = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """
                self.execute_query(query, (user_id,))
            
            logger.debug(f"✅ Activity updated for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating activity for user {user_id}: {e}")
            return False 