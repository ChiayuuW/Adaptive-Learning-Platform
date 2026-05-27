import sqlite3

DB_PATH = "data/student_progress.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS student_attempts (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    student_answer TEXT,
    created_at TEXT
)
""")

conn.commit()
conn.close()

print("student_attempts table created.")