import streamlit as st
import duckdb
import os
import time

DB_PATH = "dictionary.duckdb"

def get_connection(read_only=False):
    """
    Returns (conn, is_shared)
    """
    try:
        if 'duckdb_conn' not in st.session_state:
            st.session_state.duckdb_conn = duckdb.connect(DB_PATH, read_only=False)
            # Ensure JSON extension is loaded for metadata queries
            st.session_state.duckdb_conn.execute("INSTALL json; LOAD json;")
            st.session_state.duckdb_conn.execute("SET preserve_insertion_order=false")
        return st.session_state.duckdb_conn, True
    except Exception:
        conn = duckdb.connect(DB_PATH, read_only=read_only)
        try:
            conn.execute("INSTALL json; LOAD json;")
        except:
            pass
        return conn, False

def safe_execute(conn, query, params=(), retries=3):
    """Executes query with retries for locked database."""
    for i in range(retries):
        try:
            return conn.execute(query, params)
        except Exception as e:
            if "used by another process" in str(e) or "TransactionContext Error" in str(e):
                if i < retries - 1:
                    time.sleep(1 * (i + 1))
                    continue
            raise e

def init_db(conn=None):
    """Initializes the database schema."""
    close_conn = False
    if conn is None:
        conn, is_shared = get_connection()
        close_conn = not is_shared
    
    # transform metadata to json for flexibility
    # token table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id BIGINT,
            token VARCHAR,
            tag VARCHAR,
            lemma VARCHAR,
            corpus VARCHAR,
            metadata JSON,
            file_id VARCHAR
        );
    """)
    
    if close_conn:
        conn.close()

def reset_db():
    try:
        os.remove(DB_PATH)
    except FileNotFoundError:
        pass
    init_db()
