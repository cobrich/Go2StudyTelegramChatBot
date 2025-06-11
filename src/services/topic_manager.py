import logging
from typing import List, Dict, Optional
from difflib import SequenceMatcher
from services.database import Database
from services.ai_service import AIService

logger = logging.getLogger(__name__)

class TopicManager:
    """Сервис для управления темами."""
    
    def __init__(self):
        self.db = Database()
        self.ai_service = AIService()
        # Кэш для часто используемых данных
        self._topics_cache = None
        self._structure_cache = None
    
    def _invalidate_cache(self):
        """Сбросить кэш при изменении данных."""
        self._topics_cache = None
        self._structure_cache = None
    
    def get_base_topic_structure(self) -> Dict[str, List[str]]:
        """Получить базовую структуру тем с кэшированием."""
        if self._structure_cache is None:
            self._structure_cache = self.db.get_base_topic_structure()
        return self._structure_cache
    
    def get_available_topics(self) -> List[str]:
        """Получить список доступных тем с кэшированием."""
        if self._topics_cache is None:
            self._topics_cache = self.db.get_topic_names(active_only=True)
        return self._topics_cache
    
    def find_best_topic_match(self, query: str, threshold: float = 0.6) -> Optional[str]:
        """Найти наиболее подходящую тему по запросу."""
        try:
            available_topics = self.get_available_topics()
            
            if not available_topics:
                return None
            
            best_match = None
            best_score = 0
            
            # Ищем по названиям тем
            for topic in available_topics:
                score = SequenceMatcher(None, query.lower(), topic.lower()).ratio()
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = topic
            
            # Если точного совпадения нет, ищем по ключевым словам
            if not best_match:
                for topic in available_topics:
                    if any(word.lower() in topic.lower() for word in query.split() if len(word) > 2):
                        return topic
            
            return best_match
            
        except Exception as e:
            logging.error(f"Ошибка при поиске темы: {e}")
            return None
    
    def get_topic_by_similarity(self, question_text: str) -> Optional[str]:
        """Определить тему по содержанию вопроса."""
        try:
            available_topics = self.get_available_topics()
            
            if not available_topics:
                return None
            
            # Ключевые слова для определения тем
            topic_keywords = {
                "дроби": ["дроб", "числит", "знамен", "сократ", "общий"],
                "проценты": ["процент", "%", "скидк", "наценк"],
                "уравнения": ["уравнен", "неизвестн", "найд", "x", "y"],
                "геометрия": ["треуголь", "квадрат", "круг", "периметр", "площад", "угол"],
                "арифметика": ["сложен", "вычитан", "умножен", "делен", "+", "-", "*", "/"],
                "время": ["час", "минут", "секунд", "время", "дат"],
                "длина": ["метр", "сантиметр", "километр", "расстоян"],
                "масса": ["килограмм", "грамм", "тонн", "вес"]
            }
            
            question_lower = question_text.lower()
            
            # Проверяем ключевые слова
            for topic_type, keywords in topic_keywords.items():
                if any(keyword in question_lower for keyword in keywords):
                    # Ищем подходящую тему в доступных
                    for topic in available_topics:
                        if topic_type in topic.lower():
                            return topic
            
            # Если не найдено по ключевым словам, возвращаем первую доступную
            return available_topics[0] if available_topics else None
            
        except Exception as e:
            logging.error(f"Ошибка при определении темы: {e}")
            return None
    
    def suggest_topics_for_questions(self, questions: List[Dict]) -> Dict[str, List[Dict]]:
        """Предложить распределение вопросов по темам."""
        try:
            topic_suggestions = {}
            
            for question in questions:
                suggested_topic = self.get_topic_by_similarity(question.get('question', ''))
                
                if suggested_topic:
                    if suggested_topic not in topic_suggestions:
                        topic_suggestions[suggested_topic] = []
                    topic_suggestions[suggested_topic].append(question)
                else:
                    # Добавляем в категорию "неопределенные"
                    if "Неопределенные" not in topic_suggestions:
                        topic_suggestions["Неопределенные"] = []
                    topic_suggestions["Неопределенные"].append(question)
            
            return topic_suggestions
            
        except Exception as e:
            logging.error(f"Ошибка при предложении тем: {e}")
            return {}
    
    def create_topic_if_not_exists(self, topic_name: str, main_topic_name: str = None) -> bool:
        """Создать тему если она не существует."""
        try:
            # Проверяем, существует ли тема
            existing_topics = self.db.get_topic_names(active_only=False)
            
            if topic_name in existing_topics:
                return True
            
            # Создаем новую тему в указанном разделе или в первом доступном
            success = self.db.add_topic(topic_name, main_topic_name=main_topic_name)
            
            if success:
                # Сбрасываем кэш после добавления
                self._invalidate_cache()
            
            return success
            
        except Exception as e:
            logging.error(f"Ошибка при создании темы: {e}")
            return False
    
    def get_topics_with_questions_count(self) -> List[Dict]:
        """Получить темы с количеством вопросов (оптимизированная версия)."""
        try:
            # Получаем все данные одним запросом
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        st.id,
                        st.name,
                        mt.name as main_topic,
                        st.is_active,
                        st.created_at,
                        COUNT(q.id) as question_count
                    FROM subtopics st
                    JOIN main_topics mt ON st.main_topic_id = mt.id
                    LEFT JOIN questions q ON st.name = q.topic
                    WHERE st.is_active = 1 AND mt.is_active = 1
                    GROUP BY st.id, st.name, mt.name, st.is_active, st.created_at
                    ORDER BY mt.order_index, st.order_index
                ''')
                
                results = cursor.fetchall()
                return [
                    {
                        'id': row[0],
                        'name': row[1],
                        'main_topic': row[2],
                        'is_active': bool(row[3]),
                        'created_at': row[4],
                        'question_count': row[5]
                    }
                    for row in results
                ]
            
        except Exception as e:
            logging.error(f"Ошибка при получении тем с количеством вопросов: {e}")
            return []
    
    def get_main_topics_with_stats(self) -> List[Dict]:
        """Получить статистику по основным разделам."""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        mt.id,
                        mt.name,
                        mt.order_index,
                        COUNT(st.id) as subtopics_count,
                        COUNT(q.id) as total_questions
                    FROM main_topics mt
                    LEFT JOIN subtopics st ON mt.id = st.main_topic_id AND st.is_active = 1
                    LEFT JOIN questions q ON st.name = q.topic
                    WHERE mt.is_active = 1
                    GROUP BY mt.id, mt.name, mt.order_index
                    ORDER BY mt.order_index
                ''')
                
                results = cursor.fetchall()
                return [
                    {
                        'id': row[0],
                        'name': row[1],
                        'order_index': row[2],
                        'subtopics_count': row[3],
                        'total_questions': row[4]
                    }
                    for row in results
                ]
            
        except Exception as e:
            logging.error(f"Ошибка при получении статистики основных разделов: {e}")
            return []
    
    def merge_topics(self, source_topic: str, target_topic: str) -> bool:
        """Объединяет две темы (перемещает все вопросы из source в target)."""
        try:
            # Получаем ID тем
            topics = self.db.get_all_topics(active_only=False)
            source_id = None
            target_id = None
            
            for topic in topics:
                if topic['name'] == source_topic:
                    source_id = topic['id']
                elif topic['name'] == target_topic:
                    target_id = topic['id']
            
            if not source_id or not target_id:
                return False
            
            # Перемещаем все вопросы
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE questions SET topic = ? WHERE topic = ?',
                    (target_topic, source_topic)
                )
                
                # Деактивируем исходную тему
                cursor.execute(
                    'UPDATE subtopics SET is_active = 0 WHERE id = ?',
                    (source_id,)
                )
                
                conn.commit()
            
            # Сбрасываем кэш после изменений
            self._invalidate_cache()
            
            logging.info(f"Темы объединены: '{source_topic}' -> '{target_topic}'")
            return True
            
        except Exception as e:
            logging.error(f"Ошибка при объединении тем: {e}")
            return False
    
    def get_topic_statistics(self) -> Dict[str, Dict]:
        """Возвращает статистику по темам (оптимизированная версия)."""
        try:
            # Получаем все данные одним запросом
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        st.name,
                        st.id,
                        mt.name as main_topic,
                        st.is_active,
                        st.created_at,
                        COUNT(q.id) as question_count
                    FROM subtopics st
                    JOIN main_topics mt ON st.main_topic_id = mt.id
                    LEFT JOIN questions q ON st.name = q.topic
                    GROUP BY st.id, st.name, mt.name, st.is_active, st.created_at
                    ORDER BY mt.order_index, st.order_index
                ''')
                
                results = cursor.fetchall()
                stats = {}
                
                for row in results:
                    topic_name = row[0]
                    stats[topic_name] = {
                        'id': row[1],
                        'main_topic': row[2],
                        'is_active': bool(row[3]),
                        'created_at': row[4],
                        'question_count': row[5]
                    }
                
                return stats
            
        except Exception as e:
            logging.error(f"Ошибка при получении статистики тем: {e}")
            return {}
    
    def add_main_topic_section(self, main_topic_name: str, subtopics: List[str]) -> bool:
        """Добавить новый основной раздел с подтемами."""
        try:
            success = self.db.add_base_topic_section(main_topic_name, subtopics)
            if success:
                self._invalidate_cache()
            return success
        except Exception as e:
            logging.error(f"Ошибка при добавлении раздела: {e}")
            return False
    
    def update_main_topic_section(self, old_name: str, new_name: str = None, new_subtopics: List[str] = None) -> bool:
        """Обновить основной раздел."""
        try:
            success = self.db.update_base_topic_section(old_name, new_name, new_subtopics)
            if success:
                self._invalidate_cache()
            return success
        except Exception as e:
            logging.error(f"Ошибка при обновлении раздела: {e}")
            return False
    
    def delete_main_topic_section(self, main_topic_name: str, hard_delete: bool = False) -> bool:
        """Удалить основной раздел."""
        try:
            success = self.db.delete_base_topic_section(main_topic_name, hard_delete)
            if success:
                self._invalidate_cache()
            return success
        except Exception as e:
            logging.error(f"Ошибка при удалении раздела: {e}")
            return False 