#!/usr/bin/env python3
"""
Скрипт для очистки неправильно добавленных правильных ответов в поле incorrect_options.
Предыдущий скрипт ошибочно добавлял правильные ответы в варианты неправильных ответов.
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
            logging.FileHandler('cleanup_incorrect_options_log.txt', encoding='utf-8')
        ]
    )

def cleanup_incorrect_options(db_path: str = 'math_bot.db'):
    """
    Удаляет правильные ответы из поля incorrect_options.
    
    Returns:
        int: Количество исправленных вопросов
    """
    logging.info("🔍 Начинаем очистку правильных ответов из incorrect_options...")
    
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
            
            # Проверяем, есть ли правильный ответ в неправильных вариантах
            if correct_answer in options:
                logging.warning(f"❌ Вопрос ID {question_id}: правильный ответ '{correct_answer}' найден в неправильных вариантах")
                
                # Удаляем правильный ответ из неправильных вариантов
                cleaned_options = [opt for opt in options if opt != correct_answer]
                
                # Обновляем в базе данных
                new_incorrect_options = '\n'.join(cleaned_options)
                cursor.execute('''
                    UPDATE questions 
                    SET incorrect_options = ?
                    WHERE id = ?
                ''', (new_incorrect_options, question_id))
                
                fixed_count += 1
                logging.info(f"✅ Исправлен вопрос ID {question_id}: удален правильный ответ из неправильных вариантов")
                logging.info(f"   Было: {len(options)} вариантов, стало: {len(cleaned_options)} вариантов")
            else:
                logging.debug(f"✓ Вопрос ID {question_id}: правильный ответ не найден в неправильных вариантах")
        
        conn.commit()
    
    return fixed_count

def main():
    """Основная функция."""
    setup_logging()
    
    try:
        logging.info("🚀 Запуск скрипта очистки неправильных вариантов ответов")
        
        fixed_count = cleanup_incorrect_options()
        
        if fixed_count > 0:
            logging.info(f"✅ ЗАВЕРШЕНО: Исправлено {fixed_count} вопросов")
            logging.info("📝 Правильные ответы удалены из неправильных вариантов")
        else:
            logging.info("✅ ЗАВЕРШЕНО: Все вопросы уже корректны")
        
        logging.info("🎯 Скрипт выполнен успешно!")
        
    except Exception as e:
        logging.error(f"❌ ОШИБКА: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 