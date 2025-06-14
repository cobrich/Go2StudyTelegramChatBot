"""
Модуль для управления темами в админ-панели.
Включает добавление, редактирование, удаление тем и слияние тем.
"""

from .base import AdminBaseHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sqlite3
import logging

class TopicsHandler(AdminBaseHandler):
    """Обработчик для управления темами."""

    async def topics_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Меню управления темами."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        text = f"📚 <b>Управление темами</b>\n\nВыберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить тему", callback_data="add_topic")],
            [InlineKeyboardButton("📋 Список тем", callback_data="list_topics")],
            [InlineKeyboardButton("✏️ Редактировать тему", callback_data="edit_topic_start")],
            [InlineKeyboardButton("🔄 Объединить темы", callback_data="merge_topics")],
            [InlineKeyboardButton("🗑️ Удалить тему", callback_data="remove_topic")],
            [InlineKeyboardButton("📊 Статистика тем", callback_data="detailed_topics_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

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

    async def list_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Список всех тем с количеством вопросов."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        topics = self.db.get_all_topics(active_only=False)
        
        if not topics:
            text = "📋 <b>Список тем</b>\n\nТемы не найдены."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]]
        else:
            # Группируем темы по основным разделам
            topics_by_section = {}
            for topic in topics:
                main_topic = topic.get('main_topic', 'Без раздела')
                if main_topic not in topics_by_section:
                    topics_by_section[main_topic] = []
                topics_by_section[main_topic].append(topic)
            
            text = f"📋 <b>Список тем</b>\n\n"
            text += f"Всего тем: {len(topics)}\n\n"
            
            for main_topic, section_topics in topics_by_section.items():
                text += f"📚 <b>{main_topic}</b> ({len(section_topics)} тем)\n"
                
                # Сортируем темы: сначала активные, потом неактивные
                active_topics = [t for t in section_topics if t['is_active']]
                inactive_topics = [t for t in section_topics if not t['is_active']]
                
                for topic in active_topics:
                    status = "✅"
                    text += f"  {status} {topic['name']} ({topic['question_count']} вопросов)\n"
                
                for topic in inactive_topics:
                    status = "❌"
                    text += f"  {status} {topic['name']} ({topic['question_count']} вопросов)\n"
                
                text += "\n"
            
            keyboard = [
                [InlineKeyboardButton("📊 Детальная статистика", callback_data="detailed_topics_stats")],
                [InlineKeyboardButton("🔄 Обновить статистику", callback_data="refresh_topics_stats")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_topics")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    # === ВРЕМЕННЫЕ ЗАГЛУШКИ ДЛЯ СОВМЕСТИМОСТИ ===
    
    async def add_custom_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для добавления пользовательской темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция добавления пользовательских тем в разработке...")

    async def add_base_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для добавления базовых тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция добавления базовых тем в разработке...")

    async def edit_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для редактирования тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция редактирования тем в разработке...")

    async def merge_topics_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для слияния тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция слияния тем в разработке...")

    async def remove_topic_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Временная заглушка для удаления тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция удаления тем в разработке...")

    async def detailed_topics_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Детальная статистика по темам."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем статистику по темам
                cursor.execute('''
                    SELECT 
                        s.name as topic_name,
                        s.main_topic,
                        s.is_active,
                        COUNT(q.id) as question_count,
                        COUNT(DISTINCT tr.user_id) as unique_users,
                        COUNT(tr.id) as total_tests,
                        ROUND(AVG(tr.score), 1) as avg_score
                    FROM subtopics s
                    LEFT JOIN questions q ON s.name = q.topic
                    LEFT JOIN test_results tr ON s.name = tr.topic
                    GROUP BY s.name, s.main_topic, s.is_active
                    ORDER BY s.main_topic, s.name
                ''')
                
                stats = cursor.fetchall()
                
                if not stats:
                    text = "📊 <b>Детальная статистика тем</b>\n\nДанных нет."
                else:
                    text = "📊 <b>Детальная статистика тем</b>\n\n"
                    
                    # Группируем по разделам
                    current_section = None
                    total_questions = 0
                    total_tests = 0
                    
                    for stat in stats:
                        topic_name, main_topic, is_active, question_count, unique_users, total_tests_topic, avg_score = stat
                        
                        if main_topic != current_section:
                            if current_section is not None:
                                text += "\n"
                            text += f"📚 <b>{main_topic or 'Без раздела'}</b>\n"
                            current_section = main_topic
                        
                        status = "✅" if is_active else "❌"
                        text += f"  {status} <b>{topic_name}</b>\n"
                        text += f"    • Вопросов: {question_count}\n"
                        text += f"    • Уникальных пользователей: {unique_users}\n"
                        text += f"    • Всего тестов: {total_tests_topic}\n"
                        if avg_score:
                            text += f"    • Средний балл: {avg_score}%\n"
                        text += "\n"
                        
                        total_questions += question_count
                        total_tests += total_tests_topic
                    
                    text += f"📈 <b>Общая статистика:</b>\n"
                    text += f"• Всего вопросов: {total_questions}\n"
                    text += f"• Всего тестов: {total_tests}\n"
                
        except Exception as e:
            logging.error(f"Error getting topics stats: {e}")
            text = "❌ Ошибка при получении статистики."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="detailed_topics_stats")],
            [InlineKeyboardButton("🔙 Назад к списку", callback_data="list_topics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def refresh_topics_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обновить статистику тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        # Просто перенаправляем на список тем для обновления
        await self.list_topics(update, context)

    # === ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ИЗ СТАРОГО ФАЙЛА ===

    async def select_main_topic_for_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор основной темы для новой подтемы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выбора основной темы в разработке...")

    async def show_section_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать темы в разделе."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция просмотра тем раздела в разработке...")

    async def add_base_topics_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало добавления базовых тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция добавления базовых тем в разработке...")

    async def add_base_topic_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение добавления базовой темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выполнения добавления базовой темы в разработке...")

    async def add_all_missing_topics_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Добавление всех отсутствующих тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция добавления всех отсутствующих тем в разработке...")

    async def edit_topic_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор темы для редактирования."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выбора темы для редактирования в разработке...")

    async def edit_topic_name_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало редактирования названия темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция редактирования названия темы в разработке...")

    async def edit_topic_desc_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало редактирования описания темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция редактирования описания темы в разработке...")

    async def edit_topic_toggle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Переключение статуса темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция переключения статуса темы в разработке...")

    async def remove_topic_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция подтверждения удаления темы в разработке...")

    async def remove_topic_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение удаления темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выполнения удаления темы в разработке...")

    async def merge_topics_select_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выбор целевой темы для слияния."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выбора целевой темы для слияния в разработке...")

    async def merge_topics_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение слияния тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция подтверждения слияния тем в разработке...")

    async def merge_topics_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выполнение слияния тем."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция выполнения слияния тем в разработке...")

    async def remove_topic_permanent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Постоянное удаление темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция постоянного удаления темы в разработке...")

    async def remove_topic_permanent_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение постоянного удаления темы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        await query.edit_message_text("🚧 Функция подтверждения постоянного удаления темы в разработке...")

    # === ОБРАБОТЧИКИ ТЕКСТА ДЛЯ ТЕМ ===

    async def handle_add_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE, topic_name: str) -> None:
        """Обработка добавления темы."""
        await update.message.reply_text("🚧 Функция добавления темы в разработке...")

    async def handle_topic_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, description: str) -> None:
        """Обработка описания темы."""
        await update.message.reply_text("🚧 Функция обработки описания темы в разработке...")

    async def handle_edit_topic_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_name: str) -> None:
        """Обработка изменения названия темы."""
        await update.message.reply_text("🚧 Функция изменения названия темы в разработке...")

    async def handle_edit_topic_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_description: str) -> None:
        """Обработка изменения описания темы."""
        await update.message.reply_text("🚧 Функция изменения описания темы в разработке...") 