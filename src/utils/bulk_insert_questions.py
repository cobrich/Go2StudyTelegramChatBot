import sqlite3

# === Пример списка вопросов ===
questions = [
    {
        "topic": "Соотношение и пропорция",
        "question": "Если 20% числа равны 50, то чему равно всё число?",
        "answer": "250",
        "explanation": "20% от 250 = 50",
        "incorrect_options": "200;300;400",
        "question_type": "test",
        "image_path": "",
        "source": "pdf"
    },
    {
        "topic": "Масштаб и процент",
        "question": "На карте 1 см соответствует 10 км. Какое реальное расстояние соответствует 5 см на карте?",
        "answer": "50 км",
        "explanation": "",
        "incorrect_options": "5 км;10 км;500 км",
        "question_type": "test",
        "image_path": "",
        "source": "pdf"
    }
    # Добавляй сюда ещё словари с вопросами
]

# === Подключение к базе ===
conn = sqlite3.connect("math_bot.db")
cursor = conn.cursor()

# === SQL-запрос ===
insert_query = """
INSERT INTO questions (
    topic,
    question,
    answer,
    explanation,
    incorrect_options,
    question_type,
    image_path,
    source
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

# === Вставка всех вопросов ===
for q in questions:
    cursor.execute(insert_query, (
        q["topic"],
        q["question"],
        q["answer"],
        q["explanation"],
        q["incorrect_options"],
        q["question_type"],
        q["image_path"],
        q["source"]
    ))

conn.commit()
conn.close()

print(f"✅ Успешно добавлено {len(questions)} вопрос(ов).")
