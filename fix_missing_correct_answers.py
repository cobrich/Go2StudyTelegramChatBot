#!/usr/bin/env python3
"""
Скрипт для исправления вопросов, у которых правильный ответ отсутствует в вариантах ответов.
Эта проблема возникала из-за ошибки в логике формирования вариантов.
"""

import sys
import os
import logging
import sqlite3

# Добавляем путь к проекту
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

def setup_logging():
    """Настройка логирования."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('fix_missing_answers_log.txt', encoding='utf-8')
        ]
    )

def check_and_fix_missing_correct_answers(db_path: str = 'math_bot.db'):
    """
    Проверяет и исправляет вопросы, у которых правильный ответ отсутствует в вариантах.
    
    Returns:
        int: Количество исправленных вопросов
    """
    logging.info("🔍 Начинаем поиск вопросов с отсутствующими правильными ответами...")
    
    fixed_count = 0
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Получаем все вопросы с их вариантами ответов
        cursor.execute('''
            SELECT id, question, answer, incorrect_options
            FROM questions 
            WHERE incorrect_options IS NOT NULL AND incorrect_options != ''
            ORDER BY id
        ''')
        
        questions = cursor.fetchall()
        logging.info(f"📊 Найдено {len(questions)} вопросов с вариантами ответов")
        
        for question_id, question_text, correct_answer, incorrect_options in questions:
            # Парсим варианты ответов
            if isinstance(incorrect_options, str):
                options = [opt.strip() for opt in incorrect_options.split('\n') if opt.strip()]
            else:
                options = []
            
            # Проверяем, есть ли правильный ответ в вариантах
            if correct_answer not in options:
                logging.warning(f"❌ Вопрос ID {question_id}: правильный ответ '{correct_answer}' отсутствует в вариантах: {options}")
                
                # Добавляем правильный ответ к вариантам
                options.append(correct_answer)
                
                # Обновляем в базе данных
                new_incorrect_options = '\n'.join(options)
                cursor.execute('''
                    UPDATE questions 
                    SET incorrect_options = ?
                    WHERE id = ?
                ''', (new_incorrect_options, question_id))
                
                fixed_count += 1
                logging.info(f"✅ Исправлен вопрос ID {question_id}: добавлен правильный ответ в варианты")
            else:
                logging.debug(f"✓ Вопрос ID {question_id}: правильный ответ присутствует в вариантах")
        
        conn.commit()
    
    return fixed_count

def main():
    """Основная функция."""
    setup_logging()
    
    try:
        logging.info("🚀 Запуск скрипта исправления отсутствующих правильных ответов")
        
        fixed_count = check_and_fix_missing_correct_answers()
        
        if fixed_count > 0:
            logging.info(f"✅ ЗАВЕРШЕНО: Исправлено {fixed_count} вопросов")
            logging.info("📝 Теперь все вопросы содержат правильный ответ в вариантах")
        else:
            logging.info("✅ ЗАВЕРШЕНО: Все вопросы уже корректны")
        
        logging.info("🎯 Скрипт выполнен успешно!")
        
    except Exception as e:
        logging.error(f"❌ ОШИБКА: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 