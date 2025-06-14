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
        query = update.callback_query
        if query:
            await self.safe_answer_callback(query)
        
        user_id = update.effective_user.id
        
        if not self.db.is_admin(user_id):
            text = "❌ У вас нет прав администратора."
            if query:
                await query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return
        
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
        
        keyboard = [
            [InlineKeyboardButton("👥 Управление учениками", callback_data="admin_students")],
            [InlineKeyboardButton("📚 Управление темами", callback_data="admin_topics")],
            [InlineKeyboardButton("❓ Управление вопросами", callback_data="admin_questions")],
            [InlineKeyboardButton("👨‍💼 Управление админами", callback_data="admin_admins")],
            [InlineKeyboardButton("📊 Статистика и отчеты", callback_data="admin_stats")],
            [InlineKeyboardButton("🏗️ Базовая структура", callback_data="manage_base_structure")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

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
        
        action = context.user_data.get('admin_action')
        
        if action == 'upload_pdf':
            # Этот метод будет в questions.py
            pass
        else:
            await update.message.reply_text("❌ Неожиданный документ. Пожалуйста, используйте админ-панель для загрузки файлов.") 