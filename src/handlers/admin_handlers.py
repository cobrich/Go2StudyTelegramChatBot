from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from services.database import Database
from services.question_service import QuestionService
from services.pdf_processor import PDFProcessor, add_questions_to_db
import logging
import os
import tempfile
import asyncio
import sqlite3
from handlers.base_handler import BaseHandler
from services.topic_manager import TopicManager

class AdminHandlers(BaseHandler):
    def __init__(self, db: Database, question_service: QuestionService):
        super().__init__(db, question_service)
        self.pdf_processor = PDFProcessor()
        self.topic_manager = TopicManager()
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Главная админ-панель."""
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            if update.message:
                await update.message.reply_text("❌ У вас нет прав администратора.")
            else:
                await update.callback_query.answer("❌ У вас нет прав администратора.")
            return
        
        is_super = self.db.is_super_admin(user_id)
        
        keyboard = []
        
        # Основные функции для всех админов
        keyboard.extend([
            [InlineKeyboardButton("👥 Управление учениками", callback_data="admin_students")],
            [InlineKeyboardButton("📚 Управление темами", callback_data="admin_topics")],
            [InlineKeyboardButton("❓ Управление вопросами", callback_data="admin_questions")],
        ])
        
        # Функции только для суперадмина
        if is_super:
            keyboard.append([InlineKeyboardButton("👑 Управление админами", callback_data="admin_admins")])
        
        keyboard.append([InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        role = "Суперадминистратор" if is_super else "Администратор"
        text = f"🔧 **Админ-панель**\n\nВаша роль: {role}\n\nВыберите действие:"
        
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # === УПРАВЛЕНИЕ УЧЕНИКАМИ ===
    
    async def students_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления учениками."""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить ученика (по username)", callback_data="add_student")],
            [InlineKeyboardButton("🆔 Добавить ученика (по ID)", callback_data="add_student_by_id")],
            [InlineKeyboardButton("📋 Список учеников", callback_data="list_students")],
            [InlineKeyboardButton("🗑️ Удалить ученика", callback_data="remove_student")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👥 **Управление учениками**\n\nВыберите действие:", 
                                     reply_markup=reply_markup, parse_mode='Markdown')
    
    async def add_student_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления ученика."""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'add_student'
        await query.edit_message_text("➕ **Добавление ученика**\n\nВведите username ученика (без @):")
    
    async def add_student_by_id_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления ученика по ID."""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'add_student_by_id'
        await query.edit_message_text("🆔 **Добавление ученика по ID**\n\nВведите Telegram user_id ученика:")
    
    async def list_students(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех учеников."""
        query = update.callback_query
        await query.answer()
        
        students = self.db.get_all_allowed_users()
        
        if not students:
            text = "📋 **Список учеников**\n\nУченики не найдены."
        else:
            text = "📋 **Список учеников**\n\n"
            for i, student in enumerate(students, 1):
                status = "✅" if student['is_active'] else "❌"
                
                # Проверяем, есть ли username или user_id
                identifier = ""
                if student.get('username'):
                    identifier = f"@{student['username']}"
                elif student.get('user_id'):
                    identifier = f"ID: {student['user_id']}"
                else:
                    identifier = "Не указан"
                
                text += f"{i}. {status} {identifier}\n"
                text += f"   ФИО: {student['full_name']}\n"
                text += f"   Класс: {student['grade']}\n"
                text += f"   Добавлен: {student['added_at'][:10]}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # === УПРАВЛЕНИЕ ТЕМАМИ ===
    
    async def topics_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления темами."""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить тему", callback_data="add_topic")],
            [InlineKeyboardButton("📋 Список тем", callback_data="list_topics")],
            [InlineKeyboardButton("✏️ Редактировать тему", callback_data="edit_topic")],
            [InlineKeyboardButton("🗑️ Удалить тему", callback_data="remove_topic")],
            [InlineKeyboardButton("🔗 Объединить темы", callback_data="merge_topics")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📚 **Управление темами**\n\nВыберите действие:", 
                                     reply_markup=reply_markup, parse_mode='Markdown')
    
    async def add_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления темы."""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'add_topic'
        await query.edit_message_text("➕ **Добавление темы**\n\nВведите название новой темы:")
    
    async def list_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех тем."""
        query = update.callback_query
        await query.answer()
        
        topics = self.db.get_all_topics(active_only=False)
        topic_stats = self.topic_manager.get_topic_statistics()
        
        if not topics:
            text = "📋 **Список тем**\n\nТемы не найдены."
        else:
            text = "📋 **Список тем**\n\n"
            for i, topic in enumerate(topics, 1):
                status = "✅" if topic['is_active'] else "❌"
                question_count = topic_stats.get(topic['name'], {}).get('question_count', 0)
                text += f"{i}. {status} **{topic['name']}**\n"
                text += f"   ID: {topic['id']} | Вопросов: {question_count}\n"
                text += f"   Описание: {topic['description']}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить статистику", callback_data="refresh_topics")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # === УПРАВЛЕНИЕ ВОПРОСАМИ ===
    
    async def questions_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления вопросами."""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📄 Загрузить PDF", callback_data="upload_pdf")],
            [InlineKeyboardButton("📋 Статистика вопросов", callback_data="questions_stats")],
            [InlineKeyboardButton("🔍 Поиск вопросов", callback_data="search_questions")],
            [InlineKeyboardButton("🗑️ Удалить вопросы", callback_data="delete_questions")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❓ **Управление вопросами**\n\nВыберите действие:", 
                                     reply_markup=reply_markup, parse_mode='Markdown')
    
    async def upload_pdf_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало загрузки PDF файла."""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'upload_pdf'
        
        text = "📄 **Загрузка PDF файла**\n\n"
        text += "Отправьте PDF файл с вопросами в следующем формате:\n\n"
        text += "```\nТема: Пропорция(10)\n\n"
        text += "1) Вопрос\nA) Вариант A\nB) Вариант B ✅\nC) Вариант C\nD) Вариант D\n\n"
        text += "2) Следующий вопрос\n...\n```\n\n"
        text += "⚠️ Убедитесь, что правильные ответы помечены символом ✅"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_questions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def questions_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Статистика вопросов по темам."""
        query = update.callback_query
        await query.answer()
        
        # Получаем статистику вопросов из базы данных
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT topic, COUNT(*) as count, 
                           SUM(CASE WHEN source = 'pdf' THEN 1 ELSE 0 END) as pdf_count,
                           SUM(CASE WHEN source = 'ai' THEN 1 ELSE 0 END) as ai_count
                    FROM questions 
                    GROUP BY topic 
                    ORDER BY count DESC
                """)
                stats = cursor.fetchall()
                
                if not stats:
                    text = "📋 **Статистика вопросов**\n\nВопросы не найдены."
                else:
                    text = "📋 **Статистика вопросов**\n\n"
                    total_questions = 0
                    total_pdf = 0
                    total_ai = 0
                    
                    for topic, count, pdf_count, ai_count in stats:
                        text += f"📚 **{topic}**\n"
                        text += f"   Всего: {count}\n"
                        text += f"   📄 PDF: {pdf_count}\n"
                        text += f"   🤖 AI: {ai_count}\n\n"
                        
                        total_questions += count
                        total_pdf += pdf_count
                        total_ai += ai_count
                    
                    text += f"**📊 Общая статистика:**\n"
                    text += f"Всего вопросов: {total_questions}\n"
                    text += f"Из PDF: {total_pdf}\n"
                    text += f"Сгенерировано AI: {total_ai}"
            
        except Exception as e:
            text = f"❌ Ошибка при получении статистики: {e}"
            logging.error(f"Error getting questions stats: {e}")
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_questions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
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
            # Скачиваем файл
            file = await context.bot.get_file(update.message.document.file_id)
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                await file.download_to_drive(temp_file.name)
                temp_path = temp_file.name
            
            # Обрабатываем PDF
            await processing_msg.edit_text("⏳ Извлекаю вопросы из PDF...")
            
            # Запускаем обработку в отдельном потоке, чтобы не блокировать бот
            loop = asyncio.get_event_loop()
            questions = await loop.run_in_executor(None, self.pdf_processor.process_pdf_file, temp_path)
            
            if not questions:
                await processing_msg.edit_text("❌ Не удалось извлечь вопросы из PDF файла. Проверьте формат файла.")
                return
            
            await processing_msg.edit_text(f"⏳ Найдено {len(questions)} вопросов. Сохраняю в базу данных...")
            
            # Сохраняем вопросы в базу данных
            saved_count = 0
            skipped_count = 0
            topic_stats = {}
            
            for question in questions:
                question_text = question['question'].strip()
                topic = question.get('topic', 'Операции с дробями и остатками')
                
                # Обновляем статистику
                topic_stats[topic] = topic_stats.get(topic, 0) + 1
                
                # Проверяем уникальность
                exists = self.db.get_explanation_by_question_text(question_text)
                if exists:
                    skipped_count += 1
                    continue
                
                # Подготавливаем данные для базы
                correct_answer_index = ord(question['correct_answer']) - ord('A')
                correct_answer_text = question['options'][correct_answer_index]
                
                # Формируем неправильные варианты
                incorrect_options = []
                for i, option in enumerate(question['options']):
                    if i != correct_answer_index:
                        incorrect_options.append(option)
                
                db_question = {
                    'topic': topic,
                    'question': question_text,
                    'answer': correct_answer_text,
                    'explanation': f"Правильный ответ: {question['correct_answer']}) {correct_answer_text}",
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
            result_text = f"✅ **Обработка завершена!**\n\n"
            result_text += f"📄 Файл: {update.message.document.file_name}\n"
            result_text += f"📊 Найдено вопросов: {len(questions)}\n"
            result_text += f"💾 Сохранено новых: {saved_count}\n"
            result_text += f"⏭️ Пропущено (дубликаты): {skipped_count}\n\n"
            
            if topic_stats:
                result_text += "**📚 Статистика по темам:**\n"
                for topic, count in sorted(topic_stats.items()):
                    result_text += f"• {topic}: {count}\n"
            
            await processing_msg.edit_text(result_text, parse_mode='Markdown')
            
        except Exception as e:
            error_msg = f"❌ Ошибка при обработке PDF: {str(e)}"
            logging.error(f"PDF processing error: {e}")
            await processing_msg.edit_text(error_msg)
        
        finally:
            # Удаляем временный файл
            try:
                if 'temp_path' in locals():
                    os.unlink(temp_path)
            except:
                pass
            
            # Очищаем состояние
            context.user_data.pop('admin_action', None)
    
    # === УПРАВЛЕНИЕ АДМИНАМИ (только для суперадмина) ===
    
    async def admins_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления админами (только для суперадмина)."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if not self.db.is_super_admin(user_id):
            await query.edit_message_text("❌ Только суперадминистратор может управлять админами.")
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton("📋 Список админов", callback_data="list_admins")],
            [InlineKeyboardButton("🗑️ Удалить админа", callback_data="remove_admin")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👑 **Управление админами**\n\nВыберите действие:", 
                                     reply_markup=reply_markup, parse_mode='Markdown')
    
    async def add_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления админа."""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'add_admin'
        await query.edit_message_text("➕ **Добавление админа**\n\nВведите user_id нового админа:")
    
    async def list_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех админов."""
        query = update.callback_query
        await query.answer()
        
        admins = self.db.get_all_admins()
        
        if not admins:
            text = "📋 **Список админов**\n\nАдмины не найдены."
        else:
            text = "📋 **Список админов**\n\n"
            for i, admin in enumerate(admins, 1):
                role = "👑 Суперадмин" if admin['is_super_admin'] else "🔧 Админ"
                text += f"{i}. {role}\n"
                text += f"   ID: {admin['user_id']}\n"
                text += f"   Username: @{admin['username'] or 'не указан'}\n"
                text += f"   ФИО: {admin['full_name'] or 'не указано'}\n"
                text += f"   Добавлен: {admin['created_at'][:10]}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # === ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ===
    
    async def handle_admin_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка текстовых сообщений в админ-режиме."""
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            return
        
        action = context.user_data.get('admin_action')
        text = update.message.text.strip()
        
        if action == 'add_student':
            await self._handle_add_student(update, context, text)
        elif action == 'add_student_by_id':
            await self._handle_add_student_by_id(update, context, text)
        elif action == 'add_topic':
            await self._handle_add_topic(update, context, text)
        elif action == 'add_admin':
            await self._handle_add_admin(update, context, text)
        elif action == 'student_fullname':
            await self._handle_student_fullname(update, context, text)
        elif action == 'student_by_id_fullname':
            await self._handle_student_by_id_fullname(update, context, text)
        elif action == 'student_grade':
            await self._handle_student_grade(update, context, text)
        elif action == 'student_by_id_grade':
            await self._handle_student_by_id_grade(update, context, text)
        elif action == 'topic_description':
            await self._handle_topic_description(update, context, text)
    
    # === ОБРАБОТКА ДОКУМЕНТОВ ===
    
    async def handle_admin_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка документов в админ-режиме."""
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            return
        
        action = context.user_data.get('admin_action')
        
        if action == 'upload_pdf':
            await self.process_pdf_file(update, context)
        else:
            await update.message.reply_text("❌ Неожиданный документ. Пожалуйста, используйте админ-панель для загрузки файлов.")
    
    async def _handle_add_student(self, update: Update, context: ContextTypes.DEFAULT_TYPE, username: str) -> None:
        """Обработка добавления ученика - этап 1 (username)."""
        if username.startswith('@'):
            username = username[1:]
        
        context.user_data['new_student_username'] = username
        context.user_data['admin_action'] = 'student_fullname'
        
        await update.message.reply_text(f"Введите ФИО ученика @{username}:")
    
    async def _handle_add_student_by_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_text: str) -> None:
        """Обработка добавления ученика по ID - этап 1 (user_id)."""
        try:
            student_user_id = int(user_id_text)
        except ValueError:
            await update.message.reply_text("❌ Введите корректный user_id (число). Попробуйте еще раз:")
            return
        
        # Проверяем, что этот пользователь еще не добавлен
        if self.db.check_user_access(student_user_id):
            await update.message.reply_text(f"❌ Пользователь с ID {student_user_id} уже имеет доступ к боту.")
            context.user_data.pop('admin_action', None)
            return
        
        context.user_data['new_student_user_id'] = student_user_id
        context.user_data['admin_action'] = 'student_by_id_fullname'
        
        await update.message.reply_text(f"Введите ФИО ученика с ID {student_user_id}:")

    async def _handle_student_fullname(self, update: Update, context: ContextTypes.DEFAULT_TYPE, fullname: str) -> None:
        """Обработка добавления ученика - этап 2 (ФИО)."""
        context.user_data['new_student_fullname'] = fullname
        context.user_data['admin_action'] = 'student_grade'
        
        await update.message.reply_text("Введите класс ученика (число от 1 до 11):")
    
    async def _handle_student_by_id_fullname(self, update: Update, context: ContextTypes.DEFAULT_TYPE, fullname: str) -> None:
        """Обработка добавления ученика по ID - этап 2 (ФИО)."""
        context.user_data['new_student_fullname'] = fullname
        context.user_data['admin_action'] = 'student_by_id_grade'
        
        await update.message.reply_text("Введите класс ученика (число от 1 до 11):")

    async def _handle_student_grade(self, update: Update, context: ContextTypes.DEFAULT_TYPE, grade_text: str) -> None:
        """Обработка добавления ученика - этап 3 (класс)."""
        try:
            grade = int(grade_text)
            if grade < 1 or grade > 11:
                await update.message.reply_text("❌ Класс должен быть от 1 до 11. Попробуйте еще раз:")
                return
        except ValueError:
            await update.message.reply_text("❌ Введите корректный номер класса (число). Попробуйте еще раз:")
            return
        
        username = context.user_data.get('new_student_username')
        fullname = context.user_data.get('new_student_fullname')
        admin_id = update.effective_user.id
        
        success = self.db.add_allowed_user(username, fullname, grade, admin_id)
        
        if success:
            await update.message.reply_text(f"✅ Ученик @{username} успешно добавлен!\n\nФИО: {fullname}\nКласс: {grade}")
        else:
            await update.message.reply_text(f"❌ Ошибка при добавлении ученика. Возможно, @{username} уже существует.")
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_student_username', None)
        context.user_data.pop('new_student_fullname', None)
    
    async def _handle_student_by_id_grade(self, update: Update, context: ContextTypes.DEFAULT_TYPE, grade_text: str) -> None:
        """Обработка добавления ученика по ID - этап 3 (класс)."""
        try:
            grade = int(grade_text)
            if grade < 1 or grade > 11:
                await update.message.reply_text("❌ Класс должен быть от 1 до 11. Попробуйте еще раз:")
                return
        except ValueError:
            await update.message.reply_text("❌ Введите корректный номер класса (число). Попробуйте еще раз:")
            return
        
        student_user_id = context.user_data.get('new_student_user_id')
        fullname = context.user_data.get('new_student_fullname')
        admin_id = update.effective_user.id
        
        success = self.db.add_allowed_user_by_id(student_user_id, fullname, grade, admin_id)
        
        if success:
            await update.message.reply_text(f"✅ Ученик с ID {student_user_id} успешно добавлен!\n\nФИО: {fullname}\nКласс: {grade}")
        else:
            await update.message.reply_text(f"❌ Ошибка при добавлении ученика. Возможно, пользователь с ID {student_user_id} уже существует.")
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_student_user_id', None)
        context.user_data.pop('new_student_fullname', None)
    
    async def _handle_add_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE, topic_name: str) -> None:
        """Обработка добавления темы - этап 1 (название)."""
        context.user_data['new_topic_name'] = topic_name
        context.user_data['admin_action'] = 'topic_description'
        
        await update.message.reply_text(f"Введите описание для темы '{topic_name}' (или отправьте '-' для пропуска):")
    
    async def _handle_topic_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, description: str) -> None:
        """Обработка добавления темы - этап 2 (описание)."""
        topic_name = context.user_data.get('new_topic_name')
        admin_id = update.effective_user.id
        
        if description == '-':
            description = f"Тема: {topic_name}"
        
        success = self.db.add_topic(topic_name, description, admin_id)
        
        if success:
            await update.message.reply_text(f"✅ Тема '{topic_name}' успешно добавлена!")
        else:
            await update.message.reply_text(f"❌ Ошибка при добавлении темы. Возможно, тема '{topic_name}' уже существует.")
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_topic_name', None)
    
    async def _handle_add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_text: str) -> None:
        """Обработка добавления админа."""
        try:
            new_admin_id = int(user_id_text)
        except ValueError:
            await update.message.reply_text("❌ Введите корректный user_id (число). Попробуйте еще раз:")
            return
        
        admin_id = update.effective_user.id
        
        # Проверяем, что пользователь не пытается добавить себя
        if new_admin_id == admin_id:
            await update.message.reply_text("❌ Вы не можете добавить себя в качестве админа.")
            context.user_data.pop('admin_action', None)
            return
        
        success = self.db.add_admin(new_admin_id, "unknown", "Новый админ", False, admin_id)
        
        if success:
            await update.message.reply_text(f"✅ Пользователь {new_admin_id} успешно добавлен в качестве админа!")
        else:
            await update.message.reply_text(f"❌ Ошибка при добавлении админа. Возможно, пользователь {new_admin_id} уже является админом.")
        
        context.user_data.pop('admin_action', None)
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать общую статистику системы."""
        query = update.callback_query
        await query.answer()
        
        # Получаем статистику
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Статистика пользователей
            cursor.execute('SELECT COUNT(*) FROM allowed_users WHERE is_active = 1')
            active_students = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM allowed_users')
            total_students = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM admins')
            total_admins = cursor.fetchone()[0]
            
            # Статистика вопросов
            cursor.execute('SELECT COUNT(*) FROM questions')
            total_questions = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM questions WHERE source = "ai"')
            ai_questions = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM questions WHERE source = "db"')
            db_questions = cursor.fetchone()[0]
            
            # Статистика тестов
            cursor.execute('SELECT COUNT(*) FROM test_results')
            total_tests = cursor.fetchone()[0]
            
            cursor.execute('SELECT AVG(percentage) FROM test_results')
            avg_score = cursor.fetchone()[0] or 0
            
            # Статистика активности
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM test_results')
            users_with_tests = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM test_results 
                WHERE timestamp >= datetime('now', '-7 days')
            ''')
            tests_last_week = cursor.fetchone()[0]
        
        text = f"📊 **Статистика системы**\n\n"
        text += f"👥 **Пользователи:**\n"
        text += f"• Активные ученики: {active_students}\n"
        text += f"• Всего в whitelist: {total_students}\n"
        text += f"• Администраторы: {total_admins}\n\n"
        
        text += f"❓ **Вопросы:**\n"
        text += f"• Всего вопросов: {total_questions}\n"
        text += f"• Из базы данных: {db_questions}\n"
        text += f"• Сгенерированы ИИ: {ai_questions}\n\n"
        
        text += f"📝 **Тестирование:**\n"
        text += f"• Всего тестов: {total_tests}\n"
        text += f"• Пользователей с тестами: {users_with_tests}\n"
        text += f"• Средний балл: {avg_score:.1f}%\n"
        text += f"• Тестов за неделю: {tests_last_week}\n"
        
        keyboard = [
            [InlineKeyboardButton("📈 История пользователей", callback_data="admin_user_history")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_user_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать историю всех пользователей, включая удаленных из whitelist."""
        query = update.callback_query
        await query.answer()
        
        users_with_history = self.db.get_all_users_with_history()
        
        if not users_with_history:
            text = "📈 **История пользователей**\n\nПользователей с историей тестов не найдено."
        else:
            text = "📈 **История пользователей**\n\n"
            text += "*(включая удаленных из whitelist)*\n\n"
            
            for i, user in enumerate(users_with_history[:10], 1):  # Показываем первых 10
                username = user['username'] or f"ID_{user['user_id']}"
                full_name = user['full_name'] or "Не указано"
                
                # Проверяем, есть ли пользователь в whitelist
                is_whitelisted = self.db.is_user_allowed(user['username']) if user['username'] else False
                status = "✅ Активен" if is_whitelisted else "❌ Не в whitelist"
                
                # Безопасное форматирование avg_percentage
                avg_percentage = user.get('avg_percentage') or 0
                avg_percentage = float(avg_percentage) if avg_percentage is not None else 0.0
                
                text += f"{i}. **@{username}** ({status})\n"
                text += f"   ФИО: {full_name}\n"
                text += f"   Тестов: {user['total_tests']}, Средний балл: {avg_percentage:.1f}%\n"
                text += f"   Ошибок: {user['unique_errors']} уникальных\n"
                if user['last_activity']:
                    text += f"   Последняя активность: {user['last_activity'][:10]}\n"
                text += "\n"
            
            if len(users_with_history) > 10:
                text += f"... и еще {len(users_with_history) - 10} пользователей"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад к статистике", callback_data="admin_stats")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def merge_topics_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало объединения тем."""
        query = update.callback_query
        await query.answer()
        
        topics = self.db.get_all_topics(active_only=False)
        topic_stats = self.topic_manager.get_topic_statistics()
        
        if len(topics) < 2:
            await query.edit_message_text(
                "❌ Недостаточно тем для объединения. Нужно минимум 2 темы.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]])
            )
            return
        
        text = "🔗 **Объединение тем**\n\n"
        text += "Выберите исходную тему (из которой будут перенесены вопросы):\n\n"
        
        keyboard = []
        for topic in topics:
            question_count = topic_stats.get(topic['name'], {}).get('question_count', 0)
            status = "✅" if topic['is_active'] else "❌"
            keyboard.append([InlineKeyboardButton(
                f"{status} {topic['name']} ({question_count} вопросов)",
                callback_data=f"merge_source_{topic['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_topics")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def merge_topics_select_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор целевой темы для объединения."""
        query = update.callback_query
        source_topic_id = int(query.data.replace('merge_source_', ''))
        await query.answer()
        
        # Сохраняем ID исходной темы
        context.user_data['merge_source_id'] = source_topic_id
        
        # Получаем информацию об исходной теме
        topics = self.db.get_all_topics(active_only=False)
        source_topic = next((t for t in topics if t['id'] == source_topic_id), None)
        
        if not source_topic:
            await query.edit_message_text(
                "❌ Исходная тема не найдена.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]])
            )
            return
        
        topic_stats = self.topic_manager.get_topic_statistics()
        
        text = f"🔗 **Объединение тем**\n\n"
        text += f"Исходная тема: **{source_topic['name']}**\n"
        text += f"Вопросов: {topic_stats.get(source_topic['name'], {}).get('question_count', 0)}\n\n"
        text += "Выберите целевую тему (в которую будут перенесены вопросы):\n\n"
        
        keyboard = []
        for topic in topics:
            if topic['id'] == source_topic_id:
                continue  # Пропускаем исходную тему
            
            question_count = topic_stats.get(topic['name'], {}).get('question_count', 0)
            status = "✅" if topic['is_active'] else "❌"
            keyboard.append([InlineKeyboardButton(
                f"{status} {topic['name']} ({question_count} вопросов)",
                callback_data=f"merge_target_{topic['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_topics")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def merge_topics_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение объединения тем."""
        query = update.callback_query
        target_topic_id = int(query.data.replace('merge_target_', ''))
        source_topic_id = context.user_data.get('merge_source_id')
        await query.answer()
        
        if not source_topic_id:
            await query.edit_message_text(
                "❌ Ошибка: исходная тема не выбрана.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]])
            )
            return
        
        # Получаем информацию о темах
        topics = self.db.get_all_topics(active_only=False)
        source_topic = next((t for t in topics if t['id'] == source_topic_id), None)
        target_topic = next((t for t in topics if t['id'] == target_topic_id), None)
        
        if not source_topic or not target_topic:
            await query.edit_message_text(
                "❌ Одна из тем не найдена.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]])
            )
            return
        
        topic_stats = self.topic_manager.get_topic_statistics()
        source_count = topic_stats.get(source_topic['name'], {}).get('question_count', 0)
        target_count = topic_stats.get(target_topic['name'], {}).get('question_count', 0)
        
        text = f"🔗 **Подтверждение объединения**\n\n"
        text += f"**Исходная тема:** {source_topic['name']}\n"
        text += f"Вопросов: {source_count}\n\n"
        text += f"**Целевая тема:** {target_topic['name']}\n"
        text += f"Вопросов: {target_count}\n\n"
        text += f"**Результат:** {target_count + source_count} вопросов в теме '{target_topic['name']}'\n\n"
        text += "⚠️ **Внимание:** Исходная тема будет деактивирована!\n\n"
        text += "Подтвердите объединение:"
        
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data=f"merge_execute_{source_topic_id}_{target_topic_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="admin_topics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def merge_topics_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение объединения тем."""
        query = update.callback_query
        await query.answer()
        
        # Парсим данные
        parts = query.data.replace('merge_execute_', '').split('_')
        source_topic_id = int(parts[0])
        target_topic_id = int(parts[1])
        
        # Получаем информацию о темах
        topics = self.db.get_all_topics(active_only=False)
        source_topic = next((t for t in topics if t['id'] == source_topic_id), None)
        target_topic = next((t for t in topics if t['id'] == target_topic_id), None)
        
        if not source_topic or not target_topic:
            await query.edit_message_text(
                "❌ Ошибка: темы не найдены.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]])
            )
            return
        
        # Выполняем объединение
        success = self.topic_manager.merge_topics(source_topic['name'], target_topic['name'])
        
        if success:
            text = f"✅ **Объединение завершено!**\n\n"
            text += f"Все вопросы из темы '{source_topic['name']}' перенесены в '{target_topic['name']}'.\n"
            text += f"Исходная тема деактивирована."
        else:
            text = f"❌ **Ошибка при объединении тем.**\n\n"
            text += "Попробуйте еще раз или обратитесь к разработчику."
        
        keyboard = [[InlineKeyboardButton("🔙 К управлению темами", callback_data="admin_topics")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Очищаем данные
        context.user_data.pop('merge_source_id', None) 