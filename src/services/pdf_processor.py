"""
PDF Question Processor

Processes PDF files containing questions and extracts them into the database.
"""

import logging
import os
import re
from typing import List, Dict, Any, Optional, Tuple
import PyPDF2
from telegram import Update
from telegram.ext import ContextTypes
import tempfile
import json
import time
from pathlib import Path
from src.db.sync_database_facade import get_sync_database_facade
from src.services.ai_service_improved import ImprovedAIService
import fitz  # PyMuPDF
from PIL import Image

import sys

# Добавляем путь к src в PYTHONPATH для корректных импортов
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class PDFProcessor:
    def __init__(self, db, ai_service, output_dir: str = "question_images"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Инициализируем сервисы извне
        self.db = db
        self.ai_service = ai_service
        
        # Паттерн для поиска заголовков тем
        self.topic_header_pattern = r'Тема:\s*([^(]+)\((\d+)\)'
        
        # Паттерн для поиска вопросов (строгий - только цифра + точка или скобка)
        self.question_pattern = r'^(\d+)[.)](\s*(.+))?$'
        
        # Паттерны для поиска вариантов ответов
        self.option_patterns = [
            r'^([A-D])\)\s*(.*?)(\s*✅)?$',  # A) текст ✅ (опционально)
            r'^([А-Г])\)\s*(.*?)(\s*✅)?$',  # А) текст ✅ (опционально)
        ]

    def get_available_topics_from_db(self) -> List[str]:
        """Получение списка доступных тем из базы данных."""
        try:
            return self.db.get_topic_names(active_only=True)
        except Exception as e:
            logging.error(f"Ошибка при получении тем из БД: {e}")
            return []

    def validate_topic_exists(self, topic_name: str) -> bool:
        """Проверка существования темы в базе данных."""
        available_topics = self.get_available_topics_from_db()
        # Точное соответствие названия темы
        return topic_name.strip() in available_topics

    def detect_language(self, text: str) -> str:
        """Определение языка на основе содержимого."""
        kazakh_chars = set('әіңғүұқөһӘІҢҒҮҰҚӨҺ')
        if any(char in text for char in kazakh_chars):
            return 'kk'
        return 'ru'

    def extract_topics_and_questions(self, text: str) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Извлечение тем и вопросов из текста PDF.
        Возвращает кортеж: (список_вопросов, статистика_по_темам)
        """
        # Проверяем структуру текста для определения типа парсера
        lines = text.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        empty_lines_count = len(lines) - len(non_empty_lines)
        
        # Подсчитываем очень короткие строки (1-3 символа) - признак фрагментированного текста
        very_short_lines_count = sum(1 for line in non_empty_lines if len(line) <= 3)
        short_lines_count = sum(1 for line in non_empty_lines if len(line) <= 20)
        
        # Проверяем на фрагментированную структуру:
        # 1. Много очень коротких строк (1-3 символа) - основной признак
        # 2. Или много пустых строк + много коротких строк (для PyPDF2)
        is_fragmented = (
            (very_short_lines_count / len(non_empty_lines) > 0.4) or  # Более 40% очень коротких строк
            (empty_lines_count / len(lines) > 0.3 and short_lines_count / len(non_empty_lines) > 0.5)  # Старое условие для PyPDF2
        )
        
        if is_fragmented:
            print(f"[DEBUG] Обнаружена фрагментированная структура PDF:")
            print(f"[DEBUG] - Очень короткие строки (1-3 символа): {very_short_lines_count}/{len(non_empty_lines)} ({very_short_lines_count / len(non_empty_lines) * 100:.1f}%)")
            print(f"[DEBUG] - Короткие строки (<=20 символов): {short_lines_count}/{len(non_empty_lines)} ({short_lines_count / len(non_empty_lines) * 100:.1f}%)")
            print(f"[DEBUG] - Пустые строки: {empty_lines_count}/{len(lines)} ({empty_lines_count / len(lines) * 100:.1f}%)")
            print("[DEBUG] Используем специальный парсер для фрагментированного текста")
            return self._extract_from_fragmented_text(text)
        else:
            print("[DEBUG] Используем стандартный парсер")
            return self._extract_topics_and_questions_standard(text)

    def _extract_from_fragmented_text(self, text: str) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Специальный метод для извлечения вопросов из PDF с фрагментированным текстом,
        где каждое слово находится на отдельной строке.
        """
        questions = []
        lines = text.split('\n')
        
        # Статистика обработки
        topic_stats = {
            'found_topics': {},
            'valid_topics': {},
            'invalid_topics': {},
            'total_questions': 0,
            'valid_questions': 0,
            'invalid_questions': 0
        }
        
        # Получаем список доступных тем из БД
        available_topics = self.get_available_topics_from_db()
        print(f"[DEBUG] Доступные темы в БД ({len(available_topics)}): {available_topics}")
        
        # Сначала склеиваем фрагментированный текст в нормальные строки
        reconstructed_lines = []
        current_line = ""
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:  # Пустая строка
                if current_line.strip():
                    reconstructed_lines.append(current_line.strip())
                    current_line = ""
                i += 1
                continue
            
            # Проверяем, является ли это началом нового элемента (номер вопроса, вариант ответа, тема)
            is_question_number = re.match(r'^\d+\.$', line)
            is_option = re.match(r'^[A-DА-Г]\)$', line)
            is_topic_start = line == 'Тема:'
            is_checkmark = line == '✅'
            
            if is_question_number or is_option or is_topic_start:
                # Сохраняем предыдущую строку
                if current_line.strip():
                    reconstructed_lines.append(current_line.strip())
                
                # Начинаем новую строку с этого элемента
                current_line = line
            elif is_checkmark:
                # Добавляем галочку к текущей строке
                current_line += " " + line
            else:
                # Добавляем к текущей строке
                if current_line:
                    current_line += " " + line
                else:
                    current_line = line
            
            i += 1
        
        # Добавляем последнюю строку
        if current_line.strip():
            reconstructed_lines.append(current_line.strip())
        
        print(f"[DEBUG] Восстановлено строк: {len(reconstructed_lines)}")
        for i, line in enumerate(reconstructed_lines[:20]):
            print(f"[DEBUG][{i}] Восстановленная строка: '{line}'")
        
        # Теперь парсим восстановленные строки
        current_topic = None
        current_question = None
        current_options = []
        correct_answer = None
        
        i = 0
        while i < len(reconstructed_lines):
            line = reconstructed_lines[i].strip()
            
            # Проверяем на заголовок темы
            if line == 'Тема:' and i + 1 < len(reconstructed_lines):
                # Сохраняем предыдущий вопрос
                if current_question and current_options and correct_answer:
                    self._save_current_question(
                        current_topic, current_question, current_options, 
                        correct_answer, questions, topic_stats, available_topics
                    )
                
                # Ищем название темы и количество вопросов в следующих строках
                topic_name = ""
                question_count = 0
                j = i + 1
                
                while j < len(reconstructed_lines):
                    next_line = reconstructed_lines[j].strip()
                    
                    # Проверяем, является ли это количеством вопросов в скобках
                    count_match = re.match(r'^\((\d+)\)$', next_line)
                    if count_match:
                        question_count = int(count_match.group(1))
                        break
                    elif re.match(r'^\d+\.$', next_line):
                        # Начался первый вопрос, прекращаем поиск
                        break
                    else:
                        # Добавляем к названию темы
                        if topic_name:
                            topic_name += " " + next_line
                        else:
                            topic_name = next_line
                    j += 1
                
                current_topic = topic_name.strip()
                
                # Проверяем валидность темы
                topic_exists = self.validate_topic_exists(current_topic)
                
                if topic_exists:
                    print(f"[✅ VALID] Найдена валидная тема: '{current_topic}' ({question_count} вопросов)")
                    topic_stats['valid_topics'][current_topic] = 0
                else:
                    print(f"[❌ INVALID] Найдена невалидная тема: '{current_topic}' (не найдена в БД)")
                    topic_stats['invalid_topics'][current_topic] = 0
                
                topic_stats['found_topics'][current_topic] = 0
                
                # Сбрасываем текущий вопрос
                current_question = None
                current_options = []
                correct_answer = None
                
                i = j
                continue
            
            # Проверяем на начало вопроса
            question_match = re.match(self.question_pattern, line)
            if question_match:
                # Сохраняем предыдущий вопрос
                if current_question and current_options and correct_answer:
                    self._save_current_question(
                        current_topic, current_question, current_options, 
                        correct_answer, questions, topic_stats, available_topics
                    )
                
                # Начинаем новый вопрос
                question_number = question_match.group(1)
                # Группа 3 содержит текст вопроса (может быть None)
                question_text = question_match.group(3) if question_match.group(3) else ""
                current_question = question_text.strip()
                current_options = []
                correct_answer = None
                
                print(f"[LOG] Вопрос {question_number}: {current_question[:100]}...")
                i += 1
                continue
            
            # Проверяем на вариант ответа
            option_match = re.match(r'^([A-DА-Г])\)\s*(.*)', line)
            if option_match:
                option_letter = option_match.group(1)
                option_text = option_match.group(2).strip()
                has_checkmark = '✅' in line
                
                # Конвертируем русские буквы в латинские
                if option_letter in 'АБВГ':
                    option_letter = ['A', 'B', 'C', 'D']['АБВГ'.index(option_letter)]
                
                # Убираем галочку из текста
                option_text = option_text.replace('✅', '').strip()
                
                if option_text:  # Добавляем только непустые варианты
                    current_options.append(option_text)
                    
                    if has_checkmark:
                        correct_answer = option_letter
                        print(f"[LOG] Правильный ответ: {option_letter}) {option_text}")
            
            i += 1
        
        # Сохраняем последний вопрос
        if current_question and current_options and correct_answer:
            self._save_current_question(
                current_topic, current_question, current_options, 
                correct_answer, questions, topic_stats, available_topics
            )
        
        print(f"[DEBUG] Итого извлечено вопросов: {len(questions)}")
        return questions, topic_stats

    def _extract_topics_and_questions_standard(self, text: str) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Стандартный метод извлечения тем и вопросов из текста PDF.
        """
        questions = []
        lines = text.split('\n')
        current_topic = None
        current_question = None
        current_options = []
        correct_answer = None
        
        # Статистика обработки
        topic_stats = {
            'found_topics': {},      # найденные темы и количество вопросов
            'valid_topics': {},      # валидные темы (существуют в БД)
            'invalid_topics': {},    # невалидные темы (не найдены в БД)
            'total_questions': 0,    # общее количество найденных вопросов
            'valid_questions': 0,    # количество вопросов с валидными темами
            'invalid_questions': 0   # количество вопросов с невалидными темами
        }
        
        print(f"[DEBUG] Всего строк для обработки: {len(lines)}")
        print(f"[DEBUG] Получаю список доступных тем из БД...")
        
        # Получаем список доступных тем из БД
        available_topics = self.get_available_topics_from_db()
        print(f"[DEBUG] Доступные темы в БД ({len(available_topics)}): {available_topics}")
        
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
                    self._save_current_question(
                        current_topic, current_question, current_options, 
                        correct_answer, questions, topic_stats, available_topics
                    )
                
                # Устанавливаем новую тему
                current_topic = topic_match.group(1).strip()
                expected_questions = int(topic_match.group(2))
                
                # Проверяем, существует ли тема в БД
                topic_exists = self.validate_topic_exists(current_topic)
                
                if topic_exists:
                    print(f"[✅ VALID] Найдена валидная тема: '{current_topic}' ({expected_questions} вопросов)")
                    topic_stats['valid_topics'][current_topic] = 0
                else:
                    print(f"[❌ INVALID] Найдена невалидная тема: '{current_topic}' (не найдена в БД)")
                    topic_stats['invalid_topics'][current_topic] = 0
                
                topic_stats['found_topics'][current_topic] = 0
                
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
                    self._save_current_question(
                        current_topic, current_question, current_options, 
                        correct_answer, questions, topic_stats, available_topics
                    )
                
                # Начинаем новый вопрос
                question_number = question_match.group(1)
                # Группа 3 содержит текст вопроса (может быть None)
                question_text = question_match.group(3) if question_match.group(3) else ""
                current_question = question_text.strip()
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
                    is_new_question = re.match(self.question_pattern, clean_line)  # Используем строгий паттерн
                    
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
            self._save_current_question(
                current_topic, current_question, current_options, 
                correct_answer, questions, topic_stats, available_topics
            )
        
        print(f"[DEBUG] Итого извлечено вопросов: {len(questions)}")
        return questions, topic_stats

    def _save_current_question(self, current_topic: str, current_question: str, 
                             current_options: List[str], correct_answer: str,
                             questions: List[Dict], topic_stats: Dict, 
                             available_topics: List[str]) -> None:
        """Сохранение текущего вопроса с проверкой валидности темы."""
        # Очищаем текст вопроса
        clean_question = ''.join(char for char in current_question if char.isprintable() or char.isspace())
        clean_question = clean_question.strip()
        
        if len(clean_question) >= 10:  # Минимальная длина вопроса
            topic_name = current_topic or 'Неизвестная тема'
            
            # Обновляем статистику
            topic_stats['total_questions'] += 1
            if topic_name in topic_stats['found_topics']:
                topic_stats['found_topics'][topic_name] += 1
            
            # Проверяем валидность темы
            if topic_name in available_topics:
                # Тема валидна - добавляем вопрос
                questions.append({
                    'topic': topic_name,
                    'question': clean_question,
                    'options': current_options,
                    'correct_answer': correct_answer
                })
                topic_stats['valid_questions'] += 1
                if topic_name in topic_stats['valid_topics']:
                    topic_stats['valid_topics'][topic_name] += 1
                print(f"[✅ SAVE] Сохранен вопрос: {clean_question[:100]}...")
            else:
                # Тема невалидна - пропускаем вопрос
                topic_stats['invalid_questions'] += 1
                if topic_name in topic_stats['invalid_topics']:
                    topic_stats['invalid_topics'][topic_name] += 1
                print(f"[❌ SKIP] Пропущен вопрос (невалидная тема '{topic_name}'): {clean_question[:100]}...")

    def extract_questions_from_pdf(self, pdf_path: str) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Извлечение вопросов из PDF файла.
        Возвращает кортеж: (список_вопросов, статистика_обработки)
        """
        questions = []
        topic_stats = {}
        
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
                extracted_questions, topic_stats = self.extract_topics_and_questions(full_text)
            else:
                print("[DEBUG] Используем парсер без заголовков тем")
                extracted_questions, topic_stats = self.extract_questions_without_topics(full_text)
            
            print(f"[DEBUG] Извлечено {len(extracted_questions)} валидных вопросов")
            
            # Обрабатываем каждый вопрос
            valid_count = 0
            invalid_count = 0
            
            for i, q in enumerate(extracted_questions):
                question_data = {
                    'question': q['question'].strip(),
                    'options': q['options'],
                    'correct_answer': q['correct_answer'],
                    'language': language,
                    'topic': q['topic'],
                    'source_file': os.path.basename(pdf_path)
                }
                
                if self.validate_question(question_data):
                    questions.append(question_data)
                    valid_count += 1
                    print(f"[VALID][{i+1}] Тема: {q['topic']} | {q['question'][:100]}...")
                else:
                    invalid_count += 1
                    print(f"[SKIP][{i+1}] Невалидный вопрос: {q['question'][:100]}...")
            
            print(f"[DEBUG] Финальных валидных вопросов: {valid_count}, Невалидных: {invalid_count}")
            logging.info(f"Извлечено {len(questions)} валидных вопросов из {pdf_path}")
            return questions, topic_stats
            
        except Exception as e:
            logging.error(f"Ошибка при обработке {pdf_path}: {e}")
            return [], {}

    def process_pdf_file(self, pdf_path: str) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Обработка PDF файла и извлечение вопросов.
        Возвращает кортеж: (список_вопросов, статистика_обработки)
        """
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
            
            questions, topic_stats = self.extract_questions_from_pdf(pdf_path)
            
            logging.info(f"Обработано {len(questions)} вопросов из {pdf_path}")
            return questions, topic_stats
            
        except Exception as e:
            logging.error(f"Ошибка при обработке {pdf_path}: {e}")
            return [], {}

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

    def extract_questions_without_topics(self, text: str) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Извлечение вопросов из PDF без четких заголовков тем.
        Возвращает кортеж: (список_вопросов, статистика_по_темам)
        """
        questions = []
        lines = text.split('\n')
        current_question = None
        current_options = []
        correct_answer = None
        question_number = 0
        
        # Статистика (для совместимости)
        topic_stats = {
            'found_topics': {'Неопределенная тема': 0},
            'valid_topics': {},
            'invalid_topics': {'Неопределенная тема': 0},
            'total_questions': 0,
            'valid_questions': 0,
            'invalid_questions': 0
        }
        
        print("[WARNING] PDF без заголовков тем - все вопросы будут отклонены")
        
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
                        # Все вопросы без заголовков тем считаются невалидными
                        topic_stats['total_questions'] += 1
                        topic_stats['invalid_questions'] += 1
                        topic_stats['found_topics']['Неопределенная тема'] += 1
                        topic_stats['invalid_topics']['Неопределенная тема'] += 1
                        print(f"[❌ SKIP] Вопрос без темы: {clean_question[:100]}...")
                
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
                    is_new_question = re.match(self.question_pattern, clean_line)  # Используем строгий паттерн
                    
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
                # Все вопросы без заголовков тем считаются невалидными
                topic_stats['total_questions'] += 1
                topic_stats['invalid_questions'] += 1
                topic_stats['found_topics']['Неопределенная тема'] += 1
                topic_stats['invalid_topics']['Неопределенная тема'] += 1
                print(f"[❌ SKIP] Последний вопрос без темы: {clean_question[:100]}...")
        
        return questions, topic_stats

def add_questions_to_db(questions: List[Dict], db, ai_service) -> Dict[str, int]:
    """
    Добавление вопросов в базу данных с генерацией подробных объяснений.
    Возвращает статистику добавления.
    """
    total = len(questions)
    print(f"[LOG] Начинаю добавление {total} вопросов в базу...")
    saved_count = 0
    
    # Статистика по темам
    topic_stats = {}
    
    with open('added_questions.log', 'a', encoding='utf-8') as logf:
        for idx, q in enumerate(questions, 1):
            question_text = q['question'].strip()
            topic = q.get('topic', 'Неизвестная тема')
            
            # Обновляем статистику
            topic_stats[topic] = topic_stats.get(topic, 0) + 1
            
            # ИСПРАВЛЕНО: Проверяем уникальность по ТОЧНОМУ совпадению текста вопроса
            exists = db.question_exists_exact(question_text)
            if exists:
                print(f"[SKIP][{idx}/{total}] Вопрос уже существует (точное совпадение): {question_text[:100]}...")
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
                # Определяем язык темы
                topic_language = db.get_topic_language(topic)
                
                detailed_explanation = ai_service.generate_detailed_explanation(
                    question_text, 
                    correct_answer_text, 
                    topic,
                    topic_language
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
    
    return {
        'total_processed': total,
        'saved_count': saved_count,
        'topic_stats': topic_stats
    }

def print_processing_report(pdf_file: str, questions: List[Dict], topic_stats: Dict, 
                          db_stats: Dict) -> None:
    """Печать детального отчета об обработке PDF файла."""
    print(f"\n{'='*80}")
    print(f"📊 ОТЧЕТ ОБ ОБРАБОТКЕ ФАЙЛА: {os.path.basename(pdf_file)}")
    print(f"{'='*80}")
    
    # Общая статистика
    print(f"\n📈 ОБЩАЯ СТАТИСТИКА:")
    print(f"  • Всего найдено вопросов в PDF: {topic_stats.get('total_questions', 0)}")
    print(f"  • Вопросов с валидными темами: {topic_stats.get('valid_questions', 0)}")
    print(f"  • Вопросов с невалидными темами: {topic_stats.get('invalid_questions', 0)}")
    print(f"  • Финально добавлено в БД: {db_stats.get('saved_count', 0)}")
    
    # Статистика по валидным темам
    if topic_stats.get('valid_topics'):
        print(f"\n✅ ВАЛИДНЫЕ ТЕМЫ (найдены в БД):")
        for topic, count in topic_stats['valid_topics'].items():
            print(f"  • {topic}: {count} вопросов")
    
    # Статистика по невалидным темам
    if topic_stats.get('invalid_topics'):
        print(f"\n❌ НЕВАЛИДНЫЕ ТЕМЫ (НЕ найдены в БД):")
        for topic, count in topic_stats['invalid_topics'].items():
            print(f"  • {topic}: {count} вопросов (ОТКЛОНЕНЫ)")
    
    # Рекомендации
    if topic_stats.get('invalid_topics'):
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        print(f"  • Проверьте названия тем в PDF файле")
        print(f"  • Убедитесь, что темы точно соответствуют темам в базе данных")
        print(f"  • Добавьте недостающие темы через админ-панель бота")
    
    print(f"\n{'='*80}")

def main():
    """Основная функция для обработки PDF файлов."""
    # Инициализируем сервисы один раз
    db = get_sync_database_facade()
    ai_service = ImprovedAIService()
    processor = PDFProcessor(db=db, ai_service=ai_service)
    
    # Список PDF файлов для обработки
    pdf_files = [
        "files/file1.pdf",  # Первый правильно отформатированный файл
        "files/file2.pdf"   # Второй файл с математическими задачами
    ]
    
    total_questions = 0
    total_saved = 0
    
    for pdf_file in pdf_files:
        if not os.path.exists(pdf_file):
            print(f"❌ Файл не найден: {pdf_file}")
            continue
            
        print(f"\n{'='*60}")
        print(f"🔄 Обрабатываю файл: {pdf_file}")
        print(f"{'='*60}")
        
        try:
            questions, topic_stats = processor.process_pdf_file(pdf_file)
            print(f"✅ Успешно обработано {len(questions)} валидных вопросов из {pdf_file}")
            
            # Добавляем вопросы в базу данных
            db_stats = {'saved_count': 0, 'topic_stats': {}}
            if questions:
                print(f"\n🔄 Добавляю {len(questions)} вопросов в базу данных...")
                db_stats = add_questions_to_db(questions, db, ai_service)
                print(f"✅ Вопросы успешно добавлены в базу данных")
            
            # Печатаем детальный отчет
            print_processing_report(pdf_file, questions, topic_stats, db_stats)
            
            total_questions += len(questions)
            total_saved += db_stats.get('saved_count', 0)
            
        except Exception as e:
            print(f"❌ Ошибка при обработке {pdf_file}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"🎉 ИТОГОВАЯ СТАТИСТИКА:")
    print(f"  • Всего обработано валидных вопросов: {total_questions}")
    print(f"  • Всего добавлено в БД: {total_saved}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main() 