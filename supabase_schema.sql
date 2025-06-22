-- Supabase Database Schema for go2study_bot
-- Execute this script in Supabase SQL Editor to create all necessary tables

-- Drop existing tables if they exist (optional - remove if you want to keep existing data)
-- DROP TABLE IF EXISTS user_errors CASCADE;
-- DROP TABLE IF EXISTS test_results CASCADE;
-- DROP TABLE IF EXISTS questions CASCADE;
-- DROP TABLE IF EXISTS subtopics CASCADE;
-- DROP TABLE IF EXISTS main_topics CASCADE;
-- DROP TABLE IF EXISTS allowed_users CASCADE;
-- DROP TABLE IF EXISTS admins CASCADE;

-- Create admins table
CREATE TABLE IF NOT EXISTS admins (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    is_super_admin BOOLEAN DEFAULT FALSE,
    created_by BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create allowed_users table
CREATE TABLE IF NOT EXISTS allowed_users (
    user_id BIGINT PRIMARY KEY,
    username TEXT UNIQUE,
    full_name TEXT,
    grade INTEGER CHECK (grade IN (5, 6)),
    added_by BIGINT REFERENCES admins(user_id),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT FALSE,
    language TEXT DEFAULT 'ru' CHECK (language IN ('ru', 'kk')),
    current_topic TEXT,
    last_activity TIMESTAMP,
    has_access BOOLEAN DEFAULT TRUE
);

-- Create main_topics table
CREATE TABLE IF NOT EXISTS main_topics (
    id SERIAL PRIMARY KEY,
    topic_name TEXT NOT NULL,
    language TEXT NOT NULL CHECK (language IN ('ru', 'kk')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(topic_name, language)
);

-- Create subtopics table
CREATE TABLE IF NOT EXISTS subtopics (
    id SERIAL PRIMARY KEY,
    subtopic_name TEXT NOT NULL,
    main_topic_id INTEGER NOT NULL REFERENCES main_topics(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subtopic_name, main_topic_id)
);

-- Create questions table
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_answer TEXT NOT NULL CHECK (correct_answer IN ('A', 'B', 'C', 'D')),
    topic_id INTEGER NOT NULL REFERENCES subtopics(id) ON DELETE CASCADE,
    source TEXT DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create test_results table
CREATE TABLE IF NOT EXISTS test_results (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES allowed_users(user_id),
    topic_id INTEGER NOT NULL REFERENCES subtopics(id),
    percentage REAL NOT NULL CHECK (percentage >= 0 AND percentage <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create user_errors table
CREATE TABLE IF NOT EXISTS user_errors (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES allowed_users(user_id),
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_answer TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    error_count INTEGER DEFAULT 1,
    first_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_error_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, question_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_allowed_users_user_id ON allowed_users(user_id);
CREATE INDEX IF NOT EXISTS idx_questions_topic_id ON questions(topic_id);
CREATE INDEX IF NOT EXISTS idx_test_results_user_id ON test_results(user_id);
CREATE INDEX IF NOT EXISTS idx_test_results_topic_id ON test_results(topic_id);
CREATE INDEX IF NOT EXISTS idx_user_errors_user_id ON user_errors(user_id);
CREATE INDEX IF NOT EXISTS idx_user_errors_question_id ON user_errors(question_id);
CREATE INDEX IF NOT EXISTS idx_subtopics_main_topic_id ON subtopics(main_topic_id);
CREATE INDEX IF NOT EXISTS idx_allowed_users_is_active ON allowed_users(is_active);
CREATE INDEX IF NOT EXISTS idx_main_topics_language ON main_topics(language);
CREATE INDEX IF NOT EXISTS idx_questions_source ON questions(source);
CREATE INDEX IF NOT EXISTS idx_test_results_created_at ON test_results(created_at);
CREATE INDEX IF NOT EXISTS idx_user_topic_results ON test_results(user_id, topic_id);
CREATE INDEX IF NOT EXISTS idx_user_question_errors ON user_errors(user_id, question_id);
CREATE INDEX IF NOT EXISTS idx_active_topics ON subtopics(is_active, main_topic_id);
CREATE INDEX IF NOT EXISTS idx_active_main_topics ON main_topics(is_active, language);
CREATE INDEX IF NOT EXISTS idx_allowed_users_grade ON allowed_users(grade);
CREATE INDEX IF NOT EXISTS idx_allowed_users_language ON allowed_users(language);

-- Insert initial topics data
INSERT INTO main_topics (topic_name, language) VALUES
    ('Математика', 'ru'),
    ('Физика', 'ru'),
    ('Химия', 'ru'),
    ('Биология', 'ru'),
    ('Математика', 'kk'),
    ('Физика', 'kk'),
    ('Химия', 'kk'),
    ('Биология', 'kk')
ON CONFLICT (topic_name, language) DO NOTHING;

-- Insert some basic subtopics
INSERT INTO subtopics (subtopic_name, main_topic_id) 
SELECT 'Алгебра', id FROM main_topics WHERE topic_name = 'Математика' AND language = 'ru'
ON CONFLICT (subtopic_name, main_topic_id) DO NOTHING;

INSERT INTO subtopics (subtopic_name, main_topic_id) 
SELECT 'Геометрия', id FROM main_topics WHERE topic_name = 'Математика' AND language = 'ru'
ON CONFLICT (subtopic_name, main_topic_id) DO NOTHING;

INSERT INTO subtopics (subtopic_name, main_topic_id) 
SELECT 'Арифметика', id FROM main_topics WHERE topic_name = 'Математика' AND language = 'ru'
ON CONFLICT (subtopic_name, main_topic_id) DO NOTHING;

INSERT INTO subtopics (subtopic_name, main_topic_id) 
SELECT 'Механика', id FROM main_topics WHERE topic_name = 'Физика' AND language = 'ru'
ON CONFLICT (subtopic_name, main_topic_id) DO NOTHING;

INSERT INTO subtopics (subtopic_name, main_topic_id) 
SELECT 'Термодинамика', id FROM main_topics WHERE topic_name = 'Физика' AND language = 'ru'
ON CONFLICT (subtopic_name, main_topic_id) DO NOTHING;

-- For Kazakh language
INSERT INTO subtopics (subtopic_name, main_topic_id) 
SELECT 'Алгебра', id FROM main_topics WHERE topic_name = 'Математика' AND language = 'kk'
ON CONFLICT (subtopic_name, main_topic_id) DO NOTHING;

INSERT INTO subtopics (subtopic_name, main_topic_id) 
SELECT 'Геометрия', id FROM main_topics WHERE topic_name = 'Математика' AND language = 'kk'
ON CONFLICT (subtopic_name, main_topic_id) DO NOTHING;

-- Verify the setup
SELECT 'Tables created successfully!' as status;

-- Show table counts
SELECT 
    'admins' as table_name, 
    COUNT(*) as record_count 
FROM admins
UNION ALL
SELECT 
    'allowed_users' as table_name, 
    COUNT(*) as record_count 
FROM allowed_users
UNION ALL
SELECT 
    'main_topics' as table_name, 
    COUNT(*) as record_count 
FROM main_topics
UNION ALL
SELECT 
    'subtopics' as table_name, 
    COUNT(*) as record_count 
FROM subtopics
UNION ALL
SELECT 
    'questions' as table_name, 
    COUNT(*) as record_count 
FROM questions
UNION ALL
SELECT 
    'test_results' as table_name, 
    COUNT(*) as record_count 
FROM test_results
UNION ALL
SELECT 
    'user_errors' as table_name, 
    COUNT(*) as record_count 
FROM user_errors
ORDER BY table_name; 