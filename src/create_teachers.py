import sqlite3

DB_PATH = "data/student_progress.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
DROP TABLE IF EXISTS teachers
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS teachers (
    teacher_id TEXT PRIMARY KEY,
    teacher_name TEXT,
    created_at TEXT
)
""")

cursor.execute("""
INSERT OR IGNORE INTO teachers (
    teacher_id,
    teacher_name,
    created_at
)
VALUES
    ('T10101', 'Teacher One', datetime('now')),
    ('T10102', 'Teacher Two', datetime('now'))
""")

conn.commit()
conn.close()

print("Teacher table created.")