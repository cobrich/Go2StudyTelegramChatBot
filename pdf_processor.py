import os
import logging
import fitz  # PyMuPDF
import re
from PIL import Image
from typing import List, Dict
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from services.database import Database

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

    def detect_language(self, text: str, filename: str) -> str:
        """Detect language based on filename and content."""
        # Check filename first
        if any(keyword in filename.lower() for keyword in ['казакша', 'казахша', 'нуска']):
            return 'kk'
            
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

    def extract_questions_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extract questions from PDF file."""
        questions = []
        current_question = None
        language = 'ru'  # Default language
        
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Detect language from first page
                if page_num == 0:
                    language = self.detect_language(text, os.path.basename(pdf_path))
                
                # Split text into lines and process
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Check if this is a new question
                    if self.is_test_question(line, language) or self.is_quantitative_question(line, language):
                        if current_question:
                            questions.append(current_question)
                        current_question = {
                            'text': line,
                            'type': 'quantitative' if self.is_quantitative_question(line, language) else 'test',
                            'language': language,
                            'image_paths': []
                        }
                    elif current_question:
                        current_question['text'] += '\n' + line
                        
            # Add the last question if exists
            if current_question:
                questions.append(current_question)
                
            # Extract images for each question
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

def add_questions_to_db(questions: List[Dict], db: Database, topic: str):
    """Добавить вопросы в базу данных, если их там ещё нет (по тексту)."""
    with open('added_questions.log', 'a', encoding='utf-8') as logf:
        for q in questions:
            question_text = q['text'].strip()
            # Проверка на уникальность по тексту
            exists = db.get_explanation_by_question_text(question_text)
            if exists:
                continue
            db_path = db.db_path if hasattr(db, 'db_path') else 'math_bot.db'
            # answer, explanation, incorrect_options можно доработать вручную или парсить из PDF
            db_question = {
                'topic': topic,
                'question': question_text,
                'answer': '',  # TODO: заполнить вручную или парсить
                'explanation': '',  # TODO: заполнить вручную или парсить
                'incorrect_options': '',  # TODO: заполнить вручную или парсить
                'question_type': q.get('type', 'standard')
            }
            with db_conn(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO questions (topic, question, answer, explanation, incorrect_options, question_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (db_question['topic'], db_question['question'], db_question['answer'], db_question['explanation'], db_question['incorrect_options'], db_question['question_type']))
                conn.commit()
            logf.write(f"Added: {question_text}\n")

def db_conn(db_path):
    import sqlite3
    return sqlite3.connect(db_path)

def main():
    processor = PDFProcessor()
    db = Database()
    pdf_files = [
        os.path.join("files", "Колич характ (рус).pdf"),
        os.path.join("files", "Математика,_10_вариантов,_на_русском.pdf"),
        os.path.join("files", "Математика, 10 нуска, казакша.pdf")
    ]
    for pdf_file in pdf_files:
        if os.path.exists(pdf_file):
            questions = processor.process_pdf_file(pdf_file)
            print(f"Processed {pdf_file}: {len(questions)} questions found")
            # Определяем тему по имени файла или вручную
            if 'дроб' in pdf_file.lower():
                topic = 'Дроби'
            elif 'процент' in pdf_file.lower():
                topic = 'Проценты'
            elif 'пропорц' in pdf_file.lower():
                topic = 'Пропорции'
            elif 'уравн' in pdf_file.lower():
                topic = 'Уравнения'
            elif 'геом' in pdf_file.lower():
                topic = 'Геометрия'
            elif 'логик' in pdf_file.lower():
                topic = 'Логика'
            else:
                topic = 'Математика'
            add_questions_to_db(questions, db, topic)
        else:
            print(f"File not found: {pdf_file}")

if __name__ == "__main__":
    main() 