import os
import logging
import fitz  # PyMuPDF
import re
from PIL import Image
from typing import List, Dict, Optional
from .database import Database

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
        """Extract topic from text if it's a topic header."""
        # Look for common topic patterns
        topic_patterns = [
            r'^[А-Я][А-Я\s]+:',  # Russian topic with colon
            r'^[А-Я][А-Я\s]+$',  # Russian topic without colon
            r'^[А-Я][а-яА-Я\s]+:',  # Russian topic with mixed case
            r'^[А-Я][а-яА-Я\s]+$',  # Russian topic with mixed case without colon
        ]
        
        for pattern in topic_patterns:
            match = re.match(pattern, text.strip())
            if match:
                # Clean up the topic text
                topic = match.group(0).strip(':').strip()
                return topic
        return None

    def extract_questions_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extract questions from PDF file."""
        questions = []
        current_question = None
        current_topic = None
        language = 'ru'  # Default language
        
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Detect language from first page
                if page_num == 0:
                    language = self.detect_language(text)
                
                # Split text into lines and process
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if this is a topic header
                    topic = self.extract_topic_from_text(line)
                    if topic:
                        current_topic = topic
                        continue
                        
                    # Check if this is a new question
                    if self.is_test_question(line, language) or self.is_quantitative_question(line, language):
                        if current_question:
                            questions.append(current_question)
                        current_question = {
                            'text': line,
                            'type': 'quantitative' if self.is_quantitative_question(line, language) else 'test',
                            'language': language,
                            'topic': current_topic or 'Общие вопросы',  # Use current topic or default
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

def add_questions_to_db(questions: List[Dict], db: Database):
    """Add questions to database if they don't exist (by text)."""
    with open('added_questions.log', 'a', encoding='utf-8') as logf:
        for q in questions:
            question_text = q['text'].strip()
            # Check for uniqueness by text
            exists = db.get_explanation_by_question_text(question_text)
            if exists:
                continue
                
            # answer, explanation, incorrect_options can be filled manually or parsed from PDF
            db_question = {
                'topic': q.get('topic', 'Общие вопросы'),
                'question': question_text,
                'answer': '',  # TODO: fill manually or parse
                'explanation': '',  # TODO: fill manually or parse
                'incorrect_options': '',  # TODO: fill manually or parse
                'question_type': q.get('type', 'standard')
            }
            
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO questions (topic, question, answer, explanation, incorrect_options, question_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (db_question['topic'], db_question['question'], db_question['answer'], 
                     db_question['explanation'], db_question['incorrect_options'], db_question['question_type']))
                conn.commit()
            logf.write(f"Added: {question_text}\n")

def main():
    processor = PDFProcessor()
    db = Database()
    pdf_file = os.path.join("files", "NIS.pdf")
    
    if os.path.exists(pdf_file):
        questions = processor.process_pdf_file(pdf_file)
        print(f"Processed {pdf_file}: {len(questions)} questions found")
        add_questions_to_db(questions, db)
    else:
        print(f"File not found: {pdf_file}")

if __name__ == "__main__":
    main() 