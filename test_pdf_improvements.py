#!/usr/bin/env python3
"""
Тест для проверки улучшений PDF процессора.
"""

from src.services.pdf_processor import PDFProcessor

def test_improved_parsing():
    """Тестирование улучшенной логики парсинга."""
    
    processor = PDFProcessor()
    
    # Тестовый текст с проблематичными случаями
    test_text = """
Тема: Пропорция и разность(5)

1. В саду растут яблоневые и грушевые деревья, отношение их количеств равно
2:1. Грушевых деревьев на 6 меньше, чем яблоневых. Найдите общее количество
яблоневых и грушевых деревьев в саду.
A) 12 деревьев
B) 18 деревьев ✅
C) 24 дерева  
D) 30 деревьев

2. Два числа относятся как 3:4. Если первое число увеличить на 6, а второе на 8,
то отношение станет равным 5:6. Найдите эти числа.
A) 9 и 12 ✅
B) 12 и 16
C) 15 и 20
D) 18 и 24

3:4 - это соотношение, не начало вопроса!

3. Решите пропорцию: x/5 = 12/15
A) x = 3
B) x = 4 ✅  
C) x = 5
D) x = 6

15 - это просто число на странице

4. длины сторон треугольника относятся как 2:3:4.
Периметр треугольника равен 36 см. Найдите длины сторон.
A) 6, 9, 12 см
B) 8, 12, 16 см ✅
C) 10, 15, 20 см
D) 4, 6, 8 см
"""

    print("🧪 Тестирование улучшенной логики парсинга PDF...")
    print("=" * 60)
    
    # Тестируем метод с темами
    questions, stats = processor.extract_topics_and_questions(test_text)
    
    print(f"\n📊 Результаты парсинга:")
    print(f"Найдено вопросов: {len(questions)}")
    print(f"Статистика: {stats}")
    
    print(f"\n📝 Извлеченные вопросы:")
    for i, q in enumerate(questions, 1):
        print(f"\n{i}. Тема: {q['topic']}")
        print(f"   Вопрос: {q['question'][:100]}...")
        print(f"   Варианты: {len(q['options'])}")
        print(f"   Правильный ответ: {q['correct_answer']}")
    
    # Тестируем методы валидации отдельно
    print(f"\n🔍 Тестирование методов валидации:")
    
    test_cases = [
        ("1. Это правильный вопрос?", True),
        ("2:1. Грушевых деревьев на 6 меньше", False),  # Соотношение
        ("15", False),  # Просто число
        ("3:4 - это соотношение", False),  # Соотношение в начале
        ("2. Два числа относятся как 3:4", True),  # Правильный вопрос
        ("продолжение предыдущего вопроса", False),  # Начинается с маленькой буквы
    ]
    
    for test_line, expected in test_cases:
        result = processor._is_likely_question_start(test_line)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{test_line}' → {result} (ожидалось: {expected})")
    
    # Тестируем валидацию номеров
    print(f"\n🔢 Тестирование валидации номеров:")
    
    number_tests = [
        ("1", None, None, True),
        ("2", None, 1, True),
        ("5", None, 3, False),  # Слишком большой скачок
        ("1", None, 2, False),  # Номер меньше предыдущего
        ("0", None, None, False),  # Недопустимый номер
        ("1001", None, None, False),  # Слишком большой номер
    ]
    
    for number_str, expected, last_num, expected_result in number_tests:
        result = processor._is_valid_question_number(number_str, expected, last_num)
        status = "✅" if result == expected_result else "❌"
        print(f"{status} Номер '{number_str}' (после {last_num}) → {result} (ожидалось: {expected_result})")

if __name__ == "__main__":
    test_improved_parsing() 