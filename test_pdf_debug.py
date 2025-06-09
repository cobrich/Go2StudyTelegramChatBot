import fitz  # PyMuPDF
import re

def analyze_pdf_structure(pdf_path):
    """Анализ структуры PDF файла."""
    doc = fitz.open(pdf_path)
    
    print(f"Анализ файла: {pdf_path}")
    print(f"Количество страниц: {len(doc)}")
    
    full_text = ""
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text()
        full_text += page_text + "\n"
        
        print(f"\n=== СТРАНИЦА {page_num + 1} ===")
        print(f"Символов на странице: {len(page_text)}")
        
        # Ищем вопросы на странице
        questions = re.findall(r'(\d+)\)\s*([^\n]+)', page_text)
        print(f"Найдено вопросов: {len(questions)}")
        
        if questions:
            print("Первые 3 вопроса:")
            for i, (num, text) in enumerate(questions[:3]):
                print(f"  {num}) {text[:50]}...")
    
    doc.close()
    
    print(f"\n=== ОБЩАЯ СТАТИСТИКА ===")
    print(f"Общее количество символов: {len(full_text)}")
    
    # Ищем все вопросы в тексте
    all_questions = re.findall(r'(\d+)\)\s*([^\n]+)', full_text)
    print(f"Всего найдено вопросов: {len(all_questions)}")
    
    # Анализируем нумерацию
    question_numbers = [int(num) for num, _ in all_questions]
    if question_numbers:
        print(f"Номера вопросов: от {min(question_numbers)} до {max(question_numbers)}")
        print(f"Уникальных номеров: {len(set(question_numbers))}")
    
    # Ищем варианты ответов
    options = re.findall(r'[A-D]\)\s*[^\n]+', full_text)
    print(f"Найдено вариантов ответов: {len(options)}")
    
    # Ищем правильные ответы
    correct_answers = re.findall(r'[A-D]\)[^\n]*✅', full_text)
    print(f"Найдено правильных ответов: {len(correct_answers)}")
    
    # Показываем первые 1000 символов для анализа
    print(f"\n=== ПЕРВЫЕ 1000 СИМВОЛОВ ===")
    clean_text = ''.join(char for char in full_text[:1000] if char.isprintable() or char.isspace())
    print(repr(clean_text))

if __name__ == "__main__":
    analyze_pdf_structure("files/математика темы 180 вопросов (2).pdf") 