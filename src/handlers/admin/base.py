"""
Базовый класс для админ-хендлеров.
Содержит общие методы и импорты.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.database import Database
from services.question_service import QuestionService
from services.pdf_processor import PDFProcessor, add_questions_to_db
import logging
import tempfile
import asyncio
import sqlite3
from handlers.base_handler import BaseHandler
from services.topic_manager import TopicManager
from typing import Dict, List
from datetime import datetime
from services.ai_service import AIService

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
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Количество учеников
                cursor.execute('SELECT COUNT(*) FROM allowed_users WHERE is_active = 1')
                students_count = cursor.fetchone()[0]
                
                # Количество тем
                cursor.execute('SELECT COUNT(*) FROM subtopics WHERE is_active = 1')
                topics_count = cursor.fetchone()[0]
                
                # Количество вопросов
                cursor.execute('SELECT COUNT(*) FROM questions')
                questions_count = cursor.fetchone()[0]
                
                # Количество админов
                cursor.execute('SELECT COUNT(*) FROM admins')
                admins_count = cursor.fetchone()[0]
                
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
        
        # Здесь будут вызываться методы из соответствующих модулей
        # Пока оставляем заглушку
        return False

    async def handle_admin_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка документов в админ-режиме."""
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            return
        
        # Проверяем, ожидается ли PDF файл
        if context.user_data.get('admin_action') == 'upload_pdf':
            # Здесь должна быть обработка PDF, но пока заглушка
            await update.message.reply_text("🚧 Обработка PDF файлов в разработке...")
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