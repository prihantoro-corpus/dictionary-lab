from pipeline.indexing import get_connection

def drop_indexes(conn=None):
    """Drops all indexes on the tokens table to speed up ingestion."""
    should_close = False
    if conn is None:
        conn, is_shared = get_connection(read_only=False)
        should_close = not is_shared
    
    print("Dropping indexes...")
    try:
        conn.execute("DROP INDEX IF EXISTS idx_tokens_token")
        conn.execute("DROP INDEX IF EXISTS idx_tokens_corpus")
        conn.execute("DROP INDEX IF EXISTS idx_tokens_file_id_id")
        print("Indexes dropped.")
    except Exception as e:
        print(f"Error dropping indexes: {e}")
    finally:
        if should_close:
            conn.close()

def add_indexes(conn=None):
    """Recreates indexes for query performance."""
    should_close = False
    if conn is None:
        conn, is_shared = get_connection(read_only=False)
        should_close = not is_shared

    print("Creating indexes...")
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens (token)")
        print("Created idx_tokens_token")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tokens_corpus ON tokens (corpus)")
        print("Created idx_tokens_corpus")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tokens_file_id_id ON tokens (file_id, id)")
        print("Created idx_tokens_file_id_id")
        print("All indexes created successfully.")
    except Exception as e:
        print(f"Error creating indexes: {e}")
    finally:
        if should_close:
            conn.close()

if __name__ == "__main__":
    add_indexes()
