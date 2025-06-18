"""
Модуль для управления вопросами в админ-панели.
Включает загрузку PDF, добавление, редактирование, удаление вопросов.
"""

from .base import AdminBaseHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sqlite3
import logging

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
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Общая статистика
                cursor.execute('SELECT COUNT(*) FROM questions')
                total_questions = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(DISTINCT s.name) 
                    FROM questions q 
                    JOIN subtopics s ON q.topic_id = s.id
                ''')
                unique_topics = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM questions WHERE explanation IS NOT NULL AND explanation != ""')
                questions_with_explanations = cursor.fetchone()[0]
                
                # Статистика по темам
                cursor.execute('''
                    SELECT s.name as topic, COUNT(*) as count 
                    FROM questions q
                    JOIN subtopics s ON q.topic_id = s.id
                    GROUP BY s.name 
                    ORDER BY count DESC 
                    LIMIT 10
                ''')
                top_topics = cursor.fetchall()
                
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
            from services.pdf_processor import PDFProcessor
            from services.ai_service import AIService
            
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
            
            from services.ai_service import AIService
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
            from services.ai_service import AIService
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
                        if len(results) >= 10:  # Ограничиваем до 10 результатов
                            break
                            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка поиска: {e}")
            context.user_data.pop('admin_action', None)
            return
        
        if not results:
            await update.message.reply_text(f"🔍 По запросу '<i>{search_text}</i>' вопросы не найдены.\n\nПопробуйте другой поисковый запрос:", parse_mode='HTML')
            return
        
        text = f"🔍 <b>Найдено {len(results)} вопросов</b>\n\nВведите ID вопроса для редактирования:\n\n"
        
        for i, (q_id, topic, question, answer, explanation) in enumerate(results, 1):
            short_question = question[:80] + "..." if len(question) > 80 else question
            text += f"<b>ID {q_id}</b> | {topic}\n{short_question}\n\n"
        
        context.user_data['admin_action'] = 'edit_question_id'
        await update.message.reply_text(text, parse_mode='HTML')

    async def handle_edit_question_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question_id_text: str) -> None:
        """Обработка ID вопроса для редактирования."""
        try:
            question_id = int(question_id_text.strip())
        except ValueError:
            await update.message.reply_text("❌ Введите корректный ID вопроса (число):")
            return
        
        # Получаем информацию о вопросе
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.name as topic, q.question, q.answer, q.explanation 
                    FROM questions q 
                    JOIN subtopics s ON q.topic_id = s.id 
                    WHERE q.id = ?
                ''', (question_id,))
                result = cursor.fetchone()
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения вопроса: {e}")
            context.user_data.pop('admin_action', None)
            return
        
        if not result:
            await update.message.reply_text(f"❌ Вопрос с ID {question_id} не найден. Попробуйте другой ID:")
            return
        
        topic, question, answer, explanation = result
        
        text = f"✏️ <b>Редактирование вопроса ID {question_id}</b>\n\n"
        text += f"<b>Тема:</b> {topic}\n"
        text += f"<b>Вопрос:</b> {question}\n"
        text += f"<b>Ответ:</b> {answer}\n"
        text += f"<b>Текущее объяснение:</b> {explanation or 'Отсутствует'}\n\n"
        text += "Выберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("🤖 Сгенерировать ИИ объяснение", callback_data=f"generate_ai_explanation_{question_id}")],
            [InlineKeyboardButton("✏️ Ввести объяснение вручную", callback_data=f"manual_explanation_{question_id}")],
            [InlineKeyboardButton("🔙 Назад к поиску", callback_data="edit_question")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.user_data.pop('admin_action', None)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

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