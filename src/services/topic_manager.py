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
            "Поиск закономерностей",
            
            # Геометрия
            "Геометрические фигуры",
            "Периметр и площадь",
            "Углы",
            "Координатная плоскость",
            
            # Единицы измерения
            "Единицы времени",
            "Единицы длины и массы",
            "Перевод единиц",
            
            # Работа с данными
            "Таблицы и диаграммы",
            "Анализ графиков",
            
            # Практические задачи
            "Задачи на практическое мышление",
            "Оптимизация",
            "Распределение по условиям"
        ]
    
    def ensure_topic_exists(self, topic_name: str, description: str = None, sample_question: str = None) -> str:
        """
        Убеждается, что тема существует в базе данных.
        Если темы нет - создает её.
        Возвращает нормализованное название темы.
        
        Args:
            topic_name: Название темы из PDF
            description: Описание темы (опционально)
            sample_question: Пример вопроса из этой темы для лучшего анализа
        """
        if not topic_name or not topic_name.strip():
            return "Математика"
        
        topic_name = topic_name.strip()
        
        # Проверяем, существует ли тема
        existing_topics = self.db.get_all_topics(active_only=False)
        existing_names = [t['name'] for t in existing_topics]
        
        # Если тема уже существует
        if topic_name in existing_names:
            return topic_name
        
        # Ищем похожую тему
        similar_topic = self._find_similar_topic(topic_name, existing_names)
        if similar_topic:
            logging.info(f"Используем существующую похожую тему '{similar_topic}' для '{topic_name}'")
            return similar_topic
        
        # Нормализуем название темы с помощью AI (передаем пример вопроса)
        normalized_name = self._normalize_topic_with_ai(topic_name, sample_question)
        
        # Проверяем еще раз после нормализации
        if normalized_name in existing_names:
            return normalized_name
        
        # Создаем новую тему только если AI действительно предложил уникальное название
        description = description or f"Тема: {normalized_name}"
        success = self.db.add_topic(normalized_name, description)
        
        if success:
            logging.info(f"Создана новая тема: '{normalized_name}' (исходное название: '{topic_name}')")
            return normalized_name
        else:
            logging.warning(f"Не удалось создать тему '{normalized_name}', используем 'Математика'")
            return "Математика"
    
    def _find_similar_topic(self, topic_name: str, existing_names: List[str]) -> Optional[str]:
        """Ищет похожую тему среди существующих."""
        topic_lower = topic_name.lower()
        
        # Словарь синонимов и сокращений для тем НИШ
        synonyms = {
            'натуральные числа': ['натуральн', 'числ', 'цифр'],
            'чётные и нечётные числа': ['чётн', 'нечётн', 'парн', 'непарн'],
            'делимость чисел': ['делимост', 'делител', 'кратн', 'остаток'],
            'простые и составные числа': ['прост', 'составн', 'разложен'],
            'нок и нод': ['нок', 'нод', 'общий кратн', 'общий делител'],
            'сравнение и округление чисел': ['сравнен', 'округлен', 'больш', 'меньш'],
            
            'арифметические операции': ['арифметик', 'сложен', 'вычитан', 'умножен', 'делен'],
            'порядок действий': ['порядок', 'скобк', 'приоритет'],
            'деление с остатком': ['остаток', 'нацело'],
            'свойства операций': ['свойств', 'переместительн', 'сочетательн', 'распределительн'],
            
            'обыкновенные дроби': ['обыкновенн', 'дроб', 'числител', 'знаменател'],
            'десятичные дроби': ['десятичн', 'запят'],
            'сравнение дробей': ['сравнен дроб'],
            'действия с дробями': ['действи', 'операци', 'дроб'],
            
            'проценты': ['процент', '%'],
            'нахождение процента от числа': ['процент от числ', 'найти процент'],
            'нахождение числа по проценту': ['числ по процент', 'обратн'],
            
            'простейшие уравнения': ['уравнен', 'неизвестн', 'x', 'y'],
            'арифметические выражения': ['выражен', 'вычислен'],
            'составление уравнений': ['составлен', 'задач'],
            
            'числовые последовательности': ['последовательност', 'ряд', 'прогресси'],
            'логические задачи': ['логик', 'логическ', 'рассуждени'],
            'поиск закономерностей': ['закономерност', 'правил', 'паттерн'],
            
            'геометрические фигуры': ['геометр', 'фигур', 'треугольник', 'квадрат', 'прямоугольник', 'круг'],
            'периметр и площадь': ['периметр', 'площад'],
            'углы': ['угол', 'градус'],
            'координатная плоскость': ['координат', 'плоскост', 'ось'],
            
            'единицы времени': ['врем', 'час', 'минут', 'секунд'],
            'единицы длины и массы': ['длин', 'масс', 'метр', 'килограмм', 'грамм'],
            'перевод единиц': ['перевод', 'единиц', 'измерен'],
            
            'таблицы и диаграммы': ['таблиц', 'диаграмм', 'данн'],
            'анализ графиков': ['график', 'анализ'],
            
            'задачи на практическое мышление': ['практическ', 'реальн', 'жизненн'],
            'оптимизация': ['оптимизаци', 'минимальн', 'максимальн'],
            'распределение по условиям': ['распределен', 'групп', 'условия']
        }
        
        # Проверяем прямые совпадения
        for existing in existing_names:
            if topic_lower in existing.lower() or existing.lower() in topic_lower:
                return existing
        
        # Проверяем синонимы
        for base_topic, keywords in synonyms.items():
            for keyword in keywords:
                if keyword in topic_lower:
                    # Ищем соответствующую тему в базе
                    for existing in existing_names:
                        if base_topic in existing.lower():
                            return existing
        
        return None
    
    def _normalize_topic_with_ai(self, topic_name: str, sample_question: str = None) -> str:
        """
        Использует ИИ для определения правильной темы на основе содержания вопроса
        """
        try:
            # Создаем структурированный список тем для ИИ
            topic_list = []
            for category, topics in TOPIC_HIERARCHY.items():
                for topic in topics:
                    topic_list.append(f"- {topic}")
            
            topics_text = "\n".join(topic_list)
            
            prompt = f"""Проанализируй математический вопрос и определи наиболее подходящую тему из списка.

ДОСТУПНЫЕ ТЕМЫ:
{topics_text}

ПРАВИЛА КЛАССИФИКАЦИИ:
1. Анализируй СОДЕРЖАНИЕ вопроса, а не только название темы
2. Обращай внимание на тип математических операций в вопросе
3. Учитывай специфические ключевые слова и формулировки

СПЕЦИАЛЬНЫЕ ПРАВИЛА:
- Если вопрос содержит ДЕСЯТИЧНЫЕ ЧИСЛА (с запятой: 2,5; 3,14; 0,25) и арифметические операции → "Десятичные дроби"
- Если вопрос содержит "Найдите X% от числа" или "Вычислите X% от Y" → "Нахождение процента от числа"  
- Если вопрос содержит "X% от какого числа равны Y" → "Нахождение числа по проценту"
- Если вопрос содержит пропорцию (a:b = c:x) → "Простейшие уравнения"
- Если вопрос содержит обыкновенные дроби (3/4, 1/2) и операции → "Действия с дробями"
- Если вопрос содержит "Решите уравнение" или "Найдите x" → "Простейшие уравнения"
- Если вопрос содержит сложные арифметические выражения с порядком действий → "Порядок действий"
- Если вопрос содержит "остаток от деления" → "Деление с остатком"
- Если вопрос содержит "Сравните дроби" → "Сравнение дробей"
- Если вопрос содержит "натуральные числа" → "Натуральные числа"

ПРИМЕРЫ:
- "2,46 × 18 =" → "Десятичные дроби" (содержит десятичное число)
- "Вычислите: 2,5 × 1,4" → "Десятичные дроби" (операции с десятичными числами)
- "Найдите 25% от 80" → "Нахождение процента от числа"
- "25% от какого числа равны 15?" → "Нахождение числа по проценту"
- "Найдите x в пропорции 2:3 = x:12" → "Простейшие уравнения"
- "Вычислите: 3/4 + 1/2" → "Действия с дробями"
- "38,3 − 24,16 : 4 + 3,78 × 3 = ?" → "Порядок действий"

ВХОДНЫЕ ДАННЫЕ:
Название темы из PDF: "{topic_name}"
Пример вопроса: "{sample_question}"

Верни ТОЛЬКО название темы из списка, которая наиболее точно соответствует содержанию вопроса."""

            response = self.ai_service.model.generate_content(prompt)
            
            if response and response.text and response.text.strip():
                normalized_topic = response.text.strip()
                
                # Проверяем, что тема существует в нашем списке
                all_topics = []
                for topics in TOPIC_HIERARCHY.values():
                    all_topics.extend(topics)
                
                if normalized_topic in all_topics:
                    logger.info(f"AI нормализовал тему '{topic_name}' -> '{normalized_topic}' на основе вопроса")
                    return normalized_topic
                else:
                    logger.warning(f"AI вернул неизвестную тему: {normalized_topic}")
                    return self._find_similar_topic(topic_name, all_topics) or topic_name
            else:
                logger.warning("AI не вернул ответ для нормализации темы")
                return topic_name
                
        except Exception as e:
            logger.error(f"Ошибка при нормализации темы с AI: {e}")
            return topic_name
    
    def get_topic_by_content(self, question_text: str) -> str:
        """Определяет тему по содержанию вопроса."""
        try:
            existing_topics = self.db.get_all_topics(active_only=True)
            topic_names = [t['name'] for t in existing_topics]
            
            if not topic_names:
                return "Математика"
            
            prompt = f"""
Вопрос: "{question_text}"

Доступные темы:
{chr(10).join(topic_names)}

Определи наиболее подходящую тему для этого вопроса из списка выше.
Ответь только названием темы из списка.
"""
            
            response = self.ai_service.model.generate_content(prompt)
            suggested_topic = response.text.strip()
            
            # Проверяем, что предложенная тема есть в списке
            if suggested_topic in topic_names:
                return suggested_topic
            
            # Ищем частичное совпадение
            for topic in topic_names:
                if suggested_topic.lower() in topic.lower() or topic.lower() in suggested_topic.lower():
                    return topic
            
            # Если ничего не найдено, возвращаем первую тему или создаем новую
            return topic_names[0] if topic_names else "Математика"
            
        except Exception as e:
            logging.error(f"Ошибка при определении темы по содержанию: {e}")
            return "Математика"
    
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
                    'UPDATE topics SET is_active = 0 WHERE id = ?',
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
                    'is_active': topic['is_active'],
                    'question_count': question_count,
                    'created_at': topic['created_at']
                }
            
            return stats
            
        except Exception as e:
            logging.error(f"Ошибка при получении статистики тем: {e}")
            return {} 