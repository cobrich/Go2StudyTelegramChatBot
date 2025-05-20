import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL')

# Test Configuration
DEFAULT_QUESTIONS_PER_TEST = 10
MAX_EXPLANATION_PREVIEW_LENGTH = 700
MAX_QUESTIONS_PER_TEST = 10
MAX_OPTION_LENGTH = 40

# Topics
TOPICS = [
    "Дроби",
    "Проценты",
    "Пропорции",
    "Уравнения",
    "Геометрия",
    "Логика"
]

# Menu Configuration
MAIN_MENU_KEYBOARD = [
    ["📚 Выбрать тему и начать"],
    ["📊 Мой прогресс"],
    ["❓ Помощь"]
]

# Help Text
HELP_TEXT = """
🤖 Я бот для изучения математики. Вот что я умею:

📚 Выбрать тему и начать - Начать тест по выбранной теме
📊 Мой прогресс - Посмотреть статистику ваших результатов
❓ Помощь - Показать это сообщение

Как пользоваться:
1. Выберите тему из списка
2. Отвечайте на вопросы
3. После каждого ответа вы получите объяснение
4. В конце теста увидите общий результат

Удачи в изучении математики! 🎓
""" 