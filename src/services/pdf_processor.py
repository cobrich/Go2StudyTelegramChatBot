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
        
        # Паттерны для поиска вопросов
        self.question_patterns = [
            r'^\d+[\.\)]\s+',  # 1) или 1.
            r'^\d+\.\s+',      # 1. 
        ]
        
        # Паттерны для поиска вариантов ответов
        self.option_patterns = [
            r'^\s*[A-D]\)\s+',  # A) B) C) D)
            r'^\s*[А-Г]\)\s+',  # А) Б) В) Г)
        ]
        
        # Паттерны для поиска правильного ответа
        self.correct_answer_patterns = [
            r'✅\s*Правильный ответ:\s*([A-DА-Г])\)',  # ✅ Правильный ответ: A)
            r'✅\s*([A-DА-Г])\)',                      # ✅ A)
            r'([A-DА-Г])\s*✅',                        # A) ✅
            r'([A-DА-Г])\).*?✅',                      # A) текст ✅ (новый формат)
        ]

    def detect_language(self, text: str) -> str:
        """Определение языка на основе содержимого."""
        kazakh_chars = set('әіңғүұқөһӘІҢҒҮҰҚӨҺ')
        if any(char in text for char in kazakh_chars):
            return 'kk'
        return 'ru'

    def extract_topic_from_filename(self, filename: str) -> str:
        """Извлечение темы из имени файла - fallback тема."""
        # Возвращаем fallback тему, которая точно есть в TOPICS
        return "Операции с дробями и остатками"  # Первая подходящая тема для математики 5 класса

    def determine_topic_with_ai(self, question_text: str) -> str:
        """Определение темы вопроса с помощью AI."""
        try:
            from config.constants import TOPICS
            ai_service = AIService()
            
            prompt = f"""
Определи наиболее подходящую тему для этого математического вопроса из списка:

{', '.join(TOPICS)}

Вопрос: {question_text}

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

    def parse_question_block(self, text_block: str) -> Optional[Dict]:
        """Парсинг блока текста с вопросом."""
        lines = text_block.strip().split('\n')
        if not lines:
            return None
        
        # Поиск начала вопроса
        question_text = ""
        options = []
        correct_answer = None
        
        i = 0
        # Найти строку с номером вопроса
        while i < len(lines):
            line = lines[i].strip()
            if any(re.match(pattern, line) for pattern in self.question_patterns):
                # Убираем номер вопроса
                question_text = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
                i += 1
                break
            i += 1
        
        if not question_text:
            return None
        
        # Собираем продолжение вопроса до первого варианта ответа
        while i < len(lines):
            line = lines[i].strip()
            if any(re.match(pattern, line) for pattern in self.option_patterns):
                break
            if line and not any(re.search(pattern, line) for pattern in self.correct_answer_patterns):
                question_text += " " + line
            i += 1
        
        # Собираем варианты ответов
        current_option = ""
        while i < len(lines):
            line = lines[i].strip()
            
            # Проверяем на правильный ответ
            for pattern in self.correct_answer_patterns:
                match = re.search(pattern, line)
                if match:
                    correct_answer = match.group(1).upper()
                    # Убираем маркер правильного ответа из строки
                    line = re.sub(r'✅.*', '', line).strip()
                    break
            
            # Проверяем начало нового варианта ответа
            option_match = None
            for pattern in self.option_patterns:
                option_match = re.match(pattern, line)
                if option_match:
                    break
            
            if option_match:
                # Сохраняем предыдущий вариант
                if current_option:
                    options.append(current_option.strip())
                # Начинаем новый вариант
                current_option = re.sub(r'^\s*[A-DА-Г]\)\s*', '', line)
            else:
                # Продолжение текущего варианта
                if line:
                    current_option += " " + line
            
            i += 1
        
        # Добавляем последний вариант
        if current_option:
            options.append(current_option.strip())
        
        # Проверяем, что у нас есть все необходимые данные
        if not question_text or len(options) < 2:
            return None
        
        # Нормализуем правильный ответ
        if correct_answer:
            # Конвертируем русские буквы в латинские
            if correct_answer in 'АБВГ':
                correct_answer = ['A', 'B', 'C', 'D']['АБВГ'.index(correct_answer)]
        
        return {
            'question': question_text.strip(),
            'options': options,
            'correct_answer': correct_answer,
            'raw_text': text_block
        }

    def extract_topics_from_headers(self, text: str) -> Dict[int, str]:
        """Извлечение тем из заголовков PDF."""
        from config.constants import TOPICS
        
        lines = text.split('\n')
        topic_map = {}  # номер_строки -> тема
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Ищем строки с "ТЕМА:"
            if line_clean.startswith('ТЕМА:'):
                topic_name = line_clean.replace('ТЕМА:', '').strip()
                if topic_name in TOPICS:
                    topic_map[i] = topic_name
                    continue
            
            # Ищем темы в обычных строках (без префикса)
            for topic in TOPICS:
                if topic.lower() in line_clean.lower() and len(line_clean) < 100:
                    # Проверяем, что это не часть вопроса
                    if not any(pattern in line_clean for pattern in ['A)', 'B)', 'C)', 'D)', '1.', '2.', '3.']):
                        topic_map[i] = topic
                        break
        
        return topic_map

    def determine_topic_for_question(self, question_text: str, question_line_num: int, topic_map: Dict[int, str]) -> str:
        """Определение темы для конкретного вопроса."""
        # Ищем ближайшую тему перед вопросом
        closest_topic = None
        closest_distance = float('inf')
        
        for line_num, topic in topic_map.items():
            if line_num < question_line_num:
                distance = question_line_num - line_num
                if distance < closest_distance:
                    closest_distance = distance
                    closest_topic = topic
        
        if closest_topic:
            return closest_topic
        
        # Если тема не найдена в заголовках, используем AI
        return self.determine_topic_with_ai(question_text)

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
            
            # Извлекаем темы из заголовков
            topic_map = self.extract_topics_from_headers(full_text)
            print(f"[LOG] Найдено тем в заголовках: {len(topic_map)}")
            for line_num, topic in topic_map.items():
                print(f"  Строка {line_num}: {topic}")
            
            # Разбиваем текст на блоки вопросов
            question_blocks = self.split_into_question_blocks(full_text)
            lines = full_text.split('\n')
            
            for block in question_blocks:
                parsed_question = self.parse_question_block(block)
                if parsed_question:
                    # Находим номер строки для этого вопроса
                    question_line_num = 0
                    for i, line in enumerate(lines):
                        if parsed_question['question'][:20] in line:
                            question_line_num = i
                            break
                    
                    # Определяем тему для вопроса
                    topic = self.determine_topic_for_question(
                        parsed_question['question'], 
                        question_line_num, 
                        topic_map
                    )
                    
                    parsed_question.update({
                        'language': language,
                        'topic': topic,
                        'source_file': os.path.basename(pdf_path)
                    })
                    questions.append(parsed_question)
            
            logging.info(f"Извлечено {len(questions)} вопросов из {pdf_path}")
            return questions
            
        except Exception as e:
            logging.error(f"Ошибка при обработке {pdf_path}: {e}")
            return []

    def split_into_question_blocks(self, text: str) -> List[str]:
        """Разбивка текста на блоки вопросов."""
        # Ищем начала вопросов
        question_starts = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if any(re.match(pattern, line) for pattern in self.question_patterns):
                question_starts.append(i)
        
        if not question_starts:
            return []
        
        # Создаем блоки
        blocks = []
        for i in range(len(question_starts)):
            start_line = question_starts[i]
            end_line = question_starts[i + 1] if i + 1 < len(question_starts) else len(lines)
            
            block_lines = lines[start_line:end_line]
            block_text = '\n'.join(block_lines)
            blocks.append(block_text)
        
        return blocks

    def process_pdf_file(self, pdf_path: str) -> List[Dict]:
        """Обработка PDF файла и извлечение вопросов."""
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
            
            questions = self.extract_questions_from_pdf(pdf_path)
            
            # Дополнительная обработка и валидация
            validated_questions = []
            for question in questions:
                if self.validate_question(question):
                    validated_questions.append(question)
            
            logging.info(f"Валидировано {len(validated_questions)} из {len(questions)} вопросов")
            return validated_questions
            
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
    
    # Список файлов для обработки
    pdf_files = [
        "files/математика темы 180 вопросов.pdf",
        "files/Математика 5 класс 120 вопросов.pdf"
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