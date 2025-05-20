# Go2Study Bot Documentation

## Recent Changes

### PDF Processor Updates (2024-03-XX)
- Enhanced language detection for Kazakh and Russian files
- Added support for Kazakh-specific question patterns
- Improved file naming detection for language identification
- Added language-specific statistics tracking
- Updated test script to handle language-specific files

### Language Support
- The bot now correctly identifies and processes both Russian and Kazakh files
- Language detection based on:
  - Filename patterns (e.g., "казакша", "нуска" for Kazakh)
  - Content analysis for Kazakh characters
  - Default to Russian if no Kazakh indicators found
- Questions are properly categorized by language in the database

### Question Types
- Test questions (multiple choice)
- Quantitative questions (comparison-based)
- Support for questions with images
- Automatic categorization of questions by type
- Language-specific pattern matching for question types

### Test Modes
1. Regular Test Mode
   - Questions from the database
   - Random selection
   - Progress tracking
   - Language-specific question delivery

2. Error-Focused Test Mode
   - Questions based on previous mistakes
   - Topic-specific practice
   - Performance analytics
   - Language-specific error tracking

### Image Handling
- Automatic extraction of images from PDFs
- Storage of image paths in database
- Support for questions with and without images
- Language-specific image association

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