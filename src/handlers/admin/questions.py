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

    # === ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ИЗ СТАРОГО ФАЙЛА ===

    async def process_pdf_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка PDF файла."""
        await update.message.reply_text("🚧 Функция обработки PDF файла в разработке...")

    async def delete_questions_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления вопросов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция подтверждения удаления вопросов в разработке...")

    async def delete_questions_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления вопросов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выполнения удаления вопросов в разработке...")

    async def add_question_topic_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор темы для добавления вопроса."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выбора темы для добавления вопроса в разработке...")

    async def handle_delete_single_question_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_text: str) -> None:
        """Обработка поиска для удаления одного вопроса."""
        await update.message.reply_text("🚧 Функция поиска для удаления одного вопроса в разработке...")

    async def delete_single_question_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления одного вопроса."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция подтверждения удаления одного вопроса в разработке...")

    async def delete_single_question_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления одного вопроса."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выполнения удаления одного вопроса в разработке...")

    async def generate_ai_explanation_for_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Генерация ИИ объяснения для редактирования."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция генерации ИИ объяснения в разработке...")

    async def manual_explanation_for_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Ручное объяснение для редактирования."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция ручного объяснения в разработке...")

    # === ОБРАБОТЧИКИ ТЕКСТА ДЛЯ ВОПРОСОВ ===

    async def handle_search_questions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_text: str) -> None:
        """Обработка поиска вопросов."""
        await update.message.reply_text("🚧 Функция поиска вопросов в разработке...")

    async def handle_add_question_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question_text: str) -> None:
        """Обработка текста вопроса."""
        await update.message.reply_text("🚧 Функция обработки текста вопроса в разработке...")

    async def handle_add_question_option_a(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option_a: str) -> None:
        """Обработка варианта A."""
        await update.message.reply_text("🚧 Функция обработки варианта A в разработке...")

    async def handle_add_question_option_b(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option_b: str) -> None:
        """Обработка варианта B."""
        await update.message.reply_text("🚧 Функция обработки варианта B в разработке...")

    async def handle_add_question_option_c(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option_c: str) -> None:
        """Обработка варианта C."""
        await update.message.reply_text("🚧 Функция обработки варианта C в разработке...")

    async def handle_add_question_option_d(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option_d: str) -> None:
        """Обработка варианта D."""
        await update.message.reply_text("🚧 Функция обработки варианта D в разработке...")

    async def handle_add_question_correct(self, update: Update, context: ContextTypes.DEFAULT_TYPE, correct_text: str) -> None:
        """Обработка правильного ответа."""
        await update.message.reply_text("🚧 Функция обработки правильного ответа в разработке...")

    async def handle_add_question_explanation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, explanation: str) -> None:
        """Обработка объяснения вопроса."""
        await update.message.reply_text("🚧 Функция обработки объяснения вопроса в разработке...")

    async def handle_edit_question_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_text: str) -> None:
        """Обработка поиска для редактирования вопроса."""
        await update.message.reply_text("🚧 Функция поиска для редактирования вопроса в разработке...")

    async def handle_edit_question_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question_id_text: str) -> None:
        """Обработка ID вопроса для редактирования."""
        await update.message.reply_text("🚧 Функция обработки ID вопроса для редактирования в разработке...")

    async def handle_edit_question_explanation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_explanation: str) -> None:
        """Обработка нового объяснения вопроса."""
        await update.message.reply_text("🚧 Функция обработки нового объяснения вопроса в разработке...") 