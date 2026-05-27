import sqlite3

DB_PATH = "data/student_progress.db"

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS student_progress (
    student_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER DEFAULT 0,
    last_answer TEXT,
    updated_at TEXT,
    PRIMARY KEY (student_id, question_id)
)
""")

conn.commit()

conn.close()

print("Database initialized.")