import os
import logging
from pdf_processor import PDFProcessor
from database import Database
from constants import TOPICS
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel(os.getenv('GEMINI_MODEL'))

async def determine_topic_with_ai(question_text: str) -> str:
    """
    Uses AI to determine the most appropriate topic for a question from our predefined list.
    Returns the topic name or 'Математика' if no specific topic is determined.
    """
    prompt = f"""Ты - эксперт по математике для 5-6 классов. Твоя задача - определить, к какой из следующих тем относится вопрос:

{', '.join(TOPICS)}

Вопрос: {question_text}

Ответь ТОЛЬКО названием темы из списка выше, без дополнительных слов или объяснений. Если вопрос не подходит ни к одной теме или подходит к нескольким, ответь 'Математика'."""
    try:
        response = model.generate_content(prompt)
        determined_topic = response.text.strip()
        if determined_topic in TOPICS:
            return determined_topic
        else:
            logging.warning(f"AI returned invalid topic '{determined_topic}' for question: {question_text[:100]}...")
            return "Математика"
    except Exception as e:
        logging.error(f"Error determining topic with AI: {e}")
        return "Математика"

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
            
            # Save questions to database with AI-determined topics
            for question in questions:
                try:
                    # Get topic using AI
                    topic = asyncio.run(determine_topic_with_ai(question['text']))
                    logging.info(f"AI determined topic '{topic}' for question: {question['text'][:100]}...")
                    
                    db.add_task_with_image(
                        question=question['text'],
                        answer="",  # You'll need to provide correct answers
                        explanation="",  # You'll need to provide explanations
                        topic=topic,  # Use AI-determined topic
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