#!/usr/bin/env python3
"""
Патч для улучшения PDF процессора.
Применяет улучшенную логику определения вопросов.
"""

def apply_pdf_processor_improvements():
    """Применение улучшений к PDF процессору."""
    
    # Читаем текущий файл
    with open('src/services/pdf_processor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Заменяем строку проверки вопроса
    old_check = """            # Проверяем на начало вопроса
            question_match = re.match(self.question_pattern, line)
            if question_match:"""
    
    new_check = """            # Проверяем на начало вопроса с улучшенной валидацией
            if self._is_likely_question_start(line):
                question_match = re.match(self.question_pattern, line)
                if question_match:
                    question_number_str = question_match.group(1)
                    
                    # Дополнительная валидация номера вопроса
                    if self._is_valid_question_number(question_number_str, None, last_question_number):"""
    
    # Заменяем инициализацию переменных
    old_init = """        current_question = None
        current_options = []
        correct_answer = None"""
    
    new_init = """        current_question = None
        current_options = []
        correct_answer = None
        last_question_number = None  # Для отслеживания последовательности"""
    
    # Заменяем присваивание номера вопроса  
    old_assign = """                # Начинаем новый вопрос
                question_number = question_match.group(1)
                current_question = question_match.group(2).strip()
                current_options = []
                correct_answer = None
                
                print(f"[LOG] Вопрос {question_number}: {current_question[:100]}...")"""
    
    new_assign = """                        # Начинаем новый вопрос
                        current_question_number = int(question_number_str)
                        current_question = question_match.group(2).strip()
                        current_options = []
                        correct_answer = None
                        last_question_number = current_question_number
                        
                        print(f"[✅ VALID_Q] Вопрос {current_question_number}: {current_question[:100]}...")"""
    
    # Применяем замены
    content = content.replace(old_check, new_check)
    content = content.replace(old_init, new_init)
    content = content.replace(old_assign, new_assign)
    
    # Сохраняем измененный файл
    with open('src/services/pdf_processor.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Патч применен успешно!")

if __name__ == "__main__":
    apply_pdf_processor_improvements() 