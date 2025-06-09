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
        questions = re.findall(r'(\d+)[.)]\s*([^\n]+)', page_text)
        print(f"Найдено вопросов: {len(questions)}")
        
        if questions:
            print("Первые 3 вопроса:")
            for i, (num, text) in enumerate(questions[:3]):
                print(f"  {num}) {text[:100]}...")
        
        # Ищем правильные ответы
        correct_answers = re.findall(r'[A-DА-Г]\)[^✅]*✅', page_text)
        print(f"Найдено правильных ответов: {len(correct_answers)}")
        
        # Ищем заголовки тем
        topics = re.findall(r'Тема:\s*([^(]+)\((\d+)\)', page_text)
        if topics:
            print(f"Найдены темы: {topics}")
    
    # Общая статистика
    print(f"\n{'='*60}")
    print("ОБЩАЯ СТАТИСТИКА:")
    print(f"{'='*60}")
    
    # Все вопросы
    all_questions = re.findall(r'(\d+)[.)]\s*([^\n]+)', full_text)
    print(f"Всего вопросов в файле: {len(all_questions)}")
    
    # Все правильные ответы
    all_correct = re.findall(r'[A-DА-Г]\)[^✅]*✅', full_text)
    print(f"Всего правильных ответов: {len(all_correct)}")
    
    # Все темы
    all_topics = re.findall(r'Тема:\s*([^(]+)\((\d+)\)', full_text)
    print(f"Всего тем: {len(all_topics)}")
    if all_topics:
        print("Список тем:")
        for topic, count in all_topics:
            print(f"  - {topic.strip()}: {count} вопросов")
    
    doc.close()
    return full_text

if __name__ == "__main__":
    # Анализируем оба PDF файла
    pdf_files = ["files/file1.pdf", "files/file2.pdf"]
    
    for pdf_file in pdf_files:
        try:
            print(f"\n{'='*80}")
            print(f"АНАЛИЗ ФАЙЛА: {pdf_file}")
            print(f"{'='*80}")
            analyze_pdf_structure(pdf_file)
        except Exception as e:
            print(f"❌ Ошибка при анализе {pdf_file}: {e}")
        
        print("\n" + "="*80 + "\n") 