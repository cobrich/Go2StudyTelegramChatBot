# Go2Study Bot Documentation

## Recent Changes

### PDF Processor Updates
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