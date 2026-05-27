import os
import re
import joblib
import pandas as pd
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score


DATA_PATH = "data/middle_school_math_questions.csv"
MODEL_DIR = "models"


def extract_difficulty_features(text):
    text_lower = text.lower()

    words = re.findall(r"\b\w+\b", text_lower)
    numbers = re.findall(r"\d+\.?\d*", text_lower)

    easy_words = [
        "find", "add", "subtract", "convert", "round",
        "identify", "write", "evaluate"
    ]

    hard_words = [
        "explain", "compare", "interpret", "estimate",
        "determine", "analyze", "create", "design",
        "justify", "prove"
    ]

    operation_words = [
        "add", "subtract", "multiply", "divide",
        "solve", "simplify", "evaluate", "convert",
        "increase", "decrease"
    ]

    formula_words = [
        "area", "perimeter", "circumference",
        "volume", "surface area", "radius",
        "diameter", "hypotenuse", "scale",
        "ratio", "proportion", "percent"
    ]

    advanced_formula_words = [
        "surface area", "cylinder", "cone",
        "hypotenuse", "pythagorean",
        "interquartile", "compound probability",
        "scale factor", "percent change"
    ]

    word_problem_words = [
        "recipe", "runner", "restaurant", "phone",
        "garden", "class", "school", "survey",
        "bag", "spinner", "coin", "dice",
        "taxi", "store", "fundraiser", "map",
        "bank", "team", "population", "mixture"
    ]

    multi_step_phrases = [
        "then", "after", "before", "compare",
        "explain", "determine", "find both",
        "create", "design", "write and solve",
        "set up", "estimate", "total", "including"
    ]

    unit_words = [
        "cm", "meter", "meters", "mile", "miles",
        "feet", "foot", "inch", "inches",
        "gallon", "gallons", "hour", "hours",
        "dollar", "dollars", "$", "cup", "cups",
        "yard", "yards", "degree", "degrees"
    ]

    has_fraction = int("/" in text)
    has_decimal = int(bool(re.search(r"\d+\.\d+", text)))
    has_percent = int("%" in text or "percent" in text_lower)
    has_equation = int("=" in text or "solve" in text_lower)
    has_formula = int(any(word in text_lower for word in formula_words))
    has_advanced_formula = int(any(word in text_lower for word in advanced_formula_words))
    has_word_problem = int(any(word in text_lower for word in word_problem_words))

    operation_count = sum(word in text_lower for word in operation_words)
    formula_word_count = sum(word in text_lower for word in formula_words)
    advanced_formula_count = sum(word in text_lower for word in advanced_formula_words)
    word_problem_count = sum(word in text_lower for word in word_problem_words)
    multi_step_count = sum(phrase in text_lower for phrase in multi_step_phrases)
    unit_count = sum(word in text_lower for word in unit_words)

    concept_count = (
        has_fraction
        + has_decimal
        + has_percent
        + has_equation
        + has_formula
        + has_word_problem
    )

    estimated_steps = (
        operation_count
        + has_formula
        + has_advanced_formula
        + has_word_problem
        + int(len(numbers) >= 2)
        + int(multi_step_count >= 1)
        + int(concept_count >= 2)
    )

    return {
        "word_count": len(words),
        "char_count": len(text),
        "sentence_complexity": len(words) / max(1, len(re.split(r"[,.?;]", text))),
        "number_count": len(numbers),

        "has_fraction": has_fraction,
        "has_decimal": has_decimal,
        "has_percent": has_percent,
        "has_equation": has_equation,

        "operation_count": operation_count,
        "easy_word_count": sum(word in text_lower for word in easy_words),
        "hard_word_count": sum(word in text_lower for word in hard_words),

        "formula_word_count": formula_word_count,
        "advanced_formula_count": advanced_formula_count,
        "has_formula": has_formula,
        "has_advanced_formula": has_advanced_formula,

        "word_problem_count": word_problem_count,
        "has_word_problem": has_word_problem,

        "multi_step_count": multi_step_count,
        "unit_count": unit_count,
        "has_unit_conversion": int(unit_count >= 2),

        "concept_count": concept_count,
        "has_multiple_concepts": int(concept_count >= 2),

        "estimated_steps": estimated_steps,
        "question_mark": int("?" in text),
    }

def build_feature_matrix(questions):
    feature_rows = [extract_difficulty_features(q) for q in questions]
    return pd.DataFrame(feature_rows)


def train_topic_embedding_model(df):
    print("\n=== Training Topic Embedding Model ===")

    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    topic_examples = {}

    for topic in df["topic"].unique():
        topic_questions = df[df["topic"] == topic]["question"].tolist()
        topic_embeddings = embedding_model.encode(topic_questions)
        topic_centroid = np.mean(topic_embeddings, axis=0)
        topic_examples[topic] = topic_centroid

    joblib.dump(topic_examples, f"{MODEL_DIR}/topic_centroids.pkl")

    # save sentence-transformer model name only
    joblib.dump("all-MiniLM-L6-v2", f"{MODEL_DIR}/embedding_model_name.pkl")

    print("Saved topic embedding centroids.")


def predict_topic_by_similarity(question, embedding_model, topic_centroids):
    question_embedding = embedding_model.encode([question])

    scores = {}

    for topic, centroid in topic_centroids.items():
        similarity = cosine_similarity(
            question_embedding,
            centroid.reshape(1, -1)
        )[0][0]

        scores[topic] = similarity

    best_topic = max(scores, key=scores.get)

    return best_topic, scores


def evaluate_topic_model(df):
    embedding_model_name = joblib.load(f"{MODEL_DIR}/embedding_model_name.pkl")
    embedding_model = SentenceTransformer(embedding_model_name)
    topic_centroids = joblib.load(f"{MODEL_DIR}/topic_centroids.pkl")

    predictions = []

    for question in df["question"]:
        topic, _ = predict_topic_by_similarity(
            question,
            embedding_model,
            topic_centroids
        )
        predictions.append(topic)

    print("\n=== Topic Similarity Model Evaluation ===")
    print("Accuracy:", accuracy_score(df["topic"], predictions))
    print(classification_report(df["topic"], predictions))


def train_difficulty_feature_model(df):
    print("\n=== Training Difficulty Feature Model ===")

    X_features = build_feature_matrix(df["question"])
    y = df["difficulty"]

    X_train, X_test, y_train, y_test = train_test_split(
        X_features,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    print("Accuracy:", accuracy_score(y_test, predictions))
    print(classification_report(y_test, predictions))

    joblib.dump(model, f"{MODEL_DIR}/difficulty_feature_model.pkl")
    joblib.dump(X_features.columns.tolist(), f"{MODEL_DIR}/difficulty_feature_columns.pkl")

    print("Saved difficulty feature model.")


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    df = pd.read_csv(DATA_PATH)

    train_topic_embedding_model(df)
    evaluate_topic_model(df)
    train_difficulty_feature_model(df)


if __name__ == "__main__":
    main()