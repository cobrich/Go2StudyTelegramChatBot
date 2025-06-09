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
        # Проблемные случаи из реального тестирования
        (
            "Арифметика - Дроби, проценты, уравнения",
            "Найдите 25% от числа 80",
            ["Нахождение процента от числа", "Проценты"]
        ),
        (
            "Числовые выражения", 
            "Вычислите: 31.4 ÷ 7.9",
            ["Натуральные числа", "Арифметические операции"]
        ),
        (
            "Арифметика-выражения с переменными",
            "Найдите значение выражения: 2x - y при x = 3, y = 10",
            ["Арифметические выражения"]
        ),
        (
            "Геометрия",
            "Найдите периметр прямоугольника с длиной 4 см и шириной 19 см",
            ["Периметр и площадь", "Геометрические фигуры"]
        ),
        (
            "Порядок выполнения операций",
            "Вычислите: (2 + 3) × 6",
            ["Порядок действий"]
        ),
        (
            "Линейные уравнения (усложнённый уровень)",
            "Решите уравнение: 5x + 5 = 45",
            ["Простейшие уравнения"]
        ),
        
        # Классические тестовые случаи
        (
            "Найти значение 2x",
            "Найдите значение выражения 2x + 3, если x = 5",
            ["Арифметические выражения", "Простейшие уравнения"]
        ),
        (
            "Операции с дробями и остатками",
            "Вычислите: 3/4 + 1/2 - 1/8",
            ["Действия с дробями", "Обыкновенные дроби"]
        ),
        (
            "Процентные вычисления",
            "Найдите 25% от числа 80",
            ["Нахождение процента от числа", "Проценты"]
        ),
        (
            "Геометрические задачи",
            "Найдите площадь прямоугольника со сторонами 5 см и 8 см",
            ["Периметр и площадь", "Геометрические фигуры"]
        ),
        (
            "Арифметические примеры",
            "Вычислите: 125 + 347 - 89",
            ["Арифметические операции", "Натуральные числа"]
        ),
        
        # Новые сложные случаи
        (
            "Проценты",
            "Найдите 12.5% от числа 232",
            ["Нахождение процента от числа", "Проценты"]
        ),
        (
            "Движение",
            "Скорости: 6,7 км/ч и 4,6 км/ч. Встретились через 2 часа",
            ["Движение"]
        ),
        (
            "Масштаб",
            "Расстояние на карте между городами 13.5 см, масштаб 1:2000000",
            ["Масштаб и расстояние"]
        ),
        (
            "Пропорция",
            "В саду растут яблоневые и грушевые деревья в отношении 3:2",
            ["Пропорция и разность"]
        )
    ]
    
    print("🧪 ТЕСТИРОВАНИЕ УЛУЧШЕННОГО AI-ПРОМПТА ДЛЯ ОБРАБОТКИ ТЕМ")
    print("=" * 80)
    
    success_count = 0
    total_count = len(test_cases)
    results = []
    
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
            is_success = False
            if result in expected:
                print("✅ УСПЕХ: Точное совпадение")
                is_success = True
            elif any(expected_topic.lower() in result.lower() or result.lower() in expected_topic.lower() for expected_topic in expected):
                print("✅ УСПЕХ: Частичное совпадение")
                is_success = True
            else:
                print("❌ НЕУДАЧА: Результат не соответствует ожиданиям")
                print(f"   Получено: '{result}'")
                print(f"   Ожидалось одно из: {expected}")
            
            if is_success:
                success_count += 1
            
            results.append({
                'pdf_topic': pdf_topic,
                'sample_question': sample_question[:50] + "...",
                'expected': expected,
                'result': result,
                'success': is_success
            })
                
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            results.append({
                'pdf_topic': pdf_topic,
                'sample_question': sample_question[:50] + "...",
                'expected': expected,
                'result': f"ОШИБКА: {e}",
                'success': False
            })
        
        print("-" * 60)
    
    # Подробная статистика
    print(f"\n📊 ДЕТАЛЬНЫЕ ИТОГИ ТЕСТИРОВАНИЯ:")
    print("=" * 80)
    
    print(f"Успешных тестов: {success_count}/{total_count}")
    print(f"Процент успеха: {(success_count/total_count)*100:.1f}%")
    
    # Анализ по категориям
    categories = {
        'Проценты': ['Проценты', 'Нахождение процента от числа'],
        'Арифметика': ['Арифметические операции', 'Натуральные числа', 'Арифметические выражения'],
        'Геометрия': ['Геометрические фигуры', 'Периметр и площадь'],
        'Уравнения': ['Простейшие уравнения', 'Составление уравнений'],
        'Специальные': ['Движение', 'Масштаб и расстояние', 'Пропорция и разность']
    }
    
    print(f"\n📈 АНАЛИЗ ПО КАТЕГОРИЯМ:")
    for category, topics in categories.items():
        category_results = [r for r in results if r['result'] in topics]
        if category_results:
            category_success = sum(1 for r in category_results if r['success'])
            category_total = len(category_results)
            print(f"  {category}: {category_success}/{category_total} ({(category_success/category_total)*100:.1f}%)")
    
    print(f"\n🔍 НЕУДАЧНЫЕ СЛУЧАИ:")
    failed_cases = [r for r in results if not r['success']]
    if failed_cases:
        for case in failed_cases:
            print(f"  ❌ '{case['pdf_topic']}' → '{case['result']}' (ожидалось: {case['expected']})")
    else:
        print("  🎉 Все тесты прошли успешно!")
    
    if success_count == total_count:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    elif success_count >= total_count * 0.85:
        print("\n✅ ОТЛИЧНЫЕ РЕЗУЛЬТАТЫ! AI-промпт значительно улучшен!")
    elif success_count >= total_count * 0.75:
        print("\n✅ ХОРОШИЕ РЕЗУЛЬТАТЫ! Есть улучшения!")
    else:
        print("\n⚠️ ТРЕБУЕТСЯ ДОПОЛНИТЕЛЬНАЯ ДОРАБОТКА ПРОМПТА")
    
    return results

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
        ("Неизвестная тема XYZ", "Несуществующая тема"),
    ]
    
    for topic, description in edge_cases:
        print(f"\nТест: {description}")
        print(f"Входная тема: '{topic}'")
        
        try:
            result = topic_manager.ensure_topic_exists(topic)
            print(f"Результат: '{result}'")
        except Exception as e:
            print(f"Ошибка: {e}")

def compare_with_previous_results():
    """Сравниваем с предыдущими результатами тестирования."""
    
    print("\n📊 СРАВНЕНИЕ С ПРЕДЫДУЩИМИ РЕЗУЛЬТАТАМИ")
    print("=" * 50)
    
    # Результаты из предыдущего тестирования (75% успеха)
    previous_success_rate = 75.0
    
    # Запускаем новое тестирование
    results = test_topic_normalization()
    current_success_rate = (sum(1 for r in results if r['success']) / len(results)) * 100
    
    improvement = current_success_rate - previous_success_rate
    
    print(f"\n📈 СРАВНЕНИЕ РЕЗУЛЬТАТОВ:")
    print(f"Предыдущий результат: {previous_success_rate:.1f}%")
    print(f"Текущий результат: {current_success_rate:.1f}%")
    print(f"Улучшение: {improvement:+.1f}%")
    
    if improvement > 5:
        print("🚀 ЗНАЧИТЕЛЬНОЕ УЛУЧШЕНИЕ!")
    elif improvement > 0:
        print("📈 ЕСТЬ УЛУЧШЕНИЯ!")
    elif improvement == 0:
        print("➡️ БЕЗ ИЗМЕНЕНИЙ")
    else:
        print("📉 УХУДШЕНИЕ - ТРЕБУЕТСЯ ДОРАБОТКА")

if __name__ == "__main__":
    print("🚀 ЗАПУСК ТЕСТИРОВАНИЯ УЛУЧШЕННОГО AI-ПРОМПТА")
    
    # Основные тесты
    results = test_topic_normalization()
    
    # Граничные случаи
    test_edge_cases()
    
    # Сравнение с предыдущими результатами
    # compare_with_previous_results()  # Закомментировано чтобы избежать двойного запуска
    
    print("\n✨ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!") 