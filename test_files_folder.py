#!/usr/bin/env python3
"""
Тест для проверки PDF файлов в папке files/ перед добавлением в базу данных.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.pdf_processor import PDFProcessor
from services.database import Database

class FilesTestRunner:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.db = Database()
        
    def test_pdf_file(self, file_path: str):
        """Тестирует один PDF файл"""
        print(f"\n{'='*80}")
        print(f"🔍 ТЕСТИРОВАНИЕ ФАЙЛА: {file_path}")
        print(f"{'='*80}")
        
        if not os.path.exists(file_path):
            print(f"❌ Файл не найден: {file_path}")
            return False
            
        try:
            # Получаем размер файла
            file_size = os.path.getsize(file_path)
            print(f"📁 Размер файла: {file_size / 1024:.1f} KB")
            
            # Обрабатываем PDF файл
            print("⏳ Извлекаю вопросы из PDF...")
            questions = self.pdf_processor.process_pdf_file(file_path)
            
            if not questions:
                print("❌ Не удалось извлечь вопросы из файла")
                return False
                
            print(f"✅ Извлечено {len(questions)} вопросов")
            
            # Анализируем качество вопросов
            self.analyze_questions_quality(questions)
            
            # Проверяем темы
            self.analyze_topics(questions)
            
            # Проверяем дубликаты с базой данных
            self.check_duplicates(questions)
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при обработке файла: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def analyze_questions_quality(self, questions):
        """Анализирует качество извлеченных вопросов"""
        print(f"\n📊 АНАЛИЗ КАЧЕСТВА ВОПРОСОВ:")
        print(f"{'='*50}")
        
        valid_count = 0
        invalid_count = 0
        short_questions = 0
        missing_answers = 0
        insufficient_options = 0
        
        for i, q in enumerate(questions):
            is_valid = True
            issues = []
            
            # Проверяем длину вопроса
            if len(q['question'].strip()) < 10:
                short_questions += 1
                is_valid = False
                issues.append("слишком короткий")
            
            # Проверяем наличие правильного ответа
            if not q.get('correct_answer'):
                missing_answers += 1
                is_valid = False
                issues.append("нет правильного ответа")
            
            # Проверяем количество вариантов
            if len(q.get('options', [])) < 2:
                insufficient_options += 1
                is_valid = False
                issues.append("мало вариантов ответов")
            
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                if i < 5:  # Показываем первые 5 проблемных вопросов
                    print(f"❌ Вопрос {i+1}: {q['question'][:50]}... | Проблемы: {', '.join(issues)}")
        
        print(f"✅ Валидных вопросов: {valid_count}")
        print(f"❌ Невалидных вопросов: {invalid_count}")
        if short_questions > 0:
            print(f"⚠️  Слишком коротких вопросов: {short_questions}")
        if missing_answers > 0:
            print(f"⚠️  Без правильного ответа: {missing_answers}")
        if insufficient_options > 0:
            print(f"⚠️  С недостаточным количеством вариантов: {insufficient_options}")
    
    def analyze_topics(self, questions):
        """Анализирует распределение по темам"""
        print(f"\n📚 АНАЛИЗ ТЕМ:")
        print(f"{'='*50}")
        
        topic_stats = {}
        for q in questions:
            topic = q.get('topic', 'Неизвестная тема')
            topic_stats[topic] = topic_stats.get(topic, 0) + 1
        
        print(f"Всего тем: {len(topic_stats)}")
        print("\nРаспределение по темам:")
        for topic, count in sorted(topic_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {topic}: {count} вопросов")
        
        # Показываем примеры вопросов для каждой темы
        print(f"\n🔍 ПРИМЕРЫ ВОПРОСОВ ПО ТЕМАМ:")
        print(f"{'='*50}")
        
        topic_examples = {}
        for q in questions:
            topic = q.get('topic', 'Неизвестная тема')
            if topic not in topic_examples:
                topic_examples[topic] = q['question'][:100] + "..."
        
        for topic, example in topic_examples.items():
            print(f"\n📖 {topic}:")
            print(f"   Пример: {example}")
    
    def check_duplicates(self, questions):
        """Проверяет дубликаты с базой данных"""
        print(f"\n🔍 ПРОВЕРКА ДУБЛИКАТОВ:")
        print(f"{'='*50}")
        
        duplicates = 0
        new_questions = 0
        
        for q in questions:
            question_text = q['question'].strip()
            exists = self.db.get_explanation_by_question_text(question_text)
            if exists:
                duplicates += 1
                if duplicates <= 3:  # Показываем первые 3 дубликата
                    print(f"🔄 Дубликат: {question_text[:60]}...")
            else:
                new_questions += 1
        
        print(f"🆕 Новых вопросов: {new_questions}")
        print(f"🔄 Дубликатов: {duplicates}")
        
        if duplicates > 3:
            print(f"   ... и еще {duplicates - 3} дубликатов")
    
    def test_all_files(self):
        """Тестирует все PDF файлы в папке files/"""
        files_dir = "files"
        
        if not os.path.exists(files_dir):
            print(f"❌ Папка {files_dir} не найдена")
            return
        
        # Находим все PDF файлы
        pdf_files = []
        for file in os.listdir(files_dir):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(files_dir, file))
        
        if not pdf_files:
            print(f"❌ PDF файлы не найдены в папке {files_dir}")
            return
        
        print(f"🔍 Найдено {len(pdf_files)} PDF файлов для тестирования")
        
        successful_tests = 0
        total_questions = 0
        total_new_questions = 0
        
        for pdf_file in pdf_files:
            success = self.test_pdf_file(pdf_file)
            if success:
                successful_tests += 1
                # Подсчитываем вопросы для статистики
                questions = self.pdf_processor.process_pdf_file(pdf_file)
                total_questions += len(questions)
                
                # Подсчитываем новые вопросы
                new_count = 0
                for q in questions:
                    if not self.db.get_explanation_by_question_text(q['question'].strip()):
                        new_count += 1
                total_new_questions += new_count
        
        # Итоговая статистика
        print(f"\n{'='*80}")
        print(f"📊 ИТОГОВАЯ СТАТИСТИКА")
        print(f"{'='*80}")
        print(f"✅ Успешно протестировано файлов: {successful_tests}/{len(pdf_files)}")
        print(f"📝 Всего вопросов в файлах: {total_questions}")
        print(f"🆕 Новых вопросов для добавления: {total_new_questions}")
        print(f"🔄 Дубликатов: {total_questions - total_new_questions}")
        
        if successful_tests == len(pdf_files) and total_new_questions > 0:
            print(f"\n🎉 ВСЕ ФАЙЛЫ ГОТОВЫ К ДОБАВЛЕНИЮ В БАЗУ ДАННЫХ!")
            print(f"💡 Для добавления запустите: python -m src.services.pdf_processor")
        elif total_new_questions == 0:
            print(f"\n⚠️  ВСЕ ВОПРОСЫ УЖЕ ЕСТЬ В БАЗЕ ДАННЫХ")
        else:
            print(f"\n⚠️  НЕКОТОРЫЕ ФАЙЛЫ ИМЕЮТ ПРОБЛЕМЫ - ПРОВЕРЬТЕ ЛОГИ ВЫШЕ")

def main():
    """Основная функция"""
    print("🧪 ТЕСТИРОВАНИЕ PDF ФАЙЛОВ В ПАПКЕ files/")
    print("=" * 80)
    
    tester = FilesTestRunner()
    tester.test_all_files()

if __name__ == "__main__":
    main() 