#!/usr/bin/env python3
"""
Скрипт для поиска и исправления вопросов с несоответствием между ответом и объяснением.
Использует валидацию из QuestionService для проверки соответствия.
"""

import sys
import os
import logging
import sqlite3
import re

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
            logging.FileHandler('fix_answer_explanation_log.txt', encoding='utf-8')
        ]
    )

def extract_number_from_explanation(explanation: str):
    """
    Извлекает числовой результат из объяснения.
    
    Returns:
        float or None: Найденное число или None
    """
    calculation_patterns = [
        r'=\s*(-?\d+(?:[.,]\d+)?)',  # = 24, = 26.5
        r'равно\s*(-?\d+(?:[.,]\d+)?)',  # равно 24
        r'составляет\s*(-?\d+(?:[.,]\d+)?)',  # составляет 24
        r'получается\s*(-?\d+(?:[.,]\d+)?)',  # получается 24
        r'итого\s*(-?\d+(?:[.,]\d+)?)',  # итого 24
        r'ответ:?\s*(-?\d+(?:[.,]\d+)?)',  # ответ: 24
        r'периметр:?\s*.*?=\s*(-?\d+(?:[.,]\d+)?)',  # периметр: ... = 24
    ]
    
    for pattern in calculation_patterns:
        matches = re.findall(pattern, explanation, re.IGNORECASE)
        if matches:
            try:
                # Берем последнее найденное число (обычно финальный результат)
                return float(matches[-1].replace(',', '.'))
            except ValueError:
                continue
    
    return None

def check_and_fix_answer_explanation_mismatch(db_path: str = 'math_bot.db'):
    """
    Проверяет и исправляет вопросы с несоответствием между ответом и объяснением.
    
    Returns:
        int: Количество исправленных вопросов
    """
    logging.info("🔍 Начинаем поиск вопросов с несоответствием ответа и объяснения...")
    
    # Инициализируем сервисы
    db = Database(db_path)
    ai_service = AIService()
    question_service = QuestionService(db, ai_service)
    
    fixed_count = 0
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Получаем все вопросы
        cursor.execute('''
            SELECT id, question, answer, explanation
            FROM questions 
            WHERE explanation IS NOT NULL AND explanation != ''
            AND answer IS NOT NULL AND answer != ''
            ORDER BY id
        ''')
        
        questions = cursor.fetchall()
        logging.info(f"📊 Найдено {len(questions)} вопросов для проверки")
        
        for question_id, question_text, current_answer, explanation in questions:
            # Проверяем соответствие с помощью валидации из QuestionService
            is_consistent = question_service._validate_answer_explanation_consistency(current_answer, explanation)
            
            if not is_consistent:
                logging.warning(f"❌ Вопрос ID {question_id}: несоответствие между ответом и объяснением")
                logging.info(f"   Текущий ответ: '{current_answer}'")
                
                # Пытаемся извлечь правильный ответ из объяснения
                explanation_number = extract_number_from_explanation(explanation)
                
                if explanation_number is not None:
                    # Определяем единицы измерения из текущего ответа
                    current_answer_parts = current_answer.split()
                    if len(current_answer_parts) > 1:
                        unit = ' '.join(current_answer_parts[1:])
                        corrected_answer = f"{explanation_number} {unit}".strip()
                    else:
                        corrected_answer = str(explanation_number)
                    
                    logging.info(f"   Исправленный ответ: '{corrected_answer}' (из объяснения: {explanation_number})")
                    
                    # Обновляем ответ в базе данных
                    cursor.execute('''
                        UPDATE questions 
                        SET answer = ?
                        WHERE id = ?
                    ''', (corrected_answer, question_id))
                    
                    fixed_count += 1
                    logging.info(f"✅ Исправлен вопрос ID {question_id}: ответ изменен с '{current_answer}' на '{corrected_answer}'")
                else:
                    logging.warning(f"⚠️  Вопрос ID {question_id}: не удалось извлечь правильный ответ из объяснения")
                    logging.info(f"   Объяснение: {explanation[:200]}...")
            else:
                logging.debug(f"✓ Вопрос ID {question_id}: ответ соответствует объяснению")
        
        conn.commit()
    
    return fixed_count

def main():
    """Основная функция."""
    setup_logging()
    
    try:
        logging.info("🚀 Запуск скрипта исправления несоответствий ответа и объяснения")
        
        fixed_count = check_and_fix_answer_explanation_mismatch()
        
        if fixed_count > 0:
            logging.info(f"✅ ЗАВЕРШЕНО: Исправлено {fixed_count} вопросов")
            logging.info("📝 Теперь все ответы соответствуют объяснениям")
        else:
            logging.info("✅ ЗАВЕРШЕНО: Все вопросы уже корректны")
        
        logging.info("🎯 Скрипт выполнен успешно!")
        
    except Exception as e:
        logging.error(f"❌ ОШИБКА: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 