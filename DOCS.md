# Go2Study Bot Documentation

## Project Overview
Go2Study Bot is a Telegram bot designed to help students learn mathematics through interactive tests and quizzes. The bot provides a structured learning experience with immediate feedback and explanations.

## Project Structure
```
go2study_bot/
├── src/
│   ├── config/
│   │   └── constants.py         # Configuration and constants
│   ├── handlers/
│   │   ├── base_handler.py     # Base handler class
│   │   ├── command_handlers.py # Command handlers (/start, /stop)
│   │   └── callback_handlers.py # Callback query handlers
│   ├── services/
│   │   ├── database.py         # Database operations
│   │   ├── ai_service.py       # AI question generation
│   │   └── question_service.py # Question management
│   ├── utils/
│   │   └── keyboards.py        # Keyboard utilities
│   └── bot.py                  # Main bot file
├── files/                      # Additional files
├── question_images/           # Question-related images
├── requirements.txt           # Project dependencies
└── DOCS.md                    # This documentation file
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

### Test Flow
1. User selects a topic
2. Bot generates or retrieves questions
3. User answers questions
4. Immediate feedback provided
5. Results and statistics shown
6. Option to review incorrect answers

### Database Schema
- Users table: Tracks user sessions and activity
- Test results table: Stores test outcomes
- Questions table: Stores question bank
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

### Project Restructuring
- Reorganized code into logical modules
- Separated concerns into different services
- Improved code maintainability
- Enhanced error handling

### New Features
- Improved question generation using AI
- Better error tracking and analysis
- Enhanced user progress monitoring
- More detailed explanations for answers

### Technical Improvements
- Modular architecture
- Better separation of concerns
- Improved error handling
- Enhanced logging
- More efficient database operations

## Usage

### Commands
- `/start` - Start the bot and show main menu
- `/stop` - Stop the bot and clear user data

### Main Menu Options
- 📚 Выбрать тему и начать - Start a new test
- 📊 Мой прогресс - View progress statistics
- ❓ Помощь - Show help information

## Contributing
Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

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