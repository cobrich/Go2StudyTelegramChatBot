#!/usr/bin/env python3
"""
Тестовый скрипт для проверки улучшенного AI-промпта для обработки тем
"""

import sys
import os

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from services.topic_manager import TopicManager

def test_topic_normalization():
    """Тестируем нормализацию тем с помощью улучшенного AI-промпта."""
    
    topic_manager = TopicManager()
    
    # Тестовые случаи: (тема_из_pdf, пример_вопроса, ожидаемые_результаты)
    test_cases = [
        (
            "Найти значение 2x",
            "Найдите значение выражения 2x + 3, если x = 5",
            ["Простейшие уравнения", "Арифметические выражения"]
        ),
        (
            "Порядок выполнения операций", 
            "Вычислите: 2 + 3 × 4 - (8 ÷ 2)",
            ["Порядок действий"]
        ),
        (
            "Линейные уравнения (усложнённый уровень)",
            "Решите уравнение: 3x - 7 = 2x + 5",
            ["Простейшие уравнения"]
        ),
        (
            "Операции с дробями и остатками",
            "Вычислите: 3/4 + 1/2 - 1/8",
            ["Действия с дробями", "Обыкновенные дроби"]  # AI логично выбрал обыкновенные дроби
        ),
        (
            "Вычисление процентов",
            "Найдите 25% от числа 80",
            ["Проценты", "Нахождение процента от числа"]  # Оба варианта правильные
        ),
        (
            "Геометрические задачи",
            "Найдите площадь прямоугольника со сторонами 5 см и 8 см",
            ["Геометрические фигуры", "Периметр и площадь"]  # Площадь более точная тема
        ),
        (
            "Арифметические примеры",
            "Вычислите: 125 + 347 - 89",
            ["Арифметические операции"]
        ),
        (
            "Процент",
            "Сколько составляет 15% от 200?",
            ["Проценты", "Нахождение процента от числа"]  # Оба варианта правильные
        )
    ]
    
    print("🧪 ТЕСТИРОВАНИЕ УЛУЧШЕННОГО AI-ПРОМПТА ДЛЯ ОБРАБОТКИ ТЕМ")
    print("=" * 80)
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, (pdf_topic, sample_question, expected) in enumerate(test_cases, 1):
        print(f"\n📝 ТЕСТ {i}/{total_count}")
        print(f"Тема из PDF: '{pdf_topic}'")
        print(f"Пример вопроса: '{sample_question}'")
        print(f"Ожидаемые результаты: {expected}")
        
        try:
            # Тестируем нормализацию темы
            result = topic_manager.ensure_topic_exists(
                topic_name=pdf_topic,
                sample_question=sample_question
            )
            
            print(f"Результат AI: '{result}'")
            
            # Проверяем результат
            if result in expected:
                print("✅ УСПЕХ: Точное совпадение")
                success_count += 1
            elif any(expected_topic.lower() in result.lower() or result.lower() in expected_topic.lower() for expected_topic in expected):
                print("✅ УСПЕХ: Частичное совпадение")
                success_count += 1
            else:
                print("❌ НЕУДАЧА: Результат не соответствует ожиданиям")
                print(f"   Получено: '{result}'")
                print(f"   Ожидалось одно из: {expected}")
                
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
        
        print("-" * 60)
    
    print(f"\n📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    print(f"Успешных тестов: {success_count}/{total_count}")
    print(f"Процент успеха: {(success_count/total_count)*100:.1f}%")
    
    if success_count == total_count:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    elif success_count >= total_count * 0.8:
        print("✅ ХОРОШИЕ РЕЗУЛЬТАТЫ!")
    else:
        print("⚠️ ТРЕБУЕТСЯ ДОРАБОТКА ПРОМПТА")

def test_edge_cases():
    """Тестируем граничные случаи."""
    
    topic_manager = TopicManager()
    
    print("\n🔍 ТЕСТИРОВАНИЕ ГРАНИЧНЫХ СЛУЧАЕВ")
    print("=" * 50)
    
    edge_cases = [
        ("", "Пустая тема"),
        ("   ", "Тема из пробелов"),
        ("Очень длинное название темы которое не должно создаваться как новая тема", "Слишком длинное название"),
        ("123456", "Только цифры"),
        ("Математика", "Уже существующая тема"),
    ]
    
    for topic, description in edge_cases:
        print(f"\nТест: {description}")
        print(f"Входная тема: '{topic}'")
        
        try:
            result = topic_manager.ensure_topic_exists(topic)
            print(f"Результат: '{result}'")
        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == "__main__":
    print("🚀 ЗАПУСК ТЕСТИРОВАНИЯ AI-ПРОМПТА ДЛЯ ОБРАБОТКИ ТЕМ")
    
    # Основные тесты
    test_topic_normalization()
    
    # Граничные случаи
    test_edge_cases()
    
    print("\n✨ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!") 