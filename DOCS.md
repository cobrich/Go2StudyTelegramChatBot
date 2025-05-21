# Go2Study Bot Documentation

## Project Overview
Go2Study Bot is a Telegram bot designed to help students learn mathematics through interactive tests and quizzes. The bot provides a structured learning experience with immediate feedback and explanations.

## Project Structure
The project follows a modular architecture with clear separation of concerns:

```
go2study_bot/
├── src/
│   ├── bot.py                 # Main bot entry point
│   ├── config/
│   │   └── constants.py       # Configuration constants
│   ├── handlers/
│   │   ├── base_handler.py    # Base handler class
│   │   ├── callback_handlers.py # Callback query handlers
│   │   └── command_handlers.py # Command handlers
│   ├── services/
│   │   ├── ai_service.py      # AI question generation service
│   │   ├── database.py        # Database management
│   │   └── question_service.py # Question management service
│   └── utils/
│       └── keyboards.py       # Keyboard utilities
├── question_images/           # Directory for question images
└── DOCS.md                   # Project documentation
```

## Features

### User Management
- User session tracking
- Progress monitoring
- Error tracking and analysis
- Data persistence

### Question Management
- Dynamic question generation using AI
- Topic-based question organization
- Multiple-choice questions
- Detailed explanations for answers
- Support for questions with images and function graphs

### Test Flow
1. User selects a topic
2. Bot generates or retrieves questions
3. User answers questions (with support for image-based questions)
4. Immediate feedback provided
5. Results and statistics shown
6. Option to review incorrect answers

### Database Schema
- Users table: Tracks user sessions and activity
- Test results table: Stores test outcomes
- Questions table: Stores question bank (including image paths for visual questions)
- User errors table: Tracks user mistakes

## Setup and Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd go2study_bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_gemini_model
```

4. Run the bot:
```bash
python src/bot.py
```

## Recent Changes
- Added missing Update import in bot.py for proper telegram updates handling
- Added text message handler (handle_text) for ReplyKeyboardMarkup main menu buttons, so menu actions now work as expected
- 'Мой прогресс' now shows real user statistics (total tests, average, recent topics, error topics)
- Fixed topic selection: now topic index is correctly mapped to topic name, so tests by topic work as expected
- Improved test UX: robust answer handling, error handling for Telegram API, reset user state after test, and better navigation in tests
- Added: after test, user can view explanations for mistakes and repeat the topic with one click
- Now pdf_processor.py automatically adds questions from PDF files to the database (no duplicates)
- Fixed import paths in all Python files to work correctly when running from src directory
- Restructured project directory for better code organization
- Separated handlers into command and callback handlers
- Created dedicated services for AI, database, and question management
- Added keyboard utilities for better user interaction
- Implemented configuration management
- Added comprehensive documentation

## Usage

### Commands
- `/start` - Start the bot and show main menu
- `/stop` - Stop the bot and clear user data

### Main Menu Options
- 📚 Выбрать тему и начать - Start a new test
- 📊 Мой прогресс - View progress statistics
- ❓ Помощь - Show help information

## Contributing
Please follow the established project structure when adding new features or making changes.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## PDF Processor Updates
- Improved file path handling with `os.path.join` for better cross-platform compatibility
- Enhanced language detection based on both filename and content
- Updated question type detection patterns for both Russian and Kazakh
- Improved image extraction with unique filenames including page numbers
- Added better error handling and logging
- Fixed file path issues with spaces in filenames

### Language Support
- Enhanced detection of Kazakh language using:
  - Filename keywords: 'казакша', 'казахша', 'нуска'
  - Content analysis for Kazakh characters
- Improved Russian language detection for remaining files

### Question Type Detection
- Updated patterns for test questions:
  - Numbered questions with letters (both Russian and Latin)
  - Case-sensitive pattern matching
- Enhanced quantitative question detection:
  - Letter comparison patterns
  - Support for both languages

### Image Handling
- Improved image extraction with unique filenames
- Added page number to image filenames for better organization
- Enhanced error handling for image processing

## Features

### Language Support
- Support for Russian ('ru') and Kazakh ('kk') languages
- Automatic language detection based on:
  - Filename analysis
  - Content analysis
  - Character set detection

### Question Types
- Test questions:
  - Numbered questions with letter options
  - Support for both Russian and Latin letters
- Quantitative questions:
  - Letter comparison questions
  - Support for both languages

### Image Processing
- Automatic extraction of images from PDFs
- Unique image filenames including:
  - Question number
  - Original PDF filename
  - Page number
  - Image index
- Organized storage in `question_images` directory

## Usage

### Processing PDF Files
```python
processor = PDFProcessor()
questions = processor.process_pdf_file("path/to/file.pdf")
```

### Language Detection
```python
language = processor.detect_language(text, filename)
```

### Question Type Detection
```python
is_test = processor.is_test_question(text, language)
is_quantitative = processor.is_quantitative_question(text, language)
```

## Future Improvements
- Add support for more question types
- Enhance language detection accuracy
- Improve image quality and processing
- Add support for more file formats
- Implement parallel processing for large files

## Database Schema

### Users Table
- user_id: Primary key
- language: User's preferred language ('ru' or 'kk')
- other user-related fields

### Active Users Table
- user_id: Foreign key
- test_mode: Current test mode
- language: Current test language
- other active session fields

### Tasks Table
- task_id: Primary key
- language: Question language ('ru' or 'kk')
- has_image: Boolean flag
- is_test_question: Boolean flag
- question_text: The actual question
- other task-related fields

### Test History Table
- history_id: Primary key
- user_id: Foreign key
- language: Test language
- other history fields

### Errors Table
- error_id: Primary key
- user_id: Foreign key
- language: Error language
- other error tracking fields

## PDF Processing

### Supported File Types
- PDF files with questions in Russian or Kazakh
- Automatic language detection based on:
  - Filename patterns
  - Content analysis
  - Default language settings

### Question Extraction
- Automatic detection of question boundaries
- Type classification (test vs quantitative)
- Image extraction and storage
- Language-specific pattern matching
- Support for both Russian and Kazakh question formats

### Image Processing
- Automatic extraction from PDFs
- Storage in dedicated directory
- Association with questions
- Support for multiple images per question
- Language-specific image handling

## Usage

### Language Selection
Users can select their preferred language when starting the bot. The language can be changed at any time.

### Test Modes
1. Regular Test:
   - Start with /start
   - Select language
   - Begin test
   - Questions delivered in selected language

2. Error-Focused Test:
   - Start with /start
   - Select language
   - Choose error-focused mode
   - Begin practice
   - Language-specific error tracking

### Question Types
- Test questions are automatically detected and categorized
- Quantitative questions are stored separately
- Questions with images are preserved with their images
- Language-specific patterns are used for classification
- Support for both Russian and Kazakh question formats

## Future Improvements
- Enhanced language detection accuracy
- More sophisticated question categorization
- Improved image handling
- Additional test modes
- Performance analytics
- Topic-based question organization
- Support for additional languages
- Better handling of mixed-language content

### [2024-06-09] Обновление списка обрабатываемых файлов

- Удален файл Абай_рус.pdf из списка обрабатываемых PDF файлов
- Теперь обрабатываются только основные математические тесты:
  - Колич характ (рус).pdf
  - Математика,_10_вариантов,_на_русском.pdf
  - Математика, 10 нуска, казакша.pdf

### [2024-06-09] Удаление лишних тестовых файлов

- Удален файл test_pdf_processor_final2.py, так как он был дублирующим и больше не нужен
- Оставлены только основные тестовые файлы для обработки PDF

### [2024-06-09] Улучшение определения тем для вопросов из PDF
- Добавлено автоматическое определение тем для вопросов из PDF файлов на основе ключевых слов
- Вопросы теперь сохраняются с конкретными темами из constants.py вместо общей темы "Математика"
- Добавлен словарь соответствия ключевых слов темам для более точной классификации
- Если тема не определена, используется общая тема "Математика"

### [2024-06-09] Улучшение логики выбора вопросов для теста

- Изменена логика выбора вопросов для теста:
  1. Сначала берутся обычные вопросы из базы данных
  2. Если у ученика есть неправильно отвеченные вопросы по теме, они добавляются к тесту
  3. Если после этого не хватает вопросов, генерируются новые вопросы с помощью ИИ:
     - Если есть неправильно отвеченные вопросы, ИИ генерирует похожие вопросы для лучшего освоения темы
     - Если неправильно отвеченных вопросов нет, генерируются новые вопросы по теме
- Это позволяет:
  - Всегда иметь вопросы для теста, даже если нет ошибок
  - Приоритизировать неправильно отвеченные вопросы
  - Генерировать похожие вопросы для лучшего освоения проблемных тем
  - Обеспечить разнообразие вопросов в тесте 

### [2024-06-10] AI-based Topic Detection for PDF Questions
- Replaced keyword-based topic detection in PDF processing with Gemini AI-based classification.
- Now, when processing PDF files, each question is sent to Gemini, which selects the most appropriate topic from the predefined list (`constants.TOPICS`).
- If the AI cannot determine a specific topic, it defaults to 'Математика'.
- This ensures more accurate and robust topic categorization for all imported questions.

#### Workflow
- For each question extracted from a PDF, the system:
    1. Sends the question text to Gemini with a prompt listing all available topics.
    2. Receives the topic name from Gemini (or 'Математика' if ambiguous).
    3. Saves the question to the database with the AI-determined topic.
- This improves the reliability of topic assignment and reduces errors from manual or keyword-based methods. 

## Changelog

### [Date: YYYY-MM-DD] (replace with today's date)

#### Major Fixes & Features

- **Import Path Refactor:**  
  All Python import paths were updated to work when running `bot.py` from the `src` directory. The `src.` prefix was removed from all internal imports.

- **Menu Button Handling:**  
  Added a text message handler to process menu button presses (ReplyKeyboardMarkup), enabling actions for options like "Мой прогресс".

- **User Progress Statistics:**  
  Implemented real user progress stats for the "Мой прогресс" menu option, including total tests, average score, recent topics, and error topics.

- **Test Flow Improvements:**  
  - Fixed topic selection logic and improved error handling.
  - Enhanced test flow robustness, including Telegram API error handling.
  - Added explanations for mistakes after tests and an option to repeat topics.

- **Database & PDF Import:**  
  - Improved `pdf_processor.py` to import questions from PDF into the database only if they don't already exist.
  - Ensured all project components use the same `math_bot.db` file.

- **Question Source Tracking:**  
  - Added a feature to mark each question as coming from either the database or AI (Gemini).
  - Displayed the source to users during tests and explanations.

- **/stop Command Enhancement:**  
  - `/stop` now always resets user state and activity, preventing stale sessions from blocking new tests.

- **Documentation & Version Control:**  
  - Updated `DOCS.md` after each major change.
  - Committed all major changes to git for transparency and version tracking.

---

**The bot is now fully functional with robust error handling, clear user feedback, reliable question sourcing, and seamless PDF-to-database import.** 

## [FIX] Navigation Buttons (Продолжить, Предыдущий, Следующий)
- Added missing callback query handlers for 'prev_question', 'next_question', and 'continue_test' in bot.py.
- Implemented `handle_prev_question` and `handle_next_question` in `CallbackHandlers` to allow users to move between questions during a test.
- Now, the navigation buttons work as expected during the test flow. 

## [UX] Main menu buttons disabled during test
- Теперь во время прохождения теста кнопки главного меню неактивны.
- Если пользователь пытается нажать на "Мой прогресс" или "Помощь" во время теста, он получает сообщение, что нужно завершить тест или вернуться к темам.
- Это предотвращает наложение меню и теста, и делает UX чище. 

## [BUGFIX] Progress: error topics display
- Исправлено: теперь в разделе прогресса темы с ошибками отображаются корректно (например: Дроби (2), Проценты (1)), а не возникает ошибка типов. 

## [BUGFIX] Test flow: 'Продолжить' button
- Исправлено: теперь данные пользователя очищаются только после показа результатов теста, а не после каждого ответа.
- Кнопка 'Продолжить' теперь работает корректно, вопросы не теряются между переходами. 

## PDF Processing Updates (2024-03-21)

### Changes Made:
1. Moved PDF processor to `src/services/pdf_processor.py` for better code organization
2. Modified PDF processor to focus on processing only NIS.pdf file
3. Added topic extraction from PDF content
4. Improved question extraction with topic association
5. Updated database integration to store topics from PDF

### New Features:
- Automatic topic detection from PDF headers
- Questions are now associated with their respective topics from the PDF
- Improved language detection for Russian and Kazakh content
- Better error handling and logging

### Usage:
To process NIS.pdf and add questions to the database:
```bash
python -m src.services.pdf_processor
```

The processor will:
1. Extract questions from NIS.pdf
2. Detect topics from PDF headers
3. Associate questions with their topics
4. Save questions to the database
5. Log added questions to added_questions.log 

## [2024-03-21] Topics Update

### Changes Made:
1. Updated topics list in `constants.py` to match NIS.pdf content:
   - Added new topics: АЛГЕБРА, ТРИГОНОМЕТРИЯ, СТЕРЕОМЕТРИЯ, КОМБИНАТОРИКА, ТЕОРИЯ ВЕРОЯТНОСТЕЙ, СТАТИСТИКА, МАТЕМАТИЧЕСКИЙ АНАЛИЗ
   - Removed old topics: Дроби, Проценты, Пропорции, Уравнения
   - Kept existing topics: ГЕОМЕТРИЯ, ЛОГИКА
2. Topics are now in uppercase to match the PDF format
3. Topics are more comprehensive and aligned with the NIS curriculum

### Impact:
- Better alignment with NIS curriculum
- More accurate topic categorization for questions
- Improved user experience with standardized topic names 

## [2024-06-11] Темы обновлены по содержанию NIS.pdf

### Изменения:
- Список TOPICS в constants.py теперь соответствует темам из содержания NIS.pdf:
  1. Соотношение и пропорция
  2. Масштаб и процент
  3. Арифметика, модуль числа и уравнения
  4. Система уравнений
  5. Текстовые задачи
  6. Выражения
  7. Неравенства
  8. Логические задачи
  9. Функция
  10. Круг и окружность
- Старые темы удалены.
- Теперь вопросы будут категоризироваться строго по этим темам. 

## 2024-05-21
- Теперь пользователь регистрируется в базе данных при /start, включая username.
- Добавлен метод `register_user` в `Database` и вызов в `CommandHandlers.start`. 

- Теперь при выборе темы главная клавиатура скрывается (ReplyKeyboardRemove), чтобы пользователь видел только inline-кнопки выбора темы. 

- Исправлен порядок скрытия клавиатуры — теперь сначала убирается главная клавиатура, затем показываются inline-кнопки выбора темы. Это гарантирует, что кнопки главного меню не видны во время выбора темы. 

- Исправлена ошибка Telegram (BadRequest: Text must be non-empty) — теперь при скрытии клавиатуры отправляется техническое сообщение 'Пожалуйста, выберите тему ниже:'. 

- Исправлено формирование вариантов ответа для вопросов из базы — теперь варианты собираются из правильного и неправильных ответов, корректно отображаются в inline-кнопках.

- Исправлена ошибка с tuple indices must be integers or slices, not str при переходе по кнопке 'Продолжить'. Теперь тема берётся из user_data, а не из question. Исправлена обработка callback_data для ответов.

- Улучшен промпт для ИИ при нормализации вопросов из PDF — теперь ИИ фильтрует мусорные вопросы, восстанавливает переменные, не добавляет нечитабельные задачи. Добавлена фильтрация: в базу не попадают вопросы без переменных/чисел или с пустым JSON от Gemini.

- Добавлен метод add_question в Database для корректного добавления вопросов в базу из PDF/ИИ.

- Исправлена работа кнопки 'В главное меню' — теперь при нажатии на кнопку 'В главное меню' сначала удаляется inline-клавиатура, затем отправляется новое сообщение с главным меню (обычная клавиатура). Это устраняет ошибку 400 Bad Request и делает возврат в главное меню стабильным.