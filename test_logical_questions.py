#!/usr/bin/env python3
"""
Тестовый скрипт для проверки парсинга файла "Тема_ Логические вопросы (31).pdf"
"""

import sys
import os
sys.path.append('src')

from services.pdf_processor import PDFProcessor

def main():
    # Путь к конкретному файлу
    pdf_path = "files/Тема_ Логические вопросы (31).pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Файл не найден: {pdf_path}")
        return
    
    print(f"🔄 Тестируем парсинг файла: {pdf_path}")
    print("=" * 80)
    
    # Создаем процессор
    processor = PDFProcessor()
    
    # Обрабатываем файл
    try:
        questions, topic_stats = processor.process_pdf_file(pdf_path)
        
        print(f"\n📊 РЕЗУЛЬТАТЫ ПАРСИНГА:")
        print(f"  • Всего извлечено вопросов: {len(questions)}")
        print(f"  • Статистика по темам: {topic_stats}")
        
        print(f"\n📝 ПЕРВЫЕ 5 ВОПРОСОВ:")
        for i, q in enumerate(questions[:5], 1):
            print(f"  [{i}] Тема: {q['topic']}")
            print(f"      Вопрос: {q['question'][:100]}...")
            print(f"      Ответ: {q['correct_answer']}")
            print(f"      Варианты: {q['options']}")
            print()
        
        # Проверяем конкретные вопросы 1, 26, 27
        print(f"\n🔍 ПРОВЕРКА КОНКРЕТНЫХ ВОПРОСОВ:")
        if len(questions) >= 1:
            print(f"  Вопрос 1: {questions[0]['question']}")
            print(f"  Ответ 1: {questions[0]['correct_answer']}")
        
        if len(questions) >= 26:
            print(f"  Вопрос 26: {questions[25]['question']}")
            print(f"  Ответ 26: {questions[25]['correct_answer']}")
        
        if len(questions) >= 27:
            print(f"  Вопрос 27: {questions[26]['question']}")
            print(f"  Ответ 27: {questions[26]['correct_answer']}")
            
    except Exception as e:
        print(f"❌ Ошибка при обработке файла: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 