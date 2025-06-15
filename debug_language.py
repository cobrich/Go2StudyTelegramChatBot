#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import Database
from utils.translations import get_message

def debug_user_language():
    """Отладка проблемы с языком пользователя"""
    
    # Создаем экземпляр базы данных
    db = Database()
    
    # ID пользователя из скриншота
    user_id = 1117916124
    
    print("=== ОТЛАДКА ЯЗЫКА ПОЛЬЗОВАТЕЛЯ ===")
    print(f"User ID: {user_id}")
    
    # Получаем информацию о пользователе из разных таблиц
    user_info = db.get_user_info(user_id)
    print(f"User info from users table: {user_info}")
    
    # Получаем информацию из allowed_users
    allowed_user_info = db.get_allowed_user_by_id(user_id)
    print(f"User info from allowed_users table: {allowed_user_info}")
    
    # Получаем язык пользователя
    user_language = db.get_user_language(user_id)
    print(f"User language from get_user_language(): {user_language}")
    
    # Проверяем, есть ли расхождения
    if user_info and len(user_info) > 2:
        users_language = user_info[2]  # language из users
        print(f"Language from users table: {users_language}")
    
    if allowed_user_info and 'language' in allowed_user_info:
        allowed_language = allowed_user_info['language']
        print(f"Language from allowed_users table: {allowed_language}")
        
        # Проверяем расхождение
        if user_language != allowed_language:
            print(f"⚠️  РАСХОЖДЕНИЕ! users.language='{user_language}' vs allowed_users.language='{allowed_language}'")
    
    # Тестируем переводы
    print("\n=== ТЕСТИРОВАНИЕ ПЕРЕВОДОВ ===")
    
    # Тестируем random_test_question
    ru_message = get_message('random_test_question', 'ru', current=1, total=6, question='Тестовый вопрос')
    kk_message = get_message('random_test_question', 'kk', current=1, total=6, question='Тестовый вопрос')
    user_message = get_message('random_test_question', user_language, current=1, total=6, question='Тестовый вопрос')
    
    print(f"RU message: {repr(ru_message)}")
    print(f"KK message: {repr(kk_message)}")
    print(f"User message: {repr(user_message)}")
    
    # Проверяем, совпадает ли пользовательское сообщение с русским
    print(f"\nUser message == RU message: {user_message == ru_message}")
    print(f"User message == KK message: {user_message == kk_message}")
    
    # Проверяем, что происходит если мы принудительно используем казахский
    if allowed_user_info and 'language' in allowed_user_info:
        allowed_language = allowed_user_info['language']
        if allowed_language != user_language:
            print(f"\n=== ТЕСТ С ЯЗЫКОМ ИЗ ALLOWED_USERS ({allowed_language}) ===")
            allowed_message = get_message('random_test_question', allowed_language, current=1, total=6, question='Тестовый вопрос')
            print(f"Message with allowed_users language: {repr(allowed_message)}")
    
    # Тестируем другие сообщения
    print("\n=== ДРУГИЕ СООБЩЕНИЯ ===")
    
    preparing_ru = get_message('preparing_random_test', 'ru')
    preparing_kk = get_message('preparing_random_test', 'kk')
    preparing_user = get_message('preparing_random_test', user_language)
    
    print(f"Preparing RU: {repr(preparing_ru)}")
    print(f"Preparing KK: {repr(preparing_kk)}")
    print(f"Preparing User: {repr(preparing_user)}")
    
    # Проверяем topic_question
    topic_ru = get_message('topic_question', 'ru', topic='Тест', current=1, total=6, question='Вопрос')
    topic_kk = get_message('topic_question', 'kk', topic='Тест', current=1, total=6, question='Вопрос')
    topic_user = get_message('topic_question', user_language, topic='Тест', current=1, total=6, question='Вопрос')
    
    print(f"\nTopic RU: {repr(topic_ru)}")
    print(f"Topic KK: {repr(topic_kk)}")
    print(f"Topic User: {repr(topic_user)}")
    
    # Проверяем, есть ли проблема с кэшированием в keyboards.py
    print("\n=== ПРОВЕРКА КЭШИРОВАНИЯ ===")
    from utils.keyboards import _db as keyboards_db
    keyboards_language = keyboards_db.get_user_language(user_id)
    print(f"Language from keyboards._db: {keyboards_language}")
    
    if keyboards_language != user_language:
        print(f"⚠️  ПРОБЛЕМА С КЭШИРОВАНИЕМ! main_db='{user_language}' vs keyboards_db='{keyboards_language}'")

if __name__ == "__main__":
    debug_user_language() 