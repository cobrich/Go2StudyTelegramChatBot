#!/usr/bin/env python3
"""
Тестовый скрипт для обработки file1.pdf и file2.pdf из папки files/
Анализирует какие темы будут добавлены в базу данных
"""

import sys
import os
from collections import defaultdict

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from services.pdf_processor import PDFProcessor
from services.database import Database

def test_pdf_files():
    """Тестируем обработку PDF файлов и анализируем темы."""
    
    print("🧪 ТЕСТИРОВАНИЕ ОБРАБОТКИ PDF ФАЙЛОВ")
    print("=" * 80)
    
    # Список файлов для тестирования
    pdf_files = [
        "files/file1.pdf",
        "files/file2.pdf"
    ]
    
    processor = PDFProcessor()
    db = Database()
    
    # Статистика по темам
    all_topics = defaultdict(int)
    file_topics = {}
    
    for pdf_file in pdf_files:
        print(f"\n📄 ОБРАБОТКА ФАЙЛА: {pdf_file}")
        print("-" * 60)
        
        if not os.path.exists(pdf_file):
            print(f"❌ Файл не найден: {pdf_file}")
            continue
        
        try:
            # Извлекаем вопросы из PDF
            questions = processor.extract_questions_from_pdf(pdf_file)
            
            print(f"✅ Извлечено {len(questions)} вопросов")
            
            # Анализируем темы
            file_topic_stats = defaultdict(int)
            
            for question in questions:
                topic = question.get('topic', 'Неопределенная тема')
                file_topic_stats[topic] += 1
                all_topics[topic] += 1
            
            file_topics[pdf_file] = dict(file_topic_stats)
            
            print(f"\n📊 ТЕМЫ В ФАЙЛЕ {os.path.basename(pdf_file)}:")
            for topic, count in sorted(file_topic_stats.items()):
                print(f"  • {topic}: {count} вопросов")
            
            # Показываем примеры вопросов по темам
            print(f"\n📝 ПРИМЕРЫ ВОПРОСОВ ПО ТЕМАМ:")
            shown_topics = set()
            for question in questions[:10]:  # Показываем первые 10 вопросов
                topic = question.get('topic', 'Неопределенная тема')
                if topic not in shown_topics:
                    print(f"\n🎯 Тема: {topic}")
                    print(f"   Вопрос: {question['question'][:100]}...")
                    print(f"   Правильный ответ: {question['correct_answer']}) {question['options'][ord(question['correct_answer']) - ord('A')]}")
                    shown_topics.add(topic)
                    
                    if len(shown_topics) >= 5:  # Показываем максимум 5 тем
                        break
            
        except Exception as e:
            print(f"❌ Ошибка при обработке {pdf_file}: {e}")
            import traceback
            traceback.print_exc()
    
    # Общая статистика
    print(f"\n📈 ОБЩАЯ СТАТИСТИКА ПО ВСЕМ ФАЙЛАМ:")
    print("=" * 60)
    
    total_questions = sum(all_topics.values())
    print(f"Всего вопросов: {total_questions}")
    print(f"Уникальных тем: {len(all_topics)}")
    
    print(f"\n🎯 РАСПРЕДЕЛЕНИЕ ПО ТЕМАМ:")
    for topic, count in sorted(all_topics.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_questions) * 100 if total_questions > 0 else 0
        print(f"  • {topic}: {count} вопросов ({percentage:.1f}%)")
    
    # Анализ соответствия темам НИШ
    print(f"\n🎓 АНАЛИЗ СООТВЕТСТВИЯ ТЕМАМ НИШ:")
    print("-" * 40)
    
    # Получаем список тем НИШ из TopicManager
    from services.topic_manager import TopicManager
    topic_manager = TopicManager()
    nis_topics = set(topic_manager.base_topics)
    
    found_topics = set(all_topics.keys())
    
    # Темы, которые точно соответствуют НИШ
    matching_topics = found_topics.intersection(nis_topics)
    print(f"✅ Точные совпадения с темами НИШ ({len(matching_topics)}):")
    for topic in sorted(matching_topics):
        print(f"  • {topic}")
    
    # Темы, которые не соответствуют НИШ
    non_matching_topics = found_topics - nis_topics
    if non_matching_topics:
        print(f"\n⚠️ Темы, не входящие в стандарт НИШ ({len(non_matching_topics)}):")
        for topic in sorted(non_matching_topics):
            print(f"  • {topic}")
    
    # Проверяем, какие темы НИШ не представлены
    missing_topics = nis_topics - found_topics
    if missing_topics:
        print(f"\n📋 Темы НИШ, не представленные в файлах ({len(missing_topics)}):")
        for topic in sorted(missing_topics):
            print(f"  • {topic}")
    
    return file_topics, all_topics

def analyze_topic_mapping():
    """Анализируем как работает система сопоставления тем."""
    
    print(f"\n🔍 АНАЛИЗ СИСТЕМЫ СОПОСТАВЛЕНИЯ ТЕМ")
    print("=" * 50)
    
    from services.topic_manager import TopicManager
    topic_manager = TopicManager()
    
    # Тестовые случаи - темы, которые могут встретиться в PDF
    test_cases = [
        ("Арифметические операции", "Вычислите: 25 + 37 - 18"),
        ("Порядок выполнения операций", "Вычислите: 2 + 3 × 4 - (8 ÷ 2)"),
        ("Линейные уравнения", "Решите уравнение: 3x - 7 = 2x + 5"),
        ("Операции с дробями", "Вычислите: 3/4 + 1/2 - 1/8"),
        ("Найти значение выражения", "Найдите значение 2x + 3, если x = 5"),
        ("Процентные вычисления", "Найдите 25% от числа 80"),
        ("Геометрические задачи", "Найдите площадь прямоугольника 5×8 см"),
        ("Пропорции", "Решите пропорцию: x : 6 = 4 : 3"),
        ("Масштаб", "На карте масштаба 1:1000 расстояние 5 см"),
        ("Движение", "Автомобиль едет со скоростью 60 км/ч")
    ]
    
    print("Тестируем сопоставление тем:")
    for original_topic, sample_question in test_cases:
        try:
            normalized_topic = topic_manager.ensure_topic_exists(
                topic_name=original_topic,
                sample_question=sample_question
            )
            
            status = "✅" if normalized_topic != original_topic else "➡️"
            print(f"{status} '{original_topic}' → '{normalized_topic}'")
            
        except Exception as e:
            print(f"❌ '{original_topic}' → Ошибка: {e}")

if __name__ == "__main__":
    print("🚀 ЗАПУСК ТЕСТИРОВАНИЯ PDF ФАЙЛОВ")
    
    # Основной тест обработки файлов
    file_topics, all_topics = test_pdf_files()
    
    # Анализ системы сопоставления тем
    analyze_topic_mapping()
    
    print(f"\n✨ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    print(f"📊 Результаты сохранены в переменных file_topics и all_topics") 