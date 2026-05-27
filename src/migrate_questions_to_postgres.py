import pandas as pd
from db import execute_query


CSV_PATH = "data/middle_school_math_questions.csv"


def create_questions_table():
    execute_query("""
        CREATE TABLE IF NOT EXISTS questions (
            question_id INTEGER PRIMARY KEY,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            skill TEXT,
            question TEXT NOT NULL,
            answer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def migrate_questions():
    df = pd.read_csv(CSV_PATH)

    if "skill" not in df.columns:
        df["skill"] = ""

    for _, row in df.iterrows():
        execute_query("""
            INSERT INTO questions (
                question_id,
                topic,
                difficulty,
                skill,
                question,
                answer
            )
            VALUES (
                :question_id,
                :topic,
                :difficulty,
                :skill,
                :question,
                :answer
            )
            ON CONFLICT (question_id) DO NOTHING
        """, {
            "question_id": int(row["question_id"]),
            "topic": row["topic"],
            "difficulty": str(row["difficulty"]).lower(),
            "skill": row.get("skill", ""),
            "question": row["question"],
            "answer": row.get("answer", "")
        })


if __name__ == "__main__":
    create_questions_table()
    migrate_questions()
    print("Questions migrated to PostgreSQL.")