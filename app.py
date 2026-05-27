import re
# import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from src.db import fetch_all, fetch_one, execute_query

# DATA_PATH = "data/middle_school_math_questions.csv"
# DB_PATH = "data/student_progress.db"

def normalize_answer(answer):
    if answer is None:
        return ""

    answer = str(answer).strip().lower()
    answer = answer.replace(",", "")
    answer = re.sub(r"\s+", " ", answer)

    return answer


def extract_numeric_value(answer):
    if answer is None or pd.isna(answer):
        return None

    text = normalize_answer(answer)

    # mixed number: 2 1/2
    mixed_match = re.search(r"(-?\d+)\s+(\d+)\s*/\s*(\d+)", text)
    if mixed_match:
        whole = int(mixed_match.group(1))
        numerator = int(mixed_match.group(2))
        denominator = int(mixed_match.group(3))

        if denominator != 0:
            sign = -1 if whole < 0 else 1
            return whole + sign * (numerator / denominator)

    # fraction: 1/2, 2/4
    fraction_match = re.search(r"(-?\d+)\s*/\s*(-?\d+)", text)
    if fraction_match:
        numerator = int(fraction_match.group(1))
        denominator = int(fraction_match.group(2))

        if denominator != 0:
            return numerator / denominator

    # decimal or integer
    number_match = re.search(r"-?\d+\.?\d*", text)
    if number_match:
        return float(number_match.group(0))

    return None


def is_correct(student_answer, correct_answer):
    if pd.isna(correct_answer) or str(correct_answer).strip() == "":
        return False

    student_text = normalize_answer(student_answer)
    correct_text = normalize_answer(correct_answer)

    student_num = extract_numeric_value(student_answer)
    correct_num = extract_numeric_value(correct_answer)

    # If both answers contain numbers, compare numeric values
    if student_num is not None and correct_num is not None:
        return abs(student_num - correct_num) < 0.01

    # Otherwise, fall back to text comparison
    return student_text == correct_text

@st.cache_data
def load_questions():
    rows = fetch_all("""
        SELECT
            question_id,
            topic,
            difficulty,
            skill,
            question,
            answer
        FROM questions
        ORDER BY question_id
    """)

    df = pd.DataFrame(
        rows,
        columns=[
            "question_id",
            "topic",
            "difficulty",
            "skill",
            "question",
            "answer"
        ]
    )

    if df.empty:
        st.error("No questions found in PostgreSQL questions table.")
        st.stop()

    df["question_id"] = df["question_id"].astype(str)
    df["difficulty"] = df["difficulty"].str.lower()

    return df

# REVIEW_PATH = "data/review_questions.csv"
# QUESTION_BANK_PATH = "data/middle_school_math_questions.csv"

def teacher_review_page():
    render_header()

    if st.button("Logout"):
        logout()
        st.rerun()

    topic_options = [
        "Algebra",
        "Geometry",
        "Fractions & Decimals",
        "Statistics & Probability",
        "Ratios & Percentages",
        "Integers & Expressions"
    ]

    difficulty_options = ["easy", "medium", "hard"]

    st.markdown("## New Question Review")

    review_df = load_review_questions()

    if review_df.empty:
        st.info("No new question review items.")
    else:
        pending_df = review_df[
            review_df["review_status"].str.lower() == "pending"
        ]

        if pending_df.empty:
            st.success("No pending new questions.")
        else:
            for idx, row in pending_df.iterrows():
                review_id = row["review_id"]

                with st.container():
                    st.markdown("---")
                    st.markdown(f"### Pending Question #{review_id}")

                    st.markdown(f"**Question:** {row['question']}")
                    st.markdown(f"**Answer:** {row['answer']}")

                    predicted_topic = row.get("predicted_topic", topic_options[0])
                    predicted_difficulty = row.get("predicted_difficulty", "medium")

                    col1, col2 = st.columns(2)

                    with col1:
                        selected_topic = st.selectbox(
                            "Topic",
                            topic_options,
                            index=topic_options.index(predicted_topic)
                            if predicted_topic in topic_options else 0,
                            key=f"topic_review_{review_id}"
                        )

                    with col2:
                        selected_difficulty = st.selectbox(
                            "Difficulty",
                            difficulty_options,
                            index=difficulty_options.index(predicted_difficulty)
                            if predicted_difficulty in difficulty_options else 1,
                            key=f"difficulty_review_{review_id}"
                        )

                    col3, col4 = st.columns(2)

                    with col3:
                        if st.button(
                            "Approve and Add to Question Bank",
                            key=f"approve_{review_id}"
                        ):
                            approve_question(
                                review_id,
                                selected_topic,
                                selected_difficulty
                            )
                            st.success("Question approved and added.")
                            st.rerun()

                    with col4:
                        if st.button("Reject", key=f"reject_{review_id}"):
                            reject_question(review_id)
                            st.warning("Question rejected.")
                            st.rerun()

    st.markdown("---")
    st.markdown("## Difficulty Review")

    difficulty_df = load_difficulty_reviews()

    if difficulty_df.empty:
        st.info("No difficulty review items.")
    else:
        for _, row in difficulty_df.iterrows():
            review_id = row["review_id"]

            with st.container():
                st.markdown("---")
                st.markdown(f"### Difficulty Review #{review_id}")

                st.markdown(f"**Question:** {row['question']}")
                st.markdown(f"**Current Difficulty:** {row['current_difficulty']}")
                st.markdown(f"**Recommended Difficulty:** {row['recommended_difficulty']}")
                st.markdown(
                    f"**Average Attempts Until Correct:** "
                    f"{row['avg_attempts']:.2f}"
                )
                st.markdown(f"**Students Analyzed:** {row['student_count']}")
                st.markdown(f"**Reason:** {row['reason']}")

                selected_final_difficulty = st.selectbox(
                    "Teacher Final Difficulty",
                    difficulty_options,
                    index=difficulty_options.index(row["recommended_difficulty"])
                    if row["recommended_difficulty"] in difficulty_options else 1,
                    key=f"final_diff_{review_id}"
                )

                if st.button(
                    "Save Difficulty Decision",
                    key=f"save_diff_{review_id}"
                ):
                    update_reviewed_difficulty(
                        review_id,
                        row["question_id"],
                        selected_final_difficulty
                    )
                    st.success(
                        "Difficulty updated and removed from review queue."
                    )
                    st.rerun()
                    
def load_review_questions():
    rows = fetch_all("""
        SELECT
            review_id,
            question,
            answer,
            predicted_topic,
            topic_similarity_score,
            predicted_difficulty,
            difficulty_confidence,
            review_status,
            approved_topic,
            approved_difficulty,
            reviewed_at,
            created_at
        FROM review_questions
        ORDER BY created_at
    """)

    return pd.DataFrame(
        rows,
        columns=[
            "review_id",
            "question",
            "answer",
            "predicted_topic",
            "topic_similarity_score",
            "predicted_difficulty",
            "difficulty_confidence",
            "review_status",
            "approved_topic",
            "approved_difficulty",
            "reviewed_at",
            "created_at"
        ]
    )



def approve_question(review_id, topic, difficulty):
    row = fetch_one("""
        SELECT question, answer
        FROM review_questions
        WHERE review_id = :review_id
    """, {
        "review_id": int(review_id)
    })

    if row is None:
        st.error("Review question not found.")
        return

    question_text = row[0]
    answer = row[1]

    max_row = fetch_one("""
        SELECT COALESCE(MAX(question_id), 0)
        FROM questions
    """)

    next_question_id = int(max_row[0]) + 1

    execute_query("""
        INSERT INTO questions (
            question_id,
            topic,
            difficulty,
            skill,
            question,
            answer,
            created_at
        )
        VALUES (
            :question_id,
            :topic,
            :difficulty,
            :skill,
            :question,
            :answer,
            CURRENT_TIMESTAMP
        )
    """, {
        "question_id": next_question_id,
        "topic": topic,
        "difficulty": difficulty,
        "skill": "",
        "question": question_text,
        "answer": answer
    })

    execute_query("""
        DELETE FROM review_questions
        WHERE review_id = :review_id
    """, {
        "review_id": int(review_id)
    })

    st.cache_data.clear()


def reject_question(review_id):
    execute_query("""
        UPDATE review_questions
        SET
            review_status = 'rejected',
            reviewed_at = CURRENT_TIMESTAMP
        WHERE review_id = :review_id
    """, {
        "review_id": int(review_id)
    })

def load_difficulty_reviews():
    rows = fetch_all("""
        SELECT
            dq.review_id,
            dq.question_id,
            q.question,
            dq.current_difficulty,
            dq.recommended_difficulty,
            dq.avg_attempts,
            dq.student_count,
            dq.reason,
            dq.review_status,
            dq.created_at
        FROM difficulty_review_queue dq
        JOIN questions q
            ON q.question_id = dq.question_id
        WHERE dq.review_status = 'pending'
        ORDER BY dq.created_at
    """)

    return pd.DataFrame(
        rows,
        columns=[
            "review_id",
            "question_id",
            "question",
            "current_difficulty",
            "recommended_difficulty",
            "avg_attempts",
            "student_count",
            "reason",
            "review_status",
            "created_at"
        ]
    )


def update_reviewed_difficulty(review_id, question_id, selected_difficulty):
    execute_query("""
        UPDATE questions
        SET difficulty = :selected_difficulty
        WHERE question_id = :question_id
    """, {
        "selected_difficulty": selected_difficulty,
        "question_id": int(question_id)
    })

    execute_query("""
        DELETE FROM difficulty_review_queue
        WHERE review_id = :review_id
    """, {
        "review_id": int(review_id)
    })

    st.cache_data.clear()


def keep_current_difficulty(review_id):
    execute_query("""
        UPDATE difficulty_review_queue
        SET review_status = 'rejected',
            reviewed_at = CURRENT_TIMESTAMP
        WHERE review_id = :review_id
    """, {
        "review_id": int(review_id)
    })

def is_valid_teacher(teacher_id):
    result = fetch_one("""
        SELECT teacher_id
        FROM teachers
        WHERE teacher_id = :teacher_id
    """, {"teacher_id": teacher_id})

    return result is not None

def load_student_progress(student_id):
    rows = fetch_all("""
        SELECT question_id, status
        FROM student_progress
        WHERE student_id = :student_id
    """, {"student_id": student_id})

    return {
        str(row[0]): row[1]
        for row in rows
    }

def save_student_progress(student_id, question_id, status, answer):
    execute_query("""
        INSERT INTO student_progress (
            student_id,
            question_id,
            status,
            attempts,
            last_answer,
            updated_at
        )
        VALUES (
            :student_id,
            :question_id,
            :status,
            1,
            :last_answer,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (student_id, question_id)
        DO UPDATE SET
            status = EXCLUDED.status,
            attempts = student_progress.attempts + 1,
            last_answer = EXCLUDED.last_answer,
            updated_at = CURRENT_TIMESTAMP
    """, {
        "student_id": student_id,
        "question_id": str(question_id),
        "status": status,
        "last_answer": answer
    })

def save_student_attempt(student_id, question_id, topic, difficulty, is_correct_value, answer):
    execute_query("""
        INSERT INTO student_attempts (
            student_id,
            question_id,
            topic,
            difficulty,
            is_correct,
            student_answer,
            created_at
        )
        VALUES (
            :student_id,
            :question_id,
            :topic,
            :difficulty,
            :is_correct,
            :student_answer,
            CURRENT_TIMESTAMP
        )
    """, {
        "student_id": student_id,
        "question_id": str(question_id),
        "topic": topic,
        "difficulty": difficulty,
        "is_correct": int(is_correct_value),
        "student_answer": answer
    })

def update_question_difficulty_stats(question_id):
    execute_query("""
        INSERT INTO question_difficulty_stats (
            question_id,
            avg_attempts_until_correct,
            student_count,
            recommended_difficulty,
            updated_at
        )

        WITH ordered_attempts AS (
            SELECT
                student_id,
                question_id::INTEGER AS question_id,
                is_correct,
                created_at,
                ROW_NUMBER() OVER (
                    PARTITION BY student_id, question_id
                    ORDER BY created_at
                ) AS attempt_number
            FROM student_attempts
            WHERE question_id = :question_id
        ),

        first_correct AS (
            SELECT
                student_id,
                question_id,
                MIN(attempt_number) AS attempts_until_correct
            FROM ordered_attempts
            WHERE is_correct = 1
            GROUP BY student_id, question_id
        ),

        stats AS (
            SELECT
                question_id,
                AVG(attempts_until_correct) AS avg_attempts,
                COUNT(*) AS student_count
            FROM first_correct
            GROUP BY question_id
        ),

        recommendation AS (
            SELECT
                question_id,
                avg_attempts,
                student_count,
                CASE
                    WHEN avg_attempts <= 1.4 THEN 'easy'
                    WHEN avg_attempts <= 2.2 THEN 'medium'
                    ELSE 'hard'
                END AS recommended_difficulty
            FROM stats
        )

        SELECT
            question_id,
            avg_attempts,
            student_count,
            recommended_difficulty,
            CURRENT_TIMESTAMP
        FROM recommendation

        ON CONFLICT (question_id)
        DO UPDATE SET
            avg_attempts_until_correct = EXCLUDED.avg_attempts_until_correct,
            student_count = EXCLUDED.student_count,
            recommended_difficulty = EXCLUDED.recommended_difficulty,
            updated_at = CURRENT_TIMESTAMP
    """, {
        "question_id": str(question_id)
    })

def check_difficulty_mismatch(question_id):
    execute_query("""
        INSERT INTO difficulty_review_queue (
            question_id,
            current_difficulty,
            recommended_difficulty,
            avg_attempts,
            student_count,
            reason,
            review_status,
            created_at
        )

        SELECT
            q.question_id,
            q.difficulty AS current_difficulty,
            s.recommended_difficulty,
            s.avg_attempts_until_correct,
            s.student_count,
            'Observed student attempts suggest a different difficulty level.',
            'pending',
            CURRENT_TIMESTAMP
        FROM questions q
        JOIN question_difficulty_stats s
            ON q.question_id = s.question_id
        WHERE q.question_id = :question_id
          AND s.student_count >= 5
          AND q.difficulty <> s.recommended_difficulty
          AND NOT EXISTS (
              SELECT 1
              FROM difficulty_review_queue dq
              WHERE dq.question_id = q.question_id
                AND dq.review_status = 'pending'
          )
    """, {
        "question_id": int(question_id)
    })

def get_recent_accuracy(student_id, topic, limit=5):
    rows = fetch_all("""
        SELECT is_correct
        FROM student_attempts
        WHERE student_id = :student_id
          AND topic = :topic
        ORDER BY created_at DESC
        LIMIT :limit
    """, {
        "student_id": student_id,
        "topic": topic,
        "limit": limit
    })

    if len(rows) == 0:
        return None

    correct_count = sum(row[0] for row in rows)
    return correct_count / len(rows)


def get_adaptive_difficulty(current_difficulty, recent_accuracy):
    difficulty_order = ["easy", "medium", "hard"]

    if recent_accuracy is None:
        return current_difficulty

    current_index = difficulty_order.index(current_difficulty)

    if recent_accuracy >= 0.8 and current_index < 2:
        return difficulty_order[current_index + 1]

    if recent_accuracy <= 0.4 and current_index > 0:
        return difficulty_order[current_index - 1]

    return current_difficulty


def go_adaptive_next_question(df):
    student_id = st.session_state.student_id
    topic = st.session_state.selected_topic
    current_difficulty = st.session_state.selected_difficulty

    recent_accuracy = get_recent_accuracy(student_id, topic)
    next_difficulty = get_adaptive_difficulty(current_difficulty, recent_accuracy)

    answered_ids = set(st.session_state.question_status.keys())

    candidates = df[
        (df["topic"] == topic) &
        (df["difficulty"] == next_difficulty) &
        (~df["question_id"].astype(str).isin(answered_ids))
    ].reset_index(drop=True)

    if candidates.empty:
        candidates = df[
            (df["topic"] == topic) &
            (df["difficulty"] == current_difficulty)
        ].reset_index(drop=True)

    if not candidates.empty:
        next_qid = str(candidates.iloc[0]["question_id"])
        st.session_state.selected_difficulty = next_difficulty
        st.session_state.selected_question_id = next_qid
        st.session_state.last_result = None


def reset_student_progress(student_id):
    execute_query("""
        DELETE FROM student_progress
        WHERE student_id = :student_id
    """, {"student_id": student_id})

    execute_query("""
        DELETE FROM student_attempts
        WHERE student_id = :student_id
    """, {"student_id": student_id})

def init_session():
    defaults = {
        "student_id": "",
        "user_role": None,
        "page": "login",
        "selected_topic": None,
        "selected_difficulty": None,
        "selected_question_id": None,
        "question_status": {},
        "last_result": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_question_status(question_id):
    return st.session_state.question_status.get(str(question_id), "unanswered")


def set_question_status(question_id, status):
    st.session_state.question_status[str(question_id)] = status


def go_home():
    st.session_state.page = "home"
    st.session_state.selected_topic = None
    st.session_state.selected_difficulty = None
    st.session_state.selected_question_id = None
    st.session_state.last_result = None

def logout():
    st.session_state.student_id = ""
    st.session_state.user_role = None
    st.session_state.page = "login"
    st.session_state.selected_topic = None
    st.session_state.selected_difficulty = None
    st.session_state.selected_question_id = None
    st.session_state.question_status = {}
    st.session_state.last_result = None

def go_topic(topic):
    st.session_state.page = "topic"
    st.session_state.selected_topic = topic
    st.session_state.selected_difficulty = None
    st.session_state.selected_question_id = None
    st.session_state.last_result = None


def go_question(question_id):
    st.session_state.page = "question"
    st.session_state.selected_question_id = str(question_id)
    st.session_state.last_result = None


def go_next_question(df):
    current_id = str(st.session_state.selected_question_id)
    topic = st.session_state.selected_topic
    difficulty = st.session_state.selected_difficulty

    filtered = df[
        (df["topic"] == topic) &
        (df["difficulty"] == difficulty)
    ].reset_index(drop=True)

    ids = filtered["question_id"].astype(str).tolist()

    if current_id in ids and len(ids) > 0:
        idx = ids.index(current_id)
        next_idx = (idx + 1) % len(ids)
        st.session_state.selected_question_id = ids[next_idx]
        st.session_state.last_result = None

def go_previous_question(df):
    current_id = str(st.session_state.selected_question_id)
    topic = st.session_state.selected_topic
    difficulty = st.session_state.selected_difficulty

    filtered = df[
        (df["topic"] == topic) &
        (df["difficulty"] == difficulty)
    ].reset_index(drop=True)

    ids = filtered["question_id"].astype(str).tolist()

    if current_id in ids and len(ids) > 0:
        idx = ids.index(current_id)
        previous_idx = (idx - 1) % len(ids)

        st.session_state.selected_question_id = ids[previous_idx]
        st.session_state.last_result = None

def get_display_question_number(df, qid):
    topic = st.session_state.selected_topic
    difficulty = st.session_state.selected_difficulty

    filtered = df[
        (df["topic"] == topic) &
        (df["difficulty"] == difficulty)
    ].reset_index(drop=True)

    matched = filtered[filtered["question_id"].astype(str) == str(qid)]

    if matched.empty:
        return qid

    return matched.index[0] + 1


def status_color(status):
    if status == "correct":
        return "#22c55e"
    if status == "incorrect":
        return "#ef4444"
    return "#9ca3af"


def render_header():
    st.markdown(
        """
        <style>
        .main-title {
            font-size: 34px;
            font-weight: 700;
            margin-bottom: 0px;
        }

        .sub-title {
            color: #6b7280;
            margin-top: 0px;
        }

        .question-card {
            background-color: #f9fafb;
            padding: 24px;
            border-radius: 16px;
            border: 1px solid #e5e7eb;
            margin-top: 16px;
            margin-bottom: 16px;
        }

        .tag {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background-color: #e5e7eb;
            margin-left: 6px;
            font-size: 13px;
        }

        div.stButton > button {
            border-radius: 8px;
            height: 42px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<p class="main-title">Adaptive Math Practice</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">Choose a topic, select difficulty, and practice middle school math questions.</p>',
        unsafe_allow_html=True
    )

def render_logout_button():
    if st.session_state.student_id:
        col1, col2 = st.columns([6, 1])

        with col2:
            if st.button("Logout"):
                logout()
                st.rerun()

def render_question_buttons(df, topic, difficulty):
    filtered = df[
        (df["topic"] == topic) &
        (df["difficulty"] == difficulty)
    ].reset_index(drop=True)

    if filtered.empty:
        st.info("No questions available for this difficulty.")
        return

    st.markdown("### Choose a question")

    cols_per_row = 8

    for start in range(0, len(filtered), cols_per_row):
        cols = st.columns(cols_per_row)

        for i, (_, row) in enumerate(filtered.iloc[start:start + cols_per_row].iterrows()):
            qid = str(row["question_id"])
            display_num = start + i + 1
            status = get_question_status(qid)

            status_icon = {
                "correct": "🟢",
                "incorrect": "🔴",
                "unanswered": "⚪"
            }.get(status, "⚪")

            with cols[i]:
                if st.button(
                    f"{status_icon} {display_num}",
                    key=f"question_{qid}",
                    use_container_width=True
                ):
                    go_question(qid)
                    st.rerun()


def login_page():
    render_header()
    st.markdown("### Login")

    login_type = st.radio(
        "Select login type",
        ["Student", "Teacher"],
        horizontal=True
    )

    if login_type == "Student":
        student_id = st.text_input("Enter your student ID")

        if st.button("Start Practice"):
            if student_id.strip() == "":
                st.warning("Please enter your student ID.")
            else:
                student_id = student_id.strip()
                st.session_state.student_id = student_id
                st.session_state.user_role = "student"
                st.session_state.question_status = load_student_progress(student_id)
                st.session_state.page = "home"
                st.rerun()

    else:
        teacher_id = st.text_input("Enter your teacher ID")

        if st.button("Enter Teacher Review"):
            if teacher_id.strip() == "":
                st.warning("Please enter your teacher ID.")
            elif not is_valid_teacher(teacher_id.strip()):
                st.error("Invalid teacher ID. Please contact the administrator.")
            else:
                teacher_id = teacher_id.strip()
                st.session_state.student_id = teacher_id
                st.session_state.user_role = "teacher"
                st.session_state.page = "teacher_review"
                st.rerun()


def home_page(df):
    render_header()
    render_logout_button()
    st.markdown(f"**Student ID:** {st.session_state.student_id}")
    st.markdown("## Select a Topic")

    topics = sorted(df["topic"].unique())
    cols = st.columns(2)

    for i, topic in enumerate(topics):
        with cols[i % 2]:
            total = len(df[df["topic"] == topic])
            if st.button(f"{topic} ({total} questions)", key=f"topic_{topic}"):
                go_topic(topic)
                st.rerun()

    st.markdown("---")

    if st.button("Reset Progress"):

        reset_student_progress(
            st.session_state.student_id
        )

        st.session_state.question_status = {}
        st.success("Progress reset.")


def topic_page(df):
    render_header()
    render_logout_button()
    topic = st.session_state.selected_topic
    st.markdown(f"## {topic}")

    if st.button("← Back to Topic Selection"):
        go_home()
        st.rerun()

    difficulties = ["easy", "medium", "hard"]

    st.markdown("### Select Difficulty")

    difficulty_cols = st.columns(3)

    for i, difficulty in enumerate(difficulties):
        count = len(df[(df["topic"] == topic) & (df["difficulty"] == difficulty)])

        with difficulty_cols[i]:
            if st.button(f"{difficulty.title()} ({count})", key=f"diff_{difficulty}"):
                st.session_state.selected_difficulty = difficulty
                st.rerun()

    if st.session_state.selected_difficulty:
        st.markdown("---")
        st.markdown(f"## {st.session_state.selected_difficulty.title()} Questions")
        render_question_buttons(
            df,
            st.session_state.selected_topic,
            st.session_state.selected_difficulty
        )


def question_page(df):
    render_header()
    render_logout_button()

    qid = str(st.session_state.selected_question_id)
    row = df[df["question_id"].astype(str) == qid]

    if row.empty:
        st.error("Question not found.")
        if st.button("Back to Home"):
            go_home()
            st.rerun()
        return

    question = row.iloc[0]
    topic = question["topic"]
    difficulty = question["difficulty"]
    correct_answer = question["answer"]
    display_question_number = get_display_question_number(df, qid)

    top_cols = st.columns([3, 1])

    with top_cols[0]:
        st.markdown(f"### Question {display_question_number}")

    with top_cols[1]:
        st.markdown(
            f"""
            <div style="text-align:right;">
                <span class="tag">{topic}</span>
                <span class="tag">{difficulty.title()}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        f"""
        <div class="question-card">
            <h3>{question["question"]}</h3>
        </div>
        """,
        unsafe_allow_html=True
    )
    student_answer = st.text_input("Enter your answer", key=f"answer_{qid}")

    answer_cols = st.columns([1, 2, 1])

    with answer_cols[0]:
        if st.button("⬅️ Previous Question", use_container_width=True):
            go_previous_question(df)
            st.rerun()

    with answer_cols[1]:
        submit_clicked = st.button("Submit Answer", use_container_width=True)

    with answer_cols[2]:
        if st.button("Next Question ➡️", use_container_width=True):
            go_adaptive_next_question(df)
            st.rerun()

    if submit_clicked:
        if student_answer.strip() == "":
            st.warning("Please enter an answer before submitting.")
        else:
            if str(correct_answer).strip() == "":
                st.session_state.last_result = "no_answer_key"

            elif is_correct(student_answer, correct_answer):
                st.session_state.last_result = "correct"

                set_question_status(qid, "correct")

                save_student_progress(
                    st.session_state.student_id,
                    qid,
                    "correct",
                    student_answer
                )

                save_student_attempt(
                    st.session_state.student_id,
                    qid,
                    topic,
                    difficulty,
                    1,
                    student_answer
                )
                update_question_difficulty_stats(qid)
                check_difficulty_mismatch(qid)

            else:
                st.session_state.last_result = "incorrect"

                set_question_status(qid, "incorrect")

                save_student_progress(
                    st.session_state.student_id,
                    qid,
                    "incorrect",
                    student_answer
                )

                save_student_attempt(
                    st.session_state.student_id,
                    qid,
                    topic,
                    difficulty,
                    0,
                    student_answer
                )
                update_question_difficulty_stats(qid)
                check_difficulty_mismatch(qid)
            st.rerun()

    if st.session_state.last_result == "correct":
        st.success("Correct!")

        if st.button("Back to Home"):
            go_home()
            st.rerun()

    elif st.session_state.last_result == "incorrect":
        st.error("Incorrect. Try again or move to the next question.")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Try Again"):
                st.session_state.last_result = None
                st.rerun()

        with col2:
            if st.button("Back to Home"):
                go_home()
                st.rerun()

    elif st.session_state.last_result == "no_answer_key":
        st.warning(
            "This question does not have an answer key yet. "
            "Add an 'answer' column to your CSV so the app can check correctness."
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Next Question"):
                go_adaptive_next_question(df)
                st.rerun()

        with col2:
            if st.button("Back to Home"):
                go_home()
                st.rerun()

    st.markdown("---")

    if st.button("← Back to Question List"):
        st.session_state.page = "topic"
        st.session_state.selected_question_id = None
        st.session_state.last_result = None
        st.rerun()


def main():
    st.set_page_config(
        page_title="Adaptive Math Practice",
        page_icon="📘",
        layout="wide"
    )

    init_session()
    df = load_questions()

    if st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "home":
        home_page(df)
    elif st.session_state.page == "topic":
        topic_page(df)
    elif st.session_state.page == "question":
        question_page(df)
    elif st.session_state.page == "teacher_review":
        teacher_review_page()
    else:
        go_home()
        st.rerun()


if __name__ == "__main__":
    main()