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

from services.database import Database
from services.ai_service import AIService
from services.topic_manager import TopicManager

class PDFProcessor:
    def __init__(self, output_dir: str = "question_images"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.topic_manager = TopicManager()
        
        # Паттерн для поиска заголовков тем
        self.topic_header_pattern = r'Тема:\s*([^(]+)\((\d+)\)'
        
        # Паттерн для поиска вопросов (более гибкий - учитывает невидимые символы)
        self.question_pattern = r'^(\d+)[.)\s]*\s*(.+)'
        
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
        
        # Словарь для хранения первого вопроса каждой темы
        topic_first_questions = {}
        
        print(f"[DEBUG] Всего строк для обработки: {len(lines)}")
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Очищаем строку от невидимых символов
            line = ''.join(char for char in line if char.isprintable() or char.isspace())
            line = line.strip()
            
            # Пропускаем пустые строки
            if not line:
                i += 1
                continue
            
            # Проверяем на заголовок темы
            topic_match = re.match(self.topic_header_pattern, line)
            if topic_match:
                # Сохраняем предыдущий вопрос, если он был
                if current_question and current_options and correct_answer:
                    # Очищаем текст вопроса
                    clean_question = ''.join(char for char in current_question if char.isprintable() or char.isspace())
                    clean_question = clean_question.strip()
                    
                    if len(clean_question) >= 10:  # Минимальная длина вопроса
                        topic_name = current_topic or 'Математика'
                        
                        questions.append({
                            'topic': topic_name,
                            'question': clean_question,
                            'options': current_options,
                            'correct_answer': correct_answer
                        })
                        print(f"[SAVE] Сохранен вопрос: {clean_question[:100]}...")
                
                # Устанавливаем новую тему
                current_topic = topic_match.group(1).strip()
                expected_questions = int(topic_match.group(2))
                print(f"[LOG] Найдена тема: '{current_topic}' ({expected_questions} вопросов)")
                
                # Сбрасываем текущий вопрос
                current_question = None
                current_options = []
                correct_answer = None
                
                i += 1
                continue
            
            # Проверяем на начало вопроса
            question_match = re.match(self.question_pattern, line)
            if question_match:
                # Сохраняем предыдущий вопрос, если он был
                if current_question and current_options and correct_answer:
                    # Очищаем текст вопроса
                    clean_question = ''.join(char for char in current_question if char.isprintable() or char.isspace())
                    clean_question = clean_question.strip()
                    
                    if len(clean_question) >= 10:  # Минимальная длина вопроса
                        topic_name = current_topic or 'Математика'
                        
                        questions.append({
                            'topic': topic_name,
                            'question': clean_question,
                            'options': current_options,
                            'correct_answer': correct_answer
                        })
                        print(f"[SAVE] Сохранен вопрос: {clean_question[:100]}...")
                
                # Начинаем новый вопрос
                question_number = question_match.group(1)
                current_question = question_match.group(2).strip()
                current_options = []
                correct_answer = None
                
                # Сохраняем первый вопрос темы для анализа (сразу при начале вопроса)
                topic_name = current_topic or 'Математика'
                if topic_name not in topic_first_questions and current_question:
                    # Создаем предварительную версию вопроса для анализа
                    temp_question = current_question
                    # Пытаемся найти продолжение вопроса в следующих строках
                    j = i + 1
                    while j < len(lines) and j < i + 5:  # Смотрим максимум 5 строк вперед
                        next_line = lines[j].strip()
                        next_line = ''.join(char for char in next_line if char.isprintable() or char.isspace())
                        next_line = next_line.strip()
                        
                        # Если это не вариант ответа и не новый вопрос, добавляем к тексту
                        if (next_line and 
                            not re.match(r'^[A-ZА-Г]\).*', next_line) and 
                            not re.match(r'^\d+[.)\s]*\s*', next_line) and
                            not re.match(r'^\d+$', next_line)):
                            temp_question += " " + next_line
                        else:
                            break
                        j += 1
                    
                    topic_first_questions[topic_name] = temp_question
                    print(f"[FIRST_Q] Сохранен первый вопрос темы '{topic_name}': {temp_question[:100]}...")
                
                print(f"[LOG] Вопрос {question_number}: {current_question[:100]}...")
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
                    
                    # Очищаем текст варианта ответа
                    option_text = ''.join(char for char in option_text if char.isprintable() or char.isspace())
                    option_text = option_text.strip()
                    
                    # Пропускаем пустые варианты
                    if len(option_text) < 1:
                        i += 1
                        continue
                    
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
                clean_line = ''.join(char for char in line if char.isprintable() or char.isspace())
                clean_line = clean_line.strip()
                
                # Проверяем, что строка не пустая и не является служебной информацией
                if clean_line and len(clean_line) > 2:
                    # Проверяем, что это не номер страницы, не вариант ответа, и не начало нового вопроса
                    is_page_number = re.match(r'^\d+$', clean_line)
                    is_option = re.match(r'^[A-ZА-Г]\).*', clean_line)
                    is_new_question = re.match(r'^\d+[.)\s]*\s*', clean_line)
                    
                    if not is_page_number and not is_option and not is_new_question:
                        # Добавляем пробел только если предыдущая строка не заканчивается пробелом
                        if not current_question.endswith(' '):
                            current_question += " "
                        current_question += clean_line
                        print(f"[APPEND] Добавлено к вопросу: {clean_line[:50]}...")
                    else:
                        print(f"[SKIP] Пропущена строка (служебная): {clean_line[:50]}...")
            
            # Отладочная информация для первых 20 строк
            if i < 20:
                print(f"[DEBUG][{i}] Строка: '{line[:100]}...' | Тема: {current_topic} | Вопрос: {bool(current_question)}")
            
            i += 1
        
        # Сохраняем последний вопрос
        if current_question and current_options and correct_answer:
            # Очищаем текст вопроса
            clean_question = ''.join(char for char in current_question if char.isprintable() or char.isspace())
            clean_question = clean_question.strip()
            
            if len(clean_question) >= 10:  # Минимальная длина вопроса
                topic_name = current_topic or 'Математика'
                
                questions.append({
                    'topic': topic_name,
                    'question': clean_question,
                    'options': current_options,
                    'correct_answer': correct_answer
                })
                print(f"[SAVE] Сохранен последний вопрос: {clean_question[:100]}...")
        
        # Теперь обновляем темы в вопросах, используя первые вопросы для анализа
        print(f"[DEBUG] Анализируем темы с помощью AI...")
        
        # Сначала анализируем первые вопросы каждой темы для определения правильных тем
        topic_mappings = {}  # original_topic -> normalized_topic
        
        for original_topic, first_question in topic_first_questions.items():
            # Используем TopicManager для нормализации темы с первым вопросом темы
            normalized_topic = self.topic_manager.ensure_topic_exists(
                original_topic, 
                sample_question=first_question
            )
            topic_mappings[original_topic] = normalized_topic
            print(f"[TOPIC] '{original_topic}' → '{normalized_topic}' (на основе первого вопроса)")
        
        # Теперь применяем найденные темы ко всем вопросам
        for question in questions:
            original_topic = question['topic']
            normalized_topic = topic_mappings.get(original_topic, original_topic)
            question['topic'] = normalized_topic
        
        print(f"[DEBUG] Итого извлечено вопросов: {len(questions)}")
        return questions

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
            
            print(f"[DEBUG] Извлечено {len(full_text)} символов из PDF")
            print(f"[DEBUG] Первые 200 символов: {repr(full_text[:200])}")
            
            # Определяем язык
            language = self.detect_language(full_text)
            print(f"[DEBUG] Определен язык: {language}")
            
            # Проверяем, есть ли заголовки тем в формате "Тема: название(количество)"
            has_topic_headers = bool(re.search(self.topic_header_pattern, full_text))
            print(f"[DEBUG] Найдены заголовки тем: {has_topic_headers}")
            
            # Выбираем подходящий метод парсинга
            if has_topic_headers:
                print("[DEBUG] Используем парсер с заголовками тем")
                extracted_questions = self.extract_topics_and_questions(full_text)
            else:
                print("[DEBUG] Используем парсер без заголовков тем")
                extracted_questions = self.extract_questions_without_topics(full_text)
            
            print(f"[DEBUG] Извлечено {len(extracted_questions)} сырых вопросов")
            
            # Обрабатываем каждый вопрос
            valid_count = 0
            invalid_count = 0
            
            for i, q in enumerate(extracted_questions):
                # Тема уже нормализована в extract_topics_and_questions или extract_questions_without_topics
                normalized_topic = q['topic']
                
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
                    valid_count += 1
                    print(f"[VALID][{i+1}] Тема: {normalized_topic} | {q['question'][:100]}...")
                else:
                    invalid_count += 1
                    print(f"[SKIP][{i+1}] Невалидный вопрос: {q['question'][:100]}...")
            
            print(f"[DEBUG] Валидных вопросов: {valid_count}, Невалидных: {invalid_count}")
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
        
        # Очищаем текст вопроса от невидимых символов
        question_text = question['question'].strip()
        # Удаляем невидимые символы Unicode
        question_text = ''.join(char for char in question_text if char.isprintable() or char.isspace())
        question_text = question_text.strip()
        
        # Проверяем, что вопрос не пустой и содержит хотя бы 10 символов
        if len(question_text) < 10:
            logging.warning(f"Вопрос слишком короткий или пустой: '{question_text}'")
            return False
        
        # Проверяем, что вопрос содержит буквы или цифры
        if not any(char.isalnum() for char in question_text):
            logging.warning(f"Вопрос не содержит букв или цифр: '{question_text}'")
            return False
        
        # Проверяем количество вариантов ответов
        if len(question['options']) < 2:
            logging.warning(f"Недостаточно вариантов ответов: {len(question['options'])}")
            return False
        
        # Проверяем наличие правильного ответа
        if not question.get('correct_answer'):
            logging.warning(f"Вопрос без правильного ответа: {question_text[:100]}...")
            return False
        
        # Проверяем, что правильный ответ соответствует одному из вариантов
        correct_index = ord(question['correct_answer']) - ord('A')
        if correct_index >= len(question['options']):
            logging.warning(f"Неверный индекс правильного ответа: {question['correct_answer']} для вопроса: {question_text[:100]}...")
            return False
        
        # Проверяем, что варианты ответов не пустые
        for i, option in enumerate(question['options']):
            option_text = option.strip()
            option_text = ''.join(char for char in option_text if char.isprintable() or char.isspace())
            option_text = option_text.strip()
            
            if len(option_text) < 1:
                logging.warning(f"Пустой вариант ответа {i+1} для вопроса: {question_text[:100]}...")
                return False
        
        return True

    def extract_questions_without_topics(self, text: str) -> List[Dict]:
        """Извлечение вопросов из PDF без четких заголовков тем."""
        questions = []
        lines = text.split('\n')
        current_question = None
        current_options = []
        correct_answer = None
        question_number = 0
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Очищаем строку от невидимых символов
            line = ''.join(char for char in line if char.isprintable() or char.isspace())
            line = line.strip()
            
            # Пропускаем пустые строки
            if not line:
                i += 1
                continue
            
            # Проверяем на начало вопроса (любое число с закрывающей скобкой или точкой)
            question_match = re.match(r'^(\d+)[.)\s]*\s*(.+)', line)
            if question_match:
                # Сохраняем предыдущий вопрос, если он был
                if current_question and current_options and correct_answer:
                    clean_question = ''.join(char for char in current_question if char.isprintable() or char.isspace())
                    clean_question = clean_question.strip()
                    
                    if len(clean_question) >= 10:
                        questions.append({
                            'topic': self.topic_manager.get_topic_by_content(clean_question),
                            'question': clean_question,
                            'options': current_options,
                            'correct_answer': correct_answer
                        })
                
                # Начинаем новый вопрос
                question_number = int(question_match.group(1))
                current_question = question_match.group(2).strip()
                current_options = []
                correct_answer = None
                
                print(f"[LOG] Вопрос {question_number}: {current_question[:100]}...")
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
                    
                    # Очищаем текст варианта ответа
                    option_text = ''.join(char for char in option_text if char.isprintable() or char.isspace())
                    option_text = option_text.strip()
                    
                    # Пропускаем пустые варианты
                    if len(option_text) < 1:
                        i += 1
                        continue
                    
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
                clean_line = ''.join(char for char in line if char.isprintable() or char.isspace())
                clean_line = clean_line.strip()
                
                # Проверяем, что строка не пустая и не является служебной информацией
                if clean_line and len(clean_line) > 2:
                    # Проверяем, что это не номер страницы, не вариант ответа, и не начало нового вопроса
                    is_page_number = re.match(r'^\d+$', clean_line)
                    is_option = re.match(r'^[A-ZА-Г]\).*', clean_line)
                    is_new_question = re.match(r'^\d+[.)\s]*\s*', clean_line)
                    
                    if not is_page_number and not is_option and not is_new_question:
                        # Добавляем пробел только если предыдущая строка не заканчивается пробелом
                        if not current_question.endswith(' '):
                            current_question += " "
                        current_question += clean_line
                        print(f"[APPEND] Добавлено к вопросу: {clean_line[:50]}...")
                    else:
                        print(f"[SKIP] Пропущена строка (служебная): {clean_line[:50]}...")
            
            i += 1
        
        # Сохраняем последний вопрос
        if current_question and current_options and correct_answer:
            clean_question = ''.join(char for char in current_question if char.isprintable() or char.isspace())
            clean_question = clean_question.strip()
            
            if len(clean_question) >= 10:
                questions.append({
                    'topic': self.topic_manager.get_topic_by_content(clean_question),
                    'question': clean_question,
                    'options': current_options,
                    'correct_answer': correct_answer
                })
        
        return questions

def add_questions_to_db(questions: List[Dict], db: Database):
    """Добавление вопросов в базу данных с генерацией подробных объяснений."""
    total = len(questions)
    print(f"[LOG] Начинаю добавление {total} вопросов в базу...")
    saved_count = 0
    
    # Инициализируем AI сервис для генерации объяснений
    ai_service = AIService()
    
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
                print(f"[SKIP][{idx}/{total}] Вопрос уже существует: {question_text[:100]}...")
                continue
            
            # Подготавливаем данные для базы
            correct_answer_index = ord(q['correct_answer']) - ord('A')
            correct_answer_text = q['options'][correct_answer_index]
            
            # Формируем неправильные варианты
            incorrect_options = []
            for i, option in enumerate(q['options']):
                if i != correct_answer_index:
                    incorrect_options.append(option)
            
            # Генерируем подробное объяснение с помощью AI
            print(f"[AI][{idx}/{total}] Генерирую объяснение для вопроса...")
            try:
                detailed_explanation = ai_service.generate_detailed_explanation(
                    question_text, 
                    correct_answer_text, 
                    topic
                )
                print(f"[AI][{idx}/{total}] Объяснение сгенерировано: {detailed_explanation[:100]}...")
            except Exception as e:
                print(f"[AI][{idx}/{total}] Ошибка генерации объяснения: {e}")
                detailed_explanation = f"Правильный ответ: {q['correct_answer']}) {correct_answer_text}"
            
            db_question = {
                'topic': topic,
                'question': question_text,
                'answer': correct_answer_text,
                'explanation': detailed_explanation,
                'incorrect_options': '\n'.join(incorrect_options),
                'question_type': 'standard',
                'source': 'pdf'
            }
            
            try:
                db.add_question(db_question)
                logf.write(f"{idx} | {topic} | {question_text}\n")
                saved_count += 1
                print(f"[SAVED][{idx}/{total}] Тема: {topic} | {question_text[:100]}...")
            except Exception as e:
                print(f"[ERROR][{idx}/{total}] Ошибка сохранения: {e}")
    
    print(f"\n[LOG] Добавлено {saved_count} новых вопросов в базу.")
    print(f"[LOG] Статистика по темам:")
    for topic, count in sorted(topic_stats.items()):
        print(f"  - {topic}: {count} вопросов")

def main():
    """Основная функция для обработки PDF файлов."""
    processor = PDFProcessor()
    
    # Список PDF файлов для обработки
    pdf_files = [
        "files/file1.pdf",  # Первый правильно отформатированный файл
        "files/file2.pdf"   # Второй файл с математическими задачами
    ]
    
    total_questions = 0
    
    for pdf_file in pdf_files:
        if not os.path.exists(pdf_file):
            print(f"❌ Файл не найден: {pdf_file}")
            continue
            
        print(f"\n{'='*60}")
        print(f"🔄 Обрабатываю файл: {pdf_file}")
        print(f"{'='*60}")
        
        try:
            questions = processor.process_pdf_file(pdf_file)
            print(f"✅ Успешно обработано {len(questions)} вопросов из {pdf_file}")
            
            # Добавляем вопросы в базу данных
            if questions:
                print(f"\n🔄 Добавляю {len(questions)} вопросов в базу данных...")
                from services.database import Database
                db = Database()
                add_questions_to_db(questions, db)
                print(f"✅ Вопросы успешно добавлены в базу данных")
            
            total_questions += len(questions)
            
        except Exception as e:
            print(f"❌ Ошибка при обработке {pdf_file}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"🎉 ИТОГО ОБРАБОТАНО: {total_questions} вопросов")
    print(f"{'='*60}")

if __name__ == "__main__":
    main() 