from db import execute_query


def init_tables():
    execute_query("""
        CREATE TABLE IF NOT EXISTS teachers (
            teacher_id TEXT PRIMARY KEY,
            teacher_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    execute_query("""
        CREATE TABLE IF NOT EXISTS student_progress (
            student_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            last_answer TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (student_id, question_id)
        )
    """)

    execute_query("""
        CREATE TABLE IF NOT EXISTS student_attempts (
            attempt_id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            student_answer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    execute_query("""
        INSERT INTO teachers (teacher_id, teacher_name)
        VALUES
            ('T10101', 'Teacher One'),
            ('T10102', 'Teacher Two')
        ON CONFLICT (teacher_id) DO NOTHING
    """)
    execute_query("""
        CREATE TABLE IF NOT EXISTS review_questions (
            review_id SERIAL PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT,
            predicted_topic TEXT,
            topic_similarity_score FLOAT,
            predicted_difficulty TEXT,
            difficulty_confidence FLOAT,
            review_status TEXT DEFAULT 'pending',
            approved_topic TEXT,
            approved_difficulty TEXT,
            reviewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

if __name__ == "__main__":
    init_tables()
    print("PostgreSQL tables initialized.")