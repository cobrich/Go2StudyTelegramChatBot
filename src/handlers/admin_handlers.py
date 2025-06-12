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
from typing import Dict, List
from datetime import datetime

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
        
        # Удаляем предыдущие сообщения для чистого интерфейса
        if update.message:
            try:
                # Удаляем сообщение с командой /admin
                await update.message.delete()
            except Exception:
                pass  # Игнорируем ошибки удаления (например, если сообщение уже удалено)
            
            # Пытаемся удалить предыдущие сообщения (обычно там выбор тем)
            chat_id = update.message.chat_id
            message_id = update.message.message_id
            
            # Пытаемся удалить несколько предыдущих сообщений (обычно там выбор тем)
            for i in range(1, 6):  # Проверяем 5 предыдущих сообщений
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=message_id - i)
                except Exception:
                    # Если не удалось удалить, пытаемся убрать клавиатуру
                    try:
                        await context.bot.edit_message_reply_markup(
                            chat_id=chat_id, 
                            message_id=message_id - i, 
                            reply_markup=None
                        )
                    except Exception:
                        pass  # Игнорируем ошибки
        
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
        keyboard.append([InlineKeyboardButton("🔙 Назад к выбору тем", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        role = "Суперадминистратор" if is_super else "Администратор"
        text = f"🔧 <b>Админ-панель</b>\n\nВаша роль: {role}\n\nВыберите действие:"
        
        if update.message:
            # Отправляем новое сообщение (старые уже удалены/очищены)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            query = update.callback_query
            await self.safe_answer_callback(query)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    # === УПРАВЛЕНИЕ УЧЕНИКАМИ ===
    
    async def students_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления учениками."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Очищаем состояние при возврате в меню
        context.user_data.pop('admin_action', None)
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить ученика (по username)", callback_data="add_student")],
            [InlineKeyboardButton("🆔 Добавить ученика (по ID)", callback_data="add_student_by_id")],
            [InlineKeyboardButton("📋 Список учеников", callback_data="list_students")],
            [InlineKeyboardButton("🗑️ Удалить ученика", callback_data="remove_student")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👥 <b>Управление учениками</b>\n\nВыберите действие:", 
                                     reply_markup=reply_markup, parse_mode='HTML')
    
    async def add_student_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        context.user_data['admin_action'] = 'add_student'
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_students")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("➕ <b>Добавление ученика</b>\n\nВведите username ученика (без @):", 
                                     reply_markup=reply_markup, parse_mode='HTML')
    
    async def add_student_by_id_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления ученика по ID."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        context.user_data['admin_action'] = 'add_student_by_id'
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_students")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("🆔 <b>Добавление ученика по ID</b>\n\nВведите Telegram user_id ученика:", 
                                     reply_markup=reply_markup, parse_mode='HTML')
    
    async def list_students(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех учеников с краткой статистикой."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        students = self.db.get_all_students_summary()
        
        if not students:
            text = "📋 <b>Список учеников</b>\n\nУченики не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
        else:
            text = "📋 <b>Список учеников</b>\n\n"
            keyboard = []
            
            for i, student in enumerate(students[:15], 1):  # Показываем первых 15
                status = "✅" if student['is_active'] else "❌"
                
                # Определяем идентификатор
                if student.get('username'):
                    identifier = f"@{student['username']}"
                elif student.get('user_id'):
                    identifier = f"ID: {student['user_id']}"
                else:
                    identifier = "Неизвестен"
                
                # Краткая статистика
                stats = f"Тестов: {student['total_tests']}, Балл: {student['avg_score']}%"
                if student['unique_errors'] > 0:
                    stats += f", Ошибок: {student['unique_errors']}"
                
                text += f"{i}. {status} <b>{identifier}</b>\n"
                text += f"   {student['full_name']} ({student['grade']} класс)\n"
                text += f"   {stats}\n"
                text += f"   Статус: {student['status']}\n\n"
                
                # Кнопка для детального просмотра
                if student.get('user_id'):
                    keyboard.append([InlineKeyboardButton(
                        f"📊 {identifier} - детали", 
                        callback_data=f"student_details_{student['user_id']}"
                    )])
            
            if len(students) > 15:
                text += f"... и еще {len(students) - 15} учеников\n\n"
            
            # Кнопки управления
            keyboard.extend([
                [InlineKeyboardButton("📈 Статистика по классам", callback_data="class_statistics")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def show_student_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать детальную статистику ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Извлекаем user_id из callback_data
        user_id = int(query.data.split('_')[-1])
        
        stats = self.db.get_student_detailed_statistics(user_id)
        
        if not stats:
            text = "❌ Ученик не найден или нет данных."
            keyboard = [[InlineKeyboardButton("🔙 Назад к списку", callback_data="list_students")]]
        else:
            user_info = stats['user_info']
            test_stats = stats['test_statistics']
            
            text = f"📊 <b>Детальная статистика ученика</b>\n\n"
            text += f"👤 <b>Информация:</b>\n"
            text += f"• ID: {user_info['user_id']}\n"
            text += f"• Username: @{user_info['username'] or 'не указан'}\n"
            text += f"• ФИО: {user_info['full_name'] or 'не указано'}\n"
            text += f"• Класс: {user_info['grade'] or 'не указан'}\n"
            text += f"• Язык: {user_info['language']}\n"
            
            if user_info['last_activity']:
                text += f"• Последняя активность: {user_info['last_activity'][:16]}\n"
            if user_info['added_to_whitelist']:
                text += f"• Добавлен в whitelist: {user_info['added_to_whitelist'][:10]}\n"
            
            text += f"\n📝 <b>Статистика тестов:</b>\n"
            text += f"• Всего тестов: {test_stats['total_tests']}\n"
            text += f"• Средний балл: {test_stats['avg_score']}%\n"
            
            if test_stats['total_tests'] > 0:
                text += f"• Лучший результат: {test_stats['max_score']}%\n"
                text += f"• Худший результат: {test_stats['min_score']}%\n"
                text += f"• Первый тест: {test_stats['first_test'][:10] if test_stats['first_test'] else 'н/д'}\n"
                text += f"• Последний тест: {test_stats['last_test'][:10] if test_stats['last_test'] else 'н/д'}\n"
            
            # Показываем топ-5 тем по активности
            if stats['topic_performance']:
                text += f"\n🎯 <b>Активность по темам (топ-5):</b>\n"
                for i, topic in enumerate(stats['topic_performance'][:5], 1):
                    text += f"{i}. {topic['topic']}: {topic['tests_count']} тестов, {topic['avg_score']}%\n"
            
            # Показываем проблемные темы
            if stats['error_analysis']:
                text += f"\n❌ <b>Проблемные темы:</b>\n"
                for i, error in enumerate(stats['error_analysis'][:3], 1):
                    text += f"{i}. {error['topic']}: {error['unique_errors']} ошибок ({error['total_errors']} всего)\n"
            
            keyboard = [
                [InlineKeyboardButton("📈 Подробная статистика", callback_data=f"student_full_stats_{user_id}")],
                [InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_student_{user_id}")],
                [InlineKeyboardButton("🔙 Назад к списку", callback_data="list_students")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def show_student_full_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать полную статистику ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        stats = self.db.get_student_detailed_statistics(user_id)
        
        if not stats:
            text = "❌ Данные не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"student_details_{user_id}")]]
        else:
            user_info = stats['user_info']
            text = f"📈 <b>Полная статистика: {user_info['full_name'] or 'ID_' + str(user_id)}</b>\n\n"
            
            # Прогресс по дням (последние 10 дней)
            if stats['daily_progress']:
                text += f"📅 <b>Активность (последние дни):</b>\n"
                for day in stats['daily_progress'][:10]:
                    text += f"• {day['date']}: {day['tests_count']} тестов, {day['avg_score']}%\n"
                text += "\n"
            
            # Все темы с результатами
            if stats['topic_performance']:
                text += f"🎯 <b>Результаты по всем темам:</b>\n"
                for topic in stats['topic_performance']:
                    text += f"• {topic['topic']}: {topic['tests_count']} тестов, {topic['avg_score']}%\n"
                text += "\n"
            
            # Последние ошибки
            if stats['recent_errors']:
                text += f"❌ <b>Последние ошибки:</b>\n"
                for i, error in enumerate(stats['recent_errors'][:5], 1):
                    text += f"{i}. [{error['topic']}] {error['question']}\n"
                    text += f"   Ошибок: {error['error_count']}, {error['timestamp'][:10]}\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад к краткой статистике", callback_data=f"student_details_{user_id}")]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def show_class_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать статистику по классам."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        class_stats = self.db.get_class_statistics()
        
        if not class_stats['class_stats']:
            text = "📈 <b>Статистика по классам</b>\n\nДанных нет."
        else:
            text = "📈 <b>Статистика по классам</b>\n\n"
            
            total_students = 0
            total_active = 0
            total_tests = 0
            
            for cls in class_stats['class_stats']:
                if cls['grade']:  # Пропускаем записи без класса
                    text += f"🎓 <b>{cls['grade']} класс:</b>\n"
                    text += f"• Учеников: {cls['students_count']}\n"
                    text += f"• Активных: {cls['active_students']} ({cls['activity_rate']}%)\n"
                    text += f"• Тестов: {cls['total_tests']}\n"
                    text += f"• Средний балл: {cls['avg_score']}%\n\n"
                    
                    total_students += cls['students_count']
                    total_active += cls['active_students']
                    total_tests += cls['total_tests']
            
            text += f"📊 <b>Общая статистика:</b>\n"
            text += f"• Всего учеников: {total_students}\n"
            text += f"• Активных: {total_active}\n"
            text += f"• Всего тестов: {total_tests}\n"
            overall_activity = round((total_active / total_students * 100) if total_students > 0 else 0, 1)
            text += f"• Общая активность: {overall_activity}%\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад к списку учеников", callback_data="list_students")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    # === УПРАВЛЕНИЕ ТЕМАМИ ===
    
    async def topics_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления темами."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Очищаем состояние при возврате в меню
        context.user_data.pop('admin_action', None)
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить тему", callback_data="add_topic")],
            [InlineKeyboardButton("📋 Список тем", callback_data="list_topics")],
            [InlineKeyboardButton("✏️ Редактировать тему", callback_data="edit_topic")],
            [InlineKeyboardButton("🗑️ Удалить тему", callback_data="remove_topic")],
            [InlineKeyboardButton("🔗 Объединить темы", callback_data="merge_topics")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📚 <b>Управление темами</b>\n\nВыберите действие:", 
                                     reply_markup=reply_markup, parse_mode='HTML')
    
    async def add_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Очищаем состояние при возврате в меню
        context.user_data.pop('admin_action', None)
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить новую тему", callback_data="add_custom_topic")],
            [InlineKeyboardButton("📋 Добавить из базовых тем", callback_data="add_base_topics")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("➕ <b>Добавление темы</b>\n\nВыберите способ добавления:", 
                                     reply_markup=reply_markup, parse_mode='HTML')
    
    async def add_custom_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления пользовательской темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        context.user_data['admin_action'] = 'add_topic'
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_topics")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("➕ <b>Добавление новой темы</b>\n\nВведите название новой темы:", 
                                     reply_markup=reply_markup, parse_mode='HTML')
    
    async def add_base_topics_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать базовые темы для добавления."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем существующие темы из базы
        existing_topics = [topic['name'] for topic in self.db.get_all_topics(active_only=False)]
        
        # Получаем базовые темы из базы данных вместо constants.py
        base_structure = self.db.get_base_topic_structure()
        
        # Если база данных пуста, инициализируем из constants.py
        if not base_structure:
            from config.constants import TOPIC_HIERARCHY
            for main_topic, subtopics in TOPIC_HIERARCHY.items():
                self.db.add_base_topic_section(main_topic, subtopics)
            base_structure = self.db.get_base_topic_structure()
        
        missing_topics = []
        existing_base_topics = []
        
        for main_topic, subtopics in base_structure.items():
            for subtopic in subtopics:
                if subtopic in existing_topics:
                    existing_base_topics.append((main_topic, subtopic))
                else:
                    missing_topics.append((main_topic, subtopic))
        
        if not missing_topics:
            text = "📋 <b>Базовые темы</b>\n\n"
            text += "✅ Все базовые темы уже добавлены в систему!\n\n"
            text += f"Всего базовых тем: {len(existing_base_topics)}\n"
            text += "Используйте 'Добавить новую тему' для создания собственных тем.\n\n"
            text += "<b>🔧 Управление базовой структурой тем:</b>\n"
            text += "Теперь базовые темы управляются через базу данных."
            
            keyboard = [
                [InlineKeyboardButton("🏗️ Управление базовой структурой", callback_data="manage_base_structure")],
                [InlineKeyboardButton("🔙 Назад", callback_data="add_topic")]
            ]
        else:
            text = "📋 <b>Базовые темы</b>\n\n"
            text += f"✅ Добавлено: {len(existing_base_topics)}\n"
            text += f"⏳ Не добавлено: {len(missing_topics)}\n\n"
            text += "Выберите недостающие темы для добавления:\n\n"
            
            keyboard = []
            
            # Группируем по основным разделам
            current_main = None
            for main_topic, subtopic in missing_topics[:15]:  # Ограничиваем до 15 для удобства
                if main_topic != current_main:
                    text += f"\n<b>{main_topic}</b>\n"
                    current_main = main_topic
                
                # Убираем эмодзи из основной темы для краткости
                clean_main = main_topic.split(' ', 1)[-1] if ' ' in main_topic else main_topic
                keyboard.append([InlineKeyboardButton(
                    f"➕ {subtopic}",
                    callback_data=f"add_base_topic_{subtopic[:30]}"  # Ограничиваем длину
                )])
            
            if len(missing_topics) > 15:
                text += f"\n... и еще {len(missing_topics) - 15} тем"
            
            keyboard.append([InlineKeyboardButton("✅ Добавить ВСЕ недостающие", callback_data="add_all_missing_topics")])
            keyboard.append([InlineKeyboardButton("🏗️ Управление базовой структурой", callback_data="manage_base_structure")])
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="add_topic")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def add_base_topic_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Добавить выбранную базовую тему."""
        query = update.callback_query
        topic_name = query.data.replace('add_base_topic_', '')
        await self.safe_answer_callback(query)
        
        admin_id = update.effective_user.id
        
        # Находим полное название и описание темы в базовой структуре БД
        base_structure = self.db.get_base_topic_structure()
        
        full_topic_name = None
        main_topic_name = None
        
        for main_topic, subtopics in base_structure.items():
            for subtopic in subtopics:
                if subtopic.startswith(topic_name) or topic_name in subtopic:
                    full_topic_name = subtopic
                    main_topic_name = main_topic
                    break
            if full_topic_name:
                break
        
        if not full_topic_name:
            await query.edit_message_text("❌ Тема не найдена в базовых темах.")
            return
        
        # Добавляем тему
        description = f"Подтема раздела '{main_topic_name}': {full_topic_name}"
        success = self.db.add_topic(full_topic_name, description, admin_id)
        
        if success:
            text = f"✅ <b>Базовая тема добавлена!</b>\n\n"
            text += f"<b>Тема:</b> {full_topic_name}\n"
            text += f"<b>Раздел:</b> {main_topic_name}\n"
            text += f"<b>Описание:</b> {description}"
        else:
            text = f"❌ <b>Ошибка</b>\n\n"
            text += f"Тема '{full_topic_name}' уже существует или произошла ошибка."
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить еще", callback_data="add_base_topics")],
            [InlineKeyboardButton("📋 К управлению темами", callback_data="admin_topics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def add_all_missing_topics_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Добавить все недостающие базовые темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        admin_id = update.effective_user.id
        
        # Получаем существующие темы
        existing_topics = [topic['name'] for topic in self.db.get_all_topics(active_only=False)]
        
        # Получаем базовые темы из базы данных
        base_structure = self.db.get_base_topic_structure()
        
        added_count = 0
        failed_count = 0
        
        for main_topic, subtopics in base_structure.items():
            for subtopic in subtopics:
                if subtopic not in existing_topics:
                    description = f"Подтема раздела '{main_topic}': {subtopic}"
                    success = self.db.add_topic(subtopic, description, admin_id)
                    if success:
                        added_count += 1
                    else:
                        failed_count += 1
        
        if added_count > 0:
            text = f"✅ <b>Базовые темы добавлены!</b>\n\n"
            text += f"Добавлено: {added_count} тем\n"
            if failed_count > 0:
                text += f"Ошибок: {failed_count} тем\n"
            text += "\nВсе базовые темы из структуры НИШ теперь доступны в системе!"
        else:
            text = f"ℹ️ <b>Нет новых тем для добавления</b>\n\n"
            text += "Все базовые темы уже присутствуют в системе."
        
        keyboard = [[InlineKeyboardButton("📋 К управлению темами", callback_data="admin_topics")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def list_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех тем с пагинацией."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем номер страницы из callback_data или используем 0 по умолчанию
        page = 0
        if query.data.startswith('list_topics_page_'):
            try:
                page = int(query.data.replace('list_topics_page_', ''))
            except ValueError:
                page = 0
        
        topics = self.db.get_all_topics(active_only=False)
        topic_stats = self.topic_manager.get_topic_statistics()
        
        if not topics:
            text = "📋 <b>Список тем</b>\n\nТемы не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            except Exception as e:
                # Если сообщение не изменилось, просто игнорируем ошибку
                if "Message is not modified" in str(e):
                    pass  # Сообщение уже актуальное
                else:
                    # Для других ошибок пытаемся отправить новое сообщение
                    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        # Настройки пагинации
        topics_per_page = 10
        total_topics = len(topics)
        total_pages = (total_topics + topics_per_page - 1) // topics_per_page
        
        # Проверяем корректность номера страницы
        if page < 0:
            page = 0
        elif page >= total_pages:
            page = total_pages - 1
        
        # Вычисляем индексы для текущей страницы
        start_idx = page * topics_per_page
        end_idx = min(start_idx + topics_per_page, total_topics)
        current_topics = topics[start_idx:end_idx]
        
        # Общая статистика
        active_count = sum(1 for t in topics if t['is_active'])
        inactive_count = total_topics - active_count
        total_questions = sum(topic_stats.get(t['name'], {}).get('question_count', 0) for t in topics)
        
        # Формируем текст
        text = f"📋 <b>Список тем</b> (страница {page + 1} из {total_pages})\n\n"
        text += f"📊 <b>Общая статистика:</b>\n"
        text += f"• Всего тем: {total_topics}\n"
        text += f"• Активных: {active_count} ✅\n"
        text += f"• Неактивных: {inactive_count} ❌\n"
        text += f"• Всего вопросов: {total_questions}\n\n"
        
        text += f"<b>Темы {start_idx + 1}-{end_idx}:</b>\n\n"
        
        for i, topic in enumerate(current_topics, start_idx + 1):
            status = "✅" if topic['is_active'] else "❌"
            question_count = topic_stats.get(topic['name'], {}).get('question_count', 0)
            text += f"{i}. {status} <b>{topic['name']}</b>\n"
            text += f"   ID: {topic['id']} | Вопросов: {question_count}\n"
            # Ограничиваем длину описания
            description = topic['description']
            if len(description) > 60:
                description = description[:60] + "..."
            text += f"   Описание: {description}\n\n"
        
        # Создаем клавиатуру с навигацией
        keyboard = []
        
        # Кнопки навигации по страницам
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущая", callback_data=f"list_topics_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Следующая ➡️", callback_data=f"list_topics_page_{page + 1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # Кнопка быстрого перехода к первой/последней странице (если есть много страниц)
        if total_pages > 3:
            quick_nav = []
            if page > 1:
                quick_nav.append(InlineKeyboardButton("⏮️ Первая", callback_data="list_topics_page_0"))
            if page < total_pages - 2:
                quick_nav.append(InlineKeyboardButton("Последняя ⏭️", callback_data=f"list_topics_page_{total_pages - 1}"))
            if quick_nav:
                keyboard.append(quick_nav)
        
        # Функциональные кнопки
        keyboard.append([
            InlineKeyboardButton("🔄 Обновить статистику", callback_data="refresh_topics_stats"),
            InlineKeyboardButton("📊 Подробная статистика", callback_data="detailed_topics_stats")
        ])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e:
            # Если сообщение не изменилось, просто игнорируем ошибку
            if "Message is not modified" in str(e):
                pass  # Сообщение уже актуальное
            else:
                # Для других ошибок пытаемся отправить новое сообщение
                await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def edit_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало редактирования темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        topics = self.db.get_all_topics(active_only=False)
        
        if not topics:
            text = "✏️ <b>Редактирование темы</b>\n\nТемы не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]]
        else:
            text = "✏️ <b>Редактирование темы</b>\n\nВыберите тему для редактирования:\n\n"
            keyboard = []
            
            for topic in topics:
                status = "✅" if topic['is_active'] else "❌"
                display_text = f"{status} {topic['name']}"
                keyboard.append([InlineKeyboardButton(
                    display_text,
                    callback_data=f"edit_topic_select_{topic['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_topics")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def edit_topic_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор действия для редактирования темы."""
        query = update.callback_query
        topic_id = int(query.data.replace('edit_topic_select_', ''))
        await self.safe_answer_callback(query)
        
        # Получаем информацию о теме
        topics = self.db.get_all_topics(active_only=False)
        topic = next((t for t in topics if t['id'] == topic_id), None)
        
        if not topic:
            await query.edit_message_text(
                "❌ Тема не найдена.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]])
            )
            return
        
        # Сохраняем ID темы для редактирования
        context.user_data['edit_topic_id'] = topic_id
        
        status = "Активна ✅" if topic['is_active'] else "Неактивна ❌"
        text = f"✏️ <b>Редактирование темы</b>\n\n"
        text += f"<b>Название:</b> {topic['name']}\n"
        text += f"<b>Описание:</b> {topic['description']}\n"
        text += f"<b>Статус:</b> {status}\n\n"
        text += "Что хотите изменить?"
        
        keyboard = [
            [InlineKeyboardButton("📝 Изменить название", callback_data=f"edit_topic_name_{topic_id}")],
            [InlineKeyboardButton("📄 Изменить описание", callback_data=f"edit_topic_desc_{topic_id}")],
        ]
        
        if topic['is_active']:
            keyboard.append([InlineKeyboardButton("❌ Деактивировать", callback_data=f"edit_topic_deactivate_{topic_id}")])
        else:
            keyboard.append([InlineKeyboardButton("✅ Активировать", callback_data=f"edit_topic_activate_{topic_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="edit_topic")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def edit_topic_name_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения названия темы."""
        query = update.callback_query
        topic_id = int(query.data.replace('edit_topic_name_', ''))
        await self.safe_answer_callback(query)
        
        context.user_data['admin_action'] = 'edit_topic_name'
        context.user_data['edit_topic_id'] = topic_id
        
        # Получаем текущее название
        topics = self.db.get_all_topics(active_only=False)
        topic = next((t for t in topics if t['id'] == topic_id), None)
        
        if not topic:
            await query.edit_message_text("❌ Тема не найдена.")
            return
        
        text = f"📝 <b>Изменение названия темы</b>\n\n"
        text += f"Текущее название: <b>{topic['name']}</b>\n\n"
        text += "Введите новое название темы:"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_topic_select_{topic_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def edit_topic_desc_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения описания темы."""
        query = update.callback_query
        topic_id = int(query.data.replace('edit_topic_desc_', ''))
        await self.safe_answer_callback(query)
        
        context.user_data['admin_action'] = 'edit_topic_description'
        context.user_data['edit_topic_id'] = topic_id
        
        # Получаем текущее описание
        topics = self.db.get_all_topics(active_only=False)
        topic = next((t for t in topics if t['id'] == topic_id), None)
        
        if not topic:
            await query.edit_message_text("❌ Тема не найдена.")
            return
        
        text = f"📄 <b>Изменение описания темы</b>\n\n"
        text += f"Тема: <b>{topic['name']}</b>\n"
        text += f"Текущее описание: <i>{topic['description']}</i>\n\n"
        text += "Введите новое описание темы:"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_topic_select_{topic_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def edit_topic_toggle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Изменение статуса темы (активна/неактивна)."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        callback_data = query.data
        if "activate" in callback_data:
            topic_id = int(callback_data.replace('edit_topic_activate_', ''))
            new_status = True
            action_text = "активирована"
        else:
            topic_id = int(callback_data.replace('edit_topic_deactivate_', ''))
            new_status = False
            action_text = "деактивирована"
        
        # Получаем название темы
        topics = self.db.get_all_topics(active_only=False)
        topic = next((t for t in topics if t['id'] == topic_id), None)
        
        if not topic:
            await query.edit_message_text("❌ Тема не найдена.")
            return
        
        # Обновляем статус
        success = self.db.update_topic(topic_id, is_active=new_status)
        
        if success:
            text = f"✅ <b>Тема {action_text}</b>\n\n"
            text += f"Тема '{topic['name']}' успешно {action_text}."
        else:
            text = f"❌ <b>Ошибка</b>\n\n"
            text += f"Не удалось изменить статус темы '{topic['name']}'."
        
        keyboard = [
            [InlineKeyboardButton("🔙 К редактированию темы", callback_data=f"edit_topic_select_{topic_id}")],
            [InlineKeyboardButton("📋 К списку тем", callback_data="admin_topics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def remove_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало удаления темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        topics = self.db.get_all_topics(active_only=False)
        topic_stats = self.topic_manager.get_topic_statistics()
        
        if not topics:
            text = "🗑️ <b>Удаление темы</b>\n\nТемы не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]]
        else:
            text = "🗑️ <b>Удаление темы</b>\n\nВыберите тему для удаления:\n\n"
            text += "⚠️ <i>Удаление деактивирует тему, но не удаляет вопросы</i>\n\n"
            keyboard = []
            
            for topic in topics:
                if not topic['is_active']:
                    continue  # Показываем только активные темы
                
                question_count = topic_stats.get(topic['name'], {}).get('question_count', 0)
                display_text = f"✅ {topic['name']} ({question_count} вопросов)"
                keyboard.append([InlineKeyboardButton(
                    display_text,
                    callback_data=f"remove_topic_confirm_{topic['id']}"
                )])
            
            if not keyboard:
                text = "🗑️ <b>Удаление темы</b>\n\nНет активных тем для удаления."
            
            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_topics")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def remove_topic_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления темы."""
        query = update.callback_query
        topic_id = int(query.data.replace('remove_topic_confirm_', ''))
        await self.safe_answer_callback(query)
        
        # Получаем информацию о теме
        topics = self.db.get_all_topics(active_only=False)
        topic = next((t for t in topics if t['id'] == topic_id), None)
        
        if not topic:
            await query.edit_message_text(
                "❌ Тема не найдена.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]])
            )
            return
        
        topic_stats = self.topic_manager.get_topic_statistics()
        question_count = topic_stats.get(topic['name'], {}).get('question_count', 0)
        
        text = f"🗑️ <b>Подтверждение удаления темы</b>\n\n"
        text += f"<b>Тема:</b> {topic['name']}\n"
        text += f"<b>Вопросов:</b> {question_count}\n"
        text += f"<b>Описание:</b> {topic['description']}\n\n"
        text += "⚠️ <b>Внимание:</b> Тема будет деактивирована!\n"
        text += "Вопросы останутся в базе данных, но тема будет недоступна для тестирования.\n\n"
        text += "Подтвердите удаление:"
        
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"remove_topic_execute_{topic_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="remove_topic")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def remove_topic_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления темы."""
        query = update.callback_query
        topic_id = int(query.data.replace('remove_topic_execute_', ''))
        await self.safe_answer_callback(query)
        
        # Получаем название темы перед удалением
        topics = self.db.get_all_topics(active_only=False)
        topic = next((t for t in topics if t['id'] == topic_id), None)
        
        if not topic:
            await query.edit_message_text(
                "❌ Тема не найдена.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]])
            )
            return
        
        # Деактивируем тему
        success = self.db.delete_topic(topic_id)
        
        if success:
            text = f"✅ <b>Тема удалена</b>\n\n"
            text += f"Тема '{topic['name']}' успешно деактивирована.\n"
            text += f"Вопросы сохранены в базе данных."
        else:
            text = f"❌ <b>Ошибка удаления</b>\n\n"
            text += f"Не удалось удалить тему '{topic['name']}'."
        
        keyboard = [[InlineKeyboardButton("🔙 К управлению темами", callback_data="admin_topics")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
        # Очищаем данные
        context.user_data.pop('merge_source_id', None)

    async def remove_student_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало удаления ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        students = self.db.get_all_allowed_users()
        
        if not students:
            text = "🗑️ <b>Удаление ученика</b>\n\nУченики не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students")]]
        else:
            text = "🗑️ <b>Удаление ученика</b>\n\nВыберите ученика для удаления:\n\n"
            keyboard = []
            
            for student in students:
                status = "✅" if student['is_active'] else "❌"
                
                # Проверяем, есть ли username или user_id
                if student.get('username'):
                    identifier = f"@{student['username']}"
                    callback_data = f"remove_student_username_{student['username']}"
                elif student.get('user_id'):
                    identifier = f"ID: {student['user_id']}"
                    callback_data = f"remove_student_id_{student['user_id']}"
                else:
                    continue  # Пропускаем если нет идентификатора
                
                display_text = f"{status} {identifier} - {student['full_name']}"
                keyboard.append([InlineKeyboardButton(display_text, callback_data=callback_data)])
            
            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_students")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def remove_student_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        callback_data = query.data
        
        # Парсим данные из callback
        if callback_data.startswith('remove_student_username_'):
            username = callback_data.replace('remove_student_username_', '')
            student_identifier = f"@{username}"
            execute_callback = f"remove_student_execute_username_{username}"
        elif callback_data.startswith('remove_student_id_'):
            user_id = callback_data.replace('remove_student_id_', '')
            student_identifier = f"ID: {user_id}"
            execute_callback = f"remove_student_execute_id_{user_id}"
        else:
            await query.edit_message_text("❌ Ошибка в данных.")
            return
        
        text = f"🗑️ <b>Подтверждение удаления</b>\n\n"
        text += f"Вы действительно хотите удалить ученика:\n"
        text += f"<b>{student_identifier}</b>\n\n"
        text += "⚠️ <b>Внимание:</b> Это действие нельзя отменить!\n"
        text += "Пользователь потеряет доступ к боту."
        
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data=execute_callback)],
            [InlineKeyboardButton("❌ Отмена", callback_data="remove_student")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def remove_student_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        callback_data = query.data
        
        # Парсим данные из callback - исправленная версия
        if callback_data.startswith('remove_student_execute_username_'):
            username = callback_data.replace('remove_student_execute_username_', '')
            success = self.db.remove_allowed_user(username)
            student_identifier = f"@{username}"
        elif callback_data.startswith('remove_student_execute_id_'):
            user_id_str = callback_data.replace('remove_student_execute_id_', '')
            try:
                user_id = int(user_id_str)
                success = self.db.remove_allowed_user_by_id(user_id)
                student_identifier = f"ID: {user_id}"
            except ValueError:
                await query.edit_message_text("❌ Ошибка: неверный ID пользователя.")
                return
        else:
            await query.edit_message_text("❌ Ошибка в данных.")
            return
        
        if success:
            text = f"✅ <b>Ученик удален</b>\n\n"
            text += f"Ученик {student_identifier} успешно удален из whitelist.\n"
            text += f"Пользователь больше не имеет доступ к боту."
        else:
            text = f"❌ <b>Ошибка удаления</b>\n\n"
            text += f"Не удалось удалить ученика {student_identifier}.\n"
            text += f"Возможно, ученик уже был удален."
        
        keyboard = [[InlineKeyboardButton("🔙 К управлению учениками", callback_data="admin_students")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def confirm_add_student(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение добавления ученика после неудачной проверки username."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        callback_data = query.data
        username = callback_data.replace('confirm_add_student_', '')
        
        # Получаем сохраненные данные
        pending_student = context.user_data.get('pending_student')
        if not pending_student or pending_student['username'] != username:
            await query.edit_message_text("❌ Ошибка: данные ученика не найдены.")
            return
        
        # Добавляем ученика в базу данных
        await self._add_student_to_database(
            update, context, 
            pending_student['username'], 
            pending_student['fullname'], 
            pending_student['grade'], 
            pending_student.get('user_id'),
            "⚠️ Добавлен без проверки username"
        )

    async def _handle_edit_topic_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_name: str) -> None:
        """Обработка изменения названия темы."""
        topic_id = context.user_data.get('edit_topic_id')
        if not topic_id:
            await update.message.reply_text("❌ Ошибка: тема не найдена.")
            return
        
        success = self.db.update_topic(topic_id, name=new_name)
        
        if success:
            await update.message.reply_text(f"✅ <b>Название темы изменено</b>\n\n"
                                           f"Новое название: <b>{new_name}</b>")
        else:
            await update.message.reply_text(f"❌ <b>Ошибка изменения названия темы</b>\n\n"
                                           f"Не удалось изменить название темы.")
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('edit_topic_id', None)

    async def _handle_edit_topic_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_description: str) -> None:
        """Обработка изменения описания темы."""
        topic_id = context.user_data.get('edit_topic_id')
        if not topic_id:
            await update.message.reply_text("❌ Ошибка: тема не найдена.")
            return
        
        success = self.db.update_topic(topic_id, description=new_description)
        
        if success:
            await update.message.reply_text(f"✅ <b>Описание темы изменено</b>\n\n"
                                           f"Новое описание: <i>{new_description}</i>")
        else:
            await update.message.reply_text(f"❌ <b>Ошибка изменения описания темы</b>\n\n"
                                           f"Не удалось изменить описание темы.")
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('edit_topic_id', None)

    # === УПРАВЛЕНИЕ ВОПРОСАМИ ===
    
    async def questions_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления вопросами."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        keyboard = [
            [InlineKeyboardButton("📄 Загрузить PDF", callback_data="upload_pdf")],
            [InlineKeyboardButton("➕ Добавить вопрос", callback_data="add_question")],
            [InlineKeyboardButton("✏️ Редактировать вопрос", callback_data="edit_question")],
            [InlineKeyboardButton("🔍 Поиск вопросов", callback_data="search_questions")],
            [InlineKeyboardButton("📋 Статистика вопросов", callback_data="questions_stats")],
            [InlineKeyboardButton("🗑️ Удалить вопросы", callback_data="delete_questions")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❓ <b>Управление вопросами</b>\n\nВыберите действие:", 
                                     reply_markup=reply_markup, parse_mode='HTML')
    
    async def upload_pdf_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало загрузки PDF файла."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        context.user_data['admin_action'] = 'upload_pdf'
        
        text = "📄 <b>Загрузка PDF файла</b>\n\n"
        text += "Отправьте PDF файл с вопросами в следующем формате:\n\n"
        text += "<code>Тема: Пропорция(10)\n\n"
        text += "1) Вопрос\nA) Вариант A\nB) Вариант B ✅\nC) Вариант C\nD) Вариант D\n\n"
        text += "2) Следующий вопрос\n...</code>\n\n"
        text += "⚠️ Убедитесь, что правильные ответы помечены символом ✅"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_questions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def questions_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Статистика вопросов по темам."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
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
                    text = "📋 <b>Статистика вопросов</b>\n\nВопросы не найдены."
                else:
                    text = "📋 <b>Статистика вопросов</b>\n\n"
                    total_questions = 0
                    total_pdf = 0
                    total_ai = 0
                    
                    for topic, count, pdf_count, ai_count in stats:
                        text += f"📚 <b>{topic}</b>\n"
                        text += f"   Всего: {count}\n"
                        text += f"   📄 PDF: {pdf_count}\n"
                        text += f"   🤖 AI: {ai_count}\n\n"
                        
                        total_questions += count
                        total_pdf += pdf_count
                        total_ai += ai_count
                    
                    text += f"<b>📊 Общая статистика:</b>\n"
                    text += f"Всего вопросов: {total_questions}\n"
                    text += f"Из PDF: {total_pdf}\n"
                    text += f"Сгенерировано AI: {total_ai}"
            
        except Exception as e:
            text = f"❌ Ошибка при получении статистики: {e}"
            logging.error(f"Error getting questions stats: {e}")
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_questions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
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
            result_text = f"✅ <b>Обработка завершена!</b>\n\n"
            result_text += f"📄 Файл: {update.message.document.file_name}\n"
            result_text += f"📊 Найдено вопросов: {len(questions)}\n"
            result_text += f"💾 Сохранено новых: {saved_count}\n"
            result_text += f"⏭️ Пропущено (дубликаты): {skipped_count}\n\n"
            
            if topic_stats:
                result_text += "<b>📚 Статистика по темам:</b>\n"
                for topic, count in sorted(topic_stats.items()):
                    result_text += f"• {topic}: {count}\n"
            
            await processing_msg.edit_text(result_text, parse_mode='HTML')
            
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
        
        # Получаем список тем с количеством вопросов
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT topic, COUNT(*) as count
                    FROM questions 
                    GROUP BY topic 
                    ORDER BY topic
                """)
                topics_with_counts = cursor.fetchall()
        except Exception as e:
            logging.error(f"Error getting topics for deletion: {e}")
            topics_with_counts = []
        
        if not topics_with_counts:
            text = "🗑️ <b>Удаление вопросов</b>\n\nВопросы не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_questions")]]
        else:
            text = "🗑️ <b>Удаление вопросов</b>\n\nВыберите тему для удаления вопросов:\n\n"
            keyboard = []
            
            for topic, count in topics_with_counts:
                keyboard.append([InlineKeyboardButton(
                    f"📚 {topic} ({count} вопросов)",
                    callback_data=f"delete_questions_topic_{topic}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_questions")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def delete_questions_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления вопросов по теме."""
        query = update.callback_query
        topic = query.data.replace('delete_questions_topic_', '')
        await self.safe_answer_callback(query)
        
        # Получаем количество вопросов в теме
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM questions WHERE topic = ?", (topic,))
                count = cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"Error counting questions: {e}")
            count = 0
        
        text = f"🗑️ <b>Подтверждение удаления</b>\n\n"
        text += f"<b>Тема:</b> {topic}\n"
        text += f"<b>Вопросов:</b> {count}\n\n"
        text += "⚠️ <b>ВНИМАНИЕ:</b> Это действие нельзя отменить!\n"
        text += "Все вопросы данной темы будут удалены навсегда.\n\n"
        text += "Подтвердите удаление:"
        
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить ВСЕ", callback_data=f"delete_questions_execute_{topic}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="delete_questions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def delete_questions_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления вопросов."""
        query = update.callback_query
        topic = query.data.replace('delete_questions_execute_', '')
        await self.safe_answer_callback(query)
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM questions WHERE topic = ?", (topic,))
                count_before = cursor.fetchone()[0]
                
                cursor.execute("DELETE FROM questions WHERE topic = ?", (topic,))
                deleted_count = cursor.rowcount
                conn.commit()
            
            if deleted_count > 0:
                text = f"✅ <b>Вопросы удалены</b>\n\n"
                text += f"Удалено {deleted_count} вопросов из темы '{topic}'."
            else:
                text = f"❌ <b>Ошибка удаления</b>\n\n"
                text += f"Не найдено вопросов для удаления в теме '{topic}'."
        
        except Exception as e:
            logging.error(f"Error deleting questions: {e}")
            text = f"❌ <b>Ошибка удаления</b>\n\n"
            text += f"Произошла ошибка при удалении вопросов: {str(e)}"
        
        keyboard = [[InlineKeyboardButton("🔙 К управлению вопросами", callback_data="admin_questions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
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
            
            for topic in topics:
                keyboard.append([InlineKeyboardButton(
                    f"📚 {topic['name']}",
                    callback_data=f"add_question_topic_{topic['name']}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_questions")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def add_question_topic_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Тема выбрана, запрашиваем текст вопроса."""
        query = update.callback_query
        topic = query.data.replace('add_question_topic_', '')
        await self.safe_answer_callback(query)
        
        context.user_data['admin_action'] = 'add_question_text'
        context.user_data['new_question_topic'] = topic
        
        text = f"➕ <b>Добавление вопроса</b>\n\n"
        text += f"<b>Тема:</b> {topic}\n\n"
        text += "Введите текст вопроса:"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="add_question")]]
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

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать общую статистику системы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
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
            
            cursor.execute('SELECT COUNT(*) FROM questions WHERE source = "pdf" OR source = "db"')
            pdf_questions = cursor.fetchone()[0]
            
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
        
        text = f"📊 <b>Статистика системы</b>\n\n"
        text += f"👥 <b>Пользователи:</b>\n"
        text += f"• Активные ученики: {active_students}\n"
        text += f"• Всего в whitelist: {total_students}\n"
        text += f"• Администраторы: {total_admins}\n\n"
        
        text += f"❓ <b>Вопросы:</b>\n"
        text += f"• Всего вопросов: {total_questions}\n"
        text += f"• Из базы данных: {pdf_questions}\n"
        text += f"• Сгенерированы ИИ: {ai_questions}\n\n"
        
        text += f"📝 <b>Тестирование:</b>\n"
        text += f"• Всего тестов: {total_tests}\n"
        text += f"• Пользователей с тестами: {users_with_tests}\n"
        text += f"• Средний балл: {avg_score:.1f}%\n"
        text += f"• Тестов за неделю: {tests_last_week}\n"
        
        keyboard = [
            [InlineKeyboardButton("📈 История пользователей", callback_data="admin_user_history")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def show_user_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать историю всех пользователей, включая удаленных из whitelist."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        users_with_history = self.db.get_all_users_with_history()
        
        if not users_with_history:
            text = "📈 <b>История пользователей</b>\n\nПользователей с историей тестов не найдено."
        else:
            text = "📈 <b>История пользователей</b>\n\n"
            text += "<i>(включая удаленных из whitelist)</i>\n\n"
            
            for i, user in enumerate(users_with_history[:10], 1):  # Показываем первых 10
                username = user['username'] or f"ID_{user['user_id']}"
                full_name = user['full_name'] or "Не указано"
                
                # Проверяем, есть ли пользователь в whitelist
                is_whitelisted = self.db.is_user_allowed(user['username']) if user['username'] else False
                status = "✅ Активен" if is_whitelisted else "❌ Не в whitelist"
                
                # Безопасное форматирование avg_percentage
                avg_percentage = user.get('avg_percentage') or 0
                avg_percentage = float(avg_percentage) if avg_percentage is not None else 0.0
                
                text += f"{i}. <b>@{username}</b> ({status})\n"
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
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def merge_topics_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало объединения тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        topics = self.db.get_all_topics(active_only=False)
        topic_stats = self.topic_manager.get_topic_statistics()
        
        if len(topics) < 2:
            await query.edit_message_text(
                "❌ Недостаточно тем для объединения. Нужно минимум 2 темы.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]])
            )
            return
        
        text = "🔗 <b>Объединение тем</b>\n\n"
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
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def merge_topics_select_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор целевой темы для объединения."""
        query = update.callback_query
        source_topic_id = int(query.data.replace('merge_source_', ''))
        await self.safe_answer_callback(query)
        
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
        
        text = f"🔗 <b>Объединение тем</b>\n\n"
        text += f"Исходная тема: <b>{source_topic['name']}</b>\n"
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
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def merge_topics_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение объединения тем."""
        query = update.callback_query
        target_topic_id = int(query.data.replace('merge_target_', ''))
        source_topic_id = context.user_data.get('merge_source_id')
        await self.safe_answer_callback(query)
        
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
        
        text = f"🔗 <b>Подтверждение объединения</b>\n\n"
        text += f"<b>Исходная тема:</b> {source_topic['name']}\n"
        text += f"Вопросов: {source_count}\n\n"
        text += f"<b>Целевая тема:</b> {target_topic['name']}\n"
        text += f"Вопросов: {target_count}\n\n"
        text += f"<b>Результат:</b> {target_count + source_count} вопросов в теме '{target_topic['name']}'\n\n"
        text += "⚠️ <b>Внимание:</b> Исходная тема будет деактивирована!\n\n"
        text += "Подтвердите объединение:"
        
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data=f"merge_execute_{source_topic_id}_{target_topic_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="admin_topics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def merge_topics_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение объединения тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
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
            text = f"✅ <b>Объединение завершено!</b>\n\n"
            text += f"Все вопросы из темы '{source_topic['name']}' перенесены в '{target_topic['name']}'.\n"
            text += f"Исходная тема деактивирована."
        else:
            text = f"❌ <b>Ошибка при объединении тем.</b>\n\n"
            text += "Попробуйте еще раз или обратитесь к разработчику."
        
        keyboard = [[InlineKeyboardButton("🔙 К управлению темами", callback_data="admin_topics")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
        # Очищаем данные
        context.user_data.pop('merge_source_id', None)

    # === ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ===
    
    async def handle_admin_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработка текстовых сообщений в админ-режиме. Возвращает True если сообщение обработано."""
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            return False
        
        action = context.user_data.get('admin_action')
        if not action:
            return False
            
        text = update.message.text.strip()
        
        if action == 'add_student':
            await self._handle_add_student(update, context, text)
        elif action == 'add_student_by_id':
            await self._handle_add_student_by_id(update, context, text)
        elif action == 'add_topic':
            await self._handle_add_topic(update, context, text)
        elif action == 'add_admin':
            await self._handle_add_admin(update, context, text)
        elif action == 'add_admin_username':
            await self._handle_add_admin_username(update, context, text)
        elif action == 'add_admin_fullname':
            await self._handle_add_admin_fullname(update, context, text)
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
        elif action == 'edit_topic_name':
            await self._handle_edit_topic_name(update, context, text)
        elif action == 'edit_topic_description':
            await self._handle_edit_topic_description(update, context, text)
        elif action == 'search_questions':
            await self._handle_search_questions(update, context, text)
        elif action == 'add_question_text':
            await self._handle_add_question_text(update, context, text)
        elif action == 'add_question_option_a':
            await self._handle_add_question_option_a(update, context, text)
        elif action == 'add_question_option_b':
            await self._handle_add_question_option_b(update, context, text)
        elif action == 'add_question_option_c':
            await self._handle_add_question_option_c(update, context, text)
        elif action == 'add_question_option_d':
            await self._handle_add_question_option_d(update, context, text)
        elif action == 'add_question_correct':
            await self._handle_add_question_correct(update, context, text)
        elif action == 'add_question_explanation':
            await self._handle_add_question_explanation(update, context, text)
        elif action == 'edit_question_search':
            await self._handle_edit_question_search(update, context, text)
        elif action == 'edit_question_id':
            await self._handle_edit_question_id(update, context, text)
        elif action == 'edit_question_explanation':
            await self._handle_edit_question_explanation(update, context, text)
        elif action == 'add_base_section_name':
            await self._handle_add_base_section_name(update, context, text)
        elif action == 'add_base_section_subtopics':
            await self._handle_add_base_section_subtopics(update, context, text)
        elif action == 'student_phone':
            await self._handle_student_phone(update, context, text)
        elif action == 'student_by_id_phone':
            await self._handle_student_by_id_phone(update, context, text)
        elif action == 'edit_student_name':
            await self._handle_edit_student_name(update, context, text)
        elif action == 'edit_student_grade':
            await self._handle_edit_student_grade(update, context, text)
        elif action == 'edit_student_phone':
            await self._handle_edit_student_phone(update, context, text)
        else:
            return False
            
        return True
    
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
    
    # === ПОМОЩНИКИ ДЛЯ ОБРАБОТКИ ТЕКСТА ===
    
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
        context.user_data['admin_action'] = 'student_phone'
        
        await update.message.reply_text("📱 Введите номер телефона ученика (например: +77771234567) или напишите 'пропустить' чтобы не указывать:")
    
    async def _handle_student_by_id_fullname(self, update: Update, context: ContextTypes.DEFAULT_TYPE, fullname: str) -> None:
        """Обработка добавления ученика по ID - этап 2 (ФИО)."""
        context.user_data['new_student_fullname'] = fullname
        context.user_data['admin_action'] = 'student_by_id_phone'
        
        await update.message.reply_text("📱 Введите номер телефона ученика (например: +77771234567) или напишите 'пропустить' чтобы не указывать:")

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
        phone_number = context.user_data.get('new_student_phone')
        admin_id = update.effective_user.id
        
        # СНАЧАЛА проверяем username и получаем user_id
        student_user_id = None
        username_exists = False
        verification_message = ""
        
        await update.message.reply_text("🔍 Проверяю username через Telegram API...")
        
        try:
            # Правильный способ проверки username через Telegram API
            # Пытаемся получить информацию о пользователе
            chat_info = await context.bot.get_chat(f"@{username}")
            if chat_info and chat_info.id:
                student_user_id = chat_info.id
                username_exists = True
                verification_message = f"✅ Username @{username} подтвержден через Telegram API"
                logging.info(f"Found user_id {student_user_id} for username @{username}")
        except Exception as e:
            logging.warning(f"Telegram API verification failed for @{username}: {e}")
            
            # Fallback: проверяем в локальной базе данных
            try:
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM users WHERE username = ?', (username,))
                    result = cursor.fetchone()
                    if result:
                        student_user_id = result[0]
                        username_exists = True
                        verification_message = f"✅ Username @{username} найден в локальной базе данных"
                        logging.info(f"Found user_id {student_user_id} for username @{username} in local database")
                    else:
                        verification_message = f"⚠️ Username @{username} не найден в Telegram API и локальной базе"
                        logging.warning(f"Username @{username} not found in API or local database")
            except Exception as e2:
                verification_message = f"❌ Ошибка при проверке username @{username}: {e2}"
                logging.error(f"Error checking username @{username}: {e2}")
        
        # Показываем результат проверки
        await update.message.reply_text(f"📋 {verification_message}")
        
        # Спрашиваем подтверждение у админа
        if not username_exists:
            keyboard = [
                [InlineKeyboardButton("✅ Да, добавить", callback_data=f"confirm_add_student_{username}")],
                [InlineKeyboardButton("❌ Отмена", callback_data="admin_students")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"⚠️ <b>Внимание!</b>\n\n"
            text += f"Username @{username} не найден в Telegram.\n"
            text += f"Это может означать:\n"
            text += f"• Пользователь еще не писал боту\n"
            text += f"• Username указан неверно\n"
            text += f"• У пользователя скрытый профиль\n\n"
            text += f"Добавить ученика без проверки?"
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
            # Сохраняем данные для подтверждения
            context.user_data['pending_student'] = {
                'username': username,
                'fullname': fullname,
                'grade': grade,
                'user_id': student_user_id,
                'phone_number': phone_number
            }
            context.user_data.pop('new_student_phone', None)
            return
        
        # Если username подтвержден, добавляем сразу
        await self._add_student_to_database(update, context, username, fullname, grade, student_user_id, verification_message, phone_number)
    
    async def _add_student_to_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     username: str, fullname: str, grade: int, 
                                     student_user_id: int = None, verification_message: str = "", phone_number: str = ""):
        """Добавление ученика в базу данных."""
        admin_id = update.effective_user.id
        
        # Добавляем ученика в allowed_users
        success = self.db.add_allowed_user(username, fullname, grade, admin_id, phone_number)
        
        if success:
            # Если удалось найти user_id, обновляем запись
            if student_user_id:
                try:
                    with sqlite3.connect(self.db.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE allowed_users 
                            SET user_id = ? 
                            WHERE username = ?
                        ''', (student_user_id, username))
                        conn.commit()
                        logging.info(f"Updated allowed_users with user_id {student_user_id} for @{username}")
                        
                        # Также создаем/обновляем запись в users для синхронизации
                        cursor.execute('''
                            INSERT OR REPLACE INTO users (user_id, username, full_name, grade, phone_number)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (student_user_id, username, fullname, grade, phone_number))
                        conn.commit()
                        logging.info(f"Synced user data in users table for user_id {student_user_id}")
                        
                except Exception as e:
                    logging.error(f"Error updating user_id for @{username}: {e}")
            
            # Показываем сообщение об успехе и возвращаемся в меню управления учениками
            keyboard = [
                [InlineKeyboardButton("➕ Добавить ученика (по username)", callback_data="add_student")],
                [InlineKeyboardButton("🆔 Добавить ученика (по ID)", callback_data="add_student_by_id")],
                [InlineKeyboardButton("📋 Список учеников", callback_data="list_students")],
                [InlineKeyboardButton("🗑️ Удалить ученика", callback_data="remove_student")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"✅ Ученик @{username} успешно добавлен!\n\n"
            text += f"ФИО: {fullname}\nКласс: {grade}\n"
            if phone_number:
                text += f"📱 Телефон: {phone_number}\n"
            text += f"{verification_message}\n"
            
            if student_user_id:
                text += f"🆔 Telegram ID: {student_user_id}\n"
                text += f"📊 Данные синхронизированы в обеих таблицах\n"
            else:
                text += f"💡 ID будет добавлен автоматически при первом использовании бота\n"
            
            text += f"\n👥 <b>Управление учениками</b>\n\nВыберите действие:"
            
            # Определяем, это callback query или обычное сообщение
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            error_text = f"❌ Ошибка при добавлении ученика. Возможно, @{username} уже существует."
            if update.callback_query:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_student_username', None)
        context.user_data.pop('new_student_fullname', None)
        context.user_data.pop('pending_student', None)
        context.user_data.pop('new_student_phone', None)
    
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
        phone_number = context.user_data.get('new_student_phone')
        
        # Пытаемся получить username пользователя через Telegram API
        username = None
        try:
            user_info = await context.bot.get_chat(student_user_id)
            if user_info and user_info.username:
                username = user_info.username
                logging.info(f"Found username @{username} for user_id {student_user_id}")
        except Exception as e:
            # Если не удалось получить через API, проверяем локальную базу
            try:
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT username FROM users WHERE user_id = ?', (student_user_id,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        username = result[0]
                        logging.info(f"Found username @{username} for user_id {student_user_id} in local database")
            except Exception as e2:
                logging.warning(f"Could not find username for user_id {student_user_id}: {e2}")
        
        success = self.db.add_allowed_user_by_id(student_user_id, fullname, grade, admin_id, username, phone_number)
        
        if success:
            # Синхронизируем данные в таблице users
            try:
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO users (user_id, username, full_name, grade, phone_number)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (student_user_id, username, fullname, grade, phone_number))
                    conn.commit()
                    logging.info(f"Synced user data in users table for user_id {student_user_id}")
            except Exception as e:
                logging.error(f"Error syncing user data for user_id {student_user_id}: {e}")
            
            # Показываем сообщение об успехе и возвращаемся в меню управления учениками
            keyboard = [
                [InlineKeyboardButton("➕ Добавить ученика (по username)", callback_data="add_student")],
                [InlineKeyboardButton("🆔 Добавить ученика (по ID)", callback_data="add_student_by_id")],
                [InlineKeyboardButton("📋 Список учеников", callback_data="list_students")],
                [InlineKeyboardButton("🗑️ Удалить ученика", callback_data="remove_student")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"✅ Ученик с ID {student_user_id} успешно добавлен!\n\n"
            text += f"ФИО: {fullname}\nКласс: {grade}\n"
            if phone_number:
                text += f"📱 Телефон: {phone_number}\n"
            if username:
                text += f"👤 Username: @{username}\n"
                text += f"✅ Username автоматически найден и добавлен\n"
            else:
                text += f"⚠️ Username не найден\n"
                text += f"💡 Username будет добавлен автоматически при первом использовании бота\n"
            
            text += f"📊 Данные синхронизированы в обеих таблицах\n"
            text += f"\n👥 <b>Управление учениками</b>\n\nВыберите действие:"
            
            # Определяем, это callback query или обычное сообщение
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            error_text = f"❌ Ошибка при добавлении ученика. Возможно, пользователь с ID {student_user_id} уже существует."
            if update.callback_query:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_student_user_id', None)
        context.user_data.pop('new_student_fullname', None)
        context.user_data.pop('new_student_phone', None)
    
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
            # Показываем сообщение об успехе и возвращаемся в меню управления темами
            keyboard = [
                [InlineKeyboardButton("➕ Добавить тему", callback_data="add_topic")],
                [InlineKeyboardButton("📋 Список тем", callback_data="list_topics")],
                [InlineKeyboardButton("✏️ Редактировать тему", callback_data="edit_topic")],
                [InlineKeyboardButton("🗑️ Удалить тему", callback_data="remove_topic")],
                [InlineKeyboardButton("🔗 Объединить темы", callback_data="merge_topics")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"✅ Тема '{topic_name}' успешно добавлена!\n\n"
            text += "📚 <b>Управление темами</b>\n\nВыберите действие:"
            
            # Определяем, это callback query или обычное сообщение
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            error_text = f"❌ Ошибка при добавлении темы. Возможно, тема '{topic_name}' уже существует."
            if update.callback_query:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_topic_name', None)
    
    async def _handle_add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_text: str) -> None:
        """Обработка добавления админа - этап 1 (user_id)."""
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
        
        # Проверяем, что пользователь еще не является админом
        if self.db.is_admin(new_admin_id):
            await update.message.reply_text(f"❌ Пользователь {new_admin_id} уже является администратором.")
            context.user_data.pop('admin_action', None)
            return
        
        # Сохраняем user_id и переходим к следующему этапу
        context.user_data['new_admin_id'] = new_admin_id
        context.user_data['admin_action'] = 'add_admin_username'
        
        await update.message.reply_text(f"👤 <b>Добавление администратора</b>\n\nUser ID: {new_admin_id}\n\nВведите username нового администратора (без @):", parse_mode='HTML')

    async def _handle_add_admin_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE, username: str) -> None:
        """Обработка добавления админа - этап 2 (username)."""
        # Убираем @ если пользователь его добавил
        username = username.lstrip('@').strip()
        
        if not username:
            await update.message.reply_text("❌ Username не может быть пустым. Введите username:")
            return
        
        # Сохраняем username и переходим к следующему этапу
        context.user_data['new_admin_username'] = username
        context.user_data['admin_action'] = 'add_admin_fullname'
        
        new_admin_id = context.user_data.get('new_admin_id')
        await update.message.reply_text(f"👤 <b>Добавление администратора</b>\n\nUser ID: {new_admin_id}\nUsername: @{username}\n\nВведите полное имя администратора:", parse_mode='HTML')

    async def _handle_add_admin_fullname(self, update: Update, context: ContextTypes.DEFAULT_TYPE, fullname: str) -> None:
        """Обработка добавления админа - этап 3 (полное имя) - финальный."""
        fullname = fullname.strip()
        
        if not fullname:
            await update.message.reply_text("❌ Полное имя не может быть пустым. Введите полное имя:")
            return
        
        # Получаем все данные
        new_admin_id = context.user_data.get('new_admin_id')
        username = context.user_data.get('new_admin_username')
        admin_id = update.effective_user.id
        
        # Добавляем администратора
        success = self.db.add_admin(new_admin_id, username, fullname, False, admin_id)
        
        if success:
            text = f"✅ <b>Администратор успешно добавлен!</b>\n\n"
            text += f"👨‍💼 <b>Новый администратор:</b>\n"
            text += f"• ID: {new_admin_id}\n"
            text += f"• Username: @{username}\n"
            text += f"• Имя: {fullname}\n"
            text += f"• Роль: Обычный администратор\n\n"
            text += f"Пользователь получил права управления учениками, темами, вопросами и статистикой."
            
            # Показываем меню управления администраторами
            keyboard = [
                [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
                [InlineKeyboardButton("📋 Список админов", callback_data="list_admins")],
                [InlineKeyboardButton("🗑️ Удалить админа", callback_data="remove_admin")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text += f"\n\n👑 <b>Управление администраторами</b>\n\nВыберите действие:"
            
            # Определяем, это callback query или обычное сообщение
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            text = f"❌ Ошибка при добавлении админа. Возможно, пользователь {new_admin_id} уже является админом."
            
            # Даже при ошибке показываем меню
            keyboard = [
                [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
                [InlineKeyboardButton("📋 Список админов", callback_data="list_admins")],
                [InlineKeyboardButton("🗑️ Удалить админа", callback_data="remove_admin")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text += f"\n\n👑 <b>Управление администраторами</b>\n\nВыберите действие:"
            
            # Определяем, это callback query или обычное сообщение
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
        # Очищаем все данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_admin_id', None)
        context.user_data.pop('new_admin_username', None)
    
    async def _handle_search_questions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_text: str) -> None:
        """Обработка поиска вопросов."""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, topic, question, answer, explanation
                    FROM questions 
                    WHERE question LIKE ? OR answer LIKE ?
                    ORDER BY topic, id
                    LIMIT 20
                ''', (f'%{search_text}%', f'%{search_text}%'))
                results = cursor.fetchall()
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка поиска: {e}")
            context.user_data.pop('admin_action', None)
            return
        
        if not results:
            text = f"🔍 <b>Результаты поиска</b>\n\nПо запросу '<i>{search_text}</i>' ничего не найдено."
        else:
            text = f"🔍 <b>Результаты поиска</b>\n\nПо запросу '<i>{search_text}</i>' найдено {len(results)} результатов:\n\n"
            
            for i, (q_id, topic, question, answer, explanation) in enumerate(results, 1):
                # Ограничиваем длину для удобочитаемости
                short_question = question[:100] + "..." if len(question) > 100 else question
                short_answer = answer[:50] + "..." if len(answer) > 50 else answer
                
                text += f"{i}. <b>ID {q_id}</b> | {topic}\n"
                text += f"   <i>В:</i> {short_question}\n"
                text += f"   <i>О:</i> {short_answer}\n\n"
        
        await update.message.reply_text(text, parse_mode='HTML')
        context.user_data.pop('admin_action', None)
    
    async def _handle_add_question_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question_text: str) -> None:
        """Обработка добавления вопроса - этап 2 (текст вопроса)."""
        context.user_data['new_question_text'] = question_text
        context.user_data['admin_action'] = 'add_question_option_a'
        
        await update.message.reply_text(f"Введите вариант A:")
    
    async def _handle_add_question_option_a(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option_a: str) -> None:
        """Обработка добавления вопроса - этап 3 (вариант A)."""
        context.user_data['new_question_option_a'] = option_a
        context.user_data['admin_action'] = 'add_question_option_b'
        
        await update.message.reply_text(f"Введите вариант B:")
    
    async def _handle_add_question_option_b(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option_b: str) -> None:
        """Обработка добавления вопроса - этап 4 (вариант B)."""
        context.user_data['new_question_option_b'] = option_b
        context.user_data['admin_action'] = 'add_question_option_c'
        
        await update.message.reply_text(f"Введите вариант C:")
    
    async def _handle_add_question_option_c(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option_c: str) -> None:
        """Обработка добавления вопроса - этап 5 (вариант C)."""
        context.user_data['new_question_option_c'] = option_c
        context.user_data['admin_action'] = 'add_question_option_d'
        
        await update.message.reply_text(f"Введите вариант D:")
    
    async def _handle_add_question_option_d(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option_d: str) -> None:
        """Обработка добавления вопроса - этап 6 (вариант D)."""
        context.user_data['new_question_option_d'] = option_d
        context.user_data['admin_action'] = 'add_question_correct'
        
        await update.message.reply_text(f"Введите правильный ответ (A, B, C или D):")
    
    async def _handle_add_question_correct(self, update: Update, context: ContextTypes.DEFAULT_TYPE, correct_text: str) -> None:
        """Обработка добавления вопроса - этап 7 (правильный ответ)."""
        correct_letter = correct_text.upper().strip()
        
        if correct_letter not in ['A', 'B', 'C', 'D']:
            await update.message.reply_text("❌ Введите правильный ответ: A, B, C или D. Попробуйте еще раз:")
            return
        
        context.user_data['new_question_correct'] = correct_letter
        context.user_data['admin_action'] = 'add_question_explanation'
        
        await update.message.reply_text(f"Введите объяснение к вопросу:")
    
    async def _handle_add_question_explanation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, explanation: str) -> None:
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
            
            # Определяем, это callback query или обычное сообщение
            if update.callback_query:
                await update.callback_query.edit_message_text(text, parse_mode='HTML')
            else:
                await update.message.reply_text(text, parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при сохранении вопроса: {e}")
        
        # Очищаем все данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_question_topic', None)
        context.user_data.pop('new_question_text', None)
        context.user_data.pop('new_question_option_a', None)
        context.user_data.pop('new_question_option_b', None)
        context.user_data.pop('new_question_option_c', None)
        context.user_data.pop('new_question_option_d', None)
        context.user_data.pop('new_question_correct', None)
    
    async def _handle_edit_question_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_text: str) -> None:
        """Обработка поиска вопроса для редактирования."""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, topic, question, answer, explanation
                    FROM questions 
                    WHERE question LIKE ?
                    ORDER BY topic, id
                    LIMIT 10
                ''', (f'%{search_text}%',))
                results = cursor.fetchall()
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
    
    async def _handle_edit_question_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question_id_text: str) -> None:
        """Обработка выбора ID вопроса для редактирования."""
        try:
            question_id = int(question_id_text)
        except ValueError:
            await update.message.reply_text("❌ Введите корректный ID вопроса (число). Попробуйте еще раз:")
            return
        
        # Получаем вопрос из базы
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT topic, question, answer, explanation, incorrect_options
                    FROM questions WHERE id = ?
                ''', (question_id,))
                result = cursor.fetchone()
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения вопроса: {e}")
            context.user_data.pop('admin_action', None)
            return
        
        if not result:
            await update.message.reply_text(f"❌ Вопрос с ID {question_id} не найден.")
            context.user_data.pop('admin_action', None)
            return
        
        topic, question, answer, explanation, incorrect_options = result
        
        text = f"✏️ <b>Редактирование вопроса ID {question_id}</b>\n\n"
        text += f"<b>Тема:</b> {topic}\n"
        text += f"<b>Вопрос:</b> {question}\n"
        text += f"<b>Ответ:</b> {answer}\n"
        text += f"<b>Объяснение:</b> {explanation}\n\n"
        text += "Введите новое объяснение (или отправьте '-' чтобы оставить текущее):"
        
        context.user_data['edit_question_id'] = question_id
        context.user_data['edit_question_answer'] = answer
        context.user_data['admin_action'] = 'edit_question_explanation'
        
        await update.message.reply_text(text, parse_mode='HTML')
    
    async def _handle_edit_question_explanation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_explanation: str) -> None:
        """Обработка редактирования объяснения вопроса."""
        question_id = context.user_data.get('edit_question_id')
        current_answer = context.user_data.get('edit_question_answer')
        
        if not question_id:
            await update.message.reply_text("❌ Ошибка: вопрос не найден.")
            context.user_data.pop('admin_action', None)
            return
        
        # Если пользователь отправил '-', оставляем текущее объяснение
        if new_explanation == '-':
            await update.message.reply_text("❌ Редактирование отменено.")
            context.user_data.pop('admin_action', None)
            context.user_data.pop('edit_question_id', None)
            context.user_data.pop('edit_question_answer', None)
            return
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE questions 
                    SET explanation = ?
                    WHERE id = ?
                ''', (new_explanation, question_id))
                conn.commit()
            
            await update.message.reply_text(f"✅ <b>Вопрос обновлен!</b>\n\nНовое объяснение: <i>{new_explanation}</i>", parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при обновлении: {e}")
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('edit_question_id', None)
        context.user_data.pop('edit_question_answer', None) 
    
    # === УПРАВЛЕНИЕ БАЗОВОЙ СТРУКТУРЫ ТЕМ ===
    
    async def manage_base_structure_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления базовой структурой тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Получаем статистику базовой структуры
        base_structure = self.db.get_base_topic_structure()
        total_sections = len(base_structure)
        total_subtopics = sum(len(subtopics) for subtopics in base_structure.values())
        
        text = f"🏗️ <b>Управление базовой структурой тем</b>\n\n"
        text += f"📊 <b>Текущая структура:</b>\n"
        text += f"• Разделов: {total_sections}\n"
        text += f"• Подтем: {total_subtopics}\n\n"
        text += "Выберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("📋 Просмотр структуры", callback_data="view_base_structure")],
            [InlineKeyboardButton("➕ Добавить раздел", callback_data="add_base_section")],
            [InlineKeyboardButton("✏️ Редактировать раздел", callback_data="edit_base_section")],
            [InlineKeyboardButton("🗑️ Удалить раздел", callback_data="delete_base_section")],
            [InlineKeyboardButton("🔙 Назад", callback_data="add_topic")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def view_base_structure(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Просмотр базовой структуры тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        base_structure = self.db.get_base_topic_structure()
        
        text = f"📋 <b>Базовая структура тем</b>\n\n"
        
        if not base_structure:
            text += "Структура пустая."
        else:
            for i, (main_topic, subtopics) in enumerate(base_structure.items(), 1):
                text += f"{i}. <b>{main_topic}</b> ({len(subtopics)} подтем)\n"
                for j, subtopic in enumerate(subtopics[:3], 1):  # Показываем первые 3
                    text += f"   {j}. {subtopic}\n"
                if len(subtopics) > 3:
                    text += f"   ... и еще {len(subtopics) - 3}\n"
                text += "\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="manage_base_structure")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def add_base_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления нового раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        context.user_data['admin_action'] = 'add_base_section_name'
        
        text = f"➕ <b>Добавление нового раздела</b>\n\n"
        text += "Введите название основного раздела (например: '📊 Статистика и вероятность'):"
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="manage_base_structure")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def edit_base_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало редактирования раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        base_structure = self.db.get_base_topic_structure()
        
        if not base_structure:
            text = "✏️ <b>Редактирование раздела</b>\n\nНет разделов для редактирования."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="manage_base_structure")]]
        else:
            text = "✏️ <b>Редактирование раздела</b>\n\nВыберите раздел для редактирования:\n\n"
            keyboard = []
            
            for i, main_topic in enumerate(base_structure.keys()):
                # Используем индекс вместо названия для callback_data
                keyboard.append([InlineKeyboardButton(
                    f"✏️ {main_topic}",
                    callback_data=f"edit_base_section_select_{i}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="manage_base_structure")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def delete_base_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало удаления раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        base_structure = self.db.get_base_topic_structure()
        
        if not base_structure:
            text = "🗑️ <b>Удаление раздела</b>\n\nНет разделов для удаления."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="manage_base_structure")]]
        else:
            text = "🗑️ <b>Удаление раздела</b>\n\nВыберите раздел для удаления:\n\n"
            text += "⚠️ <i>Удаление раздела не удаляет созданные темы</i>\n\n"
            keyboard = []
            
            for i, (main_topic, subtopics) in enumerate(base_structure.items()):
                # Используем индекс вместо названия для callback_data
                keyboard.append([InlineKeyboardButton(
                    f"🗑️ {main_topic} ({len(subtopics)} подтем)",
                    callback_data=f"delete_base_section_confirm_{i}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="manage_base_structure")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def _handle_add_base_section_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, section_name: str) -> None:
        """Обработка названия нового раздела."""
        context.user_data['new_base_section_name'] = section_name
        context.user_data['admin_action'] = 'add_base_section_subtopics'
        
        await update.message.reply_text(
            f"Введите подтемы для раздела '<b>{section_name}</b>':\n\n"
            f"Формат: каждая подтема с новой строки\n"
            f"Пример:\n"
            f"Подтема 1\n"
            f"Подтема 2\n"
            f"Подтема 3",
                parse_mode='HTML'
            )

    async def _handle_add_base_section_subtopics(self, update: Update, context: ContextTypes.DEFAULT_TYPE, subtopics_text: str) -> None:
        """Обработка подтем нового раздела."""
        section_name = context.user_data.get('new_base_section_name')
        if not section_name:
            await update.message.reply_text("❌ Ошибка: название раздела не найдено.")
            return
        
        # Парсим подтемы
        subtopics = [line.strip() for line in subtopics_text.split('\n') if line.strip()]
        
        if not subtopics:
            await update.message.reply_text("❌ Введите хотя бы одну подтему. Попробуйте еще раз:")
            return
        
        # Добавляем в базу
        success = self.db.add_base_topic_section(section_name, subtopics)
        
        if success:
            text = f"✅ <b>Раздел добавлен!</b>\n\n"
            text += f"<b>Раздел:</b> {section_name}\n"
            text += f"<b>Подтем:</b> {len(subtopics)}\n\n"
            text += "<b>Подтемы:</b>\n"
            for i, subtopic in enumerate(subtopics, 1):
                text += f"{i}. {subtopic}\n"
        else:
            text = f"❌ <b>Ошибка добавления раздела</b>\n\n"
            text += "Возможно, некоторые подтемы уже существуют."
        
        await update.message.reply_text(text, parse_mode='HTML')
        
        # Очищаем данные
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_base_section_name', None) 
    
    async def edit_base_section_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор раздела для редактирования."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            section_index = int(query.data.replace('edit_base_section_select_', ''))
            base_structure = self.db.get_base_topic_structure()
            main_topics = list(base_structure.keys())
            
            if section_index >= len(main_topics):
                raise IndexError("Invalid section index")
                
            main_topic = main_topics[section_index]
            subtopics = base_structure[main_topic]
            
            text = f"✏️ <b>Редактирование раздела</b>\n\n"
            text += f"<b>Раздел:</b> {main_topic}\n"
            text += f"<b>Подтем:</b> {len(subtopics)}\n\n"
            text += "<b>Подтемы:</b>\n"
            for i, subtopic in enumerate(subtopics, 1):
                text += f"{i}. {subtopic}\n"
            
            text += "\n<i>Функция редактирования разделов будет добавлена в следующих обновлениях.</i>"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="edit_base_section")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text(
                "❌ Ошибка: раздел не найден.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="edit_base_section")]])
            )

    async def delete_base_section_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            section_index = int(query.data.replace('delete_base_section_confirm_', ''))
            base_structure = self.db.get_base_topic_structure()
            main_topics = list(base_structure.keys())
            
            if section_index >= len(main_topics):
                raise IndexError("Invalid section index")
                
            main_topic = main_topics[section_index]
            subtopics = base_structure[main_topic]
            
            text = f"🗑️ <b>Подтверждение удаления</b>\n\n"
            text += f"<b>Раздел:</b> {main_topic}\n"
            text += f"<b>Подтем:</b> {len(subtopics)}\n\n"
            text += "⚠️ <b>Внимание!</b> Это действие нельзя отменить.\n"
            text += "Удаление раздела не удаляет созданные темы.\n\n"
            text += "Вы уверены, что хотите удалить этот раздел?"
            
            keyboard = [
                [InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_base_section_execute_{section_index}")],
                [InlineKeyboardButton("❌ Отмена", callback_data="delete_base_section")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text(
                "❌ Ошибка: раздел не найден.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="delete_base_section")]])
            )

    async def delete_base_section_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            section_index = int(query.data.replace('delete_base_section_execute_', ''))
            base_structure = self.db.get_base_topic_structure()
            main_topics = list(base_structure.keys())
            
            if section_index >= len(main_topics):
                raise IndexError("Invalid section index")
                
            main_topic = main_topics[section_index]
            
            # Удаляем раздел из базы данных
            success = self.db.delete_base_topic_section(main_topic)
            
            if success:
                text = f"✅ <b>Раздел удален</b>\n\n"
                text += f"Раздел '{main_topic}' успешно удален из базовой структуры."
            else:
                text = f"❌ <b>Ошибка удаления</b>\n\n"
                text += f"Не удалось удалить раздел '{main_topic}'."
            
            keyboard = [[InlineKeyboardButton("🔙 К управлению структурой", callback_data="manage_base_structure")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await query.edit_message_text(
                "❌ Ошибка: раздел не найден.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="manage_base_structure")]])
            )
    
    # === УПРАВЛЕНИЕ АДМИНАМИ ===
    
    async def admins_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления админами (только для суперадмина)."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Очищаем состояние при возврате в меню
        context.user_data.pop('admin_action', None)
        
        user_id = update.effective_user.id
        
        if not self.db.is_super_admin(user_id):
            await query.edit_message_text("❌ Доступ запрещен. Только для суперадминистратора.")
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton("📋 Список админов", callback_data="list_admins")],
            [InlineKeyboardButton("🗑️ Удалить админа", callback_data="remove_admin")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👑 <b>Управление администраторами</b>\n\nВыберите действие:", 
                                     reply_markup=reply_markup, parse_mode='HTML')
    
    async def add_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления админа (только для суперадмина)."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = update.effective_user.id
        
        # Проверяем, что пользователь является суперадмином
        if not self.db.is_super_admin(user_id):
            await query.edit_message_text("❌ Доступ запрещен. Только суперадминистратор может добавлять админов.")
            return
        
        context.user_data['admin_action'] = 'add_admin'
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admins_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "➕ <b>Добавление обычного администратора</b>\n\n"
        text += "👨‍💼 <b>Права обычного администратора:</b>\n"
        text += "• Управление учениками\n"
        text += "• Управление темами\n"
        text += "• Управление вопросами\n"
        text += "• Просмотр статистики\n\n"
        text += "ℹ️ <i>Для добавления суперадминистратора используйте скрипт init_superadmin.py</i>\n\n"
        text += "Введите Telegram user_id нового администратора:"
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def list_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех админов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        admins = self.db.get_all_admins()
        
        if not admins:
            text = "👑 <b>Список администраторов</b>\n\nАдминистраторы не найдены."
        else:
            text = "👑 <b>Список администраторов</b>\n\n"
            for i, admin in enumerate(admins, 1):
                role = "👑 Суперадмин" if admin['is_super'] else "👨‍💼 Админ"
                text += f"{i}. {role}\n"
                text += f"   ID: {admin['user_id']}\n"
                text += f"   Username: @{admin['username']}\n"
                text += f"   Имя: {admin['name']}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admins_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def remove_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало удаления админа (только для суперадмина)."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = update.effective_user.id
        
        if not self.db.is_super_admin(user_id):
            await query.edit_message_text("❌ Доступ запрещен. Только суперадминистратор может удалять админов.")
            return
        
        admins = self.db.get_all_admins()
        current_admin_id = user_id
        
        # Фильтруем список: убираем суперадминов и текущего пользователя
        removable_admins = [admin for admin in admins if not admin['is_super'] and admin['user_id'] != current_admin_id]
        
        if not removable_admins:
            text = "🗑️ <b>Удаление администратора</b>\n\nНет администраторов, которых можно удалить.\n\n"
            text += "ℹ️ <i>Суперадминистратор не может удалить себя или других суперадминистраторов.</i>"
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admins_menu")]]
        else:
            text = "🗑️ <b>Удаление администратора</b>\n\nВыберите администратора для удаления:\n\n"
            text += "⚠️ <i>Можно удалить только обычных админов</i>\n\n"
            keyboard = []
            
            for admin in removable_admins:
                display_text = f"👨‍💼 @{admin['username']} - {admin['name']}"
                keyboard.append([InlineKeyboardButton(
                    display_text,
                    callback_data=f"remove_admin_confirm_{admin['user_id']}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admins_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def remove_admin_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления админа."""
        query = update.callback_query
        admin_id_to_remove = int(query.data.replace('remove_admin_confirm_', ''))
        await self.safe_answer_callback(query)
        
        current_user_id = update.effective_user.id
        
        # Дополнительная проверка прав
        if not self.db.is_super_admin(current_user_id):
            await query.edit_message_text("❌ Доступ запрещен. Только суперадминистратор может удалять админов.")
            return
        
        # Получаем информацию об админе
        admins = self.db.get_all_admins()
        admin_to_remove = next((admin for admin in admins if admin['user_id'] == admin_id_to_remove), None)
        
        if not admin_to_remove:
            await query.edit_message_text(
                "❌ Администратор не найден.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admins_menu")]])
            )
            return
        
        # Проверяем, что не пытаемся удалить суперадмина или себя
        if admin_to_remove['is_super']:
            await query.edit_message_text(
                "❌ Нельзя удалить суперадминистратора.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="remove_admin")]])
            )
            return
        
        if admin_id_to_remove == current_user_id:
            await query.edit_message_text(
                "❌ Нельзя удалить самого себя.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="remove_admin")]])
            )
            return
        
        text = f"🗑️ <b>Подтверждение удаления</b>\n\n"
        text += f"<b>Администратор:</b> @{admin_to_remove['username']}\n"
        text += f"<b>Имя:</b> {admin_to_remove['name']}\n"
        text += f"<b>ID:</b> {admin_to_remove['user_id']}\n"
        text += f"<b>Роль:</b> {'👑 Суперадмин' if admin_to_remove['is_super'] else '👨‍💼 Админ'}\n\n"
        text += "⚠️ <b>ВНИМАНИЕ:</b> Это действие нельзя отменить!\n"
        text += "Пользователь потеряет права администратора.\n\n"
        text += "Подтвердите удаление:"
        
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"remove_admin_execute_{admin_id_to_remove}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="remove_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def remove_admin_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления админа."""
        query = update.callback_query
        admin_id_to_remove = int(query.data.replace('remove_admin_execute_', ''))
        await self.safe_answer_callback(query)
        
        current_user_id = update.effective_user.id
        
        # Финальная проверка прав
        if not self.db.is_super_admin(current_user_id):
            await query.edit_message_text("❌ Доступ запрещен. Только суперадминистратор может удалять админов.")
            return
        
        # Получаем информацию об админе перед удалением
        admins = self.db.get_all_admins()
        admin_to_remove = next((admin for admin in admins if admin['user_id'] == admin_id_to_remove), None)
        
        if not admin_to_remove:
            await query.edit_message_text(
                "❌ Администратор не найден.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admins_menu")]])
            )
            return
        
        # Финальные проверки безопасности
        if admin_to_remove['is_super'] or admin_id_to_remove == current_user_id:
            await query.edit_message_text(
                "❌ Операция запрещена по соображениям безопасности.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admins_menu")]])
            )
            return
        
        # Удаляем админа
        success = self.db.remove_admin(admin_id_to_remove)
        
        if success:
            text = f"✅ <b>Администратор удален</b>\n\n"
            text += f"Пользователь @{admin_to_remove['username']} ({admin_to_remove['name']}) больше не является администратором.\n"
            text += f"ID: {admin_id_to_remove}"
        else:
            text = f"❌ <b>Ошибка удаления</b>\n\n"
            text += f"Не удалось удалить администратора @{admin_to_remove['username']}.\n"
            text += f"Возможно, администратор уже был удален."
        
        keyboard = [[InlineKeyboardButton("🔙 К управлению админами", callback_data="admins_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def refresh_topics_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обновление статистики тем."""
        query = update.callback_query
        await query.answer("🔄 Статистика обновлена!")
        
        try:
            # Принудительно обновляем статистику через сброс кэша
            self.topic_manager._invalidate_cache()
            
            # Просто вызываем list_topics напрямую с текущими данными
            await self.list_topics(update, context)
            
        except Exception as e:
            # Если произошла ошибка, показываем сообщение об ошибке
            try:
                await query.edit_message_text(
                    f"❌ <b>Ошибка обновления статистики</b>\n\n{str(e)}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="list_topics")]]),
                    parse_mode='HTML'
                )
            except Exception:
                # Если и это не сработало, отправляем новое сообщение
                await query.message.reply_text(
                    f"❌ <b>Ошибка обновления статистики</b>\n\n{str(e)}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="list_topics")]]),
                    parse_mode='HTML'
                )

    async def detailed_topics_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подробная статистика по темам."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        topics = self.db.get_all_topics(active_only=False)
        topic_stats = self.topic_manager.get_topic_statistics()
        
        if not topics:
            text = "📊 <b>Подробная статистика</b>\n\nТемы не найдены."
        else:
            # Сортируем темы по количеству вопросов (по убыванию)
            topics_with_stats = []
            for topic in topics:
                question_count = topic_stats.get(topic['name'], {}).get('question_count', 0)
                topics_with_stats.append((topic, question_count))
            
            topics_with_stats.sort(key=lambda x: x[1], reverse=True)
            
            active_count = sum(1 for t, _ in topics_with_stats if t['is_active'])
            inactive_count = len(topics_with_stats) - active_count
            total_questions = sum(count for _, count in topics_with_stats)
            
            text = f"📊 <b>Подробная статистика тем</b>\n\n"
            text += f"📈 <b>Общие показатели:</b>\n"
            text += f"• Всего тем: {len(topics_with_stats)}\n"
            text += f"• Активных: {active_count} ✅\n"
            text += f"• Неактивных: {inactive_count} ❌\n"
            text += f"• Всего вопросов: {total_questions}\n"
            text += f"• Среднее вопросов на тему: {total_questions / len(topics_with_stats):.1f}\n\n"
            
            # Топ-10 тем по количеству вопросов
            text += f"🏆 <b>Топ-10 тем по вопросам:</b>\n"
            for i, (topic, count) in enumerate(topics_with_stats[:10], 1):
                status = "✅" if topic['is_active'] else "❌"
                text += f"{i}. {status} <b>{topic['name']}</b> - {count} вопр.\n"
            
            # Темы без вопросов
            empty_topics = [topic for topic, count in topics_with_stats if count == 0]
            if empty_topics:
                text += f"\n⚠️ <b>Темы без вопросов ({len(empty_topics)}):</b>\n"
                for topic in empty_topics[:5]:  # Показываем первые 5
                    status = "✅" if topic['is_active'] else "❌"
                    text += f"• {status} {topic['name']}\n"
                if len(empty_topics) > 5:
                    text += f"... и еще {len(empty_topics) - 5}\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="detailed_topics_stats")],
            [InlineKeyboardButton("🔙 К списку тем", callback_data="list_topics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def _handle_student_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE, phone_text: str) -> None:
        """Обработка добавления ученика - этап 3 (номер телефона)."""
        phone_number = None
        
        if phone_text.lower() not in ['пропустить', 'skip', '-']:
            # Простая валидация номера телефона
            phone_clean = phone_text.strip()
            if phone_clean and (phone_clean.startswith('+') or phone_clean.startswith('8') or phone_clean.startswith('7')):
                phone_number = phone_clean
            else:
                await update.message.reply_text("❌ Неверный формат номера. Введите номер в формате +77771234567 или напишите 'пропустить':")
                return
        
        context.user_data['new_student_phone'] = phone_number
        context.user_data['admin_action'] = 'student_grade'
        
        await update.message.reply_text("Введите класс ученика (число от 1 до 11):")
    
    async def _handle_student_by_id_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE, phone_text: str) -> None:
        """Обработка добавления ученика по ID - этап 3 (номер телефона)."""
        phone_number = None
        
        if phone_text.lower() not in ['пропустить', 'skip', '-']:
            # Простая валидация номера телефона
            phone_clean = phone_text.strip()
            if phone_clean and (phone_clean.startswith('+') or phone_clean.startswith('8') or phone_clean.startswith('7')):
                phone_number = phone_clean
            else:
                await update.message.reply_text("❌ Неверный формат номера. Введите номер в формате +77771234567 или напишите 'пропустить':")
                return
        
        context.user_data['new_student_phone'] = phone_number
        context.user_data['admin_action'] = 'student_by_id_grade'
        
        await update.message.reply_text("Введите класс ученика (число от 1 до 11):")

    async def edit_student_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало редактирования информации о студенте."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        
        # Получаем информацию о студенте
        student_info = self.db.get_allowed_user_by_id(user_id)
        
        if not student_info:
            text = "❌ Студент не найден."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="list_students")]]
        else:
            text = f"✏️ <b>Редактирование студента</b>\n\n"
            text += f"👤 <b>Текущая информация:</b>\n"
            text += f"• ID: {student_info['user_id']}\n"
            text += f"• Username: @{student_info['username'] or 'не указан'}\n"
            text += f"• ФИО: {student_info['full_name'] or 'не указано'}\n"
            text += f"• Класс: {student_info['grade'] or 'не указан'}\n"
            text += f"• Телефон: {student_info['phone_number'] or 'не указан'}\n"
            text += f"• Статус: {'Активен' if student_info['is_active'] else 'Неактивен'}\n\n"
            text += "Выберите что хотите изменить:"
            
            keyboard = [
                [InlineKeyboardButton("📝 Изменить ФИО", callback_data=f"edit_student_name_{user_id}")],
                [InlineKeyboardButton("🎓 Изменить класс", callback_data=f"edit_student_grade_{user_id}")],
                [InlineKeyboardButton("📱 Изменить телефон", callback_data=f"edit_student_phone_{user_id}")],
                [InlineKeyboardButton("🔄 Изменить статус", callback_data=f"edit_student_status_{user_id}")],
                [InlineKeyboardButton("🔙 Назад к деталям", callback_data=f"student_details_{user_id}")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def edit_student_name_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения ФИО студента."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        context.user_data['admin_action'] = 'edit_student_name'
        context.user_data['edit_student_id'] = user_id
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("📝 <b>Изменение ФИО</b>\n\nВведите новое ФИО студента:", 
                                     reply_markup=reply_markup, parse_mode='HTML')

    async def edit_student_grade_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения класса студента."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        context.user_data['admin_action'] = 'edit_student_grade'
        context.user_data['edit_student_id'] = user_id
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("🎓 <b>Изменение класса</b>\n\nВведите новый класс студента (число от 1 до 11):", 
                                     reply_markup=reply_markup, parse_mode='HTML')

    async def edit_student_phone_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало изменения телефона студента."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        context.user_data['admin_action'] = 'edit_student_phone'
        context.user_data['edit_student_id'] = user_id
        
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"edit_student_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("📱 <b>Изменение телефона</b>\n\nВведите новый номер телефона студента (начинающийся с +, 8 или 7) или напишите 'удалить' для удаления номера:", 
                                     reply_markup=reply_markup, parse_mode='HTML')

    async def edit_student_status_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Изменение статуса студента (активен/неактивен)."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        user_id = int(query.data.split('_')[-1])
        
        # Получаем текущую информацию о студенте
        student_info = self.db.get_allowed_user_by_id(user_id)
        
        if not student_info:
            text = "❌ Студент не найден."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="list_students")]]
        else:
            # Переключаем статус
            new_status = not student_info['is_active']
            success = self.db.update_allowed_user_by_id(user_id, is_active=new_status)
            
            if success:
                status_text = "активен" if new_status else "неактивен"
                text = f"✅ <b>Статус изменен</b>\n\nСтудент {student_info['full_name'] or f'ID_{user_id}'} теперь {status_text}."
            else:
                text = "❌ Ошибка при изменении статуса."
            
            keyboard = [[InlineKeyboardButton("🔙 Назад к редактированию", callback_data=f"edit_student_{user_id}")]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def show_class_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать статистику по классам."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        class_stats = self.db.get_class_statistics()
        
        if not class_stats['class_stats']:
            text = "📈 <b>Статистика по классам</b>\n\nДанных нет."
        else:
            text = "📈 <b>Статистика по классам</b>\n\n"
            
            total_students = 0
            total_active = 0
            total_tests = 0
            
            for cls in class_stats['class_stats']:
                if cls['grade']:  # Пропускаем записи без класса
                    text += f"🎓 <b>{cls['grade']} класс:</b>\n"
                    text += f"• Учеников: {cls['students_count']}\n"
                    text += f"• Активных: {cls['active_students']} ({cls['activity_rate']}%)\n"
                    text += f"• Тестов: {cls['total_tests']}\n"
                    text += f"• Средний балл: {cls['avg_score']}%\n\n"
                    
                    total_students += cls['students_count']
                    total_active += cls['active_students']
                    total_tests += cls['total_tests']
            
            text += f"📊 <b>Общая статистика:</b>\n"
            text += f"• Всего учеников: {total_students}\n"
            text += f"• Активных: {total_active}\n"
            text += f"• Всего тестов: {total_tests}\n"
            overall_activity = round((total_active / total_students * 100) if total_students > 0 else 0, 1)
            text += f"• Общая активность: {overall_activity}%\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад к списку учеников", callback_data="list_students")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def _handle_edit_student_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_name: str) -> None:
        """Обработка изменения ФИО студента."""
        user_id = context.user_data.get('edit_student_id')
        
        if not user_id:
            await update.message.reply_text("❌ Ошибка: ID студента не найден.")
            context.user_data.pop('admin_action', None)
            return
        
        success = self.db.update_allowed_user_by_id(user_id, full_name=new_name)
        
        if success:
            # Также обновляем в таблице users если студент уже использовал бота
            self.db.update_user_info(user_id, new_name, None)
            
            # Создаем кнопку для возврата к списку учеников
            keyboard = [[InlineKeyboardButton("👥 Назад к списку учеников", callback_data="list_students")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ ФИО студента успешно изменено на: {new_name}",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Ошибка при изменении ФИО.")
        
        # Очищаем состояние
        context.user_data.pop('admin_action', None)
        context.user_data.pop('edit_student_id', None)

    async def _handle_edit_student_grade(self, update: Update, context: ContextTypes.DEFAULT_TYPE, grade_text: str) -> None:
        """Обработка изменения класса студента."""
        user_id = context.user_data.get('edit_student_id')
        
        if not user_id:
            await update.message.reply_text("❌ Ошибка: ID студента не найден.")
            context.user_data.pop('admin_action', None)
            return
        
        try:
            grade = int(grade_text)
            if grade < 1 or grade > 11:
                await update.message.reply_text("❌ Класс должен быть от 1 до 11. Попробуйте еще раз:")
                return
        except ValueError:
            await update.message.reply_text("❌ Введите корректный номер класса (число). Попробуйте еще раз:")
            return
        
        success = self.db.update_allowed_user_by_id(user_id, grade=grade)
        
        if success:
            # Также обновляем в таблице users если студент уже использовал бота
            self.db.update_user_info(user_id, None, grade)
            
            # Создаем кнопку для возврата к списку учеников
            keyboard = [[InlineKeyboardButton("👥 Назад к списку учеников", callback_data="list_students")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Класс студента успешно изменен на: {grade}",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Ошибка при изменении класса.")
        
        # Очищаем состояние
        context.user_data.pop('admin_action', None)
        context.user_data.pop('edit_student_id', None)

    async def _handle_edit_student_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE, phone_text: str) -> None:
        """Обработка изменения телефона студента."""
        user_id = context.user_data.get('edit_student_id')
        
        if not user_id:
            await update.message.reply_text("❌ Ошибка: ID студента не найден.")
            context.user_data.pop('admin_action', None)
            return
        
        # Проверяем на удаление номера
        if phone_text.lower() in ['удалить', 'delete', 'remove', '-']:
            phone_number = None
            action_text = "удален"
        else:
            # Валидация номера телефона
            if not (phone_text.startswith('+') or phone_text.startswith('8') or phone_text.startswith('7')):
                await update.message.reply_text("❌ Номер телефона должен начинаться с +, 8 или 7. Попробуйте еще раз:")
                return
            
            phone_number = phone_text
            action_text = f"изменен на: {phone_number}"
        
        success = self.db.update_allowed_user_phone(user_id=user_id, phone_number=phone_number)
        
        if success:
            # Также обновляем в таблице users если студент уже использовал бота
            if phone_number:
                self.db.update_user_phone(user_id, phone_number)
            
            # Создаем кнопку для возврата к списку учеников
            keyboard = [[InlineKeyboardButton("👥 Назад к списку учеников", callback_data="list_students")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Номер телефона студента {action_text}",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Ошибка при изменении номера телефона.")
        
        # Очищаем состояние
        context.user_data.pop('admin_action', None)
        context.user_data.pop('edit_student_id', None)