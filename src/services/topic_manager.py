import logging
import sqlite3
from typing import List, Dict, Optional
from difflib import SequenceMatcher
from services.database import Database
from services.ai_service import AIService
from config.constants import TOPIC_HIERARCHY

logger = logging.getLogger(__name__)

class TopicManager:
    """Сервис для управления темами."""
    
    def __init__(self):
        self.db = Database()
        self.ai_service = AIService()
        
        # Базовые темы для подготовки к НИШ (5-6 классы)
        self.base_topics = [
            # Арифметика и числа
            "Натуральные числа",
            "Чётные и нечётные числа", 
            "Делимость чисел",
            "Простые и составные числа",
            "НОК и НОД",
            "Сравнение и округление чисел",
            
            # Операции с числами
            "Арифметические операции",
            "Порядок действий",
            "Деление с остатком",
            "Свойства операций",
            
            # Дроби
            "Обыкновенные дроби",
            "Десятичные дроби",
            "Сравнение дробей",
            "Действия с дробями",
            
            # Проценты
            "Проценты",
            "Нахождение процента от числа",
            "Нахождение числа по проценту",
            
            # Уравнения и выражения
            "Простейшие уравнения",
            "Арифметические выражения",
            "Составление уравнений",
            
            # Логика и закономерности
            "Числовые последовательности",
            "Логические задачи",
            "Задачи на смекалку",
            
            # Геометрия
            "Геометрические фигуры",
            "Периметр и площадь",
            "Углы",
            "Координатная плоскость",
            
            # Единицы измерения
            "Единицы времени",
            "Единицы длины и массы",
            "Перевод единиц",
            "Масштаб и расстояние",
            
            # Работа с данными
            "Таблицы и диаграммы",
            "Анализ графиков",
            
            # Практические задачи
            "Задачи на практическое мышление",
            "Оптимизация",
            "Распределение по условиям"
        ]
    
    def find_best_topic_match(self, query: str, threshold: float = 0.6) -> Optional[str]:
        """Найти наиболее подходящую тему по запросу."""
        try:
            # Получаем активные темы из нормализованной структуры
            available_topics = self.db.get_topic_names(active_only=True)
            
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
            # Получаем активные темы
            available_topics = self.db.get_topic_names(active_only=True)
            
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
            return self.db.add_topic(topic_name, main_topic_name=main_topic_name)
            
        except Exception as e:
            logging.error(f"Ошибка при создании темы: {e}")
            return False
    
    def get_available_topics(self) -> List[str]:
        """Получить список доступных тем."""
        return self.db.get_topic_names(active_only=True)
    
    def get_topics_with_questions_count(self) -> List[Dict]:
        """Получить темы с количеством вопросов."""
        try:
            topics = self.db.get_all_topics(active_only=True)
            result = []
            
            for topic in topics:
                # Считаем вопросы для каждой темы
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT COUNT(*) FROM questions WHERE topic = ?',
                        (topic['name'],)
                    )
                    question_count = cursor.fetchone()[0]
                
                result.append({
                    'id': topic['id'],
                    'name': topic['name'],
                    'main_topic': topic['main_topic'],
                    'question_count': question_count,
                    'is_active': topic['is_active']
                })
            
            return result
            
        except Exception as e:
            logging.error(f"Ошибка при получении тем с количеством вопросов: {e}")
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
            
            logging.info(f"Темы объединены: '{source_topic}' -> '{target_topic}'")
            return True
            
        except Exception as e:
            logging.error(f"Ошибка при объединении тем: {e}")
            return False
    
    def get_topic_statistics(self) -> Dict[str, Dict]:
        """Возвращает статистику по темам."""
        try:
            topics = self.db.get_all_topics(active_only=False)
            stats = {}
            
            for topic in topics:
                topic_name = topic['name']
                
                # Считаем количество вопросов
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT COUNT(*) FROM questions WHERE topic = ?',
                        (topic_name,)
                    )
                    question_count = cursor.fetchone()[0]
                
                stats[topic_name] = {
                    'id': topic['id'],
                    'main_topic': topic['main_topic'],
                    'is_active': topic['is_active'],
                    'question_count': question_count,
                    'created_at': topic['created_at']
                }
            
            return stats
            
        except Exception as e:
            logging.error(f"Ошибка при получении статистики тем: {e}")
            return {} 