"""
Модуль для управления вопросами в админ-панели.
Включает загрузку PDF, добавление, редактирование, удаление вопросов.
"""

from .base import AdminBaseHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import logging
import sqlite3

class QuestionsHandler(AdminBaseHandler):
    """Обработчик для управления вопросами."""

    async def questions_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления вопросами."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        text = f"❓ <b>Управление вопросами</b>\n\nВыберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("📄 Загрузить PDF", callback_data="upload_pdf")],
            [InlineKeyboardButton("➕ Добавить вопрос", callback_data="add_question")],
            [InlineKeyboardButton("✏️ Редактировать вопрос", callback_data="edit_question")],
            [InlineKeyboardButton("🔍 Поиск вопросов", callback_data="search_questions")],
            [InlineKeyboardButton("🗑️ Удалить вопросы по теме", callback_data="delete_questions")],
            [InlineKeyboardButton("❌ Удалить один вопрос", callback_data="delete_single_question")],
            [InlineKeyboardButton("📊 Статистика вопросов", callback_data="questions_stats")],
            [InlineKeyboardButton("📖 Руководство по PDF", callback_data="pdf_format_guide")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def upload_pdf_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало загрузки PDF."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        text = f"📄 <b>Загрузка PDF файла</b>\n\n"
        text += f"Отправьте PDF файл с вопросами для обработки.\n\n"
        text += f"⚠️ <b>Важно:</b>\n"
        text += f"• PDF должен быть в правильном формате\n"
        text += f"• Максимальный размер: 20 МБ\n"
        text += f"• Поддерживаются только PDF файлы\n\n"
        text += f"📖 Нажмите 'Руководство по PDF' для подробной информации о формате."
        
        context.user_data['admin_action'] = 'upload_pdf'
        
        keyboard = [
            [InlineKeyboardButton("📖 Руководство по PDF", callback_data="pdf_format_guide")],
            [InlineKeyboardButton("🔙 Отмена", callback_data="admin_questions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def pdf_format_guide(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать руководство по формату PDF."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        text = f"📖 <b>Руководство по формату PDF</b>\n\n"
        text += f"<b>Формат вопроса:</b>\n"
        text += f"1. Текст вопроса\n"
        text += f"A) Вариант ответа A\n"
        text += f"B) Вариант ответа B\n"
        text += f"C) Вариант ответа C\n"
        text += f"D) Вариант ответа D\n"
        text += f"Ответ: A (или B, C, D)\n\n"
        text += f"<b>Требования:</b>\n"
        text += f"• Каждый вопрос должен быть отделен пустой строкой\n"
        text += f"• Варианты ответов должны начинаться с A), B), C), D)\n"
        text += f"• Правильный ответ указывается как 'Ответ: X'\n"
        text += f"• PDF должен содержать только текст (без изображений)\n\n"
        text += f"<b>Пример:</b>\n"
        text += f"Сколько будет 2+2?\n"
        text += f"A) 3\n"
        text += f"B) 4\n"
        text += f"C) 5\n"
        text += f"D) 6\n"
        text += f"Ответ: B"
        
        keyboard = [
            [InlineKeyboardButton("📄 Загрузить PDF", callback_data="upload_pdf")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_questions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def questions_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Статистика вопросов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            # Используем database facade вместо прямого SQLite подключения
            
            # Общая статистика
            all_questions = self.db.get_all_questions()
            total_questions = len(all_questions)
            
            all_topics = self.db.get_all_topics()
            unique_topics = len(all_topics)
            
            # Подсчитываем вопросы с объяснениями (упрощенная версия)
            questions_with_explanations = 0
            for question in all_questions:
                if question.get('explanation') and question['explanation'].strip():
                    questions_with_explanations += 1
            
            # Статистика по темам (упрощенная версия)
            # Для полной реализации потребуется расширить database facade
            topic_counts = {}
            for question in all_questions:
                topic_id = question.get('topic_id')
                if topic_id:
                    # Находим название темы
                    topic_name = "Неизвестная тема"
                    for topic in all_topics:
                        if topic.get('id') == topic_id:
                            topic_name = topic.get('name', 'Неизвестная тема')
                            break
                    
                    topic_counts[topic_name] = topic_counts.get(topic_name, 0) + 1
            
            # Сортируем темы по количеству вопросов
            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            text = f"📊 <b>Статистика вопросов</b>\n\n"
            text += f"📈 <b>Общая статистика:</b>\n"
            text += f"• Всего вопросов: {total_questions}\n"
            text += f"• Уникальных тем: {unique_topics}\n"
            text += f"• С объяснениями: {questions_with_explanations} ({round(questions_with_explanations/total_questions*100 if total_questions > 0 else 0, 1)}%)\n\n"
            
            if top_topics:
                text += f"🏆 <b>Топ-10 тем по количеству вопросов:</b>\n"
                for i, (topic, count) in enumerate(top_topics, 1):
                    text += f"{i}. {topic}: {count} вопросов\n"
                
        except Exception as e:
            logging.error(f"Error getting questions stats: {e}")
            text = "❌ Ошибка при получении статистики."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_questions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    # === ВРЕМЕННЫЕ ЗАГЛУШКИ ДЛЯ СОВМЕСТИМОСТИ ===
    
    async def add_question_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления нового вопроса."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем список активных тем
        topics = self.db.get_all_topics(active_only=True)
        
        if not topics:
            text = "➕ <b>Добавление вопроса</b>\n\nАктивные темы не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_questions")]]
        else:
            text = "➕ <b>Добавление вопроса</b>\n\nВыберите тему для нового вопроса:\n\n"
            keyboard = []
            
            # Сохраняем темы в контексте для использования по индексу
            context.user_data['add_question_topics'] = topics
            
            for i, topic in enumerate(topics):
                # Ограничиваем длину названия темы для отображения
                display_name = topic['name'][:40] + "..." if len(topic['name']) > 40 else topic['name']
                keyboard.append([InlineKeyboardButton(
                    f"📚 {display_name}",
                    callback_data=f"add_question_topic_{i}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_questions")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def edit_question_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало редактирования вопроса."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        context.user_data['admin_action'] = 'edit_question_search'
        
        text = "✏️ <b>Редактирование вопроса</b>\n\n"
        text += "Введите часть текста вопроса для поиска:"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_questions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def search_questions_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало поиска вопросов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        context.user_data['admin_action'] = 'search_questions'
        
        text = "🔍 <b>Поиск вопросов</b>\n\n"
        text += "Введите текст для поиска в вопросах:"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_questions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def delete_questions_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало удаления вопросов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем список тем с количеством вопросов для удаления
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT s.name as topic, COUNT(*) as count
                    FROM questions q
                    JOIN subtopics s ON q.topic_id = s.id
                    GROUP BY s.name 
                    ORDER BY s.name
                """)
                topics_with_counts = cursor.fetchall()
        except Exception as e:
            logging.error(f"Error getting topics for deletion: {e}")
            topics_with_counts = []
        
        if not topics_with_counts:
            text = "🗑️ <b>Удаление вопросов по теме</b>\n\nВопросы не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_questions")]]
        else:
            text = "🗑️ <b>Удаление вопросов по теме</b>\n\nВыберите тему для удаления всех вопросов:\n\n"
            keyboard = []
            
            # Сохраняем список тем в контексте для последующего использования
            context.user_data['delete_topics_list'] = [topic for topic, count in topics_with_counts]
            
            for idx, (topic, count) in enumerate(topics_with_counts):
                # Обрезаем название темы для отображения, если оно слишком длинное
                display_topic = topic[:40] + "..." if len(topic) > 40 else topic
                keyboard.append([InlineKeyboardButton(
                    f"🗑️ {display_topic} ({count} вопросов)",
                    callback_data=f"delete_questions_idx_{idx}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_questions")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def delete_single_question_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало удаления одного вопроса."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        context.user_data['admin_action'] = 'delete_single_question_search'
        
        text = "❌ <b>Удаление одного вопроса</b>\n\n"
        text += "Введите часть текста вопроса для поиска:"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_questions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    # === ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ИЗ СТАРОГО ФАЙЛА ===

    async def process_pdf_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка загруженного PDF файла."""
        if not update.message.document:
            await update.message.reply_text("❌ Пожалуйста, отправьте PDF файл.")
            return
        
        # Проверяем, что это PDF файл
        if not update.message.document.file_name.lower().endswith('.pdf'):
            await update.message.reply_text("❌ Пожалуйста, отправьте файл в формате PDF.")
            return
        
        # Проверяем размер файла (максимум 20MB)
        if update.message.document.file_size > 20 * 1024 * 1024:
            await update.message.reply_text("❌ Размер файла слишком большой. Максимум 20MB.")
            return
        
        processing_msg = await update.message.reply_text("⏳ Обрабатываю PDF файл...")
        
        try:
            import tempfile
            import os
            import asyncio
            from src.services.pdf_processor import PDFProcessor
            from src.services.ai_service import AIService
            
            # Скачиваем файл
            file = await context.bot.get_file(update.message.document.file_id)
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                await file.download_to_drive(temp_file.name)
                temp_path = temp_file.name
            
            # Обрабатываем PDF
            await processing_msg.edit_text("⏳ Извлекаю вопросы из PDF...")
            
            # Запускаем обработку в отдельном потоке
            pdf_processor = PDFProcessor()
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, pdf_processor.process_pdf_file, temp_path)
            
            # Распаковываем результат
            if isinstance(result, tuple) and len(result) == 2:
                questions, pdf_topic_stats = result
            else:
                questions = result if isinstance(result, list) else []
                pdf_topic_stats = {}
            
            if not questions:
                no_questions_msg = f"❌ <b>Вопросы не найдены</b>\n\n"
                no_questions_msg += f"📄 Файл: {update.message.document.file_name}\n"
                no_questions_msg += f"🔍 В PDF файле не найдено валидных вопросов.\n\n"
                no_questions_msg += "Возможные причины:\n"
                no_questions_msg += "• Неправильный формат файла\n"
                no_questions_msg += "• Темы не существуют в системе\n"
                no_questions_msg += "• Отсутствуют правильные ответы (✅)\n"
                no_questions_msg += "• Некорректная структура вопросов"
                
                keyboard = [
                    [InlineKeyboardButton("📋 Руководство по формату", callback_data="pdf_format_guide")],
                    [InlineKeyboardButton("📄 Попробовать другой файл", callback_data="upload_pdf")],
                    [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="admin_panel")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await processing_msg.edit_text(no_questions_msg, reply_markup=reply_markup, parse_mode='HTML')
                return
            
            await processing_msg.edit_text(f"⏳ Найдено {len(questions)} вопросов. Генерирую объяснения с помощью ИИ...")
            
            # Инициализируем AI сервис для генерации объяснений
            ai_service = AIService()
            
            # Сохраняем вопросы в базу данных
            saved_count = 0
            skipped_count = 0
            topic_stats = {}
            
            for idx, question in enumerate(questions, 1):
                question_text = question['question'].strip()
                topic = question.get('topic', 'Операции с дробями и остатками')
                
                # Обновляем статистику
                topic_stats[topic] = topic_stats.get(topic, 0) + 1
                
                # Проверяем уникальность
                exists = self.db.get_explanation_by_question_text(question_text)
                if exists:
                    skipped_count += 1
                    continue
                
                # Убеждаемся, что options является списком
                options = question.get('options', [])
                if not isinstance(options, list):
                    if isinstance(options, str):
                        options = [opt.strip() for opt in options.split('\n') if opt.strip()]
                    else:
                        options = [str(options)]
                
                if len(options) < 2:
                    logging.warning(f"Недостаточно вариантов ответов для вопроса: {question_text[:100]}...")
                    continue
                
                # Подготавливаем данные для базы
                correct_answer_letter = question.get('correct_answer', 'A')
                correct_answer_index = ord(correct_answer_letter) - ord('A')
                
                if correct_answer_index >= len(options):
                    logging.warning(f"Неверный индекс правильного ответа {correct_answer_letter} для вопроса: {question_text[:100]}...")
                    continue
                
                correct_answer_text = options[correct_answer_index]
                
                # Формируем неправильные варианты
                incorrect_options = []
                for i, option in enumerate(options):
                    if i != correct_answer_index:
                        incorrect_options.append(option)
                
                # Генерируем подробное объяснение с помощью AI
                try:
                    if idx % 3 == 0:  # Обновляем сообщение каждые 3 вопроса
                        await processing_msg.edit_text(f"⏳ Генерирую объяснение для вопроса {idx}/{len(questions)}...")
                    
                    # Определяем язык темы
                    topic_language = self.db.get_topic_language(topic)
                    
                    explanation = ai_service.generate_detailed_explanation(question, correct_answer_text, topic, topic_language)
                    logging.info(f"[AI] Объяснение сгенерировано для вопроса {idx} на языке {topic_language}: {explanation[:100]}...")
                except Exception as e:
                    logging.error(f"[AI] Ошибка генерации объяснения для вопроса {idx}: {e}")
                    explanation = f"Правильный ответ: {correct_answer_letter}) {correct_answer_text}"
                
                db_question = {
                    'topic': topic,
                    'question': question_text,
                    'answer': correct_answer_text,
                    'explanation': explanation,
                    'incorrect_options': '\n'.join(incorrect_options),
                    'question_type': 'standard',
                    'source': 'pdf'
                }
                
                try:
                    self.db.add_question(db_question)
                    saved_count += 1
                except Exception as e:
                    logging.error(f"Error saving question: {e}")
            
            # Формируем отчет
            result_text = f"✅ <b>Обработка завершена!</b>\n\n"
            result_text += f"📄 Файл: {update.message.document.file_name}\n"
            result_text += f"📊 Найдено вопросов: {len(questions)}\n"
            result_text += f"💾 Сохранено новых: {saved_count}\n"
            result_text += f"⏭️ Пропущено (дубликаты): {skipped_count}\n"
            result_text += f"🤖 ИИ объяснения: сгенерированы для всех новых вопросов\n\n"
            
            if topic_stats:
                result_text += "<b>📚 Статистика по темам:</b>\n"
                for topic, count in sorted(topic_stats.items()):
                    result_text += f"• {topic}: {count}\n"
            
            keyboard = [
                [InlineKeyboardButton("📊 Статистика вопросов", callback_data="questions_stats")],
                [InlineKeyboardButton("📄 Загрузить еще PDF", callback_data="upload_pdf")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(result_text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            error_msg = f"❌ <b>Ошибка при обработке PDF</b>\n\n"
            error_msg += f"📄 Файл: {update.message.document.file_name}\n"
            error_msg += f"🚫 Ошибка: {str(e)}\n\n"
            error_msg += "Проверьте формат файла и попробуйте снова."
            
            keyboard = [
                [InlineKeyboardButton("📄 Попробовать снова", callback_data="upload_pdf")],
                [InlineKeyboardButton("📋 Руководство по формату", callback_data="pdf_format_guide")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            logging.error(f"PDF processing error: {e}")
            await processing_msg.edit_text(error_msg, reply_markup=reply_markup, parse_mode='HTML')
        
        finally:
            # Удаляем временный файл
            try:
                if 'temp_path' in locals():
                    os.unlink(temp_path)
            except:
                pass
            
            # Очищаем состояние
            context.user_data.pop('admin_action', None)

    async def delete_questions_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления вопросов."""
        query = update.callback_query
        topic_idx_str = query.data.replace('delete_questions_idx_', '')
        await self.safe_answer_callback(query)
        
        try:
            topic_idx = int(topic_idx_str)
            # Получаем тему по индексу из сохраненного списка
            topics_list = context.user_data.get('delete_topics_list', [])
            if topic_idx >= len(topics_list):
                raise IndexError("Topic index out of range")
            topic = topics_list[topic_idx]
        except (ValueError, IndexError) as e:
            logging.error(f"Error parsing topic index {topic_idx_str}: {e}")
            text = "❌ Ошибка: неверный индекс темы. Попробуйте снова."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="delete_questions")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        # Получаем количество вопросов по теме
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM questions q
                    JOIN subtopics s ON q.topic_id = s.id
                    WHERE s.name = ?
                ''', (topic,))
                count = cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"Error counting questions for topic {topic}: {e}")
            count = 0
        
        text = f"⚠️ <b>Подтверждение удаления</b>\n\n"
        text += f"<b>Тема:</b> {topic}\n"
        text += f"<b>Количество вопросов:</b> {count}\n\n"
        text += f"❗ Это действие нельзя отменить!\n"
        text += f"Вы уверены, что хотите удалить все вопросы по этой теме?"
        
        # Сохраняем тему для следующего шага
        context.user_data['delete_topic_name'] = topic
        
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data="delete_questions_execute_confirmed")],
            [InlineKeyboardButton("❌ Отмена", callback_data="delete_questions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def delete_questions_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления вопросов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем тему из контекста
        topic = context.user_data.get('delete_topic_name')
        if not topic:
            text = "❌ Ошибка: тема не найдена. Попробуйте снова."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="delete_questions")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM questions WHERE topic_id = ?', (topic,))
                count_before = cursor.fetchone()[0]
                
                cursor.execute('''
                    DELETE FROM questions 
                    WHERE topic_id = (SELECT id FROM subtopics WHERE name = ?)
                ''', (topic,))
                deleted_count = cursor.rowcount
                conn.commit()
            
            text = f"✅ <b>Удаление завершено</b>\n\n"
            text += f"<b>Тема:</b> {topic}\n"
            text += f"<b>Удалено вопросов:</b> {deleted_count}\n\n"
            text += f"Все вопросы по теме '{topic}' были успешно удалены."
            
        except Exception as e:
            logging.error(f"Error deleting questions for topic {topic}: {e}")
            text = f"❌ <b>Ошибка при удалении</b>\n\n"
            text += f"Не удалось удалить вопросы по теме '{topic}'.\n"
            text += f"Ошибка: {str(e)}"
        
        # Очищаем контекст
        context.user_data.pop('delete_topic_name', None)
        context.user_data.pop('delete_topics_list', None)
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика вопросов", callback_data="questions_stats")],
            [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def add_question_topic_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Тема выбрана, запрашиваем текст вопроса."""
        query = update.callback_query
        topic_index = int(query.data.replace('add_question_topic_', ''))
        await self.safe_answer_callback(query)
        
        # Получаем тему по индексу
        topics = context.user_data.get('add_question_topics', [])
        if topic_index >= len(topics):
            await query.edit_message_text(
                "❌ Ошибка: тема не найдена. Попробуйте снова.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_questions")]])
            )
            return
        
        topic = topics[topic_index]['name']
        
        context.user_data['admin_action'] = 'add_question_text'
        context.user_data['new_question_topic'] = topic
        
        text = f"➕ <b>Добавление вопроса</b>\n\n"
        text += f"<b>Тема:</b> {topic}\n\n"
        text += "Введите текст вопроса:"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="add_question")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def delete_single_question_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления одного вопроса."""
        query = update.callback_query
        question_id = int(query.data.replace('delete_single_question_confirm_', ''))
        await self.safe_answer_callback(query)
        
        # Получаем информацию о вопросе
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.name as topic, q.question 
                    FROM questions q 
                    JOIN subtopics s ON q.topic_id = s.id 
                    WHERE q.id = ?
                ''', (question_id,))
                result = cursor.fetchone()
        except Exception as e:
            logging.error(f"Error getting question {question_id}: {e}")
            result = None
        
        if not result:
            text = "❌ Вопрос не найден."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="delete_single_question")]]
        else:
            topic, question = result
            short_question = question[:100] + "..." if len(question) > 100 else question
            
            text = f"⚠️ <b>Подтверждение удаления вопроса</b>\n\n"
            text += f"<b>ID:</b> {question_id}\n"
            text += f"<b>Тема:</b> {topic}\n"
            text += f"<b>Вопрос:</b> {short_question}\n\n"
            text += f"❗ Это действие нельзя отменить!\n"
            text += f"Вы уверены, что хотите удалить этот вопрос?"
            
            keyboard = [
                [InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_single_question_execute_{question_id}")],
                [InlineKeyboardButton("❌ Отмена", callback_data="delete_single_question")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def delete_single_question_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления одного вопроса."""
        query = update.callback_query
        question_id = int(query.data.replace('delete_single_question_execute_', ''))
        await self.safe_answer_callback(query)
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
                deleted_count = cursor.rowcount
                conn.commit()
            
            if deleted_count > 0:
                text = f"✅ <b>Вопрос удален</b>\n\n"
                text += f"Вопрос с ID {question_id} был успешно удален."
            else:
                text = f"❌ <b>Вопрос не найден</b>\n\n"
                text += f"Вопрос с ID {question_id} не найден в базе данных."
                
        except Exception as e:
            logging.error(f"Error deleting question {question_id}: {e}")
            text = f"❌ <b>Ошибка при удалении</b>\n\n"
            text += f"Не удалось удалить вопрос с ID {question_id}.\n"
            text += f"Ошибка: {str(e)}"
        
        keyboard = [
            [InlineKeyboardButton("❌ Удалить еще вопрос", callback_data="delete_single_question")],
            [InlineKeyboardButton("📊 Статистика вопросов", callback_data="questions_stats")],
            [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def generate_ai_explanation_for_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Генерация ИИ объяснения для редактирования."""
        query = update.callback_query
        question_id = int(query.data.replace('generate_ai_explanation_', ''))
        await self.safe_answer_callback(query)
        
        try:
            # Получаем информацию о вопросе
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.name as topic, q.question, q.answer 
                    FROM questions q 
                    JOIN subtopics s ON q.topic_id = s.id 
                    WHERE q.id = ?
                ''', (question_id,))
                result = cursor.fetchone()
            
            if not result:
                await query.edit_message_text("❌ Вопрос не найден.")
                return
            
            topic, question, answer = result
            
            # Генерируем объяснение с помощью ИИ
            await query.edit_message_text("🤖 Генерирую объяснение с помощью ИИ...")
            
            from src.services.ai_service import AIService
            ai_service = AIService()
            
            # Определяем язык темы
            topic_language = self.db.get_topic_language(topic)
            
            explanation = ai_service.generate_detailed_explanation(question, answer, topic, topic_language)
            
            # Обновляем объяснение в базе данных
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE questions SET explanation = ? WHERE id = ?', (explanation, question_id))
                conn.commit()
            
            text = f"✅ <b>ИИ объяснение сгенерировано</b>\n\n"
            text += f"<b>ID:</b> {question_id}\n"
            text += f"<b>Вопрос:</b> {question[:100]}...\n\n"
            text += f"<b>🤖 Новое объяснение:</b>\n{explanation}"
            
            keyboard = [
                [InlineKeyboardButton("✏️ Редактировать еще", callback_data="edit_question")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logging.error(f"Error generating AI explanation for question {question_id}: {e}")
            text = f"❌ <b>Ошибка генерации объяснения</b>\n\n"
            text += f"Не удалось сгенерировать объяснение для вопроса {question_id}.\n"
            text += f"Ошибка: {str(e)}"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data=f"generate_ai_explanation_{question_id}")],
                [InlineKeyboardButton("✏️ Ввести вручную", callback_data=f"manual_explanation_{question_id}")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def manual_explanation_for_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Ручное объяснение для редактирования."""
        query = update.callback_query
        question_id = int(query.data.replace('manual_explanation_', ''))
        await self.safe_answer_callback(query)
        
        context.user_data['admin_action'] = 'edit_question_explanation'
        context.user_data['edit_question_id'] = question_id
        
        text = f"✏️ <b>Ручное редактирование объяснения</b>\n\n"
        text += f"Введите новое объяснение для вопроса ID {question_id}:"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="edit_question")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    # === ОБРАБОТЧИКИ ТЕКСТА ДЛЯ ВОПРОСОВ ===

    async def handle_search_questions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_text: str) -> None:
        """Обработка поиска вопросов."""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                # Получаем все вопросы и фильтруем в Python для корректной работы с казахскими буквами
                cursor.execute('''
                    SELECT q.id, s.name as topic, q.question, q.answer, q.explanation
                    FROM questions q
                    JOIN subtopics s ON q.topic_id = s.id
                    ORDER BY s.name, q.id
                ''')
                all_results = cursor.fetchall()
                
                # Фильтруем результаты в Python для корректной работы с казахскими буквами
                search_lower = search_text.lower()
                results = []
                for row in all_results:
                    question_lower = row[2].lower()  # row[2] это q.question
                    if search_lower in question_lower:
                        results.append(row)
                        if len(results) >= 20:  # Ограничиваем до 20 результатов
                            break
                            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка поиска: {e}")
            context.user_data.pop('admin_action', None)
            return
        
        if not results:
            await update.message.reply_text(f"🔍 По запросу '<i>{search_text}</i>' вопросы не найдены.\n\nПопробуйте другой поисковый запрос:", parse_mode='HTML')
            return
        
        text = f"🔍 <b>Найдено {len(results)} вопросов</b>\n\n"
        
        for i, (q_id, topic, question, answer, explanation) in enumerate(results, 1):
            short_question = question[:80] + "..." if len(question) > 80 else question
            text += f"<b>ID {q_id}</b> | {topic}\n{short_question}\n\n"
        
        # Добавляем кнопки навигации
        keyboard = [
            [InlineKeyboardButton("🔄 Новый поиск", callback_data="search_questions")],
            [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.user_data.pop('admin_action', None)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_add_question_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question_text: str) -> None:
        """Обработка добавления вопроса - этап 2 (текст вопроса)."""
        context.user_data['new_question_text'] = question_text
        context.user_data['admin_action'] = 'add_question_option_a'
        
        await update.message.reply_text(f"Введите вариант A:")

    async def handle_add_question_option_a(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option_a: str) -> None:
        """Обработка добавления вопроса - этап 3 (вариант A)."""
        context.user_data['new_question_option_a'] = option_a
        context.user_data['admin_action'] = 'add_question_option_b'
        
        await update.message.reply_text(f"Введите вариант B:")

    async def handle_add_question_option_b(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option_b: str) -> None:
        """Обработка добавления вопроса - этап 4 (вариант B)."""
        context.user_data['new_question_option_b'] = option_b
        context.user_data['admin_action'] = 'add_question_option_c'
        
        await update.message.reply_text(f"Введите вариант C:")

    async def handle_add_question_option_c(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option_c: str) -> None:
        """Обработка добавления вопроса - этап 5 (вариант C)."""
        context.user_data['new_question_option_c'] = option_c
        context.user_data['admin_action'] = 'add_question_option_d'
        
        await update.message.reply_text(f"Введите вариант D:")

    async def handle_add_question_option_d(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option_d: str) -> None:
        """Обработка добавления вопроса - этап 6 (вариант D)."""
        context.user_data['new_question_option_d'] = option_d
        context.user_data['admin_action'] = 'add_question_correct'
        
        await update.message.reply_text(f"Введите правильный ответ (A, B, C или D):")

    async def handle_add_question_correct(self, update: Update, context: ContextTypes.DEFAULT_TYPE, correct_text: str) -> None:
        """Обработка добавления вопроса - этап 7 (правильный ответ) - финальный с ИИ генерацией объяснения."""
        correct_letter = correct_text.upper().strip()
        
        if correct_letter not in ['A', 'B', 'C', 'D']:
            await update.message.reply_text("❌ Введите правильный ответ: A, B, C или D. Попробуйте еще раз:")
            return

        context.user_data['new_question_correct'] = correct_letter
        
        # Собираем все данные для генерации объяснения
        topic = context.user_data.get('new_question_topic')
        question_text = context.user_data.get('new_question_text')
        option_a = context.user_data.get('new_question_option_a')
        option_b = context.user_data.get('new_question_option_b')
        option_c = context.user_data.get('new_question_option_c')
        option_d = context.user_data.get('new_question_option_d')
        
        # Определяем правильный ответ
        options_map = {'A': option_a, 'B': option_b, 'C': option_c, 'D': option_d}
        correct_answer = options_map[correct_letter]
        
        # Показываем сообщение о генерации объяснения
        await update.message.reply_text("🤖 Генерирую объяснение с помощью ИИ...")
        
        # Инициализируем AI сервис для генерации объяснения
        try:
            from src.services.ai_service import AIService
            ai_service = AIService()
            
            # Определяем язык темы
            topic_language = self.db.get_topic_language(topic)
            
            # Генерируем объяснение
            explanation = ai_service.generate_detailed_explanation(
                question_text, 
                correct_answer, 
                topic,
                topic_language
            )
            
            # Формируем неправильные варианты
            incorrect_options = []
            for letter, option in options_map.items():
                if letter != correct_letter:
                    incorrect_options.append(option)
            
            # Создаем вопрос для базы данных
            db_question = {
                'topic': topic,
                'question': question_text,
                'answer': correct_answer,
                'explanation': explanation,
                'incorrect_options': '\n'.join(incorrect_options),
                'question_type': 'standard',
                'source': 'admin'
            }
            
            # Сохраняем в базу данных
            self.db.add_question(db_question)
            
            text = f"✅ <b>Вопрос добавлен с ИИ объяснением!</b>\n\n"
            text += f"<b>Тема:</b> {topic}\n"
            text += f"<b>Вопрос:</b> {question_text}\n"
            text += f"<b>Правильный ответ:</b> {correct_letter}) {correct_answer}\n\n"
            text += f"<b>🤖 ИИ объяснение:</b>\n{explanation}"
            
            # Добавляем кнопки навигации
            keyboard = [
                [InlineKeyboardButton("➕ Добавить еще вопрос", callback_data="add_question")],
                [InlineKeyboardButton("📊 Статистика вопросов", callback_data="questions_stats")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            # В случае ошибки ИИ генерации, переходим к ручному вводу
            error_text = f"⚠️ Ошибка ИИ генерации: {e}\n\nВведите объяснение вручную:"
            context.user_data['admin_action'] = 'add_question_explanation'
            await update.message.reply_text(error_text)
            return
        
        # Очищаем все данные после успешного добавления
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_question_topic', None)
        context.user_data.pop('new_question_text', None)
        context.user_data.pop('new_question_option_a', None)
        context.user_data.pop('new_question_option_b', None)
        context.user_data.pop('new_question_option_c', None)
        context.user_data.pop('new_question_option_d', None)
        context.user_data.pop('new_question_correct', None)

    async def handle_add_question_explanation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, explanation: str) -> None:
        """Обработка добавления вопроса - этап 8 (объяснение) - финальный."""
        # Собираем все данные
        topic = context.user_data.get('new_question_topic')
        question_text = context.user_data.get('new_question_text')
        option_a = context.user_data.get('new_question_option_a')
        option_b = context.user_data.get('new_question_option_b')
        option_c = context.user_data.get('new_question_option_c')
        option_d = context.user_data.get('new_question_option_d')
        correct_letter = context.user_data.get('new_question_correct')
        
        # Определяем правильный ответ
        options_map = {'A': option_a, 'B': option_b, 'C': option_c, 'D': option_d}
        correct_answer = options_map[correct_letter]
        
        # Формируем неправильные варианты
        incorrect_options = []
        for letter, option in options_map.items():
            if letter != correct_letter:
                incorrect_options.append(option)
        
        # Создаем вопрос для базы данных
        db_question = {
            'topic': topic,
            'question': question_text,
            'answer': correct_answer,
            'explanation': explanation,
            'incorrect_options': '\n'.join(incorrect_options),
            'question_type': 'standard',
            'source': 'admin'
        }
        
        try:
            self.db.add_question(db_question)
            
            text = f"✅ <b>Вопрос добавлен!</b>\n\n"
            text += f"<b>Тема:</b> {topic}\n"
            text += f"<b>Вопрос:</b> {question_text}\n"
            text += f"<b>Правильный ответ:</b> {correct_letter}) {correct_answer}\n"
            text += f"<b>Объяснение:</b> {explanation}"
            
            # Добавляем кнопки навигации
            keyboard = [
                [InlineKeyboardButton("➕ Добавить еще вопрос", callback_data="add_question")],
                [InlineKeyboardButton("📊 Статистика вопросов", callback_data="questions_stats")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e:
            error_text = f"❌ Ошибка при сохранении вопроса: {e}"
            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="add_question")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(error_text, reply_markup=reply_markup)
        
        # Очищаем все данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_question_topic', None)
        context.user_data.pop('new_question_text', None)
        context.user_data.pop('new_question_option_a', None)
        context.user_data.pop('new_question_option_b', None)
        context.user_data.pop('new_question_option_c', None)
        context.user_data.pop('new_question_option_d', None)
        context.user_data.pop('new_question_correct', None)

    async def handle_edit_question_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_text: str) -> None:
        """Обработка поиска вопроса для редактирования."""
        logging.info(f"[EDIT_SEARCH] Starting search for: '{search_text}'")
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                # Получаем все вопросы и фильтруем в Python для корректной работы с казахскими буквами
                cursor.execute('''
                    SELECT q.id, s.name as topic, q.question, q.answer, q.explanation
                    FROM questions q
                    JOIN subtopics s ON q.topic_id = s.id
                    ORDER BY s.name, q.id
                ''')
                all_results = cursor.fetchall()
                logging.info(f"[EDIT_SEARCH] Found {len(all_results)} total questions in database")
                
                # Фильтруем результаты в Python для корректной работы с казахскими буквами
                search_lower = search_text.lower()
                results = []
                for row in all_results:
                    question_lower = row[2].lower()  # row[2] это q.question
                    if search_lower in question_lower:
                        results.append(row)
                        if len(results) >= 10:  # Ограничиваем до 10 результатов
                            break
                            
                logging.info(f"[EDIT_SEARCH] Filtered to {len(results)} matching questions")
                            
        except Exception as e:
            logging.error(f"[EDIT_SEARCH] Database error: {e}")
            await update.message.reply_text(f"❌ Ошибка поиска: {e}")
            context.user_data.pop('admin_action', None)
            return
        
        if not results:
            logging.info(f"[EDIT_SEARCH] No results found for search: '{search_text}'")
            await update.message.reply_text(f"🔍 По запросу '<i>{search_text}</i>' вопросы не найдены.\n\nПопробуйте другой поисковый запрос:", parse_mode='HTML')
            return
        
        text = f"🔍 <b>Найдено {len(results)} вопросов</b>\n\nВыберите вопрос для редактирования:\n\n"
        keyboard = []
        
        for q_id, topic, question, answer, explanation in results:
            short_question = question[:50] + "..." if len(question) > 50 else question
            callback_data = f"edit_question_select_{q_id}"
            logging.info(f"[EDIT_SEARCH] Creating button for question {q_id} with callback_data: '{callback_data}'")
            keyboard.append([InlineKeyboardButton(
                f"✏️ ID {q_id}: {short_question}",
                callback_data=callback_data
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="edit_question")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        logging.info(f"[EDIT_SEARCH] Sending message with {len(keyboard)} buttons")
        context.user_data.pop('admin_action', None)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_edit_question_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question_id_text: str) -> None:
        """Обработка ID вопроса для редактирования."""
        logging.info(f"[EDIT_ID] Called with question_id_text: '{question_id_text}'")
        logging.info(f"[EDIT_ID] Update type: {type(update)}")
        
        query = update.callback_query
        if query:
            logging.info(f"[EDIT_ID] Callback query data: '{query.data}'")
            logging.info(f"[EDIT_ID] Callback query from user: {query.from_user.id}")
        else:
            logging.error("[EDIT_ID] No callback query found in update!")
            return
        
        # Не отвечаем на callback здесь, так как это уже сделано в делегирующей функции
        
        try:
            question_id = int(question_id_text.strip())
            logging.info(f"[EDIT_ID] Parsed question_id: {question_id}")
        except ValueError as e:
            logging.error(f"[EDIT_ID] Failed to parse question_id from '{question_id_text}': {e}")
            await query.edit_message_text("❌ Введите корректный ID вопроса (число):")
            return
        
        # Получаем информацию о вопросе
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.name as topic, q.question, q.answer, q.explanation, q.incorrect_options, q.topic_id
                    FROM questions q 
                    JOIN subtopics s ON q.topic_id = s.id 
                    WHERE q.id = ?
                ''', (question_id,))
                result = cursor.fetchone()
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка получения вопроса: {e}")
            context.user_data.pop('admin_action', None)
            return
        
        if not result:
            await query.edit_message_text(f"❌ Вопрос с ID {question_id} не найден. Попробуйте другой ID:")
            return
        
        topic, question, answer, explanation, incorrect_options, topic_id = result
        
        # Парсим варианты ответов
        options = []
        if incorrect_options:
            try:
                import json
                # Сначала пробуем JSON формат
                options_data = json.loads(incorrect_options)
                if isinstance(options_data, list):
                    options = options_data
                elif isinstance(options_data, dict):
                    options = [options_data.get('A', ''), options_data.get('B', ''), 
                              options_data.get('C', ''), options_data.get('D', '')]
            except:
                # Если JSON не работает, пробуем простой текст с переносами строк
                try:
                    # Разбиваем по переносам строк и убираем пустые строки
                    text_options = [opt.strip() for opt in incorrect_options.split('\n') if opt.strip()]
                    options = text_options
                except:
                    options = []
        
        # Добавляем правильный ответ к вариантам для полного отображения
        all_options = []
        if answer:
            all_options.append(answer.strip())
        if options:
            for opt in options:
                if opt.strip() and opt.strip() not in [answer.strip() if answer else ""]:
                    all_options.append(opt.strip())
        
        text = f"✏️ <b>Редактирование вопроса ID {question_id}</b>\n\n"
        text += f"<b>Тема:</b> {topic}\n"
        text += f"<b>Вопрос:</b> {question[:200]}{'...' if len(question) > 200 else ''}\n"
        text += f"<b>Правильный ответ:</b> {answer}\n"
        
        if all_options:  # Проверяем что есть хотя бы один вариант
            text += "<b>Варианты ответов:</b>\n"
            labels = ['A', 'B', 'C', 'D']
            for i, option in enumerate(all_options[:4]):
                if option:
                    # Проверяем, является ли этот вариант правильным ответом
                    if option.strip() == answer.strip() if answer else False:
                        text += f"✅ {labels[i]}) {option} <i>(правильный)</i>\n"
                    else:
                        text += f"❌ {labels[i]}) {option}\n"
        else:
            text += "<b>Варианты ответов:</b> Отсутствуют\n"
        
        text += f"<b>Объяснение:</b> {(explanation or 'Отсутствует')[:200]}{'...' if explanation and len(explanation) > 200 else ''}\n\n"
        text += "Выберите что хотите изменить:"
        
        keyboard = [
            [InlineKeyboardButton("📝 Изменить тему", callback_data=f"edit_question_topic_{question_id}")],
            [InlineKeyboardButton("❓ Изменить текст вопроса", callback_data=f"edit_question_text_{question_id}")],
            [InlineKeyboardButton("✅ Изменить правильный ответ", callback_data=f"edit_question_correct_{question_id}")],
            [InlineKeyboardButton("📋 Изменить варианты ответов", callback_data=f"edit_question_options_{question_id}")],
            [InlineKeyboardButton("💡 Изменить объяснение", callback_data=f"edit_question_explanation_{question_id}")],
            [InlineKeyboardButton("🤖 Сгенерировать ИИ объяснение", callback_data=f"generate_ai_explanation_{question_id}")],
            [InlineKeyboardButton("🔙 Назад к поиску", callback_data="edit_question")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Сохраняем ID вопроса в контексте для дальнейшего использования
        context.user_data['editing_question_id'] = question_id
        context.user_data.pop('admin_action', None)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_edit_question_explanation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_explanation: str) -> None:
        """Обработка нового объяснения вопроса."""
        question_id = context.user_data.get('edit_question_id')
        
        if not question_id:
            await update.message.reply_text("❌ Ошибка: ID вопроса не найден.")
            context.user_data.pop('admin_action', None)
            return
        
        try:
            # Обновляем объяснение в базе данных
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE questions SET explanation = ? WHERE id = ?', (new_explanation, question_id))
                conn.commit()
            
            text = f"✅ <b>Объяснение обновлено</b>\n\n"
            text += f"<b>ID вопроса:</b> {question_id}\n"
            text += f"<b>Новое объяснение:</b> {new_explanation}"
            
            keyboard = [
                [InlineKeyboardButton("✏️ Редактировать еще", callback_data="edit_question")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logging.error(f"Error updating question explanation: {e}")
            text = f"❌ <b>Ошибка обновления объяснения</b>\n\n"
            text += f"Не удалось обновить объяснение для вопроса {question_id}.\n"
            text += f"Ошибка: {str(e)}"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data=f"manual_explanation_{question_id}")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup)
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('edit_question_id', None)

    async def handle_delete_single_question_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_text: str) -> None:
        """Обработка поиска для удаления одного вопроса."""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                # Получаем все вопросы и фильтруем в Python для корректной работы с казахскими буквами
                cursor.execute('''
                    SELECT q.id, s.name as topic, q.question
                    FROM questions q
                    JOIN subtopics s ON q.topic_id = s.id
                    ORDER BY s.name, q.id
                ''')
                all_results = cursor.fetchall()
                
                # Фильтруем результаты в Python для корректной работы с казахскими буквами
                search_lower = search_text.lower()
                results = []
                for row in all_results:
                    question_lower = row[2].lower()  # row[2] это q.question
                    if search_lower in question_lower:
                        results.append(row)
                        if len(results) >= 10:  # Ограничиваем до 10 результатов
                            break
                            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка поиска: {e}")
            context.user_data.pop('admin_action', None)
            return
        
        if not results:
            await update.message.reply_text(f"🔍 По запросу '<i>{search_text}</i>' вопросы не найдены.\n\nПопробуйте другой поисковый запрос:", parse_mode='HTML')
            return
        
        text = f"🔍 <b>Найдено {len(results)} вопросов</b>\n\nВыберите вопрос для удаления:\n\n"
        keyboard = []
        
        for q_id, topic, question in results:
            short_question = question[:50] + "..." if len(question) > 50 else question
            keyboard.append([InlineKeyboardButton(
                f"🗑️ ID {q_id}: {short_question}",
                callback_data=f"delete_single_question_confirm_{q_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="delete_single_question")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.user_data.pop('admin_action', None)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def improve_explanations_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало улучшения объяснений."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем статистику объяснений
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Подсчет общего количества вопросов
                cursor.execute("SELECT COUNT(*) FROM questions")
                total_questions = cursor.fetchone()[0]
                
                # Подсчет вопросов с короткими объяснениями (менее 100 символов)
                cursor.execute("SELECT COUNT(*) FROM questions WHERE LENGTH(explanation) < 100")
                short_explanations = cursor.fetchone()[0]
                
                # Подсчет вопросов без пошагового объяснения
                cursor.execute("""
                    SELECT COUNT(*) FROM questions 
                    WHERE explanation NOT LIKE '%Шаг%' 
                    AND explanation NOT LIKE '%шаг%'
                    AND explanation NOT LIKE '%қадам%'
                    AND explanation NOT LIKE '%ҚАДАМ%'
                """)
                no_steps = cursor.fetchone()[0]
                
        except Exception as e:
            logging.error(f"Error getting explanation stats: {e}")
            total_questions = 0
            short_explanations = 0
            no_steps = 0
        
        text = f"🤖 <b>Улучшение объяснений</b>\n\n"
        text += f"📊 <b>Статистика:</b>\n"
        text += f"• Всего вопросов: {total_questions}\n"
        text += f"• Короткие объяснения (< 100 символов): {short_explanations}\n"
        text += f"• Без пошагового объяснения: {no_steps}\n\n"
        text += f"⚠️ <b>Внимание:</b> Процесс может занять несколько минут.\n"
        text += f"Будут улучшены объяснения, которые:\n"
        text += f"• Слишком короткие\n"
        text += f"• Не содержат пошаговое решение\n"
        text += f"• Написаны сложным языком\n\n"
        text += f"Выберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("🚀 Улучшить все короткие объяснения", callback_data="improve_short_explanations")],
            [InlineKeyboardButton("📝 Улучшить объяснения без шагов", callback_data="improve_no_steps_explanations")],
            [InlineKeyboardButton("🎯 Улучшить все объяснения", callback_data="improve_all_explanations")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_questions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def improve_short_explanations(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Улучшение коротких объяснений."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        await self._process_explanation_improvement(query, "short")

    async def improve_no_steps_explanations(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Улучшение объяснений без шагов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        await self._process_explanation_improvement(query, "no_steps")

    async def improve_all_explanations(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Улучшение всех объяснений."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        await self._process_explanation_improvement(query, "all")

    async def _process_explanation_improvement(self, query, improvement_type: str) -> None:
        """Обработка улучшения объяснений."""
        try:
            # Показываем сообщение о начале процесса
            await query.edit_message_text("🤖 Начинаю улучшение объяснений...\n\nЭто может занять несколько минут.")
            
            # Получаем вопросы для улучшения
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                if improvement_type == "short":
                    cursor.execute("""
                        SELECT q.id, q.question, q.answer, q.explanation, s.name as topic
                        FROM questions q
                        JOIN subtopics s ON q.topic_id = s.id
                        WHERE LENGTH(q.explanation) < 100
                        ORDER BY q.id
                    """)
                elif improvement_type == "no_steps":
                    cursor.execute("""
                        SELECT q.id, q.question, q.answer, q.explanation, s.name as topic
                        FROM questions q
                        JOIN subtopics s ON q.topic_id = s.id
                        WHERE q.explanation NOT LIKE '%Шаг%' 
                        AND q.explanation NOT LIKE '%шаг%'
                        AND q.explanation NOT LIKE '%қадам%'
                        AND q.explanation NOT LIKE '%ҚАДАМ%'
                        ORDER BY q.id
                    """)
                else:  # all
                    cursor.execute("""
                        SELECT q.id, q.question, q.answer, q.explanation, s.name as topic
                        FROM questions q
                        JOIN subtopics s ON q.topic_id = s.id
                        ORDER BY q.id
                        LIMIT 50
                    """)
                
                questions_to_improve = cursor.fetchall()
            
            if not questions_to_improve:
                await query.edit_message_text("✅ Нет вопросов для улучшения!")
                return
            
            # Инициализируем AI сервис
            from src.services.ai_service import AIService
            ai_service = AIService()
            
            improved_count = 0
            total_count = len(questions_to_improve)
            
            for i, (question_id, question, answer, old_explanation, topic) in enumerate(questions_to_improve, 1):
                try:
                    # Обновляем сообщение каждые 5 вопросов
                    if i % 5 == 0 or i == 1:
                        await query.edit_message_text(
                            f"🤖 Улучшаю объяснения...\n\n"
                            f"Обработано: {i}/{total_count}\n"
                            f"Улучшено: {improved_count}\n\n"
                            f"Текущий вопрос: {question[:50]}..."
                        )
                    
                    # Определяем язык темы
                    topic_language = self.db.get_topic_language(topic)
                    
                    # Улучшаем объяснение
                    improved_explanation = ai_service.improve_existing_explanation(
                        question, answer, old_explanation, topic, topic_language
                    )
                    
                    # Проверяем, что объяснение действительно улучшилось
                    if (len(improved_explanation) > len(old_explanation) * 1.2 and 
                        improved_explanation != old_explanation):
                        
                        # Сохраняем улучшенное объяснение
                        with sqlite3.connect(self.db.db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                'UPDATE questions SET explanation = ? WHERE id = ?',
                                (improved_explanation, question_id)
                            )
                            conn.commit()
                        
                        improved_count += 1
                        logging.info(f"Improved explanation for question {question_id}")
                    
                except Exception as e:
                    logging.error(f"Error improving explanation for question {question_id}: {e}")
                    continue
            
            # Финальное сообщение
            text = f"✅ <b>Улучшение объяснений завершено!</b>\n\n"
            text += f"📊 <b>Результаты:</b>\n"
            text += f"• Обработано вопросов: {total_count}\n"
            text += f"• Улучшено объяснений: {improved_count}\n"
            text += f"• Пропущено: {total_count - improved_count}\n\n"
            text += f"💡 Улучшенные объяснения теперь содержат:\n"
            text += f"• Пошаговое решение\n"
            text += f"• Подробные вычисления\n"
            text += f"• Простой язык для детей\n"
            text += f"• Проверку ответа"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Улучшить еще", callback_data="improve_explanations")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logging.error(f"Error in explanation improvement process: {e}")
            text = f"❌ <b>Ошибка при улучшении объяснений</b>\n\n"
            text += f"Произошла ошибка: {str(e)}\n\n"
            text += f"Попробуйте еще раз или обратитесь к разработчику."
            
            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="improve_explanations")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML') 

    # === NEW EDIT FUNCTIONS ===
    
    async def edit_question_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения темы вопроса."""
        query = update.callback_query
        question_id = int(query.data.split('_')[-1])
        await self.safe_answer_callback(query)
        
        # Получаем доступные темы
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.id, s.name, m.name as main_topic
                    FROM subtopics s
                    JOIN main_topics m ON s.main_topic_id = m.id
                    WHERE s.is_active = 1 AND m.is_active = 1
                    ORDER BY m.name, s.name
                ''')
                topics = cursor.fetchall()
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка получения тем: {e}")
            return
        
        text = f"📝 <b>Изменение темы вопроса ID {question_id}</b>\n\n"
        text += "Выберите новую тему:"
        
        keyboard = []
        current_main_topic = None
        
        for topic_id, topic_name, main_topic in topics[:20]:  # Ограничиваем для избежания длинного меню
            if current_main_topic != main_topic:
                current_main_topic = main_topic
                
            keyboard.append([InlineKeyboardButton(
                f"{main_topic}: {topic_name}",
                callback_data=f"edit_topic_select_{question_id}_{topic_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_question_select_{question_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def edit_question_topic_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка выбора новой темы."""
        query = update.callback_query
        parts = query.data.split('_')
        question_id = int(parts[3])
        new_topic_id = int(parts[4])
        await self.safe_answer_callback(query)
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем название новой темы
                cursor.execute('SELECT name FROM subtopics WHERE id = ?', (new_topic_id,))
                new_topic_name = cursor.fetchone()[0]
                
                # Обновляем тему вопроса
                cursor.execute('UPDATE questions SET topic_id = ? WHERE id = ?', (new_topic_id, question_id))
                conn.commit()
                
                # Автоматически обновляем объяснение
                await self._auto_update_explanation_after_change(question_id, "topic")
                
            text = f"✅ <b>Тема изменена</b>\n\n"
            text += f"<b>ID вопроса:</b> {question_id}\n"
            text += f"<b>Новая тема:</b> {new_topic_name}\n"
            text += f"<b>Объяснение:</b> Автоматически обновлено"
            
            keyboard = [
                [InlineKeyboardButton("✏️ Продолжить редактирование", callback_data=f"edit_question_select_{question_id}")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка изменения темы: {e}")
    
    async def edit_question_text_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения текста вопроса."""
        query = update.callback_query
        question_id = int(query.data.split('_')[-1])
        await self.safe_answer_callback(query)
        
        # Получаем текущий текст вопроса
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT question FROM questions WHERE id = ?', (question_id,))
                current_question = cursor.fetchone()[0]
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка получения вопроса: {e}")
            return
        
        text = f"❓ <b>Изменение текста вопроса ID {question_id}</b>\n\n"
        text += f"<b>Текущий текст:</b>\n{current_question}\n\n"
        text += "Введите новый текст вопроса:"
        
        context.user_data['admin_action'] = 'edit_question_text'
        context.user_data['editing_question_id'] = question_id
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"edit_question_select_{question_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def edit_question_correct_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения правильного ответа."""
        query = update.callback_query
        question_id = int(query.data.split('_')[-1])
        await self.safe_answer_callback(query)
        
        # Получаем текущий ответ
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT answer FROM questions WHERE id = ?', (question_id,))
                current_answer = cursor.fetchone()[0]
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка получения ответа: {e}")
            return
        
        text = f"✅ <b>Изменение правильного ответа ID {question_id}</b>\n\n"
        text += f"<b>Текущий ответ:</b> {current_answer}\n\n"
        text += "Введите новый правильный ответ:"
        
        context.user_data['admin_action'] = 'edit_question_correct'
        context.user_data['editing_question_id'] = question_id
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"edit_question_select_{question_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def edit_question_options_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения вариантов ответов."""
        query = update.callback_query
        question_id = int(query.data.split('_')[-1])
        await self.safe_answer_callback(query)
        
        # Получаем текущие варианты и правильный ответ
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT incorrect_options, answer FROM questions WHERE id = ?', (question_id,))
                result = cursor.fetchone()
                if result:
                    incorrect_options, correct_answer = result
                else:
                    incorrect_options, correct_answer = None, None
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка получения вариантов: {e}")
            return
        
        # Парсим варианты ответов
        options = []
        if incorrect_options:
            try:
                import json
                # Сначала пробуем JSON формат
                options_data = json.loads(incorrect_options)
                if isinstance(options_data, list):
                    options = options_data
                elif isinstance(options_data, dict):
                    options = [options_data.get('A', ''), options_data.get('B', ''), 
                              options_data.get('C', ''), options_data.get('D', '')]
            except:
                # Если JSON не работает, пробуем простой текст с переносами строк
                try:
                    # Разбиваем по переносам строк и убираем пустые строки
                    text_options = [opt.strip() for opt in incorrect_options.split('\n') if opt.strip()]
                    options = text_options
                except:
                    options = []
        
        # Добавляем правильный ответ к вариантам для полного отображения
        all_options = []
        if correct_answer:
            all_options.append(correct_answer.strip())
        if options:
            for opt in options:
                if opt.strip() and opt.strip() not in [correct_answer.strip() if correct_answer else ""]:
                    all_options.append(opt.strip())
        
        text = f"📋 <b>Изменение вариантов ответов ID {question_id}</b>\n\n"
        if all_options:  # Проверяем что есть хотя бы один вариант
            text += "<b>Текущие варианты:</b>\n"
            labels = ['A', 'B', 'C', 'D']
            for i, option in enumerate(all_options[:4]):
                if option:
                    # Проверяем, является ли этот вариант правильным ответом
                    if option.strip() == correct_answer.strip() if correct_answer else False:
                        text += f"✅ {labels[i]}) {option} <i>(правильный)</i>\n"
                    else:
                        text += f"❌ {labels[i]}) {option}\n"
        else:
            text += "<b>Текущие варианты:</b> Отсутствуют\n"
        
        text += "\nВведите новые варианты ответов в формате:\n"
        text += "A: вариант A\nB: вариант B\nC: вариант C\nD: вариант D"
        
        context.user_data['admin_action'] = 'edit_question_options'
        context.user_data['editing_question_id'] = question_id
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"edit_question_select_{question_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def edit_question_explanation_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения объяснения."""
        query = update.callback_query
        question_id = int(query.data.split('_')[-1])
        await self.safe_answer_callback(query)
        
        # Получаем текущее объяснение
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT explanation FROM questions WHERE id = ?', (question_id,))
                current_explanation = cursor.fetchone()[0] or "Отсутствует"
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка получения объяснения: {e}")
            return
        
        text = f"💡 <b>Изменение объяснения ID {question_id}</b>\n\n"
        text += f"<b>Текущее объяснение:</b>\n{current_explanation[:500]}{'...' if len(current_explanation) > 500 else ''}\n\n"
        text += "Введите новое объяснение:"
        
        context.user_data['admin_action'] = 'edit_question_explanation'
        context.user_data['editing_question_id'] = question_id
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"edit_question_select_{question_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def handle_edit_question_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_text: str) -> None:
        """Обработка нового текста вопроса."""
        question_id = context.user_data.get('editing_question_id')
        
        if not question_id:
            await update.message.reply_text("❌ Ошибка: ID вопроса не найден.")
            context.user_data.pop('admin_action', None)
            return
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE questions SET question = ? WHERE id = ?', (new_text, question_id))
                conn.commit()
            
            # Автоматически обновляем объяснение
            await self._auto_update_explanation_after_change(question_id, "question")
            
            text = f"✅ <b>Текст вопроса обновлен</b>\n\n"
            text += f"<b>ID вопроса:</b> {question_id}\n"
            text += f"<b>Новый текст:</b> {new_text[:200]}{'...' if len(new_text) > 200 else ''}\n"
            text += f"<b>Объяснение:</b> Автоматически обновлено"
            
            keyboard = [
                [InlineKeyboardButton("✏️ Продолжить редактирование", callback_data=f"edit_question_select_{question_id}")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка обновления текста вопроса: {e}")
        
        context.user_data.pop('admin_action', None)
        context.user_data.pop('editing_question_id', None)
    
    async def handle_edit_question_correct_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_answer: str) -> None:
        """Обработка нового правильного ответа."""
        question_id = context.user_data.get('editing_question_id')
        
        if not question_id:
            await update.message.reply_text("❌ Ошибка: ID вопроса не найден.")
            context.user_data.pop('admin_action', None)
            return
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE questions SET answer = ? WHERE id = ?', (new_answer, question_id))
                conn.commit()
            
            # Автоматически обновляем объяснение
            await self._auto_update_explanation_after_change(question_id, "answer")
            
            text = f"✅ <b>Правильный ответ обновлен</b>\n\n"
            text += f"<b>ID вопроса:</b> {question_id}\n"
            text += f"<b>Новый ответ:</b> {new_answer}\n"
            text += f"<b>Объяснение:</b> Автоматически обновлено"
            
            keyboard = [
                [InlineKeyboardButton("✏️ Продолжить редактирование", callback_data=f"edit_question_select_{question_id}")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка обновления ответа: {e}")
        
        context.user_data.pop('admin_action', None)
        context.user_data.pop('editing_question_id', None)
    
    async def handle_edit_question_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, options_text: str) -> None:
        """Обработка новых вариантов ответов."""
        question_id = context.user_data.get('editing_question_id')
        
        if not question_id:
            await update.message.reply_text("❌ Ошибка: ID вопроса не найден.")
            context.user_data.pop('admin_action', None)
            return
        
        # Парсим варианты ответов
        try:
            import json
            lines = options_text.strip().split('\n')
            options = {}
            
            for line in lines:
                if ':' in line:
                    parts = line.split(':', 1)
                    label = parts[0].strip().upper()
                    value = parts[1].strip()
                    if label in ['A', 'B', 'C', 'D'] and value:
                        options[label] = value
            
            if not options:
                await update.message.reply_text("❌ Неверный формат. Используйте:\nA: вариант A\nB: вариант B\nи т.д.")
                return
            
            # Конвертируем в список для сохранения
            options_list = [options.get('A', ''), options.get('B', ''), options.get('C', ''), options.get('D', '')]
            options_json = json.dumps(options_list)
            
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE questions SET incorrect_options = ? WHERE id = ?', (options_json, question_id))
                conn.commit()
            
            # Автоматически обновляем объяснение
            await self._auto_update_explanation_after_change(question_id, "options")
            
            text = f"✅ <b>Варианты ответов обновлены</b>\n\n"
            text += f"<b>ID вопроса:</b> {question_id}\n"
            text += f"<b>Новые варианты:</b>\n"
            for label, value in options.items():
                text += f"{label}: {value}\n"
            text += f"\n<b>Объяснение:</b> Автоматически обновлено"
            
            keyboard = [
                [InlineKeyboardButton("✏️ Продолжить редактирование", callback_data=f"edit_question_select_{question_id}")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка обновления вариантов: {e}")
        
        context.user_data.pop('admin_action', None)
        context.user_data.pop('editing_question_id', None)
    
    async def handle_edit_question_explanation_manual(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_explanation: str) -> None:
        """Обработка нового объяснения (ручной ввод)."""
        question_id = context.user_data.get('editing_question_id')
        
        if not question_id:
            await update.message.reply_text("❌ Ошибка: ID вопроса не найден.")
            context.user_data.pop('admin_action', None)
            return
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE questions SET explanation = ? WHERE id = ?', (new_explanation, question_id))
                conn.commit()
            
            text = f"✅ <b>Объяснение обновлено</b>\n\n"
            text += f"<b>ID вопроса:</b> {question_id}\n"
            text += f"<b>Новое объяснение:</b> {new_explanation[:200]}{'...' if len(new_explanation) > 200 else ''}"
            
            keyboard = [
                [InlineKeyboardButton("✏️ Продолжить редактирование", callback_data=f"edit_question_select_{question_id}")],
                [InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка обновления объяснения: {e}")
        
        context.user_data.pop('admin_action', None)
        context.user_data.pop('editing_question_id', None)
    
    async def _auto_update_explanation_after_change(self, question_id: int, change_type: str) -> None:
        """Автоматически обновляет объяснение после изменения вопроса."""
        try:
            # Получаем данные вопроса
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT q.question, q.answer, q.incorrect_options, s.name as topic
                    FROM questions q
                    JOIN subtopics s ON q.topic_id = s.id
                    WHERE q.id = ?
                ''', (question_id,))
                result = cursor.fetchone()
            
            if not result:
                return
            
            question, answer, incorrect_options, topic = result
            
            # Создаем новое объяснение с помощью ИИ
            from src.services.ai_service import AIService
            ai_service = AIService()
            
            options_text = ""
            if incorrect_options:
                try:
                    import json
                    options_data = json.loads(incorrect_options)
                    if isinstance(options_data, list):
                        labels = ['A', 'B', 'C', 'D']
                        for i, option in enumerate(options_data[:4]):
                            if option:
                                options_text += f"{labels[i]}: {option}\n"
                except:
                    pass
            
            new_explanation = await ai_service.generate_explanation(
                question=question,
                correct_answer=answer,
                topic=topic,
                options=options_text
            )
            
            if new_explanation:
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('UPDATE questions SET explanation = ? WHERE id = ?', (new_explanation, question_id))
                    conn.commit()
                    
        except Exception as e:
            logging.error(f"Error auto-updating explanation: {e}")