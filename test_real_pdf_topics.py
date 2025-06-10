#!/usr/bin/env python3
"""
Тест с реальными заголовками тем из PDF файла.
Проверяет, как AI анализирует реальные заголовки типа "Тема: Арифметика-Операции с дробями(13)".
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from services.topic_manager import TopicManager
from services.ai_service import AIService
import re

def test_real_pdf_topics():
    """Тестирует анализ реальных заголовков тем из PDF."""
    
    # Реальные заголовки из PDF файлов
    real_topics = [
        {
            "header": "Тема: Арифметика-Операции с дробями(13)",
            "first_question": "Вычислите: 2/3 + 1/4",
            "expected": "Действия с дробями",
            "note": "Все 13 вопросов должны быть про операции с дробями"
        },
        {
            "header": "Тема: Числовые закономерности(10)", 
            "first_question": "Найдите следующее число: 2, 5, 8, 11, ?",
            "expected": "Числовые последовательности",
            "note": "Все 10 вопросов должны быть про закономерности"
        },
        {
            "header": "Тема: Геометрия-Площади и периметры(15)",
            "first_question": "Найдите площадь квадрата со стороной 6 см",
            "expected": "Периметр и площадь", 
            "note": "Все 15 вопросов должны быть про площади и периметры"
        },
        {
            "header": "Тема: Проценты и пропорции(8)",
            "first_question": "Найдите 25% от 120",
            "expected": "Нахождение процента от числа",
            "note": "Все 8 вопросов должны быть про проценты"
        },
        {
            "header": "Тема: Простые уравнения(12)",
            "first_question": "Решите уравнение: x + 7 = 15",
            "expected": "Простейшие уравнения",
            "note": "Все 12 вопросов должны быть про уравнения"
        }
    ]
    
    topic_manager = TopicManager()
    
    print("🧪 ТЕСТ РЕАЛЬНЫХ ЗАГОЛОВКОВ ТЕМ ИЗ PDF")
    print("="*80)
    print("Проверяем, как AI анализирует реальные заголовки из PDF файлов")
    print("="*80)
    
    for i, topic_data in enumerate(real_topics, 1):
        print(f"\n📋 ТЕСТ {i}")
        print("-" * 70)
        print(f"📄 Заголовок: {topic_data['header']}")
        print(f"❓ Первый вопрос: {topic_data['first_question']}")
        print(f"🎯 Ожидаемая тема: {topic_data['expected']}")
        print(f"📝 Примечание: {topic_data['note']}")
        
        # Извлекаем название темы из заголовка
        topic_match = re.match(r'Тема:\s*([^(]+)\((\d+)\)', topic_data['header'])
        if topic_match:
            original_topic_name = topic_match.group(1).strip()
            question_count = int(topic_match.group(2))
            print(f"📊 Извлечено: '{original_topic_name}' ({question_count} вопросов)")
        else:
            print(f"❌ Не удалось извлечь название темы")
            continue
        
        try:
            # Анализируем с помощью AI
            print(f"\n🤖 AI анализ...")
            ai_topic = topic_manager._normalize_topic_with_ai(
                original_topic_name, 
                topic_data['first_question']
            )
            
            print(f"✅ AI определил: '{ai_topic}'")
            
            # Проверяем правильность
            if ai_topic == topic_data['expected']:
                print(f"🎉 ОТЛИЧНО! Тема определена правильно")
                print(f"   Все {question_count} вопросов получат тему: '{ai_topic}'")
            else:
                print(f"⚠️  ПРОБЛЕМА! Ожидалось: '{topic_data['expected']}'")
                print(f"   Все {question_count} вопросов получат неправильную тему: '{ai_topic}'")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        print("-" * 70)
    
    print(f"\n{'='*80}")
    print("🏁 ТЕСТ ЗАВЕРШЕН")
    print("="*80)

def test_problematic_mixed_topics():
    """Тестирует проблемные смешанные темы."""
    print(f"\n🔍 ТЕСТ ПРОБЛЕМНЫХ СМЕШАННЫХ ТЕМ")
    print("="*60)
    
    # Проблемные заголовки, которые содержат несколько тем
    mixed_topics = [
        {
            "header": "Тема: Арифметика - Дроби, проценты, уравнения(90)",
            "questions": [
                "Решите уравнение: x + 5 = 12",  # Уравнение
                "Вычислите: 2,5 × 4",            # Десятичные дроби  
                "Найдите 20% от 150",            # Проценты
                "Сложите дроби: 1/3 + 1/6"      # Обыкновенные дроби
            ],
            "problem": "Один заголовок содержит 4 разные темы, но все вопросы получат тему первого вопроса"
        }
    ]
    
    topic_manager = TopicManager()
    
    for mixed in mixed_topics:
        print(f"\n📄 Проблемный заголовок: {mixed['header']}")
        print(f"⚠️  Проблема: {mixed['problem']}")
        
        # Извлекаем название
        topic_match = re.match(r'Тема:\s*([^(]+)\((\d+)\)', mixed['header'])
        if topic_match:
            original_name = topic_match.group(1).strip()
            count = int(topic_match.group(2))
            print(f"📊 Извлечено: '{original_name}' ({count} вопросов)")
        
        print(f"\n🔍 Анализ каждого типа вопроса:")
        
        for i, question in enumerate(mixed['questions'], 1):
            try:
                ai_topic = topic_manager._normalize_topic_with_ai(original_name, question)
                print(f"  {i}. '{question}' → '{ai_topic}'")
            except Exception as e:
                print(f"  {i}. Ошибка: {e}")
        
        print(f"\n💡 Текущая логика: ВСЕ {count} вопросов получат тему первого вопроса")
        first_question_topic = topic_manager._normalize_topic_with_ai(original_name, mixed['questions'][0])
        print(f"   Все вопросы будут: '{first_question_topic}'")

def main():
    """Основная функция."""
    print("🚀 ТЕСТИРОВАНИЕ РЕАЛЬНЫХ ТЕМ ИЗ PDF")
    print("Проверяем анализ реальных заголовков тем из PDF файлов")
    
    try:
        test_real_pdf_topics()
        test_problematic_mixed_topics()
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 