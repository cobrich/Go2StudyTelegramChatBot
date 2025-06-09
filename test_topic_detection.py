#!/usr/bin/env python3
"""
Тест для проверки правильности определения тем ИИ.
Тестирует логику TopicManager._normalize_topic_with_ai
"""

import sys
import os
import re

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from services.topic_manager import TopicManager
from services.database import Database

class TopicDetectionTester:
    def __init__(self):
        self.topic_manager = TopicManager()
        self.db = Database()
        
        # Тестовые случаи: (название_темы_из_pdf, первый_вопрос, ожидаемая_тема)
        self.test_cases = [
            (
                "Пропорция",
                "Найдите значение x в пропорции 2:3 = x:12",
                "Простейшие уравнения"
            ),
            (
                "Процентные вычисления", 
                "Найдите 25% от числа 80",
                "Нахождение процента от числа"
            ),
            (
                "Линейные уравнения",
                "Решите уравнение 3x - 7 = 2x + 5",
                "Простейшие уравнения"
            ),
            (
                "Арифметика",
                "Вычислите: 2 + 3 × 4",
                "Порядок действий"
            ),
            (
                "Дроби",
                "Вычислите: 3/4 + 1/2",
                "Действия с дробями"
            ),
            (
                "Геометрические задачи",
                "Найдите площадь прямоугольника со сторонами 5 см и 8 см",
                "Периметр и площадь"
            ),
            (
                "Десятичные числа",
                "Вычислите: 31.4 ÷ 7.9",
                "Натуральные числа"
            ),
            (
                "Проценты",
                "В магазине скидка 20%. Сколько стоит товар после скидки?",
                "Проценты"
            ),
            (
                "Числовые выражения",
                "Найдите значение выражения 2x + 3, если x = 5",
                "Арифметические выражения"
            ),
            (
                "Четные числа",
                "Какие из чисел 12, 15, 18, 21 являются четными?",
                "Чётные и нечётные числа"
            )
        ]

    def parse_test_file(self, file_path: str) -> tuple:
        """Парсит тестовый файл и извлекает название темы и первый вопрос."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ищем заголовок темы
            topic_match = re.search(r'Тема:\s*([^(]+)\((\d+)\)', content)
            if not topic_match:
                return None, None
            
            topic_name = topic_match.group(1).strip()
            
            # Ищем первый вопрос
            question_match = re.search(r'1\.\s*(.+?)(?=\nA\))', content, re.DOTALL)
            if not question_match:
                return topic_name, None
            
            first_question = question_match.group(1).strip()
            
            return topic_name, first_question
            
        except Exception as e:
            print(f"Ошибка при парсинге файла {file_path}: {e}")
            return None, None

    def test_ai_topic_detection(self):
        """Тестирует определение тем ИИ на заранее подготовленных случаях."""
        print("🧪 ТЕСТ ОПРЕДЕЛЕНИЯ ТЕМ ИИ")
        print("=" * 60)
        
        correct_predictions = 0
        total_tests = len(self.test_cases)
        
        for i, (pdf_topic, sample_question, expected_topic) in enumerate(self.test_cases, 1):
            print(f"\n📝 Тест {i}/{total_tests}")
            print(f"Тема из PDF: '{pdf_topic}'")
            print(f"Первый вопрос: '{sample_question}'")
            print(f"Ожидаемая тема: '{expected_topic}'")
            
            # Тестируем AI
            predicted_topic = self.topic_manager._normalize_topic_with_ai(pdf_topic, sample_question)
            print(f"Предсказанная тема: '{predicted_topic}'")
            
            if predicted_topic == expected_topic:
                print("✅ ПРАВИЛЬНО")
                correct_predictions += 1
            else:
                print("❌ НЕПРАВИЛЬНО")
            
            print("-" * 40)
        
        accuracy = correct_predictions / total_tests * 100
        print(f"\n📊 РЕЗУЛЬТАТЫ:")
        print(f"Правильных предсказаний: {correct_predictions}/{total_tests}")
        print(f"Точность: {accuracy:.1f}%")
        
        return accuracy >= 80  # Считаем тест пройденным, если точность >= 80%

    def test_file_parsing(self, file_path: str):
        """Тестирует парсинг конкретного файла и определение темы."""
        print(f"\n🔍 ТЕСТ ФАЙЛА: {file_path}")
        print("=" * 60)
        
        if not os.path.exists(file_path):
            print(f"❌ Файл не найден: {file_path}")
            return False
        
        # Парсим файл
        topic_name, first_question = self.parse_test_file(file_path)
        
        if not topic_name:
            print("❌ Не удалось извлечь название темы")
            return False
        
        if not first_question:
            print("❌ Не удалось извлечь первый вопрос")
            return False
        
        print(f"📋 Извлеченная тема: '{topic_name}'")
        print(f"📝 Первый вопрос: '{first_question}'")
        
        # Определяем тему с помощью AI
        predicted_topic = self.topic_manager._normalize_topic_with_ai(topic_name, first_question)
        print(f"🤖 Предсказанная тема: '{predicted_topic}'")
        
        # Проверяем, что тема существует в системе
        existing_topics = self.db.get_all_topics(active_only=True)
        topic_names = [t['name'] for t in existing_topics]
        
        if predicted_topic in topic_names:
            print("✅ Тема найдена в системе")
            return True
        else:
            print("❌ Тема не найдена в системе")
            print(f"Доступные темы: {', '.join(topic_names[:5])}...")
            return False

    def run_all_tests(self):
        """Запускает все тесты."""
        print("🚀 ЗАПУСК ВСЕХ ТЕСТОВ ОПРЕДЕЛЕНИЯ ТЕМ")
        print("=" * 80)
        
        # Тест 1: AI на заранее подготовленных случаях
        ai_test_passed = self.test_ai_topic_detection()
        
        # Тест 2: Файлы
        file1_passed = self.test_file_parsing("test_files/file1.txt")
        file2_passed = self.test_file_parsing("test_files/file2.txt")
        
        # Общий результат
        print(f"\n🏁 ОБЩИЕ РЕЗУЛЬТАТЫ:")
        print("=" * 40)
        print(f"AI тест: {'✅ ПРОЙДЕН' if ai_test_passed else '❌ НЕ ПРОЙДЕН'}")
        print(f"Файл 1: {'✅ ПРОЙДЕН' if file1_passed else '❌ НЕ ПРОЙДЕН'}")
        print(f"Файл 2: {'✅ ПРОЙДЕН' if file2_passed else '❌ НЕ ПРОЙДЕН'}")
        
        all_passed = ai_test_passed and file1_passed and file2_passed
        print(f"\nИТОГ: {'🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ' if all_passed else '⚠️  ЕСТЬ ПРОБЛЕМЫ'}")
        
        return all_passed

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Тест определения тем ИИ')
    parser.add_argument('--file', type=str, help='Тестировать конкретный файл')
    parser.add_argument('--ai-only', action='store_true', help='Только AI тест')
    args = parser.parse_args()
    
    tester = TopicDetectionTester()
    
    if args.file:
        # Тестируем конкретный файл
        tester.test_file_parsing(args.file)
    elif args.ai_only:
        # Только AI тест
        tester.test_ai_topic_detection()
    else:
        # Все тесты
        tester.run_all_tests()

if __name__ == '__main__':
    main() 