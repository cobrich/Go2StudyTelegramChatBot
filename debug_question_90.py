#!/usr/bin/env python3
"""
Отладка вопроса 90 - почему он обрезается при парсинге
"""

import sys
import os
import fitz
import re

sys.path.append('.')

def debug_question_90():
    """Отладка конкретного вопроса про повара."""
    
    print("🔍 ОТЛАДКА ВОПРОСА 90")
    print("=" * 50)
    
    # Открываем PDF файл
    pdf_path = 'files/file1.pdf'
    doc = fitz.open(pdf_path)
    
    # Ищем страницу с вопросом про повара
    target_page = None
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if 'Повар использовал 2/7 всего теста' in text:
            target_page = page_num
            break
    
    if target_page is None:
        print("❌ Вопрос не найден")
        return
    
    print(f"📄 Найден на странице {target_page + 1}")
    
    # Получаем текст страницы
    page = doc[target_page]
    text = page.get_text()
    lines = text.split('\n')
    
    print(f"\n📝 Анализ строк страницы:")
    print("-" * 30)
    
    # Найдем строки с вопросом
    question_lines = []
    for i, line in enumerate(lines):
        if 'Повар' in line or 'кг теста' in line or 'Сколько всего было' in line:
            print(f"Строка {i:2d}: {repr(line)}")
            question_lines.append((i, line))
    
    print(f"\n🔧 Симуляция парсинга:")
    print("-" * 30)
    
    # Симулируем логику парсинга
    current_question = ""
    question_number = None
    
    for i, line in enumerate(lines):
        clean_line = ''.join(char for char in line if char.isprintable() or char.isspace())
        clean_line = clean_line.strip()
        
        # Проверяем, начинается ли строка с номера вопроса
        question_match = re.match(r'^(\d+)\.\s*(.+)', clean_line)
        if question_match:
            # Если у нас уже есть вопрос, сохраняем его
            if current_question:
                print(f"💾 Предыдущий вопрос: {current_question[:100]}...")
            
            # Начинаем новый вопрос
            question_number = question_match.group(1)
            current_question = question_match.group(2)
            print(f"🆕 Новый вопрос {question_number}: {repr(current_question)}")
            continue
        
        # Проверяем, является ли строка вариантом ответа
        option_match = re.match(r'^([A-D])\)\s*(.+)', clean_line)
        if option_match:
            print(f"📋 Вариант ответа: {option_match.group(1)}) {option_match.group(2)}")
            continue
        
        # Если это не вариант ответа и у нас есть текущий вопрос, это может быть продолжение
        if current_question and clean_line and len(clean_line) > 2:
            # Проверяем, что это не номер страницы или служебная информация
            if not re.match(r'^\d+$', clean_line) and not re.match(r'^[A-Z]\).*', clean_line):
                print(f"➕ Добавляем к вопросу: {repr(clean_line)}")
                if not current_question.endswith(' '):
                    current_question += " "
                current_question += clean_line
                print(f"📝 Текущий вопрос: {repr(current_question)}")
    
    print(f"\n✅ Финальный результат:")
    print(f"Вопрос {question_number}: {current_question}")
    
    print(f"\n🎯 Ожидаемый результат:")
    print("8. Повар использовал 2/7 всего теста утром и 3/5 оставшегося вечером. Осталось 24 кг теста. Сколько всего было изначально?")
    
    doc.close()

if __name__ == "__main__":
    debug_question_90() 