"""
Admin Repository

Handles all admin-related database operations.
"""

import logging
from typing import Dict, List, Optional
from ..base_repository import BaseRepository
import inspect

logger = logging.getLogger(__name__)

class AdminRepository(BaseRepository):
    """Repository for admin operations"""
    
    def __init__(self):
        super().__init__()
    
    def _get_fallback_value(self):
        """Get fallback value when database is unreachable"""
        # Для админских операций возвращаем безопасные значения
        # Анализируем стек вызовов, чтобы понять, что именно запрашивается
        frame = inspect.currentframe()
        try:
            # Получаем имя вызывающего метода
            caller_name = frame.f_back.f_back.f_code.co_name if frame.f_back and frame.f_back.f_back else ""
            
            # Возвращаем подходящие fallback значения в зависимости от метода
            if 'get_all_admins' in caller_name or 'search_admins' in caller_name:
                return []  # Пустой список для методов, возвращающих списки
            elif 'get_admin_activity_stats' in caller_name:
                return {
                    'total_admins': 0,
                    'super_admins': 0,
                    'regular_admins': 0,
                    'recent_additions': 0
                }
            elif 'is_' in caller_name:  # is_admin, is_super_admin
                return False  # Безопасно - нет доступа при недоступности БД
            else:
                return None  # Для остальных случаев
        finally:
            del frame
    
    # ============== ADMIN CHECK METHODS ==============
    
    def is_super_admin(self, user_id: int) -> bool:
        """Check if user is super admin."""
        query = f'SELECT is_super_admin FROM admins WHERE user_id = {self._get_placeholder(1)}'
        result = self.fetch_val(query, (user_id,))
        return bool(result)
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin (regular or super)."""
        query = f'SELECT 1 FROM admins WHERE user_id = {self._get_placeholder(1)}'
        result = self.fetch_val(query, (user_id,))
        return result is not None
    
    # ============== ADMIN MANAGEMENT METHODS ==============
    
    def add_admin(self, user_id: int, username: str, full_name: str, is_super: bool = False, added_by: int = None) -> bool:
        """Add new admin."""
        try:
            # PostgreSQL syntax with ON CONFLICT
            query = f'''
                INSERT INTO admins (user_id, username, full_name, is_super_admin, created_by)
                VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_placeholder(3)}, 
                        {self._get_placeholder(4)}, {self._get_placeholder(5)})
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    is_super_admin = EXCLUDED.is_super_admin
            '''
            params = (user_id, username, full_name, is_super, added_by)
            self.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error adding admin: {e}")
            return False
    
    def remove_admin(self, user_id: int) -> bool:
        """Remove admin (only super admin can do this)."""
        try:
            # Only remove non-super admins
            query = f'''
                DELETE FROM admins 
                WHERE user_id = {self._get_placeholder(1)} AND is_super_admin = {self._get_placeholder(2)}
            '''
            params = (user_id, False)
            self.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error removing admin: {e}")
            return False
    
    def get_all_admins(self) -> List[Dict]:
        """Get list of all admins."""
        query = '''
            SELECT user_id, username, full_name, is_super_admin, created_at
            FROM admins
            ORDER BY is_super_admin DESC, created_at ASC
        '''
        admins = self.fetch_all(query)
        
        # Проверяем, что admins это список, а не fallback значение
        if not isinstance(admins, list):
            return []
        
        # Convert boolean values for consistency
        for admin in admins:
            admin['is_super'] = bool(admin['is_super_admin'])
            admin['name'] = admin['full_name']
            admin['added_at'] = admin['created_at']
        
        return admins
    
    def get_admin_info(self, user_id: int) -> Optional[Dict]:
        """Get admin information by user_id."""
        query = f'''
            SELECT user_id, username, full_name, is_super_admin, created_at, created_by
            FROM admins 
            WHERE user_id = {self._get_placeholder(1)}
        '''
        admin = self.fetch_one(query, (user_id,))
        
        if admin:
            admin['is_super_admin'] = bool(admin['is_super_admin'])
        
        return admin
    
    def update_admin_info(self, user_id: int, full_name: str) -> bool:
        """Update admin's full name."""
        try:
            query = f'''
                UPDATE admins 
                SET full_name = {self._get_placeholder(1)} 
                WHERE user_id = {self._get_placeholder(2)}
            '''
            self.execute_query(query, (full_name, user_id))
            return True
        except Exception as e:
            logger.error(f"Error updating admin info: {e}")
            return False
    
    def update_admin_username(self, user_id: int, username: str) -> bool:
        """Update admin's username."""
        try:
            query = f'''
                UPDATE admins 
                SET username = {self._get_placeholder(1)} 
                WHERE user_id = {self._get_placeholder(2)}
            '''
            self.execute_query(query, (username, user_id))
            return True
        except Exception as e:
            logger.error(f"Error updating admin username: {e}")
            return False
    
    # ============== ADMIN STATISTICS METHODS ==============
    
    def get_admin_activity_stats(self) -> Dict:
        """Get admin activity statistics."""
        try:
            # Count total admins
            total_query = 'SELECT COUNT(*) FROM admins'
            total_admins = self.fetch_val(total_query)
            
            # Count super admins
            super_query = f'SELECT COUNT(*) FROM admins WHERE is_super_admin = {self._get_placeholder(1)}'
            super_admins = self.fetch_val(super_query, (True,))
            
            # Get recent admin additions (PostgreSQL syntax)
            recent_query = '''
                SELECT COUNT(*) FROM admins 
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            '''
            recent_additions = self.fetch_val(recent_query)
            
            return {
                'total_admins': total_admins or 0,
                'super_admins': super_admins or 0,
                'regular_admins': (total_admins or 0) - (super_admins or 0),
                'recent_additions': recent_additions or 0
            }
        except Exception as e:
            logger.error(f"Error getting admin stats: {e}")
            return {
                'total_admins': 0,
                'super_admins': 0,
                'regular_admins': 0,
                'recent_additions': 0
            }
    
    def get_admin_creation_history(self, limit: int = 10) -> List[Dict]:
        """Get recent admin creation history."""
        query = f'''
            SELECT a1.user_id, a1.username, a1.full_name, a1.is_super_admin, a1.created_at,
                   a2.username as created_by_username, a2.full_name as created_by_name
            FROM admins a1
            LEFT JOIN admins a2 ON a1.created_by = a2.user_id
            ORDER BY a1.created_at DESC
            LIMIT {self._get_placeholder(1)}
        '''
        
        history = self.fetch_all(query, (limit,))
        
        # Format the results
        for record in history:
            record['is_super'] = bool(record['is_super_admin'])
            record['created_by_display'] = record['created_by_name'] or record['created_by_username'] or 'System'
        
        return history
    
    # ============== ADMIN VALIDATION METHODS ==============
    
    def validate_admin_permissions(self, admin_user_id: int, target_user_id: int) -> Dict[str, bool]:
        """Validate admin permissions for operations on target user."""
        admin_info = self.get_admin_info(admin_user_id)
        target_info = self.get_admin_info(target_user_id)
        
        if not admin_info:
            return {
                'can_modify': False,
                'can_delete': False,
                'reason': 'Admin not found'
            }
        
        is_super_admin = admin_info['is_super_admin']
        target_is_admin = target_info is not None
        target_is_super = target_info['is_super_admin'] if target_info else False
        
        # Super admins can modify anyone except other super admins
        if is_super_admin:
            can_modify = not target_is_super or admin_user_id == target_user_id
            can_delete = not target_is_super
        else:
            # Regular admins can only modify themselves
            can_modify = admin_user_id == target_user_id and not target_is_super
            can_delete = False
        
        return {
            'can_modify': can_modify,
            'can_delete': can_delete,
            'target_is_admin': target_is_admin,
            'target_is_super': target_is_super,
            'admin_is_super': is_super_admin
        }
    
    # ============== ADMIN SEARCH METHODS ==============
    
    def find_admin_by_username(self, username: str) -> Optional[Dict]:
        """Find admin by username."""
        query = f'''
            SELECT user_id, username, full_name, is_super_admin, created_at
            FROM admins
            WHERE username = {self._get_placeholder(1)} OR username = {self._get_placeholder(2)}
        '''
        admin = self.fetch_one(query, (username, username.lstrip('@')))
        
        if admin:
            admin['is_super_admin'] = bool(admin['is_super_admin'])
        
        return admin
    
    def search_admins(self, search_term: str) -> List[Dict]:
        """Search admins by username or full name."""
        search_pattern = f'%{search_term}%'
        
        # PostgreSQL syntax with ILIKE
        query = f'''
            SELECT user_id, username, full_name, is_super_admin, created_at
            FROM admins
            WHERE username ILIKE {self._get_placeholder(1)} OR full_name ILIKE {self._get_placeholder(2)}
            ORDER BY is_super_admin DESC, created_at ASC
        '''
        
        admins = self.fetch_all(query, (search_pattern, search_pattern))
        
        # Convert boolean values
        for admin in admins:
            admin['is_super'] = bool(admin['is_super_admin'])
        
        return admins 