"""
Question Repository

Handles all question and topic-related database operations.
"""

import logging
import json
from typing import Dict, List, Optional, Tuple
from ..base_repository import BaseRepository

logger = logging.getLogger(__name__)

class QuestionRepository(BaseRepository):
    """Repository for question and topic operations"""
    
    def __init__(self):
        super().__init__()
    
    # ============== TOPIC METHODS ==============
    
    def get_all_topics(self, active_only: bool = True) -> List[Dict]:
        """Get all subtopics as flat list for compatibility."""
        where_clause = 'WHERE st.is_active = TRUE AND mt.is_active = TRUE' if active_only else ''
        
        query = f'''
            SELECT st.id, st.subtopic_name as name, mt.topic_name as main_topic, st.is_active, st.created_at,
                   COALESCE(q.question_count, 0) as question_count
            FROM subtopics st
            JOIN main_topics mt ON st.main_topic_id = mt.id
            LEFT JOIN (
                SELECT topic_id, COUNT(*) as question_count
                FROM questions
                GROUP BY topic_id
            ) q ON st.id = q.topic_id
            {where_clause}
            ORDER BY mt.id, st.id
        '''
        
        topics = self.fetch_all(query)
        
        # Format for compatibility
        for topic in topics:
            topic['description'] = f"Подтема раздела '{topic['main_topic']}': {topic['name']}"
        
        return topics
    
    def get_topics_by_language(self, language: str, active_only: bool = True) -> Dict[str, List[Dict]]:
        """Get topics grouped by main topic for specific language."""
        where_clause = 'AND st.is_active = TRUE AND mt.is_active = TRUE' if active_only else ''
        
        query = f'''
            SELECT mt.topic_name as main_topic, st.subtopic_name as subtopic, st.id
            FROM main_topics mt
            JOIN subtopics st ON mt.id = st.main_topic_id
            WHERE mt.language = {self._get_placeholder(1)} {where_clause}
            ORDER BY mt.id, st.id
        '''
        
        rows = self.fetch_all(query, (language,))
        
        # Group by main topic
        topics_dict = {}
        for row in rows:
            main_topic = row['main_topic']
            if main_topic not in topics_dict:
                topics_dict[main_topic] = []
            topics_dict[main_topic].append({
                'id': row['id'],
                'name': row['subtopic'],
                'language': language
            })
        
        return topics_dict
    
    def get_topic_names(self, active_only: bool = True) -> List[str]:
        """Get list of subtopic names for compatibility."""
        topics = self.get_all_topics(active_only)
        return [topic['name'] for topic in topics]
    
    def add_topic(self, name: str, description: str = None, created_by: int = None, main_topic_name: str = None) -> bool:
        """Add new subtopic."""
        try:
            # Find main topic ID
            if main_topic_name:
                main_topic_query = f'SELECT id FROM main_topics WHERE topic_name = {self._get_placeholder(1)}'
                main_topic_id = self.fetch_val(main_topic_query, (main_topic_name,))
                if not main_topic_id:
                    return False
            else:
                # Use first available main topic
                main_topic_query = f'SELECT id FROM main_topics WHERE is_active = {self._get_placeholder(1)} ORDER BY id LIMIT 1'
                main_topic_id = self.fetch_val(main_topic_query, (self._get_boolean_value(True),))
                if not main_topic_id:
                    return False
            
            # Insert subtopic (убираем order_index, его нет в новой схеме)
            insert_query = f'''
                INSERT INTO subtopics (main_topic_id, subtopic_name)
                VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)})
            '''
            self.execute_query(insert_query, (main_topic_id, name))
            return True
        except Exception as e:
            logger.error(f"Error adding topic: {e}")
            return False
    
    def update_topic(self, topic_id: int, name: str = None, description: str = None, is_active: bool = None) -> bool:
        """Update subtopic."""
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append(f"subtopic_name = {self._get_placeholder(len(params) + 1)}")
                params.append(name)
            if is_active is not None:
                updates.append(f"is_active = {self._get_placeholder(len(params) + 1)}")
                params.append(self._get_boolean_value(is_active))
            
            if updates:
                params.append(topic_id)
                query = f'''
                    UPDATE subtopics 
                    SET {", ".join(updates)}
                    WHERE id = {self._get_placeholder(len(params))}
                '''
                self.execute_query(query, tuple(params))
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating topic: {e}")
            return False
    
    def delete_topic(self, topic_id: int) -> bool:
        """Delete subtopic (soft delete)."""
        return self.update_topic(topic_id, is_active=False)
    
    def get_topic_id_by_name(self, topic_name: str) -> Optional[int]:
        """Get topic ID by name."""
        query = f'SELECT id FROM subtopics WHERE subtopic_name = {self._get_placeholder(1)}'
        return self.fetch_val(query, (topic_name,))
    
    def get_topic_name_by_id(self, topic_id: int) -> Optional[str]:
        """Get topic name by ID."""
        query = f'SELECT subtopic_name FROM subtopics WHERE id = {self._get_placeholder(1)}'
        return self.fetch_val(query, (topic_id,))
    
    # ============== QUESTION METHODS ==============
    
    def get_tasks_for_topic(self, topic: str, limit: int = 20) -> List[Dict]:
        """Get tasks for specific topic by name."""
        query = f'''
            SELECT q.id, q.question_text as question, q.correct_answer as answer, 
                   q.option_a, q.option_b, q.option_c, q.option_d,
                   q.source, s.subtopic_name as topic_name
            FROM questions q
            JOIN subtopics s ON q.topic_id = s.id
            WHERE s.subtopic_name = {self._get_placeholder(1)} AND s.is_active = {self._get_placeholder(2)}
            ORDER BY RANDOM()
            LIMIT {self._get_placeholder(3)}
        '''
        
        questions = self.fetch_all(query, (topic, self._get_boolean_value(True), limit))
        
        # Format for compatibility - создаем explanation и incorrect_options
        for question in questions:
            question['explanation'] = f"Правильный ответ: {question['answer']}"
            question['incorrect_options'] = [
                opt for opt in [question['option_a'], question['option_b'], 
                               question['option_c'], question['option_d']]
                if opt != question['answer']
            ]
        
        return questions
    
    def get_tasks_for_topic_id(self, topic_id: int, limit: int = 20) -> List[Dict]:
        """Get tasks for specific topic by ID."""
        query = f'''
            SELECT q.id, q.question, q.answer, q.explanation, q.incorrect_options, 
                   q.question_type, q.source, q.image_path, s.name as topic_name
            FROM questions q
            JOIN subtopics s ON q.topic_id = s.id
            WHERE q.topic_id = {self._get_placeholder(1)} AND s.is_active = {self._get_placeholder(2)}
            ORDER BY RANDOM()
            LIMIT {self._get_placeholder(3)}
        '''
        
        return self.fetch_all(query, (topic_id, self._get_boolean_value(True), limit))
    
    def get_all_questions(self) -> List[Dict]:
        """Get all questions from database."""
        query = '''
            SELECT q.id, q.question, q.answer, q.explanation, q.incorrect_options,
                   q.question_type, q.source, q.image_path, s.name as topic,
                   q.topic_id, q.created_at
            FROM questions q
            LEFT JOIN subtopics s ON q.topic_id = s.id
            ORDER BY q.created_at DESC
        '''
        
        questions = self.fetch_all(query)
        
        # Process incorrect_options
        for question in questions:
            if question.get('incorrect_options'):
                try:
                    if isinstance(question['incorrect_options'], str):
                        question['incorrect_options'] = json.loads(question['incorrect_options'])
                except (json.JSONDecodeError, TypeError):
                    question['incorrect_options'] = question['incorrect_options'].split('\n') if question['incorrect_options'] else []
        
        return questions
    
    def add_question(self, question: dict) -> bool:
        """Add new question to database with automatic topic conversion."""
        try:
            # Validate required fields
            required_fields = ['question', 'answer', 'explanation']
            for field in required_fields:
                if not question.get(field):
                    logger.error(f"Cannot add question: {field} is None or empty")
                    return False
            
            # Determine topic_id
            topic_id = None
            topic_name = None
            
            if question.get('topic_id'):
                topic_id = question['topic_id']
                topic_name = self.get_topic_name_by_id(topic_id)
            elif question.get('topic'):
                topic_name = question['topic']
                topic_id = self.get_topic_id_by_name(topic_name)
                
                if not topic_id:
                    # Create missing subtopic
                    if self.add_topic(topic_name):
                        topic_id = self.get_topic_id_by_name(topic_name)
                    
                if not topic_id:
                    logger.error(f"Failed to create topic '{topic_name}' for question")
                    return False
            else:
                logger.error("Cannot add question: neither topic nor topic_id provided")
                return False
            
            # Prepare incorrect_options
            incorrect_options = question.get('incorrect_options', '')
            if isinstance(incorrect_options, list):
                incorrect_options = json.dumps(incorrect_options)
            
            # Insert question
            query = f'''
                INSERT INTO questions (topic_id, question, answer, explanation, incorrect_options, question_type, source)
                VALUES ({self._get_placeholder(1)}, {self._get_placeholder(2)}, {self._get_placeholder(3)}, 
                        {self._get_placeholder(4)}, {self._get_placeholder(5)}, {self._get_placeholder(6)}, 
                        {self._get_placeholder(7)})
            '''
            params = (
                topic_id,
                question['question'],
                question['answer'],
                question['explanation'],
                incorrect_options,
                question.get('question_type', 'standard'),
                question.get('source', 'db')
            )
            
            self.execute_query(query, params)
            logger.info(f"Successfully added question with topic: {topic_name}, topic_id: {topic_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding question: {e}")
            return False
    
    def update_question(self, question_text: str, new_answer: str, new_explanation: str) -> bool:
        """Update a question's answer and explanation."""
        try:
            query = f'''
                UPDATE questions 
                SET answer = {self._get_placeholder(1)}, explanation = {self._get_placeholder(2)}
                WHERE question = {self._get_placeholder(3)}
            '''
            self.execute_query(query, (new_answer, new_explanation, question_text))
            return True
        except Exception as e:
            logger.error(f"Error updating question: {e}")
            return False
    
    def delete_question_by_id(self, question_id: int) -> bool:
        """Delete question by ID."""
        try:
            # Check if question exists
            check_query = f'SELECT 1 FROM questions WHERE id = {self._get_placeholder(1)}'
            if not self.fetch_val(check_query, (question_id,)):
                return False
            
            # Delete question
            delete_query = f'DELETE FROM questions WHERE id = {self._get_placeholder(1)}'
            self.execute_query(delete_query, (question_id,))
            return True
        except Exception as e:
            logger.error(f"Error deleting question: {e}")
            return False
    
    def get_all_ai_questions(self) -> List[Dict]:
        """Get all AI-generated questions."""
        query = f'''
            SELECT q.id, q.question, q.answer, q.explanation, s.name as topic, 
                   q.source, q.topic_id, q.created_at
            FROM questions q
            LEFT JOIN subtopics s ON q.topic_id = s.id
            WHERE q.source = {self._get_placeholder(1)}
            ORDER BY q.id DESC
        '''
        
        return self.fetch_all(query, ('ai',))
    
    # ============== QUESTION STATISTICS METHODS ==============
    
    def get_topic_question_counts(self) -> Dict[str, int]:
        """Get question count for each topic."""
        query = '''
            SELECT s.name as topic, COUNT(q.id) as question_count
            FROM subtopics s
            LEFT JOIN questions q ON s.id = q.topic_id
            GROUP BY s.name
            ORDER BY s.name
        '''
        
        results = self.fetch_all(query)
        return {row['topic']: row['question_count'] for row in results}
    
    def get_topics_with_question_counts(self, active_only: bool = True) -> List[Dict]:
        """Get all topics with their question counts."""
        where_clause = 'WHERE s.is_active = TRUE AND m.is_active = TRUE' if active_only else ''
        
        query = f'''
            SELECT s.name, 
                   COALESCE(q.question_count, 0) as question_count,
                   m.topic_name as main_topic
            FROM subtopics s
            JOIN main_topics m ON s.main_topic_id = m.id
            LEFT JOIN (
                SELECT topic_id, COUNT(*) as question_count
                FROM questions
                GROUP BY topic_id
            ) q ON s.id = q.topic_id
            {where_clause}
            ORDER BY m.id, s.id
        '''
        
        topics = self.fetch_all(query)
        
        # Add availability status
        for topic in topics:
            topic['has_questions'] = topic['question_count'] > 0
            topic['availability_status'] = 'db' if topic['question_count'] > 0 else 'ai'
        
        return topics
    
    def get_explanation_by_question_text(self, question_text: str) -> Optional[str]:
        """Get explanation for a question by exact text match."""
        query = f'SELECT explanation FROM questions WHERE question = {self._get_placeholder(1)}'
        return self.fetch_val(query, (question_text,))
    
    def get_explanation_fuzzy_by_question_text(self, question_text: str) -> Optional[str]:
        """Get explanation for a question using fuzzy matching."""
        search_pattern = f'%{question_text}%'
        
        query = f'''
            SELECT explanation FROM questions 
            WHERE question LIKE {self._get_placeholder(1)} 
            LIMIT 1
        ''' if not self.is_postgresql else f'''
            SELECT explanation FROM questions 
            WHERE question ILIKE {self._get_placeholder(1)} 
            LIMIT 1
        '''
        
        return self.fetch_val(query, (search_pattern,))
    
    # ============== MAIN TOPIC METHODS ==============
    
    def get_main_topics_by_language(self, language: str, active_only: bool = True) -> List[Dict]:
        """Get main topics for specific language."""
        where_clause = f'AND is_active = {self._get_placeholder(2)}' if active_only else ''
        
        query = f'''
            SELECT id, topic_name, order_index, language, is_active
            FROM main_topics
            WHERE language = {self._get_placeholder(1)} {where_clause}
            ORDER BY order_index
        '''
        
        params = (language, self._get_boolean_value(True)) if active_only else (language,)
        return self.fetch_all(query, params)
    
    def get_full_topic_structure_by_language(self, language: str, active_only: bool = True) -> Dict[str, List[Dict]]:
        """Get full topic structure with subtopics for specific language."""
        where_clause = 'AND st.is_active = TRUE AND mt.is_active = TRUE' if active_only else ''
        
        query = f'''
            SELECT mt.topic_name as main_topic, st.subtopic_name as subtopic, 
                   st.id, COALESCE(q.question_count, 0) as question_count
            FROM main_topics mt
            JOIN subtopics st ON mt.id = st.main_topic_id
            LEFT JOIN (
                SELECT topic_id, COUNT(*) as question_count
                FROM questions
                GROUP BY topic_id
            ) q ON st.id = q.topic_id
            WHERE mt.language = {self._get_placeholder(1)} {where_clause}
            ORDER BY mt.id, st.id
        '''
        
        rows = self.fetch_all(query, (language,))
        
        # Group by main topic
        topics_dict = {}
        for row in rows:
            main_topic = row['main_topic']
            if main_topic not in topics_dict:
                topics_dict[main_topic] = []
            topics_dict[main_topic].append({
                'id': row['id'],
                'name': row['subtopic'],
                'question_count': row['question_count']
            })
        
        return topics_dict
    
    # ============== MISSING METHODS FOR ADMIN FUNCTIONALITY ==============
    
    def search_questions(self, search_term: str, limit: int = 50) -> List[Dict]:
        """Search questions by text (stub implementation)."""
        try:
            # Простой поиск по тексту вопроса
            query = f'''
                SELECT q.id, q.question_text as question, q.correct_answer as answer, 
                       q.explanation, s.subtopic_name as topic
                FROM questions q
                LEFT JOIN subtopics s ON q.topic_id = s.id
                WHERE LOWER(q.question_text) LIKE {self._get_placeholder(1)}
                ORDER BY q.created_at DESC
                LIMIT {self._get_placeholder(2)}
            '''
            
            search_pattern = f"%{search_term.lower()}%"
            results = self.fetch_all(query, (search_pattern, limit))
            
            logger.info(f"Found {len(results)} questions matching '{search_term}'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching questions: {e}")
            return []
    
    def get_question_by_id(self, question_id: int) -> Optional[Dict]:
        """Get question by ID (stub implementation)."""
        try:
            query = f'''
                SELECT q.id, q.question_text as question, q.correct_answer as answer,
                       q.explanation, q.option_a, q.option_b, q.option_c, q.option_d,
                       q.topic_id, s.subtopic_name as topic
                FROM questions q
                LEFT JOIN subtopics s ON q.topic_id = s.id
                WHERE q.id = {self._get_placeholder(1)}
            '''
            
            result = self.fetch_one(query, (question_id,))
            if result:
                # Формируем incorrect_options из опций
                incorrect_options = []
                for opt in [result.get('option_a'), result.get('option_b'), 
                           result.get('option_c'), result.get('option_d')]:
                    if opt and opt != result.get('answer'):
                        incorrect_options.append(opt)
                
                result['incorrect_options'] = '\n'.join(incorrect_options)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting question by ID {question_id}: {e}")
            return None
    
    def update_question_explanation(self, question_id: int, explanation: str) -> bool:
        """Update question explanation (stub implementation)."""
        try:
            query = f'''
                UPDATE questions 
                SET explanation = {self._get_placeholder(1)}
                WHERE id = {self._get_placeholder(2)}
            '''
            
            self.execute_query(query, (explanation, question_id))
            logger.info(f"Updated explanation for question {question_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating question explanation: {e}")
            return False
    
    def update_question_text(self, question_id: int, question_text: str) -> bool:
        """Update question text (stub implementation)."""
        try:
            query = f'''
                UPDATE questions 
                SET question_text = {self._get_placeholder(1)}
                WHERE id = {self._get_placeholder(2)}
            '''
            
            self.execute_query(query, (question_text, question_id))
            logger.info(f"Updated text for question {question_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating question text: {e}")
            return False
    
    def update_question_correct_answer(self, question_id: int, correct_answer: str) -> bool:
        """Update question correct answer (stub implementation)."""
        try:
            query = f'''
                UPDATE questions 
                SET correct_answer = {self._get_placeholder(1)}
                WHERE id = {self._get_placeholder(2)}
            '''
            
            self.execute_query(query, (correct_answer, question_id))
            logger.info(f"Updated correct answer for question {question_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating question correct answer: {e}")
            return False
    
    def update_question_options(self, question_id: int, options: List[str]) -> bool:
        """Update question options (stub implementation)."""
        try:
            # Предполагаем что options это список из 4 элементов [A, B, C, D]
            option_a = options[0] if len(options) > 0 else ''
            option_b = options[1] if len(options) > 1 else ''
            option_c = options[2] if len(options) > 2 else ''
            option_d = options[3] if len(options) > 3 else ''
            
            query = f'''
                UPDATE questions 
                SET option_a = {self._get_placeholder(1)},
                    option_b = {self._get_placeholder(2)},
                    option_c = {self._get_placeholder(3)},
                    option_d = {self._get_placeholder(4)}
                WHERE id = {self._get_placeholder(5)}
            '''
            
            self.execute_query(query, (option_a, option_b, option_c, option_d, question_id))
            logger.info(f"Updated options for question {question_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating question options: {e}")
            return False
    
    def update_question_topic(self, question_id: int, topic_id: int) -> bool:
        """Update question topic (stub implementation)."""
        try:
            query = f'''
                UPDATE questions 
                SET topic_id = {self._get_placeholder(1)}
                WHERE id = {self._get_placeholder(2)}
            '''
            
            self.execute_query(query, (topic_id, question_id))
            logger.info(f"Updated topic for question {question_id} to topic {topic_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating question topic: {e}")
            return False
    
    def delete_questions_by_topic_id(self, topic_id: int) -> int:
        """Delete all questions for a topic and return count (stub implementation)."""
        try:
            # Сначала получаем количество вопросов
            count_query = f'SELECT COUNT(*) FROM questions WHERE topic_id = {self._get_placeholder(1)}'
            count = self.fetch_val(count_query, (topic_id,))
            
            if count and count > 0:
                # Удаляем вопросы
                delete_query = f'DELETE FROM questions WHERE topic_id = {self._get_placeholder(1)}'
                self.execute_query(delete_query, (topic_id,))
                logger.info(f"Deleted {count} questions for topic {topic_id}")
                return count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error deleting questions for topic {topic_id}: {e}")
            return 0
    
    def get_questions_without_explanation(self, limit: int = 50) -> List[Dict]:
        """Get questions without explanations (stub implementation)."""
        try:
            query = f'''
                SELECT q.id, q.question_text as question, q.correct_answer as answer,
                       s.subtopic_name as topic
                FROM questions q
                LEFT JOIN subtopics s ON q.topic_id = s.id
                WHERE q.explanation IS NULL OR q.explanation = ''
                ORDER BY q.created_at DESC
                LIMIT {self._get_placeholder(1)}
            '''
            
            return self.fetch_all(query, (limit,))
            
        except Exception as e:
            logger.error(f"Error getting questions without explanation: {e}")
            return []
    
    def get_questions_with_short_explanation(self, max_length: int = 50, limit: int = 50) -> List[Dict]:
        """Get questions with short explanations (stub implementation)."""
        try:
            query = f'''
                SELECT q.id, q.question_text as question, q.correct_answer as answer,
                       q.explanation, s.subtopic_name as topic
                FROM questions q
                LEFT JOIN subtopics s ON q.topic_id = s.id
                WHERE LENGTH(q.explanation) < {self._get_placeholder(1)} AND q.explanation IS NOT NULL
                ORDER BY q.created_at DESC
                LIMIT {self._get_placeholder(2)}
            '''
            
            return self.fetch_all(query, (max_length, limit))
            
        except Exception as e:
            logger.error(f"Error getting questions with short explanation: {e}")
            return []
    
    def get_questions_by_language(self, language: str) -> List[Dict]:
        """Get questions available for specific language (stub implementation)."""
        try:
            query = f'''
                SELECT q.id, q.question_text as question, q.correct_answer as answer,
                       q.explanation, s.subtopic_name as topic
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                JOIN main_topics mt ON s.main_topic_id = mt.id
                WHERE mt.language = {self._get_placeholder(1)} AND s.is_active = {self._get_placeholder(2)}
                ORDER BY q.created_at DESC
            '''
            
            return self.fetch_all(query, (language, self._get_boolean_value(True)))
            
        except Exception as e:
            logger.error(f"Error getting questions by language {language}: {e}")
            return []
    
    def get_subtopics_by_main_topic(self, main_topic_name: str, user_language: str = None) -> List[Dict]:
        """Get subtopics for a main topic (stub implementation)."""
        try:
            where_clause = ''
            params = [main_topic_name]
            
            if user_language:
                where_clause = f'AND mt.language = {self._get_placeholder(2)}'
                params.append(user_language)
            
            query = f'''
                SELECT s.id, s.subtopic_name as name, 
                       COALESCE(q.question_count, 0) as question_count
                FROM subtopics s
                JOIN main_topics mt ON s.main_topic_id = mt.id
                LEFT JOIN (
                    SELECT topic_id, COUNT(*) as question_count
                    FROM questions
                    GROUP BY topic_id
                ) q ON s.id = q.topic_id
                WHERE mt.topic_name = {self._get_placeholder(1)} {where_clause}
                ORDER BY s.id
            '''
            
            return self.fetch_all(query, tuple(params))
            
        except Exception as e:
            logger.error(f"Error getting subtopics for main topic {main_topic_name}: {e}")
            return []
    
    # ============== ADDITIONAL ADMIN METHODS ==============
    
    def count_questions_by_topic_name(self, topic_name: str) -> int:
        """Count questions for a topic by name."""
        try:
            query = f'''
                SELECT COUNT(*) 
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                WHERE s.subtopic_name = {self._get_placeholder(1)}
            '''
            
            return self.fetch_val(query, (topic_name,)) or 0
            
        except Exception as e:
            logger.error(f"Error counting questions for topic {topic_name}: {e}")
            return 0
    
    def delete_questions_by_topic_name(self, topic_name: str) -> int:
        """Delete all questions for a topic by name and return count."""
        try:
            # First get the topic ID
            topic_id = self.get_topic_id_by_name(topic_name)
            if not topic_id:
                return 0
            
            # Count questions before deletion
            count = self.count_questions_by_topic_name(topic_name)
            
            if count > 0:
                # Delete questions
                delete_query = f'''
                    DELETE FROM questions 
                    WHERE topic_id = (SELECT id FROM subtopics WHERE subtopic_name = {self._get_placeholder(1)})
                '''
                self.execute_query(delete_query, (topic_name,))
                logger.info(f"Deleted {count} questions for topic '{topic_name}'")
                return count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error deleting questions for topic {topic_name}: {e}")
            return 0
    
    def get_question_with_topic_by_id(self, question_id: int) -> Optional[Dict]:
        """Get question with topic information by ID."""
        try:
            query = f'''
                SELECT q.id, q.question_text as question, q.correct_answer as answer,
                       q.explanation, q.option_a, q.option_b, q.option_c, q.option_d,
                       q.topic_id, s.subtopic_name as topic
                FROM questions q
                LEFT JOIN subtopics s ON q.topic_id = s.id
                WHERE q.id = {self._get_placeholder(1)}
            '''
            
            result = self.fetch_one(query, (question_id,))
            return result
            
        except Exception as e:
            logger.error(f"Error getting question with topic by ID {question_id}: {e}")
            return None
    
    def get_active_topics_for_selection(self) -> List[Dict]:
        """Get active topics formatted for selection UI."""
        try:
            query = f'''
                SELECT s.id, s.subtopic_name as name, mt.topic_name as main_topic,
                       s.is_active, s.created_at
                FROM subtopics s
                JOIN main_topics mt ON s.main_topic_id = mt.id
                WHERE s.is_active = {self._get_placeholder(1)} AND mt.is_active = {self._get_placeholder(2)}
                ORDER BY mt.topic_name, s.subtopic_name
            '''
            
            return self.fetch_all(query, (self._get_boolean_value(True), self._get_boolean_value(True)))
            
        except Exception as e:
            logger.error(f"Error getting active topics for selection: {e}")
            return []
    
    def get_topic_language(self, topic_name: str) -> str:
        """Get language for a topic by name."""
        try:
            query = f'''
                SELECT mt.language
                FROM subtopics s
                JOIN main_topics mt ON s.main_topic_id = mt.id
                WHERE s.subtopic_name = {self._get_placeholder(1)}
            '''
            
            result = self.fetch_val(query, (topic_name,))
            return result or 'kz'  # Default to Kazakh
            
        except Exception as e:
            logger.error(f"Error getting topic language for {topic_name}: {e}")
            return 'kz'
    
    def search_questions_for_edit(self, search_term: str, limit: int = 10) -> List[Tuple]:
        """Search questions for editing with topic information."""
        try:
            query = f'''
                SELECT q.id, s.subtopic_name as topic, q.question_text as question, 
                       q.correct_answer as answer, q.explanation
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                WHERE LOWER(q.question_text) LIKE {self._get_placeholder(1)}
                ORDER BY s.subtopic_name, q.id
                LIMIT {self._get_placeholder(2)}
            '''
            
            search_pattern = f"%{search_term.lower()}%"
            results = self.fetch_all(query, (search_pattern, limit))
            
            # Convert to tuples for compatibility
            return [(r['id'], r['topic'], r['question'], r['answer'], r['explanation']) for r in results]
            
        except Exception as e:
            logger.error(f"Error searching questions for edit: {e}")
            return []
    
    def search_questions_for_deletion(self, search_term: str, limit: int = 10) -> List[Tuple]:
        """Search questions for deletion."""
        try:
            query = f'''
                SELECT q.id, s.subtopic_name as topic, q.question_text as question
                FROM questions q
                JOIN subtopics s ON q.topic_id = s.id
                WHERE LOWER(q.question_text) LIKE {self._get_placeholder(1)}
                ORDER BY s.subtopic_name, q.id
                LIMIT {self._get_placeholder(2)}
            '''
            
            search_pattern = f"%{search_term.lower()}%"
            results = self.fetch_all(query, (search_pattern, limit))
            
            # Convert to tuples for compatibility
            return [(r['id'], r['topic'], r['question']) for r in results]
            
        except Exception as e:
            logger.error(f"Error searching questions for deletion: {e}")
            return []
    
    def get_topics_for_editing(self) -> List[Tuple]:
        """Get topics for editing with IDs and names."""
        try:
            query = f'''
                SELECT s.id, s.subtopic_name as name, mt.topic_name as main_topic
                FROM subtopics s
                JOIN main_topics mt ON s.main_topic_id = mt.id
                WHERE s.is_active = {self._get_placeholder(1)} AND mt.is_active = {self._get_placeholder(2)}
                ORDER BY mt.topic_name, s.subtopic_name
            '''
            
            results = self.fetch_all(query, (self._get_boolean_value(True), self._get_boolean_value(True)))
            
            # Convert to tuples for compatibility
            return [(r['id'], r['name'], r['main_topic']) for r in results]
            
        except Exception as e:
            logger.error(f"Error getting topics for editing: {e}")
            return []
    
    def get_topic_name_by_id_for_edit(self, topic_id: int) -> Optional[str]:
        """Get topic name by ID for editing operations."""
        try:
            query = f'SELECT subtopic_name FROM subtopics WHERE id = {self._get_placeholder(1)}'
            return self.fetch_val(query, (topic_id,))
            
        except Exception as e:
            logger.error(f"Error getting topic name by ID {topic_id}: {e}")
            return None
    
    def update_question_in_database(self, question_id: int, field: str, value: str) -> bool:
        """Generic method to update any question field."""
        try:
            # Map field names to database columns
            field_mapping = {
                'question': 'question_text',
                'answer': 'correct_answer',
                'explanation': 'explanation',
                'topic_id': 'topic_id'
            }
            
            db_field = field_mapping.get(field, field)
            
            query = f'''
                UPDATE questions 
                SET {db_field} = {self._get_placeholder(1)}
                WHERE id = {self._get_placeholder(2)}
            '''
            
            self.execute_query(query, (value, question_id))
            logger.info(f"Updated {field} for question {question_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating question {question_id} field {field}: {e}")
            return False
    
    def get_questions_for_explanation_improvement(self, improvement_type: str, limit: int = 50) -> List[Tuple]:
        """Get questions that need explanation improvement."""
        try:
            if improvement_type == "short":
                query = f'''
                    SELECT q.id, q.question_text, q.correct_answer, q.explanation, s.subtopic_name as topic
                    FROM questions q
                    JOIN subtopics s ON q.topic_id = s.id
                    WHERE LENGTH(q.explanation) < 100
                    ORDER BY q.id
                    LIMIT {self._get_placeholder(1)}
                '''
                params = (limit,)
            elif improvement_type == "no_steps":
                query = f'''
                    SELECT q.id, q.question_text, q.correct_answer, q.explanation, s.subtopic_name as topic
                    FROM questions q
                    JOIN subtopics s ON q.topic_id = s.id
                    WHERE q.explanation NOT LIKE '%Шаг%' 
                    AND q.explanation NOT LIKE '%шаг%'
                    AND q.explanation NOT LIKE '%қадам%'
                    AND q.explanation NOT LIKE '%ҚАДАМ%'
                    ORDER BY q.id
                    LIMIT {self._get_placeholder(1)}
                '''
                params = (limit,)
            else:  # all
                query = f'''
                    SELECT q.id, q.question_text, q.correct_answer, q.explanation, s.subtopic_name as topic
                    FROM questions q
                    JOIN subtopics s ON q.topic_id = s.id
                    ORDER BY q.id
                    LIMIT {self._get_placeholder(1)}
                '''
                params = (limit,)
            
            results = self.fetch_all(query, params)
            
            # Convert to tuples for compatibility
            return [(r['id'], r['question_text'], r['correct_answer'], r['explanation'], r['topic']) for r in results]
            
        except Exception as e:
            logger.error(f"Error getting questions for explanation improvement: {e}")
            return []
    
    def get_explanation_improvement_stats(self) -> Dict[str, int]:
        """Get statistics for explanation improvement."""
        try:
            stats = {}
            
            # Total questions
            total_query = 'SELECT COUNT(*) FROM questions'
            stats['total_questions'] = self.fetch_val(total_query) or 0
            
            # Short explanations
            short_query = 'SELECT COUNT(*) FROM questions WHERE LENGTH(explanation) < 100'
            stats['short_explanations'] = self.fetch_val(short_query) or 0
            
            # No steps
            no_steps_query = '''
                SELECT COUNT(*) FROM questions 
                WHERE explanation NOT LIKE '%Шаг%' 
                AND explanation NOT LIKE '%шаг%'
                AND explanation NOT LIKE '%қадам%'
                AND explanation NOT LIKE '%ҚАДАМ%'
            '''
            stats['no_steps'] = self.fetch_val(no_steps_query) or 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting explanation improvement stats: {e}")
            return {'total_questions': 0, 'short_explanations': 0, 'no_steps': 0} 