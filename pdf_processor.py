import os
import fitz  # PyMuPDF
import logging
from PIL import Image
import io
import re
from typing import List, Dict, Tuple, Optional

class PDFProcessor:
    def __init__(self, output_dir: str = "question_images"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Регулярные выражения для поиска вопросов
        self.question_pattern = re.compile(r'(\d+)[\.\)]\s*(.*?)(?=\d+[\.\)]|\Z)', re.DOTALL)
        self.quantitative_pattern = re.compile(r'А:\s*(.*?)\s*Б:\s*(.*?)(?=\d+[\.\)]|\Z)', re.DOTALL)
        
    def extract_questions_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Извлекает вопросы из PDF файла"""
        questions = []
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # Ищем обычные вопросы
            for match in self.question_pattern.finditer(text):
                question_num = match.group(1)
                question_text = match.group(2).strip()
                
                # Проверяем, является ли это вопросом с количественными характеристиками
                quant_match = self.quantitative_pattern.search(question_text)
                
                if quant_match:
                    # Это вопрос с количественными характеристиками
                    char_a = quant_match.group(1).strip()
                    char_b = quant_match.group(2).strip()
                    
                    # Извлекаем основной текст вопроса
                    main_question = question_text[:quant_match.start()].strip()
                    
                    questions.append({
                        'type': 'quantitative',
                        'number': question_num,
                        'question': main_question,
                        'characteristic_a': char_a,
                        'characteristic_b': char_b,
                        'page': page_num + 1
                    })
                else:
                    # Обычный вопрос
                    questions.append({
                        'type': 'standard',
                        'number': question_num,
                        'question': question_text,
                        'page': page_num + 1
                    })
        
        return questions
    
    def extract_images_for_question(self, pdf_path: str, question: Dict) -> Optional[str]:
        """Извлекает изображение для вопроса из PDF"""
        doc = fitz.open(pdf_path)
        page = doc[question['page'] - 1]
        
        # Получаем все изображения на странице
        image_list = page.get_images()
        
        if not image_list:
            return None
            
        # Берем первое изображение (можно улучшить логику выбора нужного изображения)
        xref = image_list[0][0]
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]
        
        # Сохраняем изображение
        image_filename = f"q_{question['number']}_{os.path.basename(pdf_path)}.png"
        image_path = os.path.join(self.output_dir, image_filename)
        
        with open(image_path, "wb") as image_file:
            image_file.write(image_bytes)
            
        return image_path
    
    def process_pdf_file(self, pdf_path: str) -> List[Dict]:
        """Обрабатывает PDF файл и извлекает все вопросы с изображениями"""
        questions = self.extract_questions_from_pdf(pdf_path)
        
        for question in questions:
            image_path = self.extract_images_for_question(pdf_path, question)
            if image_path:
                question['image_path'] = image_path
                
        return questions

def main():
    # Пример использования
    processor = PDFProcessor()
    pdf_files = [
        "files/Колич характ (рус).pdf",
        "files/Математика,_10_вариантов,_на_русском.pdf"
    ]
    
    for pdf_file in pdf_files:
        try:
            questions = processor.process_pdf_file(pdf_file)
            print(f"Обработано {len(questions)} вопросов из {pdf_file}")
        except Exception as e:
            logging.error(f"Ошибка при обработке {pdf_file}: {e}")

if __name__ == "__main__":
    main() 