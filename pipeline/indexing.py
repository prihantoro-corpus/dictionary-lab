import streamlit as st
import duckdb
import os
import time

DB_PATH = "dictionary.duckdb"

def _connect_with_retry(path, read_only=False, retries=5):
    """Internal helper to connect with retries for locked DB."""
    for i in range(retries):
        try:
            conn = duckdb.connect(path, read_only=read_only)
            # Ensure JSON extension is loaded
            try:
                conn.execute("INSTALL json; LOAD json;")
            except:
                pass
            return conn
        except Exception as e:
            if "used by another process" in str(e) and i < retries - 1:
                time.sleep(0.5 * (i + 1))
                continue
            raise e

def get_connection(read_only=False):
    """
    Returns (conn, is_shared). 
    In Streamlit, attempts to use st.session_state for a persistent connection.
    """
    try:
        # Check if we are in a Streamlit context
        if 'duckdb_conn' not in st.session_state:
            # First time: try to connect. If locked, maybe it's another session/process.
            # We try read-only first if that's what's requested, or read-write if it's the main session.
            st.session_state.duckdb_conn = _connect_with_retry(DB_PATH, read_only=read_only)
            st.session_state.duckdb_conn.execute("SET preserve_insertion_order=false")
        return st.session_state.duckdb_conn, True
    except (st.errors.StreamlitAPIException, Exception):
        # Fallback for background scripts or if session_state fails
        conn = _connect_with_retry(DB_PATH, read_only=read_only)
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
