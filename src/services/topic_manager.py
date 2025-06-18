import logging
from typing import List, Dict, Optional
from difflib import SequenceMatcher
from services.database import get_database_instance
from services.ai_service import AIService

logger = logging.getLogger(__name__)

class TopicManager:
    """Сервис для управления темами."""
    
    def __init__(self):
        self.db = get_database_instance()
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
                    LEFT JOIN questions q ON st.id = q.topic_id
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
                    LEFT JOIN questions q ON st.id = q.topic_id
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
                
                # Получаем topic_id для обеих тем
                cursor.execute('SELECT id FROM subtopics WHERE name = ?', (source_topic,))
                source_result = cursor.fetchone()
                if not source_result:
                    logging.error(f"Source topic '{source_topic}' not found")
                    return False
                source_id = source_result[0]
                
                cursor.execute('SELECT id FROM subtopics WHERE name = ?', (target_topic,))
                target_result = cursor.fetchone()
                if not target_result:
                    logging.error(f"Target topic '{target_topic}' not found")
                    return False
                target_id = target_result[0]
                
                # Перемещаем все вопросы с source_topic_id на target_topic_id
                cursor.execute(
                    'UPDATE questions SET topic_id = ? WHERE topic_id = ?',
                    (target_id, source_id)
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
                    LEFT JOIN questions q ON st.id = q.topic_id
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
    
    def ensure_topic_exists(self, original_topic: str, sample_question: str = None) -> str:
        """
        Обеспечить существование темы с AI-анализом содержания вопроса.
        
        Args:
            original_topic: Исходное название темы из PDF
            sample_question: Пример вопроса для анализа содержания
            
        Returns:
            Нормализованное название темы
        """
        try:
            # Шаг 1: AI анализ содержания вопроса (если предоставлен)
            if sample_question and len(sample_question.strip()) > 10:
                try:
                    normalized_topic = self._normalize_topic_with_ai(original_topic, sample_question)
                    if normalized_topic and normalized_topic != original_topic:
                        logger.info(f"AI нормализация: '{original_topic}' → '{normalized_topic}'")
                        original_topic = normalized_topic
                except Exception as e:
                    logger.warning(f"AI анализ не удался, используем резервную логику: {e}")
            
            # Шаг 2: Поиск похожих существующих тем
            existing_topics = self.get_available_topics()
            
            # Точное совпадение
            if original_topic in existing_topics:
                return original_topic
            
            # Поиск похожих тем
            similar_topic = self._find_similar_topic(original_topic, existing_topics)
            if similar_topic:
                logger.info(f"Найдена похожая тема: '{original_topic}' → '{similar_topic}'")
                return similar_topic
            
            # Шаг 3: Создание новой темы если не найдена
            success = self.create_topic_if_not_exists(original_topic)
            if success:
                logger.info(f"Создана новая тема: '{original_topic}'")
                return original_topic
            else:
                # Fallback к первой доступной теме
                if existing_topics:
                    fallback_topic = existing_topics[0]
                    logger.warning(f"Не удалось создать тему '{original_topic}', используем fallback: '{fallback_topic}'")
                    return fallback_topic
                else:
                    logger.error("Нет доступных тем и не удалось создать новую")
                    return "Математика"  # Базовая тема по умолчанию
                    
        except Exception as e:
            logger.error(f"Ошибка в ensure_topic_exists: {e}")
            # Возвращаем первую доступную тему или базовую
            existing_topics = self.get_available_topics()
            return existing_topics[0] if existing_topics else "Математика"

    def _normalize_topic_with_ai(self, original_topic: str, sample_question: str) -> Optional[str]:
        """
        Нормализация темы с помощью AI на основе содержания вопроса.
        
        Args:
            original_topic: Исходное название темы
            sample_question: Пример вопроса для анализа
            
        Returns:
            Нормализованное название темы или None при ошибке
        """
        try:
            # Получаем список доступных тем для контекста
            available_topics = self.get_available_topics()
            topics_list = "\n".join([f"- {topic}" for topic in available_topics[:20]])  # Ограничиваем для промпта
            
            prompt = f"""
Проанализируй математический вопрос и определи наиболее подходящую тему из существующих.

ВОПРОС: {sample_question}

ИСХОДНАЯ ТЕМА ИЗ PDF: {original_topic}

ДОСТУПНЫЕ ТЕМЫ В СИСТЕМЕ:
{topics_list}

ЗАДАЧА:
1. Проанализируй СОДЕРЖАНИЕ вопроса (какие математические операции, понятия используются)
2. Определи наиболее подходящую тему из списка доступных тем
3. Игнорируй широкие названия типа "Арифметика - Дроби, проценты, уравнения"
4. Фокусируйся на конкретном содержании вопроса

ПРИМЕРЫ:
- Вопрос "2,46 × 18 =" + тема "Арифметика - Дроби, проценты, уравнения" → "Десятичные дроби"
- Вопрос "Найдите 25% от 80" + тема "Математические задачи" → "Нахождение процента от числа"
- Вопрос "x + 15 = 23" + тема "Школьная программа" → "Простейшие уравнения"

ОТВЕТ (только название темы без объяснений):
"""
            
            response = self.ai_service.get_completion(prompt)
            if response and response.strip():
                normalized = response.strip()
                # Проверяем, что ответ является одной из доступных тем
                if normalized in available_topics:
                    return normalized
                else:
                    # Ищем наиболее похожую тему
                    return self._find_similar_topic(normalized, available_topics)
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка AI нормализации темы: {e}")
            return None

    def _find_similar_topic(self, query: str, available_topics: List[str], threshold: float = 0.6) -> Optional[str]:
        """
        Найти наиболее похожую тему из доступных.
        
        Args:
            query: Запрос для поиска
            available_topics: Список доступных тем
            threshold: Минимальный порог схожести
            
        Returns:
            Наиболее похожая тема или None
        """
        try:
            if not available_topics:
                return None
            
            best_match = None
            best_score = 0
            
            query_lower = query.lower()
            
            # Точное совпадение
            for topic in available_topics:
                if query_lower == topic.lower():
                    return topic
            
            # Поиск по вхождению ключевых слов
            for topic in available_topics:
                topic_lower = topic.lower()
                
                # Проверяем вхождение слов из запроса в название темы
                query_words = [word for word in query_lower.split() if len(word) > 2]
                topic_words = [word for word in topic_lower.split() if len(word) > 2]
                
                # Считаем количество совпадающих слов
                matches = sum(1 for word in query_words if any(word in topic_word or topic_word in word for topic_word in topic_words))
                
                if matches > 0:
                    score = matches / max(len(query_words), len(topic_words))
                    if score > best_score and score >= threshold:
                        best_score = score
                        best_match = topic
            
            # Если не найдено по словам, используем SequenceMatcher
            if not best_match:
                for topic in available_topics:
                    score = SequenceMatcher(None, query_lower, topic.lower()).ratio()
                    if score > best_score and score >= threshold:
                        best_score = score
                        best_match = topic
            
            return best_match
            
        except Exception as e:
            logger.error(f"Ошибка при поиске похожей темы: {e}")
            return None

    def get_topic_by_content(self, question_text: str) -> str:
        """
        Определить тему по содержанию вопроса (для совместимости).
        Использует ensure_topic_exists с анализом содержания.
        """
        try:
            # Пытаемся определить тему по содержанию
            detected_topic = self.get_topic_by_similarity(question_text)
            if detected_topic:
                return detected_topic
            
            # Используем ensure_topic_exists с базовой темой
            return self.ensure_topic_exists("Математика", question_text)
            
        except Exception as e:
            logger.error(f"Ошибка при определении темы по содержанию: {e}")
            # Возвращаем первую доступную тему или базовую
            available_topics = self.get_available_topics()
            return available_topics[0] if available_topics else "Математика" 