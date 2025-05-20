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
    
    # List of PDF files to process
    pdf_files = [
        "files/Колич характ (рус).pdf",
        "files/Математика,_10_вариантов,_на_русском.pdf",
        "files/Абай рус.pdf"
    ]
    
    total_questions = 0
    questions_with_images = 0
    
    for pdf_file in pdf_files:
        try:
            logging.info(f"Processing {pdf_file}...")
            questions = processor.process_pdf_file(pdf_file)
            
            # Log statistics
            file_questions = len(questions)
            file_images = sum(1 for q in questions if 'image_path' in q)
            total_questions += file_questions
            questions_with_images += file_images
            
            logging.info(f"Found {file_questions} questions in {pdf_file}")
            logging.info(f"Questions with images: {file_images}")
            
            # Save questions to database
            for question in questions:
                try:
                    db.add_task_with_image(
                        question=question['question'],
                        answer="",  # You'll need to provide correct answers
                        explanation="",  # You'll need to provide explanations
                        topic="Математика",  # You can customize the topic
                        level=1,
                        image_path=question.get('image_path'),
                        question_type=question['type'],
                        characteristic_a=question.get('characteristic_a'),
                        characteristic_b=question.get('characteristic_b'),
                        source_file=pdf_file
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

if __name__ == "__main__":
    test_pdf_processing() 