#!/usr/bin/env python3
"""
Утилита для очистки вопросов с NULL значениями из базы данных.
Удаляет все вопросы, у которых отсутствуют обязательные поля: question, answer, explanation.
"""

import sys
import os
import sqlite3
import logging

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.database import Database

def cleanup_null_questions():
    """Удаляет вопросы с NULL значениями из базы данных."""
    
    # Инициализация логирования
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Подключение к базе данных
    db = Database()
    
    logging.info("Начинаю поиск вопросов с NULL значениями...")
    
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        
        # Найти все вопросы с NULL значениями
        cursor.execute('''
            SELECT id, topic, question, answer, explanation, source
            FROM questions 
            WHERE question IS NULL OR answer IS NULL OR explanation IS NULL
        ''')
        
        null_questions = cursor.fetchall()
        
        if not null_questions:
            logging.info("Вопросы с NULL значениями не найдены.")
            return
        
        logging.info(f"Найдено {len(null_questions)} вопросов с NULL значениями:")
        
        for question in null_questions:
            id_, topic, question_text, answer, explanation, source = question
            logging.info(f"ID: {id_}, Тема: {topic}, Источник: {source}")
            logging.info(f"  Вопрос: {question_text}")
            logging.info(f"  Ответ: {answer}")
            logging.info(f"  Объяснение: {explanation}")
            logging.info("---")
        
        # Подтверждение удаления
        confirm = input(f"\nУдалить {len(null_questions)} вопросов с NULL значениями? (y/N): ")
        
        if confirm.lower() in ['y', 'yes', 'да']:
            # Удаление вопросов с NULL значениями
            cursor.execute('''
                DELETE FROM questions 
                WHERE question IS NULL OR answer IS NULL OR explanation IS NULL
            ''')
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logging.info(f"Успешно удалено {deleted_count} вопросов с NULL значениями.")
        else:
            logging.info("Операция отменена.")

if __name__ == "__main__":
    cleanup_null_questions() 