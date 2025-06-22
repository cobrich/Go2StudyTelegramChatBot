"""
Synchronous Topic Repository for Neon PostgreSQL

Handles topic-related database operations synchronously.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from ..sync_base_repository import SyncBaseRepository

logger = logging.getLogger(__name__)

class SyncTopicRepository(SyncBaseRepository):
    """Synchronous repository for topic operations"""
    
    def get_all_topics(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all subtopics with their main topic info"""
        try:
            query = """
                SELECT s.id, s.subtopic_name as name, m.topic_name as main_topic, 
                       s.is_active, s.created_at, m.language,
                       COUNT(q.id) as question_count
                FROM subtopics s
                JOIN main_topics m ON s.main_topic_id = m.id
                LEFT JOIN questions q ON s.id = q.topic_id
            """
            params = []
            
            if active_only:
                query += " WHERE s.is_active = %s AND m.is_active = %s"
                params = [True, True]
            
            query += """
                GROUP BY s.id, s.subtopic_name, m.topic_name, s.is_active, s.created_at, m.language
                ORDER BY m.topic_name, s.subtopic_name
            """
            
            return self.fetch_all(query, params)
            
        except Exception as e:
            logger.error(f"Error getting all topics: {e}")
            return []
    
    def add_topic(self, name: str, main_topic_id: int, created_by: int = None) -> bool:
        """Add new subtopic"""
        try:
            query = """
                INSERT INTO subtopics (subtopic_name, main_topic_id)
                VALUES (%s, %s)
            """
            self.execute_query(query, (name, main_topic_id))
            logger.info(f"✅ Added subtopic: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding topic {name}: {e}")
            return False
    
    def update_topic(self, topic_id: int, name: str = None, is_active: bool = None) -> bool:
        """Update subtopic"""
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append("subtopic_name = %s")
                params.append(name)
            
            if is_active is not None:
                updates.append("is_active = %s")
                params.append(is_active)
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(topic_id)
            
            query = f"UPDATE subtopics SET {', '.join(updates)} WHERE id = %s"
            self.execute_query(query, params)
            logger.info(f"✅ Updated topic {topic_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating topic {topic_id}: {e}")
            return False
    
    def delete_topic(self, topic_id: int) -> bool:
        """Soft delete topic"""
        return self.update_topic(topic_id, is_active=False)
    
    def delete_topic_permanently(self, topic_id: int) -> bool:
        """Permanently delete topic and all related data"""
        try:
            # This will cascade delete questions and related data
            query = "DELETE FROM subtopics WHERE id = %s"
            self.execute_query(query, (topic_id,))
            logger.info(f"✅ Permanently deleted topic {topic_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error permanently deleting topic {topic_id}: {e}")
            return False
    
    def get_subtopics_by_main_topic(self, main_topic_name: str) -> List[str]:
        """Get subtopics by main topic name"""
        try:
            query = """
                SELECT s.subtopic_name
                FROM subtopics s
                JOIN main_topics m ON s.main_topic_id = m.id
                WHERE m.topic_name = %s AND s.is_active = %s
                ORDER BY s.subtopic_name
            """
            results = self.fetch_all(query, (main_topic_name, True))
            return [row['subtopic_name'] for row in results]
            
        except Exception as e:
            logger.error(f"Error getting subtopics for {main_topic_name}: {e}")
            return []
    
    def toggle_topic_status(self, topic_id: int) -> bool:
        """Toggle topic active status"""
        try:
            # Get current status
            query = "SELECT is_active FROM subtopics WHERE id = %s"
            result = self.fetch_one(query, (topic_id,))
            
            if not result:
                return False
            
            new_status = not result['is_active']
            return self.update_topic(topic_id, is_active=new_status)
            
        except Exception as e:
            logger.error(f"Error toggling topic status {topic_id}: {e}")
            return False
    
    def update_topic_name(self, topic_id: int, new_name: str) -> bool:
        """Update topic name"""
        return self.update_topic(topic_id, name=new_name)
    
    def delete_topic_completely(self, topic_id: int) -> bool:
        """Delete topic completely"""
        return self.delete_topic_permanently(topic_id)
    
    def rename_topic_by_id(self, topic_id: int, new_name: str) -> bool:
        """Rename topic by ID"""
        return self.update_topic_name(topic_id, new_name)
    
    def rename_topic_by_name(self, old_name: str, new_name: str) -> bool:
        """Rename topic by name"""
        try:
            # Find topic ID by name
            query = "SELECT id FROM subtopics WHERE subtopic_name = %s"
            result = self.fetch_one(query, (old_name,))
            
            if not result:
                return False
            
            return self.rename_topic_by_id(result['id'], new_name)
            
        except Exception as e:
            logger.error(f"Error renaming topic {old_name} to {new_name}: {e}")
            return False
    
    def update_topic_section(self, topic_id: int, new_main_topic_id: int) -> bool:
        """Update topic's main topic"""
        try:
            query = """
                UPDATE subtopics 
                SET main_topic_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            self.execute_query(query, (new_main_topic_id, topic_id))
            logger.info(f"✅ Updated topic {topic_id} section")
            return True
            
        except Exception as e:
            logger.error(f"Error updating topic section {topic_id}: {e}")
            return False
    
    # Main Topics methods
    def get_main_topics_by_language(self, language: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get main topics by language"""
        try:
            query = """
                SELECT id, topic_name as name, language, is_active, created_at
                FROM main_topics
                WHERE language = %s
            """
            params = [language]
            
            if active_only:
                query += " AND is_active = %s"
                params.append(True)
            
            query += " ORDER BY topic_name"
            
            return self.fetch_all(query, params)
            
        except Exception as e:
            logger.error(f"Error getting main topics for language {language}: {e}")
            return []
    
    def add_main_topic_with_language(self, main_topic: str, language: str, 
                                    subtopics: List[str] = None, created_by: int = None) -> bool:
        """Add main topic with language"""
        try:
            # Add main topic
            query = """
                INSERT INTO main_topics (topic_name, language)
                VALUES (%s, %s)
                RETURNING id
            """
            result = self.fetch_one(query, (main_topic, language))
            
            if not result:
                return False
            
            main_topic_id = result['id']
            
            # Add subtopics if provided
            if subtopics:
                for subtopic in subtopics:
                    self.add_topic(subtopic, main_topic_id, created_by)
            
            logger.info(f"✅ Added main topic: {main_topic} ({language})")
            return True
            
        except Exception as e:
            logger.error(f"Error adding main topic {main_topic}: {e}")
            return False
    
    def toggle_main_topic_status(self, main_topic_name: str) -> bool:
        """Toggle main topic status"""
        try:
            # Get current status
            query = "SELECT is_active FROM main_topics WHERE topic_name = %s"
            result = self.fetch_one(query, (main_topic_name,))
            
            if not result:
                return False
            
            new_status = not result['is_active']
            
            query = """
                UPDATE main_topics 
                SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                WHERE topic_name = %s
            """
            self.execute_query(query, (new_status, main_topic_name))
            logger.info(f"✅ Toggled main topic {main_topic_name} to {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"Error toggling main topic status {main_topic_name}: {e}")
            return False
    
    def toggle_main_topic_status_by_language(self, main_topic_name: str, language: str) -> bool:
        """Toggle main topic status by name and language"""
        try:
            # Get current status for specific language
            query = "SELECT id, is_active FROM main_topics WHERE topic_name = %s AND language = %s"
            result = self.fetch_one(query, (main_topic_name, language))
            
            if not result:
                return False
            
            main_topic_id = result['id']
            new_status = not result['is_active']
            
            # Update main topic status
            query = """
                UPDATE main_topics 
                SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                WHERE topic_name = %s AND language = %s
            """
            self.execute_query(query, (new_status, main_topic_name, language))
            
            # Update all subtopics status to match main topic
            query = """
                UPDATE subtopics 
                SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                WHERE main_topic_id = %s
            """
            self.execute_query(query, (new_status, main_topic_id))
            
            logger.info(f"✅ Toggled main topic {main_topic_name} ({language}) and its subtopics to {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"Error toggling main topic status {main_topic_name} ({language}): {e}")
            return False
    
    def delete_main_topic_permanently(self, main_topic_name: str, language: str = None) -> bool:
        """Permanently delete main topic and all related data"""
        try:
            # Build query based on whether language is specified
            if language:
                query = "SELECT id FROM main_topics WHERE topic_name = %s AND language = %s"
                params = (main_topic_name, language)
            else:
                query = "SELECT id FROM main_topics WHERE topic_name = %s"
                params = (main_topic_name,)
            
            # Get main topic ID(s)
            results = self.fetch_all(query, params)
            
            if not results:
                logger.warning(f"Main topic '{main_topic_name}' not found for deletion")
                return False
            
            for result in results:
                main_topic_id = result['id']
                
                # Get all subtopic IDs for this main topic
                subtopic_query = "SELECT id FROM subtopics WHERE main_topic_id = %s"
                subtopic_results = self.fetch_all(subtopic_query, (main_topic_id,))
                
                # Delete all questions for each subtopic (CASCADE should handle this, but let's be explicit)
                for subtopic in subtopic_results:
                    subtopic_id = subtopic['id']
                    
                    # Delete user errors for questions in this subtopic first
                    delete_errors_query = """
                        DELETE FROM user_errors 
                        WHERE question_id IN (
                            SELECT id FROM questions WHERE topic_id = %s
                        )
                    """
                    self.execute_query(delete_errors_query, (subtopic_id,))
                    
                    # Delete test results for this subtopic
                    delete_results_query = "DELETE FROM test_results WHERE topic_id = %s"
                    self.execute_query(delete_results_query, (subtopic_id,))
                    
                    # Delete questions for this subtopic
                    delete_questions_query = "DELETE FROM questions WHERE topic_id = %s"
                    self.execute_query(delete_questions_query, (subtopic_id,))
                
                # Delete all subtopics for this main topic
                delete_subtopics_query = "DELETE FROM subtopics WHERE main_topic_id = %s"
                self.execute_query(delete_subtopics_query, (main_topic_id,))
                
                # Finally, delete the main topic
                delete_main_topic_query = "DELETE FROM main_topics WHERE id = %s"
                self.execute_query(delete_main_topic_query, (main_topic_id,))
                
                logger.info(f"✅ Permanently deleted main topic {main_topic_name} (ID: {main_topic_id}) and all related data")
            
            return True
            
        except Exception as e:
            logger.error(f"Error permanently deleting main topic {main_topic_name}: {e}")
            return False
    
    def get_base_topic_structure(self) -> Dict[str, List[str]]:
        """Get base topic structure (all languages)"""
        try:
            query = """
                SELECT m.topic_name, s.subtopic_name
                FROM main_topics m
                JOIN subtopics s ON m.id = s.main_topic_id
                WHERE m.is_active = %s AND s.is_active = %s
                ORDER BY m.topic_name, s.subtopic_name
            """
            
            results = self.fetch_all(query, (True, True))
            structure = {}
            
            for row in results:
                main_topic = row['topic_name']
                subtopic = row['subtopic_name']
                
                if main_topic not in structure:
                    structure[main_topic] = []
                structure[main_topic].append(subtopic)
            
            return structure
            
        except Exception as e:
            logger.error(f"Error getting base topic structure: {e}")
            return {}
    
    def get_base_topic_structure_by_language(self, language: str) -> Dict[str, List[str]]:
        """Get base topic structure by language"""
        try:
            query = """
                SELECT m.topic_name, s.subtopic_name
                FROM main_topics m
                JOIN subtopics s ON m.id = s.main_topic_id
                WHERE m.language = %s AND m.is_active = %s AND s.is_active = %s
                ORDER BY m.topic_name, s.subtopic_name
            """
            
            results = self.fetch_all(query, (language, True, True))
            structure = {}
            
            for row in results:
                main_topic = row['topic_name']
                subtopic = row['subtopic_name']
                
                if main_topic not in structure:
                    structure[main_topic] = []
                structure[main_topic].append(subtopic)
            
            return structure
            
        except Exception as e:
            logger.error(f"Error getting topic structure for {language}: {e}")
            return {}
    
    def get_full_topic_structure_by_language(self, language: str, active_only: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """Get full topic structure with details by language"""
        try:
            query = """
                SELECT m.topic_name as main_topic, s.id as subtopic_id,
                       s.subtopic_name as subtopic, COUNT(q.id) as question_count
                FROM main_topics m
                LEFT JOIN subtopics s ON m.id = s.main_topic_id
                LEFT JOIN questions q ON s.id = q.topic_id
                WHERE m.language = %s
            """
            params = [language]
            
            if active_only:
                query += " AND m.is_active = %s AND (s.is_active = %s OR s.is_active IS NULL)"
                params.extend([True, True])
            
            query += """
                GROUP BY m.topic_name, s.id, s.subtopic_name
                ORDER BY m.topic_name, s.subtopic_name
            """
            
            results = self.fetch_all(query, params)
            structure = {}
            
            for row in results:
                main_topic = row['main_topic']
                
                if main_topic not in structure:
                    structure[main_topic] = []
                
                if row['subtopic']:
                    structure[main_topic].append({
                        'id': row['subtopic_id'],
                        'name': row['subtopic'],
                        'question_count': row['question_count'] or 0,
                        'has_questions': (row['question_count'] or 0) > 0
                    })
            
            return structure
            
        except Exception as e:
            logger.error(f"Error getting full topic structure for {language}: {e}")
            return {}
    
    def get_topic_language(self, topic_name: str) -> str:
        """Get topic language"""
        try:
            query = """
                SELECT m.language
                FROM subtopics s
                JOIN main_topics m ON s.main_topic_id = m.id
                WHERE s.subtopic_name = %s AND s.is_active = %s AND m.is_active = %s
                LIMIT 1
            """
            result = self.fetch_one(query, (topic_name, True, True))
            return result['language'] if result else 'ru'
            
        except Exception as e:
            logger.error(f"Error getting topic language for {topic_name}: {e}")
            return 'ru'
    
    def get_main_topic_and_language_for_subtopic(self, subtopic_name: str) -> Tuple[Optional[str], str]:
        """Get main topic and language for subtopic"""
        try:
            query = """
                SELECT m.topic_name, m.language
                FROM subtopics s
                JOIN main_topics m ON s.main_topic_id = m.id
                WHERE s.subtopic_name = %s AND s.is_active = %s AND m.is_active = %s
                LIMIT 1
            """
            result = self.fetch_one(query, (subtopic_name, True, True))
            
            if result:
                return result['topic_name'], result['language']
            else:
                return None, 'ru'
                
        except Exception as e:
            logger.error(f"Error getting main topic for {subtopic_name}: {e}")
            return None, 'ru'
    
    def get_topics_with_question_counts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get topics with question counts"""
        try:
            query = """
                SELECT s.id, s.subtopic_name as name, m.topic_name as main_topic,
                       m.language, s.is_active, COUNT(q.id) as question_count
                FROM subtopics s
                JOIN main_topics m ON s.main_topic_id = m.id
                LEFT JOIN questions q ON s.id = q.topic_id
            """
            params = []
            
            if active_only:
                query += " WHERE s.is_active = %s AND m.is_active = %s"
                params = [True, True]
            
            query += """
                GROUP BY s.id, s.subtopic_name, m.topic_name, m.language, s.is_active
                ORDER BY m.topic_name, s.subtopic_name
            """
            
            results = self.fetch_all(query, params)
            
            return [
                {
                    'id': row['id'],
                    'name': row['name'],
                    'main_topic': row['main_topic'],
                    'language': row['language'],
                    'is_active': row['is_active'],
                    'question_count': row['question_count'],
                    'has_questions': row['question_count'] > 0,
                    'availability_status': 'db' if row['question_count'] > 0 else 'ai'
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting topics with question counts: {e}")
            return []
    
    def get_topic_question_counts(self) -> Dict[str, int]:
        """Get question count for each topic"""
        try:
            query = """
                SELECT s.subtopic_name, COUNT(q.id) as question_count
                FROM subtopics s
                LEFT JOIN questions q ON s.id = q.topic_id
                WHERE s.is_active = %s
                GROUP BY s.subtopic_name
                ORDER BY s.subtopic_name
            """
            
            results = self.fetch_all(query, (True,))
            return {row['subtopic_name']: row['question_count'] for row in results}
            
        except Exception as e:
            logger.error(f"Error getting topic question counts: {e}")
            return {}
    
    def get_topic_question_counts_by_id(self) -> Dict[int, Dict[str, Any]]:
        """Get question counts by topic ID"""
        try:
            query = """
                SELECT s.id, s.subtopic_name as name, m.topic_name as main_topic,
                       s.is_active, COUNT(q.id) as question_count
                FROM subtopics s
                JOIN main_topics m ON s.main_topic_id = m.id
                LEFT JOIN questions q ON s.id = q.topic_id
                WHERE s.is_active = %s
                GROUP BY s.id, s.subtopic_name, m.topic_name, s.is_active
                ORDER BY m.topic_name, s.subtopic_name
            """
            
            results = self.fetch_all(query, (True,))
            
            return {
                row['id']: {
                    'name': row['name'],
                    'question_count': row['question_count'],
                    'main_topic': row['main_topic'],
                    'is_active': row['is_active']
                }
                for row in results
            }
            
        except Exception as e:
            logger.error(f"Error getting topic question counts by ID: {e}")
            return {} 