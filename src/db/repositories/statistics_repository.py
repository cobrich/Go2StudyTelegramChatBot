"""
Statistics Repository

Handles all statistics and analytics-related database operations.
"""

import logging
from typing import Dict, List, Optional, Tuple
from ..base_repository import BaseRepository

logger = logging.getLogger(__name__)

class StatisticsRepository(BaseRepository):
    """Repository for statistics and analytics operations"""
    
    def __init__(self):
        super().__init__()
    
    def _get_fallback_value(self):
        """Get fallback value when database is unreachable"""
        # Для статистики возвращаем пустые списки
        return []
    
    # ============== TEST RESULTS METHODS ==============
    
    def add_test_result(self, user_id: int, topic: str, percentage: float) -> None:
        """Add test result for user."""
        query = f'''
            INSERT INTO test_results (user_id, topic, percentage, date, timestamp)
            VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_placeholder(3)}, 
                    {self._get_current_timestamp()}, {self._get_current_timestamp()})
        '''
        self.execute_query(query, (user_id, topic, percentage))
    
    def get_user_test_results(self, user_id: int) -> List[Dict]:
        """Get all test results for a user."""
        query = f'''
            SELECT topic, percentage, timestamp 
            FROM test_results 
            WHERE user_id = {self._get_placeholder(1)} 
            ORDER BY timestamp DESC
        '''
        
        results = self.fetch_all(query, (user_id,))
        
        # Format results for compatibility
        for result in results:
            result['date'] = str(result['timestamp'])[:10] if result['timestamp'] else ''
        
        return results
    
    def get_user_progress(self, user_id: int) -> Tuple[int, float]:
        """Get user's test progress statistics."""
        query = f'''
            SELECT COUNT(*) as total_tests, COALESCE(AVG(percentage), 0) as avg_percentage
            FROM test_results
            WHERE user_id = {self._get_placeholder(1)}
        '''
        
        result = self.fetch_one(query, (user_id,))
        if result:
            return (result['total_tests'], result['avg_percentage'])
        return (0, 0)
    
    def get_recent_topics(self, user_id: int, limit: int = 5) -> List[Tuple[str, float, str]]:
        """Get user's recent test topics with results."""
        query = f'''
            SELECT topic, percentage, timestamp
            FROM test_results
            WHERE user_id = {self._get_placeholder(1)}
            ORDER BY timestamp DESC
            LIMIT {self._get_placeholder(2)}
        '''
        
        results = self.fetch_all(query, (user_id, limit))
        return [(r['topic'], r['percentage'], str(r['timestamp'])) for r in results]
    
    def get_recent_unique_topics(self, user_id: int, unique_limit: int = 5, history_limit: int = 20) -> List[Tuple[str, int]]:
        """Get last unique topics with counts from recent test attempts."""
        query = f'''
            SELECT topic
            FROM test_results
            WHERE user_id = {self._get_placeholder(1)}
            ORDER BY timestamp DESC
            LIMIT {self._get_placeholder(2)}
        '''
        
        results = self.fetch_all(query, (user_id, history_limit))
        
        # Count topics and maintain order
        topic_counts = {}
        topic_order = []
        for result in results:
            topic = result['topic']
            if topic not in topic_counts:
                topic_counts[topic] = 1
                topic_order.append(topic)
            else:
                topic_counts[topic] += 1
        
        # Return only the first unique_limit unique topics
        return [(topic, topic_counts[topic]) for topic in topic_order[:unique_limit]]
    
    # ============== USER ERROR TRACKING METHODS ==============
    
    def add_user_error(self, user_id: int, topic: str, question_text: str,
                      user_answer_text: str, correct_answer_text: str,
                      explanation_text: str) -> None:
        """Add a user's error to the database or increment error count if exists."""
        try:
            # Find question ID by question text
            question_query = f'SELECT id FROM questions WHERE question = {self._get_placeholder(1)} LIMIT 1'
            question_id = self.fetch_val(question_query, (question_text,))
            
            if not question_id:
                logger.warning(f"Question not found in database: {question_text[:100]}...")
                return
            
            # Check if error already exists
            check_query = f'''
                SELECT id, error_count FROM user_errors 
                WHERE user_id = {self._get_placeholder(1)} AND question_id = {self._get_placeholder(2)}
            '''
            existing = self.fetch_one(check_query, (user_id, question_id))
            
            if existing:
                # Update existing error
                update_query = f'''
                    UPDATE user_errors 
                    SET error_count = error_count + 1,
                        last_error_date = {self._get_current_timestamp()}
                    WHERE id = {self._get_placeholder(1)}
                '''
                self.execute_query(update_query, (existing['id'],))
                logger.info(f"Updated error count for user {user_id}, question {question_id}")
            else:
                # Insert new error
                insert_query = f'''
                    INSERT INTO user_errors 
                    (user_id, question_id, topic, user_answer, correct_answer)
                    VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_placeholder(3)}, 
                            {self._get_placeholder(4)}, {self._get_placeholder(5)})
                '''
                self.execute_query(insert_query, (user_id, question_id, topic, user_answer_text, correct_answer_text))
                logger.info(f"Inserted new error for user {user_id}, question {question_id}")
                
        except Exception as e:
            logger.error(f"Error adding user error: {e}")
    
    def add_user_error_by_question_id(self, user_id: int, question_id: int, topic: str,
                                     user_answer_text: str, correct_answer_text: str) -> None:
        """Add user error using question_id directly."""
        try:
            # Check if error already exists
            check_query = f'''
                SELECT id, error_count FROM user_errors 
                WHERE user_id = {self._get_placeholder(1)} AND question_id = {self._get_placeholder(2)}
            '''
            existing = self.fetch_one(check_query, (user_id, question_id))
            
            if existing:
                # Update existing error
                update_query = f'''
                    UPDATE user_errors 
                    SET error_count = error_count + 1,
                        last_error_date = {self._get_current_timestamp()}
                    WHERE id = {self._get_placeholder(1)}
                '''
                self.execute_query(update_query, (existing['id'],))
            else:
                # Insert new error
                insert_query = f'''
                    INSERT INTO user_errors 
                    (user_id, question_id, topic, user_answer, correct_answer)
                    VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_placeholder(3)}, 
                            {self._get_placeholder(4)}, {self._get_placeholder(5)})
                '''
                self.execute_query(insert_query, (user_id, question_id, topic, user_answer_text, correct_answer_text))
                
        except Exception as e:
            logger.error(f"Error adding user error by question ID: {e}")
    
    def decrement_error_count(self, user_id: int, question_text: str) -> None:
        """Decrement error count for a question and remove if reaches 0."""
        try:
            # Find question ID
            question_query = f'SELECT id FROM questions WHERE question = {self._get_placeholder(1)} LIMIT 1'
            question_id = self.fetch_val(question_query, (question_text,))
            
            if not question_id:
                logger.warning(f"Question not found: {question_text[:100]}...")
                return
            
            # Decrement error count
            update_query = f'''
                UPDATE user_errors 
                SET error_count = error_count - 1
                WHERE user_id = {self._get_placeholder(1)} AND question_id = {self._get_placeholder(2)}
            '''
            self.execute_query(update_query, (user_id, question_id))
            
            # Remove if count reaches 0
            delete_query = f'''
                DELETE FROM user_errors 
                WHERE user_id = {self._get_placeholder(1)} AND question_id = {self._get_placeholder(2)} AND error_count <= 0
            '''
            self.execute_query(delete_query, (user_id, question_id))
            
        except Exception as e:
            logger.error(f"Error decrementing error count: {e}")
    
    def decrement_error_count_by_question_id(self, user_id: int, question_id: int) -> None:
        """Decrement error count by question_id and remove if reaches 0."""
        try:
            # Decrement error count
            update_query = f'''
                UPDATE user_errors 
                SET error_count = error_count - 1
                WHERE user_id = {self._get_placeholder(1)} AND question_id = {self._get_placeholder(2)}
            '''
            self.execute_query(update_query, (user_id, question_id))
            
            # Remove if count reaches 0
            delete_query = f'''
                DELETE FROM user_errors 
                WHERE user_id = {self._get_placeholder(1)} AND question_id = {self._get_placeholder(2)} AND error_count <= 0
            '''
            self.execute_query(delete_query, (user_id, question_id))
            
        except Exception as e:
            logger.error(f"Error decrementing error count by question ID: {e}")
    
    def get_error_tasks_for_user(self, user_id: int, topic: str, limit: int = 10) -> List[Dict]:
        """Get tasks that user previously answered incorrectly."""
        query = f'''
            SELECT q.id, q.question, q.answer, q.explanation, q.incorrect_options, 
                   ue.error_count, q.image_path, s.name as topic_name
            FROM questions q
            JOIN subtopics s ON q.topic_id = s.id
            JOIN user_errors ue ON q.id = ue.question_id
            WHERE ue.user_id = {self._get_placeholder(1)} AND s.name = {self._get_placeholder(2)} AND s.is_active = {self._get_placeholder(3)}
            ORDER BY ue.error_count DESC, ue.last_error_date DESC
            LIMIT {self._get_placeholder(4)}
        '''
        
        return self.fetch_all(query, (user_id, topic, self._get_boolean_value(True), limit))
    
    def get_error_tasks_for_user_by_topic_id(self, user_id: int, topic_id: int, limit: int = 10) -> List[Dict]:
        """Get error tasks for user by topic_id."""
        query = f'''
            SELECT q.id, q.question, q.answer, q.explanation, q.incorrect_options, 
                   ue.error_count, q.image_path, s.name as topic_name
            FROM questions q
            JOIN subtopics s ON q.topic_id = s.id
            JOIN user_errors ue ON q.id = ue.question_id
            WHERE ue.user_id = {self._get_placeholder(1)} AND q.topic_id = {self._get_placeholder(2)} AND s.is_active = {self._get_placeholder(3)}
            ORDER BY ue.error_count DESC, ue.last_error_date DESC
            LIMIT {self._get_placeholder(4)}
        '''
        
        return self.fetch_all(query, (user_id, topic_id, self._get_boolean_value(True), limit))
    
    def get_error_topics(self, user_id: int) -> List[Tuple[str, int]]:
        """Get topics where user made errors."""
        query = f'''
            SELECT topic, COUNT(*) as error_count
            FROM user_errors
            WHERE user_id = {self._get_placeholder(1)}
            GROUP BY topic
            ORDER BY error_count DESC
        '''
        
        results = self.fetch_all(query, (user_id,))
        return [(r['topic'], r['error_count']) for r in results]
    
    # ============== COMPREHENSIVE USER STATISTICS ==============
    
    def get_user_historical_stats(self, user_id: int) -> Dict:
        """Get comprehensive user statistics."""
        # Get basic user info
        user_query = f'''
            SELECT full_name, grade, language, last_activity
            FROM allowed_users WHERE user_id = {self._get_placeholder(1)}
        '''
        user_info = self.fetch_one(user_query, (user_id,))
        
        if not user_info:
            return {}
        
        # Get test statistics
        test_query = f'''
            SELECT COUNT(*) as total_tests, COALESCE(AVG(percentage), 0) as avg_score,
                   MAX(timestamp) as last_test_date
            FROM test_results WHERE user_id = {self._get_placeholder(1)}
        '''
        test_stats = self.fetch_one(test_query, (user_id,))
        
        # Get error statistics
        error_query = f'''
            SELECT COUNT(DISTINCT question_id) as unique_errors,
                   SUM(error_count) as total_errors
            FROM user_errors WHERE user_id = {self._get_placeholder(1)}
        '''
        error_stats = self.fetch_one(error_query, (user_id,))
        
        return {
            'user_id': user_id,
            'full_name': user_info['full_name'],
            'grade': user_info['grade'],
            'language': user_info['language'],
            'last_activity': user_info['last_activity'],
            'total_tests': test_stats['total_tests'] if test_stats else 0,
            'avg_score': round(test_stats['avg_score'] if test_stats else 0, 1),
            'last_test_date': test_stats['last_test_date'] if test_stats else None,
            'unique_errors': error_stats['unique_errors'] if error_stats else 0,
            'total_errors': error_stats['total_errors'] if error_stats else 0
        }
    
    def get_student_detailed_statistics(self, user_id: int) -> Optional[Dict]:
        """Get detailed statistics for admin view."""
        # Basic user info
        user_query = f'''
            SELECT user_id, username, full_name, grade, language, last_activity, added_at
            FROM allowed_users
            WHERE user_id = {self._get_placeholder(1)}
        '''
        user_info = self.fetch_one(user_query, (user_id,))
        
        if not user_info:
            return None
        
        # Test statistics
        test_stats_query = f'''
            SELECT COUNT(*) as total_tests, 
                   COALESCE(AVG(percentage), 0) as avg_score,
                   COALESCE(MIN(percentage), 0) as min_score,
                   COALESCE(MAX(percentage), 0) as max_score,
                   MIN(timestamp) as first_test,
                   MAX(timestamp) as last_test
            FROM test_results 
            WHERE user_id = {self._get_placeholder(1)}
        '''
        test_stats = self.fetch_one(test_stats_query, (user_id,))
        
        # Topic performance
        topic_performance_query = f'''
            SELECT topic, 
                   COUNT(*) as tests_count,
                   COALESCE(AVG(percentage), 0) as avg_score,
                   MAX(timestamp) as last_attempt
            FROM test_results 
            WHERE user_id = {self._get_placeholder(1)}
            GROUP BY topic
            ORDER BY last_attempt DESC
        '''
        topic_performance = self.fetch_all(topic_performance_query, (user_id,))
        
        # Error analysis
        error_analysis_query = f'''
            SELECT ue.topic,
                   COUNT(DISTINCT ue.question_id) as unique_errors,
                   SUM(ue.error_count) as total_errors,
                   MAX(ue.last_error_date) as last_error
            FROM user_errors ue
            WHERE ue.user_id = {self._get_placeholder(1)}
            GROUP BY ue.topic
            ORDER BY total_errors DESC
        '''
        error_analysis = self.fetch_all(error_analysis_query, (user_id,))
        
        # Recent errors (top 10)
        recent_errors_query = f'''
            SELECT q.question, ue.topic, ue.error_count, ue.last_error_date
            FROM user_errors ue
            JOIN questions q ON ue.question_id = q.id
            WHERE ue.user_id = {self._get_placeholder(1)}
            ORDER BY ue.last_error_date DESC
            LIMIT 10
        '''
        recent_errors = self.fetch_all(recent_errors_query, (user_id,))
        
        # Daily progress (last 30 days)
        daily_progress_query = '''
            SELECT DATE(timestamp) as test_date,
                   COUNT(*) as tests_count,
                   AVG(percentage) as avg_score
            FROM test_results 
            WHERE user_id = ? AND timestamp >= datetime('now', '-30 days')
            GROUP BY DATE(timestamp)
            ORDER BY test_date DESC
        ''' if not self.is_postgresql else f'''
            SELECT DATE(timestamp) as test_date,
                   COUNT(*) as tests_count,
                   AVG(percentage) as avg_score
            FROM test_results 
            WHERE user_id = {self._get_placeholder(1)} AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            GROUP BY DATE(timestamp)
            ORDER BY test_date DESC
        '''
        daily_progress = self.fetch_all(daily_progress_query, (user_id,))
        
        return {
            'user_info': dict(user_info),
            'test_statistics': {
                'total_tests': test_stats['total_tests'] if test_stats else 0,
                'avg_score': round(test_stats['avg_score'] or 0, 1),
                'min_score': test_stats['min_score'] or 0,
                'max_score': test_stats['max_score'] or 0,
                'first_test': test_stats['first_test'] if test_stats else None,
                'last_test': test_stats['last_test'] if test_stats else None
            },
            'topic_performance': [
                {
                    'topic': row['topic'],
                    'tests_count': row['tests_count'],
                    'avg_score': round(row['avg_score'], 1),
                    'last_attempt': row['last_attempt']
                }
                for row in topic_performance
            ],
            'error_analysis': [
                {
                    'topic': row['topic'],
                    'unique_errors': row['unique_errors'],
                    'total_errors': row['total_errors'],
                    'last_error': row['last_error']
                }
                for row in error_analysis
            ],
            'recent_errors': [
                {
                    'question': row['question'][:100] + '...' if len(row['question']) > 100 else row['question'],
                    'topic': row['topic'],
                    'error_count': row['error_count'],
                    'timestamp': row['last_error_date']
                }
                for row in recent_errors
            ],
            'daily_progress': [
                {
                    'date': str(row['test_date']),
                    'tests_count': row['tests_count'],
                    'avg_score': round(row['avg_score'], 1)
                }
                for row in daily_progress
            ]
        }
    
    # ============== GLOBAL STATISTICS ==============
    
    def get_all_students_summary(self) -> List[Dict]:
        """Get summary of all students for admin panel."""
        query = f'''
            SELECT au.user_id, au.username, au.full_name, au.grade, au.has_access, au.added_at,
                   au.last_activity, au.is_active,
                   COUNT(tr.id) as total_tests,
                   COALESCE(AVG(tr.percentage), 0) as avg_score,
                   COUNT(DISTINCT ue.question_id) as unique_errors,
                   MAX(tr.timestamp) as last_test
            FROM allowed_users au
            LEFT JOIN test_results tr ON au.user_id = tr.user_id
            LEFT JOIN user_errors ue ON au.user_id = ue.user_id
            GROUP BY au.id, au.user_id, au.username, au.full_name, au.grade, au.has_access, 
                     au.added_at, au.last_activity, au.is_active
            ORDER BY au.added_at DESC
        '''
        
        results = self.fetch_all(query)
        
        for result in results:
            result['avg_score'] = round(result['avg_score'], 1)
            result['status'] = 'Активен' if result['has_access'] else 'Заблокирован'
        
        return results
    
    def get_class_statistics(self, grade: int = None) -> Dict:
        """Get statistics by class or all classes."""
        if grade:
            # Statistics for specific grade
            query = f'''
                SELECT au.grade,
                       COUNT(DISTINCT au.id) as students_count,
                       COUNT(DISTINCT tr.user_id) as active_students,
                       COUNT(tr.id) as total_tests,
                       COALESCE(AVG(tr.percentage), 0) as avg_score
                FROM allowed_users au
                LEFT JOIN test_results tr ON au.user_id = tr.user_id
                WHERE au.grade = {self._get_placeholder(1)} AND au.has_access = {self._get_placeholder(2)}
                GROUP BY au.grade
            '''
            params = (grade, self._get_boolean_value(True))
        else:
            # Statistics for all grades
            query = f'''
                SELECT au.grade,
                       COUNT(DISTINCT au.id) as students_count,
                       COUNT(DISTINCT tr.user_id) as active_students,
                       COUNT(tr.id) as total_tests,
                       COALESCE(AVG(tr.percentage), 0) as avg_score
                FROM allowed_users au
                LEFT JOIN test_results tr ON au.user_id = tr.user_id
                WHERE au.has_access = {self._get_placeholder(1)}
                GROUP BY au.grade
                ORDER BY au.grade
            '''
            params = (self._get_boolean_value(True),)
        
        results = self.fetch_all(query, params)
        
        class_stats = []
        for result in results:
            class_stats.append({
                'grade': result['grade'],
                'students_count': result['students_count'],
                'active_students': result['active_students'],
                'total_tests': result['total_tests'] or 0,
                'avg_score': round(result['avg_score'], 1),
                'activity_rate': round((result['active_students'] / result['students_count'] * 100) if result['students_count'] > 0 else 0, 1)
            })
        
        return {'class_stats': class_stats} 