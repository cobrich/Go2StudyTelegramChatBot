import os
import logging
import fitz  # PyMuPDF
import re
from PIL import Image
from typing import List, Dict, Optional
import sqlite3  # <--- добавлено для работы с БД
from .database import Database
from .ai_service import AIService
from src.config.constants import TOPICS

class PDFProcessor:
    def __init__(self, output_dir: str = "question_images"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Regular expressions for test questions
        self.test_patterns = {
            'ru': [
                r'^\d+[\.\)]\s*[А-Я]',  # Russian numbering with letter
                r'^\d+[\.\)]\s*[A-Z]',  # Russian numbering with Latin letter
                r'^\d+[\.\)]\s*[а-я]',  # Russian numbering with lowercase letter
            ],
            'kk': [
                r'^\d+[\.\)]\s*[А-Я]',  # Kazakh numbering with letter
                r'^\d+[\.\)]\s*[A-Z]',  # Kazakh numbering with Latin letter
                r'^\d+[\.\)]\s*[а-я]',  # Kazakh numbering with lowercase letter
            ]
        }
        
        # Regular expressions for quantitative questions
        self.quantitative_patterns = {
            'ru': [
                r'[А-Я]\.\s*[А-Я]',  # Russian letter comparison
                r'[A-Z]\.\s*[A-Z]',  # Latin letter comparison
            ],
            'kk': [
                r'[А-Я]\.\s*[А-Я]',  # Kazakh letter comparison
                r'[A-Z]\.\s*[A-Z]',  # Latin letter comparison
            ]
        }

    def detect_language(self, text: str) -> str:
        """Detect language based on content."""
        # Check content for Kazakh characters
        kazakh_chars = set('әіңғүұқөһӘІҢҒҮҰҚӨҺ')
        if any(char in text for char in kazakh_chars):
            return 'kk'
        return 'ru'

    def is_test_question(self, text: str, language: str) -> bool:
        """Check if the text matches test question patterns."""
        return any(re.match(pattern, text.strip()) for pattern in self.test_patterns[language])

    def is_quantitative_question(self, text: str, language: str) -> bool:
        """Check if the text matches quantitative question patterns."""
        return any(re.search(pattern, text) for pattern in self.quantitative_patterns[language])

    def extract_topic_from_text(self, text: str) -> Optional[str]:
        """Extract topic from text if it's a topic header (строго из TOPICS)."""
        clean = text.strip().lower()
        for topic in TOPICS:
            if clean == topic.strip().lower():
                return topic
        return None

    def extract_questions_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extract questions from PDF file."""
        questions = []
        current_question = None
        current_topic = None
        language = 'ru'  # Default language
        found_first_topic = False
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if page_num == 0:
                    language = self.detect_language(text)
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    # Явно ищем первую тему из TOPICS
                    if not found_first_topic:
                        topic = self.extract_topic_from_text(line)
                        if topic:
                            current_topic = topic
                            found_first_topic = True
                        continue
                    # После первой темы ищем только новые темы
                    topic = self.extract_topic_from_text(line)
                    if topic:
                        current_topic = topic
                        continue
                    # Игнорируем служебные строки (например, "Рецензент")
                    if line.lower().startswith('рецензент'):
                        continue
                    # Если нет текущей темы — не сохраняем вопрос
                    if not current_topic:
                        continue
                    # Check if this is a new question
                    if self.is_test_question(line, language) or self.is_quantitative_question(line, language):
                        if current_question:
                            questions.append(current_question)
                        current_question = {
                            'text': line,
                            'type': 'quantitative' if self.is_quantitative_question(line, language) else 'test',
                            'language': language,
                            'topic': current_topic,
                            'image_paths': []
                        }
                    elif current_question:
                        current_question['text'] += '\n' + line
            if current_question:
                questions.append(current_question)
            for question in questions:
                question['image_paths'] = self.extract_images_for_question(pdf_path, question)
            return questions
        except Exception as e:
            logging.error(f"Error extracting questions from {pdf_path}: {e}")
            return []

    def extract_images_for_question(self, pdf_path: str, question: Dict) -> List[str]:
        """Extract images associated with a question."""
        image_paths = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Generate unique filename
                    image_filename = f"q_{len(image_paths)}_{os.path.basename(pdf_path)}_{page_num}_{img_index}.png"
                    image_path = os.path.join(self.output_dir, image_filename)
                    
                    # Save image
                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)
                        
                    image_paths.append(image_path)
                    
            return image_paths
            
        except Exception as e:
            logging.error(f"Error extracting images from {pdf_path}: {e}")
            return []

    def process_pdf_file(self, pdf_path: str) -> List[Dict]:
        """Process a PDF file and extract questions with images."""
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
                
            questions = self.extract_questions_from_pdf(pdf_path)
            return questions
            
        except Exception as e:
            logging.error(f"Error processing {pdf_path}: {e}")
            return []

def add_questions_to_db(questions: List[Dict], db: Database):
    """Add questions to database if they don't exist (by text)."""
    import time
    ai = AIService()
    total = len(questions)
    print(f"[LOG] Начинаю добавление {total} вопросов в базу...")
    saved_count = 0
    with open('added_questions.log', 'a', encoding='utf-8') as logf:
        for idx, q in enumerate(questions, 1):
            question_text = q['text'].strip()
            topic = q.get('topic', 'Общие вопросы')
            # Check for uniqueness by text
            exists = db.get_explanation_by_question_text(question_text)
            if exists:
                continue
            short_text = question_text[:50].replace('\n', ' ')
            print(f"[LOG][{idx}/{total}] Нормализация вопроса (тема: {topic}): {short_text}...")
            norm = ai.normalize_question_via_gemini(question_text)
            if norm and norm.get('answer') and norm.get('explanation') and norm.get('question') and norm.get('options'):
                answer_letter = norm['answer']
                if isinstance(answer_letter, str) and answer_letter.upper() in 'ABCD':
                    answer_idx = ord(answer_letter.upper()) - ord('A')
                    if 0 <= answer_idx < len(norm['options']):
                        db_question = {
                            'topic': topic,
                            'question': norm['question'],
                            'answer': norm['options'][answer_idx],
                            'explanation': norm['explanation'],
                            'incorrect_options': '\n'.join([opt for i,opt in enumerate(norm['options']) if i != answer_idx]),
                            'question_type': q.get('type', 'standard')
                        }
                        print(f"[LOG][{idx}] Gemini OK: {norm['question'][:40]}... [Ответ: {norm['answer']}]" )
                        with sqlite3.connect(db.db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO questions (topic, question, answer, explanation, incorrect_options, question_type)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (db_question['topic'], db_question['question'], db_question['answer'], 
                                 db_question['explanation'], db_question['incorrect_options'], db_question['question_type']))
                            conn.commit()
                        logf.write(f"Added: {db_question['question']}\n")
                        saved_count += 1
                    else:
                        print(f"[LOG][{idx}] Gemini FAIL: некорректный индекс ответа!")
                else:
                    print(f"[LOG][{idx}] Gemini FAIL: некорректная буква ответа!")
            else:
                print(f"[LOG][{idx}] Gemini FAIL: не удалось структурировать вопрос или отсутствует ответ/объяснение!")
            if idx % 10 == 0 or idx == total:
                print(f"[LOG] Добавлено {saved_count}/{total} вопросов...")
    print(f"[LOG] Все вопросы обработаны!")
    print(f"[LOG] Всего вопросов в файле: {total}")
    print(f"[LOG] Сохранено в базу: {saved_count}")

def main():
    print("[LOG] Запуск обработки PDF...")
    processor = PDFProcessor()
    db = Database()
    pdf_file = os.path.join("files", "NIS.pdf")
    
    if os.path.exists(pdf_file):
        print(f"[LOG] Обработка файла: {pdf_file}")
        questions = processor.process_pdf_file(pdf_file)
        print(f"[LOG] Найдено {len(questions)} вопросов. Начинаю добавление в базу...")
        add_questions_to_db(questions, db)
    else:
        print(f"[LOG] Файл не найден: {pdf_file}")

if __name__ == "__main__":
    main() 