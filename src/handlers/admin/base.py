"""
Базовый класс для админ-хендлеров.
Содержит общие методы и импорты.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.question_service import QuestionService
from services.pdf_processor import PDFProcessor, add_questions_to_db
import logging
import tempfile
import asyncio

from handlers.base_handler import BaseHandler
from services.topic_manager import TopicManager
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from services.ai_service import AIService
from src.db import get_database
from src.db import Database

class AdminBaseHandler(BaseHandler):
    """Базовый класс для всех админ-хендлеров."""
    
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
        
        query = update.callback_query
        if query:
            await self.safe_answer_callback(query)
        
        # Получаем статистику для админ-панели
        try:
            # Используем database facade вместо прямого SQLite подключения
            
            # Количество учеников
            students_count = len(self.db.get_all_allowed_users())
            
            # Количество тем
            topics = self.db.get_all_topics(active_only=True)
            topics_count = len(topics)
            
            # Количество вопросов
            questions = self.db.get_all_questions()
            questions_count = len(questions)
            
            # Количество админов
            admins = self.db.get_all_admins()
            admins_count = len(admins)
            
        except Exception as e:
            logging.error(f"Error getting admin panel stats: {e}")
            students_count = topics_count = questions_count = admins_count = 0
        
        text = f"🔧 <b>Панель администратора</b>\n\n"
        text += f"📊 <b>Статистика:</b>\n"
        text += f"👥 Учеников: {students_count}\n"
        text += f"📚 Тем: {topics_count}\n"
        text += f"❓ Вопросов: {questions_count}\n"
        text += f"👨‍💼 Админов: {admins_count}\n\n"
        text += f"Выберите раздел для управления:"
        
        is_super = self.db.is_super_admin(user_id)
        
        keyboard = [
            [InlineKeyboardButton("👥 Управление учениками", callback_data="admin_students")],
            [InlineKeyboardButton("📚 Управление темами", callback_data="admin_topics")],
            [InlineKeyboardButton("📚 Управление разделами", callback_data="sections_menu")],
            [InlineKeyboardButton("❓ Управление вопросами", callback_data="admin_questions")],
        ]
        
        # Функции только для суперадмина
        if is_super:
            keyboard.append([InlineKeyboardButton("👑 Управление админами", callback_data="admin_admins")])
        
        keyboard.extend([
            [InlineKeyboardButton("📊 Статистика и отчеты", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Назад к выбору тем", callback_data="back_to_main")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            # Отправляем новое сообщение (старые уже удалены/очищены)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_admin_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработка текстовых сообщений в админ-режиме. Возвращает True если сообщение обработано."""
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            return False
        
        action = context.user_data.get('admin_action')
        if not action:
            return False
            
        text = update.message.text.strip()
        
        # Делегируем обработку в соответствующие модули
        # Обработчики для вопросов
        if action in ['search_questions', 'add_question_text', 'add_question_option_a', 
                      'add_question_option_b', 'add_question_option_c', 'add_question_option_d',
                      'add_question_correct', 'add_question_explanation', 'edit_question_search',
                      'edit_question_id', 'edit_question_explanation', 'delete_single_question_search']:
            from .questions import QuestionsHandler
            questions_handler = QuestionsHandler(self.db, self.question_service)
            
            if action == 'search_questions':
                await questions_handler.handle_search_questions(update, context, text)
            elif action == 'add_question_text':
                await questions_handler.handle_add_question_text(update, context, text)
            elif action == 'add_question_option_a':
                await questions_handler.handle_add_question_option_a(update, context, text)
            elif action == 'add_question_option_b':
                await questions_handler.handle_add_question_option_b(update, context, text)
            elif action == 'add_question_option_c':
                await questions_handler.handle_add_question_option_c(update, context, text)
            elif action == 'add_question_option_d':
                await questions_handler.handle_add_question_option_d(update, context, text)
            elif action == 'add_question_correct':
                await questions_handler.handle_add_question_correct(update, context, text)
            elif action == 'add_question_explanation':
                await questions_handler.handle_add_question_explanation(update, context, text)
            elif action == 'edit_question_search':
                await questions_handler.handle_edit_question_search(update, context, text)
            elif action == 'edit_question_id':
                await questions_handler.handle_edit_question_id(update, context, text)
            elif action == 'edit_question_explanation':
                await questions_handler.handle_edit_question_explanation(update, context, text)
            elif action == 'delete_single_question_search':
                await questions_handler.handle_delete_single_question_search(update, context, text)
            
            return True
        
        # Здесь можно добавить обработчики для других модулей (студенты, темы и т.д.)
        
        return False

    async def handle_admin_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка документов в админ-режиме."""
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            return
        
        # Проверяем, ожидается ли PDF файл
        if context.user_data.get('admin_action') == 'upload_pdf':
            # Импортируем модуль вопросов для обработки PDF
            from .questions import QuestionsHandler
            questions_handler = QuestionsHandler(self.db, self.question_service)
            await questions_handler.process_pdf_file(update, context)
        else:
            await update.message.reply_text("❓ Неожиданный документ. Используйте команды админ-панели.")

    # === ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ИЗ СТАРОГО ФАЙЛА ===

    async def manage_base_structure_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления базовой структурой."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Модуль управления базовой структурой в разработке...")

    async def view_base_structure(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Просмотр базовой структуры."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция просмотра базовой структуры в разработке...")

    async def add_base_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления базового раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция добавления базового раздела в разработке...")

    async def edit_base_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало редактирования базового раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция редактирования базового раздела в разработке...")

    async def delete_base_section_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало удаления базового раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция удаления базового раздела в разработке...")

    async def edit_base_section_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор базового раздела для редактирования."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выбора базового раздела для редактирования в разработке...")

    async def delete_base_section_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления базового раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция подтверждения удаления базового раздела в разработке...")

    async def delete_base_section_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления базового раздела."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выполнения удаления базового раздела в разработке...")

    async def confirm_add_student(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение добавления ученика."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция подтверждения добавления ученика в разработке...")

    # === ОБРАБОТЧИКИ ТЕКСТА ДЛЯ БАЗОВОЙ СТРУКТУРЫ ===

    async def handle_add_base_section_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, section_name: str) -> None:
        """Обработка названия базового раздела."""
        await update.message.reply_text("🚧 Функция обработки названия базового раздела в разработке...")

    async def handle_add_base_section_subtopics(self, update: Update, context: ContextTypes.DEFAULT_TYPE, subtopics_text: str) -> None:
        """Обработка подтем базового раздела."""
        await update.message.reply_text("🚧 Функция обработки подтем базового раздела в разработке...") 