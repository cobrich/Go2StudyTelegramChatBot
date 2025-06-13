#!/usr/bin/env python3
"""
Второй патч для PDF процессора - улучшение extract_questions_without_topics.
"""

def apply_second_patch():
    """Применение второго патча."""
    
    with open('src/services/pdf_processor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Заменяем старый паттерн в extract_questions_without_topics
    old_pattern = """            # Проверяем на начало вопроса (любое число с закрывающей скобкой или точкой)
            question_match = re.match(r'^(\d+)[.)\s]*\s*(.+)', line)
            if question_match:"""
    
    new_pattern = """            # Проверяем на начало вопроса с улучшенной валидацией
            if self._is_likely_question_start(line):
                question_match = re.match(r'^(\d+)[.)\s]+(.+)', line)
                if question_match and self._is_valid_question_number(question_match.group(1), None, question_number):"""
    
    # Также нужно добавить переменную для отслеживания номеров
    old_vars = """        current_question = None
        current_options = []
        correct_answer = None
        question_number = 0"""
    
    new_vars = """        current_question = None
        current_options = []
        correct_answer = None
        question_number = 0
        last_question_number = None"""
    
    # Заменяем присваивание номера
    old_number_assign = """                # Начинаем новый вопрос
                question_number = int(question_match.group(1))
                current_question = question_match.group(2).strip()
                current_options = []
                correct_answer = None
                
                print(f"[LOG] Вопрос {question_number}: {current_question[:100]}...")"""
    
    new_number_assign = """                    # Начинаем новый вопрос
                    question_number = int(question_match.group(1))
                    current_question = question_match.group(2).strip()
                    current_options = []
                    correct_answer = None
                    last_question_number = question_number
                    
                    print(f"[LOG] Вопрос {question_number}: {current_question[:100]}...")"""
    
    # Применяем замены
    content = content.replace(old_pattern, new_pattern)
    content = content.replace(old_vars, new_vars)
    content = content.replace(old_number_assign, new_number_assign)
    
    with open('src/services/pdf_processor.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Второй патч применен успешно!")

if __name__ == "__main__":
    apply_second_patch() 