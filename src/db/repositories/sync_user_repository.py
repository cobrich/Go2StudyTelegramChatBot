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
        """Add new user (sync) - PRIMARY method for adding students via Telegram data
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            full_name: Student's full name (ФИО)
            grade: Student's grade (5 or 6)
            language: Student's language preference
            added_by: Admin ID who added the student
        """
        logger.info(f"➕ Adding student via Telegram: user_id={user_id}, username={username}")
        
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
            logger.info(f"✅ Student {user_id} added/updated successfully via Telegram data")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding student {user_id}: {e}")
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
                    SET last_activity = CURRENT_TIMESTAMP, current_topic = %s, 
                        is_active = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """
                self.execute_query(query, (current_topic, True, user_id))
            else:
                query = """
                    UPDATE allowed_users 
                    SET last_activity = CURRENT_TIMESTAMP, current_topic = NULL,
                        is_active = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """
                self.execute_query(query, (False, user_id))
            
            logger.debug(f"✅ Activity updated for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating activity for user {user_id}: {e}")
            return False
    
    # Additional methods from main branch
    def is_user_allowed(self, username: str) -> bool:
        """Check if user is in whitelist by username"""
        try:
            query = "SELECT 1 FROM allowed_users WHERE username = %s AND has_access = %s"
            result = self.fetch_val(query, (username, True))
            return result is not None
            
        except Exception as e:
            logger.error(f"Error checking if user allowed: {username}: {e}")
            return False
    
    def add_allowed_user(self, username: str, full_name: str, grade: int, added_by: int,
                        user_id: int = None, language: str = "ru") -> bool:
        """Add user to whitelist - DEPRECATED: Use add_user() with Telegram data instead
        
        ⚠️ DEPRECATED: Students should be added only via Telegram data using add_user()
        This method is kept for backward compatibility but should not be used for new students.
        """
        logger.warning(f"⚠️ DEPRECATED: add_allowed_user() called for {username}. Use add_user() with Telegram data instead.")
        
        try:
            query = """
                INSERT INTO allowed_users (user_id, username, full_name, grade, language, added_by, has_access)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.execute_query(query, (user_id, username, full_name, grade, language, added_by, True))
            logger.info(f"✅ Added allowed user: {username} (DEPRECATED method)")
            return True
            
        except Exception as e:
            logger.error(f"Error adding allowed user {username}: {e}")
            return False
    
    def remove_allowed_user(self, username: str) -> bool:
        """Remove user from whitelist by username"""
        try:
            query = "UPDATE allowed_users SET has_access = %s, updated_at = CURRENT_TIMESTAMP WHERE username = %s"
            self.execute_query(query, (False, username))
            logger.info(f"✅ Removed allowed user: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing allowed user {username}: {e}")
            return False
    
    def update_allowed_user(self, username: str, full_name: str = None, grade: int = None,
                           is_active: bool = None) -> bool:
        """Update allowed user info by username"""
        try:
            updates = []
            params = []
            
            if full_name is not None:
                updates.append("full_name = %s")
                params.append(full_name)
            
            if grade is not None:
                updates.append("grade = %s")
                params.append(grade)
            
            if is_active is not None:
                updates.append("is_active = %s")
                params.append(is_active)
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(username)
            
            query = f"UPDATE allowed_users SET {', '.join(updates)} WHERE username = %s"
            self.execute_query(query, params)
            logger.info(f"✅ Updated allowed user: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating allowed user {username}: {e}")
            return False
    
    def update_allowed_user_by_id(self, user_id: int, full_name: str = None, grade: int = None,
                                 has_access: bool = None) -> bool:
        """Update allowed user info by user_id"""
        try:
            updates = []
            params = []
            
            if full_name is not None:
                updates.append("full_name = %s")
                params.append(full_name)
            
            if grade is not None:
                updates.append("grade = %s")
                params.append(grade)
            
            if has_access is not None:
                updates.append("has_access = %s")
                params.append(has_access)
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)
            
            query = f"UPDATE allowed_users SET {', '.join(updates)} WHERE user_id = %s"
            self.execute_query(query, params)
            logger.info(f"✅ Updated allowed user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating allowed user {user_id}: {e}")
            return False
    
    def get_allowed_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get allowed user by ID"""
        return self.get_user_by_id(user_id)
    
    def set_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        """Set user information (create or update) - DEPRECATED for new students
        
        ⚠️ DEPRECATED: New students should be added via add_user() with complete Telegram data.
        This method is kept for updating existing student information only.
        """
        logger.warning(f"⚠️ DEPRECATED: set_user_info() called for {user_id}. Use add_user() for new students.")
        
        try:
            query = """
                INSERT INTO allowed_users (user_id, full_name, grade, has_access)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    grade = EXCLUDED.grade,
                    updated_at = CURRENT_TIMESTAMP
            """
            self.execute_query(query, (user_id, full_name, grade, True))
            logger.info(f"✅ Set user info: {user_id} (DEPRECATED method)")
            
        except Exception as e:
            logger.error(f"Error setting user info {user_id}: {e}")
    
    def set_user_info_with_language(self, user_id: int, full_name: str, grade: int, language: str) -> None:
        """Set user information with language (create or update)"""
        try:
            query = """
                INSERT INTO allowed_users (user_id, full_name, grade, language, has_access)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    grade = EXCLUDED.grade,
                    language = EXCLUDED.language,
                    updated_at = CURRENT_TIMESTAMP
            """
            self.execute_query(query, (user_id, full_name, grade, language, True))
            logger.info(f"✅ Set user info with language: {user_id}")
            
        except Exception as e:
            logger.error(f"Error setting user info with language {user_id}: {e}")
    
    def update_user_language(self, user_id: int, language: str) -> None:
        """Update user's language"""
        try:
            query = """
                UPDATE allowed_users 
                SET language = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """
            self.execute_query(query, (language, user_id))
            logger.info(f"✅ Updated user language: {user_id} -> {language}")
            
        except Exception as e:
            logger.error(f"Error updating user language {user_id}: {e}")
    
    def update_user_info(self, user_id: int, full_name: str, grade: int) -> None:
        """Update user information"""
        try:
            query = """
                UPDATE allowed_users 
                SET full_name = %s, grade = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """
            self.execute_query(query, (full_name, grade, user_id))
            logger.info(f"✅ Updated user info: {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating user info {user_id}: {e}")
    
    def set_all_users_inactive(self) -> None:
        """Set all users as inactive"""
        try:
            query = """
                UPDATE allowed_users 
                SET is_active = %s, current_topic = NULL, updated_at = CURRENT_TIMESTAMP
            """
            self.execute_query(query, (False,))
            logger.info("✅ Set all users inactive")
            
        except Exception as e:
            logger.error(f"Error setting all users inactive: {e}")
    
    def clear_user_activity(self, user_id: int) -> None:
        """Clear user activity and set as inactive"""
        self.update_user_activity(user_id, None)
    
    def register_user(self, user_id: int, username: str) -> None:
        """Register user if they don't exist - DEPRECATED for students
        
        ⚠️ DEPRECATED: Students should be properly added via add_user() with complete information.
        This method creates incomplete user records and should be avoided.
        """
        logger.warning(f"⚠️ DEPRECATED: register_user() called for {user_id}. Use add_user() with complete data.")
        
        try:
            # Check if user exists
            existing_user = self.get_user_by_id(user_id)
            
            if not existing_user:
                # Add user with minimal info - NOT RECOMMENDED
                query = """
                    INSERT INTO allowed_users (user_id, username, has_access)
                    VALUES (%s, %s, %s)
                """
                self.execute_query(query, (user_id, username, False))
                logger.info(f"✅ Registered new user: {user_id} (INCOMPLETE - needs full info)")
            else:
                logger.info(f"User {user_id} already exists")
                
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
    
    def delete_all_user_data(self, user_id: int) -> bool:
        """Delete all data associated with a user"""
        try:
            # This would need to be coordinated with other repositories
            # For now, just remove from allowed_users
            query = "DELETE FROM allowed_users WHERE user_id = %s"
            self.execute_query(query, (user_id,))
            logger.info(f"✅ Deleted all user data: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user data {user_id}: {e}")
            return False
    
    def sync_user_with_whitelist(self, user_id: int, username: str) -> bool:
        """Sync user with whitelist"""
        try:
            # Check if user exists in whitelist by username
            query = "SELECT user_id FROM allowed_users WHERE username = %s"
            result = self.fetch_one(query, (username,))
            
            if result and result['user_id'] is None:
                # Update whitelist entry with user_id
                query = """
                    UPDATE allowed_users 
                    SET user_id = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE username = %s
                """
                self.execute_query(query, (user_id, username))
                logger.info(f"✅ Synced user with whitelist: {user_id}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error syncing user with whitelist {user_id}: {e}")
            return False
    
    def get_user_historical_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user historical statistics"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return {}
            
            return {
                'user_id': user_id,
                'username': user.get('username'),
                'full_name': user.get('full_name'),
                'grade': user.get('grade'),
                'language': user.get('language'),
                'registration_date': user.get('added_at'),
                'last_activity': user.get('last_activity'),
                'is_active': user.get('is_active'),
                'has_access': user.get('has_access')
            }
            
        except Exception as e:
            logger.error(f"Error getting user historical stats {user_id}: {e}")
            return {}
    
    def get_all_users_with_history(self) -> List[Dict[str, Any]]:
        """Get all users with history - ONLY students, NOT admins"""
        try:
            query = """
                SELECT u.user_id, u.username, u.full_name, u.grade, u.language,
                       u.is_active, u.has_access, u.added_at, u.last_activity,
                       COUNT(tr.id) as test_count,
                       AVG(tr.percentage) as avg_score
                FROM allowed_users u
                LEFT JOIN test_results tr ON u.user_id = tr.user_id
                WHERE u.user_id NOT IN (SELECT user_id FROM admins)
                GROUP BY u.user_id, u.username, u.full_name, u.grade, u.language,
                         u.is_active, u.has_access, u.added_at, u.last_activity
                ORDER BY u.added_at DESC
            """
            
            results = self.fetch_all(query)
            
            return [
                {
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'full_name': row['full_name'],
                    'grade': row['grade'],
                    'language': row['language'],
                    'is_active': row['is_active'],
                    'has_access': row['has_access'],
                    'registration_date': row['added_at'],
                    'last_activity': row['last_activity'],
                    'test_count': row['test_count'] or 0,
                    'avg_score': round(row['avg_score'] or 0, 2)
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting all users with history: {e}")
            return []
    
    def get_all_students_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all students"""
        return self.get_all_users_with_history()
    
    def get_class_statistics(self, grade: int = None) -> Dict[str, Any]:
        """Get class statistics - ONLY for students, NOT admins"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_students,
                    COUNT(CASE WHEN has_access = true THEN 1 END) as active_students,
                    COUNT(CASE WHEN is_active = true THEN 1 END) as currently_active,
                    AVG(CASE WHEN grade IS NOT NULL THEN grade END) as avg_grade
                FROM allowed_users
                WHERE user_id NOT IN (SELECT user_id FROM admins)
            """
            params = []
            
            if grade is not None:
                query += " AND grade = %s"
                params.append(grade)
            
            result = self.fetch_one(query, params)
            
            if result:
                return {
                    'total_students': result['total_students'],
                    'active_students': result['active_students'],
                    'currently_active': result['currently_active'],
                    'average_grade': round(result['avg_grade'] or 0, 1),
                    'filter_grade': grade
                }
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting class statistics: {e}")
            return {}
    
    def get_detailed_class_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics grouped by class - ONLY for students, NOT admins"""
        try:
            # Get statistics by class - EXCLUDE ADMINS
            query = """
                SELECT 
                    u.grade,
                    COUNT(*) as students_count,
                    COUNT(CASE WHEN u.has_access = true THEN 1 END) as active_students,
                    COUNT(CASE WHEN u.is_active = true THEN 1 END) as currently_active,
                    COUNT(tr.id) as total_tests,
                    AVG(tr.percentage) as avg_score
                FROM allowed_users u
                LEFT JOIN test_results tr ON u.user_id = tr.user_id
                WHERE u.grade IS NOT NULL 
                AND u.user_id NOT IN (SELECT user_id FROM admins)
                GROUP BY u.grade
                ORDER BY u.grade
            """
            
            results = self.fetch_all(query)
            
            class_stats = []
            for row in results:
                activity_rate = round((row['active_students'] / row['students_count'] * 100) if row['students_count'] > 0 else 0, 1)
                class_stats.append({
                    'grade': row['grade'],
                    'students_count': row['students_count'],
                    'active_students': row['active_students'],
                    'currently_active': row['currently_active'],
                    'activity_rate': activity_rate,
                    'total_tests': row['total_tests'] or 0,
                    'avg_score': round(row['avg_score'] or 0, 1)
                })
            
            return {
                'class_stats': class_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting detailed class statistics: {e}")
            return {'class_stats': []}
    
    def find_student_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Find student by identifier (username, full_name, or user_id)"""
        try:
            # Try to find by user_id if identifier is numeric
            if identifier.isdigit():
                user = self.get_user_by_id(int(identifier))
                if user:
                    return user
            
            # Try to find by username
            query = """
                SELECT user_id, username, full_name, grade, language, 
                       is_active, has_access, current_topic, last_activity,
                       added_by, added_at, updated_at
                FROM allowed_users 
                WHERE username = %s OR full_name ILIKE %s
                LIMIT 1
            """
            result = self.fetch_one(query, (identifier, f"%{identifier}%"))
            return result
            
        except Exception as e:
            logger.error(f"Error finding student by identifier {identifier}: {e}")
            return None
    
    def get_comprehensive_user_access_check(self, user_id: int, username: str = None) -> Dict[str, Any]:
        """Comprehensive user access check"""
        try:
            user = self.get_user_by_id(user_id)
            
            return {
                'user_id': user_id,
                'username': username,
                'exists_in_db': user is not None,
                'has_access': user.get('has_access', False) if user else False,
                'is_active': user.get('is_active', False) if user else False,
                'full_name': user.get('full_name') if user else None,
                'grade': user.get('grade') if user else None,
                'language': user.get('language', 'ru') if user else 'ru',
                'last_activity': user.get('last_activity') if user else None,
                'registration_date': user.get('added_at') if user else None
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive user access check {user_id}: {e}")
            return {
                'user_id': user_id,
                'username': username,
                'exists_in_db': False,
                'has_access': False,
                'is_active': False,
                'error': str(e)
            }
    
    def clear_user_data_on_language_change(self, user_id: int) -> None:
        """Clear user data on language change"""
        try:
            # Clear current activity
            query = """
                UPDATE allowed_users 
                SET current_topic = NULL, is_active = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """
            self.execute_query(query, (False, user_id))
            logger.info(f"✅ Cleared user data on language change: {user_id}")
            
        except Exception as e:
            logger.error(f"Error clearing user data on language change {user_id}: {e}") 