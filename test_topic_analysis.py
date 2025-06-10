#!/usr/bin/env python3
"""
Тест для анализа определения тем AI на основе заголовков из PDF и первых вопросов.
Показывает, как AI анализирует строки типа "Тема: название" и первый вопрос темы.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from services.topic_manager import TopicManager
from services.ai_service import AIService
import re

def test_topic_analysis_from_pdf():
    """Тестирует анализ тем из PDF файла."""
    
    # Примеры данных из file1.pdf (реальные заголовки и первые вопросы)
    test_cases = [
        {
            "pdf_topic_header": "Тема: Арифметика - Дроби, проценты, уравнения (90)",
            "first_question": "Решите уравнение: 4(x - 5)/10 + 12 = 4(13 - 9)/(20 + 9)",
            "expected_analysis": "Должно быть 'Простейшие уравнения' (есть переменная x и знак равенства)"
        },
        {
            "pdf_topic_header": "Тема: Арифметика - Дроби, проценты, уравнения (90)", 
            "first_question": "2,46 × 18 =",
            "expected_analysis": "Должно быть 'Десятичные дроби' (операция с десятичным числом)"
        },
        {
            "pdf_topic_header": "Тема: Геометрия - Углы, площади, периметры (45)",
            "first_question": "Найдите площадь прямоугольника со сторонами 8 см и 12 см",
            "expected_analysis": "Должно быть 'Периметр и площадь' (вычисление площади фигуры)"
        },
        {
            "pdf_topic_header": "Тема: Проценты и пропорции (25)",
            "first_question": "Найдите 15% от 240",
            "expected_analysis": "Должно быть 'Нахождение процента от числа' (есть % и 'от числа')"
        },
        {
            "pdf_topic_header": "Тема: Масштаб и единицы измерения (20)",
            "first_question": "Расстояние на карте между городами Шымкент и Астана равно 5.5 см. Масштаб карты: 1 : 1 000 000 Каково расстояние между городами на местности?",
            "expected_analysis": "Должно быть 'Перевод единиц' (масштаб, преобразование единиц)"
        },
        {
            "pdf_topic_header": "Тема: Числовые последовательности (15)",
            "first_question": "Найдите следующее число в последовательности: 2, 5, 8, 11, ?",
            "expected_analysis": "Должно быть 'Числовые последовательности' (поиск закономерности)"
        }
    ]
    
    topic_manager = TopicManager()
    ai_service = AIService()
    
    print("🧪 ТЕСТ АНАЛИЗА ТЕМ ИЗ PDF")
    print("="*80)
    print("Тестируем, как AI анализирует заголовки тем и первые вопросы из PDF файлов")
    print("="*80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 ТЕСТ {i}")
        print("-" * 60)
        print(f"📄 Заголовок из PDF: {test_case['pdf_topic_header']}")
        print(f"❓ Первый вопрос: {test_case['first_question'][:100]}...")
        print(f"🎯 Ожидаемый анализ: {test_case['expected_analysis']}")
        
        # Извлекаем название темы из заголовка (как это делает PDF processor)
        topic_match = re.match(r'Тема:\s*([^(]+)\((\d+)\)', test_case['pdf_topic_header'])
        if topic_match:
            original_topic_name = topic_match.group(1).strip()
            question_count = topic_match.group(2)
            print(f"📝 Извлеченное название: '{original_topic_name}' ({question_count} вопросов)")
        else:
            original_topic_name = "Неизвестная тема"
            print(f"❌ Не удалось извлечь название темы")
        
        try:
            # Анализируем тему с помощью AI (как это делает TopicManager)
            print(f"\n🤖 Анализ AI...")
            ai_determined_topic = topic_manager._normalize_topic_with_ai(
                original_topic_name, 
                test_case['first_question']
            )
            
            print(f"✅ AI определил тему: '{ai_determined_topic}'")
            
            # Проверяем правильность
            if "уравнение" in test_case['first_question'].lower() and "x" in test_case['first_question']:
                expected = "Простейшие уравнения"
            elif "," in test_case['first_question'] and any(op in test_case['first_question'] for op in ['×', '*', '+', '-', '÷', '/']):
                expected = "Десятичные дроби"
            elif "%" in test_case['first_question'] and "от" in test_case['first_question']:
                expected = "Нахождение процента от числа"
            elif "площадь" in test_case['first_question'].lower():
                expected = "Периметр и площадь"
            elif "масштаб" in test_case['first_question'].lower():
                expected = "Перевод единиц"
            elif "последовательност" in test_case['first_question'].lower():
                expected = "Числовые последовательности"
            else:
                expected = "Неопределено"
            
            if ai_determined_topic == expected:
                print(f"🎉 ПРАВИЛЬНО! Тема определена корректно")
            else:
                print(f"⚠️  ВНИМАНИЕ! Ожидалось: '{expected}', получено: '{ai_determined_topic}'")
                
        except Exception as e:
            print(f"❌ Ошибка при анализе: {e}")
        
        print("-" * 60)
    
    print(f"\n{'='*80}")
    print("🏁 ТЕСТ ЗАВЕРШЕН")
    print("="*80)

def test_direct_ai_analysis():
    """Тестирует прямой анализ AI без TopicManager."""
    print(f"\n🔬 ПРЯМОЙ ТЕСТ AI АНАЛИЗА")
    print("="*50)
    
    ai_service = AIService()
    
    # Тестовые вопросы
    test_questions = [
        "Решите уравнение: x + 5 = 12",
        "2,46 × 18 =", 
        "Найдите 25% от 80",
        "Расстояние на карте 5 см, масштаб 1:1000000",
        "Найдите площадь квадрата со стороной 6 см"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. Вопрос: {question}")
        
        try:
            # Создаем простой промпт для AI
            prompt = f"""Определи математическую тему для вопроса: "{question}"

Доступные темы:
- Простейшие уравнения
- Десятичные дроби  
- Нахождение процента от числа
- Перевод единиц
- Периметр и площадь
- Арифметические операции

Ответь только названием темы."""

            response = ai_service.model.generate_content(prompt)
            ai_topic = response.text.strip()
            print(f"   AI ответ: {ai_topic}")
            
        except Exception as e:
            print(f"   Ошибка: {e}")

def main():
    """Основная функция."""
    print("🚀 ТЕСТИРОВАНИЕ АНАЛИЗА ТЕМ AI")
    print("Этот тест показывает, как AI анализирует заголовки тем из PDF и первые вопросы")
    
    try:
        test_topic_analysis_from_pdf()
        test_direct_ai_analysis()
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 