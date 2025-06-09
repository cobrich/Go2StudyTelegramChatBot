#!/usr/bin/env python3
"""
Скрипт для проверки состояния базы данных
"""

import sys
import os

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from services.database import Database

def check_database():
    """Проверяет состояние базы данных."""
    
    print("📊 СОСТОЯНИЕ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    try:
        db = Database()
        
        # Получаем все темы
        topics = db.get_all_topics()
        print(f"Всего тем в системе: {len(topics)}")
        
        # Проверяем вопросы по темам
        total_questions = 0
        topics_with_questions = []
        
        for topic in topics:
            # Используем get_tasks_for_topic с большим лимитом для подсчета всех вопросов
            questions = db.get_tasks_for_topic(topic['name'], limit=1000)
            count = len(questions)
            total_questions += count
            
            if count > 0:
                topics_with_questions.append((topic['name'], count))
        
        print(f"\nТем с вопросами: {len(topics_with_questions)}")
        print(f"Всего вопросов: {total_questions}")
        
        if topics_with_questions:
            print(f"\n📋 РАСПРЕДЕЛЕНИЕ ПО ТЕМАМ:")
            print("-" * 50)
            
            # Сортируем по количеству вопросов
            topics_with_questions.sort(key=lambda x: x[1], reverse=True)
            
            for topic_name, count in topics_with_questions:
                percentage = (count / total_questions) * 100 if total_questions > 0 else 0
                print(f"  {topic_name}: {count} вопросов ({percentage:.1f}%)")
        
        print(f"\n✅ База данных содержит {total_questions} вопросов")
        
        # Дополнительная статистика по источникам
        print(f"\n📈 СТАТИСТИКА ПО ИСТОЧНИКАМ:")
        print("-" * 50)
        
        # Получаем все вопросы для анализа источников
        all_questions = db.get_all_questions()
        source_stats = {}
        
        for question in all_questions:
            # Получаем источник через get_tasks_for_topic (там есть source)
            topic_questions = db.get_tasks_for_topic(question['topic'], limit=1000)
            for tq in topic_questions:
                if tq['question'] == question['question']:
                    source = tq.get('source', 'unknown')
                    source_stats[source] = source_stats.get(source, 0) + 1
                    break
        
        for source, count in source_stats.items():
            percentage = (count / total_questions) * 100 if total_questions > 0 else 0
            print(f"  {source}: {count} вопросов ({percentage:.1f}%)")
        
    except Exception as e:
        print(f"❌ Ошибка проверки базы: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database() 