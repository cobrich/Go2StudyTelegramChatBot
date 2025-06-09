import os
import logging
import fitz  # PyMuPDF
import re
from PIL import Image
from typing import List, Dict, Optional
import sqlite3
import sys

# Добавляем путь к src в PYTHONPATH для корректных импортов
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.database import Database
from src.services.ai_service import AIService

class PDFProcessor:
    def __init__(self, output_dir: str = "question_images"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Паттерн для поиска заголовков тем
        self.topic_header_pattern = r'Тема:\s*([^(]+)\((\d+)\)'
        
        # Паттерн для поиска вопросов
        self.question_pattern = r'^(\d+)\)\s*(.+)'
        
        # Паттерны для поиска вариантов ответов
        self.option_patterns = [
            r'^([A-D])\)\s*(.*?)(\s*✅)?$',  # A) текст ✅ (опционально)
            r'^([А-Г])\)\s*(.*?)(\s*✅)?$',  # А) текст ✅ (опционально)
        ]

    def detect_language(self, text: str) -> str:
        """Определение языка на основе содержимого."""
        kazakh_chars = set('әіңғүұқөһӘІҢҒҮҰҚӨҺ')
        if any(char in text for char in kazakh_chars):
            return 'kk'
        return 'ru'

    def extract_topics_and_questions(self, text: str) -> List[Dict]:
        """Извлечение тем и вопросов из текста PDF."""
        questions = []
        lines = text.split('\n')
        current_topic = None
        current_question = None
        current_options = []
        correct_answer = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Пропускаем пустые строки
            if not line:
                i += 1
                continue
            
            # Проверяем на заголовок темы
            topic_match = re.match(self.topic_header_pattern, line)
            if topic_match:
                current_topic = topic_match.group(1).strip()
                expected_questions = int(topic_match.group(2))
                print(f"[LOG] Найдена тема: '{current_topic}' ({expected_questions} вопросов)")
                i += 1
                continue
            
            # Проверяем на начало вопроса
            question_match = re.match(self.question_pattern, line)
            if question_match:
                # Сохраняем предыдущий вопрос, если он был
                if current_question and current_options and correct_answer:
                    questions.append({
                        'topic': current_topic or 'Математика',
                        'question': current_question,
                        'options': current_options,
                        'correct_answer': correct_answer
                    })
                
                # Начинаем новый вопрос
                question_number = question_match.group(1)
                current_question = question_match.group(2).strip()
                current_options = []
                correct_answer = None
                
                print(f"[LOG] Вопрос {question_number}: {current_question[:50]}...")
                i += 1
                continue
            
            # Проверяем на вариант ответа
            option_found = False
            for pattern in self.option_patterns:
                option_match = re.match(pattern, line)
                if option_match:
                    option_letter = option_match.group(1)
                    option_text = option_match.group(2).strip()
                    has_checkmark = option_match.group(3) is not None
                    
                    # Конвертируем русские буквы в латинские
                    if option_letter in 'АБВГ':
                        option_letter = ['A', 'B', 'C', 'D']['АБВГ'.index(option_letter)]
                    
                    current_options.append(option_text)
                    
                    if has_checkmark:
                        correct_answer = option_letter
                        print(f"[LOG] Правильный ответ: {option_letter}) {option_text}")
                    
                    option_found = True
                    break
            
            if not option_found and current_question:
                # Возможно, это продолжение вопроса
                current_question += " " + line
            
            i += 1
        
        # Сохраняем последний вопрос
        if current_question and current_options and correct_answer:
            questions.append({
                'topic': current_topic or 'Математика',
                'question': current_question,
                'options': current_options,
                'correct_answer': correct_answer
            })
        
        return questions

    def normalize_topic_name(self, topic_name: str) -> str:
        """Нормализация названия темы для соответствия константам."""
        try:
            from config.constants import TOPICS
            
            # Словарь соответствий для нормализации
            topic_mapping = {
                'пропорция': 'Соотношение и пропорция',
                'уравнение': 'Линейные уравнения',
                'уравнения': 'Линейные уравнения',
                'система уравнений': 'Система уравнений',
                'неравенства': 'Равенства и неравенства',
                'неравенство': 'Равенства и неравенства',
                'дроби': 'Операции с дробями и остатками',
                'дробь': 'Операции с дробями и остатками',
                'процент': 'Процент',
                'проценты': 'Процент',
                'геометрия': 'Геометрия',
                'текстовые задачи': 'Текстовые задачи',
                'текстовая задача': 'Текстовые задачи',
                'логика': 'Логические задачи',
                'логические задачи': 'Логические задачи',
                'функция': 'График функции',
                'функции': 'График функции',
                'график': 'График функции',
                'модуль': 'Модуль числа',
                'масштаб': 'Масштаб и расстояние',
                'площадь': 'Площадь и объем',
                'объем': 'Площадь и объем',
                'скорость': 'Скорость и время',
                'время': 'Скорость и время',
                'движение': 'Задачи на движение',
                'работа': 'Задачи на работу',
                'углы': 'Углы',
                'угол': 'Углы'
            }
            
            topic_lower = topic_name.lower().strip()
            
            # Прямое соответствие
            if topic_name in TOPICS:
                return topic_name
            
            # Поиск по словарю соответствий
            for key, value in topic_mapping.items():
                if key in topic_lower:
                    return value
            
            # Поиск частичного совпадения в списке TOPICS
            for topic in TOPICS:
                if topic_lower in topic.lower() or topic.lower() in topic_lower:
                    return topic
            
            # Если ничего не найдено, используем AI для определения
            return self.determine_topic_with_ai(topic_name)
            
        except Exception as e:
            logging.error(f"Ошибка при нормализации темы '{topic_name}': {e}")
            return "Операции с дробями и остатками"  # fallback

    def determine_topic_with_ai(self, topic_name: str) -> str:
        """Определение темы с помощью AI."""
        try:
            from config.constants import TOPICS
            ai_service = AIService()
            
            prompt = f"""
Определи наиболее подходящую тему из списка для темы "{topic_name}":

{', '.join(TOPICS)}

Ответь только названием темы из списка выше. Если не можешь точно определить, ответь "Операции с дробями и остатками".
"""
            
            response = ai_service.model.generate_content(prompt)
            topic = response.text.strip()
            
            # Проверяем, что тема есть в списке
            if topic in TOPICS:
                return topic
            else:
                return "Операции с дробями и остатками"  # fallback
                
        except Exception as e:
            logging.error(f"Ошибка при определении темы с AI: {e}")
            return "Операции с дробями и остатками"  # fallback

    def extract_questions_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Извлечение вопросов из PDF файла."""
        questions = []
        
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            
            # Собираем весь текст из PDF
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                full_text += page_text + "\n"
            
            doc.close()
            
            # Определяем язык
            language = self.detect_language(full_text)
            
            # Извлекаем вопросы
            extracted_questions = self.extract_topics_and_questions(full_text)
            
            # Обрабатываем каждый вопрос
            for q in extracted_questions:
                # Нормализуем тему
                normalized_topic = self.normalize_topic_name(q['topic'])
                
                question_data = {
                    'question': q['question'].strip(),
                    'options': q['options'],
                    'correct_answer': q['correct_answer'],
                    'language': language,
                    'topic': normalized_topic,
                    'source_file': os.path.basename(pdf_path)
                }
                
                if self.validate_question(question_data):
                    questions.append(question_data)
                else:
                    print(f"[SKIP] Невалидный вопрос: {q['question'][:50]}...")
            
            logging.info(f"Извлечено {len(questions)} валидных вопросов из {pdf_path}")
            return questions
            
        except Exception as e:
            logging.error(f"Ошибка при обработке {pdf_path}: {e}")
            return []

    def process_pdf_file(self, pdf_path: str) -> List[Dict]:
        """Обработка PDF файла и извлечение вопросов."""
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
            
            questions = self.extract_questions_from_pdf(pdf_path)
            
            logging.info(f"Обработано {len(questions)} вопросов из {pdf_path}")
            return questions
            
        except Exception as e:
            logging.error(f"Ошибка при обработке {pdf_path}: {e}")
            return []

    def validate_question(self, question: Dict) -> bool:
        """Валидация вопроса."""
        # Проверяем наличие обязательных полей
        if not question.get('question') or not question.get('options'):
            return False
        
        # Проверяем количество вариантов ответов
        if len(question['options']) < 2:
            return False
        
        # Проверяем наличие правильного ответа
        if not question.get('correct_answer'):
            logging.warning(f"Вопрос без правильного ответа: {question['question'][:50]}...")
            return False
        
        # Проверяем, что правильный ответ соответствует одному из вариантов
        correct_index = ord(question['correct_answer']) - ord('A')
        if correct_index >= len(question['options']):
            logging.warning(f"Неверный индекс правильного ответа: {question['correct_answer']} для вопроса: {question['question'][:50]}...")
            return False
        
        return True

def add_questions_to_db(questions: List[Dict], db: Database):
    """Добавление вопросов в базу данных."""
    total = len(questions)
    print(f"[LOG] Начинаю добавление {total} вопросов в базу...")
    saved_count = 0
    
    # Статистика по темам
    topic_stats = {}
    
    with open('added_questions.log', 'a', encoding='utf-8') as logf:
        for idx, q in enumerate(questions, 1):
            question_text = q['question'].strip()
            topic = q.get('topic', 'Операции с дробями и остатками')
            
            # Обновляем статистику
            topic_stats[topic] = topic_stats.get(topic, 0) + 1
            
            # Проверяем уникальность по тексту вопроса
            exists = db.get_explanation_by_question_text(question_text)
            if exists:
                print(f"[SKIP][{idx}/{total}] Вопрос уже существует: {question_text[:50]}...")
                continue
            
            # Подготавливаем данные для базы
            correct_answer_index = ord(q['correct_answer']) - ord('A')
            correct_answer_text = q['options'][correct_answer_index]
            
            # Формируем неправильные варианты
            incorrect_options = []
            for i, option in enumerate(q['options']):
                if i != correct_answer_index:
                    incorrect_options.append(option)
            
            db_question = {
                'topic': topic,
                'question': question_text,
                'answer': correct_answer_text,
                'explanation': f"Правильный ответ: {q['correct_answer']}) {correct_answer_text}",
                'incorrect_options': '\n'.join(incorrect_options),
                'question_type': 'standard',
                'source': 'pdf'
            }
            
            try:
                db.add_question(db_question)
                logf.write(f"{idx} | {topic} | {question_text}\n")
                saved_count += 1
                print(f"[SAVED][{idx}/{total}] Тема: {topic} | {question_text[:50]}...")
            except Exception as e:
                print(f"[ERROR][{idx}/{total}] Ошибка сохранения: {e}")
    
    print(f"\n[LOG] Добавлено {saved_count} новых вопросов в базу.")
    print(f"[LOG] Статистика по темам:")
    for topic, count in sorted(topic_stats.items()):
        print(f"  - {topic}: {count} вопросов")

def main():
    """Основная функция для обработки всех PDF файлов."""
    print("[LOG] Запуск обработки PDF файлов...")
    processor = PDFProcessor()
    db = Database()
    
    # Список файлов для обработки (обновите пути к вашим файлам)
    pdf_files = [
        "files/new_format.pdf",  # Замените на реальный путь к вашему файлу
    ]
    
    total_questions = 0
    
    for pdf_file in pdf_files:
        if os.path.exists(pdf_file):
            print(f"\n[LOG] Обработка файла: {pdf_file}")
            questions = processor.process_pdf_file(pdf_file)
            print(f"[LOG] Найдено {len(questions)} вопросов. Начинаю добавление в базу...")
            add_questions_to_db(questions, db)
            total_questions += len(questions)
        else:
            print(f"[LOG] Файл не найден: {pdf_file}")
    
    print(f"\n[LOG] Обработка завершена. Всего обработано {total_questions} вопросов.")

if __name__ == "__main__":
    main() 