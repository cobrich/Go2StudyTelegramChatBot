"""
Synchronous Admin Repository for Neon PostgreSQL

Handles admin-related database operations synchronously.
"""

import logging
from typing import Optional, List, Dict, Any
from ..sync_base_repository import SyncBaseRepository

logger = logging.getLogger(__name__)

class SyncAdminRepository(SyncBaseRepository):
    """Synchronous repository for admin operations"""
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin (sync)"""
        try:
            query = "SELECT 1 FROM admins WHERE user_id = %s"
            result = self.fetch_val(query, (user_id,))
            logger.info(f"[DEBUG is_admin] user_id={user_id}, result={result}")
            return result is not None
            
        except Exception as e:
            logger.error(f"❌ Error checking admin status for {user_id}: {e}")
            return False
    
    def get_admin_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get admin by user ID (sync)"""
        logger.info(f"🔍 Getting admin by ID: {user_id}")
        
        try:
            query = """
                SELECT user_id, username, full_name, is_super_admin, 
                       created_by, created_at, updated_at
                FROM admins 
                WHERE user_id = %s
            """
            result = self.fetch_one(query, (user_id,))
            logger.info(f"📊 Admin found: {result is not None}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting admin {user_id}: {e}")
            return None
    
    def add_admin(self, user_id: int, username: str = None, full_name: str = None, 
                  is_super_admin: bool = False, created_by: int = None) -> bool:
        """Add new admin (sync)"""
        logger.info(f"➕ Adding admin: user_id={user_id}, username={username}")
        
        try:
            query = """
                INSERT INTO admins (user_id, username, full_name, is_super_admin, created_by)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    is_super_admin = EXCLUDED.is_super_admin,
                    updated_at = CURRENT_TIMESTAMP
            """
            self.execute_query(query, (user_id, username, full_name, is_super_admin, created_by))
            logger.info(f"✅ Admin {user_id} added/updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding admin {user_id}: {e}")
            return False
    
    def remove_admin(self, user_id: int) -> bool:
        """Remove admin (sync)"""
        logger.info(f"🗑️ Removing admin: user_id={user_id}")
        
        try:
            query = "DELETE FROM admins WHERE user_id = %s"
            self.execute_query(query, (user_id,))
            logger.info(f"✅ Admin {user_id} removed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing admin {user_id}: {e}")
            return False
    
    def get_all_admins(self) -> List[Dict[str, Any]]:
        """Get all admins (sync)"""
        logger.info("📋 Getting all admins")
        
        try:
            query = """
                SELECT user_id, username, full_name, is_super_admin, 
                       created_by, created_at, updated_at
                FROM admins 
                ORDER BY created_at DESC
            """
            result = self.fetch_all(query)
            logger.info(f"📊 Found {len(result)} admins")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting all admins: {e}")
            return []
    
    def is_super_admin(self, user_id: int) -> bool:
        """Check if user is super admin (sync)"""
        logger.info(f"🔍 Checking super admin status: user_id={user_id}")
        
        try:
            query = "SELECT is_super_admin FROM admins WHERE user_id = %s"
            result = self.fetch_val(query, (user_id,))
            
            is_super = bool(result) if result is not None else False
            logger.info(f"🎯 Super admin status for {user_id}: {is_super}")
            return is_super
            
        except Exception as e:
            logger.error(f"❌ Error checking super admin status for {user_id}: {e}")
            return False
    
    def update_admin_info(self, user_id: int, username: str = None, full_name: str = None) -> bool:
        """Update admin information (sync)"""
        logger.info(f"✏️ Updating admin info: user_id={user_id}")
        
        try:
            updates = []
            params = []
            
            if username is not None:
                updates.append("username = %s")
                params.append(username)
            
            if full_name is not None:
                updates.append("full_name = %s")
                params.append(full_name)
            
            if not updates:
                logger.warning("No updates provided")
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)
            
            query = f"UPDATE admins SET {', '.join(updates)} WHERE user_id = %s"
            self.execute_query(query, tuple(params))
            
            logger.info(f"✅ Admin {user_id} info updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating admin {user_id}: {e}")
            return False 