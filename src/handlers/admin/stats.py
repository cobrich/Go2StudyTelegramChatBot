"""
Модуль для статистики в админ-панели.
Включает общую статистику, отчеты, историю пользователей.
"""

from .base import AdminBaseHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sqlite3
import logging
from datetime import datetime, timedelta

class StatsHandler(AdminBaseHandler):
    """Обработчик для статистики."""

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать общую статистику системы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Общая статистика
                cursor.execute('SELECT COUNT(*) FROM allowed_users WHERE is_active = 1')
                active_students = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM questions')
                total_questions = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(DISTINCT topic) FROM questions')
                unique_topics = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM test_results')
                total_tests = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM admins')
                total_admins = cursor.fetchone()[0]
                
                # Статистика за последние 7 дней
                week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                cursor.execute('SELECT COUNT(*) FROM test_results WHERE timestamp >= ?', (week_ago,))
                tests_last_week = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(DISTINCT user_id) FROM test_results WHERE timestamp >= ?', (week_ago,))
                active_users_week = cursor.fetchone()[0]
                
                # Средний балл (используем percentage вместо score)
                cursor.execute('SELECT AVG(percentage) FROM test_results')
                avg_score_result = cursor.fetchone()[0]
                avg_score = round(avg_score_result, 1) if avg_score_result else 0
                
                # Топ-5 активных пользователей
                cursor.execute('''
                    SELECT tr.topic, COUNT(*) as test_count, AVG(tr.percentage) as avg_score,
                           au.full_name, au.grade
                    FROM test_results tr
                    LEFT JOIN allowed_users au ON tr.user_id = au.user_id
                    WHERE tr.timestamp >= ?
                    GROUP BY tr.topic, au.full_name, au.grade
                    ORDER BY test_count DESC
                    LIMIT 10
                ''', (week_ago,))
                top_topics = cursor.fetchall()
                
                cursor.execute('''
                    SELECT tr.user_id, au.full_name, au.grade, COUNT(*) as test_count, 
                           AVG(tr.percentage) as avg_score
                    FROM test_results tr
                    LEFT JOIN allowed_users au ON tr.user_id = au.user_id
                    WHERE tr.timestamp >= ?
                    GROUP BY tr.user_id, au.full_name, au.grade
                    ORDER BY test_count DESC
                    LIMIT 10
                ''', (week_ago,))
                top_users = cursor.fetchall()
                
                text = f"📊 <b>Общая статистика системы</b>\n\n"
                text += f"👥 <b>Пользователи:</b>\n"
                text += f"• Активных учеников: {active_students}\n"
                text += f"• Админов: {total_admins}\n\n"
                
                text += f"❓ <b>Контент:</b>\n"
                text += f"• Всего вопросов: {total_questions}\n"
                text += f"• Уникальных тем: {unique_topics}\n\n"
                
                text += f"📈 <b>Активность:</b>\n"
                text += f"• Всего тестов: {total_tests}\n"
                text += f"• Тестов за неделю: {tests_last_week}\n"
                text += f"• Активных за неделю: {active_users_week}\n"
                text += f"• Средний балл: {avg_score}%\n\n"
                
                if top_topics:
                    text += f"🏆 <b>Топ-5 тем:</b>\n"
                    for i, (topic, test_count, avg_score, full_name, grade) in enumerate(top_topics, 1):
                        text += f"{i}. <b>{topic}</b>\n"
                        text += f"   📅 {grade}\n"
                        text += f"   �� {avg_score}%\n\n"
                
                if top_users:
                    text += f"🏆 <b>Топ-5 активных учеников:</b>\n"
                    for i, (user_id, full_name, grade, test_count, avg_score) in enumerate(top_users, 1):
                        text += f"{i}. <b>{full_name}</b>\n"
                        text += f"   📅 {grade}\n"
                        text += f"   📊 {avg_score}%\n\n"
                
        except Exception as e:
            logging.error(f"Error getting general stats: {e}")
            text = "❌ Ошибка при получении статистики."
            
        
        keyboard = [
            [InlineKeyboardButton("📋 История пользователей", callback_data="admin_user_history")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def show_user_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать историю активности пользователей."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Последние 20 тестов
                cursor.execute('''
                    SELECT 
                        tr.timestamp, 
                        au.full_name,
                        au.username,
                        tr.user_id,
                        tr.topic, 
                        tr.percentage
                    FROM test_results tr
                    LEFT JOIN allowed_users au ON tr.user_id = au.user_id
                    ORDER BY tr.timestamp DESC
                    LIMIT 20
                ''')
                recent_tests = cursor.fetchall()
                
                if not recent_tests:
                    text = "📋 <b>История активности</b>\n\nТестов не найдено."
                else:
                    text = f"📋 <b>История активности</b>\n\n"
                    text += f"Последние 20 тестов:\n\n"
                    
                    for i, (timestamp, full_name, username, user_id, topic, percentage) in enumerate(recent_tests, 1):
                        # Исправленная логика определения имени
                        if full_name:
                            name = full_name
                        elif username:
                            name = f"@{username}"
                        else:
                            name = f"Пользователь {user_id}"  # Используем user_id вместо номера в списке
                        date_str = timestamp[:16] if timestamp else "н/д"
                        
                        text += f"{i}. <b>{name}</b>\n"
                        text += f"   📅 {date_str}\n"
                        text += f"   📚 {topic}\n"
                        text += f"   📊 {percentage}%\n\n"
                
        except Exception as e:
            logging.error(f"Error getting user history: {e}")
            text = "❌ Ошибка при получении истории."
        
        keyboard = [
            [InlineKeyboardButton("📊 Общая статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML') 