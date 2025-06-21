"""
Модуль для статистики в админ-панели.
Включает общую статистику, отчеты, историю пользователей.
"""

from .base import AdminBaseHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import logging
from datetime import datetime, timedelta

class StatsHandler(AdminBaseHandler):
    """Обработчик для статистики."""

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать общую статистику системы."""
        query = update.callback_query
        await self.safe_answer_callback(query)
        
        try:
            # Используем database facade вместо прямого SQLite подключения
            
            # Общая статистика
            all_users = self.db.get_all_allowed_users()
            active_students = len([u for u in all_users if u.get('has_access')])
            
            all_questions = self.db.get_all_questions()
            total_questions = len(all_questions)
            
            all_topics = self.db.get_all_topics()
            unique_topics = len(all_topics)
            
            # Общая статистика - только тесты учеников
            # Получаем все результаты тестов через facade
            all_test_results = []
            for user in all_users:
                user_results = self.db.get_user_test_results(user['user_id'])
                all_test_results.extend(user_results)
            total_tests = len(all_test_results)
            
            all_admins = self.db.get_all_admins()
            total_admins = len(all_admins)
            
            # Статистика за последние 7 дней - только ученики
            week_ago = datetime.now() - timedelta(days=7)
            tests_last_week = 0
            active_users_week = set()
            
            for user in all_users:
                user_results = self.db.get_user_test_results(user['user_id'])
                for result in user_results:
                    try:
                        # Парсим дату из результата
                        result_date = datetime.fromisoformat(result.get('timestamp', '1970-01-01'))
                        if result_date >= week_ago:
                            tests_last_week += 1
                            active_users_week.add(user['user_id'])
                    except (ValueError, TypeError):
                        continue
            
            active_users_week = len(active_users_week)
            
            # Средний балл - только ученики
            if all_test_results:
                avg_score = sum(result.get('percentage', 0) for result in all_test_results) / len(all_test_results)
                avg_score = round(avg_score, 1)
            else:
                avg_score = 0
            
            # Топ активные темы и пользователи (упрощенная версия)
            # Для полной реализации потребуется расширить database facade
            
            text = f"📊 <b>Общая статистика системы</b>\n\n"
            text += f"👥 <b>Пользователи:</b>\n"
            text += f"• Активных учеников: {active_students}\n"
            text += f"• Админов: {total_admins}\n\n"
            
            text += f"❓ <b>Контент:</b>\n"
            text += f"• Всего вопросов: {total_questions}\n"
            text += f"• Уникальных тем: {unique_topics}\n\n"
            
            text += f"📈 <b>Активность учеников:</b>\n"
            text += f"• Всего тестов учеников: {total_tests}\n"
            text += f"• Тестов за неделю: {tests_last_week}\n"
            text += f"• Активных учеников за неделю: {active_users_week}\n"
            text += f"• Средний балл учеников: {avg_score}%\n\n"
                
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
            # Используем database facade вместо прямого SQLite подключения
            all_users = self.db.get_all_allowed_users()
            
            # Собираем последние 20 тестов
            recent_tests = []
            for user in all_users:
                user_results = self.db.get_user_test_results(user['user_id'])
                for result in user_results:
                    recent_tests.append({
                        'timestamp': result.get('timestamp'),
                        'full_name': user.get('full_name'),
                        'username': user.get('username'),
                        'user_id': user['user_id'],
                        'topic': result.get('topic'),
                        'percentage': result.get('percentage')
                    })
            
            # Сортируем по времени (новые сначала) и берем первые 20
            recent_tests.sort(key=lambda x: x['timestamp'] or '1970-01-01', reverse=True)
            recent_tests = recent_tests[:20]
            
            if not recent_tests:
                text = "📋 <b>История активности</b>\n\nТестов не найдено."
            else:
                text = f"📋 <b>История активности</b>\n\n"
                text += f"Последние 20 тестов учеников:\n\n"
                
                for i, test in enumerate(recent_tests, 1):
                    if test['full_name']:
                        name = test['full_name']
                    elif test['username']:
                        name = f"@{test['username']}"
                    else:
                        name = f"Ученик {test['user_id']}"
                    
                    timestamp = test['timestamp']
                    date_str = timestamp[:16] if timestamp else "н/д"
                    
                    text += f"{i}. <b>{name}</b>\n"
                    text += f"   📅 {date_str}\n"
                    text += f"   📚 {test['topic']}\n"
                    text += f"   📊 {test['percentage']}%\n\n"
                
        except Exception as e:
            logging.error(f"Error getting user history: {e}")
            text = "❌ Ошибка при получении истории."
        
        keyboard = [
            [InlineKeyboardButton("📊 Общая статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML') 