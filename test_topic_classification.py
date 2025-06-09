#!/usr/bin/env python3
"""
Тест для проверки правильности классификации вопросов по темам.
Проверяет, что вопросы из базы данных соответствуют своим темам.
"""

import sys
import os
import sqlite3
import re
from typing import List, Dict, Tuple

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from services.database import Database
from services.ai_service import AIService

class TopicClassificationTester:
    def __init__(self):
        self.db = Database()
        self.ai_service = AIService()
        
        # Правила для определения соответствия вопроса теме
        self.topic_rules = {
            'Проценты': [
                r'процент',
                r'%',
                r'найдите.*?процент.*?от',
                r'найдите.*?от.*?числа',
                r'составляет.*?процент'
            ],
            'Нахождение процента от числа': [
                r'найдите.*?\d+%.*?от.*?числа',
                r'найдите.*?\d+.*?процент.*?от.*?\d+',
                r'\d+%.*?от.*?\d+'
            ],
            'Простейшие уравнения': [
                r'[xyz]\s*[=]',
                r'решите.*?уравнение',
                r'найдите.*?[xyz]',
                r'\d*[xyz]\s*[+\-]\s*\d+\s*=',
                r'уравнение'
            ],
            'Арифметические операции': [
                r'^\d+[\+\-\×\÷\*\/]\d+',
                r'вычислите.*?\d+[\+\-\×\÷\*\/]\d+',
                r'найдите.*?значение.*?\d+[\+\-\×\÷\*\/]\d+'
            ],
            'Натуральные числа': [
                r'^\d+[,\.]\d+\s*[\+\-\×\÷\*\/]',
                r'десятичн',
                r'запятая'
            ],
            'Действия с дробями': [
                r'\d+\/\d+',
                r'дроб',
                r'числител',
                r'знаменател'
            ],
            'Геометрические фигуры': [
                r'треугольник',
                r'квадрат',
                r'прямоугольник',
                r'круг',
                r'фигур'
            ],
            'Периметр и площадь': [
                r'периметр',
                r'площад',
                r'найдите.*?площад',
                r'найдите.*?периметр'
            ]
        }

    def check_question_topic_match(self, question: str, topic: str) -> Tuple[bool, str]:
        """
        Проверяет, соответствует ли вопрос заданной теме.
        Возвращает (соответствует, объяснение)
        """
        question_lower = question.lower()
        
        # Проверяем по правилам
        if topic in self.topic_rules:
            rules = self.topic_rules[topic]
            for rule in rules:
                if re.search(rule, question_lower):
                    return True, f"Соответствует правилу: {rule}"
        
        # Если не соответствует правилам, проверяем с помощью AI
        try:
            prompt = f"""
Проанализируй, соответствует ли данный вопрос указанной теме.

ВОПРОС: "{question}"
ТЕМА: "{topic}"

Ответь в формате:
СООТВЕТСТВУЕТ: да/нет
ОБЪЯСНЕНИЕ: краткое объяснение почему

Критерии соответствия:
- Проценты: вопросы с %, "процент от числа", процентные вычисления
- Уравнения: вопросы с переменными x, y, z и знаком равенства
- Арифметические операции: простые вычисления +, -, ×, ÷
- Натуральные числа: работа с целыми и десятичными числами
- Дроби: вопросы с дробями (1/2, 3/4 и т.д.)
- Геометрия: фигуры, периметр, площадь
"""
            
            response = self.ai_service.model.generate_content(prompt)
            response_text = response.text.lower()
            
            if 'соответствует: да' in response_text:
                explanation = response_text.split('объяснение:')[-1].strip() if 'объяснение:' in response_text else "AI подтвердил соответствие"
                return True, f"AI: {explanation}"
            else:
                explanation = response_text.split('объяснение:')[-1].strip() if 'объяснение:' in response_text else "AI не подтвердил соответствие"
                return False, f"AI: {explanation}"
                
        except Exception as e:
            return False, f"Ошибка AI проверки: {e}"

    def suggest_correct_topic(self, question: str) -> str:
        """Предлагает правильную тему для вопроса."""
        question_lower = question.lower()
        
        # Проверяем по правилам
        for topic, rules in self.topic_rules.items():
            for rule in rules:
                if re.search(rule, question_lower):
                    return topic
        
        # Если не найдено по правилам, используем AI
        try:
            all_topics = self.db.get_all_topics(active_only=True)
            topic_names = [t['name'] for t in all_topics]
            
            prompt = f"""
Определи наиболее подходящую тему для данного вопроса.

ВОПРОС: "{question}"

ДОСТУПНЫЕ ТЕМЫ:
{chr(10).join([f"{i+1}. {name}" for i, name in enumerate(topic_names)])}

ПРАВИЛА КЛАССИФИКАЦИИ:
- Если есть проценты (%, "процент от") → "Проценты" или "Нахождение процента от числа"
- Если есть переменные и уравнения → "Простейшие уравнения"
- Если простые арифметические вычисления → "Арифметические операции"
- Если десятичные числа → "Натуральные числа"
- Если дроби → "Действия с дробями"
- Если геометрические фигуры → "Геометрические фигуры"

Ответь ТОЛЬКО названием темы из списка выше.
"""
            
            response = self.ai_service.model.generate_content(prompt)
            suggested = response.text.strip()
            
            # Проверяем, что предложенная тема есть в списке
            for topic in topic_names:
                if suggested.lower() == topic.lower() or topic.lower() in suggested.lower():
                    return topic
            
            return "Математика"  # По умолчанию
            
        except Exception as e:
            print(f"Ошибка при определении темы: {e}")
            return "Математика"

    def test_all_questions(self) -> Dict[str, List[Dict]]:
        """Тестирует все вопросы в базе данных."""
        print("🔍 Начинаю проверку классификации вопросов...")
        
        # Получаем все вопросы
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, topic, question, source 
                FROM questions 
                ORDER BY topic, id
            ''')
            questions = cursor.fetchall()
        
        results = {
            'correct': [],
            'incorrect': [],
            'statistics': {}
        }
        
        total_questions = len(questions)
        correct_count = 0
        
        print(f"📊 Всего вопросов для проверки: {total_questions}")
        
        for i, (q_id, topic, question, source) in enumerate(questions):
            if i % 50 == 0:
                print(f"⏳ Обработано {i}/{total_questions} вопросов...")
            
            # Проверяем соответствие
            is_correct, explanation = self.check_question_topic_match(question, topic)
            
            question_data = {
                'id': q_id,
                'topic': topic,
                'question': question[:100] + '...' if len(question) > 100 else question,
                'source': source,
                'explanation': explanation
            }
            
            if is_correct:
                results['correct'].append(question_data)
                correct_count += 1
            else:
                # Предлагаем правильную тему
                suggested_topic = self.suggest_correct_topic(question)
                question_data['suggested_topic'] = suggested_topic
                results['incorrect'].append(question_data)
        
        # Статистика по темам
        topic_stats = {}
        for q_id, topic, question, source in questions:
            if topic not in topic_stats:
                topic_stats[topic] = {'total': 0, 'correct': 0, 'incorrect': 0}
            topic_stats[topic]['total'] += 1
        
        for item in results['correct']:
            topic_stats[item['topic']]['correct'] += 1
        
        for item in results['incorrect']:
            topic_stats[item['topic']]['incorrect'] += 1
        
        results['statistics'] = topic_stats
        
        print(f"\n✅ Проверка завершена!")
        print(f"📈 Правильно классифицированных: {correct_count}/{total_questions} ({correct_count/total_questions*100:.1f}%)")
        print(f"❌ Неправильно классифицированных: {len(results['incorrect'])}")
        
        return results

    def print_detailed_report(self, results: Dict):
        """Выводит подробный отчет о результатах тестирования."""
        print("\n" + "="*80)
        print("📋 ПОДРОБНЫЙ ОТЧЕТ ПО КЛАССИФИКАЦИИ ВОПРОСОВ")
        print("="*80)
        
        # Статистика по темам
        print("\n📊 СТАТИСТИКА ПО ТЕМАМ:")
        print("-" * 60)
        for topic, stats in results['statistics'].items():
            accuracy = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"{topic:30} | Всего: {stats['total']:3} | Правильно: {stats['correct']:3} | Точность: {accuracy:5.1f}%")
        
        # Неправильно классифицированные вопросы
        if results['incorrect']:
            print(f"\n❌ НЕПРАВИЛЬНО КЛАССИФИЦИРОВАННЫЕ ВОПРОСЫ ({len(results['incorrect'])}):")
            print("-" * 80)
            
            # Группируем по темам
            by_topic = {}
            for item in results['incorrect']:
                topic = item['topic']
                if topic not in by_topic:
                    by_topic[topic] = []
                by_topic[topic].append(item)
            
            for topic, items in by_topic.items():
                print(f"\n🏷️  ТЕМА: {topic} ({len(items)} неправильных)")
                for i, item in enumerate(items[:5]):  # Показываем только первые 5
                    print(f"   {i+1}. {item['question']}")
                    print(f"      💡 Предлагаемая тема: {item['suggested_topic']}")
                    print(f"      📝 Объяснение: {item['explanation']}")
                    print()
                
                if len(items) > 5:
                    print(f"   ... и еще {len(items) - 5} вопросов")
                print()

    def fix_incorrect_classifications(self, results: Dict, dry_run: bool = True):
        """Исправляет неправильные классификации в базе данных."""
        if not results['incorrect']:
            print("✅ Все вопросы классифицированы правильно!")
            return
        
        print(f"\n🔧 {'СИМУЛЯЦИЯ' if dry_run else 'ИСПРАВЛЕНИЕ'} НЕПРАВИЛЬНЫХ КЛАССИФИКАЦИЙ")
        print("-" * 60)
        
        updates = {}
        for item in results['incorrect']:
            old_topic = item['topic']
            new_topic = item['suggested_topic']
            
            if old_topic != new_topic:
                if new_topic not in updates:
                    updates[new_topic] = []
                updates[new_topic].append(item)
        
        for new_topic, items in updates.items():
            print(f"\n➡️  Перемещение в тему '{new_topic}': {len(items)} вопросов")
            for item in items[:3]:  # Показываем первые 3
                print(f"   • {item['question'][:60]}...")
            if len(items) > 3:
                print(f"   • ... и еще {len(items) - 3} вопросов")
        
        if not dry_run:
            # Выполняем обновления
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                updated_count = 0
                
                for item in results['incorrect']:
                    if item['topic'] != item['suggested_topic']:
                        cursor.execute(
                            'UPDATE questions SET topic = ? WHERE id = ?',
                            (item['suggested_topic'], item['id'])
                        )
                        updated_count += 1
                
                conn.commit()
                print(f"\n✅ Обновлено {updated_count} записей в базе данных")
        else:
            print(f"\n💡 Для применения изменений запустите с параметром --fix")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Тест классификации вопросов по темам')
    parser.add_argument('--fix', action='store_true', help='Исправить неправильные классификации')
    parser.add_argument('--topic', type=str, help='Проверить только указанную тему')
    args = parser.parse_args()
    
    tester = TopicClassificationTester()
    
    if args.topic:
        # Проверяем только указанную тему
        print(f"🔍 Проверка темы: {args.topic}")
        # TODO: Реализовать проверку конкретной темы
    else:
        # Проверяем все вопросы
        results = tester.test_all_questions()
        tester.print_detailed_report(results)
        tester.fix_incorrect_classifications(results, dry_run=not args.fix)

if __name__ == '__main__':
    main() 