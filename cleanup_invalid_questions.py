#!/usr/bin/env python3
"""
Скрипт для очистки некачественных AI-вопросов из базы данных.
Использует строгую валидацию для выявления и удаления проблемных вопросов.
"""

import sys
import os
import logging

# Добавляем путь к проекту
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from src.services.database import Database
from src.services.ai_service import AIService
from src.services.question_service import QuestionService

def setup_logging():
    """Настройка логирования."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('cleanup_log.txt', encoding='utf-8')
        ]
    )

def main():
    """Основная функция очистки."""
    setup_logging()
    
    print("🧹 Запуск очистки некачественных AI-вопросов...")
    logging.info("Начинаем процесс очистки некачественных AI-вопросов")
    
    try:
        # Инициализируем сервисы
        db = Database()
        ai_service = AIService()
        question_service = QuestionService(db, ai_service)
        
        # Получаем статистику до очистки
        ai_questions_before = db.get_all_ai_questions()
        total_before = len(ai_questions_before)
        
        print(f"📊 Найдено AI-вопросов в базе: {total_before}")
        logging.info(f"Общее количество AI-вопросов до очистки: {total_before}")
        
        if total_before == 0:
            print("✅ В базе нет AI-вопросов для проверки.")
            return
        
        # Запускаем очистку
        deleted_count = question_service.cleanup_invalid_ai_questions()
        
        # Получаем статистику после очистки
        ai_questions_after = db.get_all_ai_questions()
        total_after = len(ai_questions_after)
        
        print(f"\n📈 Результаты очистки:")
        print(f"   • Было AI-вопросов: {total_before}")
        print(f"   • Удалено некачественных: {deleted_count}")
        print(f"   • Осталось качественных: {total_after}")
        print(f"   • Процент удаленных: {(deleted_count/total_before*100):.1f}%")
        
        logging.info(f"Очистка завершена. Удалено {deleted_count} из {total_before} AI-вопросов")
        
        if deleted_count > 0:
            print(f"\n✅ Очистка завершена успешно!")
            print(f"🗑️  Удалено {deleted_count} некачественных вопросов")
            print(f"📝 Подробный лог сохранен в cleanup_log.txt")
        else:
            print(f"\n✅ Все AI-вопросы прошли валидацию!")
            print(f"🎉 Некачественных вопросов не найдено")
            
    except Exception as e:
        error_msg = f"Ошибка при очистке: {e}"
        print(f"❌ {error_msg}")
        logging.error(error_msg, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 