import duckdb
import os

DB_PATH = "dictionary.duckdb"

def get_connection():
    """Returns a connection to the DuckDB database."""
    conn = duckdb.connect(DB_PATH)
    return conn

def init_db(conn=None):
    """Initializes the database schema."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    
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
    
    # Create sequence for ID if not exists (DuckDB auto-increments differently, but let's just use manual batch ID or row_number if needed, or simple append)
    # Actually DuckDB doesn't strictly need a primary key for analytical workloads, but an ID is good for KWIC.
    # We will assume ingestion adds a sequential ID.
    
    if close_conn:
        conn.close()

def reset_db():
    try:
        os.remove(DB_PATH)
    except FileNotFoundError:
        pass
    init_db()
