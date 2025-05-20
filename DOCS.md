# Go2Study Bot Documentation

## Recent Changes

### [2024-05-20] Database Schema Update
- Recreated the tasks table to ensure proper support for image-based questions
- Added support for storing image paths and quantitative characteristics
- Fixed issue with missing image_path column in tasks table

### [2024-05-20] Bot Initialization Fix
- Added `application.bot.initialize()` call before running the bot
- This resolves the "ExtBot was not initialized properly" error

### [2024-05-20] Added Questions from PDF Files
- Processed PDF files containing math problems
- Added 1782 questions to the database:
  - 1382 questions with images
  - 400 questions without images
- Questions are available for testing in the "Математика" topic

## Features

### Question Types and Image Support

#### Two types of questions are supported:
1. Standard questions - text-based questions with answer options
2. Quantitative questions - questions comparing two characteristics (A and B) with A, B, C, D answer options

#### Image Support:
- Ability to attach images to questions
- Images are extracted from PDF files and stored locally
- When displaying a question with an image, it is sent as a photo with the question text as a caption

### Database Changes:
- New fields added to the tasks table:
  - question_type: type of question (standard/quantitative)
  - image_path: path to the question image
  - characteristic_a: characteristic A for quantitative questions
  - characteristic_b: characteristic B for quantitative questions
  - source_file: source file from which the question was extracted

### PDF Processing:
- Created new module pdf_processor.py for extracting questions and images from PDFs
- Supports extraction of both standard and quantitative questions
- Images are saved in a separate directory for each PDF file

### Dependencies:
- Pillow (PIL) 11.2.1 - for processing images from PDF files

## Setup and Running Instructions

1. **Clone the repository (if applicable).**

2. **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # venv\Scripts\activate    # Windows
    ```

3. **Install dependencies:**
    ```bash
    pip install python-telegram-bot google-generativeai python-dotenv Pillow
    ```

4. **Configure Environment Variables:**
    Create a `.env` file in the project root with your API keys:
    ```env
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    GEMINI_API_KEY="YOUR_GOOGLE_GEMINI_API_KEY"
    GEMINI_MODEL="YOUR_GEMINI_MODEL_NAME" # e.g., "gemini-pro"
    ```

5. **Initialize the Database:**
    The database (`math_bot.db`) and its tables are created automatically when `database.py` is first imported.

6. **Run the bot:**
    ```bash
    python bot.py
    ```

## User Flows

### Starting the Bot & Main Menu
1. User sends `/start` or interacts with the bot for the first time
2. Bot displays welcome message and main menu with options:
   - "📚 Выбрать тему и начать"
   - "📊 Мой прогресс"
   - "❓ Помощь"

### Selecting a Topic & Starting a Test
1. User selects a topic from the list
2. Bot loads questions (from database or generates new ones)
3. Test begins with the first question

### Answering Questions
1. User sees question text and answer options
2. For questions with images, image is displayed with question text
3. User selects an answer
4. Bot provides immediate feedback (correct/incorrect)
5. User can navigate between questions or return to topic selection

### Viewing Results
1. After completing all questions, user sees test results
2. Results include:
   - Number of correct answers
   - Percentage score
   - List of incorrect answers with explanations
3. User can:
   - Return to main menu
   - Retry the same topic
   - Choose a different topic

## Database Schema

### Tables:
- **users**: User information
- **active_users**: Current test session data
- **test_history**: Test results history
- **errors**: Error statistics per topic
- **user_question_errors**: Detailed error logs
- **tasks**: Question bank with support for images and different question types

## Known Limitations

1. **AI Reliability**: AI-generated content might occasionally be inaccurate
2. **Image Processing**: Large PDF files might take longer to process
3. **Database**: SQLite might become a bottleneck with very high concurrent user counts
4. **Content Management**: Adding new topics requires database modification

## Future Enhancements

1. **User Profiles**: Allow users to set preferences
2. **More Content**: Additional topics and subjects
3. **Advanced Features**: 
   - Fill-in-the-blank questions
   - Matching questions
   - Spaced repetition
   - Adaptive difficulty
4. **Admin Features**: 
   - Question management interface
   - User statistics
   - Broadcast messages 