#!/usr/bin/env python3
"""
Тестовый скрипт для проверки генерации AI объяснений
"""

import sys
import os

# Добавляем путь к корню проекта
sys.path.append('.')
sys.path.append('./src')

from src.services.ai_service import AIService

def test_ai_explanations():
    """Тестирует генерацию AI объяснений для разных типов задач."""
    
    print("🧪 Тестирование генерации AI объяснений")
    print("=" * 60)
    
    ai_service = AIService()
    
    # Тестовые вопросы разных типов
    test_questions = [
        {
            "question": "Повар использовал 2/7 всего теста утром и 3/5 оставшегося вечером. Осталось 24 кг теста. Сколько всего было изначально?",
            "answer": "35",
            "topic": "Действия с дробями"
        },
        {
            "question": "Вычислите: 2,46 × 18",
            "answer": "44,28",
            "topic": "Десятичные дроби"
        },
        {
            "question": "Найдите 25% от 80",
            "answer": "20",
            "topic": "Проценты"
        },
        {
            "question": "Решите уравнение: 2x + 5 = 13",
            "answer": "4",
            "topic": "Простейшие уравнения"
        }
    ]
    
    for i, test_case in enumerate(test_questions, 1):
        print(f"\n🔍 Тест {i}: {test_case['topic']}")
        print("-" * 40)
        print(f"Вопрос: {test_case['question']}")
        print(f"Ответ: {test_case['answer']}")
        
        try:
            explanation = ai_service.generate_detailed_explanation(
                test_case['question'],
                test_case['answer'],
                test_case['topic']
            )
            
            print(f"✅ Объяснение сгенерировано:")
            print(f"📝 {explanation}")
            
        except Exception as e:
            print(f"❌ Ошибка генерации: {e}")
    
    print(f"\n{'=' * 60}")
    print("🎉 Тестирование завершено!")

if __name__ == "__main__":
    test_ai_explanations() 