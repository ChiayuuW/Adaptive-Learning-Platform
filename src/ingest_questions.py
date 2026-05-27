import os
import joblib
import pandas as pd

from sentence_transformers import SentenceTransformer
from predict import predict_topic, predict_difficulty
from db import execute_query


NEW_QUESTIONS_PATH = "data/new_questions.csv"
MODEL_DIR = "models"


def load_models():
    embedding_model_name = joblib.load(f"{MODEL_DIR}/embedding_model_name.pkl")
    embedding_model = SentenceTransformer(embedding_model_name)

    topic_centroids = joblib.load(f"{MODEL_DIR}/topic_centroids.pkl")
    difficulty_model = joblib.load(f"{MODEL_DIR}/difficulty_feature_model.pkl")
    feature_columns = joblib.load(f"{MODEL_DIR}/difficulty_feature_columns.pkl")

    return embedding_model, topic_centroids, difficulty_model, feature_columns


def validate_new_questions(df):
    required_columns = ["question", "answer"]
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()
    df["question"] = df["question"].astype(str).str.strip()
    df["answer"] = df["answer"].astype(str).str.strip()

    df = df[df["question"] != ""].reset_index(drop=True)

    if df.empty:
        raise ValueError("No valid questions found.")

    return df


def insert_review_question(row):
    execute_query("""
        INSERT INTO review_questions (
            question,
            answer,
            predicted_topic,
            topic_similarity_score,
            predicted_difficulty,
            difficulty_confidence,
            review_status,
            created_at
        )
        VALUES (
            :question,
            :answer,
            :predicted_topic,
            :topic_similarity_score,
            :predicted_difficulty,
            :difficulty_confidence,
            'pending',
            CURRENT_TIMESTAMP
        )
    """, {
        "question": str(row["question"]),
        "answer": str(row["answer"]),
        "predicted_topic": str(row["predicted_topic"]),
        "topic_similarity_score": float(row["topic_similarity_score"]),
        "predicted_difficulty": str(row["predicted_difficulty"]),
        "difficulty_confidence": float(row["difficulty_confidence"])
    })


def auto_tag_and_insert(df):
    embedding_model, topic_centroids, difficulty_model, feature_columns = load_models()

    inserted_count = 0

    for _, row in df.iterrows():
        question = row["question"]

        topic, topic_score, _ = predict_topic(
            question,
            embedding_model,
            topic_centroids
        )

        difficulty, difficulty_confidence = predict_difficulty(
            question,
            difficulty_model,
            feature_columns
        )

        tagged_row = {
            "question": str(question),
            "answer": str(row["answer"]),
            "predicted_topic": str(topic),
            "topic_similarity_score": float(round(float(topic_score), 3)),
            "predicted_difficulty": str(difficulty),
            "difficulty_confidence": float(round(float(difficulty_confidence), 3))
        }

        insert_review_question(tagged_row)
        inserted_count += 1

    return inserted_count


def clear_new_questions_file():
    pd.DataFrame(columns=["question", "answer"]).to_csv(
        NEW_QUESTIONS_PATH,
        index=False
    )


def main():
    new_df = pd.read_csv(NEW_QUESTIONS_PATH)
    new_df = validate_new_questions(new_df)

    inserted_count = auto_tag_and_insert(new_df)

    clear_new_questions_file()

    print(f"Auto-tagging completed.")
    print(f"Inserted {inserted_count} questions into review_questions table.")
    print("new_questions.csv has been cleared.")

execute_query("""
    CREATE TABLE IF NOT EXISTS difficulty_review_queue (
        review_id SERIAL PRIMARY KEY,
        question_id INTEGER NOT NULL,
        current_difficulty TEXT NOT NULL,
        recommended_difficulty TEXT NOT NULL,
        avg_attempts_until_correct FLOAT NOT NULL,
        student_count INTEGER NOT NULL,
        reason TEXT,
        review_status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TIMESTAMP
    )
""")


if __name__ == "__main__":
    main()