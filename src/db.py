import streamlit as st
from sqlalchemy import create_engine, text


@st.cache_resource
def get_engine():
    database_url = st.secrets["DATABASE_URL"]
    return create_engine(database_url, pool_pre_ping=True)


def execute_query(query, params=None):
    engine = get_engine()
    with engine.begin() as conn:
        return conn.execute(text(query), params or {})


def fetch_all(query, params=None):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        return result.fetchall()


def fetch_one(query, params=None):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        return result.fetchone()