#!/usr/bin/env python3
"""
Исправление синтаксической ошибки в PDF процессоре.
"""

def fix_syntax_error():
    """Исправление отсутствующего двоеточия."""
    
    with open('src/services/pdf_processor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Исправляем отсутствующее двоеточие
    old_line = "                if question_match and self._is_valid_question_number(question_match.group(1), None, question_number):"
    new_line = "                if question_match and self._is_valid_question_number(question_match.group(1), None, question_number):"
    
    # Исправляем основную проблему - отсутствие двоеточия после if
    content = content.replace(
        "if question_match and self._is_valid_question_number(question_match.group(1), None, question_number)",
        "if question_match and self._is_valid_question_number(question_match.group(1), None, question_number):"
    )
    
    # Также нужно правильно структурировать блок кода
    old_block = """                if question_match and self._is_valid_question_number(question_match.group(1), None, question_number):
                # Сохраняем предыдущий вопрос, если он был
                if current_question and current_options and correct_answer:"""
    
    new_block = """                if question_match and self._is_valid_question_number(question_match.group(1), None, question_number):
                    # Сохраняем предыдущий вопрос, если он был
                    if current_question and current_options and correct_answer:"""
    
    content = content.replace(old_block, new_block)
    
    # Исправляем отступы в блоке
    content = content.replace(
        "                    if len(clean_question) >= 10:\n                        # Все вопросы без заголовков тем считаются невалидными\n                        topic_stats['total_questions'] += 1\n                        topic_stats['invalid_questions'] += 1\n                        topic_stats['found_topics']['Неопределенная тема'] += 1\n                        topic_stats['invalid_topics']['Неопределенная тема'] += 1\n                        print(f\"[❌ SKIP] Вопрос без темы: {clean_question[:100]}...\")\n                \n                    # Начинаем новый вопрос\n                    question_number = int(question_match.group(1))\n                    current_question = question_match.group(2).strip()\n                    current_options = []\n                    correct_answer = None\n                    last_question_number = question_number\n                    \n                    print(f\"[LOG] Вопрос {question_number}: {current_question[:100]}...\")",
        "                        if len(clean_question) >= 10:\n                            # Все вопросы без заголовков тем считаются невалидными\n                            topic_stats['total_questions'] += 1\n                            topic_stats['invalid_questions'] += 1\n                            topic_stats['found_topics']['Неопределенная тема'] += 1\n                            topic_stats['invalid_topics']['Неопределенная тема'] += 1\n                            print(f\"[❌ SKIP] Вопрос без темы: {clean_question[:100]}...\")\n                    \n                    # Начинаем новый вопрос\n                    question_number = int(question_match.group(1))\n                    current_question = question_match.group(2).strip()\n                    current_options = []\n                    correct_answer = None\n                    last_question_number = question_number\n                    \n                    print(f\"[LOG] Вопрос {question_number}: {current_question[:100]}...\")"
    )
    
    with open('src/services/pdf_processor.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Синтаксическая ошибка исправлена!")

if __name__ == "__main__":
    fix_syntax_error() 