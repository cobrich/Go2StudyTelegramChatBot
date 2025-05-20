import os
import logging
from pdf_processor import PDFProcessor
from database import Database
from constants import TOPICS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_pdf_processing():
    # Initialize PDF processor and database
    processor = PDFProcessor()
    db = Database()
    
    # List of PDF files to process with their expected languages
    pdf_files = [
        (os.path.join("files", "Колич характ (рус).pdf"), "ru"),
        (os.path.join("files", "Математика,_10_вариантов,_на_русском.pdf"), "ru"),
        (os.path.join("files", "Математика, 10 нуска, казакша.pdf"), "kk")
    ]
    
    total_questions = 0
    questions_with_images = 0
    total_images = 0
    language_stats = {"ru": 0, "kk": 0}
    
    # Map of keywords to topics
    topic_keywords = {
        "масштаб": "Масштаб",
        "процент": "Проценты",
        "процентная": "Проценты",
        "процентное": "Проценты",
        "пропорция": "Пропорции",
        "пропорциональн": "Пропорции",
        "уравнение": "Уравнения с одним неизвестным",
        "координат": "Координатная прямая",
        "площадь": "Площади фигур",
        "периметр": "Периметр и площадь прямоугольника",
        "треугольник": "Площадь треугольника",
        "окружность": "Окружность и круг",
        "круг": "Площадь круга",
        "объем": "Объем прямоугольного параллелепипеда",
        "геометрическ": "Геометрические построения",
        "симметрия": "Симметрия",
        "среднее": "Среднее арифметическое",
        "движение": "Задачи на движение",
        "смесь": "Задачи на смеси и сплавы",
        "сплав": "Задачи на смеси и сплавы",
        "деление с остатком": "Деление с остатком",
        "римск": "Римские числа",
        "диаграмм": "Работа с диаграммами и таблицами",
        "таблиц": "Работа с диаграммами и таблицами",
        "логическ": "Логические задачи",
        "сложение": "Сложение и вычитание натуральных чисел",
        "вычитание": "Сложение и вычитание натуральных чисел",
        "умножение": "Умножение и деление натуральных чисел",
        "деление": "Умножение и деление натуральных чисел",
        "порядок действий": "Порядок действий",
        "делимость": "Делимость чисел",
        "простое число": "Простые и составные числа",
        "составное число": "Простые и составные числа",
        "дробь": "Дроби: сложение и вычитание",
        "десятичная": "Десятичные дроби",
        "сравнение дробей": "Сравнение дробей"
    }
    
    def determine_topic(question_text):
        question_text = question_text.lower()
        for keyword, topic in topic_keywords.items():
            if keyword in question_text:
                return topic
        return "Математика"  # Default topic if no specific topic is found
    
    for pdf_file, expected_language in pdf_files:
        try:
            if not os.path.exists(pdf_file):
                logging.error(f"File not found: {pdf_file}")
                continue
                
            logging.info(f"Processing {pdf_file} (expected language: {expected_language})...")
            questions = processor.process_pdf_file(pdf_file)
            
            # Log statistics
            file_questions = len(questions)
            file_images = sum(1 for q in questions if 'image_paths' in q)
            file_total_images = sum(len(q.get('image_paths', [])) for q in questions)
            total_questions += file_questions
            questions_with_images += file_images
            total_images += file_total_images
            
            # Count questions by language
            for q in questions:
                language_stats[q['language']] += 1
            
            logging.info(f"Found {file_questions} questions in {pdf_file}")
            logging.info(f"Questions with images: {file_images}")
            logging.info(f"Total images found: {file_total_images}")
            logging.info(f"Language distribution: {language_stats}")
            
            # Save questions to database
            for question in questions:
                try:
                    # Determine topic based on question text
                    topic = determine_topic(question['text'])
                    
                    db.add_task_with_image(
                        question=question['text'],
                        answer="",  # You'll need to provide correct answers
                        explanation="",  # You'll need to provide explanations
                        topic=topic,  # Use determined topic
                        level=1,
                        image_paths=question.get('image_paths', []),
                        question_type=question['type'],
                        characteristic_a=None,
                        characteristic_b=None,
                        source_file=pdf_file,
                        language=question['language']
                    )
                except Exception as e:
                    logging.error(f"Error saving question to database: {e}")
            
        except Exception as e:
            logging.error(f"Error processing {pdf_file}: {e}")
    
    # Print final statistics
    logging.info("\nProcessing Summary:")
    logging.info(f"Total PDF files processed: {len(pdf_files)}")
    logging.info(f"Total questions found: {total_questions}")
    logging.info(f"Questions with images: {questions_with_images}")
    logging.info(f"Questions without images: {total_questions - questions_with_images}")
    logging.info(f"Total images found: {total_images}")
    logging.info(f"Language distribution: {language_stats}")

if __name__ == "__main__":
    test_pdf_processing() 