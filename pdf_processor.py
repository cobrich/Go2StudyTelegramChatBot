import os
import logging
from typing import List, Dict, Optional
import fitz  # PyMuPDF
import re
from PIL import Image
import io

class PDFProcessor:
    def __init__(self, output_dir: str = "question_images"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Регулярные выражения для определения типа вопроса
        self.test_question_patterns = {
            'ru': [
                r'Выберите правильный ответ',
                r'Укажите правильный ответ',
                r'Выберите верный ответ',
                r'Какой ответ верный',
                r'Какой из ответов правильный'
            ],
            'kk': [
                r'Дұрыс жауапты таңдаңыз',
                r'Дұрыс жауабын көрсетіңіз',
                r'Дұрыс жауапты белгілеңіз',
                r'Қай жауап дұрыс',
                r'Қайсы жауап дұрыс'
            ]
        }
        
        self.quantitative_patterns = {
            'ru': [
                r'Сравните величины',
                r'Какая величина больше',
                r'Какая величина меньше',
                r'Укажите соотношение'
            ],
            'kk': [
                r'Шамаларды салыстырыңыз',
                r'Қай шама үлкен',
                r'Қай шама кіші',
                r'Қатынасты көрсетіңіз'
            ]
        }

    def detect_language(self, text: str) -> str:
        """Определяет язык текста на основе кириллицы и казахских символов"""
        kazakh_chars = set('әіңғүұқөһӘІҢҒҮҰҚӨҺ')
        text_chars = set(text)
        if kazakh_chars.intersection(text_chars):
            return 'kk'
        return 'ru'

    def is_test_question(self, text: str, language: str) -> bool:
        """Определяет, является ли вопрос тестовым"""
        patterns = self.test_question_patterns.get(language, [])
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    def is_quantitative_question(self, text: str, language: str) -> bool:
        """Определяет, является ли вопрос количественным"""
        patterns = self.quantitative_patterns.get(language, [])
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    def extract_questions_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Извлекает вопросы из PDF файла"""
        questions = []
        doc = fitz.open(pdf_path)
        
        # Определяем язык документа по имени файла
        filename = os.path.basename(pdf_path).lower()
        language = 'kk' if 'казакша' in filename or 'казахша' in filename or 'нуска' in filename else 'ru'
        
        current_question = None
        current_text = []
        
        for page in doc:
            text = page.get_text()
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Проверяем, является ли строка началом нового вопроса
                if re.match(r'^\d+[\.\)]', line) or re.match(r'^[А-Я]\.', line):
                    if current_question:
                        current_question['text'] = '\n'.join(current_text)
                        questions.append(current_question)
                    
                    current_question = {
                        'text': '',
                        'type': 'unknown',
                        'language': language,
                        'page_number': page.number + 1,
                        'image_paths': []
                    }
                    current_text = [line]
                else:
                    if current_question:
                        current_text.append(line)
        
        # Добавляем последний вопрос
        if current_question:
            current_question['text'] = '\n'.join(current_text)
            questions.append(current_question)
        
        # Определяем тип каждого вопроса
        for question in questions:
            text = question['text']
            if self.is_test_question(text, language):
                question['type'] = 'test'
            elif self.is_quantitative_question(text, language):
                question['type'] = 'quantitative'
        
        return questions

    def extract_images_for_question(self, pdf_path: str, question: Dict) -> List[str]:
        """Извлекает изображения для вопроса"""
        image_paths = []
        doc = fitz.open(pdf_path)
        page = doc[question['page_number'] - 1]
        
        # Получаем все изображения на странице
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # Сохраняем изображение
            image_filename = f"q_{len(image_paths)}_{os.path.basename(pdf_path)}.png"
            image_path = os.path.join(self.output_dir, image_filename)
            
            with open(image_path, "wb") as image_file:
                image_file.write(image_bytes)
            
            image_paths.append(image_path)
        
        return image_paths

    def process_pdf_file(self, pdf_path: str) -> List[Dict]:
        """Обрабатывает PDF файл и извлекает вопросы с изображениями"""
        questions = self.extract_questions_from_pdf(pdf_path)
        
        for question in questions:
            try:
                image_paths = self.extract_images_for_question(pdf_path, question)
                question['image_paths'] = image_paths
            except Exception as e:
                logging.error(f"Error extracting images for question: {e}")
                question['image_paths'] = []
        
        return questions

def main():
    # Пример использования
    processor = PDFProcessor()
    pdf_files = [
        "files/Колич характ (рус).pdf",
        "files/Математика,_10_вариантов,_на_русском.pdf",
        "files/Абай рус.pdf",
        "files/Математика, 10 нуска, казакша.pdf"
    ]
    
    for pdf_file in pdf_files:
        try:
            questions = processor.process_pdf_file(pdf_file)
            print(f"Processed {len(questions)} questions from {pdf_file}")
            for q in questions:
                print(f"Question type: {q['type']}, Language: {q['language']}, Images: {len(q['image_paths'])}")
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")

if __name__ == "__main__":
    main() 