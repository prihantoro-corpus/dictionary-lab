import streamlit as st
import duckdb
import os
import time

DB_PATH = "dictionary.duckdb"
if not os.path.exists(DB_PATH) and os.path.exists("bawe.duckdb"):
    DB_PATH = "bawe.duckdb"

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

def get_connection(read_only=False, allow_fallback=True):
    """
    Returns (conn, is_shared). 
    In Streamlit, attempts to use st.session_state for a persistent connection.
    read_only: Prefer read-only connection.
    allow_fallback: If True, allows falling back to Read-Only if Write fails (useful for startup).
                    If False, raises Error if requested mode cannot be satisfied (useful for Ingestion).
    """
    try:
        # Check if we are in a Streamlit context
        if 'duckdb_conn' not in st.session_state:
            # First time: try to connect. If locked, maybe it's another session/process.
            # We try read-only first if that's what's requested, or read-write if it's the main session.
            try:
                st.session_state.duckdb_conn = _connect_with_retry(DB_PATH, read_only=read_only)
            except Exception as e:
                if allow_fallback and not read_only and "used by another process" in str(e):
                     print("Database locked. Falling back to Read-Only mode.")
                     # Show warning only if in Streamlit context
                     if hasattr(st, 'warning'):
                         st.warning("⚠️ Database is locked by another process. Running in READ-ONLY mode.")
                     st.session_state.duckdb_conn = _connect_with_retry(DB_PATH, read_only=True)
                else:
                    raise e
            
            # Use safe execute for setting config (might fail on RO connection in some versions, but usually fine)
            try:
                st.session_state.duckdb_conn.execute("SET preserve_insertion_order=false")
                st.session_state.duckdb_conn.execute("PRAGMA memory_limit='512MB'")
            except:
                pass
                
        return st.session_state.duckdb_conn, True
        
    except (st.errors.StreamlitAPIException, Exception):
        # Fallback for background scripts or if session_state fails
        try:
            conn = _connect_with_retry(DB_PATH, read_only=read_only)
        except Exception as e:
            if allow_fallback and not read_only and "used by another process" in str(e):
                print("Database locked. Background script falling back to Read-Only mode.")
                conn = _connect_with_retry(DB_PATH, read_only=True)
            else:
                raise e
        return conn, False

def safe_execute(conn, query, params=(), retries=3):
    """Executes query with retries for locked database and logs duration."""
    start_time = time.time()
    for i in range(retries):
        try:
            res = conn.execute(query, params)
            duration = time.time() - start_time
            if duration > 1.0: # Log slow queries (> 1s)
                 try:
                     with open("slow_queries.log", "a", encoding="utf-8") as f:
                         f.write(f"SLOW QUERY ({duration:.2f}s): {query[:200]}... PARAMS={params}\n")
                 except: pass
            return res
        except Exception as e:
            msg = str(e)
            if "used by another process" in msg or "TransactionContext Error" in msg:
                if i < retries - 1:
                    time.sleep(1 * (i + 1))
                    continue
            # Raise immediately if it's a read-only error on a write query
            if "Cannot write to read-only database" in msg:
                 raise e
            raise e

def init_db(conn=None):
    """Initializes the database schema."""
    close_conn = False
    if conn is None:
        try:
            conn, is_shared = get_connection()
            close_conn = not is_shared
        except Exception as e:
            print(f"Failed to connect for init_db: {e}")
            return
    
    # Check if Read-Only: Try a dummy write or check config. 
    # Actually, simpler: Try creating table. If fails due to Read-Only, ignore it (assume DB exists).
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                id BIGINT,
                token VARCHAR,
                tag VARCHAR,
                lemma VARCHAR,
                corpus VARCHAR,
                metadata JSON,
                file_id VARCHAR,
                sentence_id BIGINT,
                doc_id BIGINT,
                sentence_num BIGINT
            );
        """)
    except Exception as e:
        if "read-only" in str(e).lower() or "transaction" in str(e).lower():
            print("Skipping table creation (Read-Only mode).")
        else:
            raise e
    
    if close_conn:
        conn.close()

def reset_db():
    try:
        os.remove(DB_PATH)
    except FileNotFoundError:
        pass
    init_db()
