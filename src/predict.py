import re
import joblib
import pandas as pd

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


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


def predict_topic(question, embedding_model, topic_centroids):
    question_embedding = embedding_model.encode([question])

    scores = {}

    for topic, centroid in topic_centroids.items():
        similarity = cosine_similarity(
            question_embedding,
            centroid.reshape(1, -1)
        )[0][0]

        scores[topic] = similarity

    best_topic = max(scores, key=scores.get)
    best_score = scores[best_topic]

    return best_topic, best_score, scores


def predict_difficulty(question, difficulty_model, feature_columns):
    features = pd.DataFrame([extract_difficulty_features(question)])
    features = features[feature_columns]

    difficulty = difficulty_model.predict(features)[0]
    confidence = difficulty_model.predict_proba(features)[0].max()

    return difficulty, confidence


def main():
    embedding_model_name = joblib.load("models/embedding_model_name.pkl")
    embedding_model = SentenceTransformer(embedding_model_name)

    topic_centroids = joblib.load("models/topic_centroids.pkl")
    difficulty_model = joblib.load("models/difficulty_feature_model.pkl")
    feature_columns = joblib.load("models/difficulty_feature_columns.pkl")

    question = input("Enter a math question: ")

    topic, topic_score, topic_scores = predict_topic(
        question,
        embedding_model,
        topic_centroids
    )

    difficulty, difficulty_score = predict_difficulty(
        question,
        difficulty_model,
        feature_columns
    )

    print("\nPrediction Result:")
    print(f"Question: {question}")
    print(f"Predicted Topic: {topic}")
    print(f"Topic Similarity Score: {topic_score:.3f}")
    print(f"Predicted Difficulty: {difficulty}")
    print(f"Difficulty Confidence: {difficulty_score:.3f}")

    print("\nAll Topic Similarity Scores:")
    for topic_name, score in sorted(topic_scores.items(), key=lambda x: x[1], reverse=True):
        print(f"{topic_name}: {score:.3f}")


if __name__ == "__main__":
    main()