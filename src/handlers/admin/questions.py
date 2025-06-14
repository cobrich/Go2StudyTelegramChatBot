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
                
                cursor.execute('SELECT COUNT(DISTINCT topic) FROM questions')
                unique_topics = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM questions WHERE explanation IS NOT NULL AND explanation != ""')
                questions_with_explanations = cursor.fetchone()[0]
                
                # Статистика по темам
                cursor.execute('''
                    SELECT topic, COUNT(*) as count 
                    FROM questions 
                    GROUP BY topic 
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
            [InlineKeyboardButton("🔄 Обновить", callback_data="questions_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_questions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    # === ВРЕМЕННЫЕ ЗАГЛУШКИ ДЛЯ СОВМЕСТИМОСТИ ===
    
    async def add_question_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для добавления вопроса."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция добавления вопросов в разработке...")

    async def edit_question_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для редактирования вопроса."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция редактирования вопросов в разработке...")

    async def search_questions_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для поиска вопросов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция поиска вопросов в разработке...")

    async def delete_questions_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для удаления вопросов по теме."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция удаления вопросов по теме в разработке...")

    async def delete_single_question_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для удаления одного вопроса."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция удаления одного вопроса в разработке...") 