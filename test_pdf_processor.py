import os
import logging
from pdf_processor import PDFProcessor
from database import Database

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
                    db.add_task_with_image(
                        question=question['text'],
                        answer="",  # You'll need to provide correct answers
                        explanation="",  # You'll need to provide explanations
                        topic="Математика",  # You can customize the topic
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