````markdown
## 🎓 Go2Study

AI-powered adaptive learning platform for NIS entrance exam preparation.

Go2Study combines curated educational content, adaptive testing, AI-generated questions, student analytics, PDF question import, and a complete administration system inside Telegram.

Built for production deployment with Python, PostgreSQL, Google Gemini, Docker, Railway, and Telegram Bot API.

![Python](https://img.shields.io/badge/Python-3.9-blue?style=for-the-badge&logo=python)

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql)

![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker)

![Google Gemini](https://img.shields.io/badge/Google-Gemini-blue?style=for-the-badge)

![Railway](https://img.shields.io/badge/Railway-Deployed-black?style=for-the-badge)

![MIT License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---

## Overview

Go2Study is a Telegram-based adaptive learning platform designed for students preparing for NIS entrance exams.

The system provides topic-based tests, tracks student mistakes, generates new AI-powered questions, stores test history, and gives administrators full control over students, topics, question banks, and analytics.

---

## Features

| Feature                | Description                                              |
| ---------------------- | -------------------------------------------------------- |
| Adaptive Testing       | Prioritizes questions based on previous student mistakes |
| AI Question Generation | Uses Google Gemini to generate new practice questions    |
| Question Bank          | Stores curated, AI-generated, and PDF-imported questions |
| Retake Mode            | Helps students practice previous mistakes                |
| Random Tests           | Generates mixed tests from different topics              |
| Student Analytics      | Tracks progress, history, and weak areas                 |
| Admin Panel            | CRUD for students, topics, questions, and admins         |
| PDF Import             | Extracts and imports questions from PDF files            |
| Bilingual UI           | Russian and Kazakh language support                      |
| Whitelist Access       | Only approved students can use the bot                   |
| Clean Telegram UX      | Managed messages prevent chat clutter                    |

---

## Engineering Highlights

- Adaptive testing algorithm based on student mistakes
- AI-generated exam questions with Google Gemini
- Complete administration system with CRUD operations
- PostgreSQL repository architecture
- SQLAlchemy-based database layer
- PDF question import pipeline
- Student progress analytics
- Test history tracking
- Bilingual interface: Russian and Kazakh
- Managed Telegram messages for clean UX
- Production deployment on Railway
- Dockerized application

---

## Curriculum

The platform contains 5 main sections and 23 subtopics for each language.

| Section                       | Example Topics                                    |
| ----------------------------- | ------------------------------------------------- |
| Numbers and Arithmetic        | Fractions, percentages, proportions, inequalities |
| Algebraic Expressions         | Simplification, equations, systems of equations   |
| Geometry                      | Area, perimeter, angles, scale, circles           |
| Data Analysis and Statistics  | Average, sequences, word problems, functions      |
| Logical-Mathematical Thinking | Patterns, logic problems, expression comparison   |

---

## Architecture

```mermaid
flowchart TB
    subgraph Client
        TG[Telegram Client]
    end

    subgraph App["Go2Study Bot"]
        MAIN[main.py]
        HEALTH[Flask Health Check]
        CMD[Command Handlers]
        CB[Callback Handlers]
        ADM[Admin Handlers]
        QS[Question Service]
        AI[Gemini AI Service]
        PDF[PDF Processor]
        RTS[Random Test Service]
        MM[Message Manager]
    end

    subgraph Data
        FACADE[Database Facade]
        REPOS[Repositories]
        PG[(PostgreSQL)]
    end

    subgraph External
        GEMINI[Google Gemini API]
    end

    TG <-->|Telegram Bot API| MAIN
    MAIN --> HEALTH
    MAIN --> CMD
    MAIN --> CB
    MAIN --> ADM

    CMD --> QS
    CB --> QS
    ADM --> QS
    ADM --> PDF

    QS --> AI
    QS --> RTS
    QS --> MM
    PDF --> AI
    AI <-->|REST| GEMINI

    QS --> FACADE
    ADM --> FACADE
    MM --> FACADE
    FACADE --> REPOS
    REPOS --> PG
````

---

## Test Flow

1. Student selects a section and subtopic using Telegram inline buttons.
2. `QuestionService` builds a 10-question test.
3. The system prioritizes previous mistakes.
4. Existing questions are loaded from PostgreSQL.
5. Missing questions are generated using Google Gemini.
6. Answers are processed and stored.
7. Student progress and test history are updated.
8. Retake mode uses previous mistakes and AI-generated similar questions.

---

## Adaptive Algorithm

### Normal Test Mode

1. Questions from previous mistakes.
2. Questions from PostgreSQL question bank.
3. At least several fresh AI-generated questions.

### Retake Mode

1. Previous mistakes from the selected topic.
2. Missing questions are generated by AI.
3. Results are saved for future analytics.

---

## Tech Stack

| Component      | Technology              |
| -------------- | ----------------------- |
| Language       | Python 3.9              |
| Bot Framework  | python-telegram-bot     |
| AI             | Google Gemini           |
| Database       | PostgreSQL              |
| ORM            | SQLAlchemy              |
| DB Driver      | psycopg2 / asyncpg      |
| PDF Processing | PyPDF2, PyMuPDF, Pillow |
| Health Check   | Flask                   |
| Deployment     | Docker, Railway         |
| Testing        | unittest, mocks         |

---

## Project Structure

```text
src/
├── config/              # Constants, translations, localized messages
├── db/                  # Models, repositories, database facade
├── handlers/            # Telegram command, callback and admin handlers
├── services/            # AI, questions, PDF, random tests, topics
├── utils/               # Keyboards, translations, message manager
├── init_app.py          # Application initialization
├── init_database.py     # Database schema initialization
├── init_superadmin.py   # Superadmin creation
└── init_topics.py       # Curriculum seeding

tests/
└── test_ai_service_improved.py

Dockerfile
railway.json
main.py
requirements.txt
```

---

## Database Schema

| Table             | Purpose                                          |
| ----------------- | ------------------------------------------------ |
| admins            | Administrator accounts and roles                 |
| allowed_users     | Whitelisted students                             |
| main_topics       | Main curriculum sections                         |
| subtopics         | Subtopics linked to sections                     |
| questions         | Manual, AI-generated, and PDF-imported questions |
| user_errors       | Student mistakes for adaptive testing            |
| user_progress     | Topic progress statistics                        |
| user_test_results | Test history                                     |
| managed_messages  | Telegram UI message management                   |

---

## Bot Commands

| Command      | Description                         |
| ------------ | ----------------------------------- |
| /start       | Register student and open main menu |
| /stop        | Clear active session                |
| /reset       | Reset stuck test state              |
| /myid        | Show Telegram user ID               |
| /language    | Change interface language           |
| /admin       | Open admin panel                    |
| /clear_cache | Clear user access cache             |

---

## Admin Features

* Manage students
* Manage admins
* Manage sections and topics
* Add, edit, search and delete questions
* Import questions from PDF
* View student statistics
* View system analytics
* Manage whitelist access

---

## Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create `.env`

```env
TELEGRAM_BOT_TOKEN=your_bot_token

GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.0-flash

DATABASE_URL=postgresql://user:password@host:5432/dbname
USE_POSTGRESQL=true

SUPERADMIN_ID=123456789
SUPERADMIN_USERNAME=admin_username
SUPERADMIN_FIO=Admin Name

PORT=8000
```

### 3. Initialize database manually if needed

```bash
python src/init_database.py
python src/init_topics.py
python src/init_superadmin.py
```

### 4. Run locally

```bash
python main.py
```

---

## Docker

```bash
docker build -t go2study-bot .
docker run --env-file .env -p 8000:8000 go2study-bot
```

---

## Deployment

The project is designed for Railway deployment.

Deployment flow:

```text
GitHub
  ↓
Railway
  ↓
Docker Build
  ↓
PostgreSQL
  ↓
Telegram Bot
```

Health check:

```http
GET /
```

Response:

```json
{
  "status": "ok"
}
```

---

## Testing

```bash
python -m unittest tests/test_ai_service_improved.py
```

Tests cover:

* AI response parsing
* Invalid response handling
* Structured question format validation
* Gemini service mocking

---

## Roadmap

* [x] Adaptive testing
* [x] Google Gemini integration
* [x] PostgreSQL support
* [x] Admin panel
* [x] Student whitelist
* [x] PDF question import
* [x] Russian and Kazakh interface
* [x] Test history
* [x] Student analytics
* [x] Railway deployment
* [x] Docker deployment
* [ ] Web dashboard
* [ ] Parent access
* [ ] Teacher analytics dashboard
* [ ] More exam modes
* [ ] CI/CD pipeline
* [ ] Advanced reporting

---

## Lessons Learned

Building Go2Study helped me improve:

* Telegram Bot architecture
* PostgreSQL database design
* SQLAlchemy ORM usage
* Repository pattern
* AI prompt engineering
* Adaptive learning logic
* PDF processing
* Docker deployment
* Railway deployment
* Production debugging
* Large Python project organization

---

## License

This project is licensed under the MIT License.

---

## Author

Bekzat Tursun

GitHub: https://github.com/cobrich

```
```
