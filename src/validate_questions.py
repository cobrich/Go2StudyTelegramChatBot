import logging
import asyncio
from services.database import Database
from services.ai_service import AIService

async def validate_all_questions():
    """Validate and fix all questions in the database."""
    db = Database()
    ai = AIService()
    
    # Get all questions
    questions = db.get_all_questions()
    total = len(questions)
    print(f"[LOG] Начинаю проверку {total} вопросов...")
    
    fixed_count = 0
    for idx, q in enumerate(questions, 1):
        question_text = q['question']
        current_answer = q['answer']
        current_explanation = q['explanation']
        topic = q['topic']
        
        print(f"[LOG][{idx}/{total}] Проверка вопроса (тема: {topic}): {question_text[:50]}...")
        
        # Validate question
        result = ai.validate_question_answer(question_text, current_answer, current_explanation)
        
        if result:
            new_answer, new_explanation = result
            print(f"[FIX] Исправление ответа:")
            print(f"Старый ответ: {current_answer}")
            print(f"Новый ответ: {new_answer}")
            print(f"Новое объяснение: {new_explanation}")
            
            # Update question in database
            db.update_question(question_text, new_answer, new_explanation)
            fixed_count += 1
    
    print(f"[LOG] Проверка завершена. Исправлено {fixed_count} вопросов из {total}.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(validate_all_questions()) 